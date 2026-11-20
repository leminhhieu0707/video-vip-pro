"""Free AI voice-over (Microsoft Edge neural voices) with exact word timings.

Usage:
  python tts.py script.txt -o out/voice [--voice vi-VN-NamMinhNeural] [--rate +15%] [--pitch +0Hz]

Writes out/voice.mp3 and out/voice.transcript.json (same format as transcribe.py, one segment per line of
the script), so the plan can use it as a voiceover AND as the subtitle source with perfect sync.
Vietnamese voices: vi-VN-NamMinhNeural (male), vi-VN-HoaiMyNeural (female).
Write numbers/units the way they should be SPOKEN (e.g. "mi-li-mét"); fix the on-screen form later in the
transcript json if needed (same word count keeps timing).
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG, run, save_json  # noqa: E402


async def synth_line(text: str, voice: str, rate: str, pitch: str, mp3: Path) -> list[dict]:
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with open(mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                words.append({"start": round(s, 3), "end": round(s + chunk["duration"] / 1e7, 3),
                              "word": chunk["text"]})
    return words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script", help="text file, one sentence/paragraph per line (blank lines ignored)")
    ap.add_argument("-o", "--out", required=True, help="output path stem")
    ap.add_argument("--voice", default="vi-VN-NamMinhNeural")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--pitch", default="+0Hz")
    ap.add_argument("--gap", type=float, default=0.3, help="pause between lines (s)")
    a = ap.parse_args()

    lines = [ln.strip() for ln in Path(a.script).read_text(encoding="utf-8-sig").splitlines() if ln.strip()]
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    work = out.parent / (out.name + "_parts")
    work.mkdir(exist_ok=True)

    segs, parts, t = [], [], 0.0
    for i, line in enumerate(lines):
        import hashlib
        import json as _json
        import time as _time
        key = hashlib.md5(f"{line}|{a.voice}|{a.rate}|{a.pitch}".encode()).hexdigest()[:12]
        mp3 = work / f"line_{i:03d}_{key}.mp3"
        cache = mp3.with_suffix(".words.json")
        if mp3.exists() and mp3.stat().st_size > 0 and cache.exists():  # already synthesized on a previous run
            words = _json.loads(cache.read_text(encoding="utf-8"))
        else:
            # the free service sometimes drops a request ("No audio was received"); retry with backoff
            for attempt in range(7):
                try:
                    words = asyncio.run(synth_line(line, a.voice, a.rate, a.pitch, mp3))
                    if mp3.stat().st_size > 0:
                        break
                except Exception as e:  # noqa: BLE001
                    if attempt == 6:
                        raise SystemExit(f"TTS failed on line {i + 1} after retries: {e}")
                _time.sleep(min(30, 2 * 2 ** attempt))
            cache.write_text(_json.dumps(words, ensure_ascii=False), encoding="utf-8")
        wav = work / f"line_{i:03d}.wav"
        # trim the voice's trailing silence so line pacing is controlled by --gap only
        keep = (words[-1]["end"] + 0.12) if words else None
        run([FFMPEG, "-y", "-i", str(mp3), *(["-t", f"{keep:.3f}"] if keep else []), "-ar", "48000", "-ac", "2",
             str(wav)])
        from common import probe
        dur = probe(wav)["duration"]
        segs.append({"start": round(t + (words[0]["start"] if words else 0), 3),
                     "end": round(t + (words[-1]["end"] if words else dur), 3), "text": line,
                     "words": [{**w, "start": round(w["start"] + t, 3), "end": round(w["end"] + t, 3)}
                               for w in words]})
        parts.append((wav, dur))
        t += dur + a.gap

    # concatenate with gaps
    lst = work / "concat.txt"
    sil = work / "gap.wav"
    run([FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{a.gap:.3f}", str(sil)])
    lst.write_text("".join(f"file '{p.as_posix()}'\nfile '{sil.as_posix()}'\n" for p, _ in parts), encoding="utf-8")
    mp3_out = Path(str(out) + ".mp3")
    run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame", "-q:a", "2",
         str(mp3_out)])
    save_json({"source": str(mp3_out.resolve()), "language": "vi", "segments": segs},
              Path(str(out) + ".transcript.json"))
    print(f"[tts] {len(lines)} lines, {t:.1f}s -> {mp3_out}")


if __name__ == "__main__":
    main()
