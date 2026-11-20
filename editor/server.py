"""VIP Editor — sửa tay video sau khi skill video-vip-pro dựng xong, không tốn token.

    python editor/server.py <plan.json> [--port 8790] [--no-open]

Mở trình duyệt tại http://127.0.0.1:<port>. Xem trước = <plan>_work/base.mp4 (video đã ghép, chưa chữ)
+ ảnh/video chèn vẽ bằng HTML + chữ/phụ đề vẽ bằng libass (JASSUB) từ đúng file .ass mà render.py tạo,
nên chữ trong editor giống hệt bản xuất. Bấm Xuất là gọi render.py như bình thường.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import assgen  # noqa: E402
import render  # noqa: E402
from common import list_fonts, load_json, parse_time, probe, save_json  # noqa: E402

MEDIA_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac",
             ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".ttf", ".otf", ".ttc", ".woff", ".woff2"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

S: dict = {}          # server state
JOB: dict = {"running": False}
LOCK = threading.Lock()


# ------------------------------------------------------------------ helpers

def absify(p: str | None) -> str | None:
    if not p:
        return p
    q = Path(p)
    return str(q if q.is_absolute() else (S["root"] / q).resolve())


def abs_plan(plan: dict) -> dict:
    """Deep copy with absolute paths + clip_defaults merged (what render.py works on)."""
    p = copy.deepcopy(plan)
    p["clips"] = [{**p.get("clip_defaults", {}), **c} for c in p.get("clips", [])]
    for c in p["clips"]:
        c["src"] = absify(c["src"])
    for o in p.get("overlays", []):
        if o.get("src"):
            o["src"] = absify(o["src"])
    au = p.get("audio") or {}
    for k in ("music", "voiceover"):
        v = au.get(k)
        for item in (v if isinstance(v, list) else [v]):
            if item and item.get("src"):
                item["src"] = absify(item["src"])
    sub = p.get("subtitles") or {}
    tr = sub.get("transcript")
    if tr:
        sub["transcript"] = [absify(t) for t in tr] if isinstance(tr, list) else absify(tr)
    p["_root"] = str(S["root"])
    return p


def canvas_of(plan: dict) -> dict:
    cv = dict(plan.get("canvas", {}))
    if cv.get("aspect"):
        cv["width"], cv["height"] = render.ASPECTS.get(cv["aspect"], (cv.get("width", 1080), cv.get("height", 1920)))
    if "width" not in cv:
        first = probe(absify(plan["clips"][0]["src"]))
        cv["width"], cv["height"] = first["width"] // 2 * 2, first["height"] // 2 * 2
    cv.setdefault("fps", 30)
    return cv


_probe_cache: dict = {}


def dur_of(src: str) -> float:
    k = (src, os.path.getmtime(src) if os.path.exists(src) else 0)
    if k not in _probe_cache:
        try:
            _probe_cache[k] = probe(src)
        except Exception:
            _probe_cache[k] = {"duration": 0, "width": 0, "height": 0}
    return _probe_cache[k]


def clips_sig(ap: dict) -> str:
    keys = ("src", "in", "out", "speed", "duration", "transition", "fit", "focus", "zoom", "zoom_amount", "zooms",
            "punch", "shake", "flip", "color", "grade", "beauty", "volume", "mute", "denoise", "voice")
    cv = canvas_of(ap)
    data = [{k: c.get(k) for k in keys} for c in ap["clips"]] + [[cv["width"], cv["height"], cv["fps"]]]
    return hashlib.md5(json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:12]


def estimate_timeline(ap: dict) -> tuple[list[dict], list[float], float]:
    """Clip durations/starts without rendering (used when base.mp4 is stale or missing)."""
    clips = ap["clips"]
    for c in clips:
        info = dur_of(c["src"])
        is_img = info.get("is_image") or Path(c["src"]).suffix.lower() in IMG_EXT
        sp = float(c.get("speed", 1))
        if is_img:
            d = parse_time(c.get("duration", 3))
            c["_out"], c["_dur"] = d, d
        else:
            cin = parse_time(c.get("in", 0))
            cout = parse_time(c["out"]) if c.get("out") is not None else info.get("duration", 0)
            cout = min(cout, info.get("duration", cout) or cout)
            c["_out"], c["_dur"] = cout, max(0.04, (cout - cin) / sp)
    starts, cur = [], 0.0
    for i, c in enumerate(clips):
        t = c.get("transition") if i else None
        if isinstance(t, str):
            t = {"type": t}
        if t and t.get("type", "cut") != "cut":
            cur -= min(float(t.get("duration", 0.4)), clips[i - 1]["_dur"] / 2, c["_dur"] / 2)
        starts.append(cur)
        cur += c["_dur"]
    return clips, starts, cur


def timeline_for(ap: dict) -> dict:
    """Clips with _dur/_out + starts/total. Uses timeline.json from the last render when it matches."""
    tl_path = S["work"] / "timeline.json"
    base = S["work"] / "base.mp4"
    sig = clips_sig(ap)
    built_sig = None
    sig_file = S["ed"] / "base_sig.json"
    if sig_file.exists():
        built_sig = load_json(sig_file).get("sig")
    fresh = False
    if tl_path.exists() and base.exists():
        tl = load_json(tl_path)
        same_len = len(tl.get("clips", [])) == len(ap["clips"])
        if same_len and (built_sig == sig or (built_sig is None and all(
                str(Path(a["src"])).lower() == str(Path(b["src"])).lower() and abs(float(a["in"]) - parse_time(b.get("in", 0))) < 1e-3
                for a, b in zip(tl["clips"], ap["clips"])))):
            fresh = True
            if built_sig is None:
                save_json({"sig": sig}, sig_file)
            for c, tc in zip(ap["clips"], tl["clips"]):
                c["_dur"], c["_out"] = tc["_dur"], tc["_out"]
            return {"clips": ap["clips"], "starts": tl["starts"], "total": tl["total"], "fresh": True,
                    "base": str(base), "base_v": int(base.stat().st_mtime)}
    clips, starts, total = estimate_timeline(ap)
    if base.exists() and not tl_path.exists():
        # plan rendered before render.py wrote timeline.json: trust base.mp4 if the signature or length matches
        if built_sig == sig:
            fresh = True
        elif built_sig is None:
            try:
                fresh = abs(render.video_duration(base) - total) < 0.15
            except Exception:
                fresh = False
            if fresh:
                save_json({"sig": sig}, sig_file)
    return {"clips": clips, "starts": starts, "total": total, "fresh": fresh,
            "base": str(base) if base.exists() else None, "base_v": int(base.stat().st_mtime) if base.exists() else 0}


def subtitle_words(ap: dict, clips: list[dict], starts: list[float]) -> list[dict]:
    """Same word gathering as assgen.build_ass, keeping which transcript/segment each word came from."""
    sub = ap.get("subtitles") or {}
    if not sub.get("transcript"):
        return []
    paths = sub["transcript"] if isinstance(sub["transcript"], list) else [sub["transcript"]]
    vos = (ap.get("audio") or {}).get("voiceover") or []
    vos = vos if isinstance(vos, list) else [vos]

    def same(a, b):
        return bool(a) and bool(b) and str(Path(a).resolve()).lower() == str(Path(b).resolve()).lower()

    words = []
    for ti, tp in enumerate(paths):
        if not tp or not Path(tp).exists():
            continue
        tr = load_json(tp)
        mode = sub.get("timing", "auto")
        src = tr.get("source", "")
        if mode == "clips" or (mode == "auto" and any(same(c["src"], src) for c in clips)):
            ws = assgen.timeline_words(tr, clips, starts)
        else:
            ws = assgen.timeline_words(tr, None, starts)
            shift = parse_time(sub.get("offset", 0))
            vo = next((v for v in vos if same(v["src"], src)), None)
            if vo:
                vin = parse_time(vo.get("in", 0))
                vout = parse_time(vo["out"]) if vo.get("out") is not None else 1e9
                ws = [w for w in ws if min(w["end"], vout) - max(w["start"], vin) > min(0.06, (w["end"] - w["start"]) * 0.5)]
                shift += parse_time(vo.get("start", 0)) - vin + (starts[int(vo["clip"])] if "clip" in vo else 0)
            ws = [{**w, "start": w["start"] + shift, "end": w["end"] + shift} for w in ws]
        words += [{**w, "ti": ti, "path": tp} for w in ws]
    words.sort(key=lambda w: w["start"])
    hide = [assgen._times(o, starts) for o in ap.get("overlays", []) if o.get("type") == "frost" and o.get("hide_subs", True)]
    if hide:
        words = [w for w in words if not any(a - 0.05 <= w["start"] < b for a, b in hide)]
    return words


MOTION_Q: "queue.Queue" = None  # type: ignore
MOTION_BUSY: set = set()
MOTION_ERR: dict = {}
MOTION_LATEST: dict = {}  # overlay index -> newest wanted file (older queued versions are skipped, e.g. while dragging)


def _motion_mod():
    sys.path.insert(0, str(HERE.parent / "motion"))
    import render_motion  # noqa: E402
    return render_motion


def _motion_worker():
    rm = _motion_mod()
    while True:
        args = MOTION_Q.get()
        key = str(args["path"])
        try:
            if MOTION_LATEST.get(args["idx"]) != key:
                continue
            if not Path(key).exists():
                rm.render(args["comp"], args["props"], args["dur"], args["w"], args["h"], args["fps"],
                          cache_dir=S["work"] / "motion", root=S["root"])
            MOTION_ERR.pop(args["idx"], None)
        except Exception as e:  # shown in the editor
            MOTION_ERR[args["idx"]] = str(e)[-600:]
        finally:
            MOTION_BUSY.discard(key)


def web_proxy(mov: Path) -> Path | None:
    """Browsers can't play ProRes 4444: make a small VP9-with-alpha WebM next to it for the preview (~0.5 s)."""
    webm = mov.with_suffix(".webm")
    if not webm.exists() or webm.stat().st_mtime < mov.stat().st_mtime:
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(mov), "-vf", "scale=540:-2", "-c:v", "libvpx-vp9",
                            "-pix_fmt", "yuva420p", "-crf", "36", "-b:v", "0", "-deadline", "realtime", "-cpu-used", "8",
                            "-row-mt", "1", "-an", str(webm)], capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0 or not webm.exists():
            return None
    return webm


