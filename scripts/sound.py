"""Sound design for VIP edits: trending creator SFX families (assets/sfx/pack, see get_sfx.py), variant rotation so a
sound never repeats back to back, layered hits, and automatic sounds for every effect ("sound_design": "trend").

In a plan:
  "sfx": [{"sfx": "boom", "at": 3.2}]                       family -> next variant (boom_1, boom_2, ...)
  "sfx": [{"sfx": ["whoosh", "boom"], "at": 3.2}]            layered (whoosh lands 0.08 s earlier)
  "sfx": [{"sfx": "sparkle:2", "at": 5}]                     a fixed variant
  "sound_design": "trend"   every motion / frost / person layer / big zoom gets its sound automatically
                            (an overlay with "sfx": null stays silent; "sfx": "name" overrides).
Without the pack, family names fall back to the synthesized library via render.SFX_ALIASES.
"""
from __future__ import annotations

import json
from pathlib import Path

import os

PACK = Path(os.environ["MH_SFX_PACK"]) if os.environ.get("MH_SFX_PACK") else     Path(__file__).resolve().parent.parent / "assets" / "sfx" / "pack"
MINE = Path(__file__).resolve().parent.parent / "assets" / "sfx" / "mine"   # user's own sounds (import_sfx.py)
_index: dict | None = None
_mine: dict | None = None
_turn: dict[str, int] = {}

