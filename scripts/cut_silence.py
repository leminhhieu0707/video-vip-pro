"""Find the parts of a talking video worth keeping (jump-cut out silences / dead air / retakes).

Usage:
  python cut_silence.py INPUT [--transcript X.transcript.json] [--pad 0.12] [--min-gap 0.35]
                              [--remove 12.3-15.0 --remove 40-41.2] [--db -35] [-o cuts.json]

With a transcript, cuts follow word timings (most accurate). Without one, uses ffmpeg silencedetect.
Writes a JSON list of clips [{"src","in","out"}...] ready to paste into a plan's "clips",
and prints how much time is removed.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG, load_json, parse_time, probe, save_json  # noqa: E402


def speech_from_transcript(tr: dict) -> list[list[float]]:
    ranges = []
    for seg in tr["segments"]:
        ws = seg.get("words") or [{"start": seg["start"], "end": seg["end"]}]
        for w in ws:
            ranges.append([w["start"], w["end"]])
    return ranges


def speech_from_audio(src: Path, db: float, min_sil: float, duration: float) -> list[list[float]]:
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", str(src), "-vn", "-af", f"silencedetect=n={db}dB:d={min_sil}",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    speech, cur = [], 0.0
    for i, s in enumerate(starts):
        if s > cur:
            speech.append([cur, s])
        cur = ends[i] if i < len(ends) else duration
    if cur < duration:
        speech.append([cur, duration])
    return speech


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--transcript")
    ap.add_argument("--pad", type=float, default=0.12, help="seconds kept before/after speech")
    ap.add_argument("--min-gap", type=float, default=0.35, help="pauses shorter than this are kept")
    ap.add_argument("--min-clip", type=float, default=0.4, help="drop kept pieces shorter than this")
    ap.add_argument("--db", type=float, default=-35)
    ap.add_argument("--remove", action="append", default=[], help="extra range to drop, e.g. 12.3-15 (retakes)")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    src = Path(a.input).resolve()
    dur = probe(src)["duration"]
    if a.transcript:
        speech = speech_from_transcript(load_json(a.transcript))
    else:
        speech = speech_from_audio(src, a.db, a.min_gap, dur)

    # pad, merge across small gaps
    keep: list[list[float]] = []
    for s, e in sorted(speech):
        s, e = max(0.0, s - a.pad), min(dur, e + a.pad)
        if keep and s - keep[-1][1] <= a.min_gap:
            keep[-1][1] = max(keep[-1][1], e)
        else:
            keep.append([s, e])

    for r in a.remove:
        rs, re_ = (parse_time(x) for x in r.split("-", 1))
        nxt = []
        for s, e in keep:
            if re_ <= s or rs >= e:
                nxt.append([s, e])
                continue
            if s < rs:
                nxt.append([s, rs])
            if re_ < e:
                nxt.append([re_, e])
        keep = nxt

    keep = [[round(s, 3), round(e, 3)] for s, e in keep if e - s >= a.min_clip]
    clips = [{"src": str(src), "in": s, "out": e} for s, e in keep]
    out = Path(a.out) if a.out else src.with_name(src.stem + ".cuts.json")
    save_json(clips, out)
    kept = sum(e - s for s, e in keep)
    print(f"[cut] {len(clips)} pieces, kept {kept:.1f}s of {dur:.1f}s (removed {dur - kept:.1f}s) -> {out}")


if __name__ == "__main__":
    main()
