"""Blue VIP effects for render.py's final pass: person matte (rembg u2net) + layers that need it, and frame-level fx.

Overlay types handled here (all take start/end or clip + relative times like any overlay):
  {"type": "bg", "blur": 0, "scale": 1.0, "radius": 0, "color": "0x0E1A3A", "tint": "0x..@a", "src": "img/video"}
      changes only the BACKGROUND, the speaker stays sharp on top (rembg matte):
      blur 30 = portrait bokeh · scale 0.86 + radius 40 = "tách lớp bung ra" (room shrinks into a card) ·
      src = replace the room with an image/video ("video làm phông nền")
  {"type": "popout", "bg": "0xEEF1F8", "window": {"crop": [x,y,w,h], "pos": [x,y], "width": 0.84, "radius": 44}, "head": [0.5, 0.42]}
      the speaker inside a rounded window whose head/hands break out over the window edge ("người tràn vào khung")
  {"type": "lens", "at": [0.5, 0.33], "pos": [0.62, 0.36], "size": 0.42, "zoom": 1.9}    magnifying glass
  {"type": "fx", "effect": "vhs" | "film" | "bw" | "warm" | "cool", "compare": {"from": 0.0, "to": 1.0}}
      frame look for the range; "compare" shows it only left of a moving split line (before/after slider)
TREND pack (11/2026):
  {"type": "spotlight", "at": [0.5, 0.33], "dim": 0.55, "color": "0xFFF1D6", "beam": true}
      the room goes dark, a warm light pool (and a beam from above) behind the speaker, who stays lit
  {"type": "freeze", "at": 12.3, "name": "...", "role": "...", "style": "dark" | "bw" | "theme", "zoom": 1.07, "stroke": 14}
      character intro: the frame freezes (white flash), the room darkens, the speaker becomes a white-outlined sticker
      that slowly pushes in; "name"/"role" add a NameTag motion card (render.py). Video only, the audio keeps running,
      so use it on a pause, a voice-over or the hook before the first word.
  {"type": "whip", ...}  added by render.py for a clip "transition": "whip" (or {"type":"whip","dir":"right","duration":0.36}):
      a hard cut becomes a whip pan, the frame slides out with heavy horizontal motion blur and the next one slides in
  {"type": "loopback", "duration": 0.5}   the last half second cross-fades into the opening frames: a seamless replay loop
  {"type": "neon", "color": "#FF3FD8", "cycle": true}          glowing neon tube traced around the speaker
  {"type": "clone", "copies": [{"dx": -0.3, "scale": 0.82, "flip": true}, ...]}   copies of the speaker beside them
  {"type": "dolly", "zoom": 1.35}       vertigo: the room pushes in behind a speaker who stays the same size
  {"type": "facecam", "pos": [0.78, 0.8], "size": 0.34, "face": [0.5, 0.33], "zoom": 2.2, "from": 12.0}   round face bubble
  {"type": "spinwhip", "dir": "left"}  rotating whip (render.py adds it for clip "transition": "spinwhip"): 1 soft frame
      before the cut, 3 frames of heavy rotational + sideways blur, the new shot lands tilted and settles in 4 frames
      (measured frame by frame from top real-estate tour editors). Built in Python from the base file.
  {"type": "zoomblur"}  radial zoom-through (render.py adds it for clip "transition": "zoomblur"): 5 frames rushing into
      the frame centre with radial blur, the new shot opens out of the blur and settles in 6 frames (measured)
  {"type": "tumble", "dir": "left"}  3D flip: the shot turns away on its vertical axis with motion blur, the next one
      turns in (3 + 4 frames, measured)
  {"type": "glitch"} / {"type": "leak"} / {"type": "zoomthru"}  short transition looks (render.py adds them for clip
      "transition": "glitch" | "leak" | "zoomthru"); usable as plain layers too
  {"type": "impact", "at": [0.5, 0.33]}  anime impact frame: ink black-and-white, flashing negative, speed lines, shake
  {"type": "dramatic", "at": [0.5, 0.32], "zoom": 1.7}  meme snap zoom on the face + red vignette + shake
  {"type": "colorize", "mode": "fade" | "wipe", "hold": 0.4}   old black-and-white turning into colour
STUDIO LOOK:
  {"type": "relight", "preset": "bright_luxe" | "warm_cafe" | "cine_dark" | "soft_window", "side": "left", "lamps": [[x, y]]}
      fake lighting: key light on one side of the face, rim light, room graded darker/warmer, practical lamp glows, bloom
  {"type": "prop", "src": "plant" | "plant_tall" | "lamp" | "shelf" | "vase" | "x.png", "pos": [0.14, 0.9], "width": 0.36}
      decor placed in the room BEHIND the speaker (bottom-centre anchor), colour-matched, soft contact shadow; lamp glows
Motion overlays (Remotion) get two extra flags here:
  "behind": true   drawn between the room and the speaker (text behind the head, orbit ring back half, code wall)
  "fill": "video"  the comp's alpha becomes a window onto the (zoomed) video ("chữ chứa video"); frame darkens behind
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import theme  # noqa: E402
from common import FFMPEG, parse_time  # noqa: E402

TYPES = {"bg", "popout", "lens", "fx", "outline", "spotlight", "freeze", "whip", "loopback",
         "neon", "clone", "dolly", "facecam", "glitch", "leak", "zoomthru", "spinwhip", "zoomblur", "tumble", "impact", "dramatic", "colorize", "relight", "prop"}
MATTE_TYPES = ("bg", "popout", "outline", "spotlight", "neon", "clone", "dolly", "relight", "prop")
PROPS_DIR = Path(__file__).resolve().parent.parent / "assets" / "props"
MATTE_VERSION = 4
MATTE_MODEL = "u2net"  # tested 20/11: cleaner than u2net_human_seg (which grabbed a wall logo) and more solid than isnet


_SESS: dict = {}


def rembg_session(name: str = "u2net"):
    """rembg session on the GPU when there is one (CUDA, else DirectML on Windows), cached per model.
    rembg's default picks the CPU even when onnxruntime-directml is installed: 0.41 s vs 0.03 s per frame (RTX 3060)."""
    if name not in _SESS:
        import onnxruntime as ort
        from rembg import new_session
        have = ort.get_available_providers()
        prov = [p for p in ("CUDAExecutionProvider", "DmlExecutionProvider") if p in have] + ["CPUExecutionProvider"]
        try:
            _SESS[name] = new_session(name, providers=prov)
        except Exception:
            _SESS[name] = new_session(name)
    return _SESS[name]


def times(o: dict, starts: list[float], total: float) -> tuple[float, float]:
    off = starts[int(o["clip"])] if "clip" in o else 0.0
    s = parse_time(o.get("start", 0)) + off
    e = parse_time(o["end"]) + off if o.get("end") is not None else (
        s + parse_time(o["duration"]) if "duration" in o else total)
    return s, min(e, total)


