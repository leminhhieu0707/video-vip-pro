"""Real-map toolkit for real-estate videos: satellite mosaics, exact positions, road routes, distances, VN-2000.

    python geo.py build spec.json -o work/geo         # -> work/geo/geomap.json (props for the GeoMap comp) + level JPGs
    python geo.py geocode "Vinhomes Làng Vân, Đà Nẵng"  # lat, lon (OpenStreetMap Nominatim)
    python geo.py vn2000 548123.45 1789456.78 --meridian 107.75   # sổ đỏ coordinates (VN-2000 TM3) -> WGS84 lat, lon

spec.json (all coordinates WGS84 lat/lon; a place name string is geocoded):
{
  "source": "esri",                         # esri (default, free with attribution) | mapbox (env MAPBOX_TOKEN)
  "levels": [11, 13, 15, 17],               # zoom levels to mosaic (coarse → fine), the camera flies between them
  "site": {"name": "Làng Vân", "osm": "Vinhomes Làng Vân, Đà Nẵng"}   # or "ring": [[lat, lon], …] or "vn2000": {...}
  "pois": [{"name": "Sân bay Đà Nẵng", "at": [16.0426, 108.1972], "icon": "✈", "route": true}],
  "rings_km": [5, 10, 20],
  "camera": [{"t": 0, "at": "site", "z": 10.5, "tilt": 0}, {"t": 3, "at": "site", "z": 15.2, "tilt": 45}, …],
  "scale": 1.5                               # screen px per tile px (sharpness vs coverage)
}
Everything in the output is in Web-Mercator units (u, v in 0..1) so the comp can fly, tilt and draw lines that stay
glued to the ground. Distances / times come from OSRM (public demo server) — say "khoảng" on screen, they are estimates.
Attribution must stay on screen (the comp draws `credit`).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = Path(os.environ.get("MH_GEO_CACHE", HERE.parent / ".cache" / "tiles"))
UA = {"User-Agent": "video-vip-pro-geo/1.0"}
SOURCES = {
    "esri": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
             "Ảnh vệ tinh: Esri, Maxar, Earthstar Geographics · Dữ liệu: © OpenStreetMap"),
    "mapbox": ("https://api.mapbox.com/v4/mapbox.satellite/{z}/{x}/{y}@2x.jpg90?access_token={token}",
               "© Mapbox © Maxar · Dữ liệu: © OpenStreetMap"),
}
EARTH = 40075016.686


# ------------------------------------------------------------------ projection
def merc(lat: float, lon: float) -> tuple[float, float]:
    """WGS84 -> Web-Mercator unit square (u right, v down)."""
    s = math.sin(math.radians(max(-85.0, min(85.0, lat))))
    return (lon + 180.0) / 360.0, 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)


def unmerc(u: float, v: float) -> tuple[float, float]:
    lon = u * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * v))))
    return lat, lon


def meters_per_unit(lat: float) -> float:
    return EARTH * math.cos(math.radians(lat))


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def ring_area_m2(ring: list[tuple[float, float]]) -> float:
    lat0 = sum(p[0] for p in ring) / len(ring)
    k = math.cos(math.radians(lat0))
    xy = [(math.radians(p[1]) * 6371008.8 * k, math.radians(p[0]) * 6371008.8) for p in ring]
    return abs(sum(xy[i][0] * xy[i - 1][1] - xy[i - 1][0] * xy[i][1] for i in range(len(xy)))) / 2


def vn2000_to_wgs84(x_east: float, y_north: float, meridian: float, k0: float = 0.9999) -> tuple[float, float]:
    """Sổ đỏ coordinates (VN-2000, TM3 zone with the province's central meridian, k0 0.9999, false easting 500 km)
    -> WGS84. Uses the official 7-parameter Helmert shift (TT 973/2001/TT-TCĐC). Accuracy ~1–2 m.
    In the sổ đỏ table "X" is usually NORTHING and "Y" EASTING — pass them in the right order."""
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    x = (x_east - 500000.0) / k0
    M = y_north / k0
    mu = M / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
          + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    C1, T1 = ep2 * math.cos(p1) ** 2, math.tan(p1) ** 2
    N1 = a / math.sqrt(1 - e2 * math.sin(p1) ** 2)
    R1 = a * (1 - e2) / (1 - e2 * math.sin(p1) ** 2) ** 1.5
    D = x / N1
    lat = p1 - (N1 * math.tan(p1) / R1) * (D ** 2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1 ** 2 - 9 * ep2) * D ** 4 / 24
                                             + (61 + 90 * T1 + 298 * C1 + 45 * T1 ** 2 - 252 * ep2 - 3 * C1 ** 2) * D ** 6 / 720)
    lon = math.radians(meridian) + (D - (1 + 2 * T1 + C1) * D ** 3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1 ** 2 + 8 * ep2 + 24 * T1 ** 2) * D ** 5 / 120) / math.cos(p1)
    # VN-2000 geodetic -> ECEF -> Helmert -> WGS84 geodetic
    N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    X, Y, Z = N * math.cos(lat) * math.cos(lon), N * math.cos(lat) * math.sin(lon), N * (1 - e2) * math.sin(lat)
    dx, dy, dz = -191.90441429, -39.30318279, -111.45032835
    rx, ry, rz = [math.radians(s / 3600) for s in (0.00928836, -0.01975479, 0.00427372)]
    sc = 1 + 0.252906278e-6
    X2 = dx + sc * (X - rz * Y + ry * Z)
    Y2 = dy + sc * (rz * X + Y - rx * Z)
    Z2 = dz + sc * (-ry * X + rx * Y + Z)
    lon2 = math.atan2(Y2, X2)
    pp = math.hypot(X2, Y2)
    lat2 = math.atan2(Z2, pp * (1 - e2))
    for _ in range(6):
        N2 = a / math.sqrt(1 - e2 * math.sin(lat2) ** 2)
        lat2 = math.atan2(Z2 + e2 * N2 * math.sin(lat2), pp)
    return math.degrees(lat2), math.degrees(lon2)


# ------------------------------------------------------------------ web services (cached)
def _get(url: str, params: dict | None = None, binary: bool = False, wait: float = 0.0, timeout: float = 30):
    import requests
    key = hashlib.md5((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    cf = CACHE.parent / "web" / key
    if cf.exists():
        data = cf.read_bytes()
        return data if binary else json.loads(data.decode("utf-8"))
    time.sleep(wait)
    r = requests.get(url, params=params, headers=UA, timeout=timeout)
    r.raise_for_status()
    cf.parent.mkdir(parents=True, exist_ok=True)
    cf.write_bytes(r.content)
    return r.content if binary else r.json()


def _post(url: str, data: dict, timeout: float = 60):
    """POST form (Overpass wants its query in the body), cached like _get."""
    import requests
    key = hashlib.md5((url + json.dumps(data, sort_keys=True)).encode()).hexdigest()
    cf = CACHE.parent / "web" / key
    if cf.exists():
        return json.loads(cf.read_text(encoding="utf-8"))
    r = requests.post(url, data=data, headers=UA, timeout=timeout)
    r.raise_for_status()
    cf.parent.mkdir(parents=True, exist_ok=True)
    cf.write_bytes(r.content)
    return r.json()


def geocode(q: str, polygon: bool = False) -> dict | None:
    r = _get("https://nominatim.openstreetmap.org/search", {"q": q, "format": "json", "limit": 1, "countrycodes": "vn",
                                                           "polygon_geojson": 1 if polygon else 0}, wait=1.1)
    if not r:
        return None
    d = r[0]
    out = {"lat": float(d["lat"]), "lon": float(d["lon"]), "name": d.get("display_name", "")}
    g = d.get("geojson") or {}
    if g.get("type") == "Polygon":
        out["ring"] = [(p[1], p[0]) for p in g["coordinates"][0]]
    elif g.get("type") == "MultiPolygon":
        out["ring"] = [(p[1], p[0]) for p in max(g["coordinates"], key=lambda c: len(c[0]))[0]]
    return out


def route(a: tuple[float, float], b: tuple[float, float]) -> dict:
    r = _get(f"https://router.project-osrm.org/route/v1/driving/{a[1]},{a[0]};{b[1]},{b[0]}",
             {"overview": "full", "geometries": "geojson"}, wait=0.5)
    rt = r["routes"][0]
    return {"km": round(rt["distance"] / 1000, 1), "min": max(1, round(rt["duration"] / 60)),
            "line": [(p[1], p[0]) for p in rt["geometry"]["coordinates"]]}


def tile(src: str, z: int, x: int, y: int):
    from PIL import Image
    url, _ = SOURCES[src]
    fp = CACHE / src / str(z) / str(x) / f"{y}.jpg"
    if not fp.exists():
        token = os.environ.get("MAPBOX_TOKEN", "")
        if src == "mapbox" and not token:
            raise SystemExit("mapbox needs MAPBOX_TOKEN in the environment")
        data = _get(url.format(z=z, x=x, y=y, token=token), binary=True)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(data)
    im = Image.open(fp).convert("RGB")
    im = im.resize((256, 256)) if im.size != (256, 256) else im
    if z > 3 and _placeholder(im):  # "Map data not yet available": zoom the parent tile instead
        par = tile(src, z - 1, x // 2, y // 2)
        q = par.crop(((x % 2) * 128, (y % 2) * 128, (x % 2) * 128 + 128, (y % 2) * 128 + 128))
        return q.resize((256, 256), Image.LANCZOS)
    return im


def _placeholder(im) -> bool:
    import numpy as np
    a = np.asarray(im, dtype=np.float32)
    return float(a.std()) < 12 and 185 < float(a.mean()) < 225  # flat light-grey "no imagery" tile


# ------------------------------------------------------------------ plots
DIRS = ["Bắc", "Đông Bắc", "Đông", "Đông Nam", "Nam", "Tây Nam", "Tây", "Tây Bắc"]


def fmt_m(v: float) -> str:
    return (f"{v:.1f}".rstrip("0").rstrip(".") + " m").replace(".", ",")


def facing_name(bearing_deg: float) -> str:
    return DIRS[int(((bearing_deg % 360) + 22.5) // 45) % 8]


def make_lots(spec: dict) -> list[dict]:
    """A row of lots along a frontage: {"front": [[lat, lon], [lat, lon]] (the road edge, lots numbered from the first
    point), "width_m": 5 (or "widths": [5, 5, 6, …]), "depth_m": 20, "side": "right" | "left" (where the lots lie when
    walking from front[0] to front[1]), "start": 1, "status": {"3": "sold", "7": "reserved"} (default "available")}.
    Several rows: a list of such dicts. Each lot gets its facing direction (towards the road)."""
    rows = spec if isinstance(spec, list) else [spec]
    out = []
    for row in rows:
        (la0, lo0), (la1, lo1) = row["front"]
        k = math.cos(math.radians(la0))
        D = 6371008.8 * math.pi / 180  # same sphere as haversine / Web Mercator, so edges read back exactly
        mx = lambda la, lo: ((lo - lo0) * D * k, (la - la0) * D)  # local metres, x east, y north
        back = lambda x, y: (la0 + y / D, lo0 + x / (D * k))
        ex, ey = mx(la1, lo1)
        L = math.hypot(ex, ey)
        ux, uy = ex / L, ey / L
        nx, ny = (uy, -ux) if row.get("side", "right") == "right" else (-uy, ux)
        depth = float(row.get("depth_m", 20))
        widths = row.get("widths") or [float(row.get("width_m", 5))] * int(L // float(row.get("width_m", 5)))
        road_bearing = math.degrees(math.atan2(-nx, -ny))  # from the lot towards the road
        pos, n0 = 0.0, int(row.get("start", 1))
        st = {str(a): b for a, b in (row.get("status") or {}).items()}
        for i, w in enumerate(widths):
            if pos + w > L + 0.01:
                break
            p0 = (ux * pos, uy * pos)
            p1 = (ux * (pos + w), uy * (pos + w))
            ring = [p0, p1, (p1[0] + nx * depth, p1[1] + ny * depth), (p0[0] + nx * depth, p0[1] + ny * depth)]
            lab = str(n0 + i)
            out.append({"label": lab, "status": st.get(lab, "available"), "w": w, "d": depth, "facing": facing_name(road_bearing),
                        "ring": [back(*p) for p in ring]})
            pos += w
    return out


# ------------------------------------------------------------------ build
def simplify(pts: list[tuple[float, float]], tol: float) -> list[tuple[float, float]]:
    """Douglas–Peucker on (u, v)."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1e-12
    dmax, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / L
        if d > dmax:
            dmax, idx = d, i
    if dmax <= tol:
        return [pts[0], pts[-1]]
    return simplify(pts[: idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def mosaic(src: str, z: int, u0: float, v0: float, u1: float, v1: float, out: Path, max_tiles: int = 196) -> dict:
    from PIL import Image
    n = 2 ** z
    x0, x1 = int(math.floor(u0 * n)), int(math.floor(u1 * n))
    y0, y1 = int(math.floor(v0 * n)), int(math.floor(v1 * n))
    while (x1 - x0 + 1) * (y1 - y0 + 1) > max_tiles:  # too big: shrink around the middle
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        x0, x1 = int(cx - (x1 - x0) * 0.42), int(cx + (x1 - x0) * 0.42)
        y0, y1 = int(cy - (y1 - y0) * 0.42), int(cy + (y1 - y0) * 0.42)
    img = Image.new("RGB", ((x1 - x0 + 1) * 256, (y1 - y0 + 1) * 256))
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            img.paste(tile(src, z, x % n, y), ((x - x0) * 256, (y - y0) * 256))
    img.save(out, quality=88)
    return {"src": str(out), "z": z, "u0": x0 / n, "v0": y0 / n, "du": (x1 - x0 + 1) / n, "dv": (y1 - y0 + 1) / n}


def build(spec: dict, outdir: Path, W: int = 1080, H: int = 1920) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    src = spec.get("source", "esri")
    S = float(spec.get("scale", 1.5))
    site = spec.get("site") or {}
    ring: list[tuple[float, float]] = []
    lots = make_lots(spec["lots"]) if spec.get("lots") else []
    if lots and site.get("lot") is not None:  # the plot for sale is one lot of the subdivision
        hit = next((l for l in lots if str(l["label"]) == str(site["lot"])), None)
        if hit:
            site.setdefault("ring", hit["ring"])
            site.setdefault("facing", hit["facing"])
    if site.get("ring"):
        ring = [tuple(p) for p in site["ring"]]
    elif site.get("vn2000"):
        vv = site["vn2000"]
        ring = [vn2000_to_wgs84(p[1], p[0], vv["meridian"]) if vv.get("xy_order", "NE") == "NE" else vn2000_to_wgs84(p[0], p[1], vv["meridian"])
                for p in vv["points"]]
    elif site.get("osm"):
        g = geocode(site["osm"], polygon=True)
        if not g:
            raise SystemExit(f"not found on OpenStreetMap: {site['osm']}")
        ring = g.get("ring") or []
        site.setdefault("at", [g["lat"], g["lon"]])
    if ring and ring[0] == ring[-1]:
        ring = ring[:-1]
    if ring:
        c_lat, c_lon = sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)
    else:
        at = site.get("at")
        if isinstance(at, str):
            g = geocode(at)
            at = [g["lat"], g["lon"]]
        c_lat, c_lon = at
    cu, cv = merc(c_lat, c_lon)
    mpu = meters_per_unit(c_lat)
    res = {"site": {"name": site.get("name", ""), "u": cu, "v": cv, "lat": round(c_lat, 6), "lon": round(c_lon, 6)}, "mpu": mpu}
    if ring:
        pts = [merc(*p) for p in ring]
        area = ring_area_m2(ring)
        edges = []
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            edges.append(round(haversine_km(a, b) * 1000, 1))
        res["site"].update({"ring": [[round(u, 9), round(v, 9)] for u, v in pts], "area_m2": round(area, 1), "edges_m": edges})
        if site.get("facing"):
            res["site"]["facing"] = site["facing"]
    if lots:
        res["lots"] = [{"label": l["label"], "status": l["status"], "w": l["w"], "d": l["d"], "area": round(l["w"] * l["d"], 1),
                        "facing": l["facing"], "ring": [[round(a, 9), round(b, 9)] for a, b in (merc(*p) for p in l["ring"])]} for l in lots]
    roads = []
    for r in spec.get("roads", []):  # a measured road width: two points across the road (from the satellite or the plan)
        a, b = tuple(r["across"][0]), tuple(r["across"][1])
        wm = r.get("width_m") or round(haversine_km(a, b) * 1000, 1)
        roads.append({"a": list(merc(*a)), "b": list(merc(*b)), "width_m": wm, "label": r.get("label") or f"Đường {fmt_m(wm)}"})
    res["roads"] = roads
    pois = []
    for p in spec.get("pois", []):
        at = p["at"]
        if isinstance(at, str):
            g = geocode(at)
            if not g:
                print(f"[geo] skip, not found: {at}", file=sys.stderr)
                continue
            at = [g["lat"], g["lon"]]
        u, v = merc(*at)
        item = {"name": p["name"], "icon": p.get("icon", "📍"), "u": u, "v": v, "km_air": round(haversine_km((c_lat, c_lon), tuple(at)), 1)}
        if p.get("route"):
            rt = route((c_lat, c_lon), tuple(at))
            line = [merc(*q) for q in rt["line"]]
            line = simplify(line, 1.2 / (256 * 2 ** 16))
            item.update({"km": rt["km"], "min": rt["min"], "line": [[round(a, 9), round(b, 9)] for a, b in line]})
        pois.append(item)
    res["pois"] = pois
    res["rings"] = [{"km": k, "r": k * 1000 / mpu} for k in spec.get("rings_km", [])]
    # camera keys
    cams = []
    for c in spec.get("camera", [{"t": 0, "at": "site", "z": 15, "tilt": 0}]):
        at = c.get("at", "site")
        if at == "site":
            u, v = cu, cv
        elif isinstance(at, str):
            hit = next((p for p in pois if p["name"] == at), None)
            u, v = (hit["u"], hit["v"]) if hit else (cu, cv)
        else:
            u, v = merc(*at)
        cams.append({"t": c["t"], "u": u, "v": v, "z": c["z"], "tilt": c.get("tilt", 0), "rot": c.get("rot", 0)})
    res["camera"] = cams
    # mosaic levels: each covers what the camera can see while it is the sharpest level, plus every route
    levels = []
    allu = [cu] + [p["u"] for p in pois] + [q[0] for p in pois for q in p.get("line", [])] + [c["u"] for c in cams]
    allv = [cv] + [p["v"] for p in pois] + [q[1] for p in pois for q in p.get("line", [])] + [c["v"] for c in cams]
    for z in spec.get("levels", [11, 13, 15, 17]):
        span_u = W / (256 * S * 2 ** z) * 1.6  # the view at zoom z, generous for tilt
        span_v = H / (256 * S * 2 ** z) * 2.6  # tilted views see far towards the horizon
        near = [i for i, c in enumerate(cams) if c["z"] >= z - 1.5] or [int(max(range(len(cams)), key=lambda i: cams[i]["z"]))]
        us = [cams[i]["u"] for i in near] + ([min(allu), max(allu)] if z <= min(spec.get("levels", [11])) + 2 else [])
        vs = [cams[i]["v"] for i in near] + ([min(allv), max(allv)] if z <= min(spec.get("levels", [11])) + 2 else [])
        lv = mosaic(src, z, min(us) - span_u / 2, min(vs) - span_v / 2, max(us) + span_u / 2, max(vs) + span_v / 2,
                    outdir / f"level_z{z}.jpg", max_tiles=int(spec.get("max_tiles", 196)))
        levels.append(lv)
        print(f"[geo] z{z}: {int(lv['du'] * 2 ** z)}x{int(lv['dv'] * 2 ** z)} tiles -> {lv['src']}")
    if spec.get("world"):  # whole-Earth texture for GlobeIntro (zoom 3, 8×8 tiles, Web-Mercator)
        w = mosaic(src, 3, 0.0, 0.0, 0.9999, 0.9999, outdir / "world_z3.jpg", max_tiles=64)
        res["world"] = w["src"]
        print(f"[geo] địa cầu -> {w['src']}")
    if spec.get("superres") and levels:  # one sharper level past the last real one, around the site (Lanczos ×2 + unsharp)
        levels.append(superres_level(levels[-1], cu, cv, outdir, tiles=int(spec.get("superres_tiles", 6))))
        print(f"[geo] z{levels[-1]['z']}: làm nét quanh lô -> {levels[-1]['src']}")
    res["levels"] = levels
    res["scale"] = S
    if spec.get("vector"):
        vs = spec["vector"] if isinstance(spec["vector"], dict) else {}
        res["vector"] = osm_vector(c_lat, c_lon, float(vs.get("radius_m", 1500)), float(vs.get("buildings_m", 450)))
        print(f"[geo] OSM: {len(res['vector']['roads'])} đường, {len(res['vector']['buildings'])} nhà, {len(res['vector']['water'])} mặt nước")
    if spec.get("plans"):
        res["plans"] = [plan_quad(pl, Path(spec.get("_root", "."))) for pl in spec["plans"]]
    if spec.get("isochrone_min"):
        res["iso"] = isochrones((c_lat, c_lon), [float(m) for m in spec["isochrone_min"]])
        print(f"[geo] vùng phút: {[b['min'] for b in res['iso']]}")
    res["credit"] = SOURCES[src][1]
    (outdir / "geomap.json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    return res


def superres_level(lv: dict, cu: float, cv: float, outdir: Path, tiles: int = 6) -> dict:
    from PIL import Image, ImageFilter
    im = Image.open(lv["src"])
    W0, H0 = im.size
    px = lambda u, v: ((u - lv["u0"]) / lv["du"] * W0, (v - lv["v0"]) / lv["dv"] * H0)
    x, y = px(cu, cv)
    half = tiles * 128
    box = [int(max(0, x - half)), int(max(0, y - half)), int(min(W0, x + half)), int(min(H0, y + half))]
    crop = im.crop(box).resize(((box[2] - box[0]) * 2, (box[3] - box[1]) * 2), Image.LANCZOS)
    crop = crop.filter(ImageFilter.UnsharpMask(radius=2.2, percent=90, threshold=2))
    out = outdir / f"level_z{lv['z'] + 1}_sr.jpg"
    crop.save(out, quality=90)
    return {"src": str(out), "z": lv["z"] + 1, "u0": lv["u0"] + box[0] / W0 * lv["du"], "v0": lv["v0"] + box[1] / H0 * lv["dv"],
            "du": (box[2] - box[0]) / W0 * lv["du"], "dv": (box[3] - box[1]) / H0 * lv["dv"]}


MAJOR = {"motorway", "trunk", "primary", "secondary", "tertiary", "motorway_link", "trunk_link", "primary_link"}


def osm_vector(lat: float, lon: float, radius: float, b_radius: float) -> dict:
    """Roads (with names), water, parks and building footprints around the site from OpenStreetMap (Overpass)."""
    q = f"""[out:json][timeout:60];
(way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified|living_street|motorway_link|trunk_link|primary_link"](around:{radius:.0f},{lat},{lon});
 way["natural"="water"](around:{radius:.0f},{lat},{lon}); way["waterway"="riverbank"](around:{radius:.0f},{lat},{lon});
 way["leisure"="park"](around:{radius:.0f},{lat},{lon}); way["landuse"~"grass|recreation_ground"](around:{radius:.0f},{lat},{lon});
 way["building"](around:{b_radius:.0f},{lat},{lon}););
out geom tags;"""
    d, last = None, None
    for ep in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
               "https://overpass.private.coffee/api/interpreter"):
        try:
            d = _post(ep, {"data": q}, timeout=120)
            break
        except Exception as e:  # noqa: BLE001  (busy mirror: try the next one)
            last = e
    if d is None:
        raise SystemExit(f"OpenStreetMap (Overpass) không trả lời: {last}")
    tol = 0.6 / (256 * 2 ** 17)
    out = {"roads": [], "water": [], "parks": [], "buildings": []}
    for el in d.get("elements", []):
        g = el.get("geometry") or []
        if len(g) < 2:
            continue
        pts = simplify([merc(p["lat"], p["lon"]) for p in g], tol)
        pts = [[round(a, 9), round(b, 9)] for a, b in pts]
        tg = el.get("tags", {})
        if "highway" in tg:
            out["roads"].append({"pts": pts, "major": tg["highway"] in MAJOR, "name": tg.get("name", "")})
        elif "building" in tg:
            lv = tg.get("building:levels")
            out["buildings"].append({"pts": pts, "levels": int(lv) if str(lv).isdigit() else None})
        elif tg.get("natural") == "water" or tg.get("waterway") == "riverbank":
            out["water"].append(pts)
        else:
            out["parks"].append(pts)
    out["buildings"] = out["buildings"][:400]
    return out


def plan_quad(pl: dict, root: Path) -> dict:
    """A planning map image laid on the satellite: {"image": "qh.jpg", "points": [[px, py, lat, lon], …]} (≥ 3 control points;
    4+ fits a perspective warp). Returns the image corners in Mercator units for GeoMap's `plans`."""
    import numpy as np
    from PIL import Image
    img = Path(pl["image"]) if Path(pl["image"]).is_absolute() else root / pl["image"]
    w, h = Image.open(img).size
    P = np.array([[p[0], p[1]] for p in pl["points"]], float)
    Q = np.array([merc(p[2], p[3]) for p in pl["points"]], float)
    corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
    if len(P) >= 4:  # homography (DLT)
        A = []
        for (x, y), (u, v) in zip(P, Q):
            A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
            A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
        Hm = np.linalg.svd(np.array(A))[2][-1].reshape(3, 3)
        c = np.c_[corners, np.ones(4)] @ Hm.T
        quad = c[:, :2] / c[:, 2:3]
    else:  # affine from 3 points
        M = np.linalg.lstsq(np.c_[P, np.ones(len(P))], Q, rcond=None)[0]
        quad = np.c_[corners, np.ones(4)] @ M
    return {"src": str(img), "w": w, "h": h, "quad": [[round(float(a), 10), round(float(b), 10)] for a, b in quad],
            "opacity": pl.get("opacity", 0.72), "legend": pl.get("legend", [])}


def isochrones(site: tuple[float, float], minutes: list[float], rays: int = 32) -> list[dict]:
    """Areas reachable by car within each time (OSRM table): driving time sampled along rays from the site; each band is
    the star polygon through the farthest sample still inside the time. Estimates, label them "khoảng"."""
    tmax = max(minutes)
    rmax = tmax / 60 * 55 * 1000  # metres a car could reach at ~55 km/h
    radii = [rmax * f for f in (0.06, 0.12, 0.19, 0.27, 0.36, 0.46, 0.57, 0.69, 0.82, 1.0)]
    pts = []
    for a in range(rays):
        ang = 2 * math.pi * a / rays
        for r in radii:
            dlat = r * math.cos(ang) / 111195.0
            dlon = r * math.sin(ang) / (111195.0 * math.cos(math.radians(site[0])))
            pts.append((site[0] + dlat, site[1] + dlon, a, r))
    dur = []
    for i in range(0, len(pts), 90):
        chunk = pts[i:i + 90]
        coords = ";".join([f"{site[1]},{site[0]}"] + [f"{p[1]},{p[0]}" for p in chunk])
        r = _get(f"https://router.project-osrm.org/table/v1/driving/{coords}", {"sources": "0"}, wait=0.6)
        dur += [(x if x is not None else 1e9) / 60 for x in r["durations"][0][1:]]
    bands = []
    for m in sorted(minutes):
        poly = []
        for a in range(rays):
            best = radii[0] * 0.5
            for (la, lo, aa, r), d in zip(pts, dur):
                if aa == a and d <= m:
                    best = max(best, r)
            ang = 2 * math.pi * a / rays
            la = site[0] + best * math.cos(ang) / 111195.0
            lo = site[1] + best * math.sin(ang) / (111195.0 * math.cos(math.radians(site[0])))
            poly.append(merc(la, lo))
        for _ in range(3):  # Chaikin smoothing: a soft blob instead of a star
            poly = [pt for i in range(len(poly)) for pt in (
                (0.75 * poly[i][0] + 0.25 * poly[(i + 1) % len(poly)][0], 0.75 * poly[i][1] + 0.25 * poly[(i + 1) % len(poly)][1]),
                (0.25 * poly[i][0] + 0.75 * poly[(i + 1) % len(poly)][0], 0.25 * poly[i][1] + 0.75 * poly[(i + 1) % len(poly)][1]))]
        bands.append({"min": m, "polys": [[[round(a, 9), round(b, 9)] for a, b in poly]]})
    return bands


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("spec")
    b.add_argument("-o", "--out", default="geo")
    b.add_argument("--aspect", default="9:16")
    g = sub.add_parser("geocode")
    g.add_argument("q")
    v = sub.add_parser("vn2000")
    v.add_argument("x_east", type=float)
    v.add_argument("y_north", type=float)
    v.add_argument("--meridian", type=float, required=True, help="province central meridian, e.g. Đà Nẵng 107.75, HCM 105.75, Hà Nội 105")
    a = ap.parse_args()
    if a.cmd == "build":
        W, H = (1080, 1920) if a.aspect == "9:16" else (1920, 1080)
        spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
        spec["_root"] = str(Path(a.spec).resolve().parent)
        res = build(spec, Path(a.out), W, H)
        s = res["site"]
        info = ""
        if s.get("ring"):
            am = s["area_m2"]
            size = f"{am / 1e4:.1f} ha" if am >= 5000 else f"{am:.1f} m²"
            info = f" | {size}, {len(s['ring'])} đỉnh, cạnh {s['edges_m']}" + (f", hướng {s['facing']}" if s.get("facing") else "")
        print(f"[geo] site {s['lat']}, {s['lon']}{info}")
        for p in res["pois"]:
            print(f"[geo]   {p['name']}: {p.get('km', p['km_air'])} km" + (f", ~{p['min']} phút" if p.get("min") else " (đường chim bay)"))
        print(f"[geo] -> {Path(a.out) / 'geomap.json'}")
    elif a.cmd == "geocode":
        print(json.dumps(geocode(a.q), ensure_ascii=False))
    else:
        print("%.7f, %.7f" % vn2000_to_wgs84(a.x_east, a.y_north, a.meridian))


if __name__ == "__main__":
    main()
