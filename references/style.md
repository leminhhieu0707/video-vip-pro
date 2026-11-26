# VIP style: motion graphics, camera moves, person-aware layers

A calm, premium talking-head look that works for any industry. It uses:
- two-tier captions instead of plain subtitles, with words that blur in;
- keywords in the brand colour;
- frosted-glass scenes, white glass icon tiles, tick lists and a split layout;
- rhythmic zooms;
- about 45 VIP effects.

Everything is drawn in a reference blue and re-coloured by the plan's `"theme"`. Start from `templates/build_vip.py`. Per-industry presets are in `references/industries.md`.

## Theme (brand colour)
`theme` is a top-level plan key. It applies to every layer: motion graphics, frost tints, cards, popout backgrounds, and any colours written in the plan.

| Form | Example | Notes |
|---|---|---|
| Preset name | `"theme": "orange"` | |
| Any colour | `"theme": "#FF6A1A"` | The dark tone is derived automatically. |
| Primary + dark | `"theme": {"primary": "#E8B84A", "dark": "#121212"}` | Dark `#121212` gives neutral black scenes, for a luxury black-and-gold look. |

**Presets.** `python scripts/theme.py` lists them. Vietnamese names work too.

| Preset | Vietnamese name |
|---|---|
| blue (default) | xanh |
| orange | cam |
| red | đỏ |
| gold | vàng kim |
| blackgold | đen vàng |
| green | xanh lá |
| pink | hồng |
| purple | tím |
| teal | ngọc |
| sky | da trời |
| brown | nâu |
| mono | đen |

**How colours behave:**
- **Write plan colours in the reference blue** and they follow the theme:
  - `#3158FF` primary;
  - `#8EB3FF` light;
  - `#0B1E5E` / `#0E1530` navy;
  - `0xEEF1F8` paper.
- **Non-blue colours** (red stamp, gold price, green button) stay exactly as written.
- **Light primaries** (gold, sky) read weaker on a light frost. With them, use `tone: "video"` text or a dark frost.

## Motion overlays (Remotion → transparent ProRes, cached in `<plan>_work/motion/`)

Example overlay:

```json
{"type": "motion", "comp": "BlueText", "start": 2.76, "end": 5.10,
 "props": {"top": "giờ có cái con AI này", "text": "nó **edit hết** _cho mọi người_", "y": 0.75}}
```

- **Timing:** `start` / `end` work like any overlay (or use `clip` + relative times). The clip is rendered at exactly that length.
- **Word timing:** `times` is optional. It lists the second each big-line word appears, measured from the overlay start, taken from the transcript. Without it, words are spread evenly.
- **Text markup** works in any `text` / `sub` / `title` / `t` field:

  | Markup | Result |
  |---|---|
  | plain | bold white |
  | `**x**` | brand keyword |
  | `_x_` | serif italic (Playfair) |
  | `[x]` | white on a brand pill |
  | `~x~` | dark tone (for light backgrounds) |
  | `==x==` | highlight bar |
  | `{x}` | serif in a glass pill |

| comp | props | use |
|---|---|---|
| `BlueText` | `top`, `text`, `times`, `y` (0.72–0.78), `size` 92, `align`, `tone` | **The captions.** One per phrase; replaces `subtitles`. |
| `BlueBig` | `top`, `text`, `sub`, `tone` light/dark, `size` 150, `y` | Headline on a frost scene. |
| `Tiles` | `items: [{icon (emoji or image), label, badge, badgeAt, at}]`, `size` 190, `y` 0.16 | Apps, categories or steps that pop in as they are named. |
| `Checklist` | `items: [{t, at}]`, `x`, `y`, `size`, `tone` | A tick appears as each point is said. |
| `ScreenCard` | `src` (screenshot), `url`, `title`, `chips: [{t, at}]`, `w` | A website or app shown on a light frost. |
| `NumberTitle` | `n`, `top`, `text`, `tone` | Section headers: "1 · thứ nhất…". |
| `FollowCard` | `name`, `handle`, `avatar`/`initial`, `clickAt` | End CTA: a cursor taps "Theo dõi". |

`tone` picks the colours by what is behind the element:
- `video` (default): for footage. White text, keywords near-white with a brand glow.
- `light`: for light walls or frost. Dark text, strong brand keywords.

## Frost overlays (ffmpeg)

Examples:

```json
{"type": "frost", "start": 5.10, "end": 7.34, "mode": "light"}
{"type": "frost", "start": 27.18, "end": 30.18, "window": {"crop": [0.08, 0.27, 0.84, 0.40], "pos": [0.5, 0.71], "width": 0.84, "radius": 44}}
```

- **What it does:** blurs everything below it in the overlay list (`blur` 36) and washes it with a tint.
- **`mode`:** `light` / `blue` / `dark` / `white` / `navy` / `solid` / `none`, or a literal `"0xRRGGBB@a"`.
- **Fades:** `fade` 0.25, or `fade_in` / `fade_out` separately.
- **Order:** put the motion text for that scene **after** the frost in the overlay list.
- **`window`:** split layout. A sharp rounded crop of the frame sits on top of the frost.
- **`grid: true`:** a faint grid plus a vignette, giving the dark "blueprint" scene with `mode: "navy"`.
- **Subtitles** hide during frost.