# what each effect sounds like: [(family, offset seconds, volume)]  — offsets < 0 land before the visual
SOUND_MAP: dict[str, list[tuple[str, float, float]]] = {
    # text / captions
    "BlueText": [], "BlueBig": [("whoosh", -0.1, 0.18), ("boom", 0.0, 0.16)], "GiantCaption": [("whoosh", -0.12, 0.2), ("boom", 0.0, 0.2)],
    "KineticTitle": [("whoosh", -0.05, 0.16)], "GravityText": [("hit", 0.25, 0.18)], "Stamp": [("hit", 0.1, 0.22), ("boom", 0.1, 0.16)],
    "SplitFlap": [("click", 0.0, 0.2), ("click", 0.25, 0.16)], "Highlighter": [("pen", 0.05, 0.18)], "CircleDraw": [("pen", 0.0, 0.18)],
    "NumberTitle": [("whoosh", -0.05, 0.16)], "TitleCard": [("page", -0.05, 0.16), ("boom", 0.05, 0.16)],
    "Intertitle": [("whoosh", -0.05, 0.16)],
    # lists / data
    "Tiles": [("pop", 0.0, 0.18)], "Checklist": [("pop", 0.0, 0.16)], "NumberList": [("whoosh", -0.1, 0.18)],
    "CountUp": [("riser", 0.0, 0.12), ("kaching", 0.95, 0.2)], "BarChart": [("whoosh", -0.05, 0.16), ("sparkle", 0.8, 0.14)],
    "BarChartRace": [("whoosh", -0.05, 0.16), ("ding", 1.2, 0.16)], "LineGraph": [("swipe", 0.1, 0.16), ("sparkle", 1.0, 0.14)],
    "VsCards": [("whoosh", -0.05, 0.18), ("hit", 0.35, 0.18)], "Callouts": [("pop", 0.1, 0.16)],
    "ConstellationHub": [("boom", 0.0, 0.16), ("sparkle", 0.4, 0.12)], "IconSlam": [("hit", 0.0, 0.2)],
    # UI
    "IncomingCall": [("phone", 0.0, 0.16)], "NotifyStack": [("pop", 0.0, 0.18)], "ChatBubbles": [("pop", 0.0, 0.16)],
    "CommentsDrop": [("pop", 0.0, 0.16)], "TypeBar": [("keyboard", 0.0, 0.16)], "Cursor": [("mouse", 0.6, 0.22)],
    "FloatButton": [("mouse", 0.5, 0.22)], "FileDrop": [("whoosh", 0.0, 0.16), ("pop", 0.6, 0.16)], "FocusBrackets": [("camera", 0.0, 0.18)],
    "ChapterPanel": [("whoosh", -0.05, 0.16)], "EditTimeline": [("mouse", 0.1, 0.16)], "JiggleChips": [("pop", 0.0, 0.16)],
    "DeviceSplay": [("whoosh", -0.05, 0.18), ("pop", 0.35, 0.16), ("pop", 0.7, 0.16)], "ExplodedStack": [("whoosh", 0.0, 0.18), ("sparkle", 0.6, 0.12)],
    "PhoneFrame": [("whoosh", -0.05, 0.16)], "VideoCard": [("pop", 0.0, 0.16)], "ScreenCard": [("whoosh", -0.05, 0.16)],
    # stills / transitions
    "Polaroids": [("camera", 0.0, 0.18)], "PostWall": [("whoosh", -0.05, 0.18), ("boom", 0.05, 0.14)], "CardStack": [("page", 0.0, 0.18)],
    "OrbitCarousel": [("whoosh", -0.05, 0.18), ("sparkle", 0.3, 0.12)], "VisionCarousel": [("whoosh", 0.0, 0.18), ("whoosh", 0.9, 0.12)],
    "Newspaper": [("page", -0.05, 0.2), ("hit", 0.2, 0.14)], "HeadlineWall": [("whoosh", -0.05, 0.18), ("pop", 0.3, 0.12)],
    "TearAway": [("paper", 0.05, 0.22)], "BlowAway": [("whoosh", 0.0, 0.2)], "InkSpread": [("whoosh", 0.0, 0.2), ("boom", 0.25, 0.14)],
    # effects
    "Shockwave": [("boom", 0.0, 0.22), ("whoosh", 0.05, 0.14)], "Cracks": [("hit", 0.0, 0.22), ("glitch", 0.05, 0.1)],
    "OrbitRing": [("sparkle", 0.0, 0.14)], "Portal": [("riser", -0.2, 0.12), ("boom", 0.4, 0.16)], "ScanLines": [("glitch", 0.0, 0.1)],
    "VhsHud": [("glitch", 0.0, 0.2)], "DoodleStickers": [("pen", 0.0, 0.16), ("sparkle", 0.3, 0.12)], "ScriptPage": [("page", 0.0, 0.16), ("keyboard", 0.3, 0.12)],
    "Eyedropper": [("mouse", 0.8, 0.2)], "CompareHandle": [("swipe", 0.2, 0.16)], "FollowCard": [("mouse", 0.9, 0.22), ("ding", 1.1, 0.16)],
}
TYPE_MAP = {"frost": [("whoosh", -0.12, 0.18)], "bg": [("whoosh", -0.08, 0.18)], "popout": [("whoosh", -0.1, 0.2), ("paper", 0.15, 0.14)],
            "lens": [("pop", 0.0, 0.16)], "outline": [("pen", 0.0, 0.16), ("sparkle", 0.2, 0.12)]}
FX_MAP = {"vhs": [("glitch", 0.0, 0.2)], "film": [("camera", 0.0, 0.12)], "bw": [("whoosh", 0.0, 0.12)]}


def index() -> dict:
    global _index
    if _index is None:
        p = PACK / "index.json"
        _index = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _index


# older recipe names -> pack family (used only when the pack is installed)
ALIAS = {"whoosh_air": "whoosh", "whoosh_fast": "whoosh", "whoosh_cinematic": "whoosh", "whoosh2": "whoosh", "whoosh3": "whoosh",
         "swoosh": "whoosh", "zoom_vacuum": "whoosh", "sweep_small": "whoosh", "pop_bubble": "pop", "pop2": "pop", "pop3": "pop",
         "pop_message": "pop", "bubble": "pop", "tech_tick": "click", "tech_blip": "click", "correct_answer": "ding", "notify": "ding",
         "ding2": "ding", "bass_hit": "boom", "tech_rise_hit": "boom", "vine_boom": "boom", "impact": "hit", "impact_hit": "hit",
         "camera_shutter": "camera", "shutter": "camera", "typing_real": "typing", "riser_short": "riser", "tada": "game"}


