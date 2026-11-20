#!/usr/bin/env bash
# Video VIP Pro setup (macOS / Linux). Needs python3, node 18+, ffmpeg (with libass).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
for c in python3 node ffmpeg; do command -v $c >/dev/null || { echo "THIẾU: $c"; exit 1; }; done
python3 -m pip install -r "$HERE/requirements.txt" onnxruntime
(cd "$HERE/motion" && npm ci --no-audit --no-fund)
FD="$HOME/.local/share/fonts"; [ "$(uname)" = "Darwin" ] && FD="$HOME/Library/Fonts"
mkdir -p "$FD" && cp "$HERE"/assets/fonts/*.ttf "$FD"/ && (command -v fc-cache >/dev/null && fc-cache -f >/dev/null || true)
python3 "$HERE/scripts/make_sfx.py" >/dev/null
python3 "$HERE/scripts/get_sfx.py"
mkdir -p "$HOME/.claude/skills"; [ -e "$HOME/.claude/skills/video-vip-pro" ] || ln -s "$HERE" "$HOME/.claude/skills/video-vip-pro"
echo "XONG! Trong Claude Code: dùng skill video-vip-pro edit video <đường dẫn>"
