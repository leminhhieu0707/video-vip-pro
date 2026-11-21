"""Render a video from an edit plan (JSON). See references/plan.md for the full schema.

Usage:
  python render.py plan.json [--out final.mp4] [--aspect 16:9] [--draft] [--preview 5-15] [--keep]

Pipeline:
  1. each clip -> normalized segment (canvas size, fps, fit mode, speed, 48k stereo audio)   [cached]
  2. segments joined (stream copy if all hard cuts, xfade/acrossfade otherwise)
  3. final pass: image/video overlays, ASS text (subtitles + labels/titles), music with ducking,
     voiceover, fades, loudness normalization, encode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import subprocess
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from assgen import build_ass, resolve_pos  # noqa: E402
import theme  # noqa: E402
from common import FFMPEG, has_nvenc, load_json, parse_time, probe, run, save_json, video_codec_args  # noqa: E402

SEG_VERSION = 8  # bump when segment normalization changes, to invalidate cached segments
ASPECTS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350),
           "4:3": (1440, 1080), "3:4": (1080, 1440)}
XFADES = {"fade", "fadeblack", "fadewhite", "dissolve", "wipeleft", "wiperight", "wipeup", "wipedown",
          "slideleft", "slideright", "slideup", "slidedown", "circleopen", "circleclose", "radial", "smoothleft",
          "smoothright", "smoothup", "smoothdown", "zoomin", "pixelize", "hblur", "distance", "squeezev",
          "squeezeh", "coverleft", "coverright", "revealleft", "revealright", "diagtl", "diagbr", "hlslice",
          "vuslice", "circlecrop", "rectcrop", "fadegrays"}


def esc_filter_path(p: Path | str) -> str:
    return str(p).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def atempo_chain(speed: float) -> str:
    parts, s = [], speed
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


# ------------------------------------------------------------------ step 1: segments

def fit_filter(fit: str, W: int, H: int, src_w: int, src_h: int, focus: float, bg: str) -> str:
    """Video filter chain (starting from [0:v]) that produces exactly WxH, ending in [v]."""
    if fit == "auto":
        fit = "crop" if abs(src_w / src_h - W / H) < 0.08 else "blur"
    if fit == "crop":
        return (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
                f"crop={W}:{H}:(iw-{W})*{focus}:(ih-{H})/2,setsar=1[v]")
    if fit == "pad":
        return (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={bg},setsar=1[v]")
    if fit == "stretch":
        return f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1[v]"
    # blur: blurred, darkened fill behind the whole frame
    return (f"[0:v]split=2[bgs][fgs];"
            f"[bgs]scale={W // 4}:{H // 4}:force_original_aspect_ratio=increase,crop={W // 4}:{H // 4},"
            f"gblur=sigma=12,eq=brightness=-0.08:saturation=1.1,scale={W}:{H}[bgb];"
            f"[fgs]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
            f"[bgb][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]")


GRADES = {
    # name: filters (applied after the clip is fitted to the canvas)
    "bright": ["eq=brightness=0.015:contrast=1.02:gamma=1.02:saturation=1.02", "vibrance=intensity=0.05"],
    "vivid": ["eq=contrast=1.04:saturation=1.05", "vibrance=intensity=0.12"],
    "warm": ["colortemperature=temperature=5200:mix=0.6", "eq=saturation=1.06:contrast=1.03"],
    "cool": ["colortemperature=temperature=8200:mix=0.6", "eq=contrast=1.04"],
    "cinematic": ["colorbalance=rs=-0.04:gs=0.0:bs=0.07:rh=0.07:gh=0.02:bh=-0.06",
                  "eq=contrast=1.1:saturation=0.95:gamma=0.97"],
    # filmic but retail-safe: deeper contrast, teal shadows, warm skin, whites kept clean, soft vignette
    "cinema_ad": ["colorbalance=rs=-0.035:gs=0.0:bs=0.05:rm=0.015:bm=-0.01:rh=0.025:gh=0.0:bh=-0.02",
                  "eq=contrast=1.1:saturation=1.0:gamma=0.96", "vignette=angle=PI/6"],
    "vintage": ["curves=preset=vintage", "eq=saturation=0.85:contrast=1.04"],
    "pastel": ["eq=brightness=0.04:contrast=0.94:saturation=0.85:gamma=1.06"],
    # beauty/studio kiểu Hàn: sáng, mềm, da hồng hào, nền trắng sạch
    "han_min": ["eq=brightness=0.03:contrast=0.98:gamma=1.05", "colorbalance=rm=0.025:bm=0.02:gh=-0.01", "vibrance=intensity=0.08"],
    # appetizing food / restaurant: warm mids, richer colour without neon, a touch of clarity, soft vignette
    "food": ["colorbalance=rm=0.03:bm=-0.03:rh=0.02:bh=-0.02", "eq=contrast=1.07:gamma=0.98:saturation=1.04",
             "vibrance=intensity=0.18", "unsharp=5:5:0.45:5:5:0", "vignette=angle=PI/7"],
    "moody": ["eq=brightness=-0.03:contrast=1.12:saturation=0.82", "colorbalance=bs=0.05:bh=-0.03"],
    "bw": ["hue=s=0", "eq=contrast=1.15"],
}


def grade_filters(g) -> list[str]:
    """'vivid' | ['bright','warm'] | {"preset":..,"brightness":..,"contrast":..,"saturation":..,"gamma":..,
    "temperature":K,"vibrance":x,"lut":"file.cube"}"""
    if not g:
        return []
    if isinstance(g, str):
        return list(GRADES.get(g, []))
    if isinstance(g, list):
        return [f for x in g for f in grade_filters(x)]
    out = grade_filters(g.get("preset"))
    if any(k in g for k in ("brightness", "contrast", "saturation", "gamma")):
        out.append(f"eq=brightness={g.get('brightness', 0)}:contrast={g.get('contrast', 1)}:"
                   f"saturation={g.get('saturation', 1)}:gamma={g.get('gamma', 1)}")
    if g.get("temperature"):
        out.append(f"colortemperature=temperature={g['temperature']}:mix={g.get('temperature_mix', 0.6)}")
    if g.get("vibrance"):
        out.append(f"vibrance=intensity={g['vibrance']}")
    if g.get("vignette"):
        out.append(f"vignette=angle={g['vignette']}")
    if g.get("lut"):
        out.append(f"lut3d=file='{esc_filter_path(g['lut'])}'")
    return out


def beauty_graph(inp: str, out: str, strength: float, glow: float = 0.02) -> str:
    """Skin smoothing: edge-preserving blur on luma, merged only where pixels have skin chroma
    (YCbCr skin box), with a feathered mask so eyes, hair, text and the background stay sharp."""
    s = max(0.0, min(1.0, float(strength)))
    sig_s, sig_r = 3 + 7 * s, 0.04 + 0.08 * s
    return (f"{inp}format=yuv444p,split=3[bb0][bb1][bb2];"
            f"[bb1]bilateral=sigmaS={sig_s:.1f}:sigmaR={sig_r:.3f}:planes=1,eq=brightness={glow * s:.3f}[bsm];"
            f"[bb2]extractplanes=u+v[bu][bv];"
            f"[bu]lut=c0='if(between(val,77,127),255,0)'[bmu];"
            f"[bv]lut=c0='if(between(val,134,173),255,0)'[bmv];"
            f"[bmu][bmv]blend=all_mode=multiply,gblur=sigma=5,lut=c0='val*{0.35 + 0.65 * s:.2f}',"
            f"format=yuv444p[bmask];"
            f"[bb0][bsm][bmask]maskedmerge=planes=1,format=yuv420p{out}")


DENOISE = {
    # rumble/AC/wind removal + broadband denoise + gentle gate between words
    "light": "highpass=f=90:poles=2,highpass=f=90:poles=2,afftdn=nr=10:nf=-45:tn=1",
    "medium": ("highpass=f=150:poles=2,highpass=f=150:poles=2,highpass=f=150:poles=2,highpass=f=150:poles=2,"
               "afftdn=nr=15:nf=-45:tn=1,agate=threshold=0.02:ratio=3:range=0.15:attack=5:release=180"),
    "strong": ("highpass=f=170:poles=2,highpass=f=170:poles=2,highpass=f=170:poles=2,highpass=f=170:poles=2,"
               "afftdn=nr=20:nf=-45:tn=1,anlmdn=s=3,agate=threshold=0.025:ratio=4:range=0.1:attack=5:release=150"),
}
# clearer, punchier speech: cut mud, add presence, compress, tame sibilance
VOICE_ENHANCE = ("equalizer=f=250:t=q:w=1.2:g=-2.5,equalizer=f=3200:t=q:w=1:g=3,equalizer=f=9000:t=q:w=1:g=1.5,"
                 "acompressor=threshold=0.08:ratio=3:attack=5:release=120:makeup=2,deesser=i=0.4")


def make_segment(c: dict, i: int, canvas: dict, work: Path, vcodec: list[str]) -> dict:
    W, H, fps = canvas["width"], canvas["height"], canvas["fps"]
    src = Path(c["src"])
    info = probe(src)
    is_img = info.get("is_image") or src.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp")
    speed = float(c.get("speed", 1))
    if is_img:
        dur = parse_time(c.get("duration", 3))
        cin, cout = 0.0, dur
    else:
        cin = parse_time(c.get("in", 0))
        cout = parse_time(c["out"]) if c.get("out") is not None else info["duration"]
        cout = min(cout, info["duration"])
        dur = (cout - cin) / speed
    c["_out"] = cout
    c["_dur"] = dur

    key = hashlib.md5(json.dumps({k: v for k, v in c.items() if not k.startswith("_")}, sort_keys=True,
                                 ensure_ascii=False).encode() + f"{W}x{H}@{fps}|{src.stat().st_mtime}|{vcodec}|{SEG_VERSION}".encode()
                      ).hexdigest()[:10]
    out = work / f"seg_{i:03d}_{key}.mp4"
    c["_seg"] = out
    if out.exists():
        c["_dur"] = video_duration(out)  # real length (frame-rounded) keeps overlays/voiceover in sync
        return c

    fit = c.get("fit", canvas.get("fit", "auto"))
    focus = float(c.get("focus", 0.5))
    bg = canvas.get("bg", "black")
    inputs: list[str] = []
    if is_img:
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", str(src)]
    else:
        inputs += ["-ss", f"{cin:.3f}", "-to", f"{cout:.3f}", "-i", str(src)]
    inputs += ["-f", "lavfi", "-t", f"{dur + 0.5:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]

    vf = fit_filter(fit, W, H, info["width"], info["height"], focus, bg)
    if info.get("is_hdr"):
        # iPhone HDR (HLG / PQ, 10-bit bt2020) -> SDR bt709, so it matches other clips and joins cleanly
        tin = "arib-std-b67" if info.get("color_transfer") == "arib-std-b67" else "smpte2084"
        # hable + a little contrast lands HDR phone footage at the same exposure as SDR clips (measured YAVG)
        h = {"tonemap": "hable", "npl": 150, "contrast": 1.12, "gamma": 0.92, "saturation": 1.08, **(c.get("hdr") or {})}
        vf = (f"[0:v]zscale=tin={tin}:min=bt2020nc:pin=bt2020:t=linear:npl={h['npl']},format=gbrpf32le,"
              f"zscale=p=bt709,tonemap=tonemap={h['tonemap']}:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,"
              f"eq=contrast={h['contrast']}:gamma={h['gamma']}:saturation={h['saturation']}[sdr];"
              + vf.replace("[0:v]", "[sdr]", 1))
    post = []
    if not is_img and c.get("punch"):
        # static punch-in (e.g. 1.15) to fake a second camera angle on talking-head cuts
        p = float(c["punch"])
        post.append(f"scale=iw*{p}:ih*{p}:flags=lanczos,crop={W}:{H}:(iw-{W})*{focus}:(ih-{H})*0.4")
    slow = (is_img and c.get("zoom", "in") != "none") or (not is_img and c.get("zoom") in ("in", "out"))
    if slow or (not is_img and c.get("zooms")):
        # Ken Burns: upscale then zoompan for smooth motion. zoompan emits one frame per INPUT frame, so the
        # source must be resampled to the canvas fps first (a 60 fps phone clip otherwise plays 2x slow)
        frames = int(round(dur * speed * fps))
        zexpr = "1"
        if slow:
            z = c.get("zoom", "in")
            amt = float(c.get("zoom_amount", 0.12 if is_img else 0.08))
            zexpr = f"1+{amt}*on/{frames}" if z == "in" else f"1+{amt}-{amt}*on/{frames}"
        # keyframed punch zooms (CapCut-style "zoom in on the keyword"): ease in, hold, ease out.
        # zoompan runs before the speed change, so clip-relative output times are scaled back to source time
        fx, fy = focus, 0.4
        blur_win = []
        for k in c.get("zooms") or []:
            a = parse_time(k.get("at", 0)) * speed
            amt = float(k.get("to", 1.25)) - 1
            din = max(0.04, float(k.get("in", 0.18)) * speed)
            hold = float(k.get("hold", 1.2)) * speed
            dout = k.get("out", 0.25)
            fx, fy = float(k.get("x", fx)), float(k.get("y", fy))
            up = f"st(1,clip((on/{fps}-{a:.3f})/{din:.3f},0,1))*ld(1)*(3-2*ld(1))"
            fast = abs(amt) >= 0.3 if k.get("blur") is None else bool(k.get("blur"))
            if fast and din >= 0.08:
                blur_win.append((a, a + din))
            if dout is None:  # stay zoomed to the end of the clip
                env = f"({up})"
            else:
                b = a + din + hold
                dd = max(0.04, float(dout) * speed)
                if fast:
                    blur_win.append((b, b + dd))
                env = f"({up})*(1-st(2,clip((on/{fps}-{b:.3f})/{dd:.3f},0,1))*ld(2)*(3-2*ld(2)))"
            zexpr += f"+{amt}*{env}"
        zp = (f";[pre]fps={fps},scale={W * 2}:{H * 2}:flags=lanczos,"
              f"zoompan=z='{zexpr}':x='(iw-iw/zoom)*{fx}':y='(ih-ih/zoom)*{fy}':d=1:s={W}x{H}:fps={fps}")
        if blur_win:  # motion blur while a fast zoom ramps (snap 2x -> pull back)
            en = "+".join(f"between(t,{a0:.3f},{a1:.3f})" for a0, a1 in blur_win)
            zp += f"[zp];[zp]split[zpa][zpb];[zpb]tmix=frames=5[zpm];[zpa][zpm]overlay=enable='{en}'[v]"
        else:
            zp += "[v]"
        vf = vf.replace("[v]", "[pre]") + zp
    if not is_img and c.get("shake"):
        # short camera shake on an impact moment: {"at": 1.2, "dur": 0.35, "amp": 14} (clip-relative seconds)
        sk = c["shake"] if isinstance(c["shake"], dict) else {"at": 0}
        a, d, amp = parse_time(sk.get("at", 0)) * speed, float(sk.get("dur", 0.35)) * speed, int(sk.get("amp", 14))
        env = f"between(t,{a:.3f},{a + d:.3f})*(1-(t-{a:.3f})/{d:.3f})"
        post.append(f"scale={W + 2 * amp}:{H + 2 * amp}:flags=lanczos,"
                    f"crop={W}:{H}:'{amp}+{amp}*sin(t*90)*{env}':'{amp}+{amp}*cos(t*77)*{env}'")
    if speed != 1:
        post.append(f"setpts=PTS/{speed}")
    if c.get("color"):  # simple grade: {"brightness":0.03,"contrast":1.08,"saturation":1.15}
        g = c["color"]
        post.append(f"eq=brightness={g.get('brightness', 0)}:contrast={g.get('contrast', 1)}:"
                    f"saturation={g.get('saturation', 1)}:gamma={g.get('gamma', 1)}")
    if c.get("flip"):
        post.append("hflip")
    post += grade_filters(c.get("grade"))
    # one pixel format AND one colour range for every segment: mixing full-range (yuvj420p) phone/stock clips
    # with limited-range ones makes the concat-joined base re-init filters mid-stream and lose timestamps
    post += [f"fps={fps}", "setsar=1", "scale=out_range=limited", "format=yuv420p"]
    vf = vf.replace("[v]", "[vfit]") + f";[vfit]{','.join(post)}[v]"
    if c.get("beauty"):
        vf = vf.replace("[v]", "[vbeauty]") + ";" + beauty_graph("[vbeauty]", "[v]", c["beauty"])

    vol = 0 if c.get("mute") or not info.get("has_audio") or is_img else float(c.get("volume", 1))
    clean = []
    if c.get("denoise"):
        clean.append(DENOISE.get(str(c["denoise"]), DENOISE["medium"]))
    if c.get("voice"):
        clean.append(VOICE_ENHANCE)
    clean_s = "".join(x + "," for x in clean)
    if vol and not is_img:
        af = (f"[0:a]aresample=48000,aformat=channel_layouts=stereo,{clean_s}"
              f"{atempo_chain(speed) + ',' if speed != 1 else ''}volume={vol},"
              # 12 ms ramps at both ends: hard jump cuts otherwise click/pop on the audio
              f"afade=t=in:d=0.012,afade=t=out:st={max(0.0, dur - 0.012):.3f}:d=0.012[a0];"
              f"[a0][1:a]amix=inputs=2:duration=first:normalize=0,atrim=0:{dur:.3f}[a]")
    else:
        af = f"[1:a]atrim=0:{dur:.3f}[a]"
    run([FFMPEG, "-y", *inputs, "-filter_complex", vf + ";" + af, "-map", "[v]", "-map", "[a]",
         "-t", f"{dur:.3f}", *vcodec, "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)])
    c["_dur"] = video_duration(out)
    return c


# ------------------------------------------------------------------ step 2: join

def keep_timing(clips: list[dict]) -> None:
    """Transitions without losing time: xfade overlaps two clips by d, which normally shortens the timeline and
    pushes voice-over / overlays out of sync. With "keep_timing": true every transition borrows d extra seconds of
    handle from the outgoing clip (or, if its source ends, from the incoming clip), so each clip still starts at
    the same timeline second and the total length is unchanged."""
    for i in range(1, len(clips)):
        t = clips[i].get("transition")
        if isinstance(t, str):
            t = {"type": t}
        if not t or t.get("type", "cut") == "cut":
            continue
        d = float(t.get("duration", 0.4))
        prev, cur = clips[i - 1], clips[i]
        sp_prev, sp_cur = float(prev.get("speed", 1)), float(cur.get("speed", 1))
        try:
            src_len = float(probe(prev["src"])["duration"])
        except Exception:
            src_len = 1e9
        out_p = parse_time(prev["out"]) if prev.get("out") is not None else src_len
        if out_p + d * sp_prev <= src_len - 0.02:
            prev["out"] = round(out_p + d * sp_prev, 3)
        elif parse_time(cur.get("in", 0)) - d * sp_cur >= 0:
            cur["in"] = round(parse_time(cur.get("in", 0)) - d * sp_cur, 3)
        else:  # no handles anywhere: fall back to a hard cut rather than drifting
            cur.pop("transition", None)


def join_segments(clips: list[dict], work: Path, vcodec: list[str], fps: int = 30) -> tuple[Path, list[float], float]:
    trans = []
    for i, c in enumerate(clips):
        t = c.get("transition") if i > 0 else None
        if isinstance(t, str):
            t = {"type": t}
        if t and t.get("type", "cut") != "cut":
            d = min(float(t.get("duration", 0.4)), clips[i - 1]["_dur"] / 2, c["_dur"] / 2)
            ttype = t["type"] if t["type"] in XFADES else "fade"
            trans.append((ttype, d))
        else:
            trans.append(None)

    starts, cur = [], 0.0
    for c, t in zip(clips, trans):
        if t:
            cur -= t[1]
        starts.append(cur)
        cur += c["_dur"]
    total = cur

    base = work / "base.mp4"
    if not any(trans):
        lst = work / "concat.txt"
        lst.write_text("".join(f"file '{c['_seg'].as_posix()}'\n" for c in clips), encoding="utf-8")
        run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(base)])
        return base, starts, total

    # Hard-cut runs are joined losslessly first; only the run boundaries get xfade/acrossfade.
    runs: list[list[int]] = []
    for i in range(len(clips)):
        if i == 0 or trans[i]:
            runs.append([i])
        else:
            runs[-1].append(i)
    run_files, run_durs = [], []
    for k, r in enumerate(runs):
        if len(r) == 1:
            f = clips[r[0]]["_seg"]
        else:
            lst = work / f"run_{k:02d}.txt"
            lst.write_text("".join(f"file '{clips[i]['_seg'].as_posix()}'\n" for i in r), encoding="utf-8")
            f = work / f"run_{k:02d}.mp4"
            run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(f)])
        run_files.append(f)
        run_durs.append(video_duration(f))

    # Video: xfade chain between runs. Audio: each run placed at its start with short fades at the overlaps,
    # then mixed (a long acrossfade chain stalls in ffmpeg and truncates the output).
    # Two separate passes: in one graph the audio mix needs every input at t=0 while xfade reads them in turn,
    # which deadlocks ffmpeg's demuxer queues.
    inputs, fc = [], []
    for k, f in enumerate(run_files):
        inputs += ["-i", str(f)]
        # concat -c copy of hard-cut runs can report an odd rate (e.g. 359/12), which xfade rejects
        fc.append(f"[{k}:v]fps={fps},settb=AVTB,setpts=PTS-STARTPTS[rv{k}]")
    afc = []
    vprev, acc = "[rv0]", run_durs[0]
    run_starts = [0.0]
    for k in range(1, len(runs)):
        ttype, d = trans[runs[k][0]]
        acc -= d
        run_starts.append(acc)
        fc.append(f"{vprev}[rv{k}]xfade=transition={ttype}:duration={d:.3f}:offset={acc:.3f}[v{k}]")
        acc += run_durs[k]
        vprev = f"[v{k}]"
    alabels = []
    for k in range(len(runs)):
        din = trans[runs[k][0]][1] if k > 0 else 0
        dout = trans[runs[k + 1][0]][1] if k + 1 < len(runs) else 0
        chain = [f"atrim=0:{run_durs[k]:.3f}", "asetpts=PTS-STARTPTS"]
        if din:
            chain.append(f"afade=t=in:d={din:.3f}")
        if dout:
            chain.append(f"afade=t=out:st={run_durs[k] - dout:.3f}:d={dout:.3f}")
        ms = int(round(run_starts[k] * 1000))
        chain.append(f"adelay={ms}|{ms}")
        afc.append(f"[{k}:a]{','.join(chain)}[ra{k}]")
        alabels.append(f"[ra{k}]")
    afc.append(f"{''.join(alabels)}amix=inputs={len(alabels)}:duration=longest:normalize=0,atrim=0:{acc:.3f}[aout]")
    vscript, ascript = work / "join.fc", work / "join_audio.fc"
    vscript.write_text(";\n".join(fc), encoding="utf-8")
    ascript.write_text(";\n".join(afc), encoding="utf-8")
    vtmp, atmp = work / "base_v.mp4", work / "base_a.m4a"
    run([FFMPEG, "-y", *inputs, "-/filter_complex", str(vscript), "-map", vprev, "-an", *vcodec, str(vtmp)])
    run([FFMPEG, "-y", *inputs, "-/filter_complex", str(ascript), "-map", "[aout]", "-vn",
         "-c:a", "aac", "-b:a", "192k", str(atmp)])
    run([FFMPEG, "-y", "-i", str(vtmp), "-i", str(atmp), "-map", "0:v", "-map", "1:a", "-c", "copy", str(base)])
    return base, starts, total


def video_duration(f: Path) -> float:
    import subprocess
    from common import FFPROBE
    p = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration",
                        "-of", "csv=p=0", str(f)], capture_output=True, text=True)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return probe(f)["duration"]


# ------------------------------------------------------------------ step 3: final

SFX_DIR = Path(__file__).resolve().parent.parent / "assets" / "sfx"
# lists rotate per event type so consecutive overlays don't all make the same sound
AUTO_SFX_DEFAULTS = {"transition": ["whoosh_fast", "whoosh_air", "sweep_small", "whoosh_cinematic"],
                     "label": ["pop_long", "pop_bubble", "pop_click"],
                     "badge": ["pop_message", "pop_bubble", "pop_long", "pop_click"],
                     "title": ["whoosh_cinematic", "sweep_small", "whoosh_air"],
                     "price": ["pop_long", "correct_answer", "pop_bubble"], "text": None, "image": None, "video": None}


def _pick(name, counters: dict, key: str):
    if isinstance(name, list):
        if not name:
            return None
        i = counters.get(key, 0)
        counters[key] = i + 1
        return name[i % len(name)]
    return name


# names used in recipes that may not exist in a fresh install -> the built-in synthesized sound (make_sfx.py)
SFX_ALIASES = {"whoosh_air": "whoosh", "whoosh_fast": "whoosh3", "whoosh_cinematic": "whoosh2", "sweep_small": "swoosh",
               "zoom_vacuum": "riser", "pop_bubble": "bubble", "pop_click": "pop2", "pop_long": "pop3",
               "pop_message": "notify", "pop_whoosh": "pop", "correct_answer": "ding2", "camera_shutter": "shutter",
               "typing_real": "typing", "bass_hit": "impact", "impact_trailer": "impact", "impact_intro": "vine_boom",
               "bell_notify": "notify", "achievement": "tada", "cheer": "tada", "record_scratch_real": "record_scratch",
               "sad_trombone_real": "sad_trombone", "drum_joke": "rimshot",
               "tech_tick": "click", "tech_blip": "pop2", "tech_soft": "pop", "tech_scan": "sparkle", "tech_data": "glitch",
               "tech_intro": "riser", "tech_rise_hit": "impact", "snap": "click"}


def resolve_sfx(name: str, root: Path) -> Path | None:
    p = Path(name)
    for nm in (name, SFX_ALIASES.get(name)):
        if not nm:
            continue
        for cand in ((p if p.is_absolute() else root / p) if nm == name else SFX_DIR / nm,
                     SFX_DIR / nm, SFX_DIR / f"{nm}.wav", SFX_DIR / f"{nm}.mp3"):
            if cand.exists():
                return cand
    print(f"[render] warning: sound effect '{name}' not found (run make_sfx.py?)")
    return None


# Library sounds differ by 30 dB+ (a cinematic boom peaks near 0 dB, a pencil or mouse click near -30 dB), so the same
# plan volume made quiet ones vanish under the voice and loud ones slam the limiter. With a sound design on, every file
# is first levelled to a target loudness (loudest 100 ms window), impacts a bit hotter, then the plan volume applies.
SFX_TARGET_DB = -13.0
SFX_TARGET_FAMILY = {"boom": -7.0, "hit": -7.0, "impact": -7.0, "vine": -7.0, "riser": -11.0}
SFX_MAX_BOOST_DB = 20.0
_SFX_NORM: dict | None = None
_SFX_NORM_FILE = Path.home() / ".cache" / "video-vip-pro" / "sfx_norm.json"


def sfx_norm(path: Path) -> float:
    """Linear gain that brings this sound file's loudest 100 ms to its family target (cached per file)."""
    global _SFX_NORM
    if _SFX_NORM is None:
        try:
            _SFX_NORM = json.loads(_SFX_NORM_FILE.read_text(encoding="utf-8"))
        except Exception:
            _SFX_NORM = {}
    p = Path(path)
    try:
        st = p.stat()
    except OSError:
        return 1.0
    key = f"{p.resolve()}|{st.st_size}|{int(st.st_mtime)}"
    if key not in _SFX_NORM:
        raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(p), "-t", "4", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                             capture_output=True).stdout
        x = np.frombuffer(raw, np.float32)
        w = 1600
        if len(x) < w:
            x = np.pad(x, (0, w - len(x)))
        peak = max(float(np.sqrt((x[i:i + w] ** 2).mean())) for i in range(0, len(x) - w + 1, w // 2))
        _SFX_NORM[key] = round(20 * np.log10(peak + 1e-9), 2)
        try:
            _SFX_NORM_FILE.parent.mkdir(parents=True, exist_ok=True)
            _SFX_NORM_FILE.write_text(json.dumps(_SFX_NORM, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
    fam = p.stem.split("_")[0].lower()
    target = SFX_TARGET_FAMILY.get(fam, SFX_TARGET_DB)
    db = max(-40.0, min(SFX_MAX_BOOST_DB, target - float(_SFX_NORM[key])))
    return 10 ** (db / 20)


def sfx_events(plan: dict, starts: list[float], total: float) -> list[tuple[Path, float, float, float]]:
    """[(file, time_on_timeline, volume, max_len)] from plan['sfx'] and plan['auto_sfx'].
    Long library sounds (applause, ticking, laughs) are cut to max_len with a fade-out.
    With a sound design on, each file is levelled first (sfx_norm) so the plan volume means the same for every sound."""
    root = Path(plan.get("_root", "."))
    import sound
    gain = float(plan.get("sfx_gain", 6.0 if plan.get("sound_design") else 1.0))  # effect level vs. the voice
    fb = lambda n: resolve_sfx(n, root)  # noqa: E731
    ev = []
    for s in plan.get("sfx", []) or []:
        at0 = parse_time(s.get("at", 0)) + (starts[int(s["clip"])] if "clip" in s else 0)
        for name, off, _ in sound.layers(s["sfx"]):
            f = sound.pick(name, fb)
            if f:
                ev.append((f, at0 + off, float(s.get("volume", 0.3)) * gain, float(s.get("len", 3.0))))
    # overlays that name their own sound ("sfx": "boom" or ["whoosh", "boom"])
    if plan.get("sound_design"):
        for o in plan.get("overlays", []) or []:
            if o.get("sfx"):
                at0 = parse_time(o.get("start", 0)) + (starts[int(o["clip"])] if "clip" in o else 0)
                for name, off, _ in sound.layers(o["sfx"]):
                    f = sound.pick(name, fb)
                    if f:
                        ev.append((f, at0 + off, float(o.get("sfx_volume", 0.2)) * gain, 3.0))
        taken = [e[1] for e in ev]
        for fam, at, vol in sound.design(plan, starts):
            if any(abs(at - t) < 0.12 for t in taken):  # the builder already put a sound here
                continue
            f = sound.pick(fam, fb)
            if f:
                ev.append((f, at, vol * gain, 2.5))
        # sound brain: story sounds from the meaning of the words (money -> kaching, "giòn" -> crunch, surprise -> riser+boom...)
        sd = plan.get("sound_design")
        brain = sd.get("brain") if isinstance(sd, dict) else None
        if brain:
            import sound_brain
            trs = brain.get("transcripts") or []
            trs = [str((root / t).resolve()) if not Path(t).is_absolute() else t for t in (trs if isinstance(trs, list) else [trs])]
            try:
                words = sound_brain.words_from(trs, float(brain.get("offset", 0)))
                style = sd.get("style", "trend")
                for pk in sound_brain.suggest(words, style, bool(brain.get("comedy")), busy=[e[1] for e in ev],
                                              max_memes=int(brain.get("max_memes", 3))):
                    f = sound.pick(pk["sfx"], fb)
                    if f:
                        ev.append((f, pk["at"], pk["volume"] * gain, 2.5))
            except Exception as e:  # never fail a render because of the sound brain
                print(f"[render] sound brain skipped: {e}")
    auto = plan.get("auto_sfx")
    if auto:
        cfg = {**AUTO_SFX_DEFAULTS, **(auto if isinstance(auto, dict) else {})}
        vol = float(cfg.get("volume", 0.22))
        counters: dict = {}
        # transitions: whoosh peaks mid-transition (file is ~0.55 s, peak in the middle)
        for i, c in enumerate(plan["clips"]):
            t = c.get("transition") if i else None
            kind = (t if isinstance(t, str) else (t or {}).get("type", "cut")) if t else None
            name = _pick(c.get("transition_sfx", cfg.get("transition") if kind and kind != "cut" else cfg.get("cut")),
                         counters, "transition")
            if name:
                f = resolve_sfx(name, root)
                if f:
                    ev.append((f, starts[i] - 0.25, vol, 2.0))
        for o in ([] if plan.get("sound_design") else plan.get("overlays", [])):
            name = _pick(o.get("sfx", cfg.get(o.get("type", "text"))), counters, o.get("type", "text"))
            if not name:
                continue
            f = resolve_sfx(name, root)
            if f:
                at = parse_time(o.get("start", 0)) + (starts[int(o["clip"])] if "clip" in o else 0)
                ev.append((f, at, float(o.get("sfx_volume", vol)), float(o.get("sfx_len", 3.0))))
    if plan.get("sound_design") and plan.get("sfx_normalize", True):
        ev = [(f, at, round(v * sfx_norm(f), 4), mx) for f, at, v, mx in ev]
    return [e for e in ev if 0 <= e[1] < total]

FROST_TINTS = {"light": "0xEEF2FF@0.62", "blue": "0x2A44C8@0.40", "dark": "0x0B1020@0.45", "white": "0xFFFFFF@0.7",
               "navy": "0x0B1E5E@0.86", "solid": "0xEEF1F8@1"}


def overlay_times(o: dict, starts: list[float], total: float) -> tuple[float, float]:
    off = starts[int(o["clip"])] if "clip" in o else 0.0
    s = parse_time(o.get("start", 0)) + off
    e = parse_time(o["end"]) + off if o.get("end") is not None else (
        s + parse_time(o["duration"]) if "duration" in o else total)
    return s, min(e, total)


def round_corners(r: int) -> str:
    """geq alpha mask that rounds the corners of an rgba stream by r px."""
    return (f"geq=lum='p(X,Y)':a='if(gt(abs(W/2-X),W/2-{r})*gt(abs(H/2-Y),H/2-{r}),"
            f"if(lte(hypot({r}-(W/2-abs(W/2-X)),{r}-(H/2-abs(H/2-Y))),{r}),255,0),255)*alpha(X,Y)/255'"
            f":cb='cb(X,Y)':cr='cr(X,Y)'")


def frost_layer(o: dict, k: int, vlast: str, fc: list[str], starts: list[float], total: float, W: int, H: int) -> str:
    """Frosted-glass scene (Blue style): everything below is blurred and washed with a tint for [start, end].
    Optional "window": {"crop": [x, y, w, h] fractions of the frame, "pos": [x, y], "width": 0.8, "radius": 40}
    puts a sharp, rounded crop of the frame (usually the speaker) on top, for the split layout."""
    s, e = overlay_times(o, starts, total)
    fd = float(o.get("fade", 0.25))
    mode = o.get("mode", "light")
    tint = None if mode == "none" else theme.tint(FROST_TINTS.get(mode, mode))
    sigma = float(o.get("blur", 36)) / 4
    win = o.get("window")
    fc.append(f"{vlast}split={3 if win else 2}[fra{k}][frb{k}]" + (f"[frc{k}]" if win else ""))
    fi_, fo_ = float(o.get("fade_in", fd)), float(o.get("fade_out", fd))
    fl = ([f"fade=t=in:st={s:.3f}:d={fi_}:alpha=1"] if fi_ > 0 else []) + (
        [f"fade=t=out:st={max(s, e - fo_):.3f}:d={fo_}:alpha=1"] if e < total and fo_ > 0 else [])
    fades = ",".join(fl) or "null"
    look = [f"drawbox=c={tint}:t=fill"] if tint else []
    if o.get("grid"):  # navy "blueprint" scene: faint grid + soft light blobs
        g = int(o["grid"]) if not isinstance(o["grid"], bool) else 54
        look += [f"drawgrid=w={g}:h={g}:t=2:c=white@0.07", "vignette=PI/4.5"]
    fc.append(f"[frb{k}]scale={W // 4}:{H // 4},gblur=sigma={sigma:.1f},scale={W}:{H}" + "".join("," + x for x in look) +
              f",format=rgba,{fades}[frz{k}]")
    fc.append(f"[fra{k}][frz{k}]overlay=enable='between(t,{s:.3f},{e:.3f})':eof_action=pass[fro{k}]")
    out = f"[fro{k}]"
    if win:
        cx, cy, cw, ch = win.get("crop", [0, 0.18, 1, 0.42])
        ww = float(win.get("width", 0.8))
        ow = int((ww * W if ww <= 1 else ww)) // 2 * 2
        r = int(win.get("radius", 40))
        fc.append(f"[frc{k}]crop=w=iw*{cw}:h=ih*{ch}:x=iw*{cx}:y=ih*{cy},scale={ow}:-2,format=rgba,{round_corners(r)},"
                  f"{fades}[frw{k}]")
        x, y = resolve_pos(win.get("pos", [0.5, 0.74]), W, H)
        fc.append(f"{out}[frw{k}]overlay=x={x}-w/2:y={y}-h/2:enable='between(t,{s:.3f},{e:.3f})':eof_action=pass[frx{k}]")
        out = f"[frx{k}]"
    return out


RING_COMPS = {"OrbitRing", "Portal", "OrbitCarousel"}


def resolve_stills(v, work: Path, width: int = 1080):
    """"frame:12.3" in any motion prop = a still of the edit (base.mp4) at 12.3 s: freeze-frame cards, newspaper photo,
    tear-away / blow-away transitions. Returns the props with those strings replaced by cached .jpg paths."""
    if isinstance(v, dict):
        return {k: resolve_stills(x, work, width) for k, x in v.items()}
    if isinstance(v, list):
        return [resolve_stills(x, work, width) for x in v]
    if isinstance(v, str) and v.startswith("frame:"):
        base = work / "base.mp4"
        t = float(v[6:])
        fp = work / "frames" / f"f_{t:.2f}_{base.stat().st_mtime_ns % 10**8}.jpg"
        if not fp.exists():
            fp.parent.mkdir(parents=True, exist_ok=True)
            run([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(base), "-frames:v", "1",
                 "-vf", f"scale={width // 2}:-2", "-q:v", "2", str(fp)])
        return str(fp)
    return v


def prepare_motion(plan: dict, starts: list[float], total: float, canvas: dict, work: Path, root: Path) -> None:
    """Render every "motion" overlay (Remotion, Blue pack) to a cached transparent .mov and turn it into a
    full-frame "video" overlay for the final pass."""
    ovs = plan.get("overlays", [])
    # ring comps get a back half drawn behind the speaker (needs the person matte) and a front half on top
    for i in range(len(ovs) - 1, -1, -1):
        o = ovs[i]
        if o.get("type") == "motion" and o.get("comp") in RING_COMPS and not o.get("props", {}).get("half"):
            back = json.loads(json.dumps(o))
            back["props"]["half"] = "back"
            back["behind"] = True
            o["props"]["half"] = "front"
            ovs.insert(i, back)
    items = [o for o in ovs if o.get("type") == "motion"]
    if not items:
        return
    for o in items:
        o["props"] = resolve_stills(o.get("props", {}), work, canvas["width"])
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "motion"))
    import render_motion  # noqa: E402
    from concurrent.futures import ThreadPoolExecutor
    for o in items:  # copy referenced images first, so one bundle has them all
        render_motion.stage(o.get("props", {}), root)
    bundle = render_motion.ensure_bundle()

    def one(o):
        s, e = overlay_times(o, starts, total)
        return render_motion.render(o["comp"], o.get("props", {}), max(0.2, e - s), canvas["width"], canvas["height"],
                                    int(canvas.get("fps", 30)), cache_dir=work / "motion", root=root, bundle=bundle)

    with ThreadPoolExecutor(max_workers=3) as ex:
        paths = list(ex.map(one, items))
    for o, p in zip(items, paths):
        o.update({"type": "video", "src": str(p), "pos": "center", "width": 1.0, "in": 0, "fade": 0, "_motion": o["comp"]})
        o.pop("loop", None)
        o.pop("key", None)
    print(f"[render] motion graphics: {len(items)} ready")


def final_pass(plan: dict, base: Path, starts: list[float], total: float, canvas: dict, work: Path, out: Path,
               vcodec: list[str], ass: Path | None, preview: tuple[float, float] | None):
    W, H = canvas["width"], canvas["height"]
    inputs = ["-i", str(base)]
    fc: list[str] = []
    n = 1
    # concat-joined segments can carry tiny timestamp steps at each join; overlays treat those as the end of
    # their stream and vanish, so give the base clean, continuous timestamps first
    fps_c = canvas.get("fps", 30)
    fc.append(f"[0:v]fps={fps_c},setpts=N/{fps_c}/TB[basev]")
    vlast = "[basev]"

    # image / video overlays (logos, stickers, picture-in-picture, green-screen effects)
    import vipfx
    cx = vipfx.Ctx(base, work, W, H, int(fps_c), starts, total, inputs, fc, n)
    cx.prepare(plan.get("overlays", []))
    for k, o in enumerate(plan.get("overlays", [])):
        if o.get("type") == "frost":
            vlast = frost_layer(o, k, vlast, fc, starts, total, W, H)
            continue
        if o.get("type") in vipfx.TYPES or (o.get("_motion") and (o.get("behind") or o.get("fill"))):
            cx.n = n
            vlast = vipfx.apply(o, k, vlast, cx) if o.get("type") in vipfx.TYPES else vipfx.motion_special(o, k, vlast, cx)
            n = cx.n
            continue
        if o.get("type") not in ("image", "video"):
            continue
        off = starts[int(o["clip"])] if "clip" in o else 0.0
        s = parse_time(o.get("start", 0)) + off
        e = parse_time(o["end"]) + off if o.get("end") is not None else (
            s + parse_time(o["duration"]) if "duration" in o else total)
        if o["type"] == "image":
            # looped still image at the canvas fps; a big thread queue stops many looped inputs from
            # stalling the demuxers (which froze the whole graph with 8+ cards)
            # one decoded frame held with tpad (looped image inputs are slow and can stall the graph)
            inputs += ["-i", str(o["src"])]
        else:
            if o.get("loop"):
                inputs += ["-stream_loop", "-1"]
            if str(o["src"]).lower().endswith(".webm"):
                # transparent stickers are VP9 with alpha: only libvpx decodes the alpha plane
                inputs += ["-c:v", "libvpx-vp9"]
            inputs += ["-ss", f"{parse_time(o.get('in', 0)):.3f}", "-t", f"{e - s:.3f}", "-i", str(o["src"])]
        wfrac = float(o.get("width", 0.25 if o["type"] == "image" else 0.4))
        ow = int(wfrac * W if wfrac <= 1 else wfrac) // 2 * 2
        chain = [f"scale={ow}:-2:flags=lanczos", "format=rgba"]
        if o["type"] == "image":
            chain += [f"tpad=stop_mode=clone:stop_duration={e + 0.5:.3f}", f"fps={canvas.get('fps', 30)}"]
        if o.get("key"):  # chroma / luma key, e.g. "#00FF00" green screen or "#000000" effects on black
            chain.append(f"colorkey={o['key'].replace('#', '0x')}:{o.get('similarity', 0.3)}:{o.get('blend', 0.1)}")
        if o.get("radius"):
            r = max(1, min(int(o["radius"]), ow // 2 - 1))  # px on the scaled overlay
            chain.append(f"geq=lum='p(X,Y)':a='if(gt(abs(W/2-X),W/2-{r})*gt(abs(H/2-Y),H/2-{r}),"
                         f"if(lte(hypot({r}-(W/2-abs(W/2-X)),{r}-(H/2-abs(H/2-Y))),{r}),255,0),255)*alpha(X,Y)/255'"
                         f":cb='cb(X,Y)':cr='cr(X,Y)'")
        if float(o.get("opacity", 1)) < 1:
            chain.append(f"colorchannelmixer=aa={float(o['opacity'])}")
        if o["type"] == "video":
            chain.append(f"setpts=PTS-STARTPTS+{s:.3f}/TB")
        fd = float(o.get("fade", 0.3))
        if fd:
            chain.append(f"fade=t=in:st={s:.3f}:d={fd}:alpha=1")
            if e < total:
                chain.append(f"fade=t=out:st={max(s, e - fd):.3f}:d={fd}:alpha=1")
        fc.append(f"[{n}:v]{','.join(chain)}[ov{k}]")
        x, y = resolve_pos(o.get("pos", "top-right"), W, H)
        anim = o.get("anim")
        if anim == "slide-up":  # rises ~6% of the canvas height with ease-out over 0.35 s
            dy = int(H * 0.06)
            yexpr = f"'{y}-h/2+if(lt(t-{s:.3f},0.35),{dy}*pow(1-(t-{s:.3f})/0.35,3),0)'"
        elif anim == "slide-down":  # drops ~8% of the canvas height into place
            dy = int(H * 0.08)
            yexpr = f"'{y}-h/2-if(lt(t-{s:.3f},0.35),{dy}*pow(1-(t-{s:.3f})/0.35,3),0)'"
        elif anim == "drop":  # falls in from above the frame with a small bounce (polaroids, Bee style)
            p = f"((t-{s:.3f})/0.45)"
            ease = f"(1+2.70158*pow({p}-1,3)+1.70158*pow({p}-1,2))"  # easeOutBack
            yexpr = f"'{y}-h/2-if(lt(t-{s:.3f},0.45),({y}+h)*(1-{ease}),0)'"
        else:
            yexpr = f"{y}-h/2"
        if anim == "slide-left":
            xexpr = f"'{x}-w/2+if(lt(t-{s:.3f},0.35),{int(W * 0.25)}*pow(1-(t-{s:.3f})/0.35,3),0)'"
        elif anim == "slide-right":
            xexpr = f"'{x}-w/2-if(lt(t-{s:.3f},0.35),{int(W * 0.25)}*pow(1-(t-{s:.3f})/0.35,3),0)'"
        else:
            xexpr = f"{x}-w/2"
        fc.append(f"{vlast}[ov{k}]overlay=x={xexpr}:y={yexpr}:eval=frame:enable='between(t,{s:.3f},{e:.3f})'"
                  f":eof_action=pass[vo{k}]")
        vlast = f"[vo{k}]"
        n += 1

    vchain = []
    if ass:
        vchain.append(f"ass=filename=overlay.ass:fontsdir=fonts")
    fi, fo = float(plan.get("fade_in", 0)), float(plan.get("fade_out", 0))
    if fi:
        vchain.append(f"fade=t=in:st=0:d={fi}")
    if fo:
        vchain.append(f"fade=t=out:st={max(0, total - fo):.3f}:d={fo}")
    vchain.append("format=yuv420p")
    fc.append(f"{vlast}{','.join(vchain)}[vout]")

    # ---- audio
    audio = plan.get("audio", {}) or {}
    voice = "[0:a]"
    vvol = float(audio.get("original_volume", 1))
    fc.append(f"[0:a]volume={vvol}[orig]")
    mixes = ["[orig]"]
    vos = audio.get("voiceover") or []
    for j, vo in enumerate(vos if isinstance(vos, list) else [vos]):
        # voiceover: a narration file, or a piece of another clip's audio laid over different visuals
        trim = f"atrim={parse_time(vo.get('in', 0)):.3f}" + (
            f":{parse_time(vo['out']):.3f}" if vo.get("out") is not None else "") + ",asetpts=PTS-STARTPTS,"
        inputs += ["-i", str(vo["src"])]
        d = int((parse_time(vo.get("start", 0)) + (starts[int(vo["clip"])] if "clip" in vo else 0)) * 1000)
        clean = (DENOISE.get(str(vo["denoise"]), DENOISE["medium"]) + "," if vo.get("denoise") else "") + \
                (VOICE_ENHANCE + "," if vo.get("voice") else "")
        fc.append(f"[{n}:a]{trim}aresample=48000,aformat=channel_layouts=stereo,{clean}volume={vo.get('volume', 1)},"
                  f"adelay={d}|{d}[vo{j}]")
        mixes.append(f"[vo{j}]")
        n += 1
    fc.append(f"{''.join(mixes)}amix=inputs={len(mixes)}:duration=first:normalize=0[speech]")
    voice = "[speech]"
    music = audio.get("music")
    if music:
        inputs += ["-stream_loop", "-1", "-ss", f"{parse_time(music.get('in', 0)):.3f}", "-i", str(music["src"])]
        ms = parse_time(music.get("start", 0))
        me = parse_time(music["end"]) if music.get("end") is not None else total
        mfi, mfo = float(music.get("fade_in", 0.5)), float(music.get("fade_out", 2.0))
        d = int(ms * 1000)
        fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{me - ms:.3f},"
                  f"volume={music.get('volume', 0.18)},afade=t=in:d={mfi},"
                  f"afade=t=out:st={max(0, me - ms - mfo):.3f}:d={mfo},adelay={d}|{d}[mus]")
        n += 1
        if music.get("duck", True):
            fc.append(f"{voice}asplit=2[sp1][sp2]")
            fc.append(f"[mus][sp2]sidechaincompress=threshold={music.get('duck_threshold', 0.02)}:"
                      f"ratio={music.get('duck_ratio', 6)}:attack=30:release=500[mduck]")
            fc.append("[sp1][mduck]amix=inputs=2:duration=first:normalize=0[amixed]")
        else:
            fc.append(f"{voice}[mus]amix=inputs=2:duration=first:normalize=0[amixed]")
        voice = "[amixed]"

    # sound effects (explicit list + automatic ones on transitions / overlay entrances)
    hits = sfx_events(plan, starts, total)
    if plan.get("sound_design"):
        # guard: the export once kept only 13 of 45 effect sounds while the editor played them all — say it loudly
        fxn = sum(1 for o in plan.get("overlays", []) or []
                  if (o.get("_motion") or o.get("comp")) not in (None, "BlueText") and "sfx" not in o)
        print(f"[render] tiếng hiệu ứng: {len(hits)} tiếng cho {fxn} hiệu ứng", flush=True)
        if fxn and len(hits) < fxn * 0.6:
            print("[render] CẢNH BÁO: số tiếng ít hơn hẳn số hiệu ứng — kiểm tra sound.design / sfx_events trước khi giao",
                  flush=True)
    if hits:
        labels = []
        for j, (path, at, vol, mx) in enumerate(hits):
            inputs += ["-i", str(path)]
            d = max(0, int(at * 1000))
            fd = min(0.5, mx / 3)
            fc.append(f"[{n}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{mx:.2f},"
                      f"afade=t=out:st={max(0, mx - fd):.2f}:d={fd:.2f},volume={vol},adelay={d}|{d}[sfx{j}]")
            labels.append(f"[sfx{j}]")
            n += 1
        fc.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0,"
                  f"volume={float((plan.get('auto_sfx') or {}).get('master', 1.0)) if isinstance(plan.get('auto_sfx'), dict) else 1.0},"
                  f"alimiter=limit={0.9 if plan.get('sound_design') else 0.5}:level=disabled[sfxall]")
        # sound effects duck under the voice (never cover words), then mix
        fc.append(f"{voice}asplit=2[vmix][vkey]")
        # creator-style mixes keep effects audible over speech: gentle ducking when a sound design is on
        dk = plan.get("sfx_duck") or ({"threshold": 0.06, "ratio": 2} if plan.get("sound_design") else {"threshold": 0.015, "ratio": 8})
        fc.append(f"[sfxall][vkey]sidechaincompress=threshold={dk.get('threshold', 0.06)}:ratio={dk.get('ratio', 2)}:"
                  f"attack=5:release=200:makeup=1[sfxduck]")
        fc.append("[vmix][sfxduck]amix=inputs=2:duration=first:normalize=0[withsfx]")
        voice = "[withsfx]"
    achain = []
    if fi:
        achain.append(f"afade=t=in:d={min(fi, 0.5)}")
    if fo:
        achain.append(f"afade=t=out:st={max(0, total - fo):.3f}:d={fo}")
    lufs = audio.get("normalize", -14)
    if lufs is not None and lufs is not False:
        achain.append(f"loudnorm=I={lufs}:TP=-1.5:LRA=11")
        # loudnorm alone can still overshoot after AAC encoding (seen +0.2 dBFS): hard-limit at -1.5 dBFS
        achain.append("alimiter=limit=0.84:attack=2:release=50:level=disabled")
    achain.append("aresample=48000")
    fc.append(f"{voice}{','.join(achain)}[aout]")

    script = work / "final.fc"
    script.write_text(";\n".join(fc), encoding="utf-8")
    trim = ["-t", f"{total:.3f}"]
    if preview:
        trim = ["-ss", f"{preview[0]:.3f}", "-to", f"{min(preview[1], total):.3f}"]
    out.parent.mkdir(parents=True, exist_ok=True)
    run([FFMPEG, "-y", *inputs, "-/filter_complex", "final.fc", "-map", "[vout]", "-map", "[aout]",
         *trim, *vcodec, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         str(out.resolve())], cwd=work)


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out")
    ap.add_argument("--aspect", help="override canvas aspect, e.g. 16:9 (for multi-format export)")
    ap.add_argument("--draft", action="store_true", help="fast low-quality encode for checking")
    ap.add_argument("--preview", help="only output a time range of the final timeline, e.g. 5-15")
    ap.add_argument("--work", help="work dir (default: <plan>_work)")
    ap.add_argument("--base-only", action="store_true",
                    help="stop after joining clips (writes <work>/base.mp4 + timeline.json for the VIP Editor)")
    a = ap.parse_args()

    t0 = time.time()
    plan_path = Path(a.plan).resolve()
    plan = theme.apply(load_json(plan_path))
    # Relative paths in the plan are relative to the plan file.
    root = plan_path.parent

    def absify(p):
        return str((root / p).resolve()) if p and not Path(p).is_absolute() else p

    for c in plan["clips"]:
        c["src"] = absify(c["src"])
    if plan.get("keep_timing"):
        keep_timing(plan["clips"])
    for o in plan.get("overlays", []):
        if "src" in o:
            o["src"] = absify(o["src"])
    au = plan.get("audio") or {}
    for k in ("music", "voiceover"):
        for item in (au.get(k) if isinstance(au.get(k), list) else [au.get(k)]):
            if item:
                item["src"] = absify(item["src"])
    tr = (plan.get("subtitles") or {}).get("transcript")
    if tr:
        plan["subtitles"]["transcript"] = [absify(t) for t in tr] if isinstance(tr, list) else absify(tr)

    cv = dict(plan.get("canvas", {}))
    aspect = a.aspect or cv.get("aspect")
    if aspect:
        cv["width"], cv["height"] = ASPECTS.get(aspect, (cv.get("width", 1080), cv.get("height", 1920)))
    if "width" not in cv:
        first = probe(plan["clips"][0]["src"])
        cv["width"], cv["height"] = first["width"] // 2 * 2, first["height"] // 2 * 2
    cv.setdefault("fps", 30)
    out = Path(a.out or absify(plan.get("output", plan_path.with_suffix(".mp4").name)))
    if a.aspect and not a.out:
        out = out.with_name(out.stem + "_" + a.aspect.replace(":", "x") + out.suffix)
    if a.draft and not a.out:
        out = out.with_name(out.stem + "_draft" + out.suffix)
    if a.preview and not a.out:
        out = out.with_name(out.stem + "_preview" + out.suffix)
    work = Path(a.work) if a.work else plan_path.with_name(plan_path.stem + "_work")
    work.mkdir(parents=True, exist_ok=True)

    nv = has_nvenc()
    seg_codec = video_codec_args("max" if not a.draft else "draft", nv)
    final_codec = video_codec_args("draft" if a.draft else plan.get("quality", "high"), nv)

    plan["clips"] = [{**plan.get("clip_defaults", {}), **c} for c in plan["clips"]]
    plan["_root"] = str(root)
    clips = plan["clips"]
    for i, c in enumerate(clips):
        make_segment(c, i, cv, work, seg_codec)
        print(f"[render] segment {i + 1}/{len(clips)} {Path(c['src']).name} {c['_dur']:.2f}s")
    base, starts, total = join_segments(clips, work, seg_codec, int(cv["fps"]))
    print(f"[render] timeline {total:.2f}s, clip starts: {[round(s, 2) for s in starts]}")
    # timeline manifest for the VIP Editor (editor/server.py): base.mp4 + where each clip landed
    save_json({"canvas": cv, "starts": starts, "total": total, "base": str(base), "aspect": aspect,
               "clips": [{"src": c["src"], "in": parse_time(c.get("in", 0)), "_out": c.get("_out"),
                          "_dur": c["_dur"], "speed": float(c.get("speed", 1))} for c in clips],
               "time": time.time()}, work / "timeline.json")
    if a.base_only:
        print(f"[render] base only -> {base}")
        return
    prepare_motion(plan, starts, total, cv, work, root)
    ass = build_ass(plan, cv["width"], cv["height"], clips, starts, total, work)
    preview = tuple(map(float, a.preview.split("-"))) if a.preview else None
    final_pass(plan, base, starts, total, cv, work, out, final_codec, ass, preview)
    info = probe(out)
    print(f"[render] done -> {out}  ({info['width']}x{info['height']}, {info['duration']:.2f}s, "
          f"{info['size_mb']}MB, {time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