# without the downloaded pack: each family rotates through the synthesized library (make_sfx.py names)
FAMILY_FALLBACK = {"whoosh": ["whoosh", "whoosh2", "whoosh3", "swoosh"], "boom": ["impact", "vine_boom"], "hit": ["impact"],
                   "pop": ["pop", "pop2", "pop3", "bubble"], "click": ["click"], "sparkle": ["sparkle"], "bling": ["sparkle", "ding2"],
                   "ding": ["ding", "ding2"], "riser": ["riser"], "glitch": ["glitch"], "camera": ["shutter"], "typing": ["typing"],
                   "cash": ["cash"], "drumroll": ["drumroll"], "swipe": ["swipe", "swoosh"], "game": ["tada"],
                   "cartoon": ["boing", "bonk"], "laugh": [], "applause": [], "crunch": [], "pour": []}
# "viral editor" tech set, synthesized by make_sfx_viral.py (always available, ships in apps too)
for _fam, _n in (("data", 6), ("charge", 4), ("stutter", 4), ("flash", 3), ("flicker", 3), ("popup", 5), ("cutout", 4),
                 ("dwhoosh", 4), ("thump", 3)):
    FAMILY_FALLBACK[_fam] = [f"viral_{_fam}_{k}" for k in range(1, _n + 1)]
FAMILY_FALLBACK["vclick"] = [f"viral_click_{k}" for k in range(1, 7)]
FAMILY_FALLBACK.update({"page": ["swipe", "swoosh"], "paper": ["swoosh", "swipe"], "mouse": ["click", "viral_click_1"],
                        "keyboard": ["typing"], "phone": ["notify"], "kaching": ["cash"], "pen": ["swipe"]})

# sound_design style "viral": tech/data sound design of top short-form editors (charge-ups, data blips, clicks, flashes)
VIRAL_MAP: dict[str, list[tuple[str, float, float]]] = {
    "BlueText": [], "BlueBig": [("dwhoosh", -0.1, 0.16), ("thump", 0.0, 0.18)], "GiantCaption": [("charge", -0.95, 0.14)],
    "KineticTitle": [("data", 0.0, 0.12)], "GravityText": [("thump", 0.25, 0.18)], "Stamp": [("thump", 0.1, 0.2), ("vclick", 0.1, 0.2)],
    "SplitFlap": [("stutter", 0.0, 0.14)], "Highlighter": [("data", 0.0, 0.1)], "CircleDraw": [("data", 0.0, 0.1)],
    "NumberTitle": [("popup", 0.0, 0.16)], "TitleCard": [("dwhoosh", -0.1, 0.18), ("thump", 0.05, 0.18)], "Intertitle": [("popup", 0.0, 0.14)],
    "Tiles": [("popup", 0.0, 0.16)], "Checklist": [("popup", 0.0, 0.15)], "NumberList": [("data", 0.0, 0.12)],
    "CountUp": [("data", 0.0, 0.14), ("vclick", 0.95, 0.2)], "BarChart": [("data", 0.0, 0.12)], "BarChartRace": [("data", 0.0, 0.12)],
    "LineGraph": [("data", 0.0, 0.12)], "VsCards": [("dwhoosh", -0.05, 0.16), ("thump", 0.35, 0.16)], "Callouts": [("popup", 0.1, 0.14)],
    "ConstellationHub": [("thump", 0.0, 0.16), ("data", 0.3, 0.1)], "IconSlam": [("thump", 0.0, 0.18)],
    "IncomingCall": [("popup", 0.0, 0.18)], "NotifyStack": [("popup", 0.0, 0.16)], "ChatBubbles": [("popup", 0.0, 0.15)],
    "CommentsDrop": [("popup", 0.0, 0.15)], "TypeBar": [("data", 0.0, 0.12)], "Cursor": [("vclick", 0.6, 0.2)],
    "FloatButton": [("vclick", 0.5, 0.2)], "FileDrop": [("dwhoosh", 0.0, 0.14), ("popup", 0.6, 0.14)], "FocusBrackets": [("flash", 0.0, 0.16)],
    "ChapterPanel": [("data", 0.0, 0.12)], "EditTimeline": [("vclick", 0.1, 0.14)], "JiggleChips": [("popup", 0.0, 0.15)],
    "DeviceSplay": [("dwhoosh", 0.0, 0.16), ("popup", 0.35, 0.14), ("popup", 0.7, 0.14)], "ExplodedStack": [("charge", -0.5, 0.12)],
    "PhoneFrame": [("dwhoosh", -0.05, 0.15)], "VideoCard": [("popup", 0.0, 0.15)], "ScreenCard": [("dwhoosh", -0.05, 0.15)],
    "Polaroids": [("flash", 0.0, 0.18)], "PostWall": [("stutter", 0.0, 0.14)], "CardStack": [("cutout", 0.0, 0.16)],
    "OrbitCarousel": [("dwhoosh", 0.0, 0.16), ("data", 0.3, 0.1)], "VisionCarousel": [("dwhoosh", 0.0, 0.16)],
    "Newspaper": [("flash", 0.0, 0.16)], "HeadlineWall": [("stutter", 0.0, 0.14)], "TearAway": [("cutout", 0.08, 0.22)],
    "BlowAway": [("dwhoosh", 0.0, 0.18)], "InkSpread": [("dwhoosh", 0.0, 0.18), ("thump", 0.25, 0.16)],
    "Shockwave": [("thump", 0.0, 0.22), ("dwhoosh", 0.05, 0.12)], "Cracks": [("thump", 0.0, 0.2), ("flicker", 0.05, 0.1)],
    "OrbitRing": [("data", 0.0, 0.1)], "Portal": [("charge", -0.6, 0.12), ("thump", 0.4, 0.16)], "ScanLines": [("flicker", 0.0, 0.1)],
    "VhsHud": [("flicker", 0.0, 0.16)], "DoodleStickers": [("popup", 0.0, 0.16), ("popup", 0.3, 0.12)], "ScriptPage": [("data", 0.1, 0.1)],
    "Eyedropper": [("vclick", 0.8, 0.18)], "CompareHandle": [("data", 0.2, 0.12)], "FollowCard": [("vclick", 0.9, 0.2), ("popup", 1.1, 0.14)],
}
VIRAL_TYPE = {"frost": [("dwhoosh", -0.12, 0.16)], "bg": [("cutout", 0.0, 0.18)], "popout": [("cutout", 0.0, 0.2), ("flash", 0.05, 0.12)],
              "lens": [("popup", 0.0, 0.15)], "outline": [("cutout", 0.0, 0.18)]}