def motion_paths(ap: dict, starts: list[float], total: float, cv: dict) -> tuple[dict, int]:
    """Cached .mov of every "motion" overlay; missing ones are queued for a background render."""
    global MOTION_Q
    import theme
    ap = theme.apply(ap)  # brand colour -> props.theme of every motion item
    items = [(i, o) for i, o in enumerate(ap.get("overlays", [])) if o.get("type") == "motion"]
    if not items:
        return {}, 0
    rm = _motion_mod()
    if MOTION_Q is None:
        import queue
        MOTION_Q = queue.Queue()
        threading.Thread(target=_motion_worker, daemon=True).start()
    out, pending = {}, 0
    for i, o in items:
        s, e = render.overlay_times(o, starts, total)
        dur = max(0.2, e - s)
        try:  # "frame:12.3" props -> stills of base.mp4
            o = {**o, "props": render.resolve_stills(o.get("props", {}), S["work"], cv["width"])}
        except Exception:
            pass
        try:
            p, _ = rm.target_path(o.get("comp", ""), o.get("props", {}), dur, cv["width"], cv["height"], int(cv.get("fps", 30)),
                                  cache_dir=S["work"] / "motion", root=S["root"])
        except Exception as ex:
            MOTION_ERR[i] = str(ex)
            continue
        MOTION_LATEST[i] = str(p)
        if p.exists():
            w = web_proxy(p)
            if w:
                out[i] = str(w)
        else:
            pending += 1
            if str(p) not in MOTION_BUSY:
                MOTION_BUSY.add(str(p))
                MOTION_Q.put({"idx": i, "path": p, "comp": o["comp"], "props": o.get("props", {}), "dur": dur,
                              "w": cv["width"], "h": cv["height"], "fps": int(cv.get("fps", 30))})
    return out, pending


