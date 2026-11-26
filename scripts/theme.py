"""Brand colour for the whole edit.

Every effect is designed in a reference blue palette (primary #3158FF, deep navy #0E1530). A plan picks its own
colour with a top-level key and everything blue-ish is re-mapped to it, both in the ffmpeg layers (frost tints,
cards, popout backgrounds, plan colours) and inside the Remotion motion graphics (motion/src/blue/theme.ts runs
the exact same mapping). Neutrals (white, black, greys) and non-blue accents (red stamp, green "answer" button,
gold price tag) are left alone.

    "theme": "cam"                                   # preset name (see PRESETS)
    "theme": "#FF6A1A"                               # any hex: dark tone derived from it
    "theme": {"primary": "#E8B84A", "dark": "#121212"}   # explicit primary + dark (dark #121212 = neutral black)

    python theme.py                 # list presets
    python theme.py cam "#3158FF"   # show what a reference colour becomes
"""
from __future__ import annotations

import colorsys
import re
import sys

REF_PRIMARY = "#3158FF"
REF_DARK = "#0E1530"

PRESETS = {
    # name: (primary, dark)  — Vietnamese + English aliases below
    "blue": ("#3158FF", "#0E1530"),
    "orange": ("#FF6A1A", "#2A1206"),
    "red": ("#E5303C", "#2B0A0E"),
    "gold": ("#E8B84A", "#14110A"),
    "blackgold": ("#E8B84A", "#121212"),
    "green": ("#19B46B", "#062317"),
    "pink": ("#FF4F9A", "#2B0A1C"),
    "purple": ("#7B4DFF", "#150B33"),
    "teal": ("#10B5B0", "#04221F"),
    "sky": ("#1EA7FF", "#06192B"),
    "brown": ("#B8743A", "#1E120A"),
    "mono": ("#2B2B2B", "#111111"),
}
ALIASES = {
    "xanh": "blue", "xanh duong": "blue", "xanh dương": "blue", "xanh biển": "blue", "xanh bien": "blue",
    "cam": "orange", "do": "red", "đỏ": "red", "vang": "gold", "vàng": "gold", "vang kim": "gold", "vàng kim": "gold",
    "den vang": "blackgold", "đen vàng": "blackgold", "đen-vàng": "blackgold", "xanh la": "green", "xanh lá": "green",
    "hong": "pink", "hồng": "pink", "tim": "purple", "tím": "purple", "ngoc": "teal", "ngọc": "teal",
    "xanh ngoc": "teal", "xanh ngọc": "teal", "da troi": "sky", "da trời": "sky", "xanh da trời": "sky",
    "nau": "brown", "nâu": "brown", "den": "mono", "đen": "mono", "đen trắng": "mono",
}

_HEX = re.compile(r"^(#|0x)([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(@[0-9.]+)?$")


def _hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#").replace("0x", "")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _rgb_to_hex(r, g, b) -> str:
    return "#" + "".join(f"{max(0, min(255, round(v * 255))):02X}" for v in (r, g, b))


def _hsl(hx: str):
    r, g, b = _hex_to_rgb(hx)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s, l


def resolve(theme) -> dict | None:
    """theme value from a plan -> {"primary", "dark"} or None for the reference blue (no mapping)."""
    if not theme:
        return None
    if isinstance(theme, dict):
        p = theme.get("primary") or theme.get("color")
        if not p:
            return None
        p = _norm(p)
        d = _norm(theme["dark"]) if theme.get("dark") else _derive_dark(p)
    else:
        key = str(theme).strip().lower()
        key = ALIASES.get(key, key)
        if key in PRESETS:
            p, d = PRESETS[key]
        elif _HEX.match(str(theme).strip()):
            p = _norm(str(theme).strip())
            d = _derive_dark(p)
        else:
            raise ValueError(f"theme '{theme}' không hiểu — dùng mã #RRGGBB hoặc một trong: {', '.join(PRESETS)}")
    kw = theme.get("keyword") if isinstance(theme, dict) else None
    if p.upper() == REF_PRIMARY and d.upper() == REF_DARK and not kw:
        return None
    out = {"primary": p.upper(), "dark": d.upper()}
    if kw:  # "solid": caption keywords on footage in the real brand colour (pale red/orange reads pink/peach)
        out["keyword"] = str(kw)
    return out


