"""Read a floor-plan drawing (photo / scan / PDF page as image) into FloorPlan2D props: rooms in metres, doors, windows.

Two ways in:
  1. Claude traces it (inside Claude Code, 0 credit): look at the image, write trace.json in PIXELS (schema below), then
        python -X utf8 floorplan.py trace.json -o rooms.json --preview check.jpg
  2. Automatic (KIE.AI vision, ~1–2 credits):
        python -X utf8 floorplan.py --auto plan.jpg -o rooms.json --preview check.jpg [--title "NHÀ PHỐ 5 × 15 M"]
     (KIE_API_KEY from the environment, or --env path/to/.env)

trace.json (pixel coordinates on the image, origin top-left):
{
  "image": "plan.jpg",
  "scale": {"px": [[x1, y1], [x2, y2]], "m": 5.0},     # one dimension line read on the drawing (5000 mm = 5.0 m)
                                                       # or "px_per_m": 60
  "rooms": [{"name": "Phòng khách", "px": [[x, y], …], "label_area": 25}],   # wall centre lines, label_area if written
  "doors": [{"px": [[x1, y1], [x2, y2]]}],             # the opening on its wall; px[0] = hinge side
  "windows": [{"px": [[x1, y1], [x2, y2]]}],
  "title": "MẶT BẰNG TẦNG 1"
}
What it does: pixels → metres (y up, origin at the bottom-left of the plan), snaps near-equal wall lines together
(shared walls line up), snaps openings onto their wall, checks every room's computed m² against the area written on
the drawing and the rooms against each other (overlaps / gaps), draws the result over the original image so you can
SEE it is right, and writes rooms.json for FloorPlan2D. Always open the preview before using the result.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import re
import sys
from pathlib import Path

PAL = [(255, 196, 70), (90, 170, 255), (110, 210, 130), (255, 120, 140), (170, 130, 255), (255, 160, 90), (80, 210, 210)]


def area(pts):
    return abs(sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts)))) / 2


def cluster(vals: list[float], tol: float) -> dict[float, float]:
    """Map every value to the mean of its group (values closer than tol), rounded to 5 cm."""
    out: dict[float, float] = {}
    s = sorted(set(vals))
    group: list[float] = []
    for v in s + [math.inf]:
        if group and v - group[-1] > tol:
            m = round(sum(group) / len(group) / 0.05) * 0.05
            for g in group:
                out[g] = round(m, 2)
            group = []
        group.append(v)
    return out


def to_metres(tr: dict, tol: float = 0.15) -> dict:
    if tr.get("px_per_m"):
        s = float(tr["px_per_m"])
    else:
        (x1, y1), (x2, y2) = tr["scale"]["px"]
        s = math.hypot(x2 - x1, y2 - y1) / float(tr["scale"]["m"])
    allp = [p for r in tr["rooms"] for p in r["px"]]
    x0, y0 = min(p[0] for p in allp), max(p[1] for p in allp)
    M = lambda p: ((p[0] - x0) / s, (y0 - p[1]) / s)
    rooms = [{"name": r.get("name", f"Phòng {i + 1}"), "pts": [M(p) for p in r["px"]], "label_area": r.get("label_area")}
             for i, r in enumerate(tr["rooms"])]
    # the areas written on the drawing calibrate the scale (a dimension line read a few px off changes every length)
    ratios = sorted(r["label_area"] / area(r["pts"]) for r in rooms if r.get("label_area") and area(r["pts"]) > 0.5)
    if len(ratios) >= 3:
        med = ratios[len(ratios) // 2]
        spread = max(abs(x / med - 1) for x in ratios[1:-1]) if len(ratios) > 2 else 0
        lab = [r for r in rooms if r.get("label_area") and area(r["pts"]) > 0.5]
        med = sum(r["label_area"] for r in lab) / sum(area(r["pts"]) for r in lab)  # area-weighted: small rooms are rounded
        if abs(med - 1) > 0.02 and spread < 0.08:  # only when the scale reading was clearly off; dimension lines win otherwise
            f = math.sqrt(med)
            s /= f
            for r in rooms:
                r["pts"] = [(p[0] * f, p[1] * f) for p in r["pts"]]
            print(f"[floorplan] tỷ lệ chỉnh theo diện tích ghi trên bản vẽ: ×{f:.3f}")
    M = lambda p: ((p[0] - x0) / s, (y0 - p[1]) / s)
    xs = cluster([p[0] for r in rooms for p in r["pts"]], tol)
    ys = cluster([p[1] for r in rooms for p in r["pts"]], tol)
    for r in rooms:
        pts = [(xs[p[0]], ys[p[1]]) for p in r["pts"]]
        r["pts"] = [list(p) for i, p in enumerate(pts) if p != pts[i - 1]]  # drop points merged into their neighbour
    lines_x, lines_y = sorted(set(xs.values())), sorted(set(ys.values()))

    def snap_open(o):
        a, b = M(o["px"][0]), M(o["px"][1])
        if abs(a[0] - b[0]) < abs(a[1] - b[1]):  # vertical opening -> nearest vertical wall line
            x = min(lines_x, key=lambda v: abs(v - (a[0] + b[0]) / 2))
            return {"pts": [[x, round(a[1], 2)], [x, round(b[1], 2)]]}
        y = min(lines_y, key=lambda v: abs(v - (a[1] + b[1]) / 2))
        return {"pts": [[round(a[0], 2), y], [round(b[0], 2), y]]}

    return {"scale_px_per_m": round(s, 3), "origin_px": [x0, y0], "rooms": rooms,
            "doors": [snap_open(d) for d in tr.get("doors", [])], "windows": [snap_open(w) for w in tr.get("windows", [])]}


def check(res: dict) -> list[str]:
    """Area vs label, overlaps and holes (5 cm raster)."""
    from PIL import Image, ImageDraw
    import numpy as np
    msgs = []
    rooms = res["rooms"]
    for r in rooms:
        a = area(r["pts"])
        r["area"] = round(a, 2)
        if r.get("label_area"):
            d = (a - r["label_area"]) / r["label_area"]
            flag = "OK" if abs(d) <= 0.08 else "LỆCH"
            msgs.append(f"{flag:4} {r['name']}: tính {a:.1f} m² / ghi {r['label_area']} m² ({d * 100:+.0f}%)")
        else:
            msgs.append(f"     {r['name']}: {a:.1f} m²")
    W = max(p[0] for r in rooms for p in r["pts"])
    H = max(p[1] for r in rooms for p in r["pts"])
    k = 20  # px per metre for the raster
    acc = np.zeros((int(H * k) + 2, int(W * k) + 2), np.int16)
    for r in rooms:
        im = Image.new("L", (acc.shape[1], acc.shape[0]), 0)
        poly = [(p[0] * k, (H - p[1]) * k) for p in r["pts"]]
        dr = ImageDraw.Draw(im)
        dr.polygon(poly, fill=1)
        dr.line(poly + [poly[0]], fill=0, width=1)  # shared wall lines are not an overlap
        acc += np.array(im, np.int16)
    over = float((acc > 1).sum()) / k / k
    hole = float((acc == 0)[1:-1, 1:-1].sum()) / k / k
    msgs.append(f"tổng {W:.2f} × {H:.2f} m, phòng cộng lại {sum(r['area'] for r in rooms):.1f} m²")
    if over > 0.3:
        msgs.append(f"LỆCH phòng chồng nhau ~{over:.1f} m²")
    if hole > 0.05 * W * H:
        msgs.append(f"chú ý: {hole:.1f} m² trong khung chưa thuộc phòng nào (giếng trời / thang / sót phòng?)")
    return msgs


def preview(img_path: Path, tr: dict, res: dict, out: Path):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(img_path).convert("RGB")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    s, (x0, y0) = res["scale_px_per_m"], res["origin_px"]
    P = lambda p: (x0 + p[0] * s, y0 - p[1] * s)
    try:
        font = ImageFont.truetype(str(Path(__file__).resolve().parent.parent / "assets" / "fonts" / "BeVietnamPro-Bold.ttf"), max(12, int(s * 0.28)))
    except OSError:
        font = ImageFont.load_default()
    for i, r in enumerate(res["rooms"]):
        c = PAL[i % len(PAL)]
        poly = [P(p) for p in r["pts"]]
        d.polygon(poly, fill=c + (70,), outline=c + (255,), width=max(2, int(s * 0.05)))
        cx, cy = sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)
        txt = f"{r['name']}\n{r['area']:.1f} m²" + (f" / {r['label_area']}" if r.get("label_area") else "")
        d.multiline_text((cx, cy), txt, fill=(20, 20, 20, 255), font=font, anchor="mm", align="center", stroke_width=3, stroke_fill=(255, 255, 255, 255))
    for o, col in [(x, (230, 40, 40)) for x in res["doors"]] + [(x, (30, 120, 255)) for x in res["windows"]]:
        a, b = P(o["pts"][0]), P(o["pts"][1])
        d.line([a, b], fill=col + (255,), width=max(4, int(s * 0.12)))
    out_im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    out_im.save(out, quality=90)


# ------------------------------------------------------------------ automatic reading (KIE.AI → Claude vision)
PROMPT = """You are reading an architectural floor plan image ({w}×{h} px). Return ONLY a JSON object, no prose:
{{"scale": {{"px": [[x1,y1],[x2,y2]], "m": <metres>}}, "rooms": [{{"name": "...", "px": [[x,y],...], "label_area": <m² if written else null>}}],
 "doors": [{{"px": [[x1,y1],[x2,y2]]}}], "windows": [{{"px": [[x1,y1],[x2,y2]]}}], "title": "..."}}
