"""Audition video of every sound effect in the skill: a numbered card per sound (group · family · name), then the sound.
    python sfx_preview.py -o sfx_preview.mp4        -> also writes sfx_preview.json (number -> file)
Groups: VIRAL (synthesized tech set) · TREND (Mixkit pack from get_sfx.py, if installed) · CƠ BẢN (synthesized basics).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FFMPEG, probe  # noqa: E402

SFX = Path(__file__).resolve().parent.parent / "assets" / "sfx"
FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "BeVietnamPro-Bold.ttf"
VI = {"data": "bíp dữ liệu", "charge": "sạc flash rít lên", "click": "click", "stutter": "click dồn dập", "flash": "đèn flash",
      "flicker": "nhấp nháy rè", "popup": "bật lên", "cutout": "cắt người ra", "dwhoosh": "lướt số", "thump": "bùm trầm",
      "whoosh": "lướt", "boom": "bùm", "hit": "đấm / va", "pop": "pop", "sparkle": "lấp lánh", "bling": "bling", "ding": "ding",
      "riser": "kéo lên", "glitch": "glitch", "camera": "chụp ảnh", "typing": "gõ phím", "cash": "tiền", "drumroll": "trống dồn",
      "swipe": "quẹt", "game": "game", "laugh": "cười", "applause": "vỗ tay", "cartoon": "hoạt hình", "crunch": "giòn rụm",
      "pour": "rót nước"}
GROUP_COLOR = {"VIRAL": (49, 88, 255), "TREND": (232, 184, 74), "CƠ BẢN": (90, 98, 120)}


def collect():
    items = []
    for f in sorted(SFX.glob("viral_*.wav")):
        fam = f.stem.split("_")[1]
        items.append(("VIRAL", fam, f.stem, f))
    idx = SFX / "pack" / "index.json"
    if idx.exists():
        for fam, files in json.loads(idx.read_text(encoding="utf-8")).items():
            for x in files:
                p = SFX / "pack" / x["file"]
                if p.exists():
                    items.append(("TREND", fam, x["title"], p))
    for f in sorted(SFX.glob("*.wav")):
        if not f.stem.startswith("viral_"):
            items.append(("CƠ BẢN", f.stem.rstrip("0123456789_"), f.stem, f))
    return items


def card(path: Path, n: int, total: int, group: str, fam: str, name: str):
    W = H = 720
    im = Image.new("RGB", (W, H), (14, 16, 26))
    d = ImageDraw.Draw(im)
    big, mid, small = ImageFont.truetype(str(FONT), 150), ImageFont.truetype(str(FONT), 46), ImageFont.truetype(str(FONT), 30)
    col = GROUP_COLOR[group]
    d.rounded_rectangle((40, 40, 40 + d.textlength(group, font=small) + 40, 92), 24, fill=col)
    d.text((60, 48), group, font=small, fill=(255, 255, 255))
    d.text((W - 40, 52), f"{n}/{total}", font=small, fill=(140, 150, 180), anchor="ra")
    d.text((W / 2, 300), f"#{n}", font=big, fill=(255, 255, 255), anchor="mm")
    d.text((W / 2, 450), f"{fam} · {VI.get(fam, '')}", font=mid, fill=col, anchor="mm")
    nm = name if len(name) <= 34 else name[:33] + "…"
    d.text((W / 2, 520), nm, font=small, fill=(200, 205, 220), anchor="mm")
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="sfx_preview.mp4")
    a = ap.parse_args()
    out = Path(a.out).resolve()
    work = out.with_suffix("")
    work.mkdir(parents=True, exist_ok=True)
    items = collect()
    lst, index = [], {}
    for n, (group, fam, name, f) in enumerate(items, 1):
        try:
            dur = min(3.0, float(probe(f)["duration"]))
        except Exception:
            continue
        png, seg = work / f"c{n:03d}.png", work / f"s{n:03d}.mp4"
        card(png, n, len(items), group, fam, name)
        L = dur + 0.45
        subprocess.run([FFMPEG, "-v", "error", "-y", "-loop", "1", "-framerate", "10", "-i", str(png), "-i", str(f),
                        "-filter_complex", f"[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{dur:.2f},"
                        f"afade=t=out:st={max(0, dur - 0.15):.2f}:d=0.15,apad=whole_dur={L:.2f}[a]",
                        "-map", "0:v", "-map", "[a]", "-t", f"{L:.2f}", "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
                        "-pix_fmt", "yuv420p", "-r", "10", "-c:a", "aac", "-b:a", "160k", str(seg)], check=True)
        lst.append(f"file '{seg.as_posix()}'")
        index[n] = {"group": group, "family": fam, "name": name, "file": str(f)}
    (work / "list.txt").write_text("\n".join(lst), encoding="utf-8")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(work / "list.txt"), "-c", "copy", str(out)], check=True)
    out.with_suffix(".json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(index)} sounds -> {out}")


if __name__ == "__main__":
    main()
