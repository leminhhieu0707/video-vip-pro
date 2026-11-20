"""Build one .ass file holding subtitles + all text overlays (labels, titles, badges, free text).

libass renders it in a single ffmpeg pass, so text is crisp, animated, and Vietnamese-safe.
All coordinates are in canvas pixels (PlayResX/Y = canvas size).
"""
from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path

from common import ass_color, ass_inline_color, find_font, font_is_bold_variant, font_scale, load_json, parse_time, ts

# ------------------------------------------------------------------ positions

NAMED_POS = {
    "top": (0.5, 0.12), "upper": (0.5, 0.25), "center": (0.5, 0.5), "middle": (0.5, 0.5),
    "lower": (0.5, 0.68), "bottom": (0.5, 0.86),
    "top-left": (0.22, 0.12), "top-right": (0.78, 0.12), "bottom-left": (0.22, 0.86), "bottom-right": (0.78, 0.86),
    "left": (0.25, 0.45), "right": (0.75, 0.45),
}


def resolve_pos(pos, W: int, H: int, default="center") -> tuple[int, int]:
    pos = pos if pos is not None else default
    if isinstance(pos, str):
        fx, fy = NAMED_POS.get(pos, NAMED_POS[default])
    else:
        fx, fy = pos
    # Accept fractions (<=1) or pixels.
    x = fx * W if fx <= 1 else fx
    y = fy * H if fy <= 1 else fy
    return int(round(x)), int(round(y))


def est_width(text: str, size: float) -> float:
    """Rough rendered width for clip/wipe animations."""
    return sum(size * (0.32 if ch == " " else 0.62 if ch.isupper() or ch.isdigit() else 0.52) for ch in text)


def esc(text: str) -> str:
    text = unicodedata.normalize("NFC", str(text))
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


# ------------------------------------------------------------------ document