def build_preview(plan: dict) -> dict:
    ap = abs_plan(plan)
    cv = canvas_of(ap)
    tl = timeline_for(ap)
    clips, starts, total = tl["clips"], tl["starts"], tl["total"]
    ed = S["ed"]
    ass_text = ""
    try:
        path = assgen.build_ass(ap, cv["width"], cv["height"], clips, starts, total, ed)
        if path:
            ass_text = Path(path).read_text(encoding="utf-8-sig")
            path.unlink(missing_ok=True)
    except Exception as e:  # keep the editor alive on a bad value; show the error
        ass_text = ""
        tl["ass_error"] = f"{type(e).__name__}: {e}"
    fonts = sorted(f.name for f in (ed / "fonts").glob("*") if f.suffix.lower() in {".ttf", ".otf", ".ttc"})

    # subtitle segments (for editing the transcript text) + lines (timeline blocks)
    words = subtitle_words(ap, clips, starts)
    segs: dict = {}
    for w in words:
        key = (w["ti"], w.get("seg"))
        s = segs.setdefault(key, {"ti": w["ti"], "seg": w.get("seg"), "path": w["path"], "start": w["start"],
                                  "end": w["end"]})
        s["start"], s["end"] = min(s["start"], w["start"]), max(s["end"], w["end"])
    tr_cache: dict = {}
    seg_list = []
    for s in sorted(segs.values(), key=lambda x: x["start"]):
        tr = tr_cache.setdefault(s["path"], load_json(s["path"]))
        try:
            s["text"] = tr["segments"][s["seg"]]["text"].strip()
        except Exception:
            s["text"] = ""
        s["rel"] = os.path.relpath(s["path"], S["root"]) if Path(s["path"]).drive == S["root"].drive else s["path"]
        seg_list.append(s)
    sub = ap.get("subtitles") or {}
    portrait = cv["height"] > cv["width"]
    lines = []
    if words:
        grouped = assgen.group_lines([{**w, "seg": (w["ti"], w.get("seg"))} for w in words],
                                     sub.get("words_per_line", 4 if portrait else 7),
                                     sub.get("max_chars", 24 if portrait else 42))
        for i, ln in enumerate(grouped):
            st = ln[0]["start"]
            nxt = grouped[i + 1][0]["start"] if i + 1 < len(grouped) else total
            lines.append({"start": st, "end": min(max(ln[-1]["end"] + 0.15, st + 0.5), nxt),
                          "text": " ".join(w["word"] for w in ln), "ti": ln[0]["ti"], "seg": ln[0]["seg"][1]})

    # sound effects on the timeline (explicit + auto), for preview playback
    sfx = []
    try:
        for f, at, vol, mx in render.sfx_events(ap, starts, total):
            sfx.append({"src": str(f), "at": at, "vol": vol, "len": mx})
    except Exception:
        pass

    # natural sizes of image/video overlays (to draw them at the right height)
    sizes = {}
    for o in ap.get("overlays", []):
        if o.get("type") in ("image", "video") and o.get("src") and os.path.exists(o["src"]):
            info = dur_of(o["src"])
            sizes[o["src"]] = [info.get("width") or 0, info.get("height") or 0, info.get("duration") or 0]

    clip_info = [{"name": Path(c["src"]).name, "start": st, "dur": c["_dur"], "in": parse_time(c.get("in", 0)),
                  "speed": float(c.get("speed", 1)), "src": c["src"]} for c, st in zip(clips, starts)]
    try:
        mpaths, mpending = motion_paths(ap, starts, total, cv)
    except Exception as e:
        mpaths, mpending = {}, 0
        MOTION_ERR[-1] = str(e)
    return {"motion": mpaths, "motion_pending": mpending, "motion_err": dict(MOTION_ERR),
            "ass": ass_text, "fonts": fonts, "canvas": cv, "starts": starts, "total": total, "clips": clip_info,
            "fresh": tl["fresh"], "base_v": tl["base_v"], "has_base": bool(tl["base"]), "segments": seg_list,
            "lines": lines, "sfx": sfx, "sizes": sizes, "ass_error": tl.get("ass_error"),
            "abs": {"overlays": [o.get("src") for o in ap.get("overlays", [])]}}


