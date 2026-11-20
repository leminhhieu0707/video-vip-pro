"""Detect beats / strong hits in a music track so cuts can land on the beat.

Usage:
  python beats.py MUSIC [--start 0] [--end 60] [--every 1] [-o beats.json]

Prints estimated BPM and beat times; --every N keeps every Nth beat (e.g. 2 = cut every other beat).
Output JSON: {"bpm":..., "beats":[...], "downbeats":[...], "strong":[...]}  (seconds)
  beats     - regular grid aligned to the detected tempo
  downbeats - every 4th beat (bar starts), good for scene changes
  strong    - the loudest onsets (drops, hits), good for flashes / zooms / title pops
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG, save_json  # noqa: E402

SR = 22050
HOP = 512


def load(path: str, start: float, end: float | None) -> np.ndarray:
    cmd = [FFMPEG, "-nostdin", "-v", "error", "-ss", str(start)]
    if end:
        cmd += ["-to", str(end)]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    p = subprocess.run(cmd, capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def onset_envelope(y: np.ndarray) -> np.ndarray:
    n_fft = 2048
    win = np.hanning(n_fft).astype(np.float32)
    frames = 1 + (len(y) - n_fft) // HOP
    if frames <= 0:
        return np.zeros(1)
    idx = np.arange(n_fft)[None, :] + HOP * np.arange(frames)[:, None]
    spec = np.abs(np.fft.rfft(y[idx] * win, axis=1))
    spec = np.log1p(100 * spec)
    flux = np.maximum(0, np.diff(spec, axis=0)).sum(axis=1)
    flux = np.concatenate([[0], flux])
    flux -= np.convolve(flux, np.ones(16) / 16, mode="same")  # remove slow trend
    flux = np.maximum(flux, 0)
    return flux / (flux.max() + 1e-9)


def tempo(env: np.ndarray, fps: float) -> float:
    ac = np.correlate(env, env, mode="full")[len(env) - 1:]
    lo, hi = int(fps * 60 / 180), int(fps * 60 / 70)  # 70..180 BPM
    lag = lo + int(np.argmax(ac[lo:hi]))
    return 60 * fps / lag


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("music")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--end", type=float)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("-o", "--out")
    a = ap.parse_args()

    y = load(a.music, a.start, a.end)
    fps = SR / HOP
    env = onset_envelope(y)
    bpm = tempo(env, fps)
    period = fps * 60 / bpm
    # choose phase that maximizes onset energy on the grid
    best, phase = -1, 0
    for ph in range(int(period)):
        pos = np.arange(ph, len(env), period).astype(int)
        sc = env[pos].sum()
        if sc > best:
            best, phase = sc, ph
    grid = np.arange(phase, len(env), period)
    # snap each grid point to the nearest onset peak within ±60ms
    snap = int(0.06 * fps)
    beats = []
    for g in grid.astype(int):
        lo, hi = max(0, g - snap), min(len(env), g + snap + 1)
        beats.append(float((lo + int(np.argmax(env[lo:hi]))) / fps + a.start))
    beats = [round(b, 3) for b in beats][:: max(1, a.every)]
    # strongest onsets: local maxima in top 8%
    thr = np.quantile(env, 0.92)
    peaks = [i for i in range(1, len(env) - 1) if env[i] >= thr and env[i] >= env[i - 1] and env[i] >= env[i + 1]]
    strong, last = [], -1e9
    for i in peaks:
        t = i / fps + a.start
        if t - last > 0.25:
            strong.append(round(float(t), 3))
            last = t
    res = {"bpm": round(float(bpm), 1), "beat_interval": round(float(60 / bpm), 3), "beats": beats,
           "downbeats": beats[:: 4 // max(1, a.every) or 1], "strong": strong}
    out = Path(a.out) if a.out else Path(a.music).with_suffix(".beats.json")
    save_json(res, out)
    print(f"[beats] ~{res['bpm']} BPM, {len(beats)} beats, {len(strong)} strong hits -> {out}")
    print("first beats:", beats[:12])


if __name__ == "__main__":
    main()