class AssDoc:
    def __init__(self, W: int, H: int, fonts_dir: Path):
        self.W, self.H = W, H
        self.base = min(W, H)
        self.styles: dict[str, str] = {}
        self.events: list[tuple[int, float, str]] = []  # (layer, start, line)
        self.fonts_dir = fonts_dir
        fonts_dir.mkdir(parents=True, exist_ok=True)

    def font(self, name: str | None) -> tuple[str, int]:
        """Return (family, bold_flag). Copies the font file next to the .ass for libass."""
        fam, f = find_font(name)
        if f:
            dst = self.fonts_dir / f.name
            if not dst.exists():
                shutil.copy(f, dst)
        # If the file itself is a bold face whose family isn't named "... Bold", ask libass for bold.
        bold = -1 if (f and font_is_bold_variant(f)) or (name and "bold" in name.lower()) else 0
        return fam, bold

    def scale(self, name: str | None) -> float:
        """Nominal->libass size factor so every font has Arial-like visual size."""
        return font_scale(find_font(name)[1])

    def lh(self, font: str | None, size: float) -> float:
        """Rendered line (box) height for a nominal size."""
        return size * self.scale(font)

    def style(self, name, font=None, size=60, color="white", outline_color="black", back_color="black",
              outline=4.0, shadow=0.0, border_style=1, align=5, margin_v=0, bold=None, spacing=0, back_alpha=0.6,
              outline_alpha=1.0, color_alpha=1.0):
        fam, fbold = self.font(font)
        b = fbold if bold is None else (-1 if bold else 0)
        size = size * self.scale(font)
        self.styles[name] = (
            f"Style: {name},{fam},{int(round(size))},{ass_color(color, color_alpha)},{ass_color(color, color_alpha)},"
            f"{ass_color(outline_color, outline_alpha)},{ass_color(back_color, back_alpha)},{b},0,0,0,100,100,"
            f"{spacing},0,{border_style},{outline},{shadow},{align},20,20,{int(margin_v)},1")
        return name

    def add(self, start, end, style, text, layer=0):
        self.events.append((layer, start, f"Dialogue: {layer},{ts(start)},{ts(end)},{style},,0,0,0,,{text}"))

    def write(self, path: Path):
        head = (
            "[Script Info]\nScriptType: v4.00+\nWrapStyle: 0\nScaledBorderAndShadow: yes\n"
            f"PlayResX: {self.W}\nPlayResY: {self.H}\nYCbCr Matrix: TV.709\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        )
        body = "\n".join(self.styles.values())
        evs = "\n".join(e[2] for e in sorted(self.events, key=lambda e: (e[1], e[0])))
        path.write_text(head + body + "\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
                        "MarginV, Effect, Text\n" + evs + "\n", encoding="utf-8-sig")


# ------------------------------------------------------------------ animations

def anim_tags(anim: str | None, dur: float, x: int, y: int, W: int, H: int, text_w: float, size: float,
              fade_out: bool = True) -> str:
    """Override tags for entrance animation (+ short fade out)."""
    anim = (anim or "pop").lower()
    out_ms = 150 if fade_out and dur > 0.6 else 0
    if anim == "none":
        return f"\\pos({x},{y})"
    if anim == "fade":
        return f"\\pos({x},{y})\\fad(250,{out_ms or 0})"
    if anim == "pop":
        return (f"\\pos({x},{y})\\fad(60,{out_ms})\\fscx30\\fscy30"
                f"\\t(0,140,\\fscx112\\fscy112)\\t(140,240,\\fscx100\\fscy100)")
    if anim == "bounce":
        return (f"\\pos({x},{y})\\fad(60,{out_ms})\\fscx0\\fscy0\\t(0,160,\\fscx125\\fscy125)"
                f"\\t(160,260,\\fscx90\\fscy90)\\t(260,340,\\fscx100\\fscy100)")
    if anim in ("slide-left", "slide-right"):
        sx = W + text_w / 2 if anim == "slide-left" else -text_w / 2
        return f"\\move({int(sx)},{y},{x},{y},0,280)\\fad(0,{out_ms})"
    if anim in ("slide-up", "slide-down"):
        sy = y + size * 1.5 if anim == "slide-up" else y - size * 1.5
        return f"\\move({x},{int(sy)},{x},{y},0,260)\\fad(200,{out_ms})"
    if anim == "wipe":
        x0 = int(x - text_w * 0.75 - size)
        return f"\\pos({x},{y})\\clip(0,0,{max(0, x0)},{H})\\t(0,450,\\clip(0,0,{W},{H}))\\fad(0,{out_ms})"
    if anim == "zoom":
        return f"\\pos({x},{y})\\fad(200,{out_ms})\\fscx140\\fscy140\\t(0,300,\\fscx100\\fscy100)"
    if anim in ("blurin", "blur"):
        # kiểu chữ video BĐS cao cấp: từ nhoè → nét, hơi thu nhỏ + trôi lên nhẹ, tắt bằng nhoè dần
        d = int(dur * 1000)
        return (f"\\move({x},{int(y + size * 0.16)},{x},{y},0,420)\\fad(260,300)\\blur18\\fscx110\\fscy110"
                f"\\t(0,420,0.55,\\blur0\\fscx100\\fscy100)\\t({max(0, d - 320)},{d},\\blur14)")
    if anim == "shake":
        return (f"\\pos({x},{y})\\fad(60,{out_ms})\\frz-6\\t(0,80,\\frz6)\\t(80,160,\\frz-4)"
                f"\\t(160,240,\\frz3)\\t(240,320,\\frz0)")
    return f"\\pos({x},{y})"


def pulse_tags(dur: float) -> str:
    """Gentle breathing scale for emphasis, repeated across the event."""
    tags, t, up = [], 400, True
    while t < dur * 1000 - 300:
        s = 106 if up else 100
        tags.append(f"\\t({t},{t + 400},\\fscx{s}\\fscy{s})")
        t += 400
        up = not up
    return "".join(tags)


# ------------------------------------------------------------------ overlays

def _times(o: dict, clip_starts: list[float]) -> tuple[float, float]:
    off = clip_starts[int(o["clip"])] if "clip" in o and clip_starts else 0.0
    s = parse_time(o.get("start", 0)) + off
    e = parse_time(o["end"]) + off if "end" in o else s + parse_time(o.get("duration", 3))
    # clip-anchored text leaves when the next clip starts (incl. transition overlap), unless "span": true
    if "clip" in o and not o.get("span") and int(o["clip"]) + 1 < len(clip_starts):
        e = min(e, clip_starts[int(o["clip"]) + 1] + 0.04)
    return s, e


# ------------------------------------------------------------------ premium price card

def text_width(font: str | None, size: float, text: str) -> float:
    """Rendered width in canvas px of `text` at nominal `size` (same scaling AssDoc.style applies).
    libass maps font size to winAscent+winDescent, so advance_px = adv * size / (winA + winD)."""
    from common import find_font
    _, f = find_font(font)
    if not f:
        return est_width(text, size)
    try:
        from fontTools.ttLib import TTFont
        tt = _tt_cache.get(f) or _tt_cache.setdefault(f, TTFont(f, lazy=True))
        cmap, hmtx, os2 = tt.getBestCmap(), tt["hmtx"], tt["OS/2"]
        units = sum(hmtx[cmap.get(ord(ch), cmap.get(32))][0] if cmap.get(ord(ch)) else hmtx[cmap[32]][0]
                    for ch in unicodedata.normalize("NFC", text))
        return units * size * font_scale(f) / (os2.usWinAscent + os2.usWinDescent)
    except Exception:
        return est_width(text, size)


_tt_cache: dict = {}


def rrect(x0: float, y0: float, w: float, h: float, r: float) -> str:
    """ASS vector path of a rounded rectangle (absolute coords)."""
    x1, y1 = x0 + w, y0 + h
    k = r * 0.45  # bezier handle
    f = lambda v: f"{v:.0f}"  # noqa: E731
    return (f"m {f(x0 + r)} {f(y0)} l {f(x1 - r)} {f(y0)} b {f(x1 - k)} {f(y0)} {f(x1)} {f(y0 + k)} {f(x1)} {f(y0 + r)} "
            f"l {f(x1)} {f(y1 - r)} b {f(x1)} {f(y1 - k)} {f(x1 - k)} {f(y1)} {f(x1 - r)} {f(y1)} "
            f"l {f(x0 + r)} {f(y1)} b {f(x0 + k)} {f(y1)} {f(x0)} {f(y1 - k)} {f(x0)} {f(y1 - r)} "
            f"l {f(x0)} {f(y0 + r)} b {f(x0)} {f(y0 + k)} {f(x0 + k)} {f(y0)} {f(x0 + r)} {f(y0)}")


def _parse_amount(s: str) -> tuple[str, int, str] | None:
    """'8.190.000đ' -> ('', 8190000, 'đ'); None if no number to count."""
    m = re.match(r"^(\D*?)([\d.,]+)(\D*)$", s.strip())
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(2))
    return (m.group(1), int(digits), m.group(3)) if digits else None


