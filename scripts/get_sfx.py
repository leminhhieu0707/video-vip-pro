"""Download a trending creator sound-effect pack (Mixkit, free for commercial videos, no attribution needed) to THIS
computer. The files are not part of the skill repo (Mixkit's licence forbids redistributing them as a library), so
every user runs this once:   python get_sfx.py [--per 8]

Writes assets/sfx/pack/<family>_<n>_<slug>.mp3 + assets/sfx/pack/index.json.
In plans you then write a FAMILY name and render.py rotates through its variants so the same sound never repeats
back to back:  "boom", "whoosh", "pop", "sparkle", "ding", "hit", "riser", "glitch", "camera", "typing", "cash",
"click", "drumroll", "swipe", "bling", "laugh", "applause", "cartoon", "game",
"crunch", "sizzle", "pour" (food ASMR).  "boom:3" = a fixed variant.
Mixkit licence: https://mixkit.co/license/#sfxFree
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import urllib.request
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent / "assets" / "sfx" / "pack"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
# family -> (mixkit tag pages, max seconds, title words to prefer, title words to avoid)
FAMILIES = {
    "whoosh": (["whoosh", "swoosh", "transition"], 2.5, ["whoosh", "swoosh", "woosh", "fast", "transition"], ["long"]),
    "boom": (["boom", "cinematic", "bass"], 4.0, ["boom", "impact", "bass", "hit", "drop"], ["explosion", "war", "gun", "wrong", "buzzer", "error"]),
    "hit": (["hit", "impact"], 2.0, ["hit", "punch", "impact", "slam"], ["gun", "body", "pain"]),
    "pop": (["pop", "interface"], 1.2, ["pop", "bubble", "click"], []),
    "click": (["click", "interface"], 1.0, ["click", "tap", "button"], ["camera", "shutter"]),
    "sparkle": (["sparkle", "magic"], 3.0, ["sparkle", "magic", "shine", "twinkle", "glitter"], ["spell", "evil"]),
    "bling": (["sparkle", "ding"], 2.5, ["bling", "shine", "sparkle", "ding"], []),
    "ding": (["ding", "bell", "notification"], 2.5, ["ding", "bell", "notification", "correct", "chime"], ["church", "alarm"]),
    "riser": (["rise", "cinematic"], 6.0, ["riser", "rise", "swell", "build", "uplifter"], ["whoosh", "swoosh"]),
    "glitch": (["glitch"], 2.5, ["glitch", "digital", "static"], []),
    "camera": (["camera"], 2.0, ["camera", "shutter", "photo", "snap"], []),
    "typing": (["typing"], 4.0, ["typing", "keyboard", "type"], []),
    "cash": (["cash"], 3.0, ["cash", "register", "coin", "money"], []),
    "drumroll": (["drum"], 6.0, ["drum roll"], ["swoosh", "wind"]),
    "swipe": (["swipe"], 1.5, ["swipe", "slide", "page"], []),
    "game": (["game"], 2.5, ["win", "bonus", "level", "coin", "achievement", "success"], ["lose", "over"]),
    "laugh": (["laugh"], 4.0, ["laugh"], ["evil", "scary"]),
    "applause": (["applause"], 5.0, ["applause", "clap", "cheer"], []),
    "cartoon": (["cartoon"], 2.0, ["boing", "pop", "spring", "slide", "bonk"], []),
    # food ASMR (food / restaurant / cooking videos)
    "crunch": (["crunch", "bite", "chewing"], 3.0, ["crunch", "crisp", "bite", "chew", "munch"], ["dog", "monster"]),
    "sizzle": (["sizzle", "fry", "frying"], 6.0, ["sizzl", "fry", "frying", "grill", "pan"], []),
    "pour": (["pouring", "drink"], 5.0, ["pour", "liquid", "glass", "water", "drink"], ["toilet"]),
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def items(tag: str):
    out = []
    for page in (1, 2):
        try:
            h = fetch(f"https://mixkit.co/free-sound-effects/{tag}/" + (f"?page={page}" if page > 1 else ""))
        except Exception:
            break
        for m in re.finditer(r'preview-url-value="(https://assets\.mixkit\.co/active_storage/sfx/(\d+)/\d+-preview\.mp3)"'
                             r'.*?item-grid-card__title">\s*([^<]+?)\s*</h2>.*?meta-time"[^>]*>\s*(\d+):(\d+)', h, re.S):
            url, sid, title, mm, ss = m.groups()
            out.append({"id": int(sid), "url": url, "title": html.unescape(title), "dur": int(mm) * 60 + int(ss)})
    return out


def slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s[:28] or "sfx"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per", type=int, default=8, help="variants per family")
    ap.add_argument("--only", nargs="*", help="families to (re)download")
    a = ap.parse_args()
    PACK.mkdir(parents=True, exist_ok=True)
    idx_path = PACK / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    for fam, (tags, maxd, prefer, avoid) in FAMILIES.items():
        if a.only and fam not in a.only:
            continue
        seen, cands = set(), []
        for t in tags:
            for it in items(t):
                if it["id"] in seen or it["dur"] > maxd or any(w in it["title"].lower() for w in avoid):
                    continue
                seen.add(it["id"])
                it["score"] = sum(w in it["title"].lower() for w in prefer)
                if it["score"]:  # title must say what it is
                    cands.append(it)
        cands.sort(key=lambda x: (-x["score"], x["dur"]))
        files = []
        for n, it in enumerate(cands[:a.per], 1):
            dst = PACK / f"{fam}_{n}_{slug(it['title'])}.mp3"
            if not dst.exists():
                try:
                    req = urllib.request.Request(it["url"], headers=UA)
                    dst.write_bytes(urllib.request.urlopen(req, timeout=30).read())
                except Exception as e:
                    print(f"  skip {it['title']}: {e}")
                    continue
            files.append({"file": dst.name, "title": it["title"], "id": it["id"], "dur": it["dur"]})
        index[fam] = files
        print(f"{fam:9s} {len(files)} sounds: " + ", ".join(f["title"] for f in files[:4]) + (" ..." if len(files) > 4 else ""))
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    (PACK / "LICENSE_mixkit.txt").write_text("Downloaded from mixkit.co under the Mixkit Sound Effects Free License "
                                            "(free for commercial and personal projects, no attribution; do not redistribute "
                                            "the files as a standalone library). https://mixkit.co/license/#sfxFree\n",
                                            encoding="utf-8")
    print(f"pack: {sum(len(v) for v in index.values())} sounds in {PACK}")


if __name__ == "__main__":
    main()