def make_matte(base: Path, s: float, e: float, W: int, H: int, fps: int, work: Path) -> Path:
    """Grey person matte (white = speaker) for base.mp4[s, e], cached. rembg u2net, 1/3 size."""
    key = hashlib.md5(f"{base.stat().st_mtime_ns}|{s:.3f}|{e:.3f}|{W}x{H}|{MATTE_VERSION}".encode()).hexdigest()[:12]
    out = work / "matte" / f"m_{key}.mp4"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    w, h = W // 3 // 2 * 2, H // 3 // 2 * 2
    reader = subprocess.Popen([FFMPEG, "-v", "error", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", str(base),
                               "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                              stdout=subprocess.PIPE)
    tmp = out.with_suffix(".tmp.mp4")
    writer = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}",
                               "-r", str(fps), "-i", "-", "-c:v", "libx264", "-crf", "8", "-preset", "fast",
                               "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    from PIL import Image
    sess = rembg_session(MATTE_MODEL)
    prev = None
    n = 0
    while True:
        buf = reader.stdout.read(w * h * 3)
        if len(buf) < w * h * 3:
            break
        img = Image.fromarray(np.frombuffer(buf, np.uint8).reshape(h, w, 3))
        m = np.asarray(sess.predict(img)[0].resize((w, h), Image.BILINEAR), np.float32) / 255.0
        m = np.clip((m - 0.2) / 0.55, 0, 1)  # firm edges
        m = keep_main_blob(m)  # drop stray objects the model mistakes for a person (wall logos, posters)
        if prev is not None:
            m = 0.65 * m + 0.35 * prev  # calm hair flicker
        prev = m
        writer.stdin.write((m * 255).astype(np.uint8).tobytes())
        n += 1
    writer.stdin.close()
    writer.wait()
    reader.wait()
    tmp.replace(out)
    print(f"[render] person matte {s:.2f}-{e:.2f}s: {n} frames")
    return out


def keep_main_blob(m: np.ndarray) -> np.ndarray:
    """Keep only the biggest connected region of the matte (the speaker), softly."""
    try:
        import cv2
    except ImportError:
        return m
    b = (m > 0.4).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(b, 8)
    if n <= 2:
        return m
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    keep = (lab == big).astype(np.uint8)
    keep = cv2.dilate(keep, np.ones((9, 9), np.uint8))
    keep = cv2.GaussianBlur(keep.astype(np.float32), (9, 9), 0)
    return m * keep


class Ctx:
    def __init__(self, base: Path, work: Path, W: int, H: int, fps: int, starts: list[float], total: float,
                 inputs: list[str], fc: list[str], n: int):
        self.base, self.work, self.W, self.H, self.fps = base, work, W, H, fps
        self.starts, self.total, self.inputs, self.fc, self.n = starts, total, inputs, fc, n

    def add_input(self, args: list[str]) -> int:
        self.inputs += args
        self.n += 1
        return self.n - 1

    spans: list | None = None

    def prepare(self, overlays: list) -> None:
        """Merge the time ranges of every layer that needs the person matte, so overlapping effects
        (e.g. portrait blur + text behind the head on the same sentence) share one matte pass."""
        rs = []
        for o in overlays or []:
            if o.get("type") in MATTE_TYPES and not (o.get("type") == "prop" and o.get("behind") is False) or (o.get("type") == "motion" and (o.get("behind") or o.get("fill"))):
                try:
                    rs.append(times(o, self.starts, self.total))
                except Exception:
                    pass
        rs.sort()
        merged = []
        for a, b in rs:
            if merged and a <= merged[-1][1] + 1.0:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        self.spans = merged

    def matte_in(self, s: float, e: float, k: int, tag: str = "") -> str:
        """Label of a full-size grey matte stream for [s, e], timed on the timeline."""
        s0, e0 = s, e
        for a, b in self.spans or []:
            if a <= s + 1e-3 and b >= e - 1e-3:
                s0, e0 = a, b
                break
        p = make_matte(self.base, s0, e0, self.W, self.H, self.fps, self.work)
        i = self.add_input(["-i", str(p)])
        lab = f"[mt{k}{tag}]"
        self.fc.append(f"[{i}:v]scale={self.W}:{self.H}:flags=bicubic,format=gray,gblur=sigma=1.2,"
                       f"trim=start={s - s0:.3f},setpts=PTS-STARTPTS+{s:.3f}/TB{lab}")
        return lab

    def cut(self, src: str, s: float, e: float, lab: str) -> str:
        self.fc.append(f"{src}trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS+{s:.3f}/TB{lab}")
        return lab


def _fades(s: float, e: float, total: float, fd: float) -> str:
    if fd <= 0:
        return "null"
    return f"fade=t=in:st={s:.3f}:d={fd}:alpha=1" + (f",fade=t=out:st={max(s, e - fd):.3f}:d={fd}:alpha=1" if e < total - 0.01 else "")


def _over(cx: Ctx, vlast: str, top: str, s: float, e: float, k: int, tag: str, x="0", y="0") -> str:
    out = f"[vx{k}{tag}]"
    cx.fc.append(f"{vlast}{top}overlay=x={x}:y={y}:enable='between(t,{s:.3f},{e:.3f})':eof_action=pass{out}")
    return out


def round_mask(r: int) -> str:
    return (f"geq=lum='p(X,Y)':a='if(gt(abs(W/2-X),W/2-{r})*gt(abs(H/2-Y),H/2-{r}),"
            f"if(lte(hypot({r}-(W/2-abs(W/2-X)),{r}-(H/2-abs(H/2-Y))),{r}),255,0),255)*alpha(X,Y)/255':cb='cb(X,Y)':cr='cr(X,Y)'")


def person_layer(cx: Ctx, clean: str, s: float, e: float, k: int, choke: float = 0) -> str:
    """RGBA stream of just the speaker (from `clean`) for [s, e]. choke = pull the matte edge in by ~n px and soften it
    (kills the bright rim of un-blurred wall around the hair when the room behind is blurred / darkened)."""
    c = cx.cut(clean, s, e, f"[pc{k}]")
    m = cx.matte_in(s, e, k)
    if choke > 0:
        n = max(1, min(8, int(round(choke))))
        cx.fc.append(f"{m}format=gray,{','.join(['erosion'] * n)},gblur=sigma={max(0.8, n * 0.5):.1f}[mk{k}]")
        m = f"[mk{k}]"
    cx.fc.append(f"{c}{m}alphamerge[pp{k}]")
    return f"[pp{k}]"


def outline(o: dict, k: int, vlast: str, cx: Ctx, s: float, e: float, fd: float) -> str:
    """Hand-drawn line around the speaker (doodle outline): a band just outside the person matte, coloured, with a
    'boiling' jitter every 3 frames.  {"type": "outline", "color": "#FFFFFF", "width": 9, "gap": 16, "boil": 3}"""
    W, H, fc = cx.W, cx.H, cx.fc
    gap, wid = float(o.get("gap", 16)), float(o.get("width", 9))
    col = theme.tint(str(o.get("color", "#FFFFFF")).replace("#", "0x"))
    b = float(o.get("boil", 3))
    m = cx.matte_in(s, e, k)
    q = 4  # work at 1/4 size: dilation by blur + threshold
    fc.append(f"{m}scale={W // q}:{H // q},format=gray,split=2[oa{k}][ob{k}]")
    fc.append(f"[oa{k}]gblur=sigma={gap / q:.2f},lut=y='if(gt(val,24),255,0)'[oi{k}]")
    fc.append(f"[ob{k}]gblur=sigma={(gap + wid) / q:.2f},lut=y='if(gt(val,10),255,0)'[oo{k}]")
    fc.append(f"[oo{k}][oi{k}]blend=all_mode=difference,scale={W}:{H}:flags=bicubic,gblur=sigma=1.2,format=gray[ol{k}]")
    fc.append(f"color=c={col}:s={W}x{H}:r={cx.fps},trim=duration={e - s + 0.2:.3f},setpts=PTS-STARTPTS+{s:.3f}/TB,"
              f"format=rgba[oc{k}]")
    fc.append(f"[oc{k}][ol{k}]alphamerge,{_fades(s, e, cx.total, fd)}[ox{k}]")
    fc.append(f"{vlast}[ox{k}]overlay=x='{b}*sin(floor(n/3)*2.1)':y='{b}*cos(floor(n/3)*1.7)':"
              f"enable='between(t,{s:.3f},{e:.3f})'[vo{k}]")
    return f"[vo{k}]"


def _png_input(cx: Ctx, png: Path, dur: float, s: float, lab: str, fmt: str = "rgba") -> str:
    """A still held for dur seconds from s: decoded ONCE and cloned (a looped image input re-decodes every frame)."""
    i = cx.add_input(["-i", str(png)])
    cx.fc.append(f"[{i}:v]format={fmt},tpad=stop_mode=clone:stop_duration={dur + 0.2:.3f},fps={cx.fps},"
                 f"setpts=PTS-STARTPTS+{s:.3f}/TB{lab}")
    return lab


def spotlight_png(cx: Ctx, o: dict) -> Path:
    """Light pool (soft ellipse behind the head) + optional beam from the top, as one RGBA overlay."""
    from PIL import Image, ImageDraw, ImageFilter
    ax, ay = o.get("at", [0.5, 0.33])
    col = str(theme.tint(o.get("color", "0xFFF1D6"))).replace("0x", "")[:6]
    a = float(o.get("light", 0.55))
    key = hashlib.md5(f"{cx.W}x{cx.H}|{ax}|{ay}|{col}|{a}|{o.get('beam', True)}".encode()).hexdigest()[:10]
    out = cx.work / "fx" / f"spot_{key}.png"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    W, H, q = cx.W, cx.H, 4
    w, h = W // q, H // q
    rgb = tuple(int(col[i:i + 2], 16) for i in (0, 2, 4))
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    rx, ry = 0.46 * w, 0.24 * h
    d.ellipse([ax * w - rx, ay * h - ry * 0.7, ax * w + rx, ay * h + ry * 1.3], fill=int(255 * a))
    if o.get("beam", True):
        bw0, bw1 = 0.12 * w, 0.42 * w
        d.polygon([(ax * w - bw0, 0), (ax * w + bw0, 0), (ax * w + bw1, ay * h + ry), (ax * w - bw1, ay * h + ry)],
                  fill=int(255 * a * 0.55))
    m = m.filter(ImageFilter.GaussianBlur(w * 0.07)).resize((W, H), Image.BICUBIC)
    img = Image.new("RGBA", (W, H), rgb + (0,))
    img.putalpha(m)
    img.save(out)
    return out


def freeze_pngs(cx: Ctx, o: dict, at: float) -> tuple[Path, Path]:
    """(plain frame, styled frame) for the character intro: darkened room + white-outlined speaker sticker."""
    from PIL import Image, ImageFilter
    import cv2
    style = o.get("style", "dark")
    stroke = int(o.get("stroke", 14))
    key = hashlib.md5(f"{cx.base.stat().st_mtime_ns}|{at:.3f}|{style}|{stroke}|{theme.tint('0x0E1A3A')}|{cx.W}x{cx.H}".encode()).hexdigest()[:10]
    d = cx.work / "fx"
    plain, styled = d / f"frz_{key}_a.png", d / f"frz_{key}_b.png"
    if plain.exists() and styled.exists():
        return plain, styled
    d.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{at:.3f}", "-i", str(cx.base), "-frames:v", "1",
                    "-vf", f"scale={cx.W}:{cx.H}", str(plain)], check=True)
    fr = Image.open(plain).convert("RGB")
    # one still, so afford two models: u2net (solid body) + u2net_human_seg (keeps spread arms and hands), main blob only
    ms = [np.asarray(rembg_session(n).predict(fr)[0].resize(fr.size, Image.BILINEAR), np.float32) / 255.0
          for n in (MATTE_MODEL, "u2net_human_seg")]
    m = keep_main_blob(np.clip((np.maximum(*ms) - 0.2) / 0.55, 0, 1))
    # room: darker / black-and-white / brand tint, a little blur
    arr = np.asarray(fr.filter(ImageFilter.GaussianBlur(5)), np.float32)
    if style == "bw":
        arr = np.repeat(arr.mean(axis=2, keepdims=True), 3, axis=2) * 0.55
    else:
        arr = arr * 0.42
        if style == "theme":
            dark = str(theme.tint("0x0E1A3A")).replace("0x", "")[:6]
            tc = np.array([int(dark[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
            arr = arr * 0.55 + tc * 0.45
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    # sticker: white stroke (dilated matte) + soft drop shadow, then the speaker
    mb = (m > 0.45).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * stroke + 1, 2 * stroke + 1))
    ring = cv2.GaussianBlur(cv2.dilate(mb, k).astype(np.float32), (5, 5), 0)
    sh = cv2.GaussianBlur(ring, (0, 0), stroke * 1.6)
    shadow = Image.new("RGBA", fr.size, (0, 0, 0, 0))
    shadow.putalpha(Image.fromarray((sh * 150).astype(np.uint8)))
    out.alpha_composite(shadow, (stroke // 2, stroke))
    white = Image.new("RGBA", fr.size, (255, 255, 255, 0))
    white.putalpha(Image.fromarray((ring * 255).astype(np.uint8)))
    out.alpha_composite(white)
    person = fr.convert("RGBA")
    person.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
    out.alpha_composite(person)
    out.convert("RGB").save(styled)
    return plain, styled


# ------------------------------------------------------------------ TREND pack 2 + STUDIO LOOK helpers
def _band(cx: Ctx, m: str, k: str, gap: float, wid: float) -> str:
    """Grey band just outside the person matte (gap px away, wid px wide), full size."""
    W, H, fc, q = cx.W, cx.H, cx.fc, 4
    fc.append(f"{m}scale={W // q}:{H // q},format=gray,split=2[ba{k}][bb{k}]")
    fc.append(f"[ba{k}]gblur=sigma={max(0.5, gap / q):.2f},lut=y='if(gt(val,24),255,0)'[bi{k}]")
    fc.append(f"[bb{k}]gblur=sigma={(gap + wid) / q:.2f},lut=y='if(gt(val,10),255,0)'[bo{k}]")
    fc.append(f"[bo{k}][bi{k}]blend=all_mode=difference,scale={W}:{H}:flags=bicubic,gblur=sigma=1.2,format=gray[bn{k}]")
    return f"[bn{k}]"


def _hex(c, default="FFFFFF") -> str:
    return str(theme.tint(str(c or default).replace("#", "0x"))).replace("0x", "").replace("#", "")[:6]


def _color(cx: Ctx, col: str, s: float, e: float, lab: str, fmt: str = "rgba") -> str:
    cx.fc.append(f"color=c=0x{col}:s={cx.W}x{cx.H}:r={cx.fps},trim=duration={e - s + 0.2:.3f},"
                 f"setpts=PTS-STARTPTS+{s:.3f}/TB,format={fmt}{lab}")
    return lab


def spinwhip_clip(cx: Ctx, at: float, s: float, e: float, sg: int = 1, amount: float = 1.0, kind: str = "spinwhip"):
    """Frames [s, e) of the base file with a measured transition baked in (spinwhip | zoomblur | tumble), as a short
    cached MP4 (full frame). Finds the REAL cut in the base file first (segments are frame-rounded, so a late clip can
    start 1–3 frames off its planned time) and returns (mp4, shift_seconds) so the layer lands on it."""
    import cv2
    import json as _json
    key = hashlib.md5(json_dumps([kind, 4, str(cx.base), os.path.getmtime(cx.base), at, s, e, sg, amount, cx.W, cx.H]).encode()).hexdigest()[:10]
    d = cx.work / "fx"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{kind}_{key}.mp4"
    meta = out.with_suffix(".json")
    if out.exists() and meta.exists():
        return out, float(_json.loads(meta.read_text())["shift"])
    W, H, fps = cx.W, cx.H, cx.fps
    n = max(1, int(round((e - s) * fps)))
    pad = 4
    s_ext = max(0.0, s - pad / fps)
    lead = int(round((s - s_ext) * fps))
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{s_ext:.4f}", "-i", str(cx.base), "-frames:v", str(n + lead + pad),
                          "-vf", f"fps={fps},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True, check=True).stdout
    ext = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    small = [cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), (90, 160)).astype(np.float32) for f in ext]
    diff = [0.0] + [float(np.abs(small[i] - small[i - 1]).mean()) for i in range(1, len(small))]
    exp = int(round((at - s_ext) * fps))
    win = [i for i in range(max(1, exp - 3), min(len(diff), exp + 4))]
    cut = exp
    if win:
        best = max(win, key=lambda i: diff[i])
        if diff[best] > 2.5 * (float(np.median(diff[1:])) + 1e-3):
            cut = best
    shift = cut - exp
    st = max(0, min(len(ext) - n, lead + shift))
    fr = ext[st:st + n].astype(np.float32)
    at = s_ext + cut / fps          # the real cut, in timeline seconds
    s = s_ext + st / fps            # first output frame
    meta.write_text(_json.dumps({"shift": (st - lead) / fps}))

    def rz(img, sc, deg, dx=0.0):
        M = cv2.getRotationMatrix2D((W / 2, H / 2), deg, sc)
        M[0, 2] += dx
        return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    a = amount

    def radial(img, z0, z1, n=9):  # zoom blur: average of the frame scaled between z0 and z1 about the centre
        return np.mean([rz(img, z, 0.0) for z in np.linspace(z0, z1, n)], axis=0)

    def turn(img, deg):  # perspective turn on the vertical axis (positive = right edge goes away)
        f_ = W * 1.4
        th = np.radians(deg)
        pts = []
        for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
            X, Z = (x - W / 2) * np.cos(th), (x - W / 2) * np.sin(th)
            sc = f_ / (f_ + Z)
            pts.append([W / 2 + X * sc, H / 2 + (y - H / 2) * sc])
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [W, 0], [W, H], [0, H]]), np.float32(pts))
        return cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(8, 8, 10))

    res = []
    for j, img in enumerate(fr):
        k = int(round((s + j / fps - at) * fps))  # frame index relative to the cut
        if kind == "zoomblur":  # 5 frames in (ease-in, zoom to ~2.2x), 6 frames out from ~1.8x (ease-out)
            if k < 0:
                p0, p1 = ((k + 5) / 5) ** 2, ((k + 6) / 5) ** 2
                img = radial(img, 1 + 1.2 * a * p0, 1 + 1.2 * a * p1)
            else:
                q0, q1 = (1 - k / 6) ** 3, (1 - (k + 1) / 6) ** 3
                img = radial(img, 1 + 0.8 * a * q0, 1 + 0.8 * a * max(0, q1))
            res.append(np.clip(img, 0, 255).astype(np.uint8))
            continue
        if kind == "tumble":  # 3 frames turning away to 70 deg, 4 frames turning in from -70 deg, blur between angles
            if k < 0:
                a0, a1 = 70 * a * ((k + 3) / 3) ** 2, 70 * a * ((k + 4) / 3) ** 2
            else:
                a0, a1 = -70 * a * (1 - k / 4) ** 2, -70 * a * max(0, 1 - (k + 1) / 4) ** 2
            img = np.mean([turn(img, sg * dd) for dd in np.linspace(a0, a1, 5)], axis=0)
            res.append(np.clip(img, 0, 255).astype(np.uint8))
            continue
        if k <= -1:   # outgoing shot starts to turn: light rotational smear
            img = np.mean([rz(img, 1.0, sg * dd * a) for dd in np.linspace(0, 6, 5)], axis=0)
        elif k <= 2:  # 3 frames of heavy spin + sideways travel
            b = [-32, -20, -11][k] * sg * a
            img = np.mean([rz(img, 1.10, b + dd * a, dx=sg * (-140 + 70 * k) * W / 1080) for dd in np.linspace(-14, 14, 9)], axis=0)
        elif k <= 6:  # lands tilted, settles with ease-out
            p = 1 - (1 - (k - 2) / 4) ** 3
            sp = 2 * (1 - p) * a
            img = np.mean([rz(img, 1.10 - 0.08 * p, -6 * sg * a * (1 - p) + dd) for dd in np.linspace(-sp, sp, 3)], axis=0)
        res.append(np.clip(img, 0, 255).astype(np.uint8))
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps),
                          "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", str(out)],
                         stdin=subprocess.PIPE)
    for im in res:
        p.stdin.write(im.tobytes())
    p.stdin.close()
    p.wait()
    return out, (st - lead) / fps