def _fmt_amount(v: int, template: str) -> str:
    sep = "." if "." in template else ("," if "," in template else "")
    s = f"{v:,}"
    return s.replace(",", sep) if sep else str(v)


def add_price_card(doc: AssDoc, o: dict, idx: int, s: float, e: float, font: str | None):
    """Premium price card: rounded dark glass card with gold border + soft shadow, small caption line,
    big gold price with glow, number count-up, settle bounce, and a light sweep across the card.
      {"type":"price","title":"iPhone 12 Pro Max","prefix":"Từ","text":"8.190.000đ","pos":[0.5,0.15],
       "accent":"#F5C542","card":"#0B0B0F","count":true}"""
    W, H, base = doc.W, doc.H, doc.base
    accent = o.get("accent", "#F5C542")
    card_c = o.get("card", "#0B0B0F")
    title = str(o.get("title", ""))
    prefix = str(o.get("prefix", "")).strip()
    value = str(o.get("text", ""))
    s1 = o.get("title_size", base * 0.048)
    s2 = o.get("size", base * 0.1)
    sp = s2 * 0.5  # prefix size
    pad_x, pad_y, gap = base * 0.04, base * 0.026, base * 0.012
    w_title = text_width(font, s1, title) if title else 0
    w_val = text_width(font, s2, value) * 1.1  # headroom: measured advances run ~8% short + settle bounce
    w_pre = text_width(font, sp, prefix + " ") if prefix else 0
    lh1, lh2 = doc.lh(font, s1) if title else 0, doc.lh(font, s2)
    cw = max(w_title, w_pre + w_val) + 2 * pad_x
    ch = pad_y * 2 + lh1 + (gap if title else 0) + lh2 * 0.92
    cx, cy = resolve_pos(o.get("pos"), W, H, "top")
    x0, y0 = cx - cw / 2, cy - ch / 2
    r = min(base * 0.03, ch / 3)
    t_ms = lambda sec: int(sec * 1000)  # noqa: E731
    dur = e - s
    out_ms = 200

    shape = doc.style(f"PcShape{idx}", font, 20, "white", "black", outline=0, shadow=0, align=7)
    st1 = doc.style(f"PcT{idx}", font, s1, "#E8E8EA", "black", outline=0, shadow=0, align=7)
    st2 = doc.style(f"PcV{idx}", font, s2, accent, accent, outline=0, shadow=0, align=7)
    stp = doc.style(f"PcP{idx}", font, sp, accent, "black", outline=0, shadow=0, align=1)

    path = rrect(0, 0, cw, ch, r)
    pop = "\\fscx70\\fscy70\\t(0,160,\\fscx104\\fscy104)\\t(160,260,\\fscx100\\fscy100)"
    org = f"\\org({cx:.0f},{cy:.0f})"
    # soft shadow, card body, gold border (drawn as separate layers so the border stays crisp)
    doc.add(s, e, shape, f"{{\\an5\\pos({cx:.0f},{cy + base * 0.012:.0f}){org}\\p1\\c&H000000&\\alpha&H70&\\bord0"
                         f"\\blur{base * 0.02:.0f}{pop}\\fad(120,{out_ms})}}{path}", 10)
    doc.add(s, e, shape, f"{{\\an5\\pos({cx:.0f},{cy:.0f}){org}\\p1\\c{ass_inline_color(card_c)}\\alpha&H26&"
                         f"\\bord{max(2, base * 0.0028):.1f}\\3c{ass_inline_color(accent)}\\3a&H10&\\shad0"
                         f"{pop}\\fad(120,{out_ms})}}{path}", 11)
    # light sweep across the card (clipped to the card shape)
    if o.get("shine", True) and dur > 1.4:
        sw = cw * 0.18
        shine = f"m 0 0 l {sw:.0f} 0 l {sw * 0.55:.0f} {ch:.0f} l {-sw * 0.45:.0f} {ch:.0f}"
        clip = rrect(x0, y0, cw, ch, r)
        t1, t2 = 750, 1250
        doc.add(s + t1 / 1000, min(e, s + t2 / 1000 + 0.05), shape,
                f"{{\\an7\\move({x0 - sw:.0f},{y0:.0f},{x0 + cw + sw:.0f},{y0:.0f},0,{t2 - t1})\\p1"
                f"\\c&HFFFFFF&\\alpha&HA0&\\bord0\\blur{base * 0.006:.0f}\\clip({clip})}}{shine}", 15)

    tx = x0 + pad_x
    y_title = y0 + pad_y
    y_val_bottom = y0 + ch - pad_y * 0.75
    if title:
        doc.add(s + 0.08, e, st1, f"{{\\an7\\move({tx:.0f},{y_title + base * 0.015:.0f},{tx:.0f},{y_title:.0f},0,220)"
                                  f"\\fad(180,{out_ms})\\fsp1}}{esc(title.upper() if o.get('uppercase') else title)}", 13)
        # thin gold rule under the caption
        doc.add(s + 0.15, e, shape, f"{{\\an7\\pos({tx:.0f},{y_title + lh1 + gap * 0.35:.0f})\\p1"
                                    f"\\c{ass_inline_color(accent)}\\alpha&H40&\\bord0\\fscx0\\t(0,350,\\fscx100)"
                                    f"\\fad(0,{out_ms})}}m 0 0 l {min(cw - 2 * pad_x, base * 0.12):.0f} 0 "
                                    f"l {min(cw - 2 * pad_x, base * 0.12):.0f} 3 l 0 3", 13)
    if prefix:
        doc.add(s + 0.12, e, stp, f"{{\\an1\\pos({tx:.0f},{y_val_bottom - lh2 * 0.14:.0f})\\fad(180,{out_ms})}}"
                                  f"{esc(prefix)}", 13)
    vx = tx + w_pre
    amount = _parse_amount(value) if o.get("count", True) else None
    glow = f"\\3c{ass_inline_color(accent)}\\bord{base * 0.006:.0f}\\3a&HB0&\\blur{base * 0.008:.0f}"
    vpos = f"\\an1\\pos({vx:.0f},{y_val_bottom:.0f})"
    count_start, count_len = 0.18, min(0.7, max(0.0, dur - 1.0))
    if amount and count_len > 0.2:
        pre, num, suf = amount
        steps = int(count_len * 30)
        num_part = re.search(r"[\d.,]+", value).group(0)
        for k in range(steps):
            p = (k + 1) / steps
            ease = 1 - (1 - p) ** 3
            v = int(num * ease) // 10_000 * 10_000 if num >= 100_000 else int(num * ease)
            ts0 = s + count_start + k * count_len / steps
            ts1 = s + count_start + (k + 1) * count_len / steps
            txt = esc(pre + _fmt_amount(v, num_part) + suf)
            fade = "\\fad(120,0)" if k == 0 else ""
            doc.add(ts0, ts1, st2, f"{{{vpos}{glow}{fade}}}{txt}", 14)
        settle = s + count_start + count_len
        doc.add(settle, e, st2, f"{{{vpos}{glow}\\fscx112\\fscy112\\t(0,180,\\fscx100\\fscy100)"
                                f"\\fad(0,{out_ms})}}{esc(value)}", 14)
    else:
        doc.add(s + 0.15, e, st2, f"{{{vpos}{glow}\\fad(160,{out_ms})\\fscx85\\fscy85"
                                  f"\\t(0,200,\\fscx100\\fscy100)}}{esc(value)}", 14)


