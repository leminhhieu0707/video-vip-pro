"""Speech-to-text with word timestamps (faster-whisper, GPU if available).

Usage:
  python transcribe.py INPUT [-o OUT_PREFIX] [--lang vi] [--model large-v3-turbo] [--prompt "từ khoá, tên riêng"]

Writes OUT_PREFIX.json (segments + words), OUT_PREFIX.srt and OUT_PREFIX.txt (one line per segment with times).
Default OUT_PREFIX = <input without extension>.transcript
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import save_json, setup_cuda_dlls, srt_ts  # noqa: E402


def load_model(name: str, device: str):
    setup_cuda_dlls()
    from faster_whisper import WhisperModel
    if device in ("auto", "cuda"):
        try:
            import ctranslate2
            if ctranslate2.get_cuda_device_count() > 0:
                return WhisperModel(name, device="cuda", compute_type="float16"), "cuda"
        except Exception as e:  # missing cuDNN etc.
            print(f"[transcribe] CUDA unavailable ({e}); falling back to CPU", file=sys.stderr)
        if device == "cuda":
            raise SystemExit("CUDA requested but not usable")
    return WhisperModel(name, device="cpu", compute_type="int8"), "cpu"


def decode_audio(path: Path):
    """16 kHz mono float32 via ffmpeg (avoids PyAV version mismatches)."""
    import subprocess

    import numpy as np
    from common import FFMPEG
    p = subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                        "-f", "f32le", "-"], capture_output=True)
    if p.returncode != 0:
        raise SystemExit(p.stderr.decode("utf-8", "replace")[-800:])
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def merge_number_tokens(words: list[dict]) -> list[dict]:
    """Whisper splits '8.190.000' into '8', '.190', '.000' - glue such fragments back together."""
    out: list[dict] = []
    for w in words:
        t = w["word"]
        if out and t[:1] in ".,%" and (t[1:2].isdigit() or t == "%") and out[-1]["word"][-1:].isdigit():
            out[-1] = {**out[-1], "word": out[-1]["word"] + t, "end": w["end"]}
        else:
            out.append(dict(w))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--out", help="output path STEM (adds .json/.srt/.txt); default <input>.transcript")
    ap.add_argument("--lang", default="vi", help="language code, or 'auto'")
    ap.add_argument("--model", default="large-v3-turbo",
                    help="large-v3-turbo (default, fast+good), large-v3 (best), medium, small")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--prompt", default=None,
                    help="initial prompt: brand names, product names, jargon to spell correctly")
    ap.add_argument("--no-vad", action="store_true", help="disable voice-activity filter (keep music-only parts)")
    a = ap.parse_args()

    src = Path(a.input)
    out = str(a.out) if a.out else str(src.with_name(src.stem + ".transcript"))
    t0 = time.time()
    audio = decode_audio(src)
    try:
        model, dev = load_model(a.model, a.device)
        segments, info = model.transcribe(
            audio, language=None if a.lang == "auto" else a.lang, word_timestamps=True,
            vad_filter=not a.no_vad, vad_parameters={"min_silence_duration_ms": 300},
            initial_prompt=a.prompt, beam_size=5, condition_on_previous_text=False,
        )
        segs = list(segments)
    except RuntimeError as e:
        if "cudnn" in str(e).lower() or "cublas" in str(e).lower() or "cuda" in str(e).lower():
            print(f"[transcribe] GPU failed ({e}); retrying on CPU", file=sys.stderr)
            model, dev = load_model(a.model, "cpu")
            segments, info = model.transcribe(audio, language=None if a.lang == "auto" else a.lang,
                                              word_timestamps=True, vad_filter=not a.no_vad,
                                              initial_prompt=a.prompt, beam_size=5)
            segs = list(segments)
        else:
            raise

    data = {
        "source": str(src), "language": info.language, "duration": info.duration, "model": a.model, "device": dev,
        "segments": [
            {"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
             "words": merge_number_tokens(
                 [{"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word.strip(),
                   "prob": round(w.probability, 3)} for w in (s.words or []) if w.word.strip()])}
            for s in segs
        ],
    }
    save_json(data, out + ".json")
    with open(out + ".srt", "w", encoding="utf-8") as f:
        for i, s in enumerate(data["segments"], 1):
            f.write(f"{i}\n{srt_ts(s['start'])} --> {srt_ts(s['end'])}\n{s['text']}\n\n")
    with open(out + ".txt", "w", encoding="utf-8") as f:
        for s in data["segments"]:
            f.write(f"[{s['start']:7.2f} - {s['end']:7.2f}] {s['text']}\n")
    print(f"[transcribe] {len(data['segments'])} segments, {sum(len(s['words']) for s in data['segments'])} words, "
          f"{dev}, {time.time() - t0:.1f}s -> {out + '.json'}")


if __name__ == "__main__":
    main()
