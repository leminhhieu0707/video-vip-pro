"""Synthesize the "viral editor" tech sound set (data chatter, charge-up, clicks, stutter, flash, flicker, pop-up,
cut-out, digital whoosh, sub thump) — modelled on the sound design of top short-form editors, generated from
scratch so it can ship in the skill AND inside commercial apps.

    python make_sfx_viral.py [--out DIR]        (default: <skill>/assets/sfx)  -> viral_<family>_<n>.wav

Families (use them in plans like any SFX family; sound.py rotates variants):
  data      digital data blips/loops (UI, text, numbers appearing)
  charge    camera-flash charge-up whine + bass thump (big reveal, freeze frame, before a cut)
  click     hard UI click with a tonal body (cut-outs, each item, selections)
  stutter   rapid glitchy click burst (stutter text, fast montages)
  flash     camera flash pop (photo freeze, white flash)
  flicker   electric buzz flicker (subject flicker, glitch on/off)
  popup     short blip + air (pop-up cards, stickers, labels)
  cutout    paper-cut snap + click (person cut-out, sticker peel)
  dwhoosh   digital whoosh with a bit-crushed tail (transitions)
  thump     sub bass thump (under every big hit)
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path(__file__).resolve().parent.parent / "assets" / "sfx"


def t_(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.002, d=0.08, curve=5.0):
    t = np.arange(n) / SR
    e = np.exp(-curve * np.maximum(0, t - a) / max(d, 1e-3))
    na = max(1, int(a * SR))
    e[:na] *= np.linspace(0, 1, na)
    return e


def sine(f, d, f1=None):
    t = t_(d)
    if f1 is None:
        return np.sin(2 * np.pi * f * t)
    k = np.log(f1 / f) / d
    return np.sin(2 * np.pi * f * (np.exp(k * t) - 1) / k)


def square(f, d):
    return np.sign(sine(f, d) + 1e-9)


def hp(x, a=0.95):  # cheap one-pole high-pass
    y = np.zeros_like(x)
    prev_x = prev_y = 0.0
    for i, v in enumerate(x):
        prev_y = a * (prev_y + v - prev_x)
        prev_x = v
        y[i] = prev_y
    return y


def lp(x, a=0.2):
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def bitcrush(x, bits=6, hold=4):
    q = 2 ** bits
    y = np.round(x * q) / q
    return np.repeat(y[::hold], hold)[:len(x)]


def place(dst, src, at):
    i = int(at * SR)
    j = min(len(dst), i + len(src))
    if i < len(dst):
        dst[i:j] += src[:j - i]


def norm(x, peak=0.89):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def blip(rng, d=0.03, base=None):
    f = base or rng.choice([4800, 5600, 7400, 9100, 11200, 13500])
    x = 0.6 * square(f, d) + 0.4 * sine(f * 1.5, d)
    x = x * env(len(x), 0.001, d * 0.5, 4)
    click = rng.normal(0, 1, int(0.004 * SR)) * env(int(0.004 * SR), 0.0002, 0.002)
    out = np.zeros(len(x))
    out[:len(click)] += 0.8 * click
    return out + 0.5 * x


def fx_data(rng, length=0.9, rate=16):
    out = np.zeros(int(SR * (length + 0.1)))
    t = 0.0
    while t < length:
        place(out, blip(rng, rng.uniform(0.015, 0.04)), t)
        t += rng.uniform(0.6, 1.4) / rate
    out += 0.05 * bitcrush(rng.normal(0, 1, len(out)), 4, 6) * np.linspace(1, 0.2, len(out))
    return hp(out, 0.97)


def fx_thump(rng, d=0.6):
    f0 = rng.uniform(48, 62)
    x = sine(f0 * 2.4, d, f0) * env(int(SR * d), 0.003, d * 0.35, 3.5)
    x += 0.4 * np.tanh(3 * x)
    return lp(x, 0.08)


def fx_charge(rng, d=1.3):
    n = int(SR * d)
    out = np.zeros(n + int(0.4 * SR))
    rise = d * rng.uniform(0.75, 0.95)
    for k, (f0, f1) in enumerate([(900, 1900), (2300, 3500), (3900, 6200), (7000, 11000)]):
        s = sine(f0, rise, f1) * np.linspace(0.05, 1, int(SR * rise)) ** 1.6 * (0.45 / (k + 1) ** 0.4)
        place(out, s, 0)
    place(out, 0.9 * fx_thump(rng, 0.7), 0)
    burst = fx_data(rng, 0.45, 26) * 0.7
    place(out, burst, rise - 0.05)
    snap = rng.normal(0, 1, int(0.03 * SR)) * env(int(0.03 * SR), 0.0005, 0.01)
    place(out, 0.9 * snap, rise)
    return out


def fx_click(rng):
    d = 0.09
    body = sine(rng.uniform(1000, 1500), d) * env(int(SR * d), 0.0005, 0.018, 6)
    tick = rng.normal(0, 1, int(0.006 * SR)) * env(int(0.006 * SR), 0.0002, 0.002)
    out = np.zeros(int(SR * 0.12))
    place(out, 0.7 * body, 0)
    place(out, hp(tick, 0.9), 0)
    place(out, 0.25 * blip(rng, 0.02, rng.choice([6000, 9000, 12000])), 0.003)
    return out


def fx_stutter(rng, d=0.8):
    out = np.zeros(int(SR * (d + 0.1)))
    t = 0.0
    rate = rng.uniform(16, 24)
    while t < d:
        c = fx_click(rng) * rng.uniform(0.5, 1.0)
        if rng.random() < 0.5:
            c = bitcrush(c, 5, 3)
        place(out, c, t)
        t += 1 / rate * rng.uniform(0.7, 1.3)
    place(out, 0.4 * fx_thump(rng, 0.4), 0)
    return out


def fx_flash(rng):
    d = 0.5
    pop = rng.normal(0, 1, int(SR * 0.06)) * env(int(SR * 0.06), 0.0005, 0.02)
    ping = sine(rng.uniform(5200, 7600), d) * env(int(SR * d), 0.001, 0.12, 4) * 0.35
    whine = sine(9000, 0.25, 12000) * env(int(SR * 0.25), 0.01, 0.1) * 0.15
    out = np.zeros(int(SR * 0.6))
    place(out, hp(pop, 0.85), 0)
    place(out, ping, 0.005)
    place(out, whine, 0)
    return out


def fx_flicker(rng, d=0.7):
    t = t_(d)
    buzz = np.sign(np.sin(2 * np.pi * 120 * t)) * 0.4 + rng.normal(0, 0.25, len(t))
    gate = (np.sin(2 * np.pi * rng.uniform(9, 16) * t + rng.uniform(0, 3)) > rng.uniform(-0.1, 0.4)).astype(float)
    gate = np.convolve(gate, np.ones(80) / 80, "same")
    return hp(bitcrush(buzz * gate, 6, 2) * np.linspace(1, 0.4, len(t)), 0.9)


def fx_popup(rng):
    d = 0.18
    f = rng.uniform(1300, 2200)
    tone = sine(f, d, f * rng.uniform(1.4, 2.0)) * env(int(SR * d), 0.002, 0.05, 4)
    air = hp(rng.normal(0, 1, int(SR * 0.12)), 0.97) * env(int(SR * 0.12), 0.01, 0.04) * 0.25
    out = np.zeros(int(SR * 0.25))
    place(out, 0.7 * tone, 0)
    place(out, air, 0)
    place(out, 0.3 * blip(rng, 0.015), 0.0)
    return out


def fx_cutout(rng):
    snap = rng.normal(0, 1, int(SR * 0.05)) * env(int(SR * 0.05), 0.0003, 0.008)
    tear = lp(rng.normal(0, 1, int(SR * 0.12)), 0.5) * env(int(SR * 0.12), 0.003, 0.04) * 0.35
    out = np.zeros(int(SR * 0.25))
    place(out, hp(snap, 0.8), 0)
    place(out, tear, 0.01)
    place(out, 0.6 * fx_click(rng), 0.035)
    return out


def fx_dwhoosh(rng, d=0.5):
    n = int(SR * d)
    noise = rng.normal(0, 1, n)
    shape = np.sin(np.linspace(0, np.pi, n)) ** 2
    sweep = sine(rng.uniform(300, 600), d, rng.uniform(4000, 8000)) * 0.25
    x = hp(noise, 0.9) * shape * 0.6 + sweep * shape
    tail = bitcrush(x[int(n * 0.55):], 5, 5) * 0.5
    out = np.zeros(int(n * 1.3))
    place(out, x, 0)
    place(out, tail, d * 0.55)
    return out


FAMILIES = {"data": (fx_data, 6), "charge": (fx_charge, 4), "click": (fx_click, 6), "stutter": (fx_stutter, 4),
            "flash": (fx_flash, 3), "flicker": (fx_flicker, 3), "popup": (fx_popup, 5), "cutout": (fx_cutout, 4),
            "dwhoosh": (fx_dwhoosh, 4), "thump": (fx_thump, 3)}


def write(path: Path, y: np.ndarray):
    y = norm(np.nan_to_num(y))
    fade = min(len(y), int(0.01 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    st = np.stack([y, y], axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for fam, (fn, count) in FAMILIES.items():
        for k in range(1, count + 1):
            rng = np.random.default_rng(1000 * k + len(fam))
            write(out / f"viral_{fam}_{k}.wav", fn(rng))
            n += 1
    print(f"{n} viral sounds -> {out}")


if __name__ == "__main__":
    main()
