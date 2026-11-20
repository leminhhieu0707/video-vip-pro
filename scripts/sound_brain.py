"""Sound brain: places story sounds where the WORDS and the PICTURE call for them — not on a grid.

A creator's sound design follows meaning:
  money / price spoken      -> kaching on the number          "giòn"            -> crunch on the word
  "chụp", "ảnh"             -> camera                          "gõ", "lệnh"      -> keyboard
  "click", "bấm"            -> mouse                           "lật", "trang"    -> page
  "điện thoại", "gọi"       -> phone                           "xong", "done"    -> ding
  "đẹp", "lung linh"        -> sparkle                         "nhanh", "vèo"    -> whoosh
  surprise ("bất ngờ","sốc","wow","không ngờ")  -> riser 1 s before + boom on the word (or meme woah)
  fail / wrong ("sai","hỏng","toang","dở","na ná") -> meme "what?" / sad sting (comedy only)
  the reveal of the topic / a number / a result -> riser -> boom
  section change (new topic, chapter)  -> one whoosh
Rules: one meaning = one sound; ≥0.45 s between sounds; ≤4 sounds per 10 s; loud stingers (boom, meme) at most every
6 s; memes only on a real punchline and ≤3 per video; never stack a story sound on top of an effect sound already there.

    python sound_brain.py voice.transcript.json [--offset 0.5] [--style trend|viral|calm] [--comedy] [-o sfx.json]
      -> prints each suggestion with its reason and writes a plan "sfx" list you can paste / load in build_vip.py

In a plan, "sound_design": {"style": "trend", "brain": {"transcripts": ["voice.transcript.json"], "offset": 0.5,
"comedy": false}} runs the same brain automatically at render time (after the effect sounds, so it never doubles them).
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

# (pattern on the lower-cased word window, family, offset s, volume, kind, reason)
# kind: "object" (literal sound of a thing), "accent", "stinger" (loud, rate-limited), "meme" (comedy only)
LEXICON = [
    (r"\b(\d[\d.,]*\s*(k|nghìn|ngàn|triệu|tr|tỷ|tỉ|đ|đồng|vnđ|usd|\$|%))", "kaching", 0.05, 0.2, "object", "nói tới tiền / con số giá"),
    (r"\b(giá|tiền|ưu đãi|giảm giá|miễn phí|khuyến mãi|sale)\b", "kaching", 0.0, 0.16, "object", "nói tới tiền / ưu đãi"),
    (r"\b(giòn|giòn tan|giòn rụm|rôm rốp)\b", "crunch", 0.0, 0.22, "object", "chữ 'giòn'"),
    (r"\b(rót|nước chấm|chan|canh)\b", "pour", 0.0, 0.16, "object", "rót / nước"),
    (r"\b(chụp|chụp ảnh|bức ảnh|tấm ảnh|ảnh chụp|camera)\b", "camera", 0.0, 0.2, "object", "chụp ảnh"),
    (r"\b(gõ|câu lệnh|lệnh|prompt|bàn phím|nhắn tin)\b", "keyboard", 0.0, 0.16, "object", "gõ / câu lệnh"),
    (r"\b(click|bấm|nhấn|chọn nút)\b", "mouse", 0.0, 0.2, "object", "bấm / click"),
    (r"\b(lật|trang|kịch bản|cuốn sách|tài liệu)\b", "page", 0.0, 0.18, "object", "lật trang / giấy tờ"),
    (r"\b(điện thoại|gọi điện|cuộc gọi|reng)\b", "phone", 0.0, 0.16, "object", "điện thoại"),
    (r"\b(viết|ghi chú|ghi lại|vẽ)\b", "pen", 0.0, 0.16, "object", "viết / vẽ"),
    (r"\b(xong|hoàn thành|done|ok rồi|vậy là xong|thành công)\b", "ding", 0.05, 0.18, "accent", "hoàn thành"),
    (r"\b(đẹp|lung linh|sang chảnh|xịn|long lanh|lấp lánh|đỉnh)\b", "sparkle", 0.0, 0.14, "accent", "khen đẹp / xịn"),
    (r"\b(nhanh|vèo|một phát|trong nháy mắt|chớp mắt)\b", "whoosh", -0.05, 0.16, "accent", "nhanh"),
    (r"\b(bất ngờ|sốc|choáng|wow|không ngờ|không thể tin|trời ơi|ối)\b", "boom", 0.0, 0.2, "stinger", "bất ngờ (riser trước + bùm)"),
    (r"\b(sai|hỏng|toang|dở tệ|thất bại|na ná|chán|lỗi)\b", "meme", 0.05, 0.26, "meme", "thất bại / chê (meme)"),
    (r"\b(haha|hihi|buồn cười|hài|đùa)\b", "laugh", 0.05, 0.18, "meme", "chỗ đùa"),
]
SECTION_CUES = r"\b(thứ nhất|thứ hai|thứ ba|đầu tiên|tiếp theo|tiếp đến|cuối cùng|bước \d|một là|hai là|ba là|nhưng mà|tuy nhiên|đặc biệt)\b"
STYLE_SWAP = {"viral": {"boom": "thump", "whoosh": "dwhoosh", "ding": "popup", "mouse": "vclick", "keyboard": "data"},
              "calm": {"boom": "whoosh"}}


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s.lower())


def words_from(transcripts: list, offset: float = 0.0) -> list[dict]:
    out = []
    for t in transcripts:
        tr = json.loads(Path(t).read_text(encoding="utf-8")) if not isinstance(t, dict) else t
        for seg in tr.get("segments", []):
            for w in seg.get("words") or []:
                out.append({"w": _norm(str(w["word"])), "t": float(w["start"]) + offset, "e": float(w["end"]) + offset})
    return out


def suggest(words: list[dict], style: str = "trend", comedy: bool = False, busy: list[float] | None = None,
            max_memes: int = 3) -> list[dict]:
    """[{sfx, at, volume, why}] — busy = times that already carry an effect sound (never doubled)."""
    busy = sorted(busy or [])
    picks: list[dict] = []
    used_word: set[int] = set()
    memes = 0
    last_loud = -1e9
    swap = STYLE_SWAP.get(style, {})
    for i, w in enumerate(words):
        window = " ".join(x["w"] for x in words[i:i + 4])
        for pat, fam, off, vol, kind, why in LEXICON:
            m = re.match(pat, window)
            if not m or i in used_word:
                continue
            if kind == "meme" and (not comedy or memes >= max_memes):
                continue
            at = w["t"] + off
            if kind in ("stinger", "meme") and at - last_loud < 6:
                continue
            if any(abs(at - b) < 0.35 for b in busy) or any(abs(at - p["at"]) < 0.45 for p in picks):
                continue
            if sum(1 for p in picks if at - p["at"] < 10) >= 4:
                continue
            if kind == "stinger":  # build-up lands on the word
                picks.append({"sfx": swap.get("riser", "riser"), "at": round(max(0, at - 1.1), 2), "volume": 0.12,
                              "why": "kéo lên trước cú bất ngờ"})
            fam2 = swap.get(fam, fam)
            if kind == "meme" and fam == "meme":
                fam2 = "meme"
            picks.append({"sfx": fam2, "at": round(at, 2), "volume": vol, "why": f"{why}: \"{window.split()[0]}\""})
            used_word.update(range(i, i + max(1, len(m.group(0).split()))))
            if kind in ("stinger", "meme"):
                last_loud = at
                memes += kind == "meme"
            break
    # one whoosh at spoken section changes (if no other sound right there)
    for i, w in enumerate(words):
        window = " ".join(x["w"] for x in words[i:i + 3])
        if re.match(SECTION_CUES, window):
            at = w["t"] - 0.12
            if not any(abs(at - p["at"]) < 0.8 for p in picks) and not any(abs(at - b) < 0.5 for b in busy):
                picks.append({"sfx": swap.get("whoosh", "whoosh"), "at": round(at, 2), "volume": 0.14,
                              "why": f"đổi ý: \"{window}\""})
    return sorted(picks, key=lambda p: p["at"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("transcripts", nargs="+")
    ap.add_argument("--offset", type=float, default=0.0, help="seconds to add (voice-over start on the timeline)")
    ap.add_argument("--style", default="trend", choices=["trend", "viral", "calm"])
    ap.add_argument("--comedy", action="store_true", help="allow meme / laugh stingers")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    picks = suggest(words_from(a.transcripts, a.offset), a.style, a.comedy)
    for p in picks:
        print(f"{p['at']:7.2f}s  {p['sfx']:9s} vol {p['volume']:.2f}   {p['why']}")
    if a.out:
        Path(a.out).write_text(json.dumps([{k: p[k] for k in ("sfx", "at", "volume")} for p in picks], ensure_ascii=False, indent=1),
                               encoding="utf-8")
        print("->", a.out)


if __name__ == "__main__":
    main()
