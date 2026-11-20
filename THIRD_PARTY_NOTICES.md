# Third-party components

| component | where | license |
|---|---|---|
| Remotion 4 (installed by `npm ci`, not bundled) | `motion/` | Remotion License: free for individuals and companies of up to 3 people; larger companies need a company license — https://www.remotion.dev/license |
| React, lottie-web (installed by npm) | `motion/` | MIT |
| JASSUB (libass for the browser) | `editor/vendor/jassub/` | MIT (see `editor/vendor/jassub/COPYRIGHT`) |
| Be Vietnam Pro (Lâm Bảo, Tony Le, ViệtAnh Nguyễn) | `assets/fonts/`, `motion/public/fonts/` | SIL Open Font License 1.1 — `assets/fonts/OFL.txt` |
| Playfair Display (Claus Eggers Sørensen) | `assets/fonts/`, `motion/public/fonts/` | SIL Open Font License 1.1 — `assets/fonts/OFL.txt` |
| faster-whisper, CTranslate2 (pip) | `scripts/transcribe.py` | MIT |
| rembg (pip) + U²-Net model (downloaded on first use) | `scripts/vipfx.py`, `behind_text.py` | MIT / Apache-2.0 |
| edge-tts (pip) | `scripts/tts.py` | LGPL-3.0 (used as a separate library) |
| FFmpeg (installed separately) | everywhere | LGPL/GPL depending on build |

Sound effects in `assets/sfx/` are synthesized by `scripts/make_sfx.py` (no samples) and are part of this project (MIT).