## Recipe (talking head, 9:16)
1. **Captions:** every phrase becomes a `BlueText`, with `top` as the small first half and `text` as the big punchline half. Mark one keyword per line with `**…**` and the emotional words with `_…_`. Use at most one `[pill]` per 10 s.
2. **Structure:** add one structural element every 8–15 s:
   - `Tiles` when listing things;
   - `Checklist` for pains or benefits;
   - `NumberTitle` for "thứ nhất / thứ hai";
   - `ScreenCard` when talking about a site or tool.
3. **Frost scenes:** 2–4 per minute on the big beats (price, "4 điều", the turn "nhưng yên tâm"), each with a `BlueBig`. Make one of them a `window` split. Keep each frost at least 1 s long.
4. **Sound:** soft UI sounds only:
   - `whoosh_air` 0.12 s before each frost (vol 0.2);
   - `pop_bubble` per tile (0.18);
   - `tech_tick` per tick (0.22);
   - `click` on the FollowCard tap.

   Music sits at 0.12 and is ducked.
5. **Look:** keep the grade light and neutral. Captions at y≈0.75 sit on the chest, under the chin and above TikTok's bottom bar.

## Camera moves (measured on top creators' talking-head edits)
The frame is never still for more than about 4 s. Cut the take into one clip per sentence (`scripts/aroll.py`); contiguous in/out points stay seamless.

| move | numbers | plan.json (per clip) |
|---|---|---|
| Slow push-in ("breathing") | 1.00→1.06–1.08 over 2–4 s | `zoom: "in"`, `zoom_amount` 0.06–0.08 |
| Slow pull-out | 1.08→1.00 over a long stretch | `zoom: "out"` |
| Punch-in jump cut | +15–20 % on a sentence start, next sentence back to 1.0 | `punch: 1.15–1.2` on alternate clips |
| Snap 2× + pull-back | ~2.1× on the face or hand, hold 0.4 s, ease back in 0.45 s, with motion blur | `zooms: [{at:0, to:2.1, in:0, hold:0.4, out:0.45, x, y}]` + sfx `zoom_vacuum` |
| Emphasis | 1.25× for ~1.5 s + shake | `zooms: [{to:1.25, in:0.12, hold:1.4, out:0.4}]`, `shake: {at, dur:0.35, amp:12}` |
| Offset zoom for text | 1.4–1.5×, speaker pushed to one side, text on the empty side | `punch: 1.45` + `focus` to the side |
| Hook open | first frame ~1.3×, snaps to 1.0 in 0.3 s | `zooms: [{at:0, to:1.32, in:0, hold:0.08, out:0.32}]` |

Motion blur is added automatically to fast ramps (|to−1| ≥ 0.3). Force it on or off with `"blur": true/false`. As a rule, use one camera event every 3–6 s, alternate in and out, and put the big ones on keywords.

## VIP pack
Use one VIP effect every 3–5 s at most, always on the word that names it.

### Person-aware layers (`scripts/vipfx.py`)
These use rembg u2net plus a biggest-blob filter. The matte is cached in `<work>/matte/` and costs about 1 s per 30 frames.

| overlay | what it does |
|---|---|
| `{"type":"bg","blur":28}` | Portrait blur behind the speaker. |
| `{"type":"bg","scale":0.88,"radius":46,"color":"0x0B1E5E"}` | The room shrinks into a card while the speaker stays big in front. |
| `{"type":"bg","src":"x.mp4"}` | Replaces the room with an image or video. |
| `{"type":"popout","bg":"0xEEF1F8","window":{"crop":[0.05,0.40,0.90,0.32],"pos":[0.5,0.75],"width":0.84}}` | The speaker sits in a rounded window and their head breaks out above it. **The crop must start below the chin.** `"head": [x, w]` limits what may break out to a column. |
| `{"type":"lens","at":[0.5,0.3],"pos":[0.62,0.36],"size":0.42,"zoom":1.9}` | Magnifying glass. |
| `{"type":"fx","effect":"film" / "vhs" / "bw" / "warm" / "cool"}` | Frame look. `"compare":{"from":0,"to":1}` gives a before/after split (pair it with `CompareHandle`). |
| motion + `"behind": true` | Drawn between the room and the speaker: `GiantCaption` text behind the head, `CodeLayer`. |
| motion + `"fill": "video"` | The comp's shape becomes a window onto the video (text filled with video). |
| `OrbitRing`, `Portal` | The back half goes behind the speaker automatically. |

### Frost extras
- **Rack focus:** `"mode":"none","fade_in":0,"fade_out":0.55,"blur":40` over 0.6 s. Pair it with `FocusBrackets`.
- **Video in a phone or player:** `"mode":"solid"` + `window` + `PhoneFrame` / `VideoCard`.

### Stills
Any motion prop written as `"frame:12.3"` becomes a still of the edit at 12.3 s. This feeds CardStack, Polaroids, PostWall, Newspaper, TearAway and BlowAway.