def add_overlay(doc: AssDoc, o: dict, idx: int, clip_starts: list[float], defaults: dict):
    W, H, base = doc.W, doc.H, doc.base
    t = o.get("type", "text")
    s, e = _times(o, clip_starts)
    dur = e - s
    font = o.get("font") or defaults.get("font")
    upper = o.get("uppercase", t in ("label", "title"))

    def U(x):
        return str(x).upper() if upper else str(x)

    rot = f"\\frz{o['rotate']}" if "rotate" in o else ""
    pulse = pulse_tags(dur) if o.get("pulse") else ""

    if t == "price":
        add_price_card(doc, o, idx, s, e, font)
        return

    if t == "progress":
        # thin bar that fills left -> right over [s, e]; keeps viewers watching to the end
        h = int(o.get("height", base * 0.011))
        y = int(resolve_pos(o.get("pos", [0.5, 0.006]), W, H)[1])
        st = doc.style(f"Prog{idx}", font, 20, "white", "black", outline=0, shadow=0, align=7)
        track = f"m 0 0 l {W} 0 l {W} {h} l 0 {h}"
        doc.add(s, e, st, f"{{\\an7\\pos(0,{y})\\p1\\c{ass_inline_color(o.get('track', '#000000'))}\\alpha&H90&"
                          f"\\bord0\\shad0}}{track}", 20)
        ms = int((e - s) * 1000)
        doc.add(s, e, st, f"{{\\an7\\pos(0,{y})\\p1\\c{ass_inline_color(o.get('color', '#E11D2E'))}\\bord0\\shad0"
                          f"\\clip(0,0,1,{H})\\t(0,{ms},\\clip(0,0,{W},{H}))}}{track}", 21)
        return

    if t == "label":
        # Two-tier tag: small colored title box above a big value box (price tags, specs, stats).
        x, y = resolve_pos(o.get("pos"), W, H, "left")
        tsz = o.get("title_size", base * 0.05)
        vsz = o.get("size", base * 0.095)
        rot = f"\\frz{o.get('rotate', 3)}"
        title, value = U(o.get("title", "")), str(o.get("text", ""))
        pad_t, pad_v = tsz * 0.35, vsz * 0.28
        st = doc.style(f"LblT{idx}", font, tsz, o.get("title_color", "white"), o.get("title_bg", "red"),
                       outline=pad_t, border_style=3, align=5, back_alpha=0)
        sv = doc.style(f"LblV{idx}", font, vsz, o.get("color", "#111111"), o.get("bg", "white"),
                       outline=pad_v, border_style=3, align=5, back_alpha=0)
        wv = max(est_width(value, vsz), est_width(title, tsz))
        ty = int(y - doc.lh(font, vsz) / 2 - pad_v - doc.lh(font, tsz) / 2 - pad_t + 2)
        tx = int(x - (est_width(value, vsz) - est_width(title, tsz)) / 2 * 0.6)  # title leans left like a tag
        anim = o.get("anim", "pop")
        if title:
            doc.add(s, e, st, "{" + anim_tags(anim, dur, tx, ty, W, H, wv, tsz) + rot + "}" + esc(title), 2)
        vanim = "wipe" if anim == "pop" and o.get("value_wipe", True) else anim
        doc.add(s + (0.12 if title else 0), e, sv,
                "{" + anim_tags(vanim, dur, x, y, W, H, wv, vsz) + rot + pulse + "}" + esc(value), 1)
        return

    if t == "title":
        # Headline: big outlined text, optional highlighted second line on a colored box.
        x, y = resolve_pos(o.get("pos"), W, H, "top")
        sz = o.get("size", base * 0.08)
        st = doc.style(f"Ttl{idx}", font, sz, o.get("color", "white"), o.get("outline_color", "black"),
                       outline=o.get("outline", sz * 0.11), shadow=o.get("shadow", 3), align=5, back_alpha=0.5)
        anim = o.get("anim", "slide-up")
        text = U(o.get("text", ""))
        doc.add(s, e, st, "{" + anim_tags(anim, dur, x, y, W, H, est_width(text, sz), sz) + rot + "}" + esc(text), 3)
        if o.get("highlight"):
            hs = o.get("highlight_size", sz * 1.0)
            pad = hs * 0.22
            sh = doc.style(f"TtlH{idx}", font, hs, o.get("highlight_color", "white"), o.get("highlight_bg", "red"),
                           outline=pad, border_style=3, align=5, back_alpha=0)
            hy = int(y + doc.lh(font, sz) * 0.55 + doc.lh(font, hs) * 0.5 + pad + 6)
            htext = U(o["highlight"])
            doc.add(s + 0.15, e, sh, "{" + anim_tags("pop", dur, x, hy, W, H, est_width(htext, hs), hs)
                    + rot + pulse + "}" + esc(htext), 3)
        return

    if t == "badge":
        # Single pill/box: "1 đổi 1 trong 30 ngày", "FREESHIP", "-50%".
        x, y = resolve_pos(o.get("pos"), W, H, "center")
        sz = o.get("size", base * 0.055)
        pad = sz * 0.4
        sb = doc.style(f"Bdg{idx}", font, sz, o.get("color", "white"), o.get("bg", "blue"),
                       outline=pad, border_style=3, align=5, back_alpha=0)
        text = U(o.get("text", ""))
        icon = o.get("icon")
        if icon == "dot":  # blinking dot before the text, like a live/notification bullet
            text = "{\\c" + ass_inline_color(o.get("icon_color", "#22C55E")) + "}●{\\c" + \
                   ass_inline_color(o.get("color", "white")) + "} " + esc(text)
        else:
            text = esc(text)
        doc.add(s, e, sb, "{" + anim_tags(o.get("anim", "slide-left"), dur, x, y, W, H, est_width(text, sz), sz)
                + rot + pulse + "}" + text, 2)
        return

    # Generic text
    x, y = resolve_pos(o.get("pos"), W, H, "center")
    sz = o.get("size", base * 0.06)
    if o.get("bg"):
        st = doc.style(f"Txt{idx}", font, sz, o.get("color", "white"), o["bg"], outline=sz * 0.3, border_style=3,
                       align=5, back_alpha=0, bold=o.get("bold"))
    else:
        st = doc.style(f"Txt{idx}", font, sz, o.get("color", "white"), o.get("outline_color", "black"),
                       outline=o.get("outline", sz * 0.06), shadow=o.get("shadow", 2), align=5, bold=o.get("bold"))
    text = U(o.get("text", ""))
    doc.add(s, e, st, "{" + anim_tags(o.get("anim", "fade"), dur, x, y, W, H, est_width(text, sz), sz)
            + rot + pulse + "}" + esc(text), o.get("layer", 2))


