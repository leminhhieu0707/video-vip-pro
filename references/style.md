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

## Files
- **`motion/`:** the Remotion 4.0.541 project.
  - `src/blue/theme.ts`: tokens and theme mapping.
  - `Rich.tsx`: text markup.
  - `Blue.tsx` / `Vip.tsx` / `Pro.tsx` / `Trend.tsx`: the comps.
  - `Root.tsx`: the registry.
  - Studio: `cd motion && npx remotion studio src/index.ts`.
- **`motion/render_motion.py COMP '<props json>' --duration 3 [--still 1.5 -o x.png]`:** renders one item. Use stills to check a design.
- **Adding a comp:** write it with colours wrapped in `T('…')`, then register the name in `Root.tsx`, in `COMPS` in `render_motion.py`, and in `MOTION_COMPS` in `editor/app.js`.
- **VIP Editor preview limits:**
  - It previews motion comps.
  - `bg` / `popout` / `lens` / `fx` / `freeze` / `spotlight` / `loopback`, whip transitions and `behind` only appear in "Xuất nháp".
  - Frost tints in the preview stay blue; the export uses the theme.