def _cache_png(cx: Ctx, tag: str, parts) -> Path:
    key = hashlib.md5(json_dumps([tag, parts, cx.W, cx.H]).encode()).hexdigest()[:10]
    d = cx.work / "fx"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{tag}_{key}.png"


def json_dumps(v) -> str:
    import json
    return json.dumps(v, sort_keys=True, default=str)


def grab_frame(cx: Ctx, t: float) -> "Image":
    from PIL import Image
    fp = _cache_png(cx, "grab", [str(cx.base), cx.base.stat().st_mtime_ns, round(t, 3)])
    if not fp.exists():
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(cx.base), "-frames:v", "1",
                        "-vf", f"scale={cx.W}:{cx.H}", str(fp)], check=True)
    return Image.open(fp).convert("RGB")


def still_matte(img, models=(MATTE_MODEL, "u2net_human_seg")) -> np.ndarray:
    from PIL import Image
    ms = [np.asarray(rembg_session(n).predict(img)[0].resize(img.size, Image.BILINEAR), np.float32) / 255.0 for n in models]
    return keep_main_blob(np.clip((np.maximum.reduce(ms) - 0.2) / 0.55, 0, 1))


_BOX: dict = {}


def person_box(cx: Ctx, t: float) -> tuple[float, float, float]:
    """(centre x, top y, bottom y) of the speaker at time t, as frame fractions."""
    k = (str(cx.base), round(t, 2))
    if k not in _BOX:
        m = still_matte(grab_frame(cx, t)) > 0.5
        ys, xs = np.nonzero(m)
        _BOX[k] = (float(xs.mean() / m.shape[1]), float(ys.min() / m.shape[0]), float(ys.max() / m.shape[0])) if len(xs) else (0.5, 0.2, 1.0)
    return _BOX[k]


def face_center(cx: Ctx, t: float) -> tuple[float, float, float]:
    """(x, y, face height) of the biggest face at time t (YuNet, as in face_beauty.py); falls back to the matte."""
    try:
        import cv2
        import face_beauty
        img = np.asarray(grab_frame(cx, t))[..., ::-1]
        h, w = img.shape[:2]
        sc = 640 / max(w, h)
        small = cv2.resize(img, (int(w * sc), int(h * sc)))
        det = cv2.FaceDetectorYN.create(str(face_beauty.model_path()), "", (small.shape[1], small.shape[0]), 0.6, 0.3, 50)
        _, faces = det.detect(small)
        if faces is not None and len(faces):
            f = max(faces, key=lambda r: r[2] * r[3])
            return float((f[0] + f[2] / 2) / small.shape[1]), float((f[1] + f[3] / 2) / small.shape[0]), float(f[3] / small.shape[0])
    except Exception as e:  # never fail a render on face detection
        print(f"[render] face detect skipped: {e}")
    x, top, bot = person_box(cx, t)
    return x, top + (bot - top) * 0.12, 0.1


