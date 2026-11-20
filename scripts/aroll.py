"""Talking-head A-roll in ONE pass, lip-sync safe: keep the sentences you choose, drop the rest, speed up a little,
polish (denoise, voice EQ, light skin smoothing, bright grade) and compensate the filter delay once.

Why: joining many short talking clips segment by segment makes the sound drift a few frames per cut. Cutting every
sentence from one constant-frame-rate copy in a single ffmpeg graph keeps picture and sound locked.

    python aroll.py cuts.json -o edited/aroll.mp4 [--speed 1.1] [--aspect 9:16] [--beauty 0.45] [--no-polish]

cuts.json (write it from the transcript: one entry per sentence you keep, in the order you want them):
    {"sources": ["../IMG_0992.MOV", "../IMG_0993.MOV"],
     "cuts": [{"src": 0, "in": 0.42, "out": 3.10, "text": "thôi đừng có bỏ tiền đi học edit video nữa"}, ...]}
Paths are relative to cuts.json. in/out: first word start −0.08 s, last word end +0.15 s (no breath at the cut).

Writes  aroll.mp4  and  aroll.json = {"starts": [...], "total": T, "speed": S, "cuts": [...]}: starts[i] is where
sentence i begins on the new timeline -> use them as clip boundaries ("in"/"out" on aroll.mp4) in the plan, so
every sentence can get its own zoom / punch without touching the sound.
HDR iPhone footage (HLG / PQ) is tone-mapped to SDR automatically.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FFMPEG, probe  # noqa: E402

FPS_IN = 60
SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}
TONEMAP = ("zscale=tin={tin}:min=bt2020nc:pin=bt2020:t=linear:npl=150,format=gbrpf32le,zscale=p=bt709,"
           "tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p,eq=contrast=1.1:gamma=0.93:saturation=1.06,")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit("ffmpeg lỗi:\n" + r.stderr[-1500:])
    return r


def prep(src: Path, out: Path, W: int, H: int) -> None:
    """Constant 60 fps, canvas-sized (cover crop), SDR, PCM audio."""
    if out.exists() and out.stat().st_mtime > src.stat().st_mtime:
        return
    info = probe(src)
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    trc = v.get("color_transfer", "")
    tm = TONEMAP.format(tin="arib-std-b67" if trc == "arib-std-b67" else "smpte2084") if trc in ("arib-std-b67", "smpte2084") else ""
    vf = f"{tm}scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,fps={FPS_IN}"
    print(f"[aroll] chuẩn bị {src.name}{' (HDR → SDR)' if tm else ''}", flush=True)
    run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", "14", "-preset", "fast",
         "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", str(out)])


def env_bytes(p: Path) -> np.ndarray:
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(p), "-vn", "-ac", "1", "-ar", "8000",
                        "-af", "bandpass=f=1200:width_type=h:w=1800", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.abs(np.frombuffer(r, np.int16).astype(float))
    return np.convolve(x, np.ones(8) / 8, "same")[::8]  # 1 ms resolution


def measure_delay(a: Path, b: Path) -> int:
    """ms that b's audio lags a's (median over 4 s windows)."""
    A, B = env_bytes(a), env_bytes(b)
    lags = []
    for t in range(1, max(2, int(len(A) / 1000) - 6), 5):
        x = A[t * 1000:(t + 4) * 1000]
        if len(x) < 4000 or x.std() < 1:
            continue
        x = x - x.mean()
        best = max((float(np.dot(x, B[t * 1000 + k:(t + 4) * 1000 + k] - B[t * 1000 + k:(t + 4) * 1000 + k].mean())), k)
                   for k in range(-150, 150) if t * 1000 + k >= 0 and (t + 4) * 1000 + k <= len(B))
        lags.append(best[1])
    return int(np.median(lags)) if lags else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cuts")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--speed", type=float, default=1.1, help="1.0–1.2; 1.1 = tighter talk without chipmunk voice")
    ap.add_argument("--aspect", default="9:16", choices=list(SIZES))
    ap.add_argument("--beauty", type=float, default=0.4, help="skin smoothing 0–1 (0 = off)")
    ap.add_argument("--no-polish", action="store_true", help="skip denoise / voice / grade / beauty")
    a = ap.parse_args()

    cj = Path(a.cuts).resolve()
    spec = json.loads(cj.read_text(encoding="utf-8"))
    root = cj.parent
    out = Path(a.out).resolve() if a.out else root / "aroll.mp4"
    work = out.parent / (out.stem + "_work")
    work.mkdir(parents=True, exist_ok=True)
    W, H = SIZES[a.aspect]
    srcs = [(root / s).resolve() for s in spec["sources"]]
    preps = []
    for i, s in enumerate(srcs):
        p = work / f"src{i}_60.mov"
        prep(s, p, W, H)
        preps.append(p)

    SP = max(0.5, min(2.0, a.speed))
    parts, labels, starts, acc = [], [], [], 0
    for i, c in enumerate(spec["cuts"]):
        n, f0, f1 = int(c.get("src", 0)), round(float(c["in"]) * FPS_IN), round(float(c["out"]) * FPS_IN)
        parts.append(f"[{n}:v]trim=start_frame={f0}:end_frame={f1},setpts=PTS-STARTPTS[v{i}];"
                     f"[{n}:a]atrim=start={f0 / FPS_IN:.6f}:end={f1 / FPS_IN:.6f},asetpts=PTS-STARTPTS[a{i}];")
        labels.append(f"[v{i}][a{i}]")
        starts.append(round(acc / FPS_IN / SP, 3))
        acc += f1 - f0
    total = round(acc / FPS_IN / SP, 3)
    fc = ("".join(parts) + "".join(labels) + f"concat=n={len(labels)}:v=1:a=1[vc][ac];"
          f"[vc]setpts=PTS/{SP},fps=30:round=near[v];[ac]atempo={SP}[a]")
    (work / "cut.fc").write_text(fc, encoding="utf-8")
    cut = work / "cut.mov"
    cmd = [FFMPEG, "-v", "error", "-y"]
    for p in preps:
        cmd += ["-i", str(p)]
    print(f"[aroll] cắt {len(labels)} câu trong 1 lượt, tốc độ {SP}×", flush=True)
    run(cmd + ["-filter_complex_script", str(work / "cut.fc"), "-map", "[v]", "-map", "[a]", "-r", "30",
               "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p",
               "-c:a", "pcm_s16le", "-ar", "48000", str(cut)])

    if a.no_polish:
        run([FFMPEG, "-v", "error", "-y", "-i", str(cut), "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", str(out)])
    else:
        plan = {"output": str(work / "polished.mp4"), "canvas": {"aspect": a.aspect, "fps": 30, "fit": "crop"},
                "clip_defaults": {"denoise": "light", "voice": True, "beauty": a.beauty,
                                  "grade": {"preset": "bright", "brightness": 0.01, "saturation": 1.03}},
                "clips": [{"src": str(cut), "in": 0, "out": total}], "audio": {"normalize": -14}, "quality": "high"}
        pj = work / "polish.json"
        pj.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[aroll] làm đẹp hình + tiếng", flush=True)
        subprocess.run([sys.executable, str(Path(__file__).with_name("render.py")), str(pj)], check=True)
        pol = work / "polished.mp4"
        D = measure_delay(cut, pol)
        print(f"[aroll] bù trễ bộ lọc tiếng: {D} ms", flush=True)
        sr = 48000
        raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(pol), "-vn", "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                             capture_output=True).stdout
        x = np.frombuffer(raw, np.float32).reshape(-1, 2)
        y = np.zeros_like(x)
        s = int(D * sr / 1000)
        if s > 0:
            y[:-s] = x[s:]
        elif s < 0:
            y[-s:] = x[:s]
        else:
            y[:] = x
        f32 = work / "sync.f32"
        y.tofile(f32)
        run([FFMPEG, "-v", "error", "-y", "-i", str(pol), "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", str(f32),
             "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(out)])

    meta = {"src": out.name, "starts": starts, "total": total, "speed": SP,
            "cuts": [{**c, "start": st} for c, st in zip(spec["cuts"], starts)]}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[aroll] xong: {out} ({total:.2f} s, {len(starts)} câu) + {out.with_suffix('.json').name}")


if __name__ == "__main__":
    main()
