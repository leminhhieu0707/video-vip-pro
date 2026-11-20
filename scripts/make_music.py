"""Royalty-free background bed generator (soft chord pad + light pulse), for when no music file is available.

Usage:  python make_music.py -o bed.wav --duration 65 [--mood news|calm|upbeat] [--bpm 100]
Keep it low in the mix (volume 0.08-0.15 with duck). Real music files sound better; this is a safe fallback.
"""
from __future__ import annotations

import argparse
import wave

import numpy as np

SR = 44100
MOODS = {  # chord roots (MIDI) and quality, bpm, pulse on/off
    "news": ([57, 53, 48, 55], 100, True),    # Am F C G
    "calm": ([48, 55, 57, 53], 76, False),    # C G Am F
    "upbeat": ([50, 57, 59, 55], 118, True),  # D A Bm G
}
MINOR = {57, 59, 50 + 12}


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    from scipy.signal import lfilter  # noqa: F401  (optional)
    return lfilter([1 - a], [1, -a], x)


def onepole(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    # vectorised in blocks is overkill here; a simple loop over ~3M samples is ~2 s
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--mood", default="news", choices=list(MOODS))
    ap.add_argument("--bpm", type=float)
    a = ap.parse_args()
    roots, bpm, pulse = MOODS[a.mood]
    bpm = a.bpm or bpm
    beat = 60 / bpm
    bar = beat * 4
    n = int(a.duration * SR)
    t = np.arange(n) / SR
    pad = np.zeros(n)
    rng = np.random.default_rng(1)
    for k in range(int(a.duration / bar) + 1):
        root = roots[k % len(roots)]
        third = 3 if root in (57, 59, 62) else 4
        notes = [root, root + third, root + 7, root + 12]
        s0, s1 = int(k * bar * SR), min(n, int((k + 1) * bar * SR + 0.6 * SR))
        if s0 >= n:
            break
        tt = t[s0:s1] - k * bar
        env = np.minimum(1, tt / 0.6) * np.exp(-0.25 * tt)
        env *= np.clip((bar + 0.6 - tt) / 0.6, 0, 1)
        for j, m in enumerate(notes):
            f = midi(m)
            det = 1 + (j - 1.5) * 0.002
            pad[s0:s1] += env * (np.sin(2 * np.pi * f * det * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * 0.18
        # soft bass
        pad[s0:s1] += env * np.sin(2 * np.pi * midi(root - 12) * tt) * 0.25
    pad = onepole(pad, 2500)
    if pulse:
        for b in range(int(a.duration / beat)):
            s0 = int(b * beat * SR)
            L = int(0.18 * SR)
            if s0 + L > n:
                break
            tt = np.arange(L) / SR
            kick = np.sin(2 * np.pi * (55 + 90 * np.exp(-30 * tt)) * tt) * np.exp(-14 * tt) * (0.5 if b % 2 == 0 else 0.25)
            pad[s0:s0 + L] += kick
            h0 = s0 + int(beat / 2 * SR)
            hl = int(0.05 * SR)
            if h0 + hl < n:
                hat = rng.standard_normal(hl) * np.exp(-60 * np.arange(hl) / SR) * 0.06
                pad[h0:h0 + hl] += np.diff(np.concatenate([[0], hat]))
    fade = int(1.5 * SR)
    pad[:fade] *= np.linspace(0, 1, fade)
    pad[-fade:] *= np.linspace(1, 0, fade)
    pad = pad / (np.max(np.abs(pad)) + 1e-9) * 0.8
    st = np.stack([pad, np.roll(pad, int(0.012 * SR))], axis=1)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype("<i2").tobytes())
    print(f"[music] {a.mood} {bpm:.0f}bpm {a.duration}s -> {a.out}")


if __name__ == "__main__":
    main()
