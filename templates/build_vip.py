"""VIP edit builder — copy next to the footage (e.g. <folder>/edited/build_vip.py), fill the SCRIPT section, run:
    python build_vip.py            -> plan_vip.json
    python <skill>/scripts/render.py plan_vip.json --draft   (check)  ->  without --draft (final)

Needs aroll.mp4 + aroll.json from scripts/aroll.py (one clip per kept sentence, lip-sync safe).
Every effect below is optional; keep ~1 VIP effect per 3–5 s, always on the word that names it.
Colours are written in the reference blue — "theme" re-colours everything (see references/style.md §Theme).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AR = json.loads((HERE / "aroll.json").read_text(encoding="utf-8"))
STARTS, END = AR["starts"], AR["total"]
SENT = [c["text"] for c in AR["cuts"]]           # sentence i plays from STARTS[i] to STARTS[i+1]

# ---------------------------------------------------------------- settings
THEME = "blue"            # blue | orange | red | gold | blackgold | green | pink | purple | teal | sky | brown | mono | "#RRGGBB"
FACE = (0.5, 0.3)         # where the face is in the frame (0–1) — zooms aim here
CAP_Y = 0.75              # caption height (chest); 0.70 if the speaker sits low
MUSIC = None              # path to an mp3 (royalty-free!) or None -> generated bed (make_music.py) or no music
OUTPUT = "video_vip.mp4"

ov, sfx = [], []


def S(i):  # start of sentence i on the timeline
    return STARTS[i]


def E(i):  # end of sentence i
    return STARTS[i + 1] if i + 1 < len(STARTS) else END


def cap(i, top, text, s=None, e=None, **kw):
    """Two-tier caption for sentence i: small `top` line + big `text` line (markup: **key** _serif_ [pill] ==mark==)."""
    ov.append({"type": "motion", "comp": "BlueText", "start": S(i) if s is None else s, "end": E(i) if e is None else e,
               "props": {"top": top, "text": text, "y": CAP_Y, **kw}})


def motion(comp, s, e, extra=None, **props):
    ov.append({"type": "motion", "comp": comp, "start": round(s, 2), "end": round(e, 2), "props": props, **(extra or {})})


def frost(s, e, mode="light", whoosh=True, **kw):
    ov.append({"type": "frost", "start": round(s, 2), "end": round(e, 2), "mode": mode, **kw})
    if whoosh:
        fx(s - 0.12, "whoosh_air", 0.22)


def layer(kind, s, e, **kw):   # person-aware: bg / popout / lens / fx
    ov.append({"type": kind, "start": round(s, 2), "end": round(e, 2), **kw})


def fx(t, name, vol=0.2):
    sfx.append({"sfx": name, "at": round(max(0, t), 2), "volume": vol})


# ---------------------------------------------------------------- camera: one clip per sentence, alternate moves
HOOK = {"zooms": [{"at": 0, "to": 1.32, "in": 0, "hold": 0.08, "out": 0.32, "x": FACE[0], "y": FACE[1]}]}
PUSH = {"zoom": "in", "zoom_amount": 0.06}
PULL = {"zoom": "out", "zoom_amount": 0.07}
PUNCH = {"punch": 1.15}
SNAP = {"zooms": [{"at": 0, "to": 2.1, "in": 0, "hold": 0.4, "out": 0.45, "x": FACE[0], "y": FACE[1]}]}   # + fx "zoom_vacuum"
EMPH = {"zooms": [{"at": 0.3, "to": 1.25, "in": 0.12, "hold": 1.4, "out": 0.4, "x": FACE[0], "y": FACE[1]}],
        "shake": {"at": 0.3, "dur": 0.35, "amp": 12}}
cam = {0: HOOK}            # sentence index -> move; unlisted sentences cycle PUSH / PUNCH / PULL
cycle = [PUSH, PUNCH, PULL, PUSH, {}]
clips = []
for i in range(len(STARTS)):
    move = cam.get(i, cycle[i % len(cycle)])
    clips.append({"src": AR["src"], "in": S(i), "out": E(i), "focus": FACE[0], **move})

# ---------------------------------------------------------------- SCRIPT: one block per sentence (examples — replace)
# 0  hook: blurred room + giant word behind the head
layer("bg", S(0), E(0), blur=28, fade=0.3)
motion("GiantCaption", S(0) + 0.15, E(0), {"behind": True}, text="EDIT", y=0.17, size=330)
cap(0, "câu mở đầu", "từ **khoá** _cảm xúc_")
fx(0, "whoosh_fast", 0.18)

# a number -> ink spread into the navy grid scene with a count-up
# motion("InkSpread", S(2) - 0.25, S(2) + 0.65, x=0.5, y=0.3, color="#0B1E5E", hold=0.32); fx(S(2) - 0.25, "whoosh_cinematic")
# frost(S(2), E(2), mode="navy", grid=True, whoosh=False, fade_in=0.05)
# motion("CountUp", S(2) + 0.1, E(2), top="chỉ tốn", **{"from": 0, "to": 500, "suffix": "k", "y": 0.36, "ring": True})

# listing things -> Tiles that pop as each is named (at = seconds from the overlay start)
# motion("Tiles", S(3), E(3), y=0.16, items=[{"icon": "🛍️", "label": "Bán hàng", "at": 0.6}, {"icon": "🏠", "label": "BĐS", "at": 1.6}])

# the turn ("nhưng yên tâm") -> person breaks out of a rounded window, headline on top
# layer("popout", S(5), E(5), bg="0xEEF1F8", fade=0.2, window={"crop": [0.05, 0.40, 0.90, 0.32], "pos": [0.5, 0.75], "width": 0.84, "radius": 44})
# motion("BlueBig", S(5), E(5), top="anh em cứ yên tâm", text="**AI** làm được _hết rồi_", tone="light", y=0.15, size=104)

# ---------------------------------------------------------------- plan
music = None
if MUSIC:
    music = {"src": MUSIC, "volume": 0.12, "start": 0, "fade_in": 0.3, "fade_out": 1.5, "duck": True}
plan = {
    "output": OUTPUT,
    "theme": THEME,
    "canvas": {"aspect": "9:16", "fps": 30},
    "font": "Be Vietnam Pro Bold",
    "clips": clips,
    "overlays": ov,
    "sfx": sfx,
    "audio": {**({"music": music} if music else {}), "normalize": -14},
    "fade_out": 0.4,
    "quality": "high",
}
(HERE / "plan_vip.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"plan_vip.json: {len(clips)} clip, {len(ov)} lớp, {len(sfx)} tiếng, màu {THEME}")