def _norm(c: str) -> str:
    c = c.strip()
    if c.startswith("0x"):
        c = "#" + c[2:]
    m = _HEX.match(c)
    if not m:
        raise ValueError(f"mã màu sai: {c}")
    return "#" + m.group(2) if len(m.group(2)) == 6 else _rgb_to_hex(*_hex_to_rgb(m.group(2)))


def _derive_dark(p: str) -> str:
    h, s, _ = _hsl(p)
    r, g, b = colorsys.hls_to_rgb(h / 360, 0.1, min(s, 0.6))
    return _rgb_to_hex(r, g, b)


def map_rgb(r: float, g: float, b: float, th: dict) -> tuple[float, float, float]:
    """Core mapping (kept identical to motion/src/blue/theme.ts mapRGB)."""
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h *= 360
    if s < 0.12 or not (195 <= h <= 265):
        return r, g, b
    ph, ps, pl = _hsl(th["primary"])
    dh, ds, dl = _hsl(th["dark"])
    _, rs, rl = _hsl(REF_PRIMARY)
    _, rds, rdl = _hsl(REF_DARK)
    if l >= 0.32:  # mid + light tones follow the primary
        nh = ph + (h - 229) * 0.4
        ns = min(1.0, s * ps / rs)
        w = max(0.0, 1 - abs(l - rl) / 0.36)
        nl = min(0.98, max(0.0, l + (pl - rl) * w))
    else:  # deep tones follow the dark colour
        nh = dh + (h - 228) * 0.3
        ns = min(1.0, s * (ds / rds if rds else 0), ds + 0.1)
        nl = max(0.0, min(0.45, l + (dl - rdl) * 0.8))
    return colorsys.hls_to_rgb((nh % 360) / 360, nl, ns)


def map_color(c: str, th: dict | None) -> str:
    """Map one colour string (#RGB, #RRGGBB, 0xRRGGBB, 0xRRGGBB@a) keeping its format."""
    if not th or not isinstance(c, str):
        return c
    m = _HEX.match(c.strip())
    if not m:
        return c
    pre, body, alpha = m.group(1), m.group(2), m.group(3) or ""
    out = _rgb_to_hex(*map_rgb(*_hex_to_rgb(body), th))
    return (out if pre == "#" else "0x" + out[1:]) + alpha


def _walk(v, th):
    if isinstance(v, dict):
        return {k: (v[k] if k == "theme" else _walk(v[k], th)) for k in v}
    if isinstance(v, list):
        return [_walk(x, th) for x in v]
    if isinstance(v, str):
        return map_color(v, th)
    return v


CURRENT: dict | None = None  # palette of the plan being rendered (set by apply)


def apply(plan: dict) -> dict:
    """Re-colour a whole plan and hand the palette to every motion overlay (props.theme)."""
    global CURRENT
    th = CURRENT = resolve(plan.get("theme"))
    if not th:
        return plan
    out = _walk(plan, th)
    for o in out.get("overlays", []) or []:
        if o.get("type") == "motion":
            o["props"] = {**(o.get("props") or {}), "theme": th}
    return out


def tint(value: str) -> str:
    """A built-in default colour (frost tints, card / popout backgrounds) in the current plan's palette."""
    return map_color(value, CURRENT)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        for k, (p, d) in PRESETS.items():
            al = [a for a, v in ALIASES.items() if v == k]
            print(f"{k:10s} {p} / {d}   {', '.join(al)}")
        sys.exit()
    t = resolve(sys.argv[1])
    for c in sys.argv[2:] or [REF_PRIMARY, "#8EB3FF", "#0B1E5E", "0xEEF1F8@1", "#FFFFFF", "#FF3B5C"]:
        print(c, "->", map_color(c, t))
