"""Shared helpers for the video-vip-pro skill: ffmpeg/ffprobe wrappers, fonts, colors, CUDA setup."""
from __future__ import annotations

import functools
import glob
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"

FONT_DIRS = [
    Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
    Path(__file__).resolve().parent.parent / "assets" / "fonts",
]

# Fonts tried in order when a style does not name one. All support Vietnamese.
DEFAULT_FONTS = ["Be Vietnam Pro Bold", "SVN-Nexa Bold", "Arial Bold", "Segoe UI Bold", "Tahoma Bold"]


# ---------------------------------------------------------------- process

def run(cmd: list[str], cwd: str | Path | None = None, quiet: bool = True) -> subprocess.CompletedProcess:
    """Run a command; raise with the stderr tail on failure so errors are readable."""
    if quiet and cmd and Path(cmd[0]).stem.lower() in ("ffmpeg",):
        cmd = [cmd[0], "-hide_banner", "-loglevel", "error", "-stats"] + cmd[1:]
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.returncode != 0:
        tail = "\n".join((p.stderr or "").strip().splitlines()[-25:])
        raise RuntimeError(f"Command failed ({p.returncode}): {' '.join(map(str, cmd[:6]))} ...\n{tail}")
    return p


def probe(path: str | Path) -> dict:
    p = run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)])
    data = json.loads(p.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    info = {
        "path": str(path),
        "duration": float(data["format"].get("duration", 0) or 0),
        "size_mb": round(int(data["format"].get("size", 0)) / 1e6, 1),
        "has_audio": a is not None,
        "has_video": v is not None,
    }
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        rot = rot or int((v.get("tags") or {}).get("rotate", 0) or 0)
        if abs(rot) % 180 == 90:
            w, h = h, w
        num, den = (v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1").split("/")
        fps = float(num) / float(den) if float(den) else 30.0
        info.update(width=w, height=h, fps=round(fps, 3), vcodec=v.get("codec_name"),
                    color_transfer=v.get("color_transfer"), pix_fmt=v.get("pix_fmt"))
        info["is_hdr"] = v.get("color_transfer") in ("arib-std-b67", "smpte2084")
        # Still images report a tiny duration; flag them.
        info["is_image"] = v.get("codec_name") in ("png", "mjpeg", "webp", "bmp", "tiff") and info["duration"] < 1
    if a:
        info.update(acodec=a.get("codec_name"), sample_rate=int(a.get("sample_rate", 0)), channels=a.get("channels"))
    return info


def has_nvenc() -> bool:
    try:
        p = subprocess.run([FFMPEG, "-hide_banner", "-f", "lavfi", "-i", "color=s=256x256:d=0.1", "-c:v", "h264_nvenc",
                            "-f", "null", "-"], capture_output=True, text=True)
        return p.returncode == 0
    except Exception:
        return False


def video_codec_args(quality: str = "high", nvenc: bool | None = None) -> list[str]:
    """H.264 args. quality: draft | high | max."""
    if nvenc is None:
        nvenc = has_nvenc()
    cq = {"draft": 28, "high": 19, "max": 16}[quality]
    if nvenc:
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", str(cq), "-b:v", "0",
                "-profile:v", "high", "-pix_fmt", "yuv420p"]
    preset = {"draft": "veryfast", "high": "medium", "max": "slow"}[quality]
    return ["-c:v", "libx264", "-preset", preset, "-crf", str(cq - 1), "-pix_fmt", "yuv420p"]


# ---------------------------------------------------------------- fonts

_font_cache: dict[str, Path] | None = None


def _font_index() -> dict[str, Path]:
    """Map lowercase full-name / family(+style) -> file."""
    global _font_cache
    if _font_cache is not None:
        return _font_cache
    idx: dict[str, Path] = {}
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        TTFont = None
    for d in FONT_DIRS:
        if not d.exists():
            continue
        for f in list(d.glob("*.ttf")) + list(d.glob("*.otf")) + list(d.glob("*.TTF")) + list(d.glob("*.OTF")):
            idx.setdefault(f.stem.lower(), f)
            if TTFont is None:
                continue
            try:
                n = TTFont(f, lazy=True, fontNumber=0)["name"]
                fam, sub, full = n.getDebugName(1), n.getDebugName(2), n.getDebugName(4)
                for key in (full, fam if sub in (None, "Regular") else None, f"{fam} {sub}" if fam and sub else None):
                    if key:
                        idx.setdefault(key.lower(), f)
            except Exception:
                pass
    _font_cache = idx
    return idx


def find_font(name: str | None) -> tuple[str, Path | None]:
    """Return (ass_family_name, file). Falls back through DEFAULT_FONTS."""
    idx = _font_index()
    for cand in ([name] if name else []) + DEFAULT_FONTS:
        f = idx.get(cand.lower())
        if f:
            fam = cand
            try:
                from fontTools.ttLib import TTFont
                fam = TTFont(f, lazy=True)["name"].getDebugName(1) or cand
            except Exception:
                pass
            return fam, f
    return name or "Arial", None


def font_is_bold_variant(file: Path | None) -> bool:
    try:
        from fontTools.ttLib import TTFont
        sub = TTFont(file, lazy=True)["name"].getDebugName(2) or ""
        return "bold" in sub.lower()
    except Exception:
        return False


@functools.lru_cache(maxsize=64)
def font_scale(file: Path | None) -> float:
    """libass sizes by ascent+descent, so fonts with tall line metrics look small.
    Return a factor that makes capitals as tall as Arial's at the same nominal size."""
    if not file:
        return 1.0
    try:
        from fontTools.ttLib import TTFont
        o = TTFont(file, lazy=True)["OS/2"]
        cap = getattr(o, "sCapHeight", 0) or 0
        if not cap:
            return 1.0
        ratio = cap / (o.usWinAscent + o.usWinDescent)
        return max(0.8, min(1.4, 0.641 / ratio))
    except Exception:
        return 1.0


def list_fonts() -> list[str]:
    return sorted({k for k in _font_index().keys() if " " in k or "-" in k})


# ---------------------------------------------------------------- colors

NAMED = {
    "white": "#FFFFFF", "black": "#000000", "red": "#E53935", "yellow": "#FFD600", "orange": "#FF8A00",
    "green": "#22C55E", "blue": "#2563EB", "gold": "#F5C542", "pink": "#FF4D8D", "purple": "#7C3AED",
    "gray": "#9CA3AF", "navy": "#0B1F4B", "cyan": "#06B6D4",
}


def ass_color(c: str | None, alpha: float = 1.0) -> str:
    """'#RRGGBB' / named / '#RRGGBBAA' -> ASS '&HAABBGGRR'. alpha 1 = opaque."""
    c = NAMED.get((c or "white").lower(), c or "#FFFFFF").lstrip("#")
    if len(c) == 8:
        alpha = int(c[6:8], 16) / 255
        c = c[:6]
    r, g, b = c[0:2], c[2:4], c[4:6]
    a = int(round((1 - alpha) * 255))
    return f"&H{a:02X}{b}{g}{r}".upper()


def ass_inline_color(c: str) -> str:
    """Inline override form '&HBBGGRR&'."""
    full = ass_color(c)
    return "&H" + full[4:] + "&"


# ---------------------------------------------------------------- misc

def ts(sec: float) -> str:
    """ASS timestamp h:mm:ss.cc"""
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int(sec % 3600 // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def srt_ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_time(t) -> float:
    """Accept 12.5, '12.5', '1:02.3', '00:01:02.3'."""
    if t is None:
        return 0.0
    if isinstance(t, (int, float)):
        return float(t)
    parts = str(t).strip().split(":")
    total = 0.0
    for p in parts:
        total = total * 60 + float(p)
    return total


def setup_cuda_dlls() -> None:
    """On Windows, make pip-installed nvidia cublas/cudnn DLLs visible to ctranslate2."""
    if os.name != "nt":
        return
    for site in sys.path:
        for sub in ("nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_runtime/bin"):
            d = Path(site) / sub
            if d.is_dir():
                try:
                    os.add_dll_directory(str(d))
                except OSError:
                    pass
                os.environ["PATH"] = str(d) + os.pathsep + os.environ.get("PATH", "")


def load_json(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_json(obj, path: str | Path) -> None:
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
