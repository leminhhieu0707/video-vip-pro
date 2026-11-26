---
name: video-vip-pro
description: One-call premium video editor for talking-head and sales videos in any industry (shop, real estate, spa, F&B, education, tech, finance, gym, travel, news, vlog) with a brand colour of the user's choice. Takes a raw video, transcribes it (Vietnamese or any language), cuts bad takes lip-sync safe, adds rhythmic zooms with motion blur, two-tier captions, frosted-glass scenes and ~60 VIP effects (text behind the head, portrait blur, person breaking out of the frame, freeze-frame character intro, spotlight, count-up prices, price slash, printing receipt, map pin, stamps, tear-away, cracks, shockwave, orbit ring, speed ramps, whip / glitch / light-leak / zoom-through transitions, neon outline, clones, dolly zoom, face bubble, anime impact frame, 3D photo, evidence board, seamless loop ending, film/VHS looks, UI mockups) plus a Studio Look pack (colour match between clips, fake relighting of a plain room, decor props behind the speaker) and a 26-style premium text pack (3D text in the room, text weaving around the speaker, projected / glass / gold / neon text, handwriting, odometer prices, rotating seals, cube flips, tracked price labels, documentary labels, quote cards, AI chat, beat-synced words), sound effects and music, then renders a 9:16/16:9 MP4. An edit brain (fx_brain.py) watches the footage and reads every sentence to pick which effect goes on which word. Afterwards the user refines it with plain prompts or the local VIP Editor (0 token). Use when the user says "edit video VIP", "dựng video kiểu VIP / pro", "edit video này", "đổi màu chủ đạo", or gives a raw video to edit with this skill.
---

# Video VIP Pro

A raw video goes in. You return a finished, premium edit in **one go**. After that the user steers with short prompts ("câu 3 đổi hiệu ứng", "màu cam", "bỏ VHS", "chữ to hơn"), so every edit is rebuilt from a small builder script.

Scripts live in `scripts/` next to this file. Run them as `python -X utf8 <skill>/scripts/<name>.py`. First-time setup is `setup.ps1` (Windows) or `setup.sh`; it also runs `scripts/get_sfx.py`, which downloads the trend SFX pack (about 130 Mixkit sounds in 19 families) to this computer. If a command fails with a missing module or font, run setup.

## Files to read
| when | read |
|---|---|
| always, before planning | `references/edit_brain.md` (creative pass, 7 edit styles, variety rules, trend sound design) + `references/style.md` (every effect + props, camera, theme) |
| picking effects / colour for the business | the matching row of `references/industries.md` |
| a plan field you are unsure of | grep `references/plan.md` (full schema) |
| non-talking-head genres (montage, slideshow, tutorial, podcast) | the matching section of `references/recipes.md` |
| starting the builder | run `scripts/fx_brain.py` (edit brain), then copy `templates/build_vip.py` |
| real estate: a project, a plot, a house (map, location, distances, floor plan, 3D block) | `references/style.md` → "ESTATE pack", then `scripts/geo.py build` for the satellite map and `scripts/floorplan.py` when the user sends a drawing (bản vẽ / mặt bằng) |
| real-estate footage (flycam, GES renders): plot / labels glued to the ground, sky, text behind buildings, day → night, masking transition | `references/style.md` → "ESTATE pro pack" (`scripts/footage.py`, `scripts/ges.py`) |
| a plot / land lot / project site as the hero shot (B&W world, slab lift, info sheet) | `references/style.md` → "PlotSpotlight" |
| a talking head that explains things (lists, steps, before/after, "people search for…") | `references/style.md` → "NARRATE pack" (`ExplainCanvas`, the speaker stays in a live bubble) |

## One-call workflow (do all of it without asking, unless a choice really changes the result)
1. **Brief.** Infer these:
   - **Industry**, from what is said or seen.
   - **Theme:**
     - the colour the user named, if any;
     - otherwise the brand's colour (logo, sign, uniform);
     - otherwise the industry default.
   - **Aspect:** 9:16 unless the source is horizontal and meant for YouTube.
   - **Length:** keep every good sentence.

   Ask only if the user gave several unrelated files with no hint.
2. **Watch.** Run `analyze.py SRC --every 2` and Read the sheets. Note:
   - where the face is: this becomes `FACE`;
   - where empty space is;
   - any burned-in text;
   - the shirt colour, because text on the chest must stay readable.
3. **Transcribe.** Run `transcribe.py SRC --prompt "<brand, product, names>"`. Then **proofread** the `.transcript.json`:
   - fix misheard words, keeping the word count where possible;
   - write prices the Vietnamese way: "8.190.000đ" or "8,19 triệu".
