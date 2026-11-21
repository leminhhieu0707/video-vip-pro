# Edit brain — every video gets its own idea (no fixed template)

The worst VIP edit is the same sequence on every video: hook zoom → frost → tiles → checklist → orbit ring at the end. Viewers notice after two videos. Before writing a single overlay, do the **creative pass** below and write its answers as a comment block at the top of `build_vip.py`.

## 1. Creative pass (5 answers, 2 minutes)
1. **What is this video really about?** One sentence. Who watches it? What should they feel at second 3, at the middle, and at the end?
2. **Edit style.** Pick ONE style from the table, or blend two. Choose the one that fits the content, not the one used last time.
3. **Three motifs.** Pick 3 signature effects that will carry this video. Repeat each motif 2–3 times in variations; that repetition is what makes an edit feel designed. Everything else in the video is support.
4. **Rhythm map.** Mark where the video breathes (slow, clean shot, music up) and where it hits (cut on beat, layered sound, big effect). Aim for 3–4 peaks per minute, with valleys between them.
5. **Surprise.** One moment nobody expects. Examples:
   - text that lives behind the person;
   - a freeze frame with a doodle outline;
   - a reversed zoom;
   - a silent beat right before the reveal.

## 2. Edit styles (pick by content, rotate between videos)
| style | when | motifs (pick 3) | camera | sound |
|---|---|---|---|---|
| **Calm Premium** | sharing knowledge, AI/tech, finance, real estate | two-tier captions, frost scenes, Tiles / Checklist, GiantCaption behind | push 6 %, punch 1.15, one snap per minute | soft whoosh, pop, ding, light boom |
| **Hype Trend** | shop sales, phones, gym, promos | Stamp, CountUp, VsCards, Shockwave, snap zooms, IconSlam, PriceSlash, Receipt, whip pans, velocity B-roll | snap 2× every 8–10 s, shake on hits | boom + whoosh layered, hit, cash, riser before the price |
| **Creator Showcase** (the "10 effects" reel look) | tool or feature lists, tutorials, "N tips" | OrbitCarousel, VisionCarousel, BarChartRace / LineGraph, DeviceSplay, ConstellationHub, labelled cards "01 · …" | static or gentle; the graphics move, not the camera | boom on each card entrance, sparkle on reveals, pop on list items |
| **Doodle Vlog** | lifestyle, beauty, spa, fashion, kids | outline + DoodleStickers, Polaroids, KineticTitle, Highlighter | punch-ins on reactions | sparkle, pop, cartoon (light), laugh only for real jokes |
| **News Wall** | news, commentary, drama, trends | HeadlineWall behind the person, Newspaper, Stamp, NotifyStack, CommentsDrop, bw / vhs for the past, freeze + NameTag for each person, MapPin for where it happened | snap on reveals | boom, glitch, camera, typing |
| **Cinematic Story** | food, travel, hospitality, brand films | TitleCard chapters, Polaroids, SplitFlap places, film / warm looks, InkSpread into one big number, hero speed ramps, MapPin | slow push / pull on every shot, cut on the beat | music-led; whoosh on chapter changes; sparkle on the dish or hero moment |
| **Data Explainer** | statistics, comparisons, results | BarChartRace, LineGraph, CountUp, VsCards, ExplodedStack | static | ding on numbers, riser into the key stat |

**TREND pack quick picks (11/2026):** character intro = `freeze` with `name` on the first pause; the key promise = `spotlight`; price drop = `PriceSlash`; "how the money adds up" = `Receipt`; address / location = `MapPin`; B-roll energy = `"ramp"` + `"transition": "whip"`; short-form ending = `loopback`. Pack 2: AI / tech = `neon`, `DecodeText`, `glitch`; "3 kiểu người" = `clone`; shock line = `dolly`; punchline / roast = `impact` or `dramatic` (comedy only); B-roll with the speaker still visible = `facecam`; before a reveal = `Countdown`; archive photos = `colorize` + `"parallax"`; investigations = `EvidenceBoard`; podcast quotes = `Audiogram`; chapter changes = `leak` / `zoomthru`. Use one or two per video, not all of them.

**Text pack:** at most one "hero" text effect per 15–20 s (Text3D, WeaveText, MetalText, GlassText, PunchWord, RaysTitle); everything else stays the two-tier captions. Match the channel: shop → MetalText / Odometer / SealBadge / CubeFlip / TrackLabel; documentaries → DocLabel / QuoteCard / FocusText; drama → RansomText / DustText; AI → AIChat / NeonText / GlassText. Never stack two text effects at once.

