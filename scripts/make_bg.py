"""Animated motion-graphics background for text/news videos (no stock footage needed).

Usage:
  python make_bg.py -o bg.mp4 --duration 60 [--theme cold|warm|news|dark|green] [--size 1080x1920] [--fps 30]
                     [--particles snow|dust|rain|none]

Soft vertical gradient + slowly drifting light blobs + optional falling particles + vignette.
Rendered with numpy and piped into ffmpeg; use it as a clip in a plan and put titles/cards on top.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG, video_codec_args  # noqa: E402

THEMES = {  # top colour, bottom colour, blob colours (RGB 0-255)
    "cold": ((10, 22, 48), (8, 70, 110), [(90, 170, 255), (120, 230, 255), (60, 110, 220)]),
    "warm": ((40, 12, 8), (120, 52, 10), [(255, 160, 60), (255, 90, 40), (255, 210, 120)]),
    "news": ((12, 12, 18), (70, 10, 18), [(230, 40, 60), (255, 120, 80), (90, 90, 140)]),
    "dark": ((8, 8, 12), (28, 28, 40), [(245, 197, 66), (120, 120, 160), (80, 80, 110)]),
    "green": ((6, 28, 22), (10, 80, 60), [(80, 220, 160), (180, 255, 200), (40, 140, 110)]),
}


def soft_disc(r: int) -> np.ndarray:
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.sqrt(x * x + y * y) / r
    return np.clip(1 - d, 0, 1) ** 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--theme", default="dark", choices=list(THEMES))
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--particles", default="none", choices=["snow", "dust", "rain", "none"])
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()

    W, H = map(int, a.size.split("x"))
    # render at half resolution (soft content) and let ffmpeg upscale: 4x faster
    w, h = W // 2, H // 2
    rng = np.random.default_rng(a.seed)
    top, bottom, blob_cols = THEMES[a.theme]
    t = np.linspace(0, 1, h)[:, None, None]
    base = (np.array(top) * (1 - t) + np.array(bottom) * t).astype(np.float32) * np.ones((1, w, 1), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    vign = 1 - 0.55 * (((xx - w / 2) / (w / 2)) ** 2 * 0.6 + ((yy - h / 2) / (h / 2)) ** 2 * 0.4)
    vign = np.clip(vign, 0.35, 1)[:, :, None].astype(np.float32)

    R = int(w * 0.55)
    blob = soft_disc(R).astype(np.float32)[:, :, None]
    blobs = [{"c": np.array(c, np.float32), "x0": rng.uniform(0.1, 0.9) * w, "y0": rng.uniform(0.1, 0.9) * h,
              "ax": rng.uniform(0.15, 0.3) * w, "ay": rng.uniform(0.1, 0.2) * h, "sp": rng.uniform(0.05, 0.12),
              "ph": rng.uniform(0, 6.28), "a": rng.uniform(0.28, 0.42)} for c in blob_cols]

    n = {"snow": 140, "dust": 70, "rain": 160, "none": 0}[a.particles]
    px, py = rng.uniform(0, w, n), rng.uniform(0, h, n)
    pr = rng.integers(1, 5, n)
    pv = rng.uniform(0.6, 1.8, n) * (6 if a.particles == "rain" else 1)
    pa = rng.uniform(0.35, 0.9, n)
    sprites = {r: soft_disc(r + 1).astype(np.float32) for r in range(1, 5)}

    frames = int(a.duration * a.fps)
    cmd = [FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{w}x{h}", "-r", str(a.fps), "-i", "-", "-vf", f"scale={W}:{H}:flags=bicubic,format=yuv420p",
           *video_codec_args("high"), "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           a.out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(frames):
        sec = f / a.fps
        img = base.copy()
        for b in blobs:
            cx = b["x0"] + b["ax"] * np.sin(sec * b["sp"] * 2 * np.pi + b["ph"])
            cy = b["y0"] + b["ay"] * np.cos(sec * b["sp"] * 1.6 * np.pi + b["ph"])
            x0, y0 = int(cx - R), int(cy - R)
            xa, ya, xb, yb = max(0, x0), max(0, y0), min(w, x0 + 2 * R + 1), min(h, y0 + 2 * R + 1)
            if xa < xb and ya < yb:
                sub = blob[ya - y0:yb - y0, xa - x0:xb - x0]
                img[ya:yb, xa:xb] += sub * (b["c"] - img[ya:yb, xa:xb]) * b["a"]
        if n:
            py[:] = (py + pv * (60 / a.fps) * 0.5) % h
            drift = np.sin(sec * 0.8 + px * 0.01) * (0.6 if a.particles == "snow" else 0.15)
            for i in range(n):
                s = sprites[int(pr[i])]
                r = s.shape[0] // 2
                x, y = int(px[i] + drift[i]) % w, int(py[i])
                if r <= x < w - r and r <= y < h - r:
                    img[y - r:y + r + 1, x - r:x + r + 1] += s[:, :, None] * 255 * pa[i] * 0.85
        img = np.clip(img * vign, 0, 255).astype(np.uint8)
        p.stdin.write(img.tobytes())
    p.stdin.close()
    p.wait()
    print(f"[bg] {a.theme}/{a.particles} {a.duration}s -> {a.out}")


if __name__ == "__main__":
    main()
