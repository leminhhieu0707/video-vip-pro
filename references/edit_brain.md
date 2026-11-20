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
| **Hype Trend** | shop sales, phones, gym, promos | Stamp, CountUp, VsCards, Shockwave, snap zooms, IconSlam | snap 2× every 8–10 s, shake on hits | boom + whoosh layered, hit, cash, riser before the price |
| **Creator Showcase** (the "10 effects" reel look) | tool or feature lists, tutorials, "N tips" | OrbitCarousel, VisionCarousel, BarChartRace / LineGraph, DeviceSplay, ConstellationHub, labelled cards "01 · …" | static or gentle; the graphics move, not the camera | boom on each card entrance, sparkle on reveals, pop on list items |
| **Doodle Vlog** | lifestyle, beauty, spa, fashion, kids | outline + DoodleStickers, Polaroids, KineticTitle, Highlighter | punch-ins on reactions | sparkle, pop, cartoon (light), laugh only for real jokes |
| **News Wall** | news, commentary, drama, trends | HeadlineWall behind the person, Newspaper, Stamp, NotifyStack, CommentsDrop, bw / vhs for the past | snap on reveals | boom, glitch, camera, typing |
| **Cinematic Story** | food, travel, hospitality, brand films | TitleCard chapters, Polaroids, SplitFlap places, film / warm looks, InkSpread into one big number | slow push / pull on every shot, cut on the beat | music-led; whoosh on chapter changes; sparkle on the dish or hero moment |
| **Data Explainer** | statistics, comparisons, results | BarChartRace, LineGraph, CountUp, VsCards, ExplodedStack | static | ding on numbers, riser into the key stat |

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
- **Volumes:** UI 0.14–0.2, impacts 0.18–0.24, risers 0.1–0.14. Speech always stays on top.

Families (from `get_sfx.py`): whoosh, boom, hit, pop, click, sparkle, bling, ding, riser, glitch, camera, typing, cash, drumroll, swipe, game, laugh, applause, cartoon. Use `"boom:3"` for one fixed variant.

## 5. Write the storyboard first
In `build_vip.py`, before the code, write a table: one row per sentence, with columns **time | words | visual | effect | camera | sound**. Then implement exactly that table. A builder that is a list of `motion(...)` calls without a storyboard almost always ends up formulaic.
