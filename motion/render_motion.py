"""Render a Blue-pack motion graphic (Remotion) to a transparent ProRes 4444 .mov, cached by content.

    python motion/render_motion.py BlueText '{"top":"muốn sửa đâu lại","text":"gõ _lệnh ở đó_"}' --duration 3 -o out.mov
    python motion/render_motion.py BlueText props.json --duration 3 --still 1.2 -o check.png   # one frame, fast

render.py calls render(...) for every overlay of type "motion" in a plan.
Image paths in props (icons, screenshots, avatars) may be absolute or relative to `root`; they are copied
into motion/public/_in/ so Remotion can load them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Packaged apps ship a prebuilt bundle instead of src/ + webpack: MH_MOTION_RT = folder with bundle/, render.mjs and
# node_modules (@remotion/renderer + headless Chrome), MH_NODE = node.exe, MH_MOTION_CACHE = a writable folder.
RT = Path(os.environ["MH_MOTION_RT"]) if os.environ.get("MH_MOTION_RT") else None
NODE = os.environ.get("MH_NODE") or shutil.which("node") or "node"
CACHE_ROOT = Path(os.environ["MH_MOTION_CACHE"]) if os.environ.get("MH_MOTION_CACHE") else HERE
PUBLIC_IN = HERE / "public" / "_in"
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif"}
COMPS = {"BlueText", "BlueBig", "Tiles", "Checklist", "ScreenCard", "NumberTitle", "FollowCard",
         # Blue VIP (src/blue/Vip.tsx)
         "Stamp", "KineticTitle", "GravityText", "GiantCaption", "SplitFlap", "Highlighter", "CircleDraw", "Cursor",
         "FloatButton", "IncomingCall", "TypeBar", "FileDrop", "FocusBrackets", "ChapterPanel", "NotifyStack",
         "ChatBubbles", "CommentsDrop", "BarChart", "EditTimeline", "JiggleChips", "Eyedropper", "CompareHandle",
         "VhsHud", "NumberList", "VsCards", "Callouts", "CountUp", "IconSlam", "OrbitIcons", "ScanLines", "CardStack",
         "Polaroids", "PostWall", "Newspaper", "TearAway", "BlowAway", "InkSpread", "TitleCard", "Intertitle",
         "ScriptPage", "CodeLayer", "OrbitRing", "Portal", "Shockwave", "Cracks", "PhoneFrame", "VideoCard"}


def _src_version() -> str:
    if RT:
        v = RT / "bundle" / "VERSION"
        return v.read_text().strip() if v.exists() else "rt"
    files = sorted(p for p in (HERE / "src").rglob("*.ts*"))
    return hashlib.md5("".join(f"{p.name}{p.stat().st_mtime_ns}" for p in files).encode()).hexdigest()[:8]


def _stage_assets(obj, root: Path):
    """Copy referenced image files into public/_in and rewrite the paths to staticFile keys."""
    if isinstance(obj, dict):
        return {k: _stage_assets(v, root) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stage_assets(v, root) for v in obj]
    if isinstance(obj, str) and Path(obj).suffix.lower() in IMG_EXT:
        p = Path(obj)
        p = p if p.is_absolute() else root / p
        if p.exists():
            h = hashlib.md5(f"{p.resolve()}|{p.stat().st_mtime_ns}".encode()).hexdigest()[:12]
            PUBLIC_IN = _public_in()
            PUBLIC_IN.mkdir(parents=True, exist_ok=True)
            dst = PUBLIC_IN / f"{h}{p.suffix.lower()}"
            if not dst.exists():
                shutil.copy2(p, dst)
            return f"_in/{dst.name}"
    return obj


def _npx() -> str:
    return shutil.which("npx.cmd") or shutil.which("npx") or "npx"


def stage(props: dict, root: str | Path = ".") -> dict:
    """Copy the images a props dict refers to into public/_in (call for every item before ensure_bundle)."""
    return _stage_assets(props, Path(root))


def _public_in() -> Path:
    return ensure_bundle() / "public" / "_in" if RT else PUBLIC_IN


def ensure_bundle() -> Path:
    """Bundle src/ + public/ once (webpack) and reuse it for every render until the code or assets change."""
    if RT:  # copy the shipped bundle to a writable cache once per version (staged images go into its public/_in)
        d = CACHE_ROOT / f"bundle_{_src_version()}"
        if not (d / "index.html").exists():
            shutil.copytree(RT / "bundle", d, dirs_exist_ok=True)
        return d
    names = sorted(p.name for p in PUBLIC_IN.glob("*")) if PUBLIC_IN.exists() else []
    key = _src_version() + hashlib.md5("|".join(names).encode()).hexdigest()[:6]
    d = HERE / "build" / key
    if (d / "index.html").exists():
        return d
    r = subprocess.run([_npx(), "remotion", "bundle", "src/index.ts", f"--out-dir={d}", "--log=error"], cwd=str(HERE),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not (d / "index.html").exists():
        raise RuntimeError("Remotion bundle failed:\n" + (r.stderr or r.stdout)[-2500:])
    for old in (HERE / "build").iterdir():
        if old != d and old.is_dir():
            shutil.rmtree(old, ignore_errors=True)
    return d


def target_path(comp: str, props: dict, duration: float, width: int = 1080, height: int = 1920, fps: int = 30,
                cache_dir: str | Path | None = None, root: str | Path = ".", still: float | None = None) -> tuple[Path, dict]:
    """Where render() would write this item (cached by content), plus the props it would pass to Remotion."""
    if comp not in COMPS:
        raise ValueError(f"unknown motion comp '{comp}' (have: {', '.join(sorted(COMPS))})")
    full = {**_stage_assets(props, Path(root)), "duration": round(float(duration), 3), "width": width, "height": height, "fps": fps}
    key = hashlib.md5(json.dumps([comp, full, _src_version(), still], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    cache = Path(cache_dir) if cache_dir else CACHE_ROOT / "out"
    return cache / f"{comp}_{key}{'.png' if still is not None else '.mov'}", full


def render(comp: str, props: dict, duration: float, width: int = 1080, height: int = 1920, fps: int = 30,
           cache_dir: str | Path | None = None, root: str | Path = ".", still: float | None = None,
           out: str | Path | None = None, bundle: str | Path | None = None) -> Path:
    path, full = target_path(comp, props, duration, width, height, fps, cache_dir, root, still)
    path.parent.mkdir(parents=True, exist_ok=True)
    target = Path(out) if out else path
    if target.exists() and not out:
        return target
    key = path.stem.split("_")[-1]
    cache = path.parent
    entry = str(bundle or ensure_bundle())
    pfile = cache / f"props_{key}.json"
    pfile.write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
    if RT:
        job = cache / f"job_{key}.json"
        job.write_text(json.dumps({"bundle": entry, "comp": comp, "props": str(pfile.resolve()), "out": str(target.resolve()),
                                   "frame": int(still * fps) if still is not None else None}), encoding="utf-8")
        r = subprocess.run([NODE, str(RT / "render.mjs"), str(job)], cwd=str(RT), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        job.unlink(missing_ok=True)
        if r.returncode != 0 or not target.exists():
            raise RuntimeError(f"Remotion failed for {comp}:\n{(r.stderr or r.stdout)[-2500:]}")
        pfile.unlink(missing_ok=True)
        return target
    if still is not None:
        cmd = [_npx(), "remotion", "still", entry, comp, str(target.resolve()), f"--props={pfile.resolve()}",
               f"--frame={int(still * fps)}", "--image-format=png", "--log=error"]
    else:
        cmd = [_npx(), "remotion", "render", entry, comp, str(target.resolve()), f"--props={pfile.resolve()}",
               "--codec=prores", "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png",
               "--muted", "--log=error"]
    r = subprocess.run(cmd, cwd=str(HERE), capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not target.exists():
        raise RuntimeError(f"Remotion failed for {comp}:\n{(r.stderr or r.stdout)[-2500:]}")
    pfile.unlink(missing_ok=True)
    return target


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comp")
    ap.add_argument("props", help="JSON string or path to a .json file")
    ap.add_argument("--duration", type=float, default=3)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--root", default=".")
    ap.add_argument("--still", type=float, help="render one frame at this second (PNG) instead of a video")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    props = json.loads(Path(a.props).read_text(encoding="utf-8")) if a.props.endswith(".json") else json.loads(a.props)
    p = render(a.comp, props, a.duration, a.width, a.height, a.fps, root=a.root, still=a.still, out=a.out)
    print(p)


if __name__ == "__main__":
    sys.exit(main())