# ------------------------------------------------------------------ subtitles

SUB_PRESETS = {
    # name: style kwargs + behaviour
    "tiktok": dict(color="white", outline_color="black", outline=0.09, shadow=0.03, highlight="#FFD600",
                   mode="word", upper=False, pop=True),
    "box": dict(color="white", bg="#FF8A00", mode="line", upper=False),
    "clean": dict(color="white", outline_color="black", outline=0.045, shadow=0.03, mode="line", upper=False),
    "karaoke": dict(color="white", outline_color="black", outline=0.08, highlight="#00E5FF", mode="karaoke"),
    "news": dict(color="#FFD600", outline_color="black", outline=0.09, shadow=0.04, mode="line", upper=True),
    "minimal": dict(color="white", outline_color="black", outline=0.0, shadow=0.0, bg="#000000B0", mode="line"),
}

_PUNCT_END = re.compile(r"[.!?…,;:]$")


def _retime_words(seg: dict) -> list[dict]:
    """If the segment text was hand-corrected, spread its new tokens over the segment's original timing."""
    words = seg.get("words") or []
    toks = seg.get("text", "").split()
    if words and " ".join(w["word"] for w in words).split() == toks:
        return words
    if not toks:
        return []
    if len(words) == len(toks):  # same word count (spelling fixes): keep each word's own timing
        return [{**w, "word": t} for w, t in zip(words, toks)]
    start, end = seg["start"], seg["end"]
    if words:
        start, end = words[0]["start"], words[-1]["end"]
    weights = [len(t) + 2 for t in toks]
    total = sum(weights)
    out, cur = [], start
    for t, wgt in zip(toks, weights):
        d = (end - start) * wgt / total
        out.append({"start": cur, "end": cur + d * 0.92, "word": t})
        cur += d
    return out


