# Genre recipes

Pick the recipe closest to the request and adapt it. They are starting points, not rules. When the user shows a reference video they edited themselves, match **their** style over these defaults: the colors of their labels, where text sits, the subtitle look, and the pacing.

## Contents
- A. Sales / product ad (phones, cosmetics, shop promos)
- B. Real estate tour (house / land / apartment)
- C. Talking head: news commentary, tips, storytelling
- D. Vlog / travel / event montage synced to music
- E. Photo slideshow (memories, product catalog, listings)
- F. Tutorial / screen recording / horizontal YouTube
- G. Podcast or livestream → vertical clips
- H. Multi-format export and batch variants
- I. News commentary from an article link (AI voice + motion graphics)

---

## A. Sales / product ad
**Shape:** a 0–3 s hook with the biggest offer → products with prices → trust points (warranty, genuine, returns) → gifts and bonuses → call to action with the address and phone number. Total 30–60 s.
- `transcribe` → proofread the prices, model names, and the brand → `cut_silence` with `--pad 0.08 --min-gap 0.25` for a tight pace.
- Put a **label** on every price the moment it is spoken. Find the word in the transcript, start the label 0.1 s before it, and keep it until the next product. Place it beside the product in hand, not over the face. Check the contact sheet for where the hand is.
- Trust points get a **badge**. The headline offer gets a **title** with `highlight` and `pulse`.
- Subtitles use `tiktok` or `box`, with `keywords` coloring numbers and words like "miễn phí" or "tặng".
- End on a storefront shot or photo with the address and phone number as `text`, and the logo `image` throughout.
- Music: upbeat, `volume` 0.12–0.18, `duck: true`.

## B. Real estate tour
**Shape:** a hook (best shot plus price and location) → exterior → living room → kitchen → bedrooms → view and amenities → specs → contact.
- Clips are often AI-generated or drone footage with no speech. Use `original_volume` 0 or 0.3, and music at 0.5–0.7 with `duck: false`, or a voiceover with `duck: true`.
- Cut transitions on beats: run `beats.py` on the music and use `downbeats` as clip boundaries. Use `fade`, `smoothleft`, or `slideleft` at 0.3–0.5 s.
- Spec **labels**: `{"title":"Diện tích","text":"5 x 20m"}`, `{"title":"Giá","text":"3,2 tỷ"}`, plus "Pháp lý: Sổ hồng riêng".
- Location **title** at the start: "Mặt tiền đường 10m" with a highlight on "Q.7 - TP.HCM".
- Exterior photos: `zoom: "in"` at 0.08–0.12. Interior: `zoom: "out"`. Keep color grades subtle (`saturation` 1.1, `contrast` 1.05).
- Contact card at the end: an agent photo as `image` with `radius`, plus name and phone as `text`.

## C. Talking head: news commentary, tips, storytelling
- `transcribe` → proofread → `cut_silence` (`--min-gap 0.3`). Remove retakes and false starts with `--remove a-b`. Find them by reading the transcript for repeated sentences.
- Subtitles carry this genre: `tiktok` or `news` style, 3–4 words per line, `keywords` for names and numbers.
- Every 3–5 s, add something new on screen: a **title** for each key point, B-roll or a news-photo `image` (width 0.8, pos `upper`), or a camera change. Alternate jump-cut pieces between `"punch": 1.0` and `"punch": 1.15` to fake a second angle, or use `"zoom": "in"` with `"zoom_amount": 0.06` for a slow push on an emotional line.
- Hook in the first 2 s: a big **title** stating the claim or question.
- Pairs well with the `kenh-binh-luan-tin-tuc` skill for writing the script first.

## D. Vlog / travel / event montage synced to music
- `analyze.py` on each source clip. Read the sheets to pick the best 1–3 s moments: movement, faces, scenery.
- `beats.py music.mp3 --every 2` → cut points. Clip *i* lasts `beats[i+1] - beats[i]`. Use the strongest hits (`strong`) for flashes (`fadewhite` transitions, 0.15 s) or title pops.
- `original_volume` 0–0.2, music 0.7–0.9, `duck: false`. Add `speed` 1.1–1.3 for energy and 0.5 for a slow-motion moment.
- Minimal text: a location and date `title` at the start, `clean` subtitles only if someone talks.

