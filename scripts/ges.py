"""Google Earth Studio bridge: real 3D buildings and terrain under the skill's graphics.

GES (earth.google.com/studio, free, needs a Google account) renders the 3D city; the skill puts the plot, labels and text on
top with its own ground tracker, so it does not depend on GES's tracking-data format.

  1. python -X utf8 ges.py keys geo/geomap.json -o ges_keys.txt
       camera keyframes (latitude, longitude, altitude, heading, tilt) for GES's Camera Target / Camera Position fields,
       taken from geomap.json's camera — Hiếu types them in (or copies the moves by eye), renders 1080×1920 at 30 fps.
       Start the shot looking almost straight down (tilt ≤ 25°) so step 2 can find the plot.
  2. python -X utf8 ges.py locate first_frame.jpg geo/geomap.json -o corners.json
       finds the plot in the first GES frame by matching it against the satellite mosaic (features + homography) and
       writes the plot corners as frame fractions — exactly what TrackedPlot's "track": {"corners": …} wants. Always look
       at the check image it writes; if the match failed, read the corners off the frame yourself.
  3. Plan: the GES video as a clip, a TrackedPlot over it (labels, edges, area, ground text, drops), plus anything else.
Credit line on screen: "Google Earth" (GES requires it).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import geo  # noqa: E402


def altitude_for_zoom(z: float, lat: float, H: int = 1920, scale: float = 1.5, vfov_deg: float = 34.8) -> float:
    """Camera height (m) that shows about what GeoMap shows at zoom z (vertical field of view in GES ≈ 35°)."""
    m_per_px = geo.EARTH * math.cos(math.radians(lat)) / (256 * scale * 2 ** z)
    return m_per_px * H / (2 * math.tan(math.radians(vfov_deg) / 2))


def keys(gm: dict) -> list[dict]:
    out = []
    for c in gm.get("camera", []):
        lat, lon = geo.unmerc(c["u"], c["v"])
        alt = altitude_for_zoom(c["z"], lat, scale=gm.get("scale", 1.5))
        out.append({"t": c["t"], "target_lat": round(lat, 6), "target_lon": round(lon, 6), "altitude_m": round(alt),
                    "heading": round(-c.get("rot", 0) % 360, 1), "tilt": round(c.get("tilt", 0), 1)})
    return out


def locate(frame: Path, gm: dict, out_check: Path | None = None) -> list[list[float]]:
    import cv2
    import numpy as np
    img = cv2.imread(str(frame))
    lv = gm["levels"][-1] if gm["levels"][-1]["z"] <= 19 else gm["levels"][-2]
    sat = cv2.imread(lv["src"])
    # crop the satellite around the site so the search space is small
    W0, H0 = sat.shape[1], sat.shape[0]
    px = lambda u, v: ((u - lv["u0"]) / lv["du"] * W0, (v - lv["v0"]) / lv["dv"] * H0)
    sx, sy = px(gm["site"]["u"], gm["site"]["v"])
    r = 900
    x0, y0 = int(max(0, sx - r)), int(max(0, sy - r))
    crop = sat[y0:int(min(H0, sy + r)), x0:int(min(W0, sx + r))]
    g1 = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    g2 = cv2.equalizeHist(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY))
    sift = cv2.SIFT_create(6000)
    k1, d1 = sift.detectAndCompute(g1, None)
    k2, d2 = sift.detectAndCompute(g2, None)
    if d1 is None or d2 is None:
        raise SystemExit("no features")
    m = cv2.FlannBasedMatcher({"algorithm": 1, "trees": 5}, {"checks": 64}).knnMatch(d2, d1, k=2)
    good = [a for a, b in (p for p in m if len(p) == 2) if a.distance < 0.75 * b.distance]
    if len(good) < 12:
        raise SystemExit(f"only {len(good)} matches: read the corners off the frame instead")
    Hm, inl = cv2.findHomography(np.float32([k2[g.queryIdx].pt for g in good]), np.float32([k1[g.trainIdx].pt for g in good]), cv2.RANSAC, 5.0)
    if Hm is None or inl.sum() < 10:
        raise SystemExit("no consistent match: read the corners off the frame instead")
    ring = [px(u, v) for u, v in gm["site"]["ring"]]
    pts = cv2.perspectiveTransform(np.float32([[x - x0, y - y0] for x, y in ring]).reshape(-1, 1, 2), Hm).reshape(-1, 2)
    h, w = img.shape[:2]
    if out_check:
        chk = img.copy()
        cv2.polylines(chk, [pts.astype(np.int32).reshape(-1, 1, 2)], True, (0, 200, 255), 3)
        cv2.imwrite(str(out_check), chk)
    print(f"[ges] {int(inl.sum())} matching points")
    return [[round(float(x) / w, 4), round(float(y) / h, 4)] for x, y in pts]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("keys")
    k.add_argument("geomap"); k.add_argument("-o", "--out", default="ges_keys.txt")
    lo = sub.add_parser("locate")
    lo.add_argument("frame"); lo.add_argument("geomap"); lo.add_argument("-o", "--out", default="corners.json")
    a = ap.parse_args()
    gm = json.loads(Path(a.geomap).read_text(encoding="utf-8"))
    if a.cmd == "keys":
        ks = keys(gm)
        lines = ["Google Earth Studio — keyframes (giây · điểm nhìn · độ cao camera · hướng · độ nghiêng)", ""]
        for x in ks:
            lines.append(f"{x['t']:>5.1f}s  target {x['target_lat']}, {x['target_lon']}  |  cao {x['altitude_m']} m  |  heading {x['heading']}°  |  tilt {x['tilt']}°")
        lines += ["", "Xuất: 1080 × 1920, 30 fps, MP4 (hoặc chuỗi ảnh JPEG). Ghi nguồn \"Google Earth\" trên video."]
        Path(a.out).write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
    else:
        cs = locate(Path(a.frame), gm, Path(a.out).with_suffix(".check.jpg"))
        Path(a.out).write_text(json.dumps({"corners": cs}), encoding="utf-8")
        print(f"[ges] corners -> {a.out} (check image: {Path(a.out).with_suffix('.check.jpg')})")


if __name__ == "__main__":
    main()
