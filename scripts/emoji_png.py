"""Render color emoji (Windows Segoe UI Emoji) to transparent PNG icons for image overlays.

Usage:  python emoji_png.py OUT_DIR snow=❄️ rain=🌧️ warn=⚠️ ...   [--size 512]
Then use {"type":"image","src":"OUT_DIR/snow.png","width":0.2,...} in a plan. Icons are free to use (system font).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def render(ch: str, size: int) -> Image.Image:
    font = ImageFont.truetype(r"C:\Windows\Fonts\seguiemj.ttf", 109)  # 109 px = native size of the color glyphs
    canvas = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(canvas).text((200, 200), ch, font=font, anchor="mm", embedded_color=True)
    canvas = canvas.crop(canvas.getbbox())
    scale = size / max(canvas.size)
    return canvas.resize((round(canvas.width * scale), round(canvas.height * scale)), Image.LANCZOS)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    size = int(sys.argv[sys.argv.index("--size") + 1]) if "--size" in sys.argv else 512
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    for spec in args[1:]:
        if spec.isdigit():
            continue
        name, ch = spec.split("=", 1)
        render(ch, size).save(out / f"{name}.png")
        print(out / f"{name}.png")


if __name__ == "__main__":
    main()
