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
MINE = Path(os.environ["MH_SFX_MINE"]) if os.environ.get("MH_SFX_MINE") else \
    Path(__file__).resolve().parent.parent / "assets" / "sfx" / "mine"   # user's own sounds (import_sfx.py)
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
    # TREND pack
    "NameTag": [("whoosh", 0.05, 0.16)], "PriceSlash": [("swipe", 0.3, 0.16), ("hit", 0.75, 0.2), ("kaching", 0.85, 0.16)],
    "Receipt": [("keyboard", 0.2, 0.12), ("kaching", 1.8, 0.18)], "MapPin": [("whoosh", 0.0, 0.16), ("pop", 1.05, 0.18)],
    "DecodeText": [("keyboard", 0.05, 0.12)], "Countdown": [("ding", 0.0, 0.14)], "EvidenceBoard": [("camera", 0.25, 0.16)], "Audiogram": [("pop", 0.0, 0.1)],
    "Text3D": [("boom", 0.0, 0.16)], "WeaveText": [("whoosh", 0.0, 0.14)], "ProjectText": [("camera", 0.0, 0.14)], "MetalText": [("hit", 0.0, 0.18), ("sparkle", 0.45, 0.14)], "GlassText": [("whoosh", 0.0, 0.14)], "NeonText": [("glitch", 0.0, 0.12)], "WriteOn": [("pen", 0.0, 0.16)], "SliceText": [("swipe", 0.0, 0.16)], "WeightPulse": [("pop", 0.35, 0.12)], "DustText": [("whoosh", 1.0, 0.14)], "PunchWord": [("boom", 0.0, 0.2)], "DocLabel": [("typing", 0.3, 0.12)], "QuoteCard": [("page", 0.0, 0.14)], "MarqueeRows": [("whoosh", 0.0, 0.14)], "TrackLabel": [("pop", 0.0, 0.16)], "RiseText": [("whoosh", 0.0, 0.16)], "MirrorText": [("sparkle", 0.0, 0.14)], "FocusText": [("camera", 1.4, 0.14)], "Odometer": [("riser", 0.0, 0.12), ("kaching", 1.3, 0.18)], "SealBadge": [("hit", 0.0, 0.18)], "CubeFlip": [("swipe", 0.0, 0.14)], "RaysTitle": [("riser", -0.2, 0.12), ("boom", 0.3, 0.16)], "InkText": [("whoosh", 0.0, 0.12)], "RansomText": [("paper", 0.0, 0.16)], "AIChat": [("pop", 0.0, 0.14), ("keyboard", 0.8, 0.12)], "BeatText": [],
}
TYPE_MAP = {"frost": [("whoosh", -0.12, 0.18)], "bg": [("whoosh", -0.08, 0.18)], "popout": [("whoosh", -0.1, 0.2), ("paper", 0.15, 0.14)],
            "lens": [("pop", 0.0, 0.16)], "outline": [("pen", 0.0, 0.16), ("sparkle", 0.2, 0.12)],
            "spotlight": [("boom", 0.0, 0.14)], "freeze": [("camera", 0.0, 0.2), ("hit", 0.05, 0.14)],
            "whip": [("whoosh", 0.0, 0.22)], "glitch": [("glitch", 0.0, 0.2)], "leak": [("whoosh", 0.05, 0.14)],
            "zoomthru": [("whoosh", 0.0, 0.2), ("boom", 0.25, 0.12)], "impact": [("hit", 0.0, 0.24)],
            "dramatic": [("vine_boom", 0.0, 0.22)], "dolly": [("riser", 0.0, 0.14)], "clone": [("pop", 0.0, 0.16), ("pop", 0.12, 0.14)],
            "neon": [("sparkle", 0.0, 0.14)], "facecam": [("pop", 0.0, 0.14)], "colorize": [("sparkle", 0.4, 0.12)]}
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
    "NameTag": [("dwhoosh", 0.05, 0.14)], "PriceSlash": [("dwhoosh", 0.3, 0.14), ("thump", 0.75, 0.2), ("vclick", 0.85, 0.14)],
    "Receipt": [("data", 0.2, 0.12), ("vclick", 1.8, 0.18)], "MapPin": [("dwhoosh", 0.0, 0.14), ("popup", 1.05, 0.16)],
    "DecodeText": [("data", 0.05, 0.12)], "Countdown": [("vclick", 0.0, 0.14)], "EvidenceBoard": [("flash", 0.25, 0.16)], "Audiogram": [("popup", 0.0, 0.1)],
    "Text3D": [("thump", 0.0, 0.16)], "WeaveText": [("dwhoosh", 0.0, 0.14)], "ProjectText": [("flash", 0.0, 0.14)], "MetalText": [("thump", 0.0, 0.18), ("data", 0.45, 0.12)], "GlassText": [("dwhoosh", 0.0, 0.14)], "NeonText": [("flicker", 0.0, 0.14)], "WriteOn": [("data", 0.0, 0.12)], "SliceText": [("dwhoosh", 0.0, 0.16)], "WeightPulse": [("vclick", 0.35, 0.12)], "DustText": [("dwhoosh", 1.0, 0.14)], "PunchWord": [("thump", 0.0, 0.2)], "DocLabel": [("data", 0.3, 0.12)], "QuoteCard": [("popup", 0.0, 0.14)], "MarqueeRows": [("dwhoosh", 0.0, 0.14)], "TrackLabel": [("popup", 0.0, 0.16)], "RiseText": [("dwhoosh", 0.0, 0.16)], "MirrorText": [("flash", 0.0, 0.14)], "FocusText": [("flash", 1.4, 0.14)], "Odometer": [("data", 0.0, 0.12), ("vclick", 1.3, 0.18)], "SealBadge": [("thump", 0.0, 0.18)], "CubeFlip": [("dwhoosh", 0.0, 0.14)], "RaysTitle": [("charge", -0.5, 0.12), ("thump", 0.3, 0.16)], "InkText": [("dwhoosh", 0.0, 0.12)], "RansomText": [("cutout", 0.0, 0.16)], "AIChat": [("popup", 0.0, 0.14), ("data", 0.8, 0.12)], "BeatText": [],
}
VIRAL_TYPE = {"frost": [("dwhoosh", -0.12, 0.16)], "bg": [("cutout", 0.0, 0.18)], "popout": [("cutout", 0.0, 0.2), ("flash", 0.05, 0.12)],
              "lens": [("popup", 0.0, 0.15)], "outline": [("cutout", 0.0, 0.18)],
              "spotlight": [("thump", 0.0, 0.16)], "freeze": [("flash", 0.0, 0.2), ("thump", 0.05, 0.14)],
              "whip": [("dwhoosh", 0.0, 0.22)], "glitch": [("flicker", 0.0, 0.2)], "leak": [("flash", 0.05, 0.14)],
              "zoomthru": [("dwhoosh", 0.0, 0.2), ("thump", 0.25, 0.14)], "impact": [("thump", 0.0, 0.24)],
              "dramatic": [("vine_boom", 0.0, 0.22)], "dolly": [("charge", -0.3, 0.12)], "clone": [("popup", 0.0, 0.16)],
              "neon": [("data", 0.0, 0.12)], "facecam": [("popup", 0.0, 0.14)], "colorize": [("flash", 0.3, 0.12)]}
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
    if own:
        if n.isdigit():
            q = MINE / own[(int(n) - 1) % len(own)]["file"]
        else:
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