def save_like(obj, path: Path) -> None:
    """Write JSON keeping the file's existing indentation (builders write indent=1, save_json indent=2)."""
    indent = 2
    if path.exists():
        m = re.match(r"\{\r?\n( +)\"", path.read_text(encoding="utf-8-sig")[:200])
        indent = len(m.group(1)) if m else 2
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")


def sfx_library() -> list[str]:
    names = sorted({f.stem for f in render.SFX_DIR.glob("*") if f.suffix.lower() in {".wav", ".mp3"}})
    local = []
    for d in ("sfx_kho", "sfx"):
        p = S["root"] / d
        if p.is_dir():
            local += [f"{d}/{f.name}" for f in sorted(p.iterdir()) if f.suffix.lower() in {".wav", ".mp3"}]
    return local + names


def history_list() -> list[dict]:
    h = S["ed"] / "history"
    out = []
    for f in sorted(h.glob("plan_*.json"), reverse=True)[:60]:
        out.append({"name": f.name, "time": f.stat().st_mtime, "size": f.stat().st_size})
    return out


def backup_plan() -> None:
    h = S["ed"] / "history"
    h.mkdir(parents=True, exist_ok=True)
    if S["plan_path"].exists():
        shutil.copy2(S["plan_path"], h / f"plan_{time.strftime('%Y%m%d_%H%M%S')}.json")