def timeline_words(transcript: dict, clips: list[dict] | None, clip_starts: list[float]) -> list[dict]:
    """Words on the output timeline. If clips cut from the transcribed source, remap their times."""
    words = [{**w, "seg": i} for i, seg in enumerate(transcript["segments"]) for w in _retime_words(seg)]
    if not clips:
        return words
    src = str(Path(transcript.get("source", "")).resolve()).lower()
    out = []
    for c, cs in zip(clips, clip_starts):
        if str(Path(c["src"]).resolve()).lower() != src:
            continue
        cin, cout = parse_time(c.get("in", 0)), c.get("_out")
        sp = float(c.get("speed", 1))
        for w in words:
            # keep any word that overlaps the clip by >60ms (words straddling a cut stay; times clamped)
            if min(w["end"], cout) - max(w["start"], cin) > min(0.06, (w["end"] - w["start"]) * 0.5):
                out.append({**w, "start": cs + max(0, w["start"] - cin) / sp,
                            "end": cs + (min(w["end"], cout) - cin) / sp})
    return out


def group_lines(words: list[dict], max_words: int, max_chars: int, gap: float = 0.45) -> list[list[dict]]:
    """Split into sentence/pause runs, then cut each run into evenly sized lines (no 1-word orphans)."""
    import math
    runs, cur = [], []
    for w in words:
        if cur and (w.get("seg") != cur[-1].get("seg") or w["start"] - cur[-1]["end"] > gap
                    or _PUNCT_END.search(cur[-1]["word"])):
            runs.append(cur)
            cur = []
        cur.append(w)
    if cur:
        runs.append(cur)
    lines = []
    for run in runs:
        chars = len(" ".join(x["word"] for x in run))
        n = max(math.ceil(len(run) / max_words), math.ceil(chars / max_chars), 1)
        n = min(n, len(run))
        size, extra = divmod(len(run), n)
        i = 0
        for k in range(n):
            step = size + (1 if k < extra else 0)
            lines.append(run[i:i + step])
            i += step
    return lines