### VIP motion comps (`src/blue/Vip.tsx`)
Props are `x`, `y` (0–1) plus the ones listed below; times are seconds from the overlay start.
- **Titles:**
  - `KineticTitle` {steps:[{text,at}]}
  - `GiantCaption` {text,top,size}
  - `GravityText` {words[]}
  - `Stamp` {text,color,rotate}
  - `SplitFlap` {text}
  - `Highlighter` {text,mark}
  - `CircleDraw` {x,y,w,h,label}
- **UI:**
  - `Cursor` {from,to,clickAt,label}
  - `FloatButton` {icon,label,tapAt}
  - `IncomingCall` {name,sub}
  - `TypeBar` {text,suggest,mode:search|command}
  - `FileDrop` {name,meta,dropAt}
  - `FocusBrackets` {w,h,label}
  - `ChapterPanel` {items[],current,more}
  - `NotifyStack` {items[]}
  - `ChatBubbles` {items:[{t,me,at,who}]}
  - `CommentsDrop` {items[]}
  - `BarChart` {bars:[{v,label}],title,unit}
  - `EditTimeline` {tracks[]}
  - `JiggleChips` {items[],remove,removeAt}
  - `Eyedropper` {from,to,color}
  - `CompareHandle` {from,to,left,right}
  - `VhsHud` {start}
- **Structure:**
  - `NumberList` {title,items[]} (on the navy grid)
  - `VsCards` {a:{v,label,sub},b:{…}}
  - `Callouts` {items:[{t,x,y,to:[x,y],at}]}
  - `CountUp` {from,to,suffix,top,ring}
  - `IconSlam` {items:[{icon,x,y,at}]}
  - `OrbitIcons`
  - `ScanLines`
- **Stills:**
  - `CardStack`
  - `Polaroids` {items:[{src,label}]}
  - `PostWall` {items[],label} (full-screen)
  - `Newspaper` {name,headline,sub,photo} (full-screen)
- **Transitions:**
  - `TearAway` {src:"frame:t-0.02"}
  - `BlowAway` {src,dir}
  - `InkSpread` {x,y,color,hold}: covers, then reveals; put a navy frost right after it.
  - `TitleCard` {title,sub,theme:cream|navy,iris:[x,y]}
  - `Intertitle` {text,sub}
- **Effects:**
  - `Shockwave` {x,y,color}
  - `Cracks` {x,y} (+ clip `shake`)
  - `OrbitRing` {text,y,rx,ry}
  - `Portal` {x,y,rx,ry}
  - `ScriptPage` {scene,character,paren,line,cps}
  - `CodeLayer` (behind)
  - `PhoneFrame`
  - `VideoCard` {title,total,start}

**Sound pairings** (vol 0.16–0.25):

| moment | sound |
|---|---|
| snap zoom | `zoom_vacuum` |
| ink / navy scene | `whoosh_cinematic` |
| incoming call | `notify` |
| stamp | `bass_hit` |
| cracks | `impact` |
| tear | `swipe` |
| VHS | `glitch` |
| script page | `typing_real` |
| rack focus | `camera_shutter` |
| shockwave | `tech_rise_hit` |

## PRO pack (creator-trend effects, `src/blue/Pro.tsx`)

| comp | props | use |
|---|---|---|
| `OrbitCarousel` | `items` (images or `"frame:t"`), `x`, `y` (head height), `rx`, `ry`, `size` 230, `speed`, `label` | 3D ring of photos around the head. The back half goes behind the speaker automatically. |
| `VisionCarousel` | `items`, `y`, `w`, `h`, `step` 1.1 s, `label` | Cover-flow of big cards, fast-slow change. |
| `BarChartRace` | `frames: [{label, bars: [{label, v}]}]`, `title`, `unit` | Bars grow and swap ranks. |
| `LineGraph` | `series: [{points: []}]`, `labels`, `title` | Line draws on; each value pops in. |
| `ExplodedStack` | `src` (screenshot), `layers` 3, `labels` | 3D layers split with callouts, then merge. |
| `DeviceSplay` | `src`, `y`, `label` | Phone, tablet and laptop pop out showing a site or app. |
| `ConstellationHub` | `center`, `items: [{t, at}]` | Mind map; each node lights up when it is said. |
| `HeadlineWall` | `items` (headlines), `rows` | Sliding headline pills filling the background. Use with `"behind": true`. |
| `DoodleStickers` | `x`, `y` (head), `word` | Hand-drawn crown, stars, hearts, arrow and word, with boiling lines. |

Person outline layer (vipfx), drawn as a hand-drawn line around the speaker: `{"type": "outline", "color": "#FFFFFF", "width": 9, "gap": 16, "boil": 3}`. Pair it with `DoodleStickers`.

## TREND pack (11/2026 creator trends: `src/blue/Trend.tsx`, `scripts/vipfx.py`, `render.py`)