# ------------------------------------------------------------------ render jobs

def start_job(mode: str, rng: str | None = None) -> dict:
    with LOCK:
        if JOB.get("running"):
            return {"ok": False, "error": "Đang có lệnh xuất chạy, đợi xong đã."}
        cmd = [sys.executable, "-X", "utf8", str(SCRIPTS / "render.py"), str(S["plan_path"])]
        if mode == "base":
            cmd.append("--base-only")
        elif mode == "draft":
            cmd.append("--draft")
        elif mode == "preview" and rng:
            cmd += ["--draft", "--preview", rng]
        log = S["ed"] / "job.log"
        JOB.clear()
        JOB.update({"running": True, "mode": mode, "start": time.time(), "log": "", "out": None, "code": None})

    def run():
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        sig = clips_sig(abs_plan(load_json(S["plan_path"])))
        with open(log, "w", encoding="utf-8") as fh:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(S["root"]), env=env,
                                 text=True, encoding="utf-8", errors="replace",
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            JOB["pid"] = p.pid
            for line in p.stdout:
                fh.write(line)
                fh.flush()
                JOB["log"] = (JOB["log"] + line)[-6000:]
                m = re.search(r"done -> (.+?)\s+\(", line)
                if m:
                    JOB["out"] = m.group(1).strip()
            p.wait()
        JOB["code"] = p.returncode
        if p.returncode == 0:
            save_json({"sig": sig}, S["ed"] / "base_sig.json")
        JOB["running"] = False
        JOB["end"] = time.time()

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


# ------------------------------------------------------------------ http