def trend_timed(comp: str, props: dict, dur: float, viral: bool) -> list[tuple[str, float, float]] | None:
    """TREND pack comps whose beats move with their props (slashAt, newAt, number of receipt lines, fly time)."""
    f = (lambda a, b: b if viral else a)
    if comp == "PriceSlash":
        sl, nw = float(props.get("slashAt", 0.3)), float(props.get("newAt", 0.75))
        out = [(f("swipe", "dwhoosh"), sl, 0.16), (f("hit", "thump"), nw, 0.2), (f("kaching", "vclick"), nw + 0.1, 0.16)]
        return out + ([(f("pop", "popup"), nw + 0.3, 0.14)] if props.get("badge") else [])
    if comp == "Receipt":
        at, n = float(props.get("at", 0)), max(1, len(props.get("items") or []) or 2)
        st = props.get("step") or max(0.28, min(0.7, (dur - at - 1.4) / (n + 1)))
        tt = at + 0.35 + n * float(st)
        out = [(f("keyboard", "data"), at + 0.15, 0.12), (f("kaching", "vclick"), tt, 0.18)]
        return out + ([(f("hit", "thump"), tt + 0.45, 0.18)] if props.get("stamp") else [])
    if comp == "Countdown":
        n, at = int(props.get("from", 3)), float(props.get("at", 0))
        step = max(0.4, (dur - at - 0.35) / n)
        return [(f("ding", "vclick"), at + i * step, 0.14) for i in range(n)]
    if comp == "EvidenceBoard":
        L = props.get("items") or [1, 2, 3]
        span = max(0.3, (dur - 1.2) / (len(L) + 1))
        return [(f("camera", "flash"), float((it.get("at") if isinstance(it, dict) else None) or 0.25 + i * span), 0.14)
                for i, it in enumerate(L[:6])]
    if comp == "CubeFlip":
        ws = props.get("words") or [1, 2, 3]
        at = float(props.get("at", 0))
        st = props.get("step") or max(0.45, (dur - at - 0.4) / len(ws))
        return [(f("swipe", "dwhoosh"), at + i * float(st), 0.14) for i in range(len(ws))]
    if comp == "Odometer":
        at, d = float(props.get("at", 0.1)), float(props.get("dur", 1.3))
        return [(f("riser", "data"), at, 0.12), (f("kaching", "vclick"), at + d, 0.18)]
    if comp == "FocusText":
        return [(f("camera", "flash"), float(props.get("swap", 1.4)), 0.14)]
    if comp == "BeatText":
        return [(f("hit", "thump"), float(b), 0.1) for b in (props.get("beats") or [])[:16]]
    if comp == "HudChapter":  # a whoosh per scene change (letters fly in), a click when a card lands, a pop per chip
        out = []
        sc = props.get("scenes") or []
        for i, s in enumerate(sc[:8]):
            at = float(s.get("at", (dur / max(1, len(sc))) * i))
            out.append((f("whoosh", "dwhoosh"), max(0.0, at - 0.05), 0.15))
            if s.get("card", "none") != "none" or s.get("media"):
                out.append((f("click", "vclick"), at + 0.45, 0.12))
            for ci, c in enumerate((s.get("chips") or [])[:3]):
                out.append((f("pop", "popup"), at + float(c.get("at", 0.6 + ci * 0.35) if isinstance(c, dict) else 0.6 + ci * 0.35), 0.12))
        return out
    if comp == "GeoMap":  # fly-in whoosh, a sparkle when the boundary closes, a pop on each route card, a ding on the rings
        out = [(f("whoosh", "dwhoosh"), 0.0, 0.14)]
        if props.get("site_at") is not None:
            out.append((f("sparkle", "flash"), float(props["site_at"]) + float(props.get("site_draw", 2)), 0.14))
        out += [(f("pop", "popup"), float(r.get("at", 0)) + float(r.get("dur", 1.6)), 0.14) for r in (props.get("routes") or [])[:5]]
        out += [(f("pop", "popup"), float(props["pins_at"]) + 0.05, 0.12)] if props.get("pins_at") is not None else []
        for key, snd, vol in (("lots_at", ("swipe", "data"), 0.12), ("roads_at", ("swipe", "dwhoosh"), 0.1), ("lift_at", ("whoosh", "charge"), 0.16)):
            if props.get(key) is not None and float(props[key]) >= 0:
                out.append((f(*snd), float(props[key]), vol))
        return out + ([(f("ding", "popup"), float(props["rings_at"]) + 0.3, 0.1)] if props.get("rings_at") is not None else [])
    if comp == "LotCard":  # card slides in, a ding when the price lands
        at, n = float(props.get("at", 0)), len(props.get("rows") or [])
        return [(f("whoosh", "dwhoosh"), at, 0.14)] + ([(f("ding", "vclick"), at + 0.45 + n * float(props.get("step", 0.22)), 0.16)] if props.get("price") else [])
    if comp == "Building3D":  # outline swipe, then a soft pop as each block starts rising
        out = [(f("swipe", "dwhoosh"), 0.0, 0.12)]
        return out + [(f("pop", "popup"), float(b.get("at", 0)) + 0.4, 0.1) for b in (props.get("buildings") or [])[:6]]
    if comp == "FloorPlan2D":  # walls drawn with a pen, rooms pop, whoosh as it tilts into 3D
        out = [(f("pen", "data"), 0.15, 0.12), (f("pop", "popup"), 1.25, 0.12)]
        return out + ([(f("whoosh", "dwhoosh"), float(props["extrude_at"]), 0.16)] if props.get("extrude_at") is not None else [])
    if comp == "NeonTunnel":  # rush in, a swipe on every clip swap, a hit when the big title lands
        out = [(f("riser", "charge"), 0.0, 0.12), (f("whoosh", "dwhoosh"), 0.3, 0.16)]
        out += [(f("swipe", "dwhoosh"), float(it.get("at", 0)), 0.14) for it in (props.get("items") or [])[1:4] if isinstance(it, dict)]
        return out + ([(f("hit", "thump"), float(props.get("titleAt", 0.6)), 0.18)] if props.get("title") else [])
    if comp == "MapPin":
        at, fly = float(props.get("at", 0)), float(props.get("fly", 1.1))
        return [(f("whoosh", "dwhoosh"), at, 0.16), (f("pop", "popup"), at + fly - 0.05, 0.18), (f("ding", "popup"), at + fly + 0.3, 0.12)]
    return None


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
            if (o.get("_motion") or o.get("comp")) == "BlueText" and "**" in str((o.get("props") or {}).get("text", "")) and "sfx" not in o:
                out.append(("vclick" if viral else "pop", float(o.get("start", 0)) + (starts[int(o["clip"])] if "clip" in o else 0) + 0.05, 0.1))
    for o in plan.get("overlays", []) or []:
        if "sfx" in o:  # explicit: null = silent, name/list = handled as a plan sound
            continue
        # render.prepare_motion turns rendered motion items into "video" overlays (keeping the name in "_motion")
        # before the audio pass, so read the comp from there too, or every motion effect would lose its sound
        comp = o.get("_motion") or o.get("comp")
        ty = "motion" if o.get("_motion") else o.get("type", "text")
        lay = (smap.get(comp, []) if ty == "motion" else tmap.get(ty)
               or (fmap.get(o.get("effect")) if ty == "fx" else None) or [])
        if ty == "frost" and o.get("mode") == "none":
            lay = [("flash" if viral else "camera", 0.0, 0.16)]
        if ty == "motion" and (o.get("half") or (o.get("props") or {}).get("half")) == "back":
            continue
        t0 = float(o.get("start", 0)) + (starts[int(o["clip"])] if "clip" in o else 0)
        if ty == "motion":
            od = (float(o["end"]) - float(o.get("start", 0))) if o.get("end") is not None else float(o.get("duration", 3))
            lay = trend_timed(comp, o.get("props") or {}, od, viral) or lay
        for fam, off, vol in lay:
            out.append((fam, t0 + off, vol))
        # list items that pop in one by one get one sound each
        props = o.get("props") or {}
        if ty == "motion" and comp in ("Tiles", "Checklist", "NotifyStack", "ChatBubbles", "CommentsDrop", "Callouts", "IconSlam"):
            for it in (props.get("items") or [])[1:6]:
                if isinstance(it, dict) and it.get("at") is not None:
                    out.append(("popup" if viral else ("pop" if comp != "IconSlam" else "hit"), t0 + float(it["at"]), 0.15))
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