**Motion comps**
| comp | props | use |
|---|---|---|
| `NameTag` | `name`, `role`, `kicker`, `x` 0.08, `y` 0.66, `align` left/right | Character intro card: name rises letter by letter, glowing bar, role pill. Added for you by a `freeze` with `name`. |
| `PriceSlash` | `old`, `new`, `unit`, `label`, `badge`, `slashAt` 0.3, `newAt` 0.75, `y` 0.18 | The old price is struck through in red and drops back; the new gold price slams in with sparks, then a red badge. Shop price reveals. |
| `Receipt` | `title`, `sub`, `items: [{t, v}]`, `total`, `totalLabel`, `stamp`, `w` 0.8, `step` | A paper bill prints out of a slot line by line, ends with the total and an optional stamp ("ĐÃ THANH TOÁN"). Money stories, trade-in maths, price breakdowns. |
| `MapPin` | `place`, `sub`, `src` (your own map screenshot, else a drawn map), `pin` [x, y] on the map, `full`, `zoom` 2.4, `fly` 1.1 | Camera flies into a map, a pin drops with ripples, then an address card pops. Shop address, project location, where a story happened. Never geocode: use a screenshot the user gave or the drawn map. |

Sounds follow the props automatically (strike swipe, slam hit + kaching, printer keys + kaching on the total, pin pop).

**Person-aware and frame layers (vipfx)**
| overlay | what it does |
|---|---|
| `{"type":"freeze","clip":0,"start":4.1,"end":5.6,"name":"Minh Đức Store","role":"419 Điện Biên Phủ","kicker":"SHOP IPHONE","style":"dark"}` | Character intro: white flash, the frame freezes, the room darkens (`style` dark / bw / theme), the speaker becomes a white-outlined sticker (two-model matte, keeps spread arms) and slowly pushes in (`zoom` 1.07). Video only, the voice keeps playing, so place it on a pause (≥ 1 s), a voice-over or before the first word, never mid-sentence. `"at"` picks a different source moment. |
| `{"type":"spotlight","clip":3,"start":0,"end":2.2,"at":[0.5,0.33]}` | The room dims and desaturates, a warm light pool + beam from above lands behind the speaker, who stays lit (`dim` 0.55, `color`, `beam`). The punchline / key promise. |
| `{"type":"loopback","duration":0.5}` | The last 0.5 s cross-fades into the opening frames, so TikTok / Reels replay seamlessly. Write the last line so it leads into the hook. |

**Clip-level**
- **Speed ramp (velocity edit):** `"ramp": "velocity"` on a B-roll clip (fast → slow → fast). Presets: `velocity`, `hero` (normal → slow-mo → out), `rush_in` (rush, land slow), `slowmo_end`; or your own `[[fraction, speed], …]`. It replaces `speed`, mutes the clip, adds motion blur on the fast stretches, and the output length follows from the curve. Never on talking clips.
- **Whip pan:** `"transition": "whip"` or `{"type": "whip", "dir": "right", "duration": 0.36, "amount": 0.6}`. A hard cut becomes a whip: the frame slides out with heavy horizontal motion blur, the next one slides in. It does not shorten the timeline (no overlap) and gets a whoosh. Best between B-roll shots and into a new section; at most one every ~10 s.

**Sound pairings:** freeze `camera` + `hit`, spotlight low `boom`, whip `whoosh` (viral style: flash / thump / dwhoosh).

## TREND pack 2 (the rest of the 11/2026 list)

**Person / frame layers (vipfx)** — faces and the speaker are found automatically (YuNet face detector + matte); pass `at` / `face` only to override.
| overlay | what it does |
|---|---|
| `{"type":"neon","color":"#FF3FD8","cycle":true}` | Glowing neon tube traced around the speaker; `cycle` rotates the hue, `glow` 26, `width` 7, `boil` 0. AI / tech / night looks. |
| `{"type":"clone","copies":[{"dx":-0.3,"scale":0.8,"flip":true},{"dx":0.3,"scale":0.8,"flip":true,"at":0.12}]}` | Copies of the speaker pop in beside them ("tôi 3 năm trước / bây giờ", "3 kiểu khách"). Copies are placed relative to where the speaker stands; a copy with no room on its side moves further out on the other side, smaller. |
| `{"type":"dolly","zoom":1.4}` | Vertigo shot: the room (person inpainted out) pushes in behind a speaker who stays the same size. 1–2 s on a shock line. `mode: "out"` reverses it. |
| `{"type":"facecam","pos":[0.76,0.78],"size":0.36}` | Round face bubble with a white ring over B-roll (put it after the B-roll overlay). Frames the detected face; `from` takes the face from another timeline second (when the B-roll is a clip, not an overlay). |
| `{"type":"impact"}` (0.3–0.4 s) | Anime impact frame: ink black-and-white, flashing negative every 2 frames, speed lines from the face, shake. Punchlines, roasts. |
| `{"type":"dramatic","zoom":1.7}` (~1.2 s) | Meme snap zoom on the face + red vignette + shake, with the `vine_boom` sound. Comedy only. |
| `{"type":"colorize","mode":"fade" \| "wipe","hold":0.4}` | Old black-and-white (sepia, grain) turning into colour. Archive photos, "ngày xưa ↔ bây giờ". |

**Transitions** (clip `"transition"`, a hard cut + a layer, no overlap, auto sound): `"glitch"` (0.24 s RGB split + slice shifts + noise), `"leak"` (0.7 s warm film light leak + soft flash; `{"type":"leak","color":"cool"|"gold"}`), `"zoomthru"` (0.5 s: zoom into the frame and land zoomed-out on the next shot; `"focus":[x,y]`), plus `"whip"`.