class H(BaseHTTPRequestHandler):
    server_version = "MHEditor/1.0"

    def log_message(self, fmt, *args):  # quiet
        pass

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _file(self, path: Path, cache=False):
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        size = path.stat().st_size
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".wasm":
            ctype = "application/wasm"
        if path.suffix in (".js", ".mjs"):
            ctype = "text/javascript; charset=utf-8"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                else:
                    start = max(0, size - int(m.group(2)))
            end = min(end, size - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "max-age=3600" if cache else "no-cache")
        self.end_headers()
        try:
            with open(path, "rb") as fh:
                fh.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = fh.read(min(1 << 20, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    # ---------------- GET
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            # stamp app.js / style.css with their mtime so an updated editor is never served from cache
            html = (HERE / "index.html").read_text(encoding="utf-8")
            html = re.sub(r"/static/(app\.js|style\.css)(\?v=\w+)?",
                          lambda m: f"/static/{m.group(1)}?v={int((HERE / m.group(1)).stat().st_mtime)}", html)
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        if u.path.startswith("/static/"):
            p = (HERE / u.path[len("/static/"):]).resolve()
            if HERE in p.parents:
                return self._file(p, cache="vendor" in p.parts)
            return self.send_error(403)
        if u.path == "/media":
            src = q.get("src", [""])[0]
            p = Path(absify(src)) if src else None
            if src and not p.exists():
                r = render.resolve_sfx(src, S["root"])
                p = r if r else p
            if not p or p.suffix.lower() not in MEDIA_EXT:
                return self.send_error(403)
            return self._file(p)
        if u.path == "/base.mp4":
            return self._file(S["work"] / "base.mp4")
        if u.path.startswith("/fonts/"):
            p = (S["ed"] / "fonts" / urllib.parse.unquote(u.path[len("/fonts/"):])).resolve()
            return self._file(p, cache=True)
        if u.path == "/api/state":
            plan = load_json(S["plan_path"])
            draft = S["ed"] / "draft.json"
            has_draft = draft.exists() and draft.stat().st_mtime > S["plan_path"].stat().st_mtime + 1
            return self._json({"plan": plan, "planPath": str(S["plan_path"]), "planName": S["plan_path"].name,
                               "root": str(S["root"]), "fonts": S["fonts"], "sfxLib": sfx_library(),
                               "history": history_list(), "draft": load_json(draft) if has_draft else None,
                               "job": {k: v for k, v in JOB.items() if k != "pid"}})
        if u.path == "/api/job":
            return self._json({k: v for k, v in JOB.items() if k != "pid"})
        if u.path == "/api/history":
            return self._json(history_list())
        if u.path == "/api/history/get":
            name = Path(q.get("name", [""])[0]).name
            return self._json(load_json(S["ed"] / "history" / name))
        self.send_error(404)

    # ---------------- POST
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        try:
            if u.path == "/api/preview":
                plan = json.loads(self._body())
                return self._json(build_preview(plan))
            if u.path == "/api/draft":
                body = self._body().decode("utf-8").strip()
                if body:
                    (S["ed"] / "draft.json").write_text(body, encoding="utf-8")
                else:  # back to the saved state: drop the stale draft
                    (S["ed"] / "draft.json").unlink(missing_ok=True)
                return self._json({"ok": True})
            if u.path == "/api/save":
                plan = json.loads(self._body())
                backup_plan()
                save_like(plan, S["plan_path"])
                (S["ed"] / "draft.json").unlink(missing_ok=True)
                return self._json({"ok": True, "history": history_list()})
            if u.path == "/api/transcript":
                d = json.loads(self._body())
                tp = Path(d["path"])
                tr = load_json(tp)
                bk = S["ed"] / "history" / f"{tp.stem}.orig.json"
                bk.parent.mkdir(parents=True, exist_ok=True)
                if not bk.exists():
                    shutil.copy2(tp, bk)
                seg = tr["segments"][int(d["seg"])]
                lead = " " if str(seg.get("text", "")).startswith(" ") else ""  # keep the file's own convention
                seg["text"] = lead + d["text"].strip()
                save_like(tr, tp)
                return self._json({"ok": True})
            if u.path == "/api/render":
                d = json.loads(self._body() or b"{}")
                return self._json(start_job(d.get("mode", "draft"), d.get("range")))
            if u.path == "/api/stop":
                if JOB.get("running") and JOB.get("pid"):
                    subprocess.run(["taskkill", "/PID", str(JOB["pid"]), "/T", "/F"], capture_output=True)
                return self._json({"ok": True})
            if u.path == "/api/upload":
                name = re.sub(r"[^\w.\-]+", "_", Path(q.get("name", ["file"])[0]).name, flags=re.UNICODE)
                dst_dir = S["root"] / "editor_assets"
                dst_dir.mkdir(exist_ok=True)
                dst = dst_dir / name
                dst.write_bytes(self._body())
                return self._json({"ok": True, "src": f"editor_assets/{name}"})
            if u.path == "/api/open":
                d = json.loads(self._body() or b"{}")
                p = Path(absify(d.get("path")) or S["root"])
                if p.is_file():
                    subprocess.Popen(["explorer", "/select,", str(p)])
                else:
                    os.startfile(str(p if p.exists() else S["root"]))
                return self._json({"ok": True})
        except Exception as e:
            return self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)
        self.send_error(404)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--no-open", action="store_true")
    ap.add_argument("--work", help="work dir (default: <plan>_work, same as render.py)")
    a = ap.parse_args()
    pp = Path(a.plan).resolve()
    S["plan_path"] = pp
    S["root"] = pp.parent
    S["work"] = Path(a.work).resolve() if a.work else pp.with_name(pp.stem + "_work")
    S["ed"] = S["work"] / "editor"
    S["ed"].mkdir(parents=True, exist_ok=True)
    try:
        S["fonts"] = list_fonts()
    except Exception:
        S["fonts"] = []
    port = a.port
    for _ in range(20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), H)
            break
        except OSError:
            port += 1
    url = f"http://127.0.0.1:{port}/"
    print(f"[VIP Editor] {pp.name} -> {url}", flush=True)
    if not (S["work"] / "base.mp4").exists():
        print("[VIP Editor] chưa có base.mp4 -> dựng nền (render.py --base-only)...", flush=True)
        start_job("base")
    if not a.no_open:
        webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
