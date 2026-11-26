"""Effects on real footage (flycam / tripod shots) for real-estate edits. render.py calls these; each caches in <work>.

  track_plane   follow a patch of ground through a moving drone shot (KLT features + RANSAC homography, frame to frame)
                -> one 3×3 matrix per frame mapping the reference frame's canvas px to that frame's canvas px.
                Used by the TrackedPlot comp: boundary, labels, ground text and dropped cut-outs stick to the land.
  sky_masks     per-frame sky matte (bright / blue / low-texture region connected to the top edge, smoothed in time).
                Used for: sky replacement, text behind buildings ("behind": "sky"), a neon line along the skyline.
  day_to_night  one frame -> its blue-hour / night version (KIE.AI image edit, ~6 credits), cached.
  suno          instrumental music track (KIE.AI Suno), cached.

CLI (to try things on a clip without a plan):
  python -X utf8 footage.py track clip.mp4 --t0 0 --t1 6 --corners "0.30,0.55 0.62,0.52 0.70,0.70 0.28,0.74" -o track.json
  python -X utf8 footage.py sky clip.mp4 --t0 0 --t1 6 -o mask.mp4
  python -X utf8 footage.py night frame.jpg -o night.jpg
  python -X utf8 footage.py suno --style "cinematic luxury real estate, piano, strings, deep pulse" --duration 40 -o music.mp3
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from common import FFMPEG  # noqa: E402


def _frames(src: Path, s: float, e: float, fps: int, w: int, h: int, gray: bool = True) -> np.ndarray:
    pf = "gray" if gray else "rgb24"
    r = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(src), "-vf", f"fps={fps},scale={w}:{h}",
                        "-f", "rawvideo", "-pix_fmt", pf, "-"], capture_output=True)
    c = 1 if gray else 3
    n = len(r.stdout) // (w * h * c)
    a = np.frombuffer(r.stdout, np.uint8)[: n * w * h * c]
    return a.reshape(n, h, w) if gray else a.reshape(n, h, w, 3)


def _key(*parts) -> str:
    return hashlib.md5(json.dumps(parts, default=str, sort_keys=True).encode()).hexdigest()[:12]


# ------------------------------------------------------------------ plane tracking
def track_plane(src: Path, s: float, e: float, spec: dict, fps: int, work: Path, W: int, H: int) -> list[list[float]]:
    """spec = {"corners": [[x, y] ×4] (0–1 fractions of the frame at time s: the plot / ground patch), "margin": 0.6}.
    Returns per-frame homographies (row-major 9 floats) from canvas px at time s to canvas px at that frame."""
    import cv2
    src = Path(src)
    cache = work / "track" / f"plane_{_key(str(src), src.stat().st_mtime_ns, s, e, spec, fps, W, H)}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    cache.parent.mkdir(parents=True, exist_ok=True)
    w, h = 540, int(540 * H / W)
    fr = _frames(src, s, e, fps, w, h)
    if not len(fr):
        raise RuntimeError("track_plane: no frames")
    cs = np.array([[c[0] * w, c[1] * h] for c in spec["corners"]], np.float32)
    # features on and around the patch (ground texture), not on the sky or the frame edges
    mask = np.zeros((h, w), np.uint8)
    cx, cy = cs.mean(0)
    grow = 1 + float(spec.get("margin", 0.8))
    poly = ((cs - [cx, cy]) * grow + [cx, cy]).astype(np.int32)
    cv2.fillConvexPoly(mask, poly, 255)
    Hacc = np.eye(3)
    out = [np.eye(3)]
    prev = fr[0]
    pts = cv2.goodFeaturesToTrack(prev, maxCorners=500, qualityLevel=0.01, minDistance=6, mask=mask)
    for i in range(1, len(fr)):
        cur = fr[i]
        if pts is None or len(pts) < 30:
            m2 = np.zeros_like(mask)
            cv2.fillConvexPoly(m2, cv2.perspectiveTransform(poly.reshape(-1, 1, 2).astype(np.float32), Hacc).reshape(-1, 2).astype(np.int32), 255)
            pts = cv2.goodFeaturesToTrack(prev, maxCorners=500, qualityLevel=0.01, minDistance=6, mask=m2)
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, pts, None, winSize=(25, 25), maxLevel=4)
        good0, good1 = pts[st.ravel() == 1], nxt[st.ravel() == 1]
        Hs = None
        if len(good0) >= 12:
            Hs, inl = cv2.findHomography(good0, good1, cv2.RANSAC, 2.5)
            if Hs is not None:
                good1 = good1[inl.ravel() == 1]
        if Hs is None:
            Hs = np.eye(3)
        Hacc = Hs @ Hacc
        out.append(Hacc.copy())
        prev, pts = cur, good1.reshape(-1, 1, 2) if len(good1) else None
    # canvas px: scale (w,h) -> (W,H)
    S = np.diag([W / w, H / h, 1.0])
    Si = np.diag([w / W, h / H, 1.0])
    res = []
    for M in out:
        C = S @ M @ Si
        C = C / C[2, 2]
        res.append([round(float(x), 7) for x in C.ravel()])
    cache.write_text(json.dumps(res))
    print(f"[footage] tracked ground plane over {len(res)} frames")
    return res


# ------------------------------------------------------------------ sky matte
def sky_masks(src: Path, s: float, e: float, fps: int, work: Path, W: int, H: int) -> Path:
    """Grey-scale mp4 (canvas size) of the sky matte for base[s, e]: white = sky. Cached."""
    import cv2
    src = Path(src)
    out = work / "sky" / f"sky_{_key(str(src), src.stat().st_mtime_ns, s, e, fps, W, H)}.mp4"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    w, h = 360, int(360 * H / W)
    fr = _frames(src, s, e, fps, w, h, gray=False)
    masks = []
    for f in fr:
        hsv = cv2.cvtColor(f, cv2.COLOR_RGB2HSV).astype(np.float32)
        hh, ss, vv = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        g = cv2.cvtColor(f, cv2.COLOR_RGB2GRAY).astype(np.float32)
        tex = cv2.GaussianBlur(np.abs(cv2.Laplacian(g, cv2.CV_32F)), (0, 0), 3)
        blue = ((hh > 85) & (hh < 135) & (ss > 25)).astype(np.float32)
        bright = (vv > 150).astype(np.float32) * (ss < 70)
        score = np.maximum(blue, bright) * (tex < 6)
        m = (score > 0.5).astype(np.uint8)
        # keep what touches the top edge (sky is above the skyline)
        n, lab = cv2.connectedComponents(m)
        top = set(np.unique(lab[0][m[0] > 0])) - {0}
        m = np.isin(lab, list(top)).astype(np.uint8) if top else np.zeros_like(m)
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        # everything above the topmost non-sky pixel in each column stays sky (fills small holes / antennas)
        masks.append(m.astype(np.float32))
    if not masks:
        raise RuntimeError("sky_masks: no frames")
    A = np.stack(masks)
    # temporal smoothing kills flicker
    k = 5
    pad = np.concatenate([A[:1].repeat(k // 2, 0), A, A[-1:].repeat(k // 2, 0)])
    A = np.stack([pad[i:i + k].mean(0) for i in range(len(A))])
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                          "-vf", f"scale={W}:{H}:flags=bicubic,gblur=sigma=2.5", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", str(out)],
                         stdin=subprocess.PIPE)
    for m in A:
        p.stdin.write((np.clip(m, 0, 1) * 255).astype(np.uint8).tobytes())
    p.stdin.close()
    p.wait()
    print(f"[footage] sky matte {len(A)} frames -> {out.name}")
    return out


def sky_replace_overlay(src: Path, s: float, e: float, o: dict, fps: int, work: Path, W: int, H: int, root: Path) -> Path:
    """RGBA .mov for base[s, e]: the new sky (image or video, slow drift) where the matte is white; optional neon line on the
    skyline ("glow": colour). Overlaid on top, so the buildings stay the original."""
    mask = sky_masks(src, s, e, fps, work, W, H)
    out = work / "sky" / f"rep_{_key(str(mask), o, W, H)}.mov"
    if out.exists():
        return out
    d = e - s
    sky = o.get("sky")
    chain = []
    inputs = ["-i", str(mask)]
    glow = o.get("glow")
    want_sky = bool(sky) or not glow or o.get("gradient")  # glow alone keeps the original sky
    if want_sky:
        if sky:
            sp = Path(sky) if Path(sky).is_absolute() else root / sky
            if sp.suffix.lower() in (".mp4", ".mov", ".webm"):
                inputs += ["-stream_loop", "-1", "-i", str(sp)]
                chain.append(f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},trim=duration={d:.3f},setpts=PTS-STARTPTS[sk]")
            else:  # still sky: slow drift
                inputs += ["-loop", "1", "-i", str(sp)]
                chain.append(f"[1:v]scale={int(W * 1.2)}:{int(H * 1.2)}:force_original_aspect_ratio=increase,"
                             f"crop={W}:{H}:x='(iw-{W})/2+t*6':y='(ih-{H})*0.2',trim=duration={d:.3f},setpts=PTS-STARTPTS,fps={fps}[sk]")
        else:  # a clean gradient sky
            top, bot = o.get("top", "0x3E7CC9"), o.get("bottom", "0xBFD9F2")
            chain.append(f"gradients=s={W}x{H}:c0={top}:c1={bot}:x0=0:y0=0:x1=0:y1={H}:d={d:.3f}:r={fps}[sk]")
    chain.append(f"[0:v]format=gray,trim=duration={d:.3f},setpts=PTS-STARTPTS[ma]")
    if want_sky and glow:
        chain.append("[ma]split=2[ma1][ma2]")
        m_sky, m_edge = "[ma1]", "[ma2]"
    else:
        m_sky = m_edge = "[ma]"
    parts = []
    if want_sky:
        chain.append(f"[sk]{m_sky}alphamerge,format=rgba[ska]")
        parts.append("[ska]")
    if glow:  # skyline neon: a thin band where the matte changes from sky to buildings (only inside "box" = one building)
        col = str(glow).replace("#", "0x")
        bx = o.get("box")
        lim = (f",drawbox=x=0:y=0:w={int(bx[0] * W)}:h=ih:c=black:t=fill,drawbox=x={int((bx[0] + bx[2]) * W)}:y=0:w=iw:h=ih:c=black:t=fill,"
               f"drawbox=x=0:y={int((bx[1] + bx[3]) * H)}:w=iw:h=ih:c=black:t=fill") if bx else ""
        reveal = (f",geq=lum='if(lt(X,W*min(1,T/{float(o['reveal']):.2f})),lum(X,Y),0)'" if o.get("reveal") else "")
        chain.append(f"{m_edge}gblur=sigma=1.5,lut=y='if(gt(val\\,40)*lt(val\\,215)\\,255\\,0)',gblur=sigma=2.5{lim}{reveal}[edge]")
        chain.append(f"color=c={col}:s={W}x{H}:r={fps}:d={d:.3f},format=rgba[gc];[gc][edge]alphamerge[gl]")
        parts.append("[gl]")
    if len(parts) == 2:
        chain.append("[ska][gl]overlay=0:0:format=auto,format=rgba[out]")
    else:
        chain.append(f"{parts[0]}format=rgba[out]")
    subprocess.run([FFMPEG, "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chain), "-map", "[out]", "-t", f"{d:.3f}",
                    "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(out)], check=True)
    return out


def object_wipe(base: Path, s: float, e: float, o: dict, fps: int, work: Path, W: int, H: int, root: Path) -> Path:
    """Masking transition: a foreground object (pillar, wall edge, door frame) crossing the frame in base[s, e] reveals clip B
    behind it. o = {"src": clip B, "in": 0, "box": [x, y, w, h] (the object at time s, fractions), "side": "left" | "right"
    (where B appears relative to the object), "soft": 0.01}. Returns an RGBA .mov of clip B with the moving matte."""
    import cv2
    srcb = Path(o["src"]) if Path(o["src"]).is_absolute() else root / o["src"]
    out = work / "wipe" / f"wipe_{_key(str(base), Path(base).stat().st_mtime_ns, s, e, o, W, H)}.mov"
    if out.exists():
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    side = o.get("side", "right")
    bx, by, bw, bh = [float(v) for v in o["box"]]
    # follow the object's trailing EDGE (strongest vertical edge near where it was): works for plain pillars and walls,
    # where template matching has nothing to hold on to
    w, h = 360, int(360 * H / W)
    fr = _frames(Path(base), s, e, fps, w, h)
    y0, y1 = int(by * h), max(int(by * h) + 4, int((by + bh) * h))
    x = (bx + bw) * w if side == "right" else bx * w
    edges = []
    win = max(6, int(0.12 * w))
    for f in fr:
        gx = np.abs(cv2.Sobel(f[y0:y1].astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)).mean(0)
        lo, hi = int(max(1, x - win)), int(min(w - 2, x + win))
        if hi > lo:
            seg = gx[lo:hi] * np.exp(-((np.arange(lo, hi) - x) ** 2) / (2 * (win * 0.6) ** 2))  # prefer staying close
            x = 0.4 * x + 0.6 * float(lo + int(np.argmax(seg)))
        edges.append(x / w)
    soft = max(2, int(float(o.get("soft", 0.012)) * W))
    xs = np.arange(W, dtype=np.float32)
    d = e - s
    pts = [(ex, 0.5) for ex in edges]
    p = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                          "-ss", f"{float(o.get('in', 0)):.3f}", "-i", str(srcb), "-filter_complex",
                          f"[1:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={fps},trim=duration={d:.3f},setpts=PTS-STARTPTS,format=rgba[b];"
                          f"[0:v]format=gray[m];[b][m]alphamerge[o]", "-map", "[o]", "-t", f"{d:.3f}",
                          "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(out)], stdin=subprocess.PIPE)
    for ex, _cy in pts:
        edge = ex * W
        a = np.clip((xs - edge) / soft + 0.5, 0, 1) if side == "right" else np.clip((edge - xs) / soft + 0.5, 0, 1)
        p.stdin.write(np.tile((a * 255).astype(np.uint8), (H, 1)).tobytes())
    p.stdin.close()
    p.wait()
    return out


def alpha_times_mask(mov: Path, mask: Path, out: Path, invert: bool = False) -> Path:
    """A rendered motion overlay shown only where the matte is white (text behind the buildings = only on the sky)."""
    if out.exists():
        return out
    inv = ",negate" if invert else ""
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(mov), "-i", str(mask), "-filter_complex",
                    f"[0:v]format=rgba,split[c][a0];[a0]alphaextract[a];[1:v]format=gray{inv}[m];[a][m]blend=all_mode=multiply[am];[c][am]alphamerge[o]",
                    "-map", "[o]", "-shortest", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", str(out)], check=True)
    return out


# ------------------------------------------------------------------ KIE.AI (image edit, music)
def kie_key(env: str | None = None) -> str:
    if os.environ.get("KIE_API_KEY"):
        return os.environ["KIE_API_KEY"]
    for f in (env, os.environ.get("MH_ENV_FILE")):
        if f and Path(f).exists():
            for line in Path(f).read_text(encoding="utf-8").splitlines():
                if line.startswith("KIE_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"\'')
    raise SystemExit("KIE_API_KEY not found: set it or MH_ENV_FILE=<path to .env>")


def _kie(url: str, body: dict | None, key: str) -> dict:
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method="POST" if body else "GET",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def _kie_task(model: str, inp: dict, key: str, poll: int = 6, tries: int = 150) -> dict:
    r = _kie("https://api.kie.ai/api/v1/jobs/createTask", {"model": model, "input": inp}, key)
    tid = (r.get("data") or {}).get("taskId")
    if not tid:
        raise RuntimeError(f"KIE createTask failed: {r}")
    for _ in range(tries):
        time.sleep(poll)
        d = _kie(f"https://api.kie.ai/api/v1/jobs/recordInfo?taskId={tid}", None, key)["data"]
        if d.get("state") == "success":
            return d
        if d.get("state") == "fail":
            raise RuntimeError(f"KIE task failed: {d.get('failCode')} {d.get('failMsg')}")
    raise RuntimeError("KIE task timeout")


def _upload(img: Path, key: str) -> str:
    b = base64.b64encode(img.read_bytes()).decode()
    mt = "image/png" if img.suffix.lower() == ".png" else "image/jpeg"
    r = _kie("https://kieai.redpandaai.co/api/file-base64-upload",
             {"base64Data": f"data:{mt};base64,{b}", "uploadPath": "images/vip-pro", "fileName": img.name}, key)
    d = r.get("data") or {}
    u = d.get("downloadUrl") or d.get("fileUrl")
    if not u:
        raise RuntimeError(f"upload failed: {r}")
    return u


NIGHT_PROMPT = ("The exact same photo, same camera angle, same buildings and composition, transformed to blue hour at dusk turning to "
                "night: deep blue sky with a last warm glow on the horizon, warm lights on in the windows, street lights and car light "
                "trails glowing, realistic architectural night photography, no new objects, no text.")


def day_to_night(frame: Path, out: Path, key: str, prompt: str | None = None, model: str = "nano-banana-pro") -> Path:
    if out.exists():
        return out
    from PIL import Image
    w, h = Image.open(frame).size
    ar = "9:16" if h > w else ("16:9" if w > h * 1.2 else "1:1")
    d = _kie_task(model, {"prompt": prompt or NIGHT_PROMPT, "image_input": [_upload(frame, key)], "aspect_ratio": ar,
                          "resolution": "2K", "output_format": "jpg"}, key, poll=5)
    rj = json.loads(d.get("resultJson") or "{}")
    u = (rj.get("resultUrls") or [None])[0]
    import urllib.request
    urllib.request.urlretrieve(u, out)
    align_to(out, frame)
    print(f"[footage] night version -> {out}")
    return out


def align_to(img: Path, ref: Path) -> None:
    """AI edits shift the framing a little; warp img onto ref (features + homography) so a cross-fade does not slide."""
    import cv2
    a, b = cv2.imread(str(img)), cv2.imread(str(ref))
    if a is None or b is None:
        return
    a = cv2.resize(a, (b.shape[1], b.shape[0]))
    ga = cv2.equalizeHist(cv2.cvtColor(a, cv2.COLOR_BGR2GRAY))  # night vs day: compare structure, not brightness
    gb = cv2.equalizeHist(cv2.cvtColor(b, cv2.COLOR_BGR2GRAY))
    orb = cv2.ORB_create(4000)
    ka, da = orb.detectAndCompute(ga, None)
    kb, db = orb.detectAndCompute(gb, None)
    if da is None or db is None:
        cv2.imwrite(str(img), a)
        return
    m = sorted(cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(da, db), key=lambda x: x.distance)[:600]
    if len(m) >= 20:
        Hm, inl = cv2.findHomography(np.float32([ka[x.queryIdx].pt for x in m]), np.float32([kb[x.trainIdx].pt for x in m]), cv2.RANSAC, 4.0)
        if Hm is not None and inl.sum() >= 15:
            a = cv2.warpPerspective(a, Hm, (b.shape[1], b.shape[0]), borderMode=cv2.BORDER_REFLECT)
    cv2.imwrite(str(img), a, [cv2.IMWRITE_JPEG_QUALITY, 92])


def suno(style: str, duration: float, out: Path, key: str, title: str = "Estate", negative: str = "vocals, singing, voice, choir") -> Path:
    if out.exists():
        return out
    d = _kie_task("ai-music-api/generate", {"custom_mode": True, "instrumental": True, "model": "V6", "style": style, "title": title,
                                           "negative_tags": negative, "duration": duration}, key)
    rj = json.loads(d.get("resultJson") or "{}")
    urls = rj.get("resultUrls") or [t.get("audio_url") for t in ((d.get("response") or {}).get("data") or rj.get("data") or []) if t.get("audio_url")]
    import urllib.request
    urllib.request.urlretrieve(urls[0], out)
    if len(urls) > 1:
        urllib.request.urlretrieve(urls[1], out.with_name(out.stem + "_b" + out.suffix))
    print(f"[footage] music -> {out}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("track")
    t.add_argument("clip"); t.add_argument("--t0", type=float, default=0); t.add_argument("--t1", type=float, required=True)
    t.add_argument("--corners", required=True, help='"x,y x,y x,y x,y" fractions'); t.add_argument("-o", "--out", default="track.json")
    t.add_argument("--size", default="1080x1920")
    k = sub.add_parser("sky")
    k.add_argument("clip"); k.add_argument("--t0", type=float, default=0); k.add_argument("--t1", type=float, required=True)
    k.add_argument("-o", "--out", default="sky_mask.mp4"); k.add_argument("--size", default="1080x1920")
    n = sub.add_parser("night")
    n.add_argument("frame"); n.add_argument("-o", "--out", default="night.jpg"); n.add_argument("--env")
    m = sub.add_parser("suno")
    m.add_argument("--style", required=True); m.add_argument("--duration", type=float, default=40); m.add_argument("--title", default="Estate")
    m.add_argument("-o", "--out", default="music.mp3"); m.add_argument("--env")
    a = ap.parse_args()
    work = Path(".footage_cache")
    if a.cmd in ("track", "sky"):
        W, H = map(int, a.size.split("x"))
        if a.cmd == "track":
            cs = [[float(v) for v in p.split(",")] for p in a.corners.split()]
            Path(a.out).write_text(json.dumps(track_plane(Path(a.clip), a.t0, a.t1, {"corners": cs}, 30, work, W, H)))
        else:
            p = sky_masks(Path(a.clip), a.t0, a.t1, 30, work, W, H)
            Path(a.out).write_bytes(p.read_bytes())
        print(a.out)
    elif a.cmd == "night":
        print(day_to_night(Path(a.frame), Path(a.out), kie_key(a.env)))
    else:
        print(suno(a.style, a.duration, Path(a.out), kie_key(a.env), a.title))


if __name__ == "__main__":
    main()