def add_subtitles(doc: AssDoc, cfg: dict, words: list[dict], defaults: dict, total: float):
    W, H, base = doc.W, doc.H, doc.base
    p = {**SUB_PRESETS.get(cfg.get("style", "tiktok"), SUB_PRESETS["tiktok"]), **cfg}
    portrait = H > W
    size = p.get("size", base * (0.075 if portrait else 0.06))
    max_words = p.get("words_per_line", 4 if portrait else 7)
    max_chars = p.get("max_chars", 24 if portrait else 42)
    upper = p.get("uppercase", p.get("upper", False))
    hl = p.get("highlight")
    keywords = {k.lower(): v for k, v in (p.get("keywords") or {}).items()}
    font = p.get("font") or defaults.get("font")
    x, y = resolve_pos(p.get("pos", "lower" if portrait else "bottom"), W, H)
    remove = re.compile(p.get("strip", r"[.,!?;:…]+$"))

    if p.get("bg"):
        st = doc.style("Sub", font, size, p["color"], p["bg"], outline=size * 0.28, border_style=3, align=5,
                       back_alpha=0)
    else:
        st = doc.style("Sub", font, size, p["color"], p.get("outline_color", "black"),
                       outline=size * p.get("outline", 0.08), shadow=size * p.get("shadow", 0.03), align=5,
                       back_alpha=0.55)

    def fmt(word: str) -> str:
        wtxt = remove.sub("", word) if p.get("strip_punct", True) else word
        return wtxt.upper() if upper else wtxt

    lines = group_lines(words, max_words, max_chars)
    for i, line in enumerate(lines):
        start = line[0]["start"]
        nxt = lines[i + 1][0]["start"] if i + 1 < len(lines) else total
        end = min(max(line[-1]["end"] + 0.15, start + 0.5), nxt)
        toks = [fmt(w["word"]) for w in line]

        def colored(j_active: int | None) -> str:
            parts = []
            for j, tok in enumerate(toks):
                kc = keywords.get(line[j]["word"].lower().strip(".,!?"))
                if j == j_active and hl:
                    pop = "\\fscx112\\fscy112" if p.get("pop") else ""
                    parts.append("{\\c" + ass_inline_color(hl) + pop + "}" + esc(tok) + "{\\r}")
                elif kc:
                    parts.append("{\\c" + ass_inline_color(kc) + "}" + esc(tok) + "{\\r}")
                else:
                    parts.append(esc(tok))
            return " ".join(parts)

        mode = p.get("mode", "line")
        pos = f"\\pos({x},{y})"
        if mode == "word" and hl:
            for j, w in enumerate(line):
                ws = start if j == 0 else w["start"]
                we = line[j + 1]["start"] if j + 1 < len(line) else end
                intro = "\\fscx85\\fscy85\\t(0,90,\\fscx100\\fscy100)" if j == 0 else ""
                doc.add(ws, we, st, "{" + pos + intro + "}" + colored(j), 0)
        elif mode == "karaoke" and hl:
            parts = []
            for j, w in enumerate(line):
                d = int(round(((line[j + 1]["start"] if j + 1 < len(line) else w["end"]) - w["start"]) * 100))
                parts.append(f"{{\\kf{max(d, 1)}}}" + esc(toks[j]))
            doc.styles["Sub"] = doc.styles["Sub"].replace(
                doc.styles["Sub"].split(",")[3], ass_color(hl), 1)  # primary = sung colour
            doc.add(start, end, st, "{" + pos + "\\2c" + ass_inline_color(p["color"]) + "}" + " ".join(parts), 0)
        else:
            doc.add(start, end, st, "{" + pos + "\\fad(60,60)}" + colored(None), 0)