## E. Photo slideshow
- Each photo is a clip with `duration` 2–4 s. Alternate `zoom` in and out. Use `fit: "blur"` for photos that don't match the canvas aspect.
- Transitions: `fade` or `dissolve` at 0.6 s for a soft feel, or `slideleft` for a catalog.
- Captions per photo use `text` with `clip: N`. Add music, and optionally sync durations to beats.

## F. Tutorial / screen recording / horizontal YouTube
- Canvas `16:9`. Use `clean` subtitles at `pos: "bottom"` with 7–8 words per line.
- Cut dead air with `cut_silence`. Speed up boring parts with `speed` 2–4 and `mute: true`.
- Use **badge** for step numbers ("Bước 1") and **text** with `bg` for callouts near the relevant UI. Find the location in the contact sheet.
- Webcam bubble: a `video` overlay with `radius` at `pos` `bottom-right`, `width` 0.22.

## G. Podcast / livestream → vertical clips
- Transcribe the long source once, then read it to find 30–60 s self-contained moments: a strong opinion, a story, a punchline. Propose 3–5 to the user with timestamps and a one-line hook each.
- Each clip: `fit: "crop"` with `focus` on the speaker. Use `analyze.py --frame` to see where they sit. Alternatively, `blur` keeps the whole frame.
- A hook **title** for the first 2–3 s, `tiktok` subtitles, and a progress feel through fast cuts.

## H. Multi-format and variants
- **Vertical source into a 16:9 canvas:** use `fit: "blur"`. The real video occupies the centre column, from x ≈ 0.34 to 0.66 of the width, and the blurred sides are free space. Put labels at x ≈ 0.17 and titles or contact boxes at x ≈ 0.83, so the presenter is never covered. Use 7–8 subtitle words per line at `pos: "bottom"`, which is the default for landscape.
- The same plan for several platforms: `render.py plan.json --aspect 16:9`, `--aspect 1:1`, `--aspect 4:5`. Segments re-normalize automatically. Check the contact sheet of each format, because labels positioned beside a person may need different `pos` in 16:9. Make a copy of the plan for that format if so.
- Price or offer variants: copy the plan, change the label text and output name, and re-render. Cached segments make each extra variant take seconds.

## I. News commentary from an article link
**Law first (Vietnam, Decree 174/2026, from 1/7/2026).** Reposting, screenshotting, re-reading or AI-summarising a news article into a video without the publisher's permission can be fined 20–30M VND, and crediting the source does not make it legal. So:
- Build the video as **original commentary**. Take only the *facts* (who, what, when, numbers). Write a new script in your own words and add the channel's own value: analysis, advice, what it means for the viewer. Never read or closely paraphrase the article.
- Use **at most one short direct quote**, in quotation marks, attributed on screen ("— TT Dự báo KTTV quốc gia, theo Dân trí").
- **Never use the article's photos or video, or screenshots of them.** Visuals are `make_bg.py` motion backgrounds, `emoji_png.py` icons, price/data cards, the user's own footage, or AI images labelled "Ảnh minh họa" (never fake photos of the real event).
- Show the source: a "Theo [Báo] • date" card at the start, a small persistent "Nguồn: …" line, and a sources card at the end. Write `caption.txt` with the original link and sources.
- Tell the user that this lowers the risk but does not remove it. For monetised channels, recommend permission or partnership with the publisher.

**Pipeline:**
1. Fetch the article and extract facts. Cross-check with a second source when one exists.
2. Write `script.txt`, one spoken line per scene, numbers written as spoken.
3. Run `tts.py` to get the voice and its timings.
4. Run `make_bg.py` (theme matched to the topic), `emoji_png.py` for the icons, and `make_music.py` if there is no music.
5. Write `build_plan.py`. Each scene's cards and icons appear at the word that introduces them (`T(word)` lookup on the tts transcript; normalise Unicode and match the first token, since the voice can merge "tối 4/10" into one token). Use clip 0 = background (muted), and voiceover = tts mp3 with `clip: 0`.

**Layout (9:16):** a large icon at y≈0.12–0.2, the title or cards at y 0.24–0.56, subtitles at 0.72. Use sizes of at least 56 for badges and at least 50 for body text, and `price` cards with `size` 140 for numbers. In Python strings, write a line break as a real newline (backslash-n), never a literal backslash-N.
