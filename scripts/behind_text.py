"""Big text BEHIND the person (CapCut "text behind subject"), rendered into a new clip you then use in plan.json.

Every frame is cut out with rembg (u2net, local), the text layer is drawn between background and person,
and the source audio is kept. Output is already canvas-sized, so use it with "fit": "crop" and no punch.

  python behind_text.py SRC -o hook.mp4 --in 0.2 --out 3.6 --lines "BẢO HÀNH" "VIP"
  python behind_text.py SRC -o hook.mp4 --in 0 --out 3 --lines "GIÁ SỐC" --style pop --colors "#FFFFFF"

Styles:
  marquee  each line scrolls sideways, alternate lines in opposite directions (default)
  pop      lines scale in one after another and stay
  static   lines sit still with a quick fade-in
Options: --size (px, default auto-fit), --font, --colors (one per line, hex), --stroke "#0A52DC",
         --y (line block centre, fraction of height, default 0.33), --focus (crop centre 0..1),
         --keep-bottom 0.0..1 (rows below this fraction always stay in front, e.g. a table: 0.78)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG, find_font, parse_time, probe  # noqa: E402

DEFAULT_FONT = "Be Vietnam Pro ExtraBold"


def text_layer(W, H, lines, font_path, size, colors, stroke, stroke_w, style, t, dur, y_c, shadow=True):
    """RGBA layer with the lines at time t."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    font = ImageFont.truetype(str(font_path), size)
    gap = int(size * 0.02)
    heights = [font.getbbox(s)[3] - font.getbbox(s)[1] for s in lines]
    total = sum(heights) + gap * (len(lines) - 1)
    y = int(H * y_c - total / 2)
    for i, (s, h) in enumerate(zip(lines, heights)):
        bb = font.getbbox(s)
        tw = bb[2] - bb[0]
        col = colors[i % len(colors)]
        alpha = 1.0
        scale = 1.0
        if style == "marquee":
            # endless ticker: the line repeats with a dot separator and slides at constant speed
            unit = s + "  •  "
            ub = font.getbbox(unit)
            uw = ub[2] - ub[0]
            reps = int(W / max(uw, 1)) + 3
            s = unit * reps
            bb = font.getbbox(s)
            tw = bb[2] - bb[0]
            speed = W * 0.28  # px per second
            sign = -1 if i % 2 == 0 else 1
            off = (speed * t) % uw
            x = -uw + (-off if sign < 0 else off - uw * 0)
            alpha = min(1.0, t / 0.25)
        else:
            x = (W - tw) / 2
            start = 0.12 + i * 0.22 if style == "pop" else 0.0
            k = min(1.0, max(0.0, (t - start) / 0.22))
            alpha = k
            if style == "pop":
                scale = 0.6 + 0.4 * (1 - (1 - k) ** 3) + 0.06 * np.sin(np.pi * k)
        if alpha <= 0:
            y += h + gap
            continue
        tile = Image.new("RGBA", (int(tw + stroke_w * 4 + 40), int(h + stroke_w * 4 + 60)), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        ox, oy = stroke_w * 2 + 20 - bb[0], stroke_w * 2 + 20 - bb[1]
        td.text((ox, oy), s, font=font, fill=col, stroke_width=stroke_w, stroke_fill=stroke)
        if scale != 1.0:
            tile = tile.resize((max(1, int(tile.width * scale)), max(1, int(tile.height * scale))), Image.LANCZOS)
        if alpha < 1:
            a = tile.getchannel("A").point(lambda v: int(v * alpha))
            tile.putalpha(a)
        px = int(x + tw / 2 - tile.width / 2)
        py = int(y + h / 2 - tile.height / 2)
        if shadow:
            sh = Image.new("RGBA", tile.size, (0, 0, 0, 0))
            sh.putalpha(tile.getchannel("A").point(lambda v: int(v * 0.45)))
            sh = sh.filter(ImageFilter.GaussianBlur(14))
            layer.alpha_composite(sh, (px + 6, py + 14))
        layer.alpha_composite(tile, (px, py))
        y += h + gap
    return layer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--in", dest="tin", default="0")
    ap.add_argument("--out-time", "--to", dest="tout", default=None)
    ap.add_argument("--lines", nargs="+", required=True)
    ap.add_argument("--style", default="marquee", choices=["marquee", "pop", "static"])
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--size", type=int, default=0)
    ap.add_argument("--colors", nargs="+", default=["#FFFFFF", "#05E1DB"])
    ap.add_argument("--stroke", default="#0A2F9E")
    ap.add_argument("--stroke-width", type=int, default=0)
    ap.add_argument("--y", type=float, default=0.42)
    ap.add_argument("--focus", type=float, default=0.5)
    ap.add_argument("--keep-bottom", type=float, default=1.0)
    ap.add_argument("--w", type=int, default=1080)
    ap.add_argument("--h", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--model", default="u2net")
    a = ap.parse_args()

    W, H, fps = a.w, a.h, a.fps
    info = probe(a.src)
    tin = parse_time(a.tin)
    tout = parse_time(a.tout) if a.tout else info["duration"]
    dur = tout - tin
    _, font_path = find_font(a.font)
    if font_path is None:
        sys.exit(f"font not found: {a.font}")
    # auto size: the longest line fills ~92% of the width (marquee lets long lines overflow on purpose)
    size = a.size
    if not size:
        probe_f = ImageFont.truetype(str(font_path), 200)
        longest = max(probe_f.getbbox(s)[2] - probe_f.getbbox(s)[0] for s in a.lines)
        size = int(200 * W * 0.92 / max(longest, 1))
        size = min(size, int(H * 0.22))
        if a.style == "marquee":
            size = max(size, int(H * 0.15))
    stroke_w = a.stroke_width or max(4, size // 28)

    # crop to canvas like render.py's fit=crop, HDR-safe via tonemapping when needed
    sw, sh = info["width"], info["height"]
    scale = max(W / sw, H / sh)
    nw, nh = int(round(sw * scale / 2) * 2), int(round(sh * scale / 2) * 2)
    cx = int((nw - W) * a.focus)
    cy = int((nh - H) * 0.5)
    vf = f"fps={fps},scale={nw}:{nh}:flags=lanczos,crop={W}:{H}:{cx}:{cy},format=rgb24"
    if info.get("is_hdr"):
        tr = "arib-std-b67" if info.get("color_transfer") == "arib-std-b67" else "smpte2084"
        vf = (f"zscale=tin={tr}:min=bt2020nc:pin=bt2020:t=linear:npl=150,format=gbrpf32le,zscale=p=bt709,"
              f"tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,"
              f"eq=contrast=1.12:gamma=0.92:saturation=1.08," + vf)
    reader = subprocess.Popen([FFMPEG, "-v", "error", "-ss", f"{tin:.3f}", "-to", f"{tout:.3f}", "-i", a.src,
                               "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    out = Path(a.out)
    writer = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(fps), "-i", "-", "-ss", f"{tin:.3f}", "-to", f"{tout:.3f}", "-i", a.src,
                               "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
                               "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)],
                              stdin=subprocess.PIPE)

    from rembg import new_session
    sess = new_session(a.model)
    prev = None
    n = 0
    fsz = W * H * 3
    while True:
        buf = reader.stdout.read(fsz)
        if len(buf) < fsz:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        img = Image.fromarray(frame)
        small = img.resize((W // 3, H // 3), Image.BILINEAR)
        m = sess.predict(small)[0].resize((W, H), Image.BILINEAR)
        mask = np.asarray(m, np.float32) / 255.0
        # firm up the matte, then smooth over time so hair edges do not flicker
        mask = np.clip((mask - 0.25) / 0.5, 0, 1)
        if prev is not None:
            mask = 0.6 * mask + 0.4 * prev
        prev = mask
        if a.keep_bottom < 1.0:
            mask[int(H * a.keep_bottom):, :] = 1.0
        t = n / fps
        layer = text_layer(W, H, a.lines, font_path, size, a.colors, a.stroke, stroke_w, a.style, t, dur, a.y)
        base = img.convert("RGBA")
        base.alpha_composite(layer)
        comp = np.asarray(base.convert("RGB"), np.float32)
        m3 = mask[..., None]
        res = comp * (1 - m3) + frame.astype(np.float32) * m3
        writer.stdin.write(res.astype(np.uint8).tobytes())
        n += 1
        if n % 30 == 0:
            print(f"  {n} frames", flush=True)
    writer.stdin.close()
    writer.wait()
    reader.wait()
    print(f"wrote {out} ({n} frames, {n / fps:.2f}s), text size {size}px")


if __name__ == "__main__":
    main()