4. **Choose sentences.** Write `edited/cuts.json` with one entry per sentence you keep, in order:
   - drop retakes (keep the later, cleaner take), false starts, "cắt nhé" and dead air;
   - in = first word −0.08 s, out = last word +0.15 s; add "transcripts" (the source .transcript.json files) so aroll.py also writes aroll.transcript.json for captions and the sound brain.

   Then run `aroll.py edited/cuts.json -o edited/aroll.mp4 --speed 1.1`. It produces a single lip-sync-safe A-roll plus `aroll.json`, which holds the sentence start times.

   **Face retouch** (when the user asks for "mịn da / sáng da / xoá thâm mắt / môi son"): run `face_beauty.py edited/aroll.mp4 --still 4` first and look at the before|after JPG, then the full pass `face_beauty.py edited/aroll.mp4 -o edited/aroll_face.mp4 --skin 0.5 --bright 0.5 --eyes 0.75 --lips 0.14` and swap it in as `aroll.mp4` (same frames, audio copied, so sync is kept). Keep `--lips` at 0.1–0.2 for men: 0.28 already reads as lipstick. About 4 min per 30 s of 1080p.
5. **Edit brain.** Run `fx_brain.py edited/aroll.json --brand "<brand>" --plan edited/plan_vip.json` (add `--industry`, `--theme`, `--density calm|rich`, `--studio on|off`, `--comedy` when you know better than the guess; captions default to `--captions wordpop` (WordStack word-by-word lockups above the head + a blurred, slightly darker room) whenever word times exist, `--captions blue` keeps the two-tier BlueText; list / comparison sentences may get an `ExplainCanvas` cutaway (speaker in a live bubble); `--broll <folder>` + `--logo <png>` when the user has B-roll / screenshots, so the full-screen HUD chapter and neon tunnel get real pictures, `--hud off` to never use them; see style.md → "HUD pack"). It watches the A-roll (face, free space, table line, brand colour from the logo, light, tripod or handheld) and reads every sentence (prices, discounts, lists, comparisons, places, years, questions, the turn, calls to action), then picks effects with the variety rules and writes `brain.json` plus a one-line-per-sentence report. Read the report:
   - **fast / 0-token edit** ("làm nhanh", "tự edit hết"): render that `plan_vip.json` directly (`render.py edited/plan_vip.json --draft`), then go to step 8;
   - **normal edit**: the copied `build_vip.py` loads `brain.json` automatically — keep its picks as the draft, drop weak ones with `SKIP`, fix wrong guesses (industry, theme, keyword), and add the creative touches below.
   Never keep a pick that contradicts the words (a price card on a sentence without that price, a map without the address).
6. **Build.** Do the creative pass in `references/edit_brain.md` first. Pick an edit style, 3 motifs and a rhythm map, then write the storyboard table. Never reuse the previous video's sequence. Copy `templates/build_vip.py` to `edited/` and fill it in:
   - set `THEME`, `FACE`, `CAP_Y`;
   - give each sentence a `cap(i, top, text)`;
   - give each sentence a camera move (`cam`), with HOOK on sentence 0, a SNAP or EMPH on the 2–3 biggest keywords, and alternating PUSH / PUNCH / PULL on the rest;
   - add one VIP effect every 3–5 s, chosen from the industry row and placed **on the word that names it** (a price triggers `CountUp`, "3 điều" triggers `NumberList`, "đau đầu" triggers `Cracks`);
   - keep the sound brain on (`"sound_design": {"style": "trend", "brain": {...}}`, see edit_brain.md §4a): effect sounds follow the picture, story sounds follow the words. Then read `sound_brain.py`'s suggestions and cut anything that does not add meaning;
   - previously `"sound_design": "trend"` meant: every effect gets a layered sound from the trend pack automatically, so add sounds by hand only where they carry the story (riser into a reveal, silence before a punchline);
   - add 2–4 frost scenes per minute;
   - end with a CTA.
7. **Render.** Run `build_vip.py`, then `render.py plan_vip.json --draft`. Renders over 2 min run in the background. The first render of each motion item takes 3–5 s; person matting takes about 1 s per second of effect.
8. **Check your own output.** Run `analyze.py <draft> --every 1` and Read every sheet. Look for:
   - text clipped or covering the face;
   - effects that land on the wrong word;
   - unreadable colours for this theme;
   - black or frozen frames;
   - loudness away from −14 LUFS;
   - **missing effect sounds.** The render log prints `tiếng hiệu ứng: N tiếng cho M hiệu ứng`; N should be at least M. Also count `adelay` in `<plan>_work/final.fc` (= sounds actually mixed + 1 for music) and compare it with `len(render.sfx_events(plan, starts, total))`. If they differ, the export is dropping sounds that the VIP Editor still plays. Never hand over a video until the two counts match.

   Fix the builder and re-render; the segment and motion caches make this fast. Allow at most 3 rounds per issue.
