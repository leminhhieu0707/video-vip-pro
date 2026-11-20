"""Synthesize a small royalty-free sound-effect library (no downloads needed).

Usage:  python make_sfx.py [--out DIR]     (default: <skill>/assets/sfx)

whoosh, swoosh, pop, ding, cash, click, riser, impact, sparkle, swipe, bubble, notify
Drop real .wav/.mp3 files into the same folder to extend the library; plans refer to them by file stem.
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def t_axis(d):
    return np.arange(int(SR * d)) / SR


def env_adsr(n, a=0.005, d=0.1, s=0.0, r=0.0, curve=4.0):
    t = np.arange(n) / SR
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    rest = t[na:] - a
    e[na:] = s + (1 - s) * np.exp(-curve * rest / max(d, 1e-3))
    if r:
        nr = int(r * SR)
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def bandpass_sweep(x, f0, f1, q=2.0):
    """Time-varying biquad band-pass (frequency sweeps f0 -> f1, exponential)."""
    n = len(x)
    freqs = f0 * (f1 / f0) ** (np.arange(n) / max(1, n - 1))
    y = np.zeros(n)
    x1 = x2 = y1 = y2 = 0.0
    for i in range(n):
        w = 2 * np.pi * freqs[i] / SR
        alpha = np.sin(w) / (2 * q)
        b0, b2, a0 = alpha, -alpha, 1 + alpha
        a1, a2 = -2 * np.cos(w), 1 - alpha
        yi = (b0 * x[i] + b2 * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x[i], y1, yi
        y[i] = yi
    return y


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def tone(freq, d, decay=6.0, harmonics=((1, 1.0),), chirp_to=None):
    t = t_axis(d)
    f = np.full_like(t, freq) if chirp_to is None else freq * (chirp_to / freq) ** (t / d)
    phase = 2 * np.pi * np.cumsum(f) / SR
    y = sum(a * np.sin(h * phase) for h, a in harmonics)
    return y * np.exp(-decay * t)


def norm(x, peak=0.89):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def stereo_pan_sweep(x, left_to_right=True):
    p = np.linspace(0, 1, len(x)) if left_to_right else np.linspace(1, 0, len(x))
    return np.stack([x * np.cos(p * np.pi / 2), x * np.sin(p * np.pi / 2)], axis=1)


def fx_whoosh(d=0.55):
    n = int(SR * d)
    x = bandpass_sweep(rng.standard_normal(n), 300, 4000, q=1.2)
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.6
    return stereo_pan_sweep(norm(x * e, 0.8))


def fx_swoosh(d=0.3):
    n = int(SR * d)
    x = bandpass_sweep(rng.standard_normal(n), 3000, 600, q=1.5)
    e = np.sin(np.pi * np.linspace(0, 1, n) ** 0.6) ** 2
    return stereo_pan_sweep(norm(x * e, 0.75), False)


def fx_pop():
    y = tone(900, 0.12, decay=40, chirp_to=300, harmonics=((1, 1), (2, 0.25)))
    return norm(y, 0.85)


def fx_bubble():
    y = tone(400, 0.15, decay=25, chirp_to=1200)
    return norm(y, 0.7)


def fx_ding():
    y = tone(1318.5, 1.2, decay=4, harmonics=((1, 1), (2.76, 0.3), (5.4, 0.1)))
    y += 0.6 * tone(1975.5, 1.2, decay=5)
    return norm(y, 0.7)


def fx_notify():
    a = tone(1046.5, 0.18, decay=14, harmonics=((1, 1), (2, 0.2)))
    b = tone(1568, 0.5, decay=8, harmonics=((1, 1), (2, 0.2)))
    y = np.zeros(int(SR * 0.62))
    y[:len(a)] += a
    y[int(SR * 0.11):int(SR * 0.11) + len(b)] += b
    return norm(y, 0.7)


def fx_cash():
    # "cha-ching": metallic noise burst + two bright bells
    n = int(SR * 1.1)
    y = np.zeros(n)
    burst = bandpass_sweep(rng.standard_normal(int(SR * 0.08)), 5000, 3000, q=3) * env_adsr(int(SR * 0.08), d=0.03)
    y[:len(burst)] += burst * 0.8
    for start, f in ((0.09, 2093), (0.2, 2637)):
        bell = tone(f, 0.85, decay=5, harmonics=((1, 1), (2.4, 0.4), (3.9, 0.2)))
        s = int(SR * start)
        y[s:s + len(bell)] += bell[: n - s]
    return norm(y, 0.75)


def fx_click():
    n = int(SR * 0.04)
    y = rng.standard_normal(n) * env_adsr(n, a=0.0005, d=0.004)
    return norm(lowpass(y, 6000), 0.7)


def fx_riser(d=1.2):
    n = int(SR * d)
    noise = bandpass_sweep(rng.standard_normal(n), 200, 6000, q=2.5)
    sweep = tone(150, d, decay=0, chirp_to=1200, harmonics=((1, 0.5), (2, 0.2)))
    e = np.linspace(0, 1, n) ** 2.2
    return stereo_pan_sweep(norm((noise + sweep) * e, 0.75))


def fx_impact():
    t = t_axis(1.0)
    boom = np.sin(2 * np.pi * np.cumsum(70 * (35 / 70) ** t) / SR) * np.exp(-5 * t)
    hit = lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-30 * t)
    return norm(boom + 0.5 * hit, 0.9)


def fx_sparkle():
    n = int(SR * 0.9)
    y = np.zeros(n)
    for k in range(9):
        f = rng.uniform(2500, 6000)
        s = int(SR * k * 0.06)
        g = tone(f, 0.35, decay=14) * rng.uniform(0.4, 1.0)
        y[s:s + len(g)] += g[: n - s]
    return norm(y, 0.6)


def fx_swipe():
    n = int(SR * 0.18)
    x = bandpass_sweep(rng.standard_normal(n), 1500, 7000, q=2)
    return norm(x * np.sin(np.pi * np.linspace(0, 1, n)), 0.6)


FX = {"whoosh": fx_whoosh, "swoosh": fx_swoosh, "pop": fx_pop, "bubble": fx_bubble, "ding": fx_ding,
      "notify": fx_notify, "cash": fx_cash, "click": fx_click, "riser": fx_riser, "impact": fx_impact,
      "sparkle": fx_sparkle, "swipe": fx_swipe}


def write_wav(path: Path, y: np.ndarray):
    if y.ndim == 1:
        y = np.stack([y, y], axis=1)
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


# ---------------------------------------------------------------- meme / trend style effects

def saw(f, t):
    ph = np.cumsum(f) / SR if np.ndim(f) else f * t
    return 2 * (ph % 1) - 1


def soft_clip(x, drive=2.5):
    return np.tanh(x * drive) / np.tanh(drive)


def fx_vine_boom():
    t = t_axis(1.6)
    f = 52 + 40 * np.exp(-9 * t)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-2.6 * t)
    click = lowpass(rng.standard_normal(len(t)), 1800) * np.exp(-60 * t) * 0.6
    sub = np.sin(2 * np.pi * 34 * t) * np.exp(-3.2 * t) * 0.6
    return norm(soft_clip(body + click + sub, 3.0), 0.95)


def fx_record_scratch():
    d = 0.75
    t = t_axis(d)
    rate = np.where(t < 0.35, 1 - t / 0.35 * 1.8, -0.8 + (t - 0.35) * 2)
    f = 900 * np.abs(rate) + 80
    noise = bandpass_sweep(rng.standard_normal(len(t)), 2500, 600, q=1.2)
    tone = saw(f, t) * 0.3
    env = np.minimum(1, t / 0.01) * np.exp(-1.5 * t)
    return norm((noise * 0.8 + tone) * env, 0.8)


def fx_boing():
    t = t_axis(0.8)
    f = 180 + 140 * np.sin(2 * np.pi * 9 * t) * np.exp(-3 * t) + 120 * np.exp(-6 * t)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-4 * t)
    return norm(y + 0.3 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR) * np.exp(-6 * t), 0.8)


def _tom(f0, d=0.35):
    t = t_axis(d)
    f = f0 * (1 + 0.6 * np.exp(-25 * t))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-9 * t) + lowpass(rng.standard_normal(len(t)), 3000) * np.exp(-40 * t) * 0.3


def _cymbal(d=1.4):
    t = t_axis(d)
    n = rng.standard_normal(len(t))
    hp = n - lowpass(n, 5000)
    return hp * np.exp(-3 * t) * 0.6


def fx_rimshot():
    """ba-dum-tss"""
    y = np.zeros(int(SR * 1.8))
    for st, f in ((0.0, 190), (0.16, 140)):
        tom = _tom(f)
        s = int(st * SR)
        y[s:s + len(tom)] += tom
    cy = _cymbal(1.4)
    s = int(0.36 * SR)
    y[s:s + len(cy)] += cy
    k = _tom(70, 0.4) * 0.8
    y[s:s + len(k)] += k
    return norm(y, 0.85)


def fx_drumroll():
    d = 1.6
    y = np.zeros(int(SR * (d + 1.2)))
    hits = np.arange(0, d, 0.045)
    for i, h in enumerate(hits):
        n = int(0.06 * SR)
        s = int(h * SR)
        g = 0.3 + 0.7 * (i / len(hits))
        y[s:s + n] += lowpass(rng.standard_normal(n), 4000) * np.exp(-50 * np.arange(n) / SR) * g
    cy = _cymbal(1.2)
    s = int(d * SR)
    y[s:s + len(cy)] += cy * 1.2
    return norm(y, 0.85)


def fx_sad_trombone():
    notes = [(311, 0.45), (294, 0.45), (277, 0.45), (262, 1.3)]
    out = []
    for i, (f0, d) in enumerate(notes):
        t = t_axis(d)
        vib = 1 + (0.03 * np.sin(2 * np.pi * 6 * t) * np.minimum(1, t / 0.3) if i == 3 else 0)
        f = f0 * vib * (1 - 0.02 * t / d)
        tone = saw(f, t)
        tone = lowpass(tone, 1400) * 1.4
        env = np.minimum(1, t / 0.04) * (np.exp(-0.8 * t) if i < 3 else np.exp(-1.2 * t))
        out.append(tone * env)
    return norm(np.concatenate(out), 0.8)


def fx_dun_dun_dun():
    out = []
    for f0, d in ((98, 0.35), (92.5, 0.35), (82.4, 1.4)):
        t = t_axis(d)
        chord = sum(saw(f0 * r, t) for r in (1, 1.5, 2, 2.52)) / 3
        chord = lowpass(chord, 1200)
        env = np.minimum(1, t / 0.02) * np.exp(-(1.8 if d > 1 else 3) * t)
        out.append(soft_clip(chord * env, 1.8))
        out.append(np.zeros(int(0.05 * SR)))
    return norm(np.concatenate(out), 0.85)


def fx_tada():
    y = np.zeros(int(SR * 1.6))
    for st, freqs in ((0.0, (523, 659)), (0.14, (659, 784, 1047))):
        t = t_axis(1.4)
        chord = sum(saw(f, t) for f in freqs) / len(freqs)
        chord = lowpass(chord, 2600) * np.minimum(1, t / 0.02) * np.exp(-2.2 * t)
        s = int(st * SR)
        y[s:s + len(t)] += chord[: len(y) - s]
    return norm(y, 0.8)


def fx_bonk():
    t = t_axis(0.35)
    y = np.sin(2 * np.pi * np.cumsum(420 * np.exp(-8 * t) + 160) / SR) * np.exp(-14 * t)
    y += lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-80 * t) * 0.6
    return norm(y, 0.85)


def fx_slide_up():
    t = t_axis(0.6)
    f = 400 * (2400 / 400) ** (t / 0.6)
    return norm(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * t / 0.6) ** 0.5, 0.6)


def fx_slide_down():
    return fx_slide_up()[::-1]


def fx_glitch():
    y = np.zeros(int(SR * 0.45))
    pos = 0
    while pos < len(y) - 400:
        n = int(rng.uniform(0.01, 0.05) * SR)
        kind = rng.integers(0, 3)
        seg = (rng.standard_normal(n) if kind == 0 else
               np.sign(np.sin(2 * np.pi * rng.uniform(200, 2000) * np.arange(n) / SR)) * 0.6)
        y[pos:pos + n] += seg[: len(y) - pos] * rng.uniform(0.3, 1)
        pos += n + int(rng.uniform(0, 0.02) * SR)
    return norm(y, 0.6)


def fx_shutter():
    y = np.zeros(int(SR * 0.25))
    for st in (0.0, 0.07):
        n = int(0.03 * SR)
        s = int(st * SR)
        y[s:s + n] += (rng.standard_normal(n) - lowpass(rng.standard_normal(n), 2000)) * np.exp(-90 * np.arange(n) / SR)
    return norm(y, 0.7)


def fx_typing():
    y = np.zeros(int(SR * 1.0))
    t = 0.0
    while t < 0.9:
        n = int(0.025 * SR)
        s = int(t * SR)
        y[s:s + n] += (rng.standard_normal(n) - lowpass(rng.standard_normal(n), 1500)) * np.exp(-120 * np.arange(n) / SR) * rng.uniform(0.4, 1)
        t += rng.uniform(0.06, 0.13)
    return norm(y, 0.6)


def fx_pop2():
    return norm(tone(600, 0.1, decay=45, chirp_to=1400), 0.8)


def fx_pop3():
    y = tone(1200, 0.07, decay=60, chirp_to=500)
    return norm(np.concatenate([y, np.zeros(int(0.03 * SR)), tone(1500, 0.06, decay=70, chirp_to=700)]), 0.75)


def fx_whoosh2():
    n = int(SR * 0.4)
    x = bandpass_sweep(rng.standard_normal(n), 6000, 300, q=1.0)
    return stereo_pan_sweep(norm(x * np.sin(np.pi * np.linspace(0, 1, n)) ** 2, 0.7), False)


def fx_whoosh3():
    n = int(SR * 0.7)
    x = bandpass_sweep(rng.standard_normal(n), 150, 2500, q=0.8)
    e = np.linspace(0, 1, n) ** 3 * np.exp(-0.5 * np.linspace(0, 1, n))
    return stereo_pan_sweep(norm(x * e, 0.8))


def fx_ding2():
    return norm(tone(1760, 0.9, decay=6, harmonics=((1, 1), (2.0, 0.4), (3.0, 0.15))), 0.65)


def fx_heartbeat():
    y = np.zeros(int(SR * 1.6))
    for st in (0.0, 0.22, 0.8, 1.02):
        k = _tom(55, 0.25)
        s = int(st * SR)
        y[s:s + len(k)] += k * (1 if st in (0.0, 0.8) else 0.7)
    return norm(lowpass(y, 400), 0.9)


FX.update({"vine_boom": fx_vine_boom, "record_scratch": fx_record_scratch, "boing": fx_boing, "rimshot": fx_rimshot,
           "drumroll": fx_drumroll, "sad_trombone": fx_sad_trombone, "dun_dun_dun": fx_dun_dun_dun, "tada": fx_tada,
           "bonk": fx_bonk, "slide_up": fx_slide_up, "slide_down": fx_slide_down, "glitch": fx_glitch,
           "shutter": fx_shutter, "typing": fx_typing, "pop2": fx_pop2, "pop3": fx_pop3, "whoosh2": fx_whoosh2,
           "whoosh3": fx_whoosh3, "ding2": fx_ding2, "heartbeat": fx_heartbeat})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "assets" / "sfx"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in FX.items():
        write_wav(out / f"{name}.wav", fn())
        print("  ", out / f"{name}.wav")


if __name__ == "__main__":
    main()
