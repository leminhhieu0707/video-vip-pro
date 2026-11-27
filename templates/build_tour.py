"""TOUR builder — a property walkthrough (B-roll + voice-over) cut like the top US listing editors, measured frame by
frame: short B-roll shots (0.9–1.7 s), mostly hard cuts, a few "expensive" moves on the big changes, three-tier
captions on the words, a crisp grade, whooshes only on the big moves. See references/recipes.md → "Walkthrough tour".

Copy next to the footage (e.g. <folder>/edited/build_tour.py), fill SETTINGS + SHOTS + WORDS, run:
    python build_tour.py                          -> plan_tour.json
    python <skill>/scripts/render.py plan_tour.json --draft     (check)  ->  without --draft (final)
    python <skill>/editor/server.py plan_tour.json              (hand edits, 0 token)

Shot moves (one per shot, keep most shots plain):
    "cut"      hard cut (default; ~80 % of the cuts)
    "spin"     rotating whip into this shot (1 soft frame, 3 spinning, 4 settling) — the first big room change
    "push"     THIS shot speeds up ~4x and pushes in faster and faster, the NEXT shot lands still moving (give the next
               shot "land": True) — outside -> inside, door -> room. Pick footage that walks forward.
    "dissolve" 2-frame mix — a soft change between two calm shots (inside -> balcony)
    "punch"    {"at": s, "x": 0.1, "y": 0.65}: 1.3x punch zoom in 9 frames on the keyword, aimed at the object (x, y)
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = Path(os.environ.get("VIP_SKILL", Path.home() / ".claude" / "skills" / "video-vip-pro"))  # where the skill lives

# ---------------------------------------------------------------- SETTINGS
SRC = "raw/walkthrough.mp4"          # the walkthrough clip(s); a shot may name its own "src"
VO = "vo.wav"                        # voice-over file (or None)
VO_TRANSCRIPT = "vo.transcript.json" # word times of the voice-over (scripts/transcribe.py)
VO_IN = 0.0                          # where the used part of the voice-over starts in VO (s)
DUR = 10.0                           # length of the tour (s)
MUSIC = None                         # royalty-free mp3 or None
GRADE = "bds_net"                    # bds_net (crisp listing look) | bright | warm | cinematic ...
OUTPUT = "tour.mp4"
# caption colours: key words get a gradient. Defaults are the measured listing palette (aqua / lime);
# swap to the brand colour when the user has one (e.g. gold ['#F5D77A', '#C9A227']).
AQUA = ["#16EFFD", "#7DF9FF"]
LIME = ["#E3E655", "#B4DD35"]

# ---------------------------------------------------------------- SHOTS  (timeline length "d"; source start "in")
# speed 1.0 = real time. Example: a 10 s apartment tour.
SHOTS = [
    {"in": 1.9, "d": 1.30},                                   # entrance, the door opens
    {"in": 8.0, "d": 0.70, "move": "push"},                   # walk to the window, accelerating
    {"in": 32.4, "d": 1.20, "land": True},                    # balcony view, lands still moving
    {"in": 23.8, "d": 1.20, "move": "spin"},                  # built-in cabinets
    {"in": 18.2, "d": 1.00},                                  # kitchen
    {"in": 66.2, "d": 1.05, "move": "dissolve"},              # bathroom
    {"in": 4.6, "d": 0.85, "move": {"punch": {"at": 0.40, "x": 0.1, "y": 0.65}}},   # smart lock
    {"in": 95.8, "d": 2.70, "zoom": 0.10},                    # corner bedroom, slow push to the end
]

# ---------------------------------------------------------------- WORDS  (three-tier lockups on the voice-over)
# Each group: thin = small hairline words (top-left), key = the big word, tail = small words (bottom-right).
# Times are in VOICE-OVER seconds (from VO_TRANSCRIPT); they are shifted by VO_IN automatically.
# key_tilt 0 = upright key, -9 = slanted (use slanted for the "how / smart" kind of emphasis words).
GROUPS = [
    {"thin": ["căn hộ", 28.10], "key": ["THẬT", 28.44], "tail": ["lúc bàn giao", 28.62], "end": 29.40, "grad": AQUA},
    {"thin": ["kính", 29.50], "key": ["TRÀN VIỀN", 29.68], "tail": ["đón trọn view", 30.06], "end": 30.63, "grad": AQUA},
    {"thin": ["nội thất", 31.00], "key": ["liền tường", 31.32], "end": 31.85, "grad": LIME, "key_tilt": -9},
    {"thin": ["thiết bị", 32.36], "key": ["QUỐC TẾ", 33.28], "tail": ["bếp · vệ sinh", 32.45], "end": 33.88, "grad": AQUA},
    {"thin": ["khoá cửa", 33.98], "key": ["thông minh", 34.30], "end": 34.75, "grad": LIME, "key_tilt": -9, "y": 0.78},
    {"thin": ["căn hộ từ", 34.80], "key": ["47m²", 36.36], "tail": ["1 phòng ngủ +", 35.36], "end": 37.30, "grad": AQUA},
]
Y = 0.33          # vertical centre of the lockups (keep text over calm wall / sky, never on a bright window)


# ================================================================ builder (no need to edit below)
def ramp_factor(spec):
    """timeline length per source second for a ramp curve (render.ramp_map is linear in the source length)."""
    sys.path.insert(0, str(SKILL / "scripts"))
    import render
    return render.ramp_map(spec, 1.0)[1]


clips, ov, sfx = [], [], []
t = 0.0
for i, s in enumerate(SHOTS):
    c = {"src": s.get("src", SRC), "mute": True, "fit": "crop"}
    mv = s.get("move", "cut")
    d = float(s["d"])
    if mv == "push":
        f = ramp_factor("push_out")
        c.update({"in": s["in"], "out": round(s["in"] + d / f, 3), "ramp": "push_out",
                  "zoom": "in", "zoom_amount": 0.32, "zoom_ease": "in"})
        sfx.append({"sfx": "whoosh2", "at": round(t + d - 0.55, 2), "volume": 0.5})   # builds into the cut
    elif s.get("land"):
        f = ramp_factor("push_in")
        c.update({"in": s["in"], "out": round(s["in"] + d / f, 3), "ramp": "push_in",
                  "zoom": "in", "zoom_amount": 0.22, "zoom_ease": "out"})
    else:
        c.update({"in": s["in"], "out": round(s["in"] + d * s.get("speed", 1.0), 3)})
        if s.get("speed", 1.0) != 1.0:
            c["speed"] = s["speed"]
        c.update({"zoom": "in", "zoom_amount": s.get("zoom", 0.03)})
    if mv == "spin":
        c["transition"] = {"type": "spinwhip", "dir": s.get("dir", "left")}
        sfx.append({"sfx": "whoosh", "at": round(t - 0.25, 2), "volume": 0.55})
    elif mv == "dissolve":
        c["transition"] = {"type": "dissolve", "duration": 0.067}
    elif isinstance(mv, dict) and "punch" in mv:
        p = mv["punch"]
        c["zooms"] = [{"at": p["at"], "to": p.get("to", 1.3), "in": 0.3, "out": None, "x": p.get("x", 0.5),
                       "y": p.get("y", 0.5), "blur": True}]
    clips.append(c)
    t += d

for g in GROUPS:
    words = []
    a = min(x[1] for x in (g.get("thin"), g.get("key"), g.get("tail")) if x) - VO_IN
    for tier, k in (("thin", 0), ("key", 1), ("tail", 0)):
        if g.get(tier):
            words.append({"w": g[tier][0], "t": round(g[tier][1] - VO_IN - a, 3), "k": k})
    ov.append({"type": "motion", "comp": "WordStack", "start": round(a, 3), "end": round(g["end"] - VO_IN, 3),
               "props": {"words": words, "x": 0.5, "y": g.get("y", Y), "key_size": 230, "grad": g.get("grad", AQUA),
                         "tilt": g.get("key_tilt", 0), "enter": "flicker", "max_w": 0.86,
                         "font": "MON", "key_weight": 800}})

plan = {
    "output": OUTPUT,
    "canvas": {"width": 1080, "height": 1920, "fps": 30, "fit": "crop"},
    "keep_timing": True,
    "clip_defaults": {"grade": GRADE, "beauty": 0},
    "clips": clips,
    "overlays": ov,
    "sfx": sfx,
    "audio": {"original_volume": 0, "normalize": -14,
              "voiceover": ([{"src": VO, "in": VO_IN, "out": VO_IN + DUR, "start": 0, "volume": 1.0}] if VO else []),
              **({"music": {"src": MUSIC, "volume": 0.16, "duck": True, "fade_out": 0.8}} if MUSIC else {})},
}
(HERE / "plan_tour.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"plan_tour.json: {len(clips)} shots, {len(ov)} lockups, {len(sfx)} whooshes, {t:.2f}s")