**Image clips:** `"parallax": true` (or `{"amount":1.2,"dir":"left"|"right"|"in"}`) turns a still photo into a 2.5D "3D photo": subject cut out, background inpainted, the two layers drift at different speeds. Falls back to the normal Ken Burns when the photo has no clear subject.

**Motion comps (`Trend.tsx`)**
| comp | props | use |
|---|---|---|
| `DecodeText` | `text`, `size` (auto-fits the width), `cps` 22, `box` | Letters scramble and lock in left to right. AI / tech / reveal. |
| `Countdown` | `from` 3, `label` "ĐỢI ĐÃ...", `y` | Big 3-2-1 punching in with a draining ring, a tick per number. Before a reveal. |
| `EvidenceBoard` | `items: [{src, label, x, y, at}]`, `links: [[0,1],…]`, `title` | Full-screen cork board: photos pinned one by one, red strings connect them. HST / Dam Case / news. |
| `Audiogram` | `label`, `y` 0.8, `bars` 34 | Bars that move with the real voice (render fills `levels` from the edit's audio). Podcast / quote clips. |

**Already there:** the progress bar is the ASS overlay `{"type":"progress","color":"#E11D2E"}` (fills over its range; give it the whole video).

## STUDIO LOOK (make a plain room look professionally lit)

Three parts that work together; use them on talking-head footage shot in a flat or dim room.

1. **Colour match between clips** (plan level): `"color_match": true` or `{"ref": 0, "strength": 0.7, "brighten": true}`. Every clip is measured (exposure, white balance, saturation) and matched to the reference clip (default: the longest clip with sound); a dim reference is lifted a little. Gentle by default — Hiếu dislikes heavy grading, so keep `strength` ≤ 0.8. The render log prints each clip's correction.
2. **Fake lighting**: `{"type":"relight","preset":"warm_cafe","side":"left"}` (no times = whole video; or `clip` + `start`/`end` per shot).
   | preset | look |
   |---|---|
   | `bright_luxe` | clean, bright showroom; white rim, soft bloom |
   | `warm_cafe` | room a bit darker and warmer, two warm lamp glows on the wall, orange rim |
   | `cine_dark` | dark, cool shadows, warm key, blue rim, strong vignette |
   | `soft_window` | daylight from one side, airy |

   What it does: grades the room, adds practical lamp glows (`lamps: [[x, y, r], …]`, `lamp_color`), brightens the lit side of the face with a colour-temperatured key (`side`, auto face; texture kept), adds a rim light along the far edge of the speaker, and a luma-only bloom. `strength` 0–1.5 scales everything. Costs one person-matte pass for its range (~1 s per 30 frames).
3. **Props behind the speaker**: `{"type":"prop","src":"plant","pos":[0.13,0.66],"width":0.34}` — `pos` is the bottom-centre of the object (put it on the floor / counter line), `width` a fraction of the frame. Built-ins in `assets/props/`: `plant` (monstera, white pot), `plant_tall` (fiddle-leaf fig, rattan basket), `lamp` (floor lamp, adds a warm wall glow), `shelf` (wall shelf with books), `vase` (table flowers). Any cut-out PNG works (`"src": "my.png"`). Each prop is colour-matched to the room, gets a soft contact shadow, `flip`, and stays behind the speaker (`"behind": false` puts it in front). Render orders props before `relight`, so the lighting falls on them too. Tripod shots only (the prop does not track camera moves).

Typical studio recipe: `color_match` + `relight warm_cafe` + one plant on the side the speaker is not facing + one lamp on the other side.

## TEXT pack (26 premium text effects, `src/blue/Text.tsx`)

All are `{"type": "motion", "comp": NAME, "props": {...}}`; sizes auto-fit the frame width. Never on the face; keep them in empty wall / table areas.

**Text in the room (needs a flag)**
| comp | flag | props | look |
|---|---|---|---|
| `Text3D` | `"behind": true` | `text`, `sub`, `plane` wall/table, `ry`, `y` | Big extruded 3D words standing in the room; the speaker passes in front. |
| `WeaveText` | (automatic) | `text`, `y` 0.56 (chest), `rx`, `ry`, `tilt` | A ribbon of text wrapping around the speaker; the back half goes behind them (RING_COMPS). Keep it below the face. |
| `ProjectText` | `"blend": "overlay"` | `text`, `sub`, `y` | Text projected onto the wall: takes the wall's light and texture, flickers on. Other blend modes: softlight, screen, multiply (`blend_opacity`). Needs a mid-tone wall to show. |
| `GlassText` | `"fill": "glass"` | `text`, `sub`, `y` | Frosted glass letters: the blurred video shows through, bright rim. |
| `MarqueeRows` | `"behind": true` | `text`, `rows` 3, `y`, `speed` | Huge rows (solid / outline) sliding opposite ways behind the speaker. Fashion-ad look. |
| `TrackLabel` | (render tracks) | `text`, `sub`, `track: {"box": [x, y, w, h]}` at the overlay start, `dx`, `dy` | Price / spec card on a leader line that follows a product or hand (template-matching tracker, cached). Pick a box with texture (the phone, the hand), not a plain wall. |
| `FocusText` | (render adds the frost) | `text`, `sub`, `swap` 1.4 | Text sharp over a soft room, then focus pulls to the speaker and the text melts away (rack focus). |
| `BeatText` | (render reads the music) | `text: "A|B|C"`, `beats` (auto from the plan's music via beats.py) | Words punching in on the beat; montages and music-only videos. |
| `RiseText` | — | `text`, `sub`, `edge` (y of the table / box top), `x` | Rises from behind an edge and stays clipped by it. |
| `MirrorText` | — | `text`, `sub`, `y` (the table line) | Standing on a glossy table with a soft reflection. |

**Materials and motion**
| comp | props | look |
|---|---|---|
| `MetalText` | `text`, `sub`, `metal` gold/silver/chrome/red, `sweepAt` | Extruded metal letters with one light sweep. Prices, titles, thumbnails (red-gold brands). |
| `NeonText` | `text`, `color`, `script` | Neon sign switching on with flicker, then humming. |
| `WriteOn` | `text`, `dur` 1.4, `underline` | Handwritten (Dancing Script, Vietnamese) signature drawing itself, then a flourish. Shop name, sign-off. |
| `SliceText` | `text`, `slices` 4 | Bands slide in from alternate sides and lock together. |
| `WeightPulse` | `text` with one `**keyword**` | A caption whose keyword thickens and grows as it is said. Subtle emphasis. |
| `DustText` | `text`, `dustAt` | Text blows away into dust ("hết hàng", "biến mất"). |
| `PunchWord` | `word`, `hold` 0.3, `y` | One word fills the screen, then shrinks into place. Hype only, max once per video. |
| `CubeFlip` | `words[]`, `prefix`, `step` | Words on a 3D cube flipping to the next ("iPhone ở đây RẺ → BỀN → XỊN"). |
| `InkText` | `text`, `script` | Text bleeding out of an ink blot. F&B, heritage, stories. |
| `RaysTitle` | `title`, `sub` | Poster title with light rays behind it. Openings, chapters. |

**Numbers, documents, channels**
| comp | props | look |
|---|---|---|
| `Odometer` | `value`, `unit`, `label`, `dur` 1.3 | Digits roll like a mechanical counter and land left to right, then kaching. Price reveals (premium alternative to CountUp). |
| `SealBadge` | `ring`, `center`, `sub`, `x`, `y`, `size` | Round seal with slowly rotating ring text ("GIẢM GIÁ • HSSV •") and a centre value. |
| `DocLabel` | `place`, `date`, `sub`, `x`, `y` | Documentary place / date line typed out under a drawn rule (HST, Dam Case, Rise & Ruin). |
| `QuoteCard` | `quote`, `who`, `source` | Big quote marks, the quote appearing word by word, who said it. Never invent quotes: only words from the footage or a cited source. |
| `RansomText` | `text`, `cps` | Each letter cut from a different newspaper scrap. Drama / gossip channels. |
| `AIChat` | `prompt`, `answer`, `name` "Claude", `wps` | A prompt bubble, "thinking" dots, then the AI answer streaming word by word with a cursor. AI channel. |
| `DecodeText` / `NameTag` / `PriceSlash` | see the TREND packs | |

Picks by channel: shop → MetalText, Odometer, SealBadge, CubeFlip, TrackLabel, MirrorText; HST / documentaries → DocLabel, QuoteCard, FocusText, RaysTitle, InkText; MH / drama → RansomText, PunchWord, DustText; AI channel → AIChat, NeonText, GlassText, DecodeText; premium brand → Text3D behind, WeaveText, WriteOn, GlassText.

## HUD pack (agency motion-graphics chapters, `src/blue/Hud.tsx`)

Measured on a top "xây kênh TikTok" agency reel (11/2026): the talking head stops for 10–18 s and the voice runs over full-screen graphics. Both comps are **full-screen and opaque** (the speaker is hidden, the voice keeps playing), so put them on a voice-over stretch, never on a line where the face matters, and use **one of each per video at most**.

| comp | props | use |
|---|---|---|
| `HudChapter` | `scenes: [{at, title, title2, box, kicker, script, step, chapter, card, media, chips, tone, sub}]`, `brand`, `footer`, `tc` (timecode start, s), `marquee`, `size` 128 | A run of scenes inside one HUD frame: corner brackets, `brand •` top-left, a running timecode top-right, the chapter label bottom-left (`"03 — Lộ trình"`), the footer bottom-right (`"Xây kênh 2026"`). Each title's letters fly in scattered (spun in 3D, blurred) and lock into place, then fly away into the next scene while the background cross-fades. `title2` is in the brand colour, `box: true` wipes a brand box behind it. `step: "01/04"` adds a "BƯỚC 01 / 04" pill and a progress bar. `card`: `browser` (screenshot in a browser window), `phone`, `rec` (B-roll with REC dot, timecode, focus square and `sub` label), `plain`, `clap` (clapperboard that snaps shut, `sub` lines with `\n`), `target` (crosshair rings), `none` (big centred title). `media` = image **or video** (B-roll plays muted from the moment its card lands). `chips` = floating pills around the card. `tone`: `light` / `brand` / `dark`, default rotation light → brand → light → dark. Process / roadmap lists ("từ bước nghiên cứu thị trường, insight khách hàng, …"), service packages, "quy trình 4 bước". |
| `NeonTunnel` | `items: [{src, at}]` (B-roll / screenshots), `color` '#FF5A1F', `logo`, `script` ("Vậy"), `text` (lines with `\n`), `title` ("DO VIDEO QUÁ ĐẸP?"), `titleAt`, `fly` 0.9 | Dark neon tunnel: perspective lines rush past, zig-zag light pulses, a phone flies in from the vanishing point and flips to the next clip on each `at`. Logo glow + serif script word | question on top, the big title's letters assemble on `titleAt`. The neon keeps its own colour (contrast with any brand). The hook question ("làm thế nào mà…?") right after the opening proof. |

The edit brain places them by itself: `HudChapter` on the first process / roadmap list with ≥ 3 steps (it joins the Whisper pieces of one long list, splits each step into two lines, e.g. "NGHIÊN CỨU / THỊ TRƯỜNG", and adds a "LỘ TRÌNH / N BƯỚC" intro when the sentence has a lead-in); `NeonTunnel` on an early question, only when `--broll` gives ≥ 2 files, and a short second question right after becomes its big title. Captions are skipped under both. Without `--broll` the HUD scenes use `card: "none"`; with it, videos go into `rec` cards and images into `browser` cards. Ask the user for real B-roll (team at work, channel screenshots, results): AI pictures look fake in these cards.

Sounds follow the props automatically (a whoosh per scene, a click when a card lands, a pop per chip; neon: riser + whoosh, a swipe per clip swap, a hit on the title).

```json
{"type": "motion", "comp": "HudChapter", "start": 34.4, "end": 49.0, "props": {"brand": "Viral Network", "footer": "Xây kênh 2026", "tc": 34.4,
 "marquee": "CONTENT ✦ INSIGHT ✦ KẾ HOẠCH", "scenes": [
  {"at": 0, "kicker": "VÀ ĐÓ LÀ LÝ DO", "title": "GÓI XÂY", "title2": "KÊNH", "box": true, "chapter": "01 — Giới thiệu"},
  {"at": 2.2, "kicker": "CHÚNG MÌNH SẼ", "title": "ĐỒNG HÀNH", "card": "rec", "media": "broll/team.mp4", "sub": "KOC / KOL", "chips": ["TEAM QUAY"], "tone": "brand"},
  {"at": 4.6, "step": "01/04", "title": "NGHIÊN CỨU", "title2": "THỊ TRƯỜNG", "card": "browser", "media": "broll/kenh.png", "chapter": "03 — Lộ trình"},
  {"at": 8.6, "kicker": "SẢN XUẤT", "title": "HÌNH ẢNH", "title2": "CHỈN CHU", "card": "clap", "sub": "PROD — VIRAL NETWORK\nSCENE 05 · TAKE 03", "tone": "dark"},
  {"at": 10.6, "script": "truyền thông", "title": "ĐÚNG TỆP", "title2": "KHÁCH HÀNG", "card": "target"}]}}
```

## ESTATE pack (real estate on real data: `scripts/geo.py` + `src/blue/Estate.tsx`)

**Real map, real numbers.** Never draw a made-up map or guess a distance for a real project: build it with `geo.py`.

1. Write `spec.json` (see the docstring of `geo.py`): `site` as `{"osm": "Vinhomes Làng Vân, Đà Nẵng"}` (boundary from OpenStreetMap, if mapped), `{"ring": [[lat, lon], …]}` (from the user / Google Maps), or `{"vn2000": {"meridian": 107.75, "points": [[X, Y], …]}}` (the coordinate table on the sổ đỏ, VN-2000 TM3, X = northing; province meridians: Đà Nẵng 107.75, Quảng Nam 107.75, HCM 105.75, Hà Nội 105.0, Bình Dương 105.75, Khánh Hòa 108.25 — check the sổ đỏ). `pois` with `"route": true` get the real driving route, km and minutes (OSRM). `levels` [10, 12, 14, 16] for a city → site fly-in; [14, 16, 18] for a single plot. `camera` keys sketch the moves; each comp overrides them.
2. `python -X utf8 scripts/geo.py build spec.json -o edited/geo` → `geomap.json` + one satellite mosaic per zoom level (tiles cached in `.cache/tiles`). Read its report: area, edges, km, minutes.
3. Put `geomap.json`'s keys into a `GeoMap` overlay's `props` (one GeoMap per shot, each with its own `camera`, in seconds from the overlay start; build the u/v of extra camera targets with `geo.merc(lat, lon)`).

| comp | props | use |
|---|---|---|
| `GeoMap` | geomap.json keys + `camera` [{t, u, v, z, tilt, rot}], `site_at`, `site_draw` 2, `site_label`, `site_sub`, `routes` [{name, at, dur 1.6, dx, dy}], `pins_at`, `rings_at`, `color` gold, `fill`, `compass` | Satellite fly-in with Google-Earth tilt (haze on the horizon), the boundary draws with a glowing running light then fills, road routes draw to each amenity and a card pops "✈ Sân bay Đà Nẵng · 22,2 km · ~24 phút", km rings grow from the site, compass turns with the map, the imagery credit stays at the bottom. `dx` / `dy` nudge a card that overlaps another. |
| `Building3D` | `buildings` [{pts (footprint in m, from the drawing), floors, fh 3.3, base, color, at}], `style` white / glass / wire, `yaw0` → `yaw1` (orbit), `pitch` 26, `zoom`, `dark`, `title`, `sub` | The footprint outline draws, then floors rise one by one with slabs and a window per bay, shadow on a grid, the camera orbits. Several blocks = a 3D masterplan (villas + tower). Label it "mô phỏng / minh hoạ" unless the user gave the real drawing. |
| `FloorPlan2D` | `rooms` [{name, pts (m), color}], `doors` / `windows` [{pts: [[x1,y1],[x2,y2]]}] (on a wall; a door swings from pts[0]), `extrude_at` (s; null keeps it 2D), `wall_h` 2.8, `yaw`, `dims`, `title`, `sub`, `dark` | Walls draw on, rooms fill with their name + m² (computed from the polygon, text shrinks in narrow rooms), doors cut a gap with a swing arc, windows show as blue double lines, overall dimension lines, then the camera tilts into 3D: walls rise, doors keep a lintel, windows get a sill + glass (dollhouse). The plan auto-fits the frame. Make the props from a photo of the drawing with `floorplan.py` (below). |

**Reading a drawing (bản vẽ) — `scripts/floorplan.py`.** The user sends a photo / scan / screenshot of the floor plan:
1. Inside Claude Code (0 credit): look at the image yourself and write `trace.json` in **pixels** (schema in the script's docstring): one dimension line as the scale (`"scale": {"px": [[x1,y1],[x2,y2]], "m": 5.0}`), every room as a polygon on the wall centre lines with the m² written inside (`label_area`), doors and windows as two points on their wall. Zoom into the image (crop) when lines are small.
   Automatic instead (KIE.AI, ~1–2 credits, GPT-6.1 Sol → Claude fallback): `floorplan.py --auto plan.jpg --env <.env with KIE_API_KEY>`.
2. `python -X utf8 scripts/floorplan.py trace.json -o rooms.json --preview check.jpg [--title …] [--sub …]`. It converts to metres, snaps wall lines that are within 15 cm onto one line, snaps openings onto their wall, re-calibrates the scale from the written areas when the dimension reading was off by > 2 %, and prints every room as `OK / LỆCH  computed m² / written m²` plus overlaps and unassigned space.
3. **Open `check.jpg`** (the result drawn over the drawing: rooms tinted, doors red, windows blue). Fix any `LỆCH` room or misplaced opening in trace.json and run again. Never put a plan on screen that you have not checked this way.
4. Use `rooms.json` as the `FloorPlan2D` props (add `extrude_at`, `yaw`). Several floors = several FloorPlan2D shots ("Tầng 1", "Tầng 2", …).

Rules: distances and times on screen say "khoảng / ~" and the video carries a small "ước tính theo OSRM / OpenStreetMap" note; the imagery credit never leaves the frame; a site boundary taken from OpenStreetMap is labelled as such (it may be a construction zone, not the legal plot); numbers about a real project (area, investment, dates) come from news / official pages and the sources go on the end card. For a real developer's project, add "video minh hoạ, không phải quảng cáo của chủ đầu tư" unless the user is that developer. Imagery: `"source": "esri"` (free with the credit) or `"mapbox"` with `MAPBOX_TOKEN` for commercial work; never Google tiles. Sounds follow the props (fly-in whoosh, sparkle when the boundary closes, pop per route card; pen + whoosh for the floor plan; pops as blocks rise).

## Files
- **`motion/`:** the Remotion 4.0.541 project.
  - `src/blue/theme.ts`: tokens and theme mapping.
  - `Rich.tsx`: text markup.
  - `Blue.tsx` / `Vip.tsx` / `Pro.tsx` / `Trend.tsx` / `Text.tsx`: the comps.
  - `Root.tsx`: the registry.
  - Studio: `cd motion && npx remotion studio src/index.ts`.
- **`motion/render_motion.py COMP '<props json>' --duration 3 [--still 1.5 -o x.png]`:** renders one item. Use stills to check a design.
- **Adding a comp:** write it with colours wrapped in `T('…')`, then register the name in `Root.tsx`, in `COMPS` in `render_motion.py`, and in `MOTION_COMPS` in `editor/app.js`.
- **VIP Editor preview limits:**
  - It previews motion comps.
  - `bg` / `popout` / `lens` / `fx` / `freeze` / `spotlight` / `loopback` / `neon` / `clone` / `dolly` / `facecam` / `impact` / `dramatic` / `colorize` / `relight` / `prop`, colour match, parallax, the trend transitions and `behind` only appear in "Xuất nháp".
  - Frost tints in the preview stay blue; the export uses the theme.
