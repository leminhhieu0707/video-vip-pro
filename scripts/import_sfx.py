"""Import YOUR OWN sound effects (a pack you bought, your CapCut/Premiere library, sounds you collected) into the skill.
They go to assets/sfx/mine/ (git-ignored, stays on this computer) and are used BEFORE the built-in sounds.

    python import_sfx.py "D:\\SFX\\Viral Editor SFX Pack"        # copy + auto-sort by folder / file name
    python import_sfx.py "D:\\SFX" --dry                          # only show how files would be sorted
    python import_sfx.py --list                                   # what is in your library now

Sorting uses folder and file names (English + Vietnamese): "Data UI/Data 5.wav" -> data, "Camera/Camera Charge.wav"
-> charge, "Clicks/Click 6.wav" -> click ... Files nothing matches go to family "misc" (not used automatically).
Re-run any time; already imported files are skipped. Use only sounds you are allowed to use in your videos.
"""
from __future__ import annotations

import argparse
import os
import json
import re
import shutil
from pathlib import Path

MINE = Path(os.environ["MH_SFX_MINE"]) if os.environ.get("MH_SFX_MINE") else \
    Path(__file__).resolve().parent.parent / "assets" / "sfx" / "mine"
EXT = {".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg", ".m4a"}
# family: keywords (checked against "folder/file" lower-case, first match wins — specific before generic)
RULES = [
    ("meme", ["meme", "sus", "fart", "bruh", "vine boom", "wait a minute", "woah", "wooo", "what", "goofy", "huh"]),
    ("charge", ["charge", "charging", "flash charge", "sạc"]),
    ("stutter", ["stutter", "stuttering"]),
    ("data", ["data", "computer", "digital ui", "hud", "beep", "bip", "dữ liệu"]),
    ("flash", ["flash", "photo flash"]),
    ("camera", ["camera", "shutter", "chụp"]),
    ("flicker", ["flicker", "buzz", "electric"]),
    ("glitch", ["glitch", "static", "distort", "error"]),
    ("riser", ["riser", "rise", "build", "uplift", "swell", "tension"]),
    ("whoosh", ["whoosh", "woosh", "swoosh", "swish", "transition", "pass by", "lướt"]),
    ("swipe", ["swipe", "slide", "quẹt"]),
    ("boom", ["boom", "bass drop", "sub drop", "drop", "bass", "braam", "bùm"]),
    ("hit", ["hit", "impact", "punch", "slam", "thud", "đấm"]),
    ("pop", ["pop", "bubble", "pop up", "popup", "appear"]),
    ("mouse", ["mouse", "chuột"]),
    ("click", ["click", "tick", "tap", "button", "ui"]),
    ("keyboard", ["keyboard", "typing", "type", "gõ phím", "bàn phím"]),
    ("ding", ["ding", "bell", "chime", "notification", "notify", "alert", "correct", "thông báo"]),
    ("sparkle", ["sparkle", "magic", "shine", "twinkle", "glitter", "shimmer", "lấp lánh"]),
    ("kaching", ["cash register", "ka-ching", "kaching", "register"]),
    ("cash", ["cash", "coin", "money", "tiền", "xu"]),
    ("page", ["page", "book", "lật trang"]),
    ("paper", ["paper", "crumple", "tear", "rip", "giấy"]),
    ("pen", ["pen", "pencil", "marker", "scribble", "write", "writing", "bút"]),
    ("phone", ["phone", "ring", "vibrat", "điện thoại"]),
    ("laugh", ["laugh", "cười"]),
    ("applause", ["applause", "clap", "cheer", "vỗ tay"]),
    ("cartoon", ["cartoon", "boing", "bonk", "funny", "hoạt hình"]),
    ("crunch", ["crunch", "bite", "chew", "eat"]),
    ("pour", ["pour", "liquid", "drink"]),
    ("game", ["game", "level", "bonus", "win", "achievement", "coin collect"]),
]


def family_of(rel: str) -> str:
    s = rel.lower().replace("_", " ").replace("-", " ")
    for fam, keys in RULES:
        for k in keys:
            if re.search(r"(^|[^a-z])" + re.escape(k) + r"($|[^a-z])", s) or (len(k) > 4 and k in s):
                return fam
    return "misc"


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:32] or "sfx"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", nargs="?")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    idx_path = MINE / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    if a.list or not a.folder:
        for fam, files in sorted(index.items()):
            print(f"{fam:9s} {len(files):3d}  " + ", ".join(f["title"] for f in files[:4]))
        print(f"total {sum(len(v) for v in index.values())} sounds in {MINE}")
        return
    src = Path(a.folder)
    seen = {f["source"] for files in index.values() for f in files}
    added = {}
    for p in sorted(src.rglob("*")):
        if p.suffix.lower() not in EXT or str(p) in seen:
            continue
        base = re.sub(r" \(\d+\)$", "", p.stem)
        if base != p.stem and (p.with_name(base + p.suffix)).exists():  # browser duplicate "name (1).mp3" of a file we have
            continue
        rel = str(p.relative_to(src)).replace("\\", "/")
        if re.search(r"(^|/)(nhac|nhạc|music|bgm)", rel.lower()):
            continue  # background music folders are not sound effects
        fam = family_of(rel)
        added.setdefault(fam, []).append(rel)
        if a.dry:
            continue
        MINE.mkdir(parents=True, exist_ok=True)
        n = len(index.get(fam, [])) + 1
        dst = MINE / f"{fam}_{n}_{slug(p.stem)}{p.suffix.lower()}"
        shutil.copy2(p, dst)
        index.setdefault(fam, []).append({"file": dst.name, "title": p.stem, "source": str(p)})
    for fam, rels in sorted(added.items()):
        print(f"{fam:9s} +{len(rels):3d}  " + ", ".join(rels[:3]) + (" ..." if len(rels) > 3 else ""))
    if not a.dry:
        idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"imported {sum(len(v) for v in added.values())} sounds -> {MINE} (used before built-in sounds)")


if __name__ == "__main__":
    main()