def clean_plate(cx: Ctx, t: float) -> Path:
    """The room without the speaker at time t (person area inpainted), for dolly zoom."""
    import cv2
    from PIL import Image
    out = _cache_png(cx, "plate", [str(cx.base), cx.base.stat().st_mtime_ns, round(t, 3)])
    if out.exists():
        return out
    img = grab_frame(cx, t)
    m = still_matte(img)
    a = np.asarray(img)
    h, w = a.shape[:2]
    small = cv2.resize(a, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    mk = cv2.resize((m > 0.3).astype(np.uint8) * 255, (w // 2, h // 2))
    mk = cv2.dilate(mk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
    fill = cv2.inpaint(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), mk, 9, cv2.INPAINT_TELEA)
    fill = cv2.GaussianBlur(cv2.cvtColor(fill, cv2.COLOR_BGR2RGB), (0, 0), 6)
    fill = cv2.resize(fill, (w, h), interpolation=cv2.INTER_CUBIC)
    mm = cv2.GaussianBlur(cv2.resize(mk, (w, h)).astype(np.float32) / 255, (0, 0), 8)[..., None]
    Image.fromarray((a * (1 - mm) + fill * mm).astype(np.uint8)).save(out)
    return out


def speedlines_png(cx: Ctx, ax: float, ay: float, ink=(0, 0, 0)) -> Path:
    from PIL import Image, ImageDraw
    out = _cache_png(cx, "lines", [ax, ay, ink])
    if out.exists():
        return out
    import random
    rnd = random.Random(7)
    W, H = cx.W, cx.H
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cxp, cyp, R = ax * W, ay * H, 2.2 * max(W, H)
    import math
    for i in range(150):
        a = rnd.random() * math.tau
        r0 = (0.28 + rnd.random() * 0.25) * W
        wdt = 0.004 + rnd.random() * 0.012
        p = [(cxp + math.cos(a) * r0, cyp + math.sin(a) * r0),
             (cxp + math.cos(a - wdt) * R, cyp + math.sin(a - wdt) * R),
             (cxp + math.cos(a + wdt) * R, cyp + math.sin(a + wdt) * R)]
        d.polygon(p, fill=ink + (235,))
    img.save(out)
    return out


def vignette_png(cx: Ctx, col: str, strength: float) -> Path:
    from PIL import Image
    out = _cache_png(cx, "vig", [col, strength])
    if out.exists():
        return out
    W, H = cx.W // 4, cx.H // 4
    y, x = np.mgrid[0:H, 0:W]
    dd = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    a = np.clip((dd - 0.45) / 0.75, 0, 1) ** 1.6 * 255 * strength
    rgb = [int(col[i:i + 2], 16) for i in (0, 2, 4)]
    img = Image.new("RGBA", (W, H), tuple(rgb) + (0,))
    img.putalpha(Image.fromarray(a.astype(np.uint8)))
    img.resize((cx.W, cx.H), Image.BICUBIC).save(out)
    return out


def leak_png(cx: Ctx, kind: str) -> Path:
    """Film light leak: a few big soft warm blobs on transparent, 1.6x frame width."""
    from PIL import Image, ImageDraw, ImageFilter
    out = _cache_png(cx, "leak", [kind])
    if out.exists():
        return out
    W, H = int(cx.W * 1.6) // 4, cx.H // 4
    pal = {"warm": [(255, 120, 30), (255, 190, 80), (255, 60, 40)], "cool": [(80, 160, 255), (190, 120, 255), (120, 230, 255)],
           "gold": [(255, 200, 90), (255, 150, 40), (255, 230, 160)]}.get(kind, [(255, 120, 30), (255, 190, 80), (255, 60, 40)])
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for (fx, fy, fr), c in zip([(0.3, 0.35, 0.36), (0.55, 0.62, 0.42), (0.78, 0.3, 0.3)], pal):
        lay = Image.new("RGBA", (W, H), c + (0,))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).ellipse([fx * W - fr * W, fy * H - fr * H * 0.8, fx * W + fr * W, fy * H + fr * H * 0.8], fill=210)
        lay.putalpha(m.filter(ImageFilter.GaussianBlur(W * 0.07)))
        img.alpha_composite(lay)
    img.resize((int(cx.W * 1.6), cx.H), Image.BICUBIC).save(out)
    return out


def lamps_png(cx: Ctx, lamps, col: str, a: float) -> Path:
    """Practical lights in the room: warm glow spots with a soft halo (bokeh), full frame."""
    from PIL import Image, ImageDraw, ImageFilter
    out = _cache_png(cx, "lamps", [lamps, col, a])
    if out.exists():
        return out
    W, H = cx.W // 4, cx.H // 4
    rgb = tuple(int(col[i:i + 2], 16) for i in (0, 2, 4))
    halo = Image.new("L", (W, H), 0)
    core = Image.new("L", (W, H), 0)
    dh, dc = ImageDraw.Draw(halo), ImageDraw.Draw(core)
    for lx, ly, *rr in lamps:
        rad = (rr[0] if rr else 0.16) * W
        dh.ellipse([lx * W - rad, ly * H - rad, lx * W + rad, ly * H + rad], fill=int(255 * a))
        dc.ellipse([lx * W - rad * 0.22, ly * H - rad * 0.22, lx * W + rad * 0.22, ly * H + rad * 0.22], fill=int(255 * min(1, a * 1.5)))
    m = Image.fromarray(np.maximum(np.asarray(halo.filter(ImageFilter.GaussianBlur(W * 0.06))),
                                   np.asarray(core.filter(ImageFilter.GaussianBlur(W * 0.012)))))
    img = Image.new("RGBA", (W, H), rgb + (0,))
    img.putalpha(m)
    img.resize((cx.W, cx.H), Image.BICUBIC).save(out)
    return out


def key_png(cx: Ctx, side: str, face) -> Path:
    """Grey key-light map: bright on the lit side of the face, falling off across and down."""
    from PIL import Image
    out = _cache_png(cx, "key", [side, face])
    if out.exists():
        return out
    W, H = cx.W // 4, cx.H // 4
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    fx, fy = face
    xs = (x / W - fx) * (1 if side == "right" else -1)
    across = np.clip(0.5 + xs * 2.2, 0, 1)
    rad = np.exp(-(((x / W - fx) / 0.42) ** 2 + ((y / H - fy) / 0.3) ** 2))
    g = np.clip(across * (0.35 + 0.65 * rad), 0, 1) * 255
    Image.fromarray(g.astype(np.uint8)).resize((cx.W, cx.H), Image.BICUBIC).save(out)
    return out


def rimside_png(cx: Ctx, side: str) -> Path:
    """Grey mask for where the rim light shows: the side away from the key, and the top."""
    from PIL import Image
    out = _cache_png(cx, "rims", [side])
    if out.exists():
        return out
    W, H = cx.W // 4, cx.H // 4
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    far = (x / W) if side == "left" else (1 - x / W)
    g = np.clip(0.25 + far * 1.1, 0, 1) * np.clip(1.25 - y / H * 1.4, 0.15, 1) * 255
    Image.fromarray(g.astype(np.uint8)).resize((cx.W, cx.H), Image.BICUBIC).save(out)
    return out


RELIGHT = {
    #             room eq (brightness, contrast, saturation, gamma) + balance,   key colour/alpha, rim colour/alpha, lamps, bloom, vignette
    "bright_luxe": dict(room=(0.02, 1.04, 1.05, 1.0), bal="", key=(6200, 0.55), rim=("FFFFFF", 0.4), lamp="FFE3B0", lamps=0.0, bloom=0.14, vig=0.0),
    "warm_cafe": dict(room=(-0.07, 1.06, 0.95, 0.94), bal="colorbalance=rs=0.05:gs=0.01:bs=-0.06:rm=0.04:bm=-0.04",
                      key=(4300, 0.6), rim=("FFC074", 0.5), lamp="FFB65C", lamps=0.75, bloom=0.12, vig=0.35),
    "cine_dark": dict(room=(-0.14, 1.1, 0.84, 0.9), bal="colorbalance=rs=-0.03:bs=0.06:rh=0.04:bh=-0.03",
                      key=(5200, 0.7), rim=("A8CBFF", 0.6), lamp="FFB060", lamps=0.6, bloom=0.1, vig=0.55),
    "soft_window": dict(room=(0.02, 1.02, 0.98, 1.02), bal="colorbalance=rs=-0.02:bs=0.03", key=(7200, 0.55),
                        rim=("FFFFFF", 0.3), lamp="FFFFFF", lamps=0.0, bloom=0.14, vig=0.1),
}


def prop_png(cx: Ctx, o: dict, ref_t: float) -> Path:
    """Full-frame RGBA layer with the prop placed (bottom-centre anchor), colour-matched to the room, contact shadow,
    and a warm glow for lamps."""
    from PIL import Image, ImageFilter, ImageDraw
    src = str(o.get("src", "plant"))
    path = Path(src) if Path(src).suffix else PROPS_DIR / f"{Path(src).name}.png"  # render.py absolutises bare names
    if not path.exists():
        raise FileNotFoundError(f"prop '{src}' not found (built-ins: {', '.join(p.stem for p in PROPS_DIR.glob('*.png'))})")
    px, py = o.get("pos", [0.14, 0.9])
    wf = float(o.get("width", 0.36))
    out = _cache_png(cx, "prop", [str(path), path.stat().st_mtime_ns, px, py, wf, o.get("match", True), o.get("shadow", True),
                                  o.get("glow"), o.get("flip"), round(ref_t, 2), str(cx.base)])
    if out.exists():
        return out
    im = Image.open(path).convert("RGBA")
    if o.get("flip"):
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    w = int(wf * cx.W)
    h = int(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    if o.get("match", True):  # pull the prop toward the room's exposure / white balance so it sits in the light
        fr = np.asarray(grab_frame(cx, ref_t)).astype(np.float32)
        alpha = a[..., 3:] / 255
        pm = (a[..., :3] * alpha).sum((0, 1)) / max(1, alpha.sum())
        rm = fr.reshape(-1, 3).mean(0)
        gain = np.clip((rm.mean() / max(1, pm.mean())) ** 0.45, 0.6, 1.15)
        wb = np.clip((rm / max(1, rm.mean())) / (pm / max(1, pm.mean())), 0.85, 1.15) ** 0.5
        a[..., :3] = np.clip(a[..., :3] * gain * wb, 0, 255)
    im = Image.fromarray(a.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    canvas = Image.new("RGBA", (cx.W, cx.H), (0, 0, 0, 0))
    x0, y0 = int(px * cx.W - w / 2), int(py * cx.H - h)
    if o.get("glow") or (o.get("glow") is None and path.stem.startswith("lamp")):
        g = Image.new("L", (cx.W // 4, cx.H // 4), 0)
        gx, gy, gr = (x0 + w / 2) / 4, (y0 + h * 0.14) / 4, w * 0.9 / 4
        ImageDraw.Draw(g).ellipse([gx - gr, gy - gr * 0.8, gx + gr, gy + gr * 0.8], fill=150)
        glow = Image.new("RGBA", g.size, (255, 196, 120, 0))
        glow.putalpha(g.filter(ImageFilter.GaussianBlur(gr * 0.45)))
        canvas.alpha_composite(glow.resize((cx.W, cx.H), Image.BICUBIC))
    if o.get("shadow", True):
        sh = Image.new("L", (cx.W, cx.H), 0)
        ImageDraw.Draw(sh).ellipse([x0 + w * 0.12, y0 + h - h * 0.035, x0 + w * 0.88, y0 + h + h * 0.035], fill=150)
        shadow = Image.new("RGBA", (cx.W, cx.H), (0, 0, 0, 0))
        shadow.putalpha(sh.filter(ImageFilter.GaussianBlur(w * 0.05)))
        canvas.alpha_composite(shadow)
    canvas.alpha_composite(im, (x0, y0))
    canvas.save(out)
    return out


def apply(o: dict, k: int, vlast: str, cx: Ctx) -> str:
    if o["type"] == "loopback":
        d = float(o.get("duration", 0.5))
        o = {**o, "start": max(0.0, cx.total - d), "end": cx.total}
        o.pop("clip", None)
    if o["type"] in ("relight", "prop") and "start" not in o and "clip" not in o:
        o = {**o, "start": 0, "end": o.get("end", cx.total)}
    s, e = times(o, cx.starts, cx.total)
    if e - s < 0.05:
        return vlast
    W, H, fc = cx.W, cx.H, cx.fc
    t = o["type"]
    fd = float(o.get("fade", 0.25))
    if t == "outline":
        return outline(o, k, vlast, cx, s, e, fd)
    if t in ("freeze", "loopback", "facecam", "leak", "spinwhip", "zoomblur", "tumble"):  # built from stills / the base file, no copy of the live stream needed
        clean = None
    else:
        fc.append(f"{vlast}split=2[vk{k}][cl{k}]")
        vlast, clean = f"[vk{k}]", f"[cl{k}]"

    if t == "bg":
        if not o.get("src"):
            fc.append(f"{clean}split=2[cla{k}][clb{k}]")
            pclean = f"[clb{k}]"
        else:
            pclean = clean
        if o.get("src"):
            src = str(o["src"])
            is_img = Path(src).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
            i = cx.add_input((["-loop", "1", "-t", f"{e - s + 0.5:.3f}"] if is_img else
                              ["-stream_loop", "-1", "-t", f"{e - s + 0.5:.3f}"]) + ["-i", src])
            fc.append(f"[{i}:v]fps={cx.fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                      f"setsar=1,format=yuv420p,setpts=PTS-STARTPTS+{s:.3f}/TB[bgr{k}]")
            room = f"[bgr{k}]"
        else:
            room = cx.cut(f"[cla{k}]", s, e, f"[bgr{k}]")
        chain = []
        if float(o.get("blur", 0)) > 0:
            sig = float(o["blur"]) / 4
            chain += [f"scale={W // 4}:{H // 4}", f"gblur=sigma={sig:.1f}", f"scale={W}:{H}"]
        if o.get("tint"):
            chain.append(f"drawbox=c={o['tint']}:t=fill")
        sc = float(o.get("scale", 1))
        if sc < 1:
            sw, sh = int(W * sc) // 2 * 2, int(H * sc) // 2 * 2
            chain += [f"scale={sw}:{sh}", "format=rgba"]
            if o.get("radius"):
                chain.append(round_mask(int(o["radius"])))
            col = theme.tint(o.get("color", "0x0E1A3A"))
            fc.append(f"{room}{','.join(chain)}[bgs{k}]")
            fc.append(f"color=c={col}:s={W}x{H}:r={cx.fps},trim=duration={e - s + 0.5:.3f},"
                      f"setpts=PTS-STARTPTS+{s:.3f}/TB[bgc{k}]")
            fc.append(f"[bgc{k}][bgs{k}]overlay=x=(W-w)/2:y=(H-h)/2:shortest=1[bgx{k}]")
            room = f"[bgx{k}]"
        elif chain:
            fc.append(f"{room}{','.join(chain)}[bgx{k}]")
            room = f"[bgx{k}]"
        p = person_layer(cx, pclean, s, e, k, float(o.get("choke", 0)))
        fc.append(f"{room}{p}overlay=0:0:shortest=1,format=rgba,{_fades(s, e, cx.total, fd)}[bgo{k}]")
        return _over(cx, vlast, f"[bgo{k}]", s, e, k, "b")

    if t == "popout":
        win = o.get("window", {})
        cxp, cyp, cw, ch = win.get("crop", [0.06, 0.30, 0.88, 0.42])
        ww = float(win.get("width", 0.84))
        ow = int(ww * W) // 2 * 2
        f = ow / (cw * W)
        oh = int(ch * H * f) // 2 * 2
        px, py = win.get("pos", [0.5, 0.68])
        x0, y0 = int(px * W - ow / 2), int(py * H - oh / 2)
        r = int(win.get("radius", 44))
        col = theme.tint(o.get("bg", "0xEEF1F8"))
        fc.append(f"{clean}split=2[pa{k}][pb{k}]")
        win_l = cx.cut(f"[pa{k}]", s, e, f"[pw{k}]")
        fc.append(f"{win_l}crop=w=iw*{cw}:h=ih*{ch}:x=iw*{cxp}:y=ih*{cyp},scale={ow}:{oh},format=rgba,{round_mask(r)}[pwr{k}]")
        # speaker cut-out at the same scale, from the top of the frame down to the window bottom
        per = person_layer(cx, f"[pb{k}]", s, e, k)
        top_src = 0.0
        hh = int((cyp + ch - top_src) * H * f) // 2 * 2
        # only the head/shoulders column may break out above the window (keeps wall logos etc. out)
        hx, hw = o.get("head", [0.5, 2.0])  # [centre x, width] fractions; default = no limit
        cxl = (float(hx) - cxp) / cw * ow
        hw2 = float(hw) * W * f / 2
        fc.append(f"{per}crop=w=iw*{cw}:h=ih*{cyp + ch - top_src:.4f}:x=iw*{cxp}:y=ih*{top_src},scale={ow}:{hh},format=rgba,"
                  f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*if(gt(Y,{hh - oh}),1,clip(({hw2:.1f}-abs(X-{cxl:.1f}))/40,0,1))'[ppo{k}]")
        fc.append(f"color=c={col}:s={W}x{H}:r={cx.fps},trim=duration={e - s + 0.5:.3f},setpts=PTS-STARTPTS+{s:.3f}/TB[pcol{k}]")
        fc.append(f"[pcol{k}][pwr{k}]overlay=x={x0}:y={y0}:shortest=1[pq{k}]")
        fc.append(f"[pq{k}][ppo{k}]overlay=x={x0}:y={y0 + oh - hh}:shortest=1,format=rgba,{_fades(s, e, cx.total, fd)}[po{k}]")
        return _over(cx, vlast, f"[po{k}]", s, e, k, "p")

    if t == "lens":
        ax, ay = o.get("at", [0.5, 0.33])
        px, py = o.get("pos", [ax, ay])
        z = float(o.get("zoom", 1.9))
        d = int(float(o.get("size", 0.42)) * W) // 2 * 2
        src_d = int(d / z) // 2 * 2
        sx, sy = int(ax * W - src_d / 2), int(ay * H - src_d / 2)
        l = cx.cut(clean, s, e, f"[ln{k}]")
        rim = max(6, d // 40)
        fc.append(f"{l}crop={src_d}:{src_d}:{max(0, sx)}:{max(0, sy)},scale={d}:{d}:flags=lanczos,format=rgba,"
                  f"geq=lum='p(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),W/2-{rim}),255,0)',"
                  f"{_fades(s, e, cx.total, 0.15)}[lz{k}]")
        # glass rim: white ring + soft shadow
        D = d + 2 * rim
        fc.append(f"color=c=white:s={D}x{D}:r={cx.fps},trim=duration={e - s + 0.5:.3f},format=rgba,"
                  f"geq=r=245:g=248:b=255:a='if(between(hypot(X-W/2,Y-H/2),W/2-{2 * rim},W/2),235,0)',"
                  f"setpts=PTS-STARTPTS+{s:.3f}/TB,{_fades(s, e, cx.total, 0.15)}[lr{k}]")
        v = _over(cx, vlast, f"[lz{k}]", s, e, k, "l", f"{int(px * W - d / 2)}", f"{int(py * H - d / 2)}")
        return _over(cx, v, f"[lr{k}]", s, e, k, "r", f"{int(px * W - D / 2)}", f"{int(py * H - D / 2)}")

    if t == "fx":
        eff = o.get("effect", "vhs")
        looks = {
            "vhs": "rgbashift=rh=7:bh=-7:gv=2,eq=saturation=1.25:contrast=1.08,noise=alls=16:allf=t,"
                   "drawgrid=w=iw:h=4:t=1:c=black@0.18,gblur=sigma=0.7",
            "film": "colorbalance=rs=0.06:gs=0.01:bs=-0.07:rm=0.04:bm=-0.05,eq=contrast=1.06:saturation=0.88:gamma=0.97,"
                    "vignette=PI/5,noise=alls=10:allf=t,drawbox=y=0:w=iw:h=ih*0.085:c=black:t=fill,"
                    "drawbox=y=ih*0.915:w=iw:h=ih*0.085:c=black:t=fill",
            "bw": "hue=s=0,eq=contrast=1.12",
            "warm": "colorbalance=rs=0.08:bs=-0.08:rm=0.05:bm=-0.05",
            "cool": "colorbalance=rs=-0.06:bs=0.09:bm=0.06",
        }
        look = looks.get(eff, eff)
        l = cx.cut(clean, s, e, f"[fx{k}]")
        cmp_ = o.get("compare")
        if cmp_:
            a, b = float(cmp_.get("from", 0.0)), float(cmp_.get("to", 1.0))
            dur = max(0.1, e - s)
            fc.append(f"{l}split=2[fxa{k}][fxb{k}]")
            fc.append(f"[fxb{k}]{look},format=yuv420p[fxl{k}]")
            # left of the split = new look, right = original; the split eases from `from` to `to`
            sp = f"({a}+({b}-{a})*(1-pow(1-min(1,max(0,(T-{s:.3f})/{dur:.3f})),2)))"
            fc.append(f"[fxa{k}]format=yuv420p[fxo{k}];[fxl{k}][fxo{k}]blend=all_expr='if(lt(X,W*{sp}),A,B)',"
                      f"drawbox=x='iw*{sp}-2':y=0:w=4:h=ih:c=white@0.95:t=fill:replace=0,format=rgba[fxv{k}]")
        else:
            fc.append(f"{l}{look},format=rgba,{_fades(s, e, cx.total, float(o.get('fade', 0.2)))}[fxv{k}]")
        return _over(cx, vlast, f"[fxv{k}]", s, e, k, "f")

    if t == "spotlight":
        dim = float(o.get("dim", 0.55))
        fc.append(f"{clean}split=2[sla{k}][slb{k}]")
        room = cx.cut(f"[sla{k}]", s, e, f"[slr{k}]")
        fc.append(f"{room}eq=brightness=-{dim * 0.32:.3f}:saturation={1 - dim * 0.45:.2f}:contrast=1.06,vignette=PI/3[sld{k}]")
        g = _png_input(cx, spotlight_png(cx, o), e - s, s, f"[slg{k}]")
        fc.append(f"[sld{k}]{g}overlay=0:0:shortest=1[slx{k}]")
        fc.append(f"[slb{k}]eq=brightness=0.025:contrast=1.04[slp{k}]")
        p = person_layer(cx, f"[slp{k}]", s, e, k)
        fc.append(f"[slx{k}]{p}overlay=0:0:shortest=1,format=rgba,{_fades(s, e, cx.total, fd)}[slo{k}]")
        return _over(cx, vlast, f"[slo{k}]", s, e, k, "s")

    if t == "freeze":
        if "at" in o:
            at = parse_time(o["at"]) + (cx.starts[int(o["clip"])] if "clip" in o else 0)
        else:
            at = s
        plain, styled = freeze_pngs(cx, o, at)
        dur = e - s
        z = float(o.get("zoom", 1.07))
        n = max(2, int(round(dur * cx.fps)))
        a = _png_input(cx, plain, dur, s, f"[fza{k}]")
        i = cx.add_input(["-loop", "1", "-framerate", str(cx.fps), "-t", f"{dur + 0.2:.3f}", "-i", str(styled)])
        # slow push-in with a decelerating ease (zoompan on a 2x still keeps it smooth)
        fc.append(f"[{i}:v]scale={W * 2}:{H * 2}:flags=lanczos,zoompan=z='1+{z - 1:.3f}*(1-pow(1-min(on/{n},1),3))':"
                  f"x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*0.4':d=1:s={W}x{H}:fps={cx.fps},format=rgba,"
                  f"fade=t=in:st=0.06:d=0.18:alpha=1,setpts=PTS-STARTPTS+{s:.3f}/TB[fzb{k}]")
        fc.append(f"{a}[fzb{k}]overlay=0:0:shortest=1[fzc{k}]")
        top = f"[fzc{k}]"
        if o.get("flash", True):
            fc.append(f"color=c=white:s={W}x{H}:r={cx.fps},trim=duration=0.25,format=rgba,fade=t=out:st=0:d=0.22:alpha=1,"
                      f"setpts=PTS-STARTPTS+{s:.3f}/TB[fzw{k}]")
            fc.append(f"{top}[fzw{k}]overlay=0:0:eof_action=pass[fzd{k}]")
            top = f"[fzd{k}]"
        out_fade = f",fade=t=out:st={max(s, e - 0.12):.3f}:d=0.12:alpha=1" if e < cx.total - 0.01 else ""
        fc.append(f"{top}format=rgba{out_fade}[fzo{k}]")
        return _over(cx, vlast, f"[fzo{k}]", s, e, k, "z")

    if t == "whip":
        at = float(o.get("_at", (s + e) / 2))
        amt = float(o.get("amount", 0.6))
        sg = 1 if o.get("dir", "left") == "left" else -1
        a0, a1 = max(1e-3, at - s), max(1e-3, e - at)
        l = cx.cut(clean, s, e, f"[wp{k}]")
        # mirror-tile the frame so the moving crop never runs out of picture
        fc.append(f"{l}split=3[wa{k}][wb{k}][wc{k}];[wb{k}]hflip[wbf{k}];[wc{k}]hflip[wcf{k}];"
                  f"[wbf{k}][wa{k}][wcf{k}]hstack=3[wt{k}]")
        xo = f"{W}+{sg}*{W}*{amt}*pow(min(1,(t-{s:.3f})/{a0:.3f}),2)"
        xi = f"{W}-{sg}*{W}*{amt}*pow(1-min(1,(t-{at:.3f})/{a1:.3f}),2)"
        fc.append(f"[wt{k}]crop=w={W}:h={H}:x='if(lt(t,{at:.3f}),{xo},{xi})':y=0,split=2[ws{k}][wbl{k}]")
        fc.append(f"[wbl{k}]scale={W // 2}:{H // 2},gblur=sigma={W * 0.03:.0f}:sigmaV=0,scale={W}:{H}[wbb{k}]")
        hd = max(a0, a1)
        fc.append(f"[ws{k}][wbb{k}]blend=all_expr='A+(B-A)*min(1,1.6*max(0,1-abs(T-{at:.3f})/{hd:.3f}))',format=yuv420p[wo{k}]")
        return _over(cx, vlast, f"[wo{k}]", s, e, k, "w")

    if t in ("spinwhip", "zoomblur", "tumble"):
        mp4, sh = spinwhip_clip(cx, float(o.get("_at", s + 1 / cx.fps)), s, e, 1 if o.get("dir", "left") == "left" else -1,
                                float(o.get("amount", 1.0)), kind=t)
        s, e = s + sh, e + sh  # the real cut in the base file can sit a frame or two off the planned clip start
        i = cx.add_input(["-i", str(mp4)])
        fc.append(f"[{i}:v]fps={cx.fps},format=yuv420p,setpts=PTS-STARTPTS+{s:.3f}/TB[sw{k}]")
        return _over(cx, vlast, f"[sw{k}]", s, e + 0.5 / cx.fps, k, "s")

    if t == "loopback":
        d = e - s
        i = cx.add_input(["-t", f"{d + 0.1:.3f}", "-i", str(cx.base)])
        fc.append(f"[{i}:v]fps={cx.fps},scale={W}:{H},format=rgba,setpts=PTS-STARTPTS+{s:.3f}/TB,"
                  f"fade=t=in:st={s:.3f}:d={d:.3f}:alpha=1[lb{k}]")
        return _over(cx, vlast, f"[lb{k}]", s, e, k, "o")

    if t == "neon":
        col, col2 = _hex(o.get("color", "#FF3FD8")), _hex(o.get("color2", "#FFFFFF"))
        fc.append(f"{clean}nullsink")  # unused copy
        m = cx.matte_in(s, e, k)
        fc.append(f"{m}split=2[nma{k}][nmb{k}]")
        band = _band(cx, f"[nma{k}]", f"{k}n", float(o.get("gap", 10)), float(o.get("width", 7)))
        core = _band(cx, f"[nmb{k}]", f"{k}c", float(o.get("gap", 10)) + float(o.get("width", 7)) * 0.35, float(o.get("width", 7)) * 0.3)
        fc.append(f"{band}split=2[nba{k}][nbb{k}]")
        hue = f"format=yuv444p,hue=h='t*{float(o.get('speed', 140)):.0f}',format=rgba," if o.get("cycle", True) else ""
        c1 = _color(cx, col, s, e, f"[ncl{k}]", "rgba")
        fc.append(f"{c1}{hue}split=2[ncg{k}][ncb{k}]")
        q = 4
        fc.append(f"[nba{k}]scale={W // q}:{H // q},gblur=sigma={float(o.get('glow', 26)) / q:.1f},scale={W}:{H},"
                  f"lut=y='min(255,val*2.2)'[ngl{k}]")
        fc.append(f"[ncg{k}][ngl{k}]alphamerge[ng{k}];[ncb{k}][nbb{k}]alphamerge[nt{k}]")
        c2 = _color(cx, col2, s, e, f"[nwc{k}]", "rgba")
        fc.append(f"{c2}{core}alphamerge[nw{k}]")
        fl = _fades(s, e, cx.total, fd)
        fc.append(f"[ng{k}][nt{k}]overlay=0:0:shortest=1[nx{k}];[nx{k}][nw{k}]overlay=0:0:shortest=1,{fl}[no{k}]")
        b = float(o.get("boil", 0))
        return _over(cx, vlast, f"[no{k}]", s, e, k, "n",
                     f"'{b}*sin(floor(n/3)*2.1)'" if b else "0", f"'{b}*cos(floor(n/3)*1.7)'" if b else "0")

    if t == "clone":
        cps = o.get("copies") or [{"dx": -0.3, "scale": 0.8, "flip": True, "at": 0.0}, {"dx": 0.3, "scale": 0.8, "flip": True, "at": 0.12}]
        pcx = person_box(cx, s)[0]
        p = person_layer(cx, clean, s, e, k)
        n = len(cps)
        fc.append(f"{p}split={n + 1}" + "".join(f"[cp{k}_{i}]" for i in range(n + 1)))
        v = vlast
        for i, c in enumerate(cps):
            sc = float(c.get("scale", 0.8))
            at = s + float(c.get("at", 0.12 * i))
            ch = [f"scale=iw*{sc}:ih*{sc}"] + (["hflip"] if c.get("flip") else []) + [
                f"colorchannelmixer=rr={float(c.get('dim', 0.9))}:gg={float(c.get('dim', 0.9))}:bb={float(c.get('dim', 0.9))}",
                f"fade=t=in:st={at:.3f}:d=0.18:alpha=1"] + (
                [f"fade=t=out:st={max(at, e - fd):.3f}:d={fd}:alpha=1"] if e < cx.total - 0.01 else [])
            dx = float(c.get("dx", 0.3))
            tx = pcx + dx  # where this copy's body lands; no room on that side -> further out on the other side, smaller
            if not 0.12 <= tx <= 0.88:
                tx, sc = pcx - (1 if dx > 0 else -1) * (abs(dx) + 0.22), sc * 0.82
                ch[0] = f"scale=iw*{sc}:ih*{sc}"
            tx = min(0.9, max(0.1, tx))
            fc.append(f"[cp{k}_{i}]{','.join(ch)}[cq{k}_{i}]")
            x = f"{tx * W - pcx * sc * W:.0f}"
            out = f"[cv{k}_{i}]"
            fc.append(f"{v}[cq{k}_{i}]overlay=x='{x}':y=H-h+{float(c.get('dy', 0)) * H:.0f}:enable='between(t,{s:.3f},{e:.3f})'{out}")
            v = out
        return _over(cx, v, f"[cp{k}_{n}]", s, e, k, "c")

    if t == "dolly":
        plate = clean_plate(cx, s)
        z = float(o.get("zoom", 1.35))
        n = max(2, int(round((e - s) * cx.fps)))
        fy = float(o.get("y", 0.4))
        i = cx.add_input(["-loop", "1", "-framerate", str(cx.fps), "-t", f"{e - s + 0.2:.3f}", "-i", str(plate)])
        ez = f"(on/{n})*(on/{n})*(3-2*on/{n})"
        zz = f"1+{z - 1:.3f}*{ez}" if o.get("mode", "in") == "in" else f"{z:.3f}-{z - 1:.3f}*{ez}"
        fc.append(f"[{i}:v]scale={W * 2}:{H * 2}:flags=lanczos,zoompan=z='{zz}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*{fy}':d=1:"
                  f"s={W}x{H}:fps={cx.fps},setpts=PTS-STARTPTS+{s:.3f}/TB[dp{k}]")
        p = person_layer(cx, clean, s, e, k)
        fc.append(f"[dp{k}]{p}overlay=0:0:shortest=1,format=rgba,{_fades(s, e, cx.total, float(o.get('fade', 0.12)))}[do{k}]")
        return _over(cx, vlast, f"[do{k}]", s, e, k, "d")

    if t == "facecam":
        src_t0 = parse_time(o["from"]) if "from" in o else s
        if o.get("face"):
            fx_, fy_ = o["face"]
            z = float(o.get("zoom", 2.2))
        else:  # frame the detected face: face height ~ 45 % of the bubble
            fx_, fy_, fh = face_center(cx, src_t0 + 0.05)
            fy_ += fh * 0.12
            z = float(o.get("zoom", min(4.0, max(1.6, 0.45 / max(0.02, fh) * W / H))))
        d = int(float(o.get("size", 0.34)) * W) // 2 * 2
        side = int(W / z) // 2 * 2
        src_t = parse_time(o["from"]) if "from" in o else s
        i = cx.add_input(["-ss", f"{src_t:.3f}", "-t", f"{e - s + 0.1:.3f}", "-i", str(cx.base)])
        rim = max(6, d // 30)
        x0, y0 = max(0, int(fx_ * W - side / 2)), max(0, int(fy_ * H - side / 2))
        fc.append(f"[{i}:v]fps={cx.fps},scale={W}:{H},crop={side}:{side}:{x0}:{y0},scale={d}:{d}:flags=lanczos,format=rgba,"
                  f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),W/2-{rim}),255,0)',"
                  f"setpts=PTS-STARTPTS+{s:.3f}/TB,{_fades(s, e, cx.total, 0.15)}[fcv{k}]")
        D = d + 2 * rim
        rc = _hex(o.get("ring", "#FFFFFF"))
        fc.append(f"color=c=0x{rc}:s={D}x{D}:r={cx.fps},trim=duration={e - s + 0.2:.3f},format=rgba,"
                  f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(between(hypot(X-W/2,Y-H/2),W/2-{2 * rim},W/2),255,0)',"
                  f"setpts=PTS-STARTPTS+{s:.3f}/TB,{_fades(s, e, cx.total, 0.15)}[fcr{k}]")
        px, py = o.get("pos", [0.78, 0.8])
        v = _over(cx, vlast, f"[fcv{k}]", s, e, k, "v", f"{int(px * W - d / 2)}", f"{int(py * H - d / 2)}")
        return _over(cx, v, f"[fcr{k}]", s, e, k, "r", f"{int(px * W - D / 2)}", f"{int(py * H - D / 2)}")

    if t == "glitch":
        import random
        rnd = random.Random(int(s * 1000))
        l = cx.cut(clean, s, e, f"[gl{k}]")
        step = float(o.get("step", 0.067))
        cuts = []
        a = s
        while a < e - 1e-3:
            cuts.append((a, min(e, a + step)))
            a += step
        fc.append(f"{l}split={len(cuts)}" + "".join(f"[gs{k}_{j}]" for j in range(len(cuts))))
        v = vlast
        for j, (a, b) in enumerate(cuts):
            dx = rnd.choice([-1, 1]) * rnd.randint(14, 46)
            y0 = rnd.uniform(0.1, 0.7) * H
            y1 = y0 + rnd.uniform(0.04, 0.16) * H
            sh = rnd.choice([-1, 1]) * rnd.randint(40, 160)
            band = f"if(between(Y,{y0:.0f},{y1:.0f}),{sh},0)"
            fc.append(f"[gs{k}_{j}]trim=start={a:.3f}:end={b:.3f},format=gbrp,"
                      f"geq=r='r(X+{dx}+{band},Y)':g='g(X+{band},Y)':b='b(X-{dx}+{band},Y)',"
                      f"noise=alls=28:allf=t,eq=contrast=1.25:saturation=1.3,format=yuv420p[gx{k}_{j}]")
            out = f"[gv{k}_{j}]"
            fc.append(f"{v}[gx{k}_{j}]overlay=enable='between(t,{a:.3f},{b:.3f})':eof_action=pass{out}")
            v = out
        return v

    if t == "leak":
        d = e - s
        png = leak_png(cx, o.get("color", "warm"))
        i = cx.add_input(["-loop", "1", "-framerate", str(cx.fps), "-t", f"{d + 0.2:.3f}", "-i", str(png)])
        pk = float(o.get("_at", s + d / 2))
        fc.append(f"[{i}:v]format=rgba,setpts=PTS-STARTPTS+{s:.3f}/TB,"
                  f"fade=t=in:st={s:.3f}:d={max(0.05, pk - s):.3f}:alpha=1,fade=t=out:st={pk:.3f}:d={max(0.05, e - pk):.3f}:alpha=1[lk{k}]")
        v = _over(cx, vlast, f"[lk{k}]", s, e, k, "k", f"'-w*0.35+(W*0.35)*(t-{s:.3f})/{d:.3f}'", "0")
        fl = _color(cx, "FFF4E0", s, e, f"[lf{k}]")
        fc.append(f"{fl}colorchannelmixer=aa={float(o.get('flash', 0.38)):.2f},fade=t=in:st={pk - 0.06:.3f}:d=0.06:alpha=1,"
                  f"fade=t=out:st={pk:.3f}:d=0.14:alpha=1[lfa{k}]")
        return _over(cx, v, f"[lfa{k}]", s, e, k, "h")

    if t == "zoomthru":
        at = float(o.get("_at", (s + e) / 2))
        A = float(o.get("amount", 2.4))
        fx_, fy_ = o.get("at_xy", o.get("focus", [0.5, 0.42]))
        n0, n1 = max(1, (at - s) * cx.fps), max(1, (e - at) * cx.fps)
        tt = f"(on/{cx.fps}+{s:.4f})"
        z = (f"if(lt({tt},{at:.4f}),1+{A - 1:.3f}*pow(on/{n0:.2f},2),"
             f"{A:.3f}-{A - 1:.3f}*(1-pow(1-min(1,(on-{n0:.2f})/{n1:.2f}),2)))")
        l = cx.cut(clean, s, e, f"[zt{k}]")
        fc.append(f"{l}scale={W * 2}:{H * 2}:flags=bicubic,zoompan=z='{z}':x='(iw-iw/zoom)*{fx_}':y='(ih-ih/zoom)*{fy_}':d=1:"
                  f"s={W}x{H}:fps={cx.fps},tmix=frames=3,setpts=PTS-STARTPTS+{s:.3f}/TB,format=yuv420p[zo{k}]")
        return _over(cx, vlast, f"[zo{k}]", s, e, k, "t")

    if t == "impact":
        ax, ay = o.get("at") or face_center(cx, s)[:2]
        l = cx.cut(clean, s, e, f"[im{k}]")
        lines = _png_input(cx, speedlines_png(cx, ax, ay), e - s, s, f"[iml{k}]")
        amp = int(o.get("shake", 18))
        fc.append(f"{l}hue=s=0,eq=contrast=2.4:brightness=0.06,lutyuv=y='if(lt(val,105),18,if(lt(val,150),128,240))',"
                  f"format=yuv420p[imb{k}]")
        fc.append(f"[imb{k}]{lines}overlay=0:0:shortest=1,negate=enable='lt(mod(n,4),2)',scale={W + 2 * amp}:{H + 2 * amp},"
                  f"crop={W}:{H}:'{amp}+{amp}*sin(n*2.7)':'{amp}+{amp}*cos(n*2.1)',format=yuv420p[imo{k}]")
        return _over(cx, vlast, f"[imo{k}]", s, e, k, "i")

    if t == "dramatic":
        ax, ay = o.get("at") or face_center(cx, s)[:2]
        z = float(o.get("zoom", 1.7))
        n_in = max(1, int(0.08 * cx.fps))
        l = cx.cut(clean, s, e, f"[dr{k}]")
        amp = int(o.get("shake", 14))
        nsh = int(0.3 * cx.fps)
        fc.append(f"{l}scale={W * 2}:{H * 2}:flags=bicubic,zoompan=z='1+{z - 1:.3f}*min(1,on/{n_in})':"
                  f"x='(iw-iw/zoom)*{ax}':y='(ih-ih/zoom)*{ay}':d=1:s={W}x{H}:fps={cx.fps},"
                  f"scale={W + 2 * amp}:{H + 2 * amp},crop={W}:{H}:'{amp}+{amp}*sin(n*3.1)*max(0,1-n/{nsh})':'{amp}+{amp}*cos(n*2.3)*max(0,1-n/{nsh})',"
                  f"eq=saturation=0.8:contrast=1.15,setpts=PTS-STARTPTS+{s:.3f}/TB[drz{k}]")
        vg = _png_input(cx, vignette_png(cx, _hex(o.get("tint", "#C8102E")), float(o.get("strength", 0.85))), e - s, s, f"[drv{k}]")
        fc.append(f"[drz{k}]{vg}overlay=0:0:shortest=1,format=yuv420p[dro{k}]")
        return _over(cx, vlast, f"[dro{k}]", s, e, k, "x")

    if t == "colorize":
        d = e - s
        hold = float(o.get("hold", 0.4))
        l = cx.cut(clean, s, e, f"[cz{k}]")
        fc.append(f"{l}split=2[cza{k}][czb{k}];[cza{k}]hue=s=0,colorbalance=rm=0.06:bm=-0.06,eq=contrast=1.1,noise=alls=12:allf=t[czg{k}]")
        mix = f"min(1,max(0,(T-{s + hold:.3f})/{max(0.2, d - hold - 0.1):.3f}))"
        expr = f"A+(B-A)*{mix}*{mix}*(3-2*{mix})" if o.get("mode", "fade") == "fade" else \
            f"if(lt(X,W*{mix}*1.15-W*0.08),B,if(lt(X,W*{mix}*1.15),A+(B-A)*(X-(W*{mix}*1.15-W*0.08))/(W*0.08),A))"
        fc.append(f"[czg{k}][czb{k}]blend=all_expr='{expr}',format=yuv420p[czo{k}]")
        return _over(cx, vlast, f"[czo{k}]", s, e, k, "z")

    if t == "relight":
        P = {**RELIGHT.get(o.get("preset", "warm_cafe"), RELIGHT["warm_cafe"]), **{k2: v for k2, v in o.items() if k2 in RELIGHT["warm_cafe"]}}
        st = float(o.get("strength", 1.0))
        side = o.get("side", "left")
        face = o.get("face") or list(face_center(cx, s + 0.05)[:2])
        br, ct, sa, ga = P["room"]
        fc.append(f"{clean}split=2[rla{k}][rlb{k}]")
        room = cx.cut(f"[rla{k}]", s, e, f"[rlr{k}]")
        ch = [f"eq=brightness={br * st:.3f}:contrast={1 + (ct - 1) * st:.3f}:saturation={1 + (sa - 1) * st:.3f}:gamma={1 + (ga - 1) * st:.3f}"]
        if P["bal"]:
            ch.append(P["bal"])
        if P["vig"] > 0:
            ch.append(f"vignette=angle={0.35 + 0.5 * P['vig'] * st:.2f}")
        fc.append(f"{room}{','.join(ch)}[rlg{k}]")
        rl = f"[rlg{k}]"
        lamps = o.get("lamps", [[0.12, 0.24], [0.88, 0.3]] if P["lamps"] > 0 else [])
        if lamps:
            lp = _png_input(cx, lamps_png(cx, lamps, _hex(o.get("lamp_color", P["lamp"])), P["lamps"] or 0.7), e - s, s, f"[rll{k}]")
            fc.append(f"{rl}{lp}overlay=0:0:shortest=1[rlm{k}]")
            rl = f"[rlm{k}]"
        fc.append(f"[rlb{k}]eq=brightness={0.02 * st:.3f}:contrast={1 + 0.04 * st:.3f}[rlq{k}]")
        p = person_layer(cx, f"[rlq{k}]", s, e, k)
        fc.append(f"{rl}{p}overlay=0:0:shortest=1[rlp{k}]")
        # key light: a brighter, colour-temperatured copy of the frame shown through (key map x person matte),
        # so the lit side of the face gains exposure but keeps its texture (no colour wash)
        m = cx.matte_in(s, e, k, "r")
        fc.append(f"{m}split=2[rkm{k}][rrm{k}]")
        q4w, q4h = W // 4, H // 4
        km = _png_input(cx, key_png(cx, side, face), e - s, s, f"[rkp{k}]", "gray")
        fc.append(f"{km}scale={q4w}:{q4h}[rkg{k}];[rkm{k}]scale={q4w}:{q4h},format=gray[rkq{k}];"
                  f"[rkq{k}][rkg{k}]blend=all_mode=multiply:shortest=1,lut=y='val*{P['key'][1] * st:.3f}',"
                  f"scale={W}:{H}:flags=bilinear[rka{k}]")
        fc.append(f"[rlp{k}]split=2[rlp1{k}][rlp2{k}];[rlp2{k}]eq=gamma={1 + 0.32 * st:.3f}:brightness={0.02 * st:.3f}:contrast=1.03,"
                  f"colortemperature=temperature={int(P['key'][0])}:mix={0.6 * st:.2f},format=rgba[rkb{k}]")
        fc.append(f"[rkb{k}][rka{k}]alphamerge[rk{k}];[rlp1{k}][rk{k}]overlay=0:0:shortest=1[rlk{k}]")
        # rim light: thin band just inside the matte edge, mostly on the far side and the top
        q = 4
        fc.append(f"[rrm{k}]scale={W // q}:{H // q},format=gray,split=2[rre{k}][rro{k}];"
                  f"[rre{k}]gblur=sigma=3,lut=y='if(gt(val,235),255,0)'[rri{k}];"
                  f"[rro{k}]lut=y='if(gt(val,110),255,0)'[rrf{k}];"
                  f"[rrf{k}][rri{k}]blend=all_mode=difference,gblur=sigma=0.7[rrb{k}]")
        rs = _png_input(cx, rimside_png(cx, side), e - s, s, f"[rrs{k}]", "gray")
        fc.append(f"{rs}scale={q4w}:{q4h}[rrg{k}];[rrb{k}][rrg{k}]blend=all_mode=multiply:shortest=1,"
                  f"lut=y='min(255,val*{P['rim'][1] * st * 1.6:.3f})',scale={W}:{H}:flags=bilinear[rra{k}]")
        rc = _color(cx, P["rim"][0], s, e, f"[rrc{k}]")
        fc.append(f"{rc}[rra{k}]alphamerge[rr{k}];[rlk{k}][rr{k}]overlay=0:0:shortest=1,format=yuv420p[rlz{k}]")
        out = f"[rlz{k}]"
        if P["bloom"] > 0:
            fc.append(f"{out}split=2[rbo{k}][rbh{k}];[rbh{k}]lutyuv=y='if(gt(val,190),val,16)':u=128:v=128,"
                      f"scale={W // 4}:{H // 4},gblur=sigma=10,scale={W}:{H}[rbb{k}];"
                      f"[rbo{k}][rbb{k}]blend=c0_mode=screen:c0_opacity={P['bloom'] * st:.2f}:c1_mode=normal:c1_opacity=1:c2_mode=normal:c2_opacity=1[rbz{k}]")
            out = f"[rbz{k}]"
        fc.append(f"{out}format=rgba,{_fades(s, e, cx.total, fd)}[rlo{k}]")
        return _over(cx, vlast, f"[rlo{k}]", s, e, k, "g")

    if t == "prop":
        png = prop_png(cx, o, s + 0.05)
        pl = _png_input(cx, png, e - s, s, f"[pr{k}]")
        if o.get("behind") is None:  # auto: only occlude when the prop's box reaches the speaker
            from PIL import Image
            bb = Image.open(png).getbbox() or (0, 0, 0, 0)
            px0, _, px1, _ = (b / cx.W for b in bb)
            sx, _, _ = person_box(cx, s)
            m = still_matte(grab_frame(cx, s)) > 0.5
            cols = np.nonzero(m.any(axis=0))[0]
            l, rr = (cols.min() / m.shape[1], cols.max() / m.shape[1]) if len(cols) else (sx - 0.2, sx + 0.2)
            o = {**o, "behind": not (px1 < l - 0.01 or px0 > rr + 0.01)}
        if o.get("behind") is False:
            fc.append(f"{clean}nullsink")
            fc.append(f"{pl}{_fades(s, e, cx.total, fd)}[pro{k}]")
            return _over(cx, vlast, f"[pro{k}]", s, e, k, "a")
        fc.append(f"{clean}split=2[pra{k}][prb{k}]")
        room = cx.cut(f"[pra{k}]", s, e, f"[prr{k}]")
        p = person_layer(cx, f"[prb{k}]", s, e, k)
        fc.append(f"{room}{pl}overlay=0:0:shortest=1[prx{k}];[prx{k}]{p}overlay=0:0:shortest=1,format=rgba,{_fades(s, e, cx.total, fd)}[pro{k}]")
        return _over(cx, vlast, f"[pro{k}]", s, e, k, "a")
    return vlast


BLEND_BASE = {"overlay": "gray", "softlight": "gray", "hardlight": "gray", "screen": "black", "addition": "black", "difference": "black", "exclusion": "black",
              "lighten": "black", "multiply": "white", "darken": "white"}


def motion_special(o: dict, k: int, vlast: str, cx: Ctx) -> str:
    """Motion overlay (already rendered .mov) with "behind": true, "fill": "video" | "glass", or "blend": mode."""
    s, e = times(o, cx.starts, cx.total)
    W, H, fc = cx.W, cx.H, cx.fc
    i = cx.add_input(["-i", str(o["src"])])
    fc.append(f"[{i}:v]format=rgba,setpts=PTS-STARTPTS+{s:.3f}/TB[mv{k}]")
    if o.get("blend"):
        # the comp takes the light and texture of what is under it (text projected on a wall): put it on the blend
        # mode's neutral colour, then blend in RGB so chroma is not shifted
        mode = str(o["blend"])
        neutral = {"gray": "0x808080", "black": "black", "white": "white"}[BLEND_BASE.get(mode, "gray")]
        op = float(o.get("blend_opacity", 1.0))
        fc.append(f"color=c={neutral}:s={W}x{H}:r={cx.fps},trim=duration={e - s + 0.2:.3f},setpts=PTS-STARTPTS+{s:.3f}/TB,format=rgba[mn{k}]")
        fc.append(f"[mn{k}][mv{k}]overlay=0:0:shortest=1,format=gbrp[ml{k}]")
        fc.append(f"{vlast}split=2[mw{k}][mc{k}]")
        base = cx.cut(f"[mc{k}]", s, e, f"[mb{k}]")
        fc.append(f"{base}format=gbrp[mbg{k}];[mbg{k}][ml{k}]blend=all_mode={mode}:all_opacity={op},format=yuv420p[mx{k}]")
        return _over(cx, f"[mw{k}]", f"[mx{k}]", s, e, k, "m")
    fc.append(f"{vlast}split=2[mw{k}][mc{k}]")
    vlast, clean = f"[mw{k}]", f"[mc{k}]"
    if o.get("fill") == "glass":
        # frosted glass letters: the comp's shape shows a blurred, brightened copy of the video; its own rim on top
        vz = cx.cut(clean, s, e, f"[mz{k}]")
        fc.append(f"{vz}scale={W // 4}:{H // 4},gblur=sigma={float(o.get('glass_blur', 9)):.1f},scale={W}:{H},"
                  f"eq=brightness=0.08:saturation=1.1,drawbox=c=white@0.12:t=fill,format=rgba[mzz{k}]")
        fc.append(f"[mv{k}]split=2[mva{k}][mvb{k}];[mva{k}]alphaextract,lut=y='if(gt(val,8),255,0)',gblur=sigma=0.8[ma{k}];"
                  f"[mzz{k}][ma{k}]alphamerge[mf{k}]")
        v = _over(cx, vlast, f"[mf{k}]", s, e, k, "m")
        return _over(cx, v, f"[mvb{k}]", s, e, k, "r")
    if o.get("fill") == "video":
        z = float(o.get("fill_zoom", 1.25))
        fc.append(f"{clean}split=2[mca{k}][mcb{k}]")
        vz = cx.cut(f"[mca{k}]", s, e, f"[mz{k}]")
        fc.append(f"{vz}scale=iw*{z}:ih*{z},crop={W}:{H},eq=contrast=1.1:saturation=1.15,format=rgba[mzz{k}]")
        fc.append(f"[mv{k}]alphaextract[ma{k}];[mzz{k}][ma{k}]alphamerge[mf{k}]")
        dim = float(o.get("dim", 0.62))
        fc.append(f"{vlast}drawbox=c=black@{dim}:t=fill:enable='between(t,{s:.3f},{e:.3f})'[md{k}]")
        vlast = f"[md{k}]"
        if o.get("behind"):
            v = _over(cx, vlast, f"[mf{k}]", s, e, k, "m")
            p = person_layer(cx, f"[mcb{k}]", s, e, k)
            return _over(cx, v, p, s, e, k, "q")
        return _over(cx, vlast, f"[mf{k}]", s, e, k, "m")
    v = _over(cx, vlast, f"[mv{k}]", s, e, k, "m")
    p = person_layer(cx, clean, s, e, k)
    return _over(cx, v, p, s, e, k, "q")
