"""Make several voice recordings sound like ONE voice: same tone (auto EQ matched to a reference), same loudness,
same compression and a shared light "room", so a phone take of the presenter and a studio voice-over blend.

    python voice_match.py --ref vo.wav --out-dir edited/voice  vo.wav mc_take1.wav mc_take2.wav
      -> edited/voice/<name>_matched.wav for every input (the reference gets the shared polish only)

How: average magnitude spectrum over voiced frames in 14 bands (100 Hz–12 kHz), difference to the reference,
scaled by --strength (0.75) and clamped to ±5 dB -> ffmpeg equalizer chain; then compressor, light room, loudnorm (two-pass) to -16 LUFS.
Inputs should already be denoised (e.g. afftdn) — matching amplifies whatever is there.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FFMPEG  # noqa: E402

SR = 48000
BANDS = [100, 160, 250, 400, 630, 1000, 1600, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12000]
POLISH = ("acompressor=threshold=-20dB:ratio=2.5:attack=6:release=90:makeup=1.5,"
          "aecho=0.85:0.5:24|41:0.06|0.035")   # shared tiny room so different recordings feel like one space


def load(p: Path) -> np.ndarray:
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def band_profile(x: np.ndarray) -> np.ndarray:
    n = 4096
    hop = n // 2
    win = np.hanning(n)
    frames = [x[i:i + n] * win for i in range(0, max(1, len(x) - n), hop)]
    if not frames:
        return np.zeros(len(BANDS) - 1)
    F = np.array(frames)
    rms = np.sqrt((F ** 2).mean(axis=1))
    voiced = F[rms > np.percentile(rms, 60)]          # loudest 40 % of frames = speech, not room noise
    mag = np.abs(np.fft.rfft(voiced, axis=1)).mean(axis=0) + 1e-9
    freqs = np.fft.rfftfreq(n, 1 / SR)
    prof = []
    for lo, hi in zip(BANDS, BANDS[1:]):
        sel = (freqs >= lo) & (freqs < hi)
        prof.append(20 * np.log10(mag[sel].mean()))
    prof = np.array(prof)
    return prof - prof.mean()                          # shape only, loudness is handled by loudnorm


def eq_chain(target: np.ndarray, ref: np.ndarray, limit: float = 5.0, strength: float = 0.75) -> str:
    diff = (ref - target) * strength   # partial match: full matching also boosts the hiss of a distant phone mic
    diff = np.convolve(diff, [0.25, 0.5, 0.25], mode="same")    # smooth so we fix tone, not formants
    diff = np.clip(diff, -limit, limit)
    parts = []
    for (lo, hi), g in zip(zip(BANDS, BANDS[1:]), diff):
        if abs(g) < 0.6:
            continue
        fc = (lo * hi) ** 0.5
        parts.append(f"equalizer=f={fc:.0f}:t=o:w=0.9:g={g:.1f}")
    return ",".join(parts)


def loudnorm(src: Path, dst: Path, pre: str, lufs: float) -> None:
    chain = (pre + "," if pre else "") + POLISH
    r = subprocess.run([FFMPEG, "-hide_banner", "-i", str(src), "-af", f"{chain},loudnorm=I={lufs}:TP=-1.5:LRA=7:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    j = json.loads(r.stderr[r.stderr.rfind("{"):r.stderr.rfind("}") + 1])
    second = (f"loudnorm=I={lufs}:TP=-1.5:LRA=7:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
              f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-af", f"{chain},{second}", "-ar", str(SR), "-ac", "1", str(dst)], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--ref", required=True, help="the voice everyone should sound like (usually the voice-over)")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--lufs", type=float, default=-16.0)
    a = ap.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ref_prof = band_profile(load(Path(a.ref)))
    for p in map(Path, a.inputs):
        same = p.resolve() == Path(a.ref).resolve()
        eq = "" if same else eq_chain(band_profile(load(p)), ref_prof)
        dst = out / f"{p.stem}_matched.wav"
        loudnorm(p, dst, eq, a.lufs)
        print(f"{p.name}: {'reference' if same else str(eq.count('equalizer')) + ' EQ bands'} -> {dst.name}")
        if eq:
            print("   ", eq.replace("equalizer=", "").replace(":t=o:w=0.9", ""))


if __name__ == "__main__":
    main()
