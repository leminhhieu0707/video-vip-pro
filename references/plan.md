# Edit plan schema (`plan.json`)

`render.py plan.json` turns this file into a finished video. Relative paths are resolved from the plan file's folder.
All times are seconds (number) or `"m:ss.s"` strings.

## Contents
1. Top level
2. canvas
3. clips (+ transitions)
4. subtitles
5. overlays: label, title, badge, text, image, video
6. audio
7. Positions and animations
8. Full example

---

## 1. Top level

```json
{
  "output": "edited/ads_final.mp4",
  "canvas": {...},
  "clips": [...],
  "subtitles": {...},
  "overlays": [...],
  "audio": {...},
  "font": "Be Vietnam Pro Bold",
  "quality": "high",
  "fade_in": 0,
  "fade_out": 0.6
}
```

| key | meaning |
|---|---|
| `font` | Default font for all text. Any installed font's full name works. The size of every font is normalized automatically, so a given `size` looks the same across fonts. |
| `quality` | `draft`, `high` (default), or `max`. Uses NVENC on the GPU when available. |
| `fade_in` / `fade_out` | Fade from or to black for the whole video, with audio, in seconds. |

## 2. canvas

```json
"canvas": {"aspect": "9:16", "fps": 30, "fit": "auto", "bg": "black"}
```
- `aspect`: one of `9:16` (1080×1920), `16:9` (1920×1080), `1:1`, `4:5`, `4:3`, `3:4`. Alternatively give `width` and `height` directly.
- `fit`: the default way a clip fills the canvas.
  - `auto`: crop if the clip's aspect is close to the canvas, otherwise blur.
  - `crop`: fill the frame and cut off the edges.
  - `blur`: show the whole clip over a blurred copy of itself. Best for putting a 16:9 clip into a 9:16 canvas.
  - `pad`: bars in the `bg` color.
  - `stretch`: distort to fit. Avoid this.
- `render.py --aspect 16:9` re-renders the same plan in another format. Overlay positions are fractions, so they adapt.

## 3. clips

Clips play in order on the timeline. Each one is normalized to the canvas and cached, so re-renders are fast.