**Studio Look:** when the room looks flat, dim or empty, add `"color_match": true`, one `relight` preset that suits the brand (shop / luxury → `bright_luxe`, café / F&B / lifestyle → `warm_cafe`, story / drama channels → `cine_dark`, education / spa → `soft_window`) and one or two props in empty corners. Keep the speaker's skin natural; check a still before the full render.

## 3. Variety rules (check before rendering)
- **Repetition:**
  - The same effect never appears twice in a row.
  - An effect appears at most 3 times per minute, unless it is one of your motifs.
  - Never open two videos in a row with the same hook effect; check the previous `build_vip.py` in the channel folder.
- **Placement and camera:**
  - Effects land on the word that names them, never on a fixed interval.
  - Alternate the camera: push / pull / punch / static. Never use three of the same move in a row.
- **Layout:** do not reuse the same screen zone for every graphic. Move graphics between the top band, the side opposite the face, and full-screen scenes.
- **Ending.** The last 3 seconds must feel like an ending: a final motif hit plus the CTA. It should not be "the same overlay again".

## 4a. Sound brain: right sound, right place (most important)
A sound is there because the words or the picture ask for it. Three layers, in this order:

1. **Effect sounds**, picture-led, from `sound.py`: each visible effect gets its own meaningful sound (pen for a drawn line, page for a news wall, hit for a stamp…).
2. **Story sounds**, word-led, from `scripts/sound_brain.py`:

   | spoken | sound |
   |---|---|
   | money or prices | `kaching` on the number |
   | "giòn" | `crunch` |
   | "chụp" | `camera` |
   | "gõ / lệnh" | `keyboard` |
   | "bấm" | `mouse` |
   | "lật / kịch bản" | `page` |
   | "điện thoại" | `phone` |
   | "xong" | `ding` |
   | "đẹp / xịn" | `sparkle` |
   | "nhanh" | `whoosh` |
   | surprise | `riser` 1.1 s before, then `boom` on the word |
   | fail / chê | meme (comedy only) |
   | "thứ nhất / tiếp theo / nhưng" | one whoosh (section change) |

   Turn it on with `"sound_design": {"style": "trend", "brain": {"transcripts": ["voice.transcript.json"], "offset": 0.5, "comedy": false}}`, or run `python sound_brain.py voice.transcript.json --offset 0.5` to read the suggestions and their reasons first.
3. **Your judgement on top.** Read the suggestion list and delete anything that does not add meaning. Add silence before a punchline. A meme only works on a real joke.

**Limits:**
- one meaning = one sound;
- at least 0.45 s between sounds;
- at most 4 sounds per 10 s;
- loud stingers (boom, meme) at most every 6 s;
- at most 3 memes per video;
- never double a sound that an effect already has.

## 4. Sound design (trend creator style)
Turn it on with `"sound_design": "trend"`. The automatic layer then:
- adds sounds to every effect (`scripts/sound.py` SOUND_MAP);
- rotates variants inside each family;
- de-clutters, so the same family is never within 0.3 s and there are at most 3 sounds per 0.5 s.

On top of that, add the sounds that carry the story by hand:
- **Riser before a reveal:** `{"sfx": "riser", "at": reveal - 1.2}`, then `["whoosh", "boom"]` exactly on the reveal.
- **Silence is a sound:** duck the music to 0 for 0.4 s right before the punchline (`music` ducking + a gap in sfx).
- **Hits sit on the beat:** snap SFX and cuts to `beats.py` times when there is music.
- **Price / number:** `riser`, then `ding`, then `cash` for sales; plain `ding` for information.
- **Comedy only when it is funny:** `laugh` and `cartoon` only on a real joke, at most twice per video.
- **Volumes:** these are the numbers written in plans (UI 0.14–0.2, impacts 0.18–0.24, risers 0.1–0.14). With a sound design on, render.py multiplies them by `sfx_gain` (default 6) and ducks effects only gently under speech (`sfx_duck` threshold 0.06, ratio 2). The aim is the creator mix: effects about 7 dB under the voice on average, and big hits above it.
- **Check that you can hear them.** Render an SFX-only copy (`"audio": {"original_volume": 0, "normalize": null}`) and a voice-only copy, then compare 100 ms RMS. If the effects sit 12 dB or more under the voice, nobody will hear them.

