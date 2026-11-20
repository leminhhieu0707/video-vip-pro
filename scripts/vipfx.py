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
Motion overlays (Remotion) get two extra flags here:
  "behind": true   drawn between the room and the speaker (text behind the head, orbit ring back half, code wall)
  "fill": "video"  the comp's alpha becomes a window onto the (zoomed) video ("chữ chứa video"); frame darkens behind
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import theme  # noqa: E402
from common import FFMPEG, parse_time  # noqa: E402

TYPES = {"bg", "popout", "lens", "fx"}
MATTE_VERSION = 4
MATTE_MODEL = "u2net"  # tested 20/11: cleaner than u2net_human_seg (which grabbed a wall logo) and more solid than isnet


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
    from rembg import new_session
    sess = new_session(MATTE_MODEL)
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
            if o.get("type") in ("bg", "popout") or (o.get("type") == "motion" and (o.get("behind") or o.get("fill"))):
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


def person_layer(cx: Ctx, clean: str, s: float, e: float, k: int) -> str:
    """RGBA stream of just the speaker (from `clean`) for [s, e]."""
    c = cx.cut(clean, s, e, f"[pc{k}]")
    m = cx.matte_in(s, e, k)
    cx.fc.append(f"{c}{m}alphamerge[pp{k}]")
    return f"[pp{k}]"


def apply(o: dict, k: int, vlast: str, cx: Ctx) -> str:
    s, e = times(o, cx.starts, cx.total)
    if e - s < 0.05:
        return vlast
    W, H, fc = cx.W, cx.H, cx.fc
    t = o["type"]
    fd = float(o.get("fade", 0.25))
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
        p = person_layer(cx, pclean, s, e, k)
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
    return vlast


def motion_special(o: dict, k: int, vlast: str, cx: Ctx) -> str:
    """Motion overlay (already rendered .mov) with "behind": true or "fill": "video"."""
    s, e = times(o, cx.starts, cx.total)
    W, H, fc = cx.W, cx.H, cx.fc
    i = cx.add_input(["-i", str(o["src"])])
    fc.append(f"[{i}:v]format=rgba,setpts=PTS-STARTPTS+{s:.3f}/TB[mv{k}]")
    fc.append(f"{vlast}split=2[mw{k}][mc{k}]")
    vlast, clean = f"[mw{k}]", f"[mc{k}]"
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