```json
{"src": "raw/a.mp4", "in": 12.4, "out": 18.9}
{"src": "raw/b.mov", "in": "1:02.5", "out": "1:07", "fit": "blur", "speed": 1.25, "volume": 0.8}
{"src": "photos/house.jpg", "duration": 3, "zoom": "in", "zoom_amount": 0.12}
{"src": "raw/c.mp4", "in": 0, "out": 4, "mute": true, "focus": 0.3, "color": {"contrast": 1.08, "saturation": 1.15}}
{"src": "raw/d.mp4", "in": 5, "out": 9, "transition": {"type": "fade", "duration": 0.4}}
```
| key | meaning |
|---|---|
| `in` / `out` | The trim range in the source. If `out` is omitted, the clip runs to the end. |
| `duration` | For images only. Images get a slow Ken Burns zoom (`zoom`: `in`, `out`, or `none`). |
| `speed` | Speed factor such as 0.5 or 1.5. Audio pitch is preserved. |
| `volume` / `mute` | This clip's own audio. |
| `fit` / `focus` | Overrides `canvas.fit`. `focus` sets the horizontal crop center from 0 (left) to 1 (right), for example to keep the person in frame when cropping 16:9 to 9:16. |
| `color` | `brightness` (−1…1, ~0.03), `contrast` (~1.05–1.15), `saturation` (~1.1–1.25), `gamma`. |
| `flip` | Mirrors the clip horizontally. |
| `punch` | A static punch-in on video, such as 1.15. It crops toward `focus`. Alternate it between jump cuts. |
| `zoom` on video | `in` or `out` gives a slow push across the clip (`zoom_amount` defaults to 0.08). `zoom_ease`: `"in"` accelerates (a push into the cut), `"out"` lands softly; default linear. |
| `zooms` | Keyframed **punch zooms** on the keyword (CapCut style): `[{"at": 2.3, "to": 1.25, "in": 0.16, "hold": 0.9, "out": 0.3, "x": 0.5, "y": 0.4}]`. `at` is clip-relative (use the keyword's start from the transcript), `out: null` stays zoomed to the end of the clip. Use 1.15–1.25 for emphasis and 1.3–1.4 for the price/biggest number. |
| `shake` | Short camera shake on an impact moment: `{"at": 4.5, "dur": 0.3, "amp": 12}` (clip-relative). Pair it with `bass_hit` or `vine_boom`. |
| `transition` | How this clip enters from the previous one. It is either a string or `{"type","duration"}`. The default is a hard cut. The types are the ffmpeg xfade names: `fade`, `fadeblack`, `fadewhite`, `dissolve`, `slideleft/right/up/down`, `smoothleft/right/up/down`, `wipeleft/right/up/down`, `circleopen`, `circleclose`, `radial`, `zoomin`, `pixelize`, `hblur`, `coverleft`, `revealleft`, `fadegrays`, and others. A transition overlaps the two clips, so the timeline gets shorter by its duration. `"whip"`, `"glitch"`, `"leak"`, `"zoomthru"`, `"spinwhip"` (rotating whip, 1 frame before + 7 after the cut) (or `{"type":"whip","dir":"right","duration":0.36}`) are the exception: a whip pan drawn over a hard cut, no overlap. |
| `parallax` | Image clips only: `true` or `{"amount","dir"}` makes a 2.5D "3D photo" (subject and background drift apart). |
| `ramp` | Speed ramp for B-roll: `"velocity"`, `"hero"`, `"rush_in"`, `"slowmo_end"`, `"push_out"` / `"push_in"` (the walkthrough push pair: speeds up to ~4x into the cut / lands fast and eases) or `[[fraction, speed], …]`. Replaces `speed`, mutes the clip, adds motion blur on fast parts; the clip length follows from the curve. |

`render.py` prints the **clip start times on the final timeline**, which tells you where each clip landed.

### Look & sound per clip (also settable once for all clips via top-level `"clip_defaults": {...}`)
| key | meaning |
|---|---|
| `grade` | Color preset: `bright` (clean shops, products), `bds_net` (crisp real-estate B-roll: deep blacks, kept whites, ~+30 % colour), `net` (sharpen compressed phone / Facebook / Zalo footage; stackable), `vivid`, `warm`, `cool`, `cinematic` (teal/orange), `vintage`, `pastel`, `moody`, `bw`. It also takes a list of presets, or a dict `{"preset","brightness","contrast","saturation","gamma","temperature":K,"vibrance","lut":"x.cube"}`. |
| `beauty` | Skin smoothing from 0 to 1. Use 0.5–0.7 for natural results. Only pixels with skin color are smoothed, with an edge-preserving filter, so eyes, hair, text and the background stay sharp. It adds about 1 s of render time per second of 1080p. |
| `denoise` | `light` (hiss), `medium` (AC or room rumble plus a gate between words), or `strong` (wind or loud fans; can sound thin). Check with `showspectrumpic` before and after. |
| `voice` | `true` gives clearer, punchier speech: it cuts mud, adds presence, compresses and de-esses. |

Example: `"clip_defaults": {"denoise": "medium", "voice": true, "grade": "bright", "beauty": 0.6}`. Override per clip with `"beauty": 0` (storefront or B-roll) or `"denoise": null` (muted clips).

## 4. subtitles

```json
"subtitles": {
  "transcript": "raw/a.transcript.json",
  "style": "tiktok",
  "words_per_line": 4,
  "max_chars": 24,
  "pos": "lower",
  "size": 80,
  "uppercase": false,
  "highlight": "#FFD600",
  "keywords": {"miễn": "#FF4D8D", "1.000.000": "#22C55E"},
  "timing": "auto",
  "offset": 0
}
```
- `transcript` can be **one path or a list**, for example one transcript per raw clip when the edit is built from many short takes. Each one is matched by its `source`.
- **Timing is automatic.** If the transcript's `source` file is used as clips in the plan, word times are remapped onto the edited timeline, so cut sections disappear from the subtitles too. Set `"timing": "timeline"` when the transcript was made from the final timeline itself, for example a voiceover.
- `style` presets:
  - `tiktok`: white with a thick outline, and the spoken word turns yellow and pops.
  - `box`: white text on a colored box. The default is orange. Set `bg` to change it.
  - `clean`: white with a thin outline, for vlogs and interviews.
  - `karaoke`: the color fills across each word as it is spoken.
  - `news`: yellow, all capitals, heavy outline.
  - `minimal`: a translucent dark box.
  - Any key such as `color`, `bg`, `outline_color`, `highlight`, or `font` overrides the preset.
- Correcting the transcript: edit a segment's `"text"` in the transcript JSON. If its words no longer match `words`, timing is spread across the new words automatically, so you never need to fix the word list by hand.
- The default `pos` is `lower` for portrait and `bottom` for landscape.
- `keywords` matches single words (case-insensitive, punctuation ignored).

## 5. overlays

Every overlay takes `start` and `end` (or `duration`) on the **final timeline**. Clip-anchored text is cut automatically when the next clip begins, so nothing lingers into a transition. Set `"span": true` to let it run across clips. You can instead give `"clip": N`, which makes `start` and `end` relative to clip N's start. Use the clip-relative form whenever the overlay belongs to a particular shot, because it stays correct when earlier clips change length.

Common keys are `pos`, `anim`, `rotate` (degrees), `pulse` (true gives a gentle breathing scale), `font`, `size`, and `uppercase`.

### label: a two-tier tag for prices, specs, and stats
```json
{"type": "label", "clip": 1, "start": 0.3, "end": 3.2, "title": "12 Pro Max", "text": "8.190k",
 "pos": [0.3, 0.42], "title_bg": "red", "title_color": "white", "bg": "white", "color": "#111111", "rotate": 3}
```
The small colored title box sits above a big value box. By default the title pops in and the value wipes in from the left. `size` is the value's size and `title_size` is the title's. Title text is uppercase by default.

### title: a headline with an optional highlighted line
```json
{"type": "title", "start": 34.5, "end": 38, "text": "Tặng gói thay pin", "highlight": "Miễn phí 1 năm",
 "highlight_bg": "red", "pos": "top", "pulse": true}
```

### badge: a single box
```json
{"type": "badge", "start": 33, "end": 35.5, "text": "1 đổi 1 trong 30 ngày", "bg": "blue", "icon": "dot",
 "icon_color": "#22C55E", "pos": [0.5, 0.45], "anim": "slide-left"}
```

### text: free text
```json
{"type": "text", "start": 0, "end": 3, "text": "419 Điện Biên Phủ", "size": 60, "color": "white",
 "outline_color": "black", "outline": 4, "bg": "#000000C0", "bold": true, "pos": "bottom", "anim": "fade"}
```
With `bg` set, the text sits in a box. Without it, the text is outlined. `\n` makes a new line.

### image: logos, stickers, product shots
```json
{"type": "image", "src": "assets/logo.png", "pos": [0.86, 0.07], "width": 0.16, "start": 0, "end": 60,
 "opacity": 1, "radius": 30, "fade": 0.3}
```
`width` is a fraction of the canvas width (≤1) or a number of pixels. `radius` rounds the corners, in output pixels. It is capped at half the overlay width, so a large value gives a circle. PNG transparency is kept.

### video: picture-in-picture, B-roll windows, green-screen or black-background effects
```json
{"type": "video", "src": "fx/fire.mp4", "start": 2, "end": 5, "pos": "center", "width": 0.9,
 "key": "#000000", "similarity": 0.25, "blend": 0.1, "in": 0, "loop": true}
```
`key` removes a color: `#00FF00` for green screen, or `#000000` for effects shot on black. The overlay's own audio is not used.

### motion: Remotion motion graphics (Blue style pack)
```json
{"type": "motion", "comp": "BlueText", "start": 2.76, "end": 5.1, "props": {"top": "giờ có cái con AI này", "text": "nó **edit hết** _cho mọi người_", "y": 0.75}}
```
Rendered to a cached transparent clip of exactly the overlay's length and laid over the frame. Comps: `BlueText`, `BlueBig`, `Tiles`, `Checklist`, `ScreenCard`, `NumberTitle`, `FollowCard`. Full props and markup in `style.md`. Real estate on real maps: `GeoMap`, `Building3D`, `FloorPlan2D` (ESTATE pack in `style.md`, data from `scripts/geo.py`). Full-screen agency chapters: `HudChapter` and `NeonTunnel` (HUD pack in `style.md`); their `media` / `items` accept videos as well as images.

### frost: frosted-glass scene
```json
{"type": "frost", "start": 5.1, "end": 7.3, "mode": "light", "window": {"crop": [0.08, 0.27, 0.84, 0.4], "pos": [0.5, 0.71], "width": 0.84, "radius": 44}}
```
Blurs and tints everything listed before it for the time range (`mode` light/blue/dark/white, `blur` 36, `fade` 0.25); optional `window` puts a sharp rounded crop of the frame on top (split layout). Subtitles hide during it unless `"hide_subs": false`.

## 6. audio

```json
"audio": {
  "original_volume": 1.0,
  "voiceover": [{"src": "vo.mp3", "start": 0, "volume": 1.0},
                {"src": "raw/IMG_9465.MOV", "in": 0.1, "out": 4.9, "clip": 21, "start": 0}],
  "music": {"src": "music.mp3", "volume": 0.18, "in": 0, "start": 0, "end": null,
            "fade_in": 0.5, "fade_out": 2, "duck": true, "duck_threshold": 0.02, "duck_ratio": 6},
  "normalize": -14
}
```
- `voiceover` is one object or a list. `in`/`out` trim the source, which lets you lay **the audio of one take over other visuals**, for example the address line over a storefront shot whose clip has `"mute": true`. `clip: N` makes `start` relative to clip N. Subtitles from that take's transcript follow the voiceover automatically.
- Music loops to fill the video. `duck` lowers it automatically while someone is speaking.
- Use `volume` 0.12–0.2 under speech and 0.5–0.8 for music-only montages, where you should also set `duck: false`.
- `normalize` is the target loudness in LUFS. Use −14 for TikTok, Reels, and YouTube, or `null` to skip.
- `original_volume: 0` mutes all clip audio, for example for a pure music montage.

### Sound effects
```json
"auto_sfx": {"volume": 0.4, "transition": "whoosh", "label": "pop", "badge": "pop", "title": "swoosh", "cut": null},
"sfx": [{"sfx": "impact", "clip": 0, "at": 0.3, "volume": 0.6}, {"sfx": "my_files/laugh.mp3", "at": 12.5}]
```
- The library in `assets/sfx/` (regenerate with `make_sfx.py`) holds ~35 synthesized sounds (royalty-free). Recipe names like `whoosh_air`, `pop_bubble`, `tech_tick`, `bass_hit` map to the closest built-in sound (SFX_ALIASES in render.py); drop your own .mp3/.wav with that name into `assets/sfx/` to use a better recording. **UI:** `whoosh`, `whoosh2`, `whoosh3`, `swoosh`, `swipe`, `pop`, `pop2`, `pop3`, `bubble`, `click`, `ding`, `ding2`, `notify`, `cash`, `sparkle`, `shutter`, `typing`, `glitch`. **Meme/TikTok:** `vine_boom` (punchline or shock), `rimshot` (ba-dum-tss after a joke), `sad_trombone` (fail), `dun_dun_dun` (drama reveal), `record_scratch` ("wait, what?"), `tada`, `boing`, `bonk`, `drumroll`, `slide_up`, `slide_down`, `heartbeat`, `riser`, `impact`. Put any downloaded .wav or .mp3 in that folder to use it by name. An `sfx` value or an `auto_sfx` entry can be a **list**: it rotates through the list, so repeated overlays don't sound the same.
- `auto_sfx` adds a whoosh on every non-cut transition and a sound on each overlay's entrance, by type. Per overlay, `"sfx": "cash"` overrides the sound and `"sfx": null` silences it; per clip, `"transition_sfx"` does the same. `"cut": "swipe"` also adds a sound on hard cuts.
- Use them sparingly. On every hit they get tiring, so reserve `impact`, `cash` and `riser` for the 1–3 biggest moments.

## 7. Positions and animations

`pos` accepts:
- A name: `top`, `upper`, `center`, `lower`, `bottom`, `top-left`, `top-right`, `bottom-left`, `bottom-right`, `left`, or `right`.
- `[x, y]` as fractions of the canvas, giving the overlay's center: `[0.5, 0.5]` is the middle and `[0.3, 0.42]` is left of center, a little above the middle.
- Pixel values greater than 1.

Platform safe zones for 9:16: keep text out of the top ~10% and the bottom ~20%, and important text out of the right ~15%, because the like and comment buttons sit there. The `lower` position (y = 0.68) is safe for subtitles.

`anim` accepts `blurin` / `blur` (soft blur-in, Blue style), `pop` (the default for labels), `bounce`, `fade`, `slide-left`, `slide-right`, `slide-up`, `slide-down`, `wipe`, `zoom`, `shake`, and `none`. Each one includes a short fade-out.

## 8. Full example (product ad, 9:16)

See `templates/build_vip.py` for a complete builder.


## Blue VIP overlays (scripts/vipfx.py) — see `style.md` → "VIP pack"
`{"type":"bg", blur|scale+radius+color|src}` background-only change with the speaker kept on top (rembg matte) ·
`{"type":"popout", window, bg}` speaker breaking out of a rounded window · `{"type":"lens", at, pos, size, zoom}` ·
`{"type":"fx", effect: film|vhs|bw|warm|cool, compare?}` · motion overlays accept `"behind": true` and `"fill": "video"` ·
frost accepts `"mode": "navy"|"none"|"solid"`, `"grid": true`, `fade_in`/`fade_out` · `zooms` keys accept `"blur"` (auto on fast zooms) ·
motion props accept `"frame:12.3"` (still of the edit).