**Viral style** (the tech sound design of top short-form editors, e.g. "Viral Editor SFX Pack"-type channels): `"sound_design": {"style": "viral", "cuts": true, "captions": true}`. This style swaps every effect to a synthesized tech set from `make_sfx_viral.py`, which is always installed and safe to ship in apps:
- **charge-up:** a camera-flash whine that lands on snap zooms and giant text;
- **data:** blips for UI, lists and numbers;
- **clicks:** on keyword captions and buttons;
- **stutter:** on headline walls and flip boards;
- **flash:** on stills and focus;
- **cutout:** snap on person layers;
- **digital whoosh:** on cuts;
- **sub thump:** under hits.

Use it for tech, AI, tutorials, creator content and fast promos. For food, lifestyle and hospitality, keep `"trend"`.

**Lesson (Hiếu, 20/11): sound must follow the picture, not a grid.**
- A click on every caption and a whoosh on every picture change sounds cheap ("lỏ"), whatever the sound.
- Give each visible effect its own meaningful sound:
  - pen for a drawn line;
  - paper or page for a tear or a news wall;
  - hit for a stamp;
  - glitch for cracks or VHS;
  - kaching for money;
  - whoosh + boom only for the big reveals.
- Put a whoosh on section changes only.
- Prefer recorded pack sounds (get_sfx.py). The synthesized viral set is a fallback for apps, not the first choice.
- Keep `"captions"` / `"cuts"` off unless the edit is very fast-paced.

Denser creator mix: `"sound_design": {"style": "trend", "cuts": true, "captions": true}` adds a soft whoosh on every cut (`cut_volume` 0.09) and a light pop on captions that have a **keyword**.
Food / restaurant videos: put ASMR on the exact words, e.g. `crunch` on "giòn", `pour` on "nước chấm" or "canh", plus `["whoosh", "camera"]` on each dish card. Grade them with `"grade": "food"`.
Never put motion blur on the very first frame of a video: use `"blur": false` on the hook zoom, otherwise it reads as a glitch.
Text "behind" the speaker needs a plain background behind the head. Glowing logos and bright signs get matted as foreground and cut through the text, so skip `behind` on those shots.

## 5. Smooth transitions and one voice
- **Transitions without drift.** With `"keep_timing": true`, a clip's `"transition": {"type": "zoomin" | "fade" | "smoothleft" | "hblur" | "smoothup", "duration": 0.25–0.4}` borrows handle frames, so the voice-over and overlays stay in sync. Use them like this:
  - `zoomin` at section changes;
  - soft types rotating on normal cuts;
  - hard cuts on shots shorter than 1 s (beat cuts keep the energy);
  - `fade` 0.5 into the end card.
- **One voice.** When the presenter's on-camera takes and a separate voice-over are both in the video, run `scripts/voice_match.py --ref vo.wav --out-dir voice vo.wav take1.wav take2.wav` and use the `*_matched.wav` files as `voiceover` items (`in`/`out` = the clip's in/out, `start` = the clip's timeline start, with the clip muted). This gives:
  - the same tone, via auto EQ against the voice-over;
  - the same loudness (−16 LUFS);
  - the same compression and a shared light room.

  Lip sync is unchanged. Denoise each file first.

**User library first.** Sounds the user imported with `scripts/import_sfx.py <folder>` go to `assets/sfx/mine` (git-ignored, local only). `sound.pick` uses them before the pack and the synthesized sets, and `"meme:5"` picks variant 5 of the user's own `meme` family. Meme stingers (what?, vine boom, woah, sus) go only on a real punchline or surprise, at most 2–3 per video.

Families (from `get_sfx.py`): whoosh, boom, hit, pop, click, sparkle, bling, ding, riser, glitch, camera, typing, cash, drumroll, swipe, game, laugh, applause, cartoon, crunch, pour (food ASMR), page (lật trang), paper, mouse, keyboard, phone, kaching, pen (bút viết). Use `"boom:3"` for one fixed variant.

## 5. Write the storyboard first
In `build_vip.py`, before the code, write a table: one row per sentence, with columns **time | words | visual | effect | camera | sound**. Then implement exactly that table. A builder that is a list of `motion(...)` calls without a storyboard almost always ends up formulaic.
