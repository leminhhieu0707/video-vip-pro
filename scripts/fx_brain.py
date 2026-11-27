"""fx_brain.py — the edit brain. Watches the A-roll, reads every sentence and drafts the whole VIP edit:
which effect goes on which word, where on screen, which camera move, captions, Studio Look, sounds.

    python fx_brain.py edited/aroll.json [--industry auto] [--theme auto] [--brand "Minh Đức Store"] [--aspect 9:16]
                       [--density normal|calm|rich] [--studio auto|on|off] [--comedy] [--seed 0]
                       [-o edited/brain.json] [--plan edited/plan_vip.json]

It looks at the picture (face, free space, table line, brand colour, light, tripod or handheld) and the words
(prices, discounts, lists, comparisons, places, years, questions, calls to action, shock words...), scores every
effect in the skill for every sentence, then picks with the variety rules of references/edit_brain.md
(density per industry, one hero effect at a time, no repeats, alternate screen zones, hook first, CTA last).

Output: brain.json (analysis + picks + captions + camera) and a short report on stdout. With --plan it also writes a
complete plan_vip.json that render.py can render as is (0 extra tokens). Claude should still read the report, keep
what fits the story, and fix anything that sounds wrong — the brain drafts, the editor decides.
Honesty: every price / number / place it shows comes from the transcript; nothing is invented.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG  # noqa: E402

# ------------------------------------------------------------------ industries
INDUSTRY = {  # style, effects per 30 s, theme fallback, relight preset, keywords that reveal it
    "shop": ("hype", 7, "orange", "bright_luxe", "shop|sale|đơn hàng|ship|freeship|size|mỹ phẩm|quần áo|giày|túi xách"),
    "phone": ("hype", 7, "blue", "bright_luxe", "iphone|samsung|điện thoại|pro max|ipad|macbook|pin|camera|chip|oppo|xiaomi|lên đời|máy"),
    "realestate": ("calm", 5, "gold", "bright_luxe", "đất|nhà phố|căn hộ|dự án|sổ đỏ|m2|mét vuông|lô đất|mặt tiền|bất động sản"),
    "spa": ("calm", 5, "pink", "soft_window", "spa|da mặt|mụn|trị liệu|làm đẹp|nail|mi|makeup|chăm sóc da"),
    "food": ("story", 6, "orange", "warm_cafe", "quán|món|ngon|ăn uống|cà phê|trà sữa|bún|phở|menu"),
    "edu": ("calm", 6, "blue", "soft_window", "khoá học|học viên|bài học|kiến thức|chia sẻ|mẹo|ai|claude|chatgpt|prompt|skill|câu lệnh|tự động|hiệu ứng|edit|phần mềm|công cụ|hướng dẫn"),
    "finance": ("calm", 5, "teal", "cine_dark", "lãi suất|vay|ngân hàng|bảo hiểm|đầu tư|tiết kiệm|cổ phiếu"),
    "gym": ("hype", 8, "red", "cine_dark", "gym|tập luyện|kg|cơ bụng|giảm cân|sức khoẻ"),
    "travel": ("story", 5, "sky", "warm_cafe", "du lịch|khách sạn|homestay|resort|biển|tour"),
    "car": ("hype", 6, "blackgold", "cine_dark", "ô tô|xe hơi|động cơ|mã lực|xe máy|xe số|xe ga"),
    "fashion": ("calm", 5, "mono", "soft_window", "outfit|thời trang|váy|phối đồ"),
    "news": ("story", 6, "red", "cine_dark", "vụ việc|công an|tin tức|drama|bị bắt|điều tra"),
    "vlog": ("story", 4, "blue", "warm_cafe", "hôm nay|đi chơi|cuộc sống"),
}
THEME_HUES = [("red", 345, 15), ("orange", 15, 38), ("gold", 38, 62), ("green", 80, 160), ("teal", 160, 188),
              ("sky", 188, 210), ("blue", 210, 252), ("purple", 252, 290), ("pink", 290, 345)]


def strip(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower()).replace("đ", "d")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ------------------------------------------------------------------ word lists (matched on accent-free lowercase)
INTENTS = {  # matched on lowercase text WITH accents (proofread transcripts); keep words exact
    "question": r"\?|(?<!\w)(không|sao|tại sao|vì sao|có biết|bao nhiêu|thế nào|được không|có phải|ơi)(?!\w)",
    "discount": r"(?<!\w)(giảm|sale|ưu đãi|khuyến mãi|rẻ|tặng|free|miễn phí|trả góp|voucher|chỉ còn|chỉ từ|giá tốt|quà)(?!\w)",
    "compare": r"(?<!\w)(so với|thay vì|trước đây|trước kia|bây giờ|hơn hẳn|chênh|vs)(?!\w)",
    "list": r"(?<!\w)(thứ nhất|thứ hai|thứ ba|đầu tiên|tiếp theo|cuối cùng|gồm|bao gồm|\d+ (điều|cách|bước|lý do|dòng|mẫu|mẹo|loại))(?!\w)",
    "location": r"(?<!\w)(địa chỉ|số \d+|đường|quận|phường|đà nẵng|hà nội|sài gòn|hcm|tp|ghé|chi nhánh|điện biên phủ)(?!\w)",
    "story": r"(?<!\w)(năm \d{4}|ngày xưa|hồi đó|năm đó|câu chuyện|bắt đầu|khởi nghiệp|từ con số)(?!\w)",
    "money": r"(?<!\w)(tiền|lãi|lỗ|nợ|tỷ|doanh thu|lợi nhuận|vốn)(?!\w)",
    "shock": r"(?<!\w)(sốc|không ngờ|bất ngờ|trời ơi|thật sự|khủng|cực kỳ|siêu|quá đáng|kinh khủng|đỉnh)(?!\w)",
    "cta": r"(?<!\w)(inbox|nhắn tin|liên hệ|gọi ngay|gọi cho|follow|theo dõi|đặt hàng|comment|bình luận|đăng ký|ghé|số điện thoại)(?!\w)",
    "quality": r"(?<!\w)(chính hãng|xịn|cao cấp|đẹp|bền|zin|nguyên zin|fullbox|bảo hành|chất lượng|uy tín|cam kết|kiểm tra|test máy)(?!\w)",
    "tech": r"(?<!\w)(ai|claude|chatgpt|gpt|công nghệ|app|phần mềm|tự động|code|skill|prompt)(?!\w)",
    "turn": r"^(nhưng|tuy nhiên|thế nhưng|yên tâm|đừng lo|vậy thì|mà khoan|khoan đã|chưa hết|đặc biệt|không chỉ)(?!\w)|đâu chỉ",
    "intro": r"(?<!\w)(xin chào|chào các|mình là|em là|tôi là|anh là)(?!\w)",
    "joke": r"(?<!\w)(haha|hihi|đùa thôi|cà khịa|trời đất)(?!\w)",
    "process": r"(?<!\w)(bước|quy trình|lộ trình|giai đoạn|từ khâu|đồng hành từ|từ bước)(?!\w)",
}
PRICE_RE = re.compile(r"(\d{1,3}(?:[.,]\d{3})+)\s*(đ|đồng|vnđ|k)?|(\d+(?:[.,]\d+)?)\s*(triệu|tr|củ|nghìn|ngàn|k|tỷ)\b(\s*\d{1,3})?", re.I)
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
PRODUCT_RE = re.compile(r"\b(iphone\s*\d+(?:\s*pro(?:\s*max)?|\s*plus)?|samsung\s*\w+|galaxy\s*\w+|ipad\s*\w*|macbook\s*\w*)", re.I)
STOP = set("là và của có cho với thì mà này kia đó những các một hai ba được rất cũng đang sẽ đã nè nha nhé ạ ơi không".split())


def prices(text: str) -> list[dict]:
    out = []
    for m in PRICE_RE.finditer(text):
        if m.group(1):
            raw = m.group(1)
            v = float(raw.replace(".", "").replace(",", ""))
            unit = "k" if (m.group(2) or "").lower() == "k" else "đ"
            out.append({"text": raw + ("đ" if unit == "đ" else "k"), "value": v * (1000 if unit == "k" else 1), "show": raw, "unit": unit})
        else:
            n = float(m.group(3).replace(",", "."))
            u = m.group(4).lower()
            mult = {"triệu": 1e6, "tr": 1e6, "củ": 1e6, "nghìn": 1e3, "ngàn": 1e3, "k": 1e3, "tỷ": 1e9}[u]
            tail = (m.group(5) or "").strip()
            v = n * mult + (float(tail) * mult / 1000 if tail else 0)
            unit = {"tr": "triệu", "củ": "triệu"}.get(u, u)
            if tail or (unit in ("nghìn", "ngàn") and v >= 1000):  # "6 triệu 590 (nghìn)" -> 6.590.000đ
                show, unit = f"{int(round(v)):,}".replace(",", "."), "đ"
            else:
                show = m.group(3)
            out.append({"text": m.group(0).strip(), "value": v, "show": show, "unit": unit})
    return [p for p in out if p["value"] >= 1000]


# ------------------------------------------------------------------ picture
def frames(src: Path, total: float, n: int, w: int = 360) -> list[np.ndarray]:
    r = subprocess.run([FFMPEG, "-v", "error", "-i", str(src), "-vf", f"fps={n / max(1.0, total):.4f},scale={w}:-2",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    probe = subprocess.run([FFMPEG, "-v", "error", "-i", str(src), "-frames:v", "1", "-vf", f"scale={w}:-2", "-f", "rawvideo",
                            "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    h = len(probe) // (w * 3)
    k = len(r.stdout) // (w * h * 3)
    return [np.frombuffer(r.stdout, np.uint8)[i * w * h * 3:(i + 1) * w * h * 3].reshape(h, w, 3) for i in range(k)]


def watch(src: Path, total: float) -> dict:
    import cv2
    fr = frames(src, total, int(min(36, max(10, total))))
    H, W = fr[0].shape[:2]
    a = {"w": W, "h": H, "aspect": "9:16" if H > W else "16:9"}
    # faces
    faces = []
    try:
        import face_beauty
        det = cv2.FaceDetectorYN.create(str(face_beauty.model_path()), "", (W, H), 0.6, 0.3, 20)
        for f in fr:
            _, fs = det.detect(cv2.cvtColor(f, cv2.COLOR_RGB2BGR))
            if fs is not None and len(fs):
                b = max(fs, key=lambda r_: r_[2] * r_[3])
                faces.append(((b[0] + b[2] / 2) / W, (b[1] + b[3] / 2) / H, b[3] / H))
    except Exception as e:
        print(f"[brain] face detector unavailable: {e}")
    if faces:
        fa = np.array(faces)
        a["face"] = [round(float(np.median(fa[:, 0])), 3), round(float(np.median(fa[:, 1])), 3)]
        a["face_h"] = round(float(np.median(fa[:, 2])), 3)
        a["face_move"] = round(float(fa[:, 0].std() + fa[:, 1].std()), 3)
        a["face_seen"] = round(len(faces) / len(fr), 2)
    else:
        a.update(face=[0.5, 0.32], face_h=0.1, face_move=0.0, face_seen=0.0)
    # person extent (3 frames, rembg)
    try:
        from PIL import Image
        import vipfx
        sess = vipfx.rembg_session("u2net")
        ms = []
        for f in (fr[len(fr) // 5], fr[len(fr) // 2], fr[4 * len(fr) // 5]):
            m = np.asarray(sess.predict(Image.fromarray(f))[0].resize((W, H)), np.float32) / 255
            ms.append(vipfx.keep_main_blob(np.clip((m - 0.2) / 0.55, 0, 1)) > 0.5)
        m = np.logical_or.reduce(ms)
        ys, xs = np.nonzero(m)
        a["person"] = [round(xs.min() / W, 3), round(ys.min() / H, 3), round(xs.max() / W, 3), round(ys.max() / H, 3)]
        mask = m
    except Exception as e:
        print(f"[brain] person matte unavailable: {e}")
        fx_, fy_ = a["face"]
        a["person"] = [max(0, fx_ - 0.25), max(0, fy_ - a["face_h"]), min(1, fx_ + 0.25), 1.0]
        mask = np.zeros((H, W), bool)
        x0, y0, x1, y1 = a["person"]
        mask[int(y0 * H):, int(x0 * W):int(x1 * W)] = True
    bg = ~mask
    st = np.stack(fr).astype(np.float32)
    # handheld or tripod: background change between samples
    diffs = [np.abs(st[i + 1] - st[i]).mean(axis=2)[bg].mean() for i in range(len(st) - 1)]
    a["bg_motion"] = round(float(np.median(diffs)), 2) if diffs else 0.0
    a["tripod"] = bool(a["bg_motion"] < 6.0)
    # light
    lum = st.mean(axis=0) @ np.array([0.299, 0.587, 0.114], np.float32) / 255
    a["luma"] = round(float(lum[bg].mean()), 3)
    a["contrast"] = round(float(lum.std()), 3)
    a["flat"] = bool(a["contrast"] < 0.2 or a["luma"] > 0.68)
    a["dim"] = bool(a["luma"] < 0.36)
    # brand colour: strongest saturated hue in the background (skin is rarely this saturated)
    hsv = cv2.cvtColor(fr[len(fr) // 2], cv2.COLOR_RGB2HSV).astype(np.float32)
    hh, ss, vv = hsv[..., 0] * 2, hsv[..., 1] / 255, hsv[..., 2] / 255
    sel = bg & (ss > 0.55) & (vv > 0.3)
    a["brand_theme"] = None
    if sel.mean() > 0.012:
        hist = {}
        for name, lo, hi in THEME_HUES:
            inr = (hh >= lo) & (hh < hi) if lo < hi else (hh >= lo) | (hh < hi)
            hist[name] = float((sel & inr).sum())
        best = max(hist, key=hist.get)
        if hist[best] / sel.sum() > 0.45:
            a["brand_theme"] = best
    # table / counter line below the face: strongest long horizontal edge
    gy = np.abs(np.diff(st.mean(axis=0).mean(axis=2), axis=0))
    y_lo = int(min(H - 2, (a["face"][1] + a["face_h"] * 1.2) * H))
    y_hi = int(H * 0.72)
    a["table_y"] = None
    if y_hi > y_lo + 5:
        rows = gy[y_lo:y_hi].mean(axis=1)
        j = int(np.argmax(rows))
        if rows[j] > rows.mean() * 2.2:
            a["table_y"] = round((y_lo + j) / H, 3)
    # free screen zones (for text): band above the head, sides of the person
    px0, py0, px1, _ = a["person"]
    a["zones"] = {"top": [0.0, 0.04, 1.0, max(0.05, py0 - 0.02)], "left": [0.0, 0.0, px0, 1.0], "right": [px1, 0.0, 1.0, 1.0]}
    # empty corners for props (low edge density, beside the person)
    edges = cv2.Canny(cv2.cvtColor(fr[len(fr) // 2], cv2.COLOR_RGB2GRAY), 60, 140) > 0
    def busy(x0, x1):
        y0 = int(max(0.25, py0) * H)
        y1 = int((a["table_y"] or 0.75) * H)
        reg = edges[y0:y1, int(x0 * W):int(x1 * W)]
        return float(reg.mean()) if reg.size else 1.0
    a["side_busy"] = {"left": round(busy(0, max(0.05, px0)), 3), "right": round(busy(min(0.95, px1), 1), 3)}
    return a


# ------------------------------------------------------------------ words
def sentences(ar: dict, words: list[dict]) -> list[dict]:
    st, total = ar["starts"], ar["total"]
    out = []
    for i, c in enumerate(ar["cuts"]):
        s, e = st[i], st[i + 1] if i + 1 < len(st) else total
        ws = [w for w in words if s <= (w["start"] + w.get("end", w["start"])) / 2 < e]
        out.append({"i": i, "start": round(s, 3), "end": round(e, 3), "text": c.get("text", "").strip(), "words": ws})
    return out


def read(sent: dict, n_total: int) -> dict:
    t = sent["text"]
    low = unicodedata.normalize("NFC", t.lower())
    tags = {k for k, rx in INTENTS.items() if re.search(rx, low)}
    ps = prices(t)
    if ps:
        tags.add("price")
    if YEAR_RE.search(t):
        tags.add("story")
    if sent["i"] == 0:
        tags.add("hook")
    if sent["i"] == n_total - 1:
        tags.add("end")
    m = re.search(r"[\"“”](.+?)[\"“”]", t)
    if m and len(m.group(1).split()) >= 4:
        tags.add("quote")
    prod = PRODUCT_RE.search(t)
    n_list = re.search(r"\b(\d+)\s+(điều|cách|bước|lý do|dòng|mẫu|mẹo|loại)\b", t, re.I)
    gm = re.search(r"(?:bao gồm|gồm|có)\s+(.+)$", t, re.I)
    body = gm.group(1) if gm and ("," in gm.group(1) or " và " in gm.group(1)) else t
    parts = [p.strip(" .!") for p in re.split(r"[,;]| và ", body) if p.strip(" .!")]
    short_items = [p for p in parts if 1 <= len(p.split()) <= (4 if gm else 2)]
    if "process" in tags:  # "đồng hành từ bước nghiên cứu thị trường, insight khách hàng, … và lên kế hoạch tổng thể"
        steps = []
        for p in parts:
            m2 = re.search(r"(?:từ bước|từ khâu|bắt đầu từ|từ|bước|gồm|là)\s+(.+)$", p, re.I)
            if len(p.split()) > 5 and m2:
                p = m2.group(1)
            p = re.sub(r"^(cho tới khi|cho đến khi|tới khi|đến khi|rồi|sau đó|cuối cùng là|cuối cùng)\s+", "", p, flags=re.I)
            if 1 <= len(p.split()) <= 5:
                steps.append(p)
        if len(steps) >= 3:
            short_items = steps
    if len(short_items) >= 3:  # "số chạy, đóng dấu, kính vỡ": a spoken list even without a list word
        tags.add("list")
    energy = len(tags & {"shock", "price", "discount", "question", "quality"}) + (1 if "!" in t else 0)
    return {"tags": sorted(tags), "prices": ps, "year": (YEAR_RE.search(t).group(0) if YEAR_RE.search(t) else None),
            "product": prod.group(0) if prod else None, "list_n": int(n_list.group(1)) if n_list else None,
            "items": short_items if len(short_items) >= 2 else [], "quote": m.group(1) if m else None, "energy": energy}


def keyword(sent: dict, info: dict) -> str:
    """The word or phrase the caption should mark: a price, a product, the intent word, a proper noun, else the longest word."""
    if info["prices"]:
        return info["prices"][0]["text"]
    if info["product"]:
        return info["product"]
    t = sent["text"]
    low = unicodedata.normalize("NFC", t.lower())
    for k in ("discount", "quality", "shock", "tech"):
        m = re.search(INTENTS[k], low)
        if m and m.group(0).strip():
            return t[m.start():m.end()].strip(",.!?")
    ws = [w.strip(",.!?") for w in t.split()]
    caps = [w for j, w in enumerate(ws) if j > 0 and w[:1].isupper() and strip(w) not in STOP]
    if caps:
        return caps[0]
    cand = [w for w in ws if strip(w) not in STOP]
    return max(cand, key=len) if cand else (ws[0] if ws else "")


GLUE = ["học sinh sinh viên", "học sinh", "sinh viên", "pro max", "chính hãng", "ưu đãi", "điện biên phủ", "đà nẵng", "hà nội",
                "cực kỳ", "chương trình", "điện thoại", "phụ kiện", "bảo hành", "kiểm tra", "tư vấn", "giá tốt", "lên đời", "nguyên zin",
                "hấp dẫn", "tiết kiệm", "mọi người", "các bạn", "khách hàng", "cửa hàng", "thành phố", "hôm nay", "bây giờ", "trả góp",
                "miễn phí", "khuyến mãi", "giảm giá", "tai nghe", "ốp lưng", "kính cường lực", "cường lực", "thay pin", "1 năm", "đi học",
                "quyết định", "thoải mái", "tình trạng", "chất lượng", "uy tín", "sản phẩm", "dịch vụ", "đặt hàng", "liên hệ", "nhắn tin",
                "theo dõi", "đăng ký", "bình luận", "hướng dẫn", "chia sẻ", "kinh nghiệm", "đầu tiên", "cuối cùng", "tiếp theo"]


def captions(sent: dict, info: dict, max_words: int = 6) -> list[dict]:
    """Two-tier caption chunks timed on the words (BlueText: small top line + big line with one **keyword**).
    Natural reading order always: the small line is the start of the phrase, the big line its last 3 words."""
    ws = [w for k, w in enumerate(sent["words"])  # drop a word repeated at a cut ("iPhone iPhone")
          if not (k and strip(w["word"].strip(",.!?")) == strip(sent["words"][k - 1]["word"].strip(",.!?")))]
    toks = sent["text"].split()
    if not ws:  # no word times: spread the text evenly
        n = max(1, len(toks))
        ws = [{"start": sent["start"] + (sent["end"] - sent["start"]) * j / n, "word": tk} for j, tk in enumerate(toks)]
    # never split inside a price, the keyword, a product or the brand; prefer breaking before linking words
    toks_n = [strip(w["word"].strip(",.!?")) for w in ws]
    glue = set()
    phrases = [p["text"] for p in info["prices"]] + [keyword(sent, info), info.get("product") or "", BRAND_HINT.get("name", "")]
    phrases += GLUE
    for ph in phrases:
        pt = [strip(x) for x in str(ph).split() if strip(x)]
        if len(pt) < 2:
            continue
        for k in range(len(toks_n) - len(pt) + 1):
            if toks_n[k:k + len(pt)] == pt:
                glue.update(range(k, k + len(pt) - 1))  # no split after token k..end-1
    for k in range(len(toks_n) - 1):  # a number stays with its unit
        if re.fullmatch(r"[\d.,]+", toks_n[k]) and toks_n[k + 1] in ("trieu", "nghin", "ngan", "dong", "k", "ty", "tr", "nam", "%"):
            glue.add(k)
    BOUND = {"cho", "de", "thi", "ma", "va", "nhung", "khi", "voi", "tai", "cua", "la", "duoc", "dang", "se", "vi", "nen",
             "hay", "tu", "chi", "con", "neu", "roi", "vay", "o", "trong", "truoc", "sau"}
    ok_after = [k not in glue and (bool(re.search(r"[,.!?]$", ws[k]["word"])) or (k + 1 < len(ws) and toks_n[k + 1] in BOUND))
                for k in range(len(ws))]
    chunks, a0 = [], 0
    for k in range(len(ws)):
        n = k - a0 + 1
        last = k == len(ws) - 1
        if last:
            break
        if ok_after[k] and n >= 3:
            chunks.append(ws[a0:k + 1]); a0 = k + 1
        elif n >= 8:  # no natural break: cut near the middle, never inside a glued phrase
            mids = [m for m in range(a0 + 2, k) if m not in glue]
            m = min(mids, key=lambda m: abs(m - (a0 + k) / 2)) if mids else k
            chunks.append(ws[a0:m + 1]); a0 = m + 1
    rest = ws[a0:]
    if rest:
        if chunks and len(rest) <= 2 and len(chunks[-1]) <= 6:
            chunks[-1] += rest
        else:
            chunks.append(rest)
    key = [strip(k) for k in strip(keyword(sent, info)).split()]
    out = []
    for j, ch in enumerate(chunks):
        words = [w["word"].strip() for w in ch]
        n = len(words)
        cut = max(0, n - 3)
        offs = sum(len(c) for c in chunks[:j])
        while cut > 0 and (offs + cut - 1) in glue and n - cut < 5:  # keep a glued phrase together on the big line
            cut -= 1
        top, big = words[:cut], words[cut:]
        hit = [k for k, w in enumerate(big) if strip(w.strip(",.!?")) in key and strip(w.strip(",.!?"))]
        if hit:
            a, b = hit[0], hit[-1]
            big = big[:a] + ["**" + " ".join(big[a:b + 1]) + "**"] + big[b + 1:]
        s = ch[0]["start"]
        e = chunks[j + 1][0]["start"] if j + 1 < len(chunks) else sent["end"]
        out.append({"start": round(max(sent["start"], s - 0.05), 3), "end": round(e, 3),
                    "top": " ".join(top).strip(",. "), "text": " ".join(big).strip(",. ")})
    return out


GRAD = {"gold": ["#FFE7A3", "#FF8A1F"], "orange": ["#FFE7A3", "#FF8A1F"], "red": ["#FFC1B0", "#FF3B30"], "blue": ["#A8ECFF", "#2E8BFF"],
        "sky": ["#C9F4FF", "#2FC6FF"], "green": ["#E2FF8F", "#2FD47A"], "pink": ["#FFC4E1", "#FF4FA0"], "purple": ["#E0C8FF", "#8A5CFF"],
        "mono": ["#FFFFFF", "#C9CED8"]}
STOP_S = {strip(x) for x in STOP if x not in ("một", "hai", "ba")} | {strip(x) for x in "bạn mình em anh chị tôi ta họ nó cái chỗ thứ để từ khi nếu vì như nên rồi lại ra vào lên xuống đi về nào gì sao thế ấy".split()}
COVERED = {"HudChapter", "NeonTunnel", "frost", "ExplainCanvas", "PunchWord", "MetalText", "QuoteCard", "VsCards", "Odometer", "CountUp",
           "PriceSlash", "GiantCaption", "DecodeText", "GlassText", "NeonText", "CubeFlip", "Stamp", "NumberTitle"}  # these carry the words above the head


def wordpop(sents: list[dict], infos: list[dict], picks: dict, a: dict, theme: str) -> list[dict]:
    """WordStack lockups (word-by-word kinetic captions): phrase chunks timed on the words, one key per chunk (the sentence
    keyword, else the longest content word), placed just above the measured head top; now and then a wide key tucks behind the head."""
    grad = GRAD.get(theme, GRAD["gold"])
    head = a["person"][1]
    y_up, y_behind = round(max(0.2, head - 0.11), 3), round(min(0.6, head - 0.025), 3)  # behind: lead words stay above the head, the key crosses its top
    x = round(min(0.62, max(0.38, a["face"][0])), 3)
    out, last_behind = [], -9
    for s, info in zip(sents, infos):
        if picks.get(s["i"], {}).get("name") in COVERED:
            continue
        ws = [w for w in s["words"] if w["word"].strip()]
        if not ws:
            continue
        kw = keyword(s, info)
        phrases = sorted({strip(x_) for x_ in [kw] + [p_["text"] for p_ in info["prices"]] + GLUE + [BRAND_HINT.get("name", "")]
                          if x_ and len(x_.split()) > 1}, key=lambda x_: -len(x_.split()))
        toks, i = [], 0
        while i < len(ws):
            hit = 0
            for ph in phrases:
                n = len(ph.split())
                if i + n <= len(ws) and " ".join(strip(x_["word"].strip(",.!?")) for x_ in ws[i:i + n]) == ph:
                    hit = n
                    break
            g = ws[i:i + (hit or 1)]
            toks.append({"w": " ".join(x_["word"] for x_ in g), "start": g[0]["start"], "end": g[-1].get("end", g[-1]["start"] + 0.2)})
            i += hit or 1
        chunks, cur = [], []
        for j, tk in enumerate(toks):
            cur.append(tk)
            nx = toks[j + 1] if j + 1 < len(toks) else None
            if (re.search(r"[.,!?;:]$", tk["w"]) or not nx or nx["start"] - tk["end"] > 0.3 or len(cur) >= 6
                    or (len(cur) >= 4 and nx["start"] - tk["end"] > 0.12)):
                chunks.append(cur)
                cur = []
        kws = strip(kw)
        for ci, ch in enumerate(chunks):
            names = [strip(tk["w"].strip(",.!?")) for tk in ch]
            # key: a number / price > a glued phrase (multi-word token) > the last two content syllables (Vietnamese stresses
            # the end of the phrase: "phụ đề HAI TẦNG", "zoom theo NHỊP NÓI") > the sentence keyword > the longest word
            content = [j for j, nm in enumerate(names) if nm not in STOP_S]
            kset = [j for j, nm in enumerate(names) if re.search(r"\d", nm)][:1]
            if not kset:
                kset = [j for j, tk in enumerate(ch) if " " in tk["w"].strip() and names[j] not in STOP_S][-1:]
            if not kset and len(content) >= 2 and content[-1] - content[-2] == 1 and len(ch) >= 2:
                kset = [content[-2], content[-1]]
            if not kset:
                kset = [j for j, nm in enumerate(names) if nm == kws][:1] or ([max((len(names[j]), j) for j in content)[1]] if content else [len(ch) - 1])
            kidx = kset[0] if kset else None
            st = max(s["start"], ch[0]["start"] - 0.06)
            en = (chunks[ci + 1][0]["start"] - 0.03) if ci + 1 < len(chunks) else s["end"]
            if en - st < 0.35:
                continue
            words = [{"w": re.sub(r"[.,!?;:]+$", "", tk["w"]), "t": round(tk["start"] - st, 3), "k": 1 if j in kset else 0} for j, tk in enumerate(ch)]
            klen = len(" ".join(words[j]["w"] for j in kset))
            behind = bool(a["tripod"] and klen >= 8 and head > 0.3 and len(out) - last_behind >= 6)
            o = {"type": "motion", "comp": "WordStack", "start": round(st, 3), "end": round(en, 3),
                 "props": {"words": words, "x": x, "y": y_behind if behind else y_up, "key_size": 190 if behind else 175, "grad": grad}}
            if behind:
                o["behind"] = True
                last_behind = len(out)
            out.append(o)
    return out


def duo_slots(out: list[dict], a: dict) -> list[dict]:
    """--wordpop-look duo (the listing-editor look, measured frame by frame): two lockups on screen at once, alternating a
    top slot (key crossing the head, tucked behind it) and a low slot (in front of the chest); each lockup stays until the
    next one in its own slot arrives. Words pop in grey and brighten, keys strobe on (every other one just pops), and the
    lockups move with the camera ("follow": the punch zooms carry the words, so they sit in the shot)."""
    head = a["person"][1]
    y_top, y_low = round(max(0.18, min(0.6, head - 0.01)), 3), round(min(0.74, head + 0.22), 3)
    for i, o in enumerate(out):
        p = o["props"]
        p.update({"enter": "flicker", "key_in": "strobe" if i % 2 == 0 else "pop", "tilt": -9 if i % 3 == 2 else 0,
                  "y": y_top if i % 2 == 0 else y_low, "follow": 0.8, "max_w": min(p.get("max_w", 0.88), 0.78)})
        if i % 2 == 0:  # only the top slot tucks behind the head; behind the torso the key loses its middle letters
            o["behind"] = True
        else:
            o.pop("behind", None)
        nxt = out[i + 2]["start"] - 0.03 if i + 2 < len(out) else o["end"] + 0.8
        o["end"] = round(max(o["end"], min(nxt, o["end"] + 1.6)), 3)
    return out


def word_time(sent: dict, phrase: str) -> float:
    """Timeline time of the first word of `phrase` inside the sentence (effects land on the word that names them)."""
    if not phrase or not sent["words"]:
        return sent["start"]
    key = strip(phrase).split()[0] if strip(phrase).split() else ""
    for w in sent["words"]:
        if key and key in strip(w["word"]):
            return max(sent["start"], w["start"] - 0.08)
    return sent["start"]


# ------------------------------------------------------------------ effect catalogue: (name, intents it serves, base score, hero?, zone, styles)
CAT = [
    ("Odometer", {"price"}, 9, True, "top", {"hype", "calm", "story"}),
    ("CountUp", {"price"}, 7, False, "top", {"hype", "calm", "story"}),
    ("Checklist", {"list"}, 8, False, "side", {"hype", "calm", "story"}),
    ("PriceSlash", {"price", "discount"}, 10, True, "top", {"hype", "calm"}),
    ("SealBadge", {"discount"}, 7, False, "side", {"hype", "calm"}),
    ("MetalText", {"quality", "shock", "discount"}, 6, True, "top", {"hype"}),
    ("Stamp", {"shock", "quality", "discount"}, 5, False, "top", {"hype", "story"}),
    ("PunchWord", {"shock"}, 5, True, "full", {"hype"}),
    ("spotlight", {"shock", "turn", "quality"}, 6, True, "person", {"hype", "calm", "story"}),
    ("dolly", {"shock"}, 5, True, "person", {"story", "hype"}),
    ("VsCards", {"compare"}, 8, True, "top", {"hype", "calm", "story"}),
    ("CubeFlip", {"list", "quality"}, 6, False, "top", {"hype", "calm"}),
    ("NumberTitle", {"list"}, 6, False, "top", {"calm", "story", "hype"}),
    ("frost", {"list", "compare", "turn", "money"}, 5, True, "full", {"hype", "calm", "story"}),
    ("MapPin", {"location"}, 9, True, "top", {"hype", "calm", "story"}),
    ("DocLabel", {"story", "location"}, 7, False, "bottom", {"story", "calm"}),
    ("QuoteCard", {"quote"}, 9, True, "top", {"story", "calm"}),
    ("DecodeText", {"tech", "question"}, 5, False, "top", {"calm", "hype"}),
    ("GlassText", {"quality", "tech"}, 5, True, "top", {"calm"}),
    ("NeonText", {"tech"}, 4, False, "top", {"calm", "hype"}),
    ("popout", {"turn"}, 6, True, "person", {"calm", "hype"}),
    ("bgblur", {"question", "hook"}, 4, False, "person", {"calm", "hype", "story"}),
    ("impact", {"joke", "shock"}, 4, True, "full", {"comedy"}),
    ("dramatic", {"joke", "shock"}, 4, True, "full", {"comedy"}),
    ("FollowCard", {"cta"}, 8, False, "bottom", {"hype", "calm", "story"}),  # only on the last two sentences (see ok())
    ("NameTag", {"intro"}, 7, False, "bottom", {"hype", "calm", "story"}),
    ("Countdown", {"question"}, 3, False, "top", {"hype"}),
    ("ExplainCanvas", {"list", "process", "compare"}, 8, True, "full", {"calm", "story", "hype"}),  # NARRATE pack: speaker in a live bubble
]
HEROES_GAP = {"calm": 7.0, "story": 6.5, "hype": 5.0}
BRAND_HINT: dict = {}


ICON_WORDS = [("money", "giá|tiền|triệu|tỷ|chi phí|lãi|vốn"), ("home", "nhà|căn|phòng|dự án|chung cư"), ("pin", "vị trí|địa chỉ|gần|đường|quận"),
              ("clock", "phút|giờ|ngày|nhanh chóng|thời gian"), ("shield", "bảo hành|an toàn|pháp lý|sổ"), ("bolt", "tự động|nhanh|ngay|liền"),
              ("users", "khách|người|đội|nhân viên"), ("chat", "phụ đề|chữ|nói|tư vấn|nhắn"), ("search", "tìm|zoom|soi|kiểm tra"),
              ("chart", "tăng|doanh thu|lợi nhuận|biểu đồ"), ("car", "xe|ô tô"), ("school", "trường|học"), ("wave", "biển|sông|hồ bơi"),
              ("tree", "cây|công viên|xanh"), ("star", "đẹp|sang|cao cấp|hiệu ứng")]


def icon_for(text: str) -> str:
    low = unicodedata.normalize("NFC", text.lower())
    return next((ic for ic, rx in ICON_WORDS if re.search(rx, low)), "check")


def build(name: str, sent: dict, info: dict, a: dict, ctx: dict) -> list[dict] | None:
    """Overlay dicts for one pick (timeline seconds), or None when the sentence lacks what the effect needs."""
    s, e = sent["start"], sent["end"]
    ps = info["prices"]
    if name == "ExplainCanvas":  # the speaker shrinks into a live bubble while the list / comparison is drawn
        if e - s < 2.0 or a.get("face_seen", 1) < 0.5:
            return None
        face = [round(a["face"][0], 3), round(a["face"][1], 3)]
        ctx["_canvas_n"] = ctx.get("_canvas_n", 0) + 1
        bg = ("paper", "dark", "brand")[(ctx["_canvas_n"] - 1) % 3]
        if len(info["items"]) >= 2:
            items = info["items"][:4]
            if max(len(x) for x in items) > 18:
                return None
            its = [{"icon": icon_for(x), "label": x[:1].upper() + x[1:], "t": round(max(0.4, word_time(sent, x) - s), 2)} for x in items]
            return [{"type": "motion", "comp": "ExplainCanvas", "start": s, "end": e,
                     "props": {"mode": "tiles", "items": its, "face": face, "bg": bg, "accent": ctx.get("accent"), "at": 0.3}}]
        if len(ps) >= 2 and ps[0]["value"] != ps[1]["value"]:
            return [{"type": "motion", "comp": "ExplainCanvas", "start": s, "end": e,
                     "props": {"mode": "compare", "face": face, "bg": bg, "accent": ctx.get("accent"),
                               "a": {"label": "Trước", "value": ps[0]["show"] + (" " + ps[0]["unit"] if ps[0].get("unit") else ""), "icon": "clock"},
                               "b": {"label": "Bây giờ", "value": ps[1]["show"] + (" " + ps[1]["unit"] if ps[1].get("unit") else ""), "icon": "bolt"}}}]
        return None
    top_y = max(0.1, min(0.2, a["person"][1] * 0.55))
    if name == "Odometer" and ps:
        p = ps[-1]
        t0 = word_time(sent, p["text"])
        return [{"type": "motion", "comp": "Odometer", "start": t0, "end": e, "props": {"value": p["show"], "unit": p["unit"], "y": top_y,
                                                                                     "label": ctx.get("price_label", "")}}]
    if name == "CountUp" and ps:
        p = ps[-1]
        v = p["value"]
        if v >= 1e6:
            to, suf = round(v / 1e6, 2), " triệu"
        elif v >= 1e3:
            to, suf = round(v / 1e3), "k"
        else:
            return None
        return [{"type": "motion", "comp": "CountUp", "start": word_time(sent, p["text"]), "end": e,
                 "props": {"from": 0, "to": to, "suffix": suf, "y": top_y + 0.02, "ring": True}}]
    if name == "Checklist" and len(info["items"]) >= 2:
        items = info["items"][:5]
        side = ctx["free_side"]
        out = []
        for it in items:
            out.append({"t": it, "at": round(max(0.0, word_time(sent, it) - s), 2)})
        return [{"type": "motion", "comp": "Checklist", "start": s, "end": e,
                 "props": {"items": out, "x": 0.07 if side == "left" else 0.56, "y": max(0.12, top_y), "size": 46, "tone": "video"}}]
    if name == "PriceSlash" and len(ps) >= 2:
        hi, lo = max(ps, key=lambda p: p["value"]), min(ps, key=lambda p: p["value"])
        if hi["value"] == lo["value"]:
            return None
        return [{"type": "motion", "comp": "PriceSlash", "start": word_time(sent, hi["text"]), "end": e,
                 "props": {"old": hi["show"], "new": lo["show"], "unit": lo["unit"], "y": top_y + 0.02}}]
    if name == "SealBadge":
        m = re.search(r"giảm(?: thẳng)?\s+(\d+(?:[.,]\d+)?)\s*(triệu|tr|k|%|nghìn)?", sent["text"], re.I)
        center = (f"-{m.group(1)}{'TR' if (m.group(2) or '').lower() in ('triệu', 'tr') else (m.group(2) or '').upper()}") if m else "SALE"
        side = ctx["free_side"]
        return [{"type": "motion", "comp": "SealBadge", "start": word_time(sent, "giảm") if m else s, "end": e,
                 "props": {"center": center, "ring": f"ƯU ĐÃI • {ctx['brand'].upper()} • " if ctx["brand"] else "ƯU ĐÃI • GIẢM GIÁ • ",
                           "x": 0.8 if side == "right" else 0.2, "y": max(0.16, top_y + 0.06), "size": 280}}]
    if name == "MetalText":
        k = keyword(sent, info).upper()
        if len(k) > 14 or len(k) < 2:
            return None
        return [{"type": "motion", "comp": "MetalText", "start": word_time(sent, k), "end": e,
                 "props": {"text": k, "metal": ctx["metal"], "y": top_y}}]
    if name == "Stamp":
        txt = {"discount": "GIÁ SỐC", "quality": "CHÍNH HÃNG", "shock": "SỐC"}
        k = next((txt[t] for t in ("discount", "quality", "shock") if t in info["tags"]), None)
        return [{"type": "motion", "comp": "Stamp", "start": s + 0.15, "end": e, "props": {"text": k, "y": top_y}}] if k else None
    if name == "PunchWord":
        k = keyword(sent, info).upper()
        if not 2 <= len(k) <= 8:
            return None
        t0 = word_time(sent, k)
        return [{"type": "motion", "comp": "PunchWord", "start": t0, "end": min(e, t0 + 1.4), "props": {"word": k, "y": top_y}}]
    if name == "spotlight":
        return [{"type": "spotlight", "start": s, "end": e, "at": [a["face"][0], max(0.15, a["face"][1] - 0.02)]}]
    if name == "dolly":
        return [{"type": "dolly", "start": s, "end": min(e, s + 1.8), "zoom": 1.35}] if a["tripod"] and e - s >= 1.0 else None
    if name == "VsCards" and len(ps) >= 2:
        return [{"type": "motion", "comp": "VsCards", "start": s, "end": e, "props": {"a": {"v": ps[0]["text"], "label": "TRƯỚC"},
                                                                                    "b": {"v": ps[1]["text"], "label": "BÂY GIỜ"}, "y": 0.2}}]
    if name == "CubeFlip" and info["items"]:
        items = [i.upper() for i in info["items"][:4]]
        if max(len(i) for i in items) > 10:
            return None
        return [{"type": "motion", "comp": "CubeFlip", "start": s, "end": e, "props": {"words": items, "y": top_y}}]
    if name == "NumberTitle":
        m = re.search(r"\b(thứ nhất|thứ hai|thứ ba|thứ tư|đầu tiên|tiếp theo|cuối cùng)\b", sent["text"], re.I)
        if not m:
            return None
        ctx["num"] = ctx.get("num", 0) + 1
        rest = sent["text"][m.end():].strip(" ,.:").split()
        return [{"type": "motion", "comp": "NumberTitle", "start": s, "end": e,
                 "props": {"n": str(ctx["num"]), "top": m.group(0), "text": " ".join(rest[:4])}}]
    if name == "frost":
        if e - s < 1.2:
            return None
        k = keyword(sent, info)
        words = sent["text"].split()
        return [{"type": "frost", "start": s, "end": e, "mode": "navy" if ctx["style"] == "story" else "light", "grid": ctx["style"] == "story"},
                {"type": "motion", "comp": "BlueBig", "start": s, "end": e,
                 "props": {"top": " ".join(words[:5]), "text": f"**{k}**", "tone": "dark" if ctx["style"] == "story" else "light", "y": 0.42, "size": 120}}]
    if name == "MapPin":
        place = ctx["brand"] or "Địa chỉ"
        m = re.search(r"((?:số\s*)?\d+[\w/]*\s+(?:đường\s+)?[A-ZĐ][^\.,!?]+)", sent["text"])
        sub = m.group(1).strip() if m else ""
        if not (sub or ctx["brand"]):
            return None
        return [{"type": "motion", "comp": "MapPin", "start": s, "end": max(e, s + 2.6), "props": {"place": place, "sub": sub}}]
    if name == "DocLabel":
        city = re.search(r"\b(Đà Nẵng|Hà Nội|Sài Gòn|TP\.? ?HCM|Huế|Hải Phòng|Cần Thơ|Nha Trang|Đà Lạt)\b", sent["text"], re.I)
        if not (info["year"] or city):
            return None
        return [{"type": "motion", "comp": "DocLabel", "start": s, "end": e, "props": {"place": (city.group(0) if city else "").upper() or "NĂM",
                                                                                     "date": info["year"] or ""}}]
    if name == "QuoteCard" and info["quote"]:
        return [{"type": "motion", "comp": "QuoteCard", "start": s, "end": e, "props": {"quote": info["quote"], "y": 0.2}}]
    if name == "DecodeText":
        k = keyword(sent, info).upper()
        return [{"type": "motion", "comp": "DecodeText", "start": word_time(sent, k), "end": e, "props": {"text": k, "y": top_y}}] if 2 <= len(k) <= 16 else None
    if name == "GlassText":
        k = keyword(sent, info).upper()
        return [{"type": "motion", "comp": "GlassText", "start": s, "end": e, "fill": "glass", "props": {"text": k, "y": top_y}}] if 2 <= len(k) <= 10 else None
    if name == "NeonText":
        k = keyword(sent, info)
        return [{"type": "motion", "comp": "NeonText", "start": s, "end": e, "props": {"text": k, "y": top_y}}] if 2 <= len(k) <= 14 else None
    if name == "popout":
        if not a["tripod"]:
            return None
        chin = a["face"][1] + a["face_h"] * 0.75
        return [{"type": "popout", "start": s, "end": e, "bg": "0xEEF1F8", "fade": 0.2,
                 "window": {"crop": [0.05, round(chin, 3), 0.9, 0.32], "pos": [0.5, 0.74], "width": 0.84, "radius": 44}}]
    if name == "bgblur":
        return [{"type": "bg", "start": s, "end": e, "blur": 26, "fade": 0.3}]
    if name in ("impact", "dramatic"):
        t0 = word_time(sent, keyword(sent, info))
        return [{"type": name, "start": t0, "end": t0 + (0.35 if name == "impact" else 1.2)}]
    if name == "FollowCard":
        nm = ctx["brand"] or ""
        return [{"type": "motion", "comp": "FollowCard", "start": s, "end": max(e, s + 2.2),
                 "props": {"name": nm or "Theo dõi", "handle": "@" + re.sub(r"\W", "", strip(nm)) if nm else "", "initial": (nm[:1] or "★")}}]
    if name == "NameTag" and ctx["brand"]:
        return [{"type": "motion", "comp": "NameTag", "start": s, "end": e, "props": {"name": ctx["brand"], "role": ctx.get("role", "")}}]
    if name == "Countdown":
        return [{"type": "motion", "comp": "Countdown", "start": s, "end": e, "props": {"from": 3, "y": top_y + 0.05}}] if e - s >= 1.5 else None
    return None


def two_lines(item: str) -> tuple[str, str]:
    """"insight khách hàng" -> ("INSIGHT", "KHÁCH HÀNG"): the last two syllables (one Vietnamese word) go on line 2."""
    w = item.upper().split()
    if len(w) <= 2:
        return " ".join(w), ""
    return " ".join(w[:-2]), " ".join(w[-2:])


def hud_chapter(sents: list[dict], infos: list[dict], i: int, ctx: dict) -> tuple[list[dict], int] | None:
    """Full-screen HUD chapter over a process / roadmap enumeration (sentence i, plus the next one while it keeps listing).
    Returns (layers, index of the last sentence covered)."""
    # Whisper splits one long list over several "sentences": keep joining while the text runs on (no . ! ?) or the
    # next one is itself a list, up to 3 sentences
    j = i
    while (j + 1 < len(sents) and j - i < 2 and sents[j + 1]["start"] - sents[j]["end"] < 0.6
           and (not re.search(r"[.!?…]\s*$", sents[j]["text"]) or len(infos[j + 1]["items"]) >= 2)):
        j += 1
    merged = {"i": sents[i]["i"], "start": sents[i]["start"], "end": sents[j]["end"],
              "text": " ".join(sents[k]["text"].strip() for k in range(i, j + 1)), "words": [w for k in range(i, j + 1) for w in sents[k]["words"]]}
    info = read(merged, 10 ** 6)
    items: list[tuple[float, str]] = [(word_time(merged, it), it) for it in info["items"]][:6]
    # trim trailing sentences that add no step
    while j > i and items and sents[j]["start"] > items[-1][0] + 0.5 and sents[j]["end"] - items[-1][0] > 4:
        j -= 1
    s, e = sents[i]["start"], sents[j]["end"]
    if len(items) < 3 or e - s < 3.5:
        return None
    broll = ctx.get("broll") or []
    scenes = []
    if items[0][0] - s > 1.2:  # a lead-in ("không chỉ quay vài video cho có, …") gets an intro scene first
        scenes.append({"at": 0, "kicker": (ctx["brand"] or "QUY TRÌNH").upper(), "title": "LỘ TRÌNH", "title2": f"{len(items)} BƯỚC", "box": True,
                       "card": "none", "chapter": "01 — Giới thiệu", "tone": "light"})
    for n, (t, it) in enumerate(items):
        a, b = two_lines(it)
        sc = {"at": round(max(0.0, t - s), 2) if (scenes or n) else 0.0, "step": f"{n + 1:02d}/{len(items):02d}", "title": a, "title2": b,
              "chapter": f"{(n + 2) if scenes and scenes[0].get('kicker') else (n + 1):02d} — Bước {n + 1}"}
        if broll:
            src = broll[n % len(broll)]
            sc.update({"media": src, "card": "rec" if Path(src).suffix.lower() in (".mp4", ".mov", ".webm", ".m4v") else "browser"})
        else:
            sc["card"] = "none"
        scenes.append(sc)
    for k in range(1, len(scenes)):  # each scene needs ≥ 0.9 s or its letters never settle
        scenes[k]["at"] = round(max(scenes[k]["at"], scenes[k - 1]["at"] + 0.9), 2)
    if scenes[-1]["at"] > e - s - 0.8:
        return None
    lay = [{"type": "motion", "comp": "HudChapter", "start": s, "end": e,
            "props": {"brand": ctx["brand"] or "STUDIO", "footer": ctx.get("footer", ""), "tc": round(s, 2), "scenes": scenes,
                      "marquee": " ✦ ".join(two_lines(x[1])[1] or x[1].upper() for x in items[:4])}}]
    return lay, j


def neon_tunnel(sent: dict, ctx: dict) -> tuple[list[dict], bool] | None:
    """Full-screen neon tunnel on an early question, B-roll clips flying in a phone (needs ≥ 2 B-roll files)."""
    broll = ctx.get("broll") or []
    s, e = sent["start"], sent["end"]
    if len(broll) < 2 or e - s < 2.0:
        return None
    w = sent["text"].strip().split()
    script, rest = (w[0].strip(","), w[1:]) if len(w) > 4 and len(w[0]) <= 6 else ("", w)
    lines, cur = [], ""
    for x in rest:  # greedy wrap ~24 characters a line, at most 4 lines (the comp shrinks the text past 3)
        if cur and len(cur) + 1 + len(x) > 24:
            lines.append(cur)
            cur = x
        else:
            cur = f"{cur} {x}".strip()
    lines.append(cur)
    text = "\n".join(lines[:4]) + ("…" if len(lines) > 4 else "")
    title, title_at = None, None
    nxt = ctx.get("_next")
    if nxt and "question" in nxt[1]["tags"] and nxt[0]["start"] - e < 0.6 and len(nxt[0]["text"].split()) <= 14:
        # a second, shorter question right after ("do sản phẩm tốt hay do video quá đẹp?"): its tail becomes the big title
        title = " ".join(nxt[0]["text"].strip().split()[-4:]).upper()
        title_at = round(nxt[0]["start"] - s, 2)
        e = nxt[0]["end"]
    n = min(3, len(broll))
    step = (e - s) / n
    props = {"script": script[:1].upper() + script[1:], "text": text, "items": [{"src": broll[k], "at": round(k * step, 2)} for k in range(n)]}
    if title:
        props.update({"title": title, "titleAt": title_at})
    if ctx.get("logo"):
        props["logo"] = ctx["logo"]
    return [{"type": "motion", "comp": "NeonTunnel", "start": s, "end": e, "props": props}], bool(title)


# ------------------------------------------------------------------ camera
CAM = {
    "HOOK": lambda f: {"zooms": [{"at": 0, "to": 1.32, "in": 0, "hold": 0.08, "out": 0.32, "x": f[0], "y": f[1]}]},
    "SNAP": lambda f: {"zooms": [{"at": 0, "to": 2.1, "in": 0, "hold": 0.4, "out": 0.45, "x": f[0], "y": f[1]}]},
    "EMPH": lambda f: {"zooms": [{"at": 0.3, "to": 1.25, "in": 0.12, "hold": 1.4, "out": 0.4, "x": f[0], "y": f[1]}],
                       "shake": {"at": 0.3, "dur": 0.35, "amp": 12}},
    "PUSH": lambda f: {"zoom": "in", "zoom_amount": 0.06},
    "PULL": lambda f: {"zoom": "out", "zoom_amount": 0.07},
    "PUNCH": lambda f: {"punch": 1.15},
    "STILL": lambda f: {},
}


# ------------------------------------------------------------------ the brain
def pick_captions(opt, words: list[dict], ind: str, style: str, full: str) -> str:
    """One caption system per video, varied between videos (Hiếu: keep every look, don't put word-pop on every talking head).
    wordpop = WordStack lockups, blue = two-tier BlueText. --captions forces one. Auto: the share of word-pop depends on
    the edit style, and the pick is seeded by the video's own words + --seed, so different videos land on different looks."""
    if opt.captions != "auto":
        return opt.captions
    if not words or ind == "news":
        return "blue"
    share = {"calm": 0.5, "story": 0.4, "hype": 0.3}.get(style, 0.4)
    h = int(hashlib.md5((full[:400] + str(opt.seed)).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "wordpop" if h < share else "blue"


def decide(ar: dict, words: list[dict], a: dict, opt) -> dict:
    rnd = random.Random(opt.seed)
    sents = sentences(ar, words)
    infos = [read(s, len(sents)) for s in sents]
    full = strip(" ".join(s["text"] for s in sents))
    # industry
    ind = opt.industry
    if ind == "auto":
        low_full = " ".join(s_["text"] for s_ in sents).lower()
        score = {k: sum(len(re.findall(r"(?<!\w)" + re.escape(w) + r"(?!\w)", low_full)) for w in v[4].split("|"))
                 for k, v in INDUSTRY.items()}
        ind = max(score, key=score.get) if max(score.values()) > 0 else "vlog"
    style, dens, theme_fb, relight, _ = INDUSTRY[ind]
    if opt.comedy:
        style_set = {style, "comedy"}
    else:
        style_set = {style}
    dens = {"calm": dens * 0.7, "normal": dens, "rich": dens * 1.35}[opt.density]
    total = ar["total"]
    target = max(2, round(total / 30 * dens))
    theme = opt.theme if opt.theme != "auto" else (a.get("brand_theme") or theme_fb)
    free_side = "right" if (1 - a["person"][2]) >= a["person"][0] else "left"
    ctx = {"brand": opt.brand or "", "style": style, "free_side": free_side, "broll": broll_files(opt.broll), "logo": opt.logo or "",
           "metal": "red" if theme == "red" else ("silver" if theme in ("blue", "mono", "sky") else "gold"),
           "price_label": "", "accent": GRAD.get(theme, GRAD["gold"])[1]}
    wp_mode = pick_captions(opt, words, ind, style, full)
    # score every (sentence, effect)
    cands = []
    for s, info in zip(sents, infos):
        tags = set(info["tags"])
        for name, serves, base, hero, zone, styles in CAT:
            if not (styles & style_set):
                continue
            hit = serves & tags
            if not hit:
                continue
            sc = base + 1.5 * (len(hit) - 1) + info["energy"] * 0.6 + rnd.random() * 0.8
            if zone == "person" and not a["tripod"]:
                sc -= 3
            cands.append((sc, s["i"], name, hero, zone))
    cands.sort(reverse=True)
    picks, used = {}, {}
    last_hero = []

    def ok(i, name, hero, zone):
        s = sents[i]
        if i in picks:
            return False
        if used.get(name, 0) >= (1 if hero else 2):
            return False
        for j, p in picks.items():
            if abs(sents[j]["start"] - s["start"]) < 2.4:
                return False
            if p["name"] == name and abs(j - i) <= 2:
                return False
        if hero and any(abs(t - s["start"]) < HEROES_GAP[style] for t in last_hero):
            return False
        if name == "FollowCard" and i < len(sents) - 2:
            return False
        return True

    # forced hook (sentence 0): text behind the head on tripod shots, else a decode / big keyword
    s0, i0 = sents[0], infos[0]
    k0 = keyword(s0, i0).upper()
    hook = []
    if a["tripod"] and a["person"][1] > 0.14 and 2 <= len(k0) <= 11:
        hook = [{"type": "bg", "start": s0["start"], "end": s0["end"], "blur": 24, "fade": 0.3},
                {"type": "motion", "comp": "GiantCaption", "start": s0["start"] + 0.12, "end": s0["end"], "behind": True,
                 "props": {"text": k0, "y": round(max(0.12, a["person"][1] + 0.03), 3), "size": 300 if len(k0) <= 6 else 220}}]
        picks[0] = {"name": "GiantCaption", "why": "hook: keyword behind the head", "layers": hook}
    elif 2 <= len(k0) <= 16:
        hook = build("DecodeText", s0, i0, a, ctx)
        if hook:
            picks[0] = {"name": "DecodeText", "why": "hook: keyword reveal", "layers": hook}
    if 0 in picks:
        last_hero.append(s0["start"])
    # HUD pack: a process / roadmap list becomes a full-screen chapter; an early question gets the neon tunnel (needs B-roll)
    if opt.hud != "off":
        for i in range(1, len(sents)):
            if "process" in infos[i]["tags"] or (len(infos[i]["items"]) >= 3 and "list" in infos[i]["tags"]):
                got = hud_chapter(sents, infos, i, ctx)
                if got:
                    lay, j = got
                    picks[i] = {"name": "HudChapter", "why": "process list -> full-screen HUD chapter", "layers": lay}
                    for k in range(i + 1, j + 1):
                        picks[k] = {"name": "HudChapter", "why": "(continues)", "layers": []}
                    last_hero.append(sents[i]["start"])
                    break
        for i in range(1, min(5, len(sents))):
            if i in picks or "question" not in infos[i]["tags"]:
                continue
            ctx["_next"] = (sents[i + 1], infos[i + 1]) if i + 1 < len(sents) and i + 1 not in picks else None
            got = neon_tunnel(sents[i], ctx)
            if got:
                lay, two = got
                picks[i] = {"name": "NeonTunnel", "why": "early question + B-roll -> neon tunnel", "layers": lay}
                if two:
                    picks[i + 1] = {"name": "NeonTunnel", "why": "(continues)", "layers": []}
                last_hero.append(sents[i]["start"])
                break
    for sc, i, name, hero, zone in cands:
        if len(picks) >= target:
            break
        if not ok(i, name, hero, zone):
            continue
        lay = build(name, sents[i], infos[i], a, ctx)
        if not lay:
            continue
        picks[i] = {"name": name, "why": "+".join(sorted(set(infos[i]["tags"]) & next(c[1] for c in CAT if c[0] == name))), "layers": lay}
        used[name] = used.get(name, 0) + 1
        if hero:
            last_hero.append(sents[i]["start"])
    # CTA / ending
    last = len(sents) - 1
    if last not in picks and last > 0:
        recent = {picks[j]["name"] for j in picks if j >= last - 3}
        for name in ("MapPin", "FollowCard", "SealBadge"):
            if name in recent or used.get(name):
                continue
            if name == "MapPin" and "location" not in infos[last]["tags"]:
                continue
            if name == "FollowCard" and not ({"cta"} & set(infos[last]["tags"]) or opt.brand):
                continue
            lay = build(name, sents[last], infos[last], a, ctx)
            if lay:
                picks[last] = {"name": name, "why": "ending / call to action", "layers": lay}
                break
    # camera: hook, emphasis on the strongest sentences, then alternate without three alike in a row
    energy = sorted(((infos[i]["energy"], i) for i in range(1, len(sents))), reverse=True)
    cam = {0: "HOOK"}
    big = [i for en, i in energy if en >= 2][:3]
    for k, i in enumerate(big):
        cam[i] = "SNAP" if (k == 0 and style == "hype") else "EMPH"
    cyc = ["PUSH", "PUNCH", "PULL", "PUSH", "STILL"]
    c = 0
    for i in range(1, len(sents)):
        if i in cam:
            continue
        if picks.get(i, {}).get("name") in ("popout", "dolly", "frost", "GiantCaption", "HudChapter", "NeonTunnel", "ExplainCanvas"):
            cam[i] = "STILL"
            continue
        mv = cyc[c % len(cyc)]
        if i >= 2 and cam.get(i - 1) == mv and cam.get(i - 2) == mv:
            c += 1
            mv = cyc[c % len(cyc)]
        cam[i] = mv
        c += 1
    # studio look
    studio = {}
    want = opt.studio == "on" or (opt.studio == "auto" and (a["flat"] or a["dim"]))
    if want and a["face_seen"] > 0.5:
        studio["relight"] = {"type": "relight", "preset": relight, "side": "left" if a["face"][0] >= 0.5 else "right"}
        if a["tripod"] and a.get("table_y") and ind not in ("news",):
            props = []
            for side in ("left", "right"):
                if a["side_busy"][side] < 0.06:
                    x = max(0.1, a["person"][0] * 0.5) if side == "left" else min(0.9, (1 + a["person"][2]) / 2)
                    width = 0.3 if side == ("left" if a["face"][0] >= 0.5 else "right") else 0.22
                    src = "plant" if side == "left" else ("lamp" if relight == "warm_cafe" else "plant_tall")
                    props.append({"type": "prop", "src": src, "pos": [round(x, 3), a["table_y"]], "width": width})
            studio["props"] = props
    srcs = {c.get("src") or c.get("source") for c in ar["cuts"]}
    if len(srcs - {None}) > 1:
        studio["color_match"] = True
    caps, wpop = [], []
    mode = wp_mode
    if mode == "wordpop":
        wpop = wordpop(sents, infos, picks, a, theme)
        if getattr(opt, "wordpop_look", "stack") == "duo":
            wpop = duo_slots(wpop, a)
    else:
        for s, info in zip(sents, infos):
            if picks.get(s["i"], {}).get("name") in ("HudChapter", "NeonTunnel", "ExplainCanvas"):  # full-screen graphics carry their own words
                continue
            caps += captions(s, info)
    loop = (opt.aspect == "9:16" and total < 75)
    return {"industry": ind, "style": style, "theme": theme, "density_target": target, "sentences": [
        {"i": s["i"], "start": s["start"], "end": s["end"], "text": s["text"], "tags": info["tags"], "cam": cam.get(s["i"], "STILL"),
         "effect": picks.get(s["i"], {}).get("name"), "why": picks.get(s["i"], {}).get("why")} for s, info in zip(sents, infos)],
        "picks": {str(i): p for i, p in picks.items()}, "cam": {str(i): v for i, v in cam.items()}, "captions": caps, "wordpop": wpop,
        "captions_mode": mode,
        "studio": studio, "loopback": loop}


def to_plan(ar: dict, a: dict, b: dict, opt, root: Path) -> dict:
    face = a["face"]
    cap_y = round(min(0.8, max(0.66, a["face"][1] + a["face_h"] * 2.6)), 3)
    st, total = ar["starts"], ar["total"]
    clips = []
    for i in range(len(st)):
        e = st[i + 1] if i + 1 < len(st) else total
        clips.append({"src": ar["src"], "in": st[i], "out": e, "focus": face[0], **CAM[b["cam"].get(str(i), "STILL")](face)})
    ov = []
    if b["studio"].get("props"):
        ov += b["studio"]["props"]
    if b["studio"].get("relight"):
        ov.append(b["studio"]["relight"])
    for i in sorted(b["picks"], key=int):
        ov += b["picks"][i]["layers"]
    for c in b["captions"]:
        ov.append({"type": "motion", "comp": "BlueText", "start": c["start"], "end": c["end"],
                   "props": {"top": c["top"], "text": c["text"], "y": cap_y, "tone": "video"}})
    if b.get("wordpop"):
        if a["tripod"] and a.get("face_seen", 1) > 0.5:  # thin white type needs a calmer room: blur + darken behind the speaker
            s0 = 0.0
            if b["picks"].get("0", {}).get("name") == "GiantCaption":  # the hook already blurs sentence 0
                s0 = b["sentences"][0]["end"]
            ov.insert(0, {"type": "bg", "blur": 12, "tint": "0x0A0F1A@0.26", "choke": 3, "start": s0, "end": total})
        ov += b["wordpop"]
    if b["loopback"]:
        ov.append({"type": "loopback", "duration": 0.5})
    tr = ar.get("transcript")
    plan = {"output": opt.output, "theme": b["theme"],
            "sound_design": {"style": "trend", "brain": {"transcripts": [tr] if tr else [], "offset": 0, "comedy": bool(opt.comedy)}},
            "keep_timing": True, "canvas": {"aspect": opt.aspect, "fps": 30}, "font": "Be Vietnam Pro Bold",
            "clips": clips, "overlays": ov, "sfx": [], "audio": {"normalize": -14}, "fade_out": 0.4, "quality": "high"}
    if b["studio"].get("color_match"):
        plan["color_match"] = {"strength": 0.7}
    return plan


def broll_files(spec: str | None) -> list[str]:
    """--broll: a folder (its videos and images, sorted) or a comma-separated list of files."""
    if not spec:
        return []
    p = Path(spec)
    ext = {".mp4", ".mov", ".webm", ".m4v", ".png", ".jpg", ".jpeg", ".webp"}
    if p.is_dir():
        return [str(f.resolve()) for f in sorted(p.iterdir()) if f.suffix.lower() in ext]
    return [str(Path(x.strip()).resolve()) for x in spec.split(",") if x.strip() and Path(x.strip()).suffix.lower() in ext]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("aroll", help="edited/aroll.json from aroll.py")
    ap.add_argument("--industry", default="auto", choices=["auto", *INDUSTRY])  # car = ô tô / xe máy
    ap.add_argument("--theme", default="auto")
    ap.add_argument("--brand", default="")
    ap.add_argument("--aspect", default="auto")
    ap.add_argument("--density", default="normal", choices=["calm", "normal", "rich"])
    ap.add_argument("--studio", default="auto", choices=["auto", "on", "off"])
    ap.add_argument("--comedy", action="store_true")
    ap.add_argument("--broll", default=None, help="folder or comma list of B-roll clips / screenshots (HUD chapter cards, neon tunnel)")
    ap.add_argument("--logo", default=None, help="logo image for the neon tunnel")
    ap.add_argument("--hud", default="auto", choices=["auto", "off"], help="full-screen HUD chapter on a process list (off = never)")
    ap.add_argument("--captions", default="auto", choices=["auto", "wordpop", "blue"],
                    help="auto = one look per video, varied between videos; wordpop = WordStack word-by-word lockups; blue = two-tier BlueText")
    ap.add_argument("--wordpop-look", default="stack", choices=["stack", "duo"],
                    help="stack = one lockup at a time, words fly in (default); duo = listing-editor look: two lockups at once "
                         "(top / low slot), grey pop-in, strobing keys, drift-up exit")
    ap.add_argument("--seed", type=int, default=0, help="change it to get a different but equally valid pick")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--plan", default=None, help="also write a complete plan_vip.json")
    ap.add_argument("--output", default="video_vip.mp4", help="video name written into the plan")
    opt = ap.parse_args()
    arp = Path(opt.aroll).resolve()
    root = arp.parent
    ar = json.loads(arp.read_text(encoding="utf-8"))
    src = (root / ar["src"]).resolve() if not Path(ar["src"]).is_absolute() else Path(ar["src"])
    words = []
    if not ar.get("transcript"):  # older aroll.json: look for <video>.transcript.json next to it
        guess = src.with_suffix(".transcript.json")
        if guess.exists():
            ar["transcript"] = guess.name
    if ar.get("transcript"):  # aroll.transcript.json: word times already on the aroll timeline (case kept for captions)
        tr = json.loads((root / ar["transcript"]).read_text(encoding="utf-8"))
        words = [{"start": float(w["start"]), "end": float(w["end"]), "word": unicodedata.normalize("NFC", str(w["word"]).strip())}
                 for seg in tr.get("segments", []) for w in (seg.get("words") or [])]
    a = watch(src, ar["total"])
    if opt.aspect == "auto":
        opt.aspect = a["aspect"]
    BRAND_HINT["name"] = opt.brand
    b = decide(ar, words, a, opt)
    out = Path(opt.out) if opt.out else root / "brain.json"
    out.write_text(json.dumps({"analysis": a, **b}, ensure_ascii=False, indent=1), encoding="utf-8")
    # short report for the editor (Claude): what was seen, what was picked and why
    print(f"[brain] {ar['total']:.1f}s, {len(b['sentences'])} câu | ngành {b['industry']} ({b['style']}) | màu {b['theme']}"
          f"{' (theo logo)' if a.get('brand_theme') == b['theme'] else ''} | mặt {a['face']} cao {a['face_h']} | "
          f"{'máy cố định' if a['tripod'] else 'cầm tay'} | sáng {a['luma']} tương phản {a['contrast']}"
          f"{' (phẳng)' if a['flat'] else ''}{' (tối)' if a['dim'] else ''} | mặt bàn {a['table_y']} | hiệu ứng {len(b['picks'])}/{b['density_target']}")
    if b["studio"]:
        print(f"[brain] studio: {', '.join(k + ('=' + v['preset'] if isinstance(v, dict) and 'preset' in v else '') for k, v in b['studio'].items())}"
              f"{' + ' + str(len(b['studio'].get('props', []))) + ' phụ kiện' if b['studio'].get('props') else ''}")
    for s in b["sentences"]:
        print(f"  {s['start']:6.2f} {s['cam']:5} {(s['effect'] or '-'):12} {('[' + ','.join(s['tags']) + ']'):28} {s['text'][:58]}")
    print(f"[brain] phụ đề: {'chữ nhảy WordStack' if b.get('captions_mode') == 'wordpop' else 'BlueText 2 tầng'}"
          f" (đổi bằng --captions wordpop|blue hoặc --seed)")
    if b.get("wordpop"):
        print(f"[brain] chữ nhảy WordStack: {len(b['wordpop'])} cụm ({sum(1 for o in b['wordpop'] if o.get('behind'))} cụm nấp sau đầu)"
              f" | từ khoá: {', '.join(' '.join(w['w'] for w in o['props']['words'] if w['k']) or '-' for o in b['wordpop'][:12])}…")
    if opt.plan:
        plan = to_plan(ar, a, b, opt, root)
        Path(opt.plan).write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[brain] plan -> {opt.plan} ({len(plan['clips'])} clip, {len(plan['overlays'])} lớp)")
    print(f"[brain] -> {out}")


if __name__ == "__main__":
    main()