VIRAL_FX = {"vhs": [("flicker", 0.0, 0.2)], "film": [("flash", 0.0, 0.12)], "bw": [("flash", 0.0, 0.12)]}


def mine() -> dict:
    global _mine
    if _mine is None:
        p = MINE / "index.json"
        _mine = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _mine


def pick(name: str, fallback) -> Path | None:
    """Family name -> next variant file (rotates); 'family:n' -> that variant; anything else -> fallback(name).
    The user's own library (assets/sfx/mine, import_sfx.py) is used first, then the trend pack, then synthesized."""
    fam, _, n = str(name).partition(":")
    own = mine().get(fam) or (mine().get(ALIAS[fam]) if fam in ALIAS else None)
    if own and not n:
        i = _turn.get("mine_" + fam, 0)
        _turn["mine_" + fam] = i + 1
        q = MINE / own[i % len(own)]["file"]
        if q.exists():
            return q
    if fam not in index() and ALIAS.get(fam) in index():
        fam = ALIAS[fam]
    files = index().get(fam)
    if files:
        if n.isdigit():
            f = files[(int(n) - 1) % len(files)]
        else:
            i = _turn.get(fam, 0)
            _turn[fam] = i + 1
            f = files[i % len(files)]
        p = PACK / f["file"]
        if p.exists():
            return p
    if fam in FAMILY_FALLBACK:  # no pack installed: rotate through the basic library
        opts = FAMILY_FALLBACK[fam]
        for k in range(len(opts)):
            i = _turn.get("fb_" + fam, 0)
            _turn["fb_" + fam] = i + 1
            got = fallback(opts[(i + k) % len(opts)])
            if got:
                return got
        return None
    return fallback(fam if files else name)