def build_ass(plan: dict, W: int, H: int, clips: list[dict], clip_starts: list[float], total: float,
              work: Path) -> Path | None:
    defaults = {"font": plan.get("font")}
    doc = AssDoc(W, H, work / "fonts")
    sub = plan.get("subtitles")
    if sub and sub.get("transcript"):
        # One transcript or a list (e.g. one per raw clip). Each is mapped by its "source":
        # a clip source -> remapped through the clips; the voiceover source -> shifted to the voiceover start;
        # anything else -> already on the timeline (+ optional offset).
        paths = sub["transcript"] if isinstance(sub["transcript"], list) else [sub["transcript"]]
        vos = (plan.get("audio") or {}).get("voiceover") or []
        vos = vos if isinstance(vos, list) else [vos]

        def same(a, b):
            return bool(a) and bool(b) and str(Path(a).resolve()).lower() == str(Path(b).resolve()).lower()

        words = []
        for ti, tp in enumerate(paths):
            tr = load_json(tp)
            mode = sub.get("timing", "auto")
            src = tr.get("source", "")
            if mode == "clips" or (mode == "auto" and any(same(c["src"], src) for c in clips)):
                ws = timeline_words(tr, clips, clip_starts)
            else:
                ws = timeline_words(tr, None, clip_starts)
                shift = parse_time(sub.get("offset", 0))
                vo = next((v for v in vos if same(v["src"], src)), None)
                if vo:
                    vin = parse_time(vo.get("in", 0))
                    vout = parse_time(vo["out"]) if vo.get("out") is not None else 1e9
                    ws = [w for w in ws if min(w["end"], vout) - max(w["start"], vin) > min(0.06, (w["end"] - w["start"]) * 0.5)]
                    shift += parse_time(vo.get("start", 0)) - vin + (clip_starts[int(vo["clip"])] if "clip" in vo else 0)
                ws = [{**w, "start": w["start"] + shift, "end": w["end"] + shift} for w in ws]
            words += [{**w, "seg": (ti, w.get("seg"))} for w in ws]
        words.sort(key=lambda w: w["start"])
        # Blue style: a frosted scene carries its own big text, so subtitles step aside ("hide_subs": false keeps them)
        hide = [_times(o, clip_starts) for o in plan.get("overlays", [])
                if o.get("type") == "frost" and o.get("hide_subs", True)]
        if hide:
            words = [w for w in words if not any(a - 0.05 <= w["start"] < b for a, b in hide)]
        add_subtitles(doc, sub, words, defaults, total)
    for i, o in enumerate(plan.get("overlays", [])):
        if o.get("type", "text") in ("image", "video"):
            continue
        add_overlay(doc, o, i, clip_starts, defaults)
    if not doc.events:
        return None
    path = work / "overlay.ass"
    doc.write(path)
    return path