9. **Final.** Run `render.py plan_vip.json` (no `--draft`).
10. **Deliver.** Send the MP4 (via `SendUserFile` if available). Then:
   - give a 3–5 line summary: length, theme, the effects used and on which sentence, and anything you guessed;
   - start the VIP Editor in the background, `python -X utf8 <skill>/editor/server.py edited/plan_vip.json`, so the user can drag, retime, retype and recolour by hand for 0 token.

**Mixed voices.** If the video mixes on-camera speech with a voice-over, run `scripts/voice_match.py` so both sound like one voice (see `references/edit_brain.md` §5). Scan every clip for good on-camera lines (transcribe them all in one pass) before deciding to use only the voice-over.

## Refining by prompt (after the first edit)
- **Always edit `build_vip.py`, never the generated plan.** If the user said they changed things in the VIP Editor, re-read `plan_vip.json` first and edit the plan directly instead, since a rebuild would drop their hand edits. Tell them which approach you are taking.
- **Map requests to edits:**

  | request | edit |
  |---|---|
  | "đổi màu …" | `THEME` |
  | "câu N …" | the block for sentence N |
  | "bỏ / thêm hiệu ứng X" | delete or add that `motion(...)` / `layer(...)` line |
  | "chữ to / nhỏ" | `size` |
  | "chữ thấp / cao" | `CAP_Y` or `y` |
  | "zoom nhiều / ít" | the `cam` / `cycle` moves |
  | "nhạc khác" | `MUSIC` |
  | "nhanh hơn" | `aroll.py --speed` (then rebuild) |

- **Check before the full render:** run `render.py plan_vip.json --preview A-B` on just the changed range, check it, then do the full render once.

## Quality rules
- **Captions.** One `BlueText` per phrase, replacing plain subtitles. At most one `**keyword**` per line. On footage, use `tone: "video"`; on a light frost, use `tone: "light"`.
- **Clean frame.** Besides the captions, keep at most one other element on screen. Never cover the face. In 9:16, keep text out of the top 10 % and the bottom 20 %.
- **Camera.** One camera event every 3–6 s. Big moves (SNAP, EMPH) at most once per 10 s.
- **Popout crop.** The `popout` crop must start below the chin, otherwise the head won't break out.
- **Honesty.** Use only prices, specs, names and quotes that appear in the footage or the user's message.
- **Licensed media only.** Use the bundled synthesized SFX, the user's own files, or royalty-free music. Never use copyrighted songs or reuploaded clips.

## Environment notes
- **Python and Node.** Python 3.10+ with `requirements.txt` (faster-whisper, rembg, onnxruntime, opencv, numpy, fonttools, Pillow, edge-tts) and Node 18+ for `motion/`. Run `npm ci` inside `motion/` (setup does this).
- **FFmpeg.** It must be a full build with libass.
- **GPU.**
  - An NVIDIA GPU speeds up Whisper and NVENC encoding.
  - Without one, Whisper runs on the CPU; use `--model small` for speed.
  - rembg uses DirectML or CUDA when available.
- **Fonts.** Be Vietnam Pro and Playfair Display are bundled in `assets/fonts` and `motion/public/fonts`.
- **Windows printing.** Set `PYTHONIOENCODING=utf-8` before printing Vietnamese from ad-hoc snippets.
- **Caches.** They live in `<plan>_work/`. Delete that folder only if the cache is broken.

## Troubleshooting
- **A motion comp renders blank:** render a still with `motion/render_motion.py COMP '<props>' --duration 2 --still 1 -o x.png` and look at it.
- **Wrong person in the matte (a logo or poster on the wall):** use `popout` `"head": [x, w]` to limit the column that may break out, or pick a calmer moment.
- **Sound drifts after cuts:** never join many talking clips segment by segment. Always go through `aroll.py`.
- **"sound effect not found":** recipe names map to built-in sounds (see `SFX_ALIASES` in `render.py`). Drop your own `name.mp3` into `assets/sfx/` to override one.
- **An effect the scripts can't do:** render it with a direct ffmpeg command, or write a new comp in `motion/src/blue/` with colours wrapped in `T('…')`, then use it in the plan.