def layers(spec) -> list[tuple[str, float, float | None]]:
    """'boom' | ['whoosh', 'boom'] -> [(name, offset, None)] (layered: earlier layers land slightly before)."""
    if isinstance(spec, str):
        return [(spec, 0.0, None)]
    if isinstance(spec, list):
        n = len(spec)
        return [(s, -0.08 * (n - 1 - k), None) for k, s in enumerate(spec) if s]
    return []


def design(plan: dict, starts: list[float]) -> list[tuple[str, float, float]]:
    """Automatic sounds for every effect: [(family, timeline_time, volume)].
    "sound_design": "trend" (effects + zooms) or {"style": "trend", "cuts": true, "captions": true} for a denser
    creator mix: a soft whoosh on every cut and a light pop on captions that have a **keyword**."""
    sd = plan.get("sound_design")
    opts = sd if isinstance(sd, dict) else {}
    viral = (opts.get("style") if opts else sd) == "viral"
    smap, tmap, fmap = (VIRAL_MAP, VIRAL_TYPE, VIRAL_FX) if viral else (SOUND_MAP, TYPE_MAP, FX_MAP)
    out = []
    if opts.get("cuts"):
        clips = plan.get("clips", []) or []
        for i in range(1, len(clips)):
            if clips[i - 1]["out"] - clips[i - 1]["in"] >= 0.8:
                out.append(("dwhoosh" if viral else "whoosh", starts[i] - 0.12, float(opts.get("cut_volume", 0.09))))
    if opts.get("captions"):
        for o in plan.get("overlays", []) or []:
            if o.get("comp") == "BlueText" and "**" in str((o.get("props") or {}).get("text", "")) and "sfx" not in o:
                out.append(("vclick" if viral else "pop", float(o.get("start", 0)) + (starts[int(o["clip"])] if "clip" in o else 0) + 0.05, 0.1))
    for o in plan.get("overlays", []) or []:
        if "sfx" in o:  # explicit: null = silent, name/list = handled as a plan sound
            continue
        ty = o.get("type", "text")
        lay = (smap.get(o.get("comp"), []) if ty == "motion" else tmap.get(ty)
               or (fmap.get(o.get("effect")) if ty == "fx" else None) or [])
        if ty == "frost" and o.get("mode") == "none":
            lay = [("flash" if viral else "camera", 0.0, 0.16)]
        if ty == "motion" and o.get("half") == "back":
            continue
        t0 = float(o.get("start", 0)) + (starts[int(o["clip"])] if "clip" in o else 0)
        for fam, off, vol in lay:
            out.append((fam, t0 + off, vol))
        # list items that pop in one by one get one sound each
        props = o.get("props") or {}
        if ty == "motion" and o.get("comp") in ("Tiles", "Checklist", "NotifyStack", "ChatBubbles", "CommentsDrop", "Callouts", "IconSlam"):
            for it in (props.get("items") or [])[1:6]:
                if isinstance(it, dict) and it.get("at") is not None:
                    out.append(("popup" if viral else ("pop" if o["comp"] != "IconSlam" else "hit"), t0 + float(it["at"]), 0.15))
    for i, c in enumerate(plan.get("clips", []) or []):
        for z in c.get("zooms") or []:
            to = float(z.get("to", 1.2))
            at = starts[i] + float(z.get("at", 0))
            if to >= 1.7:  # snap zoom (viral: the charge-up lands on the snap, plus a flash)
                out += ([("charge", at - 0.95, 0.12), ("flash", at, 0.14)] if viral else [("whoosh", at - 0.06, 0.18), ("boom", at, 0.16)])
            elif to >= 1.2 and c.get("shake"):
                out.append(("thump" if viral else "hit", at, 0.16))
    # de-clutter: same family within 0.3 s, and never more than 3 sounds inside any 0.5 s window
    out.sort(key=lambda e: e[1])
    kept: list[tuple[str, float, float]] = []
    for e in out:
        if any(k[0] == e[0] and abs(k[1] - e[1]) < 0.3 for k in kept[-6:]):
            continue
        if sum(1 for k in kept[-6:] if e[1] - k[1] < 0.5) >= 3:
            continue
        kept.append(e)
    return kept
