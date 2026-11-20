"""Look at a video before editing: metadata, timestamped contact sheets, scene cuts, silences, loudness.

Usage:
  python analyze.py INPUT [-o OUT_DIR] [--every 2] [--cols 4] [--rows 2] [--scene 0.3] [--silence-db -35]

Outputs in OUT_DIR (default: <input>_analysis/):
  sheet_01.jpg ...   grids of frames with the timestamp burned in (Read these images to "watch" the video)
  analysis.json      metadata + scene cut times + silence ranges + loudness
For a single moment, use:  python analyze.py INPUT --frame 12.5   (writes frame_12.50.jpg)
"""
from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG, find_font, probe, run, save_json  # noqa: E402


def font_for_drawtext() -> str:
    _, f = find_font("Arial Bold")
    p = str(f or r"C:\Windows\Fonts\arial.ttf").replace("\\", "/")
    return p.replace(":", "\\:")


def contact_sheets(src: Path, out: Path, info: dict, every: float, cols: int, rows: int) -> list[str]:
    per = cols * rows
    n_frames = max(1, int(math.ceil(info["duration"] / every)))
    n_sheets = int(math.ceil(n_frames / per))
    portrait = info.get("height", 1) >= info.get("width", 1)
    tile_w = 300 if portrait else 480
    font = font_for_drawtext()
    vf = (f"fps=1/{every},scale={tile_w}:-2,"
          f"drawtext=fontfile='{font}':text='%{{pts\\:hms}}':x=6:y=6:fontsize={int(tile_w / 13)}:"
          f"fontcolor=yellow:box=1:boxcolor=black@0.65:boxborderw=4,tile={cols}x{rows}:padding=4:color=black")
    run([FFMPEG, "-y", "-i", str(src), "-vf", vf, "-frames:v", str(n_sheets), "-q:v", "3",
         str(out / "sheet_%02d.jpg")])
    return sorted(str(p) for p in out.glob("sheet_*.jpg"))


def scene_cuts(src: Path, threshold: float) -> list[float]:
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", str(src), "-vf", f"select='gt(scene,{threshold})',showinfo",
                        "-an", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [round(float(m), 2) for m in re.findall(r"pts_time:([\d.]+)", p.stderr)]


def audio_stats(src: Path, db: float, min_dur: float) -> dict:
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", str(src), "-vn", "-af",
                        f"silencedetect=n={db}dB:d={min_dur},ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    err = p.stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    silences = [[round(s, 2), round(e, 2)] for s, e in zip(starts, ends + [None] * (len(starts) - len(ends))) if e]
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    return {"silences": silences, "integrated_lufs": float(lufs[-1]) if lufs else None,
            "true_peak_dbfs": float(peak[-1]) if peak else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--out", help="output FOLDER (default <input>_analysis/)")
    ap.add_argument("--every", type=float, default=None, help="seconds between frames (auto: ~32 frames total)")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=2)
    ap.add_argument("--scene", type=float, default=0.3)
    ap.add_argument("--silence-db", type=float, default=-35)
    ap.add_argument("--silence-min", type=float, default=0.4)
    ap.add_argument("--frame", type=float, default=None, help="only grab one full-size frame at this time")
    a = ap.parse_args()

    src = Path(a.input)
    out = Path(a.out) if a.out else src.with_name(src.stem + "_analysis")
    out.mkdir(parents=True, exist_ok=True)
    info = probe(src)

    if a.frame is not None:
        f = out / f"frame_{a.frame:.2f}.jpg"
        run([FFMPEG, "-y", "-ss", str(a.frame), "-i", str(src), "-frames:v", "1", "-q:v", "2", str(f)])
        print(f)
        return

    if info.get("is_image"):
        print(info)
        return
    every = a.every or max(0.5, round(info["duration"] / 32, 1))
    for old in out.glob("sheet_*.jpg"):
        old.unlink()
    sheets = contact_sheets(src, out, info, every, a.cols, a.rows) if info.get("has_video") else []
    result = {"info": info, "frame_every_s": every, "sheets": sheets,
              "scene_cuts": scene_cuts(src, a.scene) if info.get("has_video") else []}
    if info.get("has_audio"):
        result.update(audio_stats(src, a.silence_db, a.silence_min))
    save_json(result, out / "analysis.json")

    i = info
    print(f"{src.name}: {i.get('width')}x{i.get('height')} {i.get('fps')}fps {i['duration']:.2f}s "
          f"audio={'yes' if i['has_audio'] else 'no'} {i['size_mb']}MB")
    print(f"scene cuts: {result['scene_cuts']}")
    if "silences" in result:
        print(f"silences (>{a.silence_min}s @ {a.silence_db}dB): {result['silences']}")
        print(f"loudness: {result['integrated_lufs']} LUFS, peak {result['true_peak_dbfs']} dBFS")
    print(f"contact sheets ({every}s/frame): ")
    for s in sheets:
        print("  " + s)


if __name__ == "__main__":
    main()
