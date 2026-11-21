"""Face retouch for a talking-head A-roll: brighter skin, extra smoothing, softer dark circles, light lip tint.

Runs after aroll.py on the finished A-roll (same frame count, audio copied untouched, so lip sync is kept).
Face landmarks come from OpenCV's YuNet detector (eyes + mouth corners), smoothed over time so masks never jitter.

    python face_beauty.py edited/aroll.mp4 -o edited/aroll_face.mp4 [--skin 0.5] [--bright 0.5] [--eyes 0.6] [--lips 0.14]
    python face_beauty.py edited/aroll.mp4 --still 12.0          # writes aroll_face_check.jpg: before | after at 12 s

Every strength is 0–1 (0 = off). Keep them low: the goal is "slept well", not a filter.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import cv2
import numpy as np

MODEL_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
MODEL = Path.home() / ".cache" / "vipbeauty" / "face_detection_yunet_2023mar.onnx"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"
DET_W = 480  # detection width; landmarks are scaled back to full size
LIP_LAB = np.array([0, 22.0, 8.0], np.float32)  # added to a*/b* where the lips are: rosy, not red


def model_path() -> str:
    if not MODEL.exists() or MODEL.stat().st_size < 100_000:
        MODEL.parent.mkdir(parents=True, exist_ok=True)
        print("[beauty] tải mô hình nhận diện mặt YuNet (OpenCV zoo, 230 KB)", flush=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    return str(MODEL)


def probe(src: str) -> tuple[int, int, float, int]:
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_read_packets", "-of", "json", src],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    n, d = s["r_frame_rate"].split("/")
    return int(s["width"]), int(s["height"]), float(n) / float(d), int(s.get("nb_read_packets", 0))


class Tracker:
    """YuNet landmarks with an exponential moving average; holds the last face for short misses."""

    def __init__(self, W: int, H: int):
        self.scale = DET_W / W
        self.size = (DET_W, int(round(H * self.scale)))
        self.det = cv2.FaceDetectorYN.create(model_path(), "", self.size, 0.6, 0.3, 50)
        self.pts = None  # [re, le, nose, rm, lm, box(x,y,w,h)] in full-res pixels, flattened
        self.miss = 0

    def update(self, frame: np.ndarray):
        small = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
        _, faces = self.det.detect(small)
        if faces is None or len(faces) == 0:
            self.miss += 1
            if self.miss > 8:
                self.pts = None
            return self.pts
        f = max(faces, key=lambda r: r[2] * r[3])
        p = np.array([*f[4:14], *f[0:4]], np.float32) / self.scale
        self.miss = 0
        if self.pts is None or np.abs(p[:2] - self.pts[:2]).max() > 60:
            self.pts = p
        else:
            self.pts = 0.65 * self.pts + 0.35 * p
        return self.pts


def ellipse_mask(shape, center, axes, angle, feather) -> np.ndarray:
    m = np.zeros(shape[:2], np.float32)
    cv2.ellipse(m, (int(center[0]), int(center[1])), (max(1, int(axes[0])), max(1, int(axes[1]))),
                angle, 0, 360, 1.0, -1, cv2.LINE_AA)
    k = int(feather) | 1
    return cv2.GaussianBlur(m, (k, k), 0) if k > 1 else m


def skin_mask(ycc: np.ndarray) -> np.ndarray:
    cr, cb = ycc[..., 1], ycc[..., 2]
    m = ((cr > 135) & (cr < 175) & (cb > 80) & (cb < 128) & (ycc[..., 0] > 50)).astype(np.float32)
    return cv2.GaussianBlur(m, (31, 31), 0)


def retouch(frame: np.ndarray, pts, a) -> np.ndarray:
    H, W = frame.shape[:2]
    img = frame.astype(np.float32)
    if pts is None:
        return frame
    re, le, nose, rm, lm = (pts[0:2], pts[2:4], pts[4:6], pts[6:8], pts[8:10])
    bx, by, bw, bh = pts[10:14]
    eye_d = float(np.hypot(*(le - re)))
    if eye_d < 20:
        return frame
    angle = float(np.degrees(np.arctan2(le[1] - re[1], le[0] - re[0])))

    # face region (forehead to chin, a bit wider than the box) — every effect stays inside it
    fc = (bx + bw / 2, by + bh * 0.52)
    face = ellipse_mask(frame.shape, fc, (bw * 0.62, bh * 0.72), angle, eye_d * 0.5)
    ycc = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    skin = skin_mask(ycc)
    face_skin = face * skin

    # 1) extra smoothing on facial skin only (edge-preserving, then a high-pass of the original back in for texture)
    if a.skin > 0:
        d = int(5 + 6 * a.skin)
        smooth = cv2.bilateralFilter(frame, d, 20 + 40 * a.skin, d).astype(np.float32)
        detail = img - cv2.GaussianBlur(img, (0, 0), 1.2)
        smooth = smooth + detail * 0.35
        m = (face_skin * (0.55 + 0.45 * a.skin))[..., None]
        img = img * (1 - m) + smooth * m

    lab = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = lab[..., 0], lab[..., 1], lab[..., 2]

    # 2) brighter, fresher skin: lift luminance on skin (more in shadows), trim yellow a touch
    if a.bright > 0:
        sm = cv2.GaussianBlur(skin * np.maximum(face, 0.45), (0, 0), 8)
        lift = (10 + 8 * (1 - L / 255.0)) * a.bright
        L += lift * sm
        B -= 3.0 * a.bright * sm

    # 3) dark circles: pull under-eye luminance up to the cheek level and neutralise the purple/brown cast
    if a.eyes > 0:
        down = np.array([-np.sin(np.radians(angle)), np.cos(np.radians(angle))], np.float32)
        for e in (re, le):
            c = e + down * eye_d * 0.27
            m = ellipse_mask(frame.shape, c, (eye_d * 0.26, eye_d * 0.10), angle, eye_d * 0.16) * skin
            ck = e + down * eye_d * 0.62  # cheek sample below the bag
            y0, y1 = int(max(0, ck[1] - eye_d * 0.08)), int(min(H, ck[1] + eye_d * 0.08))
            x0, x1 = int(max(0, ck[0] - eye_d * 0.12)), int(min(W, ck[0] + eye_d * 0.12))
            if y1 <= y0 or x1 <= x0:
                continue
            cl, ca, cb = (float(np.median(ch[y0:y1, x0:x1])) for ch in (L, A, B))
            k = m * a.eyes
            L += np.clip(cl - L, 0, 40) * k * 0.85
            A += (ca - A) * k * 0.6
            B += (cb - B) * k * 0.6

    # 4) lip tint: lip pixels = redder than the surrounding skin inside a mouth ellipse, teeth excluded
    if a.lips > 0:
        mc = (rm + lm) / 2
        mw = float(np.hypot(*(lm - rm)))
        down = np.array([-np.sin(np.radians(angle)), np.cos(np.radians(angle))], np.float32)
        mc2 = mc + down * mw * 0.06
        reg = ellipse_mask(frame.shape, mc2, (mw * 0.66, mw * 0.36), angle, 3)
        y0, y1 = int(max(0, mc2[1] - mw * 0.5)), int(min(H, mc2[1] + mw * 0.5))
        x0, x1 = int(max(0, mc2[0] - mw * 0.8)), int(min(W, mc2[0] + mw * 0.8))
        if y1 > y0 and x1 > x0:
            ring = (skin[y0:y1, x0:x1] > 0.5) & (reg[y0:y1, x0:x1] < 0.05)
            base_a = float(np.median(A[y0:y1, x0:x1][ring])) if ring.sum() > 50 else float(np.median(A[y0:y1, x0:x1]))
            redness = np.clip((A - base_a - 3) / 8.0, 0, 1)
            not_teeth = np.clip((A - 135) / 6.0, 0, 1) * np.clip((200 - L) / 30.0, 0, 1)
            lip = cv2.GaussianBlur(redness * not_teeth * reg, (0, 0), max(1.5, mw * 0.025))
            k = lip * a.lips
            A += LIP_LAB[1] * k
            B += LIP_LAB[2] * k
            L -= 4.0 * k

    lab = np.dstack([np.clip(L, 0, 255), np.clip(A, 0, 255), np.clip(B, 0, 255)]).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--skin", type=float, default=0.5, help="extra smoothing on facial skin 0–1")
    ap.add_argument("--bright", type=float, default=0.5, help="brighter skin 0–1")
    ap.add_argument("--eyes", type=float, default=0.75, help="dark-circle removal 0–1")
    ap.add_argument("--lips", type=float, default=0.14, help="lip tint 0–1")
    ap.add_argument("--still", type=float, default=None, help="only write a before|after JPG at this second")
    a = ap.parse_args()

    src = str(Path(a.input).resolve())
    W, H, fps, n = probe(src)
    trk = Tracker(W, H)

    if a.still is not None:
        cap = cv2.VideoCapture(src)
        start = max(0, int(a.still * fps) - 10)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        for _ in range(11):  # warm up the tracker so the still uses smoothed landmarks
            ok, fr = cap.read()
            if not ok:
                break
            pts = trk.update(fr)
        out = retouch(fr, pts, a)
        dst = Path(a.out) if a.out else Path(src).with_name(Path(src).stem + "_face_check.jpg")
        cv2.imwrite(str(dst), np.hstack([fr, out]))
        print(f"[beauty] {dst}  (mặt: {'có' if pts is not None else 'KHÔNG thấy'})")
        return

    dst = Path(a.out).resolve() if a.out else Path(src).with_name(Path(src).stem + "_face.mp4")
    tmp = dst.with_suffix(".video.mp4")
    rd = subprocess.Popen([FFMPEG, "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                          stdout=subprocess.PIPE)
    enc = ["-c:v", "h264_nvenc", "-preset", "p6", "-cq", "16", "-b:v", "0"] if _has_nvenc() else \
          ["-c:v", "libx264", "-crf", "15", "-preset", "medium"]
    wr = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                           "-r", f"{fps}", "-i", "-", *enc, "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    size, i, seen = W * H * 3, 0, 0
    while True:
        buf = rd.stdout.read(size)
        if len(buf) < size:
            break
        fr = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        pts = trk.update(fr)
        seen += pts is not None
        wr.stdin.write(retouch(fr, pts, a).tobytes())
        i += 1
        if i % 150 == 0:
            print(f"[beauty] {i}/{n or '?'} khung", flush=True)
    wr.stdin.close()
    wr.wait()
    rd.wait()
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(tmp), "-i", src, "-map", "0:v", "-map", "1:a?",
                    "-c", "copy", "-shortest", str(dst)], check=True)
    tmp.unlink(missing_ok=True)
    print(f"[beauty] xong {dst}  ({i} khung, thấy mặt {seen * 100 // max(1, i)}%)")


def _has_nvenc() -> bool:
    r = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True)
    return "h264_nvenc" in r.stdout


if __name__ == "__main__":
    sys.exit(main())