Rules:
- Pixel coordinates on THIS image, origin top-left. Be precise: zoom mentally on the wall lines.
- scale: pick the clearest dimension line (e.g. "5000" or "5.0m" = 5.0 m) and give the pixel positions of its two ends.
- rooms: every enclosed space incl. yards (sân), stairs (cầu thang), WC, balconies; polygon along the WALL CENTRE LINES,
  corners in order, rectangles as 4 points. Neighbouring rooms must share the same wall coordinates. Names in Vietnamese
  as written on the drawing (expand abbreviations: P. KHÁCH -> Phòng khách, P. NGỦ -> Phòng ngủ, WC -> WC).
- label_area: the m² written inside the room, if any.
- doors: the opening on its wall (two points on the wall line), first point = hinge side. windows likewise.
"""


def kie_key(env_file: str | None) -> str:
    if os.environ.get("KIE_API_KEY"):
        return os.environ["KIE_API_KEY"]
    for f in [env_file, os.environ.get("MH_ENV_FILE")]:
        if f and Path(f).exists():
            for line in Path(f).read_text(encoding="utf-8").splitlines():
                if line.startswith("KIE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("KIE_API_KEY not found (set it, or pass --env path/to/.env)")


def auto_trace(img: Path, key: str) -> dict:
    import requests
    from PIL import Image
    im = Image.open(img)
    w, h = im.size
    mt = {".png": "image/png", ".webp": "image/webp"}.get(img.suffix.lower(), "image/jpeg")
    b64 = base64.b64encode(img.read_bytes()).decode()
    body = lambda model: {"model": model, "max_tokens": 6000, "stream": False, "messages": [{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}},
        {"type": "text", "text": PROMPT.format(w=w, h=h)}]}]}
    hdr = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    prompt = PROMPT.format(w=w, h=h)

    def gpt(model: str) -> str:  # KIE GPT: Responses API, must stream or long answers hit HTTP 524
        r = requests.post("https://api.kie.ai/openai/v1/responses", headers=hdr, stream=True, timeout=300, json={
            "model": model, "stream": True, "max_output_tokens": 8000, "input": [{"role": "user", "content": [
                {"type": "input_image", "image_url": f"data:{mt};base64,{b64}"}, {"type": "input_text", "text": prompt}]}]})
        out = []
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data:"):
                try:
                    ev = json.loads(line[5:].strip())
                except ValueError:
                    continue
                if ev.get("type") == "response.output_text.delta":
                    out.append(ev.get("delta", ""))
                elif ev.get("type") == "error" or ev.get("error"):
                    raise RuntimeError(str(ev)[:300])
        if not out and r.status_code != 200:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
        return "".join(out)

    def claude(model: str) -> str:
        j = requests.post("https://api.kie.ai/anthropic/v1/messages", json=body(model), timeout=180, headers=hdr).json()
        if "content" not in j:
            raise RuntimeError(str(j)[:300])
        return "".join(c.get("text", "") for c in j.get("content", []) if isinstance(c, dict))

    last = ""
    for model, fn in (("gpt-6.1-sol", gpt), ("claude-sonnet-5-5", claude), ("claude-haiku-5-5", claude)):
        try:
            txt = fn(model)
            j = txt
            m = re.search(r"\{.*\}", txt, re.S)
            if m:
                tr = json.loads(m.group(0))
                tr["image"] = str(img)
                print(f"[floorplan] read by {model}: {len(tr.get('rooms', []))} rooms, {len(tr.get('doors', []))} doors, {len(tr.get('windows', []))} windows")
                return tr
            last = str(j)[:300]
        except Exception as e:  # noqa: BLE001
            last = str(e)
    raise SystemExit(f"automatic reading failed: {last}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("trace", nargs="?", help="trace.json (pixels)")
    ap.add_argument("--auto", help="read this image automatically (KIE.AI)")
    ap.add_argument("--env", help=".env file holding KIE_API_KEY")
    ap.add_argument("-o", "--out", default="rooms.json")
    ap.add_argument("--preview", help="write the check image (result drawn over the drawing)")
    ap.add_argument("--title")
    ap.add_argument("--sub")
    ap.add_argument("--tol", type=float, default=0.15, help="snap wall lines closer than this (m)")
    a = ap.parse_args()
    if a.auto:
        tr = auto_trace(Path(a.auto), kie_key(a.env))
        Path(a.out).with_suffix(".trace.json").write_text(json.dumps(tr, ensure_ascii=False, indent=1), encoding="utf-8")
        base = Path(a.auto).parent
    elif a.trace:
        tr = json.loads(Path(a.trace).read_text(encoding="utf-8"))
        base = Path(a.trace).parent
    else:
        ap.error("give trace.json or --auto image")
    res = to_metres(tr, a.tol)
    for line in check(res):
        print("[floorplan] " + line)
    img = Path(tr["image"]) if Path(tr["image"]).is_absolute() else base / tr["image"]
    if a.preview and img.exists():
        preview(img, tr, res, Path(a.preview))
        print(f"[floorplan] preview -> {a.preview}")
    W = max(p[0] for r in res["rooms"] for p in r["pts"])
    H = max(p[1] for r in res["rooms"] for p in r["pts"])
    props = {"title": a.title or tr.get("title") or f"MẶT BẰNG {W:.1f} × {H:.1f} M".replace(".", ","),
             "sub": a.sub or f"Tổng {sum(r['area'] for r in res['rooms']):.0f} m²",
             "rooms": [{"name": r["name"], "pts": r["pts"]} for r in res["rooms"]], "doors": res["doors"], "windows": res["windows"]}
    Path(a.out).write_text(json.dumps(props, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[floorplan] -> {a.out} ({len(props['rooms'])} phòng, {len(props['doors'])} cửa đi, {len(props['windows'])} cửa sổ)")


if __name__ == "__main__":
    sys.exit(main())
