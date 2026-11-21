"""2.5D "3D photo" for still images: the subject is cut out (rembg), the background behind it is inpainted, and the two
layers move at different speeds (parallax), so a flat photo gets depth.  Used by render.py for image clips with
"parallax": true | {"amount": 1.0, "dir": "right" | "left" | "in"}.  Returns an mp4 at the canvas size, cached."""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG  # noqa: E402

VERSION = 1


def make(src: str, dur: float, W: int, H: int, fps: int, work: Path, opts=True) -> Path | None:
    import cv2
    from PIL import Image
    o = opts if isinstance(opts, dict) else {}
    amount, dirn = float(o.get("amount", 1.0)), o.get("dir", "right")
    p = Path(src)
    key = hashlib.md5(f"{p.resolve()}|{p.stat().st_mtime_ns}|{dur:.3f}|{W}x{H}@{fps}|{amount}|{dirn}|{VERSION}".encode()).hexdigest()[:10]
    out = work / "parallax" / f"px_{key}.mp4"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    M = 1.18  # working canvas margin so moves never show an edge
    cw, ch = int(W * M) // 2 * 2, int(H * M) // 2 * 2
    img = Image.open(p).convert("RGB")
    sc = max(cw / img.width, ch / img.height)
    img = img.resize((int(img.width * sc + 1), int(img.height * sc + 1)), Image.LANCZOS)
    l, t = (img.width - cw) // 2, (img.height - ch) // 2
    img = img.crop((l, t, l + cw, t + ch))
    a = np.asarray(img)

    import vipfx
    m = np.asarray(vipfx.rembg_session("u2net").predict(img)[0].resize(img.size, Image.BILINEAR), np.float32) / 255.0
    m = vipfx.keep_main_blob(np.clip((m - 0.25) / 0.5, 0, 1))
    if (m > 0.5).mean() < 0.03 or (m > 0.5).mean() > 0.8:
        return None  # no clear subject: plain Ken Burns is the better look
    # background plate: subject area inpainted (half res) and softened
    small = cv2.resize(a, (cw // 2, ch // 2), interpolation=cv2.INTER_AREA)
    mk = cv2.dilate(cv2.resize((m > 0.25).astype(np.uint8) * 255, (cw // 2, ch // 2)),
                    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31)))
    fill = cv2.inpaint(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), mk, 9, cv2.INPAINT_TELEA)
    fill = cv2.resize(cv2.GaussianBlur(cv2.cvtColor(fill, cv2.COLOR_BGR2RGB), (0, 0), 5), (cw, ch), interpolation=cv2.INTER_CUBIC)
    mm = cv2.GaussianBlur(cv2.resize(mk, (cw, ch)).astype(np.float32) / 255, (0, 0), 6)[..., None]
    bg = (a * (1 - mm) + fill * mm).astype(np.uint8)
    alpha = cv2.GaussianBlur(m, (0, 0), 1.2)[..., None]

    n = max(2, int(round(dur * fps)))
    sx = {"right": 1, "left": -1}.get(dirn, 0)
    proc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
                             "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", str(out)],
                            stdin=subprocess.PIPE)
    cx0, cy0 = cw / 2, ch / 2

    def warp(im, s, dx, dy, flags=cv2.INTER_LINEAR):
        A = np.float32([[s, 0, (1 - s) * cx0 + dx], [0, s, (1 - s) * cy0 + dy]])
        return cv2.warpAffine(im, A, (cw, ch), flags=flags, borderMode=cv2.BORDER_REFLECT)

    for i in range(n):
        u = i / (n - 1)
        e = u * u * (3 - 2 * u) * 0.6 + u * 0.4
        b = warp(bg, 1.0 + 0.05 * amount * e, -sx * 0.018 * W * amount * e, 0).astype(np.float32)
        f = warp(a, 1.0 + 0.13 * amount * e, sx * 0.03 * W * amount * e, -0.01 * H * amount * e).astype(np.float32)
        al = warp(alpha, 1.0 + 0.13 * amount * e, sx * 0.03 * W * amount * e, -0.01 * H * amount * e)[..., None]
        fr = b * (1 - al) + f * al
        y0, x0 = (ch - H) // 2, (cw - W) // 2
        proc.stdin.write(fr[y0:y0 + H, x0:x0 + W].astype(np.uint8).tobytes())
    proc.stdin.close()
    proc.wait()
    return out
