# Industry presets

Pick the row that fits the video. If the user named a colour or the brand has one (logo, sign, uniform, website), that colour wins over the suggested theme.

Columns:
- **Hook**: what to do in the first 2 s.
- **Signature effects**: the ones that sell this industry.
- **Avoid**: what looks wrong for it.

Density means VIP effects per 30 s of video.

| industry (vi) | theme | hook | signature effects | density | avoid |
|---|---|---|---|---|---|
| Bán hàng online / shop (quần áo, mỹ phẩm, gia dụng) | orange or red | product held to camera → snap 2× on it + `Stamp` "GIÁ SỐC" | `CountUp` price (from the old price down to the new one), `VsCards` old/new, `Tiles` gifts, `Checklist` benefits, `Callouts` on product parts, `NotifyStack` "vừa đặt hàng" | 6–8 | slow frost scenes over 1.5 s; serif-heavy text |
| Điện thoại / công nghệ | blue, sky or blackgold | `GiantCaption` model name behind the head | `CountUp` price, `BarChart` specs, `ScreenCard`, `Callouts`, `FloatButton` tap, `fx cool` | 6–8 | warm film look |
| Bất động sản | gold, blackgold or teal | `GeoMap` satellite fly-in onto the real site (boundary drawn with a running light), or `bg` replace with an aerial/drone clip + `TitleCard` project name | `GeoMap` road routes to the airport / centre / beach with km + minutes, `FloorPlan2D` 2D → 3D, `Building3D` blocks rising floor by floor, `CountUp` price per m², `NumberList` 3 lý do, `Callouts` on the map, `PhoneFrame` virtual tour, `popout` over a project photo, `Newspaper` "tin thị trường" | 4–6 | cartoon SFX, VHS, cracks |
| Spa / làm đẹp / makeup / nail | pink or purple | before/after: `fx compare` + `CompareHandle` | `Polaroids` results, `Checklist` steps, `Highlighter` key ingredient, `bg blur`, soft `InkSpread` | 4–5 | `Cracks`, `Shockwave`, `glitch` |
| Ăn uống / quán / F&B | orange, red or brown | snap 2× on the dish + `Stamp` "NGON" | `IconSlam` ingredients, `CountUp` price, `Tiles` menu, `fx warm`, `PostWall` dishes (frame stills) | 5–7 | cold blue grade |
| Giáo dục / khoá học / chia sẻ kiến thức / AI | blue or purple | `GiantCaption` topic word behind the head | `NumberTitle` sections, `NumberList`, `ChatBubbles` Q&A, `TypeBar`, `EditTimeline`, `ScriptPage`, `ChapterPanel`, `FollowCard` | 5–7 | too many stamps |
| Tài chính / bảo hiểm / ngân hàng | teal, blue or blackgold | `CountUp` the striking number on a navy grid | `BarChart`, `VsCards`, `Checklist`, `Newspaper`, `Callouts` | 4–5 | VHS, `GravityText` jokes |
| Gym / thể thao / sức khoẻ | red or orange | punch 1.2 + `Shockwave` | `CountUp` kg / days, `VsCards` before/after, `KineticTitle`, `Cracks` | 7–9 | slow pulls, serif |
| Du lịch / khách sạn / homestay | sky or teal | `bg` replace with the location clip | `Polaroids`, `Tiles` amenities, `TitleCard` place, `PhoneFrame`, `fx warm` | 4–6 | glitch |
| Ô tô / xe máy | blackgold, red or mono | snap 2× + `Shockwave` | `CountUp` price, `BarChart` specs, `Callouts` on parts, `VsCards` | 5–7 | pastel tiles |
| Thời trang | mono, pink or blackgold | `KineticTitle` style word | `Polaroids` outfits, `PostWall`, `fx film`, `Highlighter` | 5–6 | heavy UI mockups |
| Tin tức / bình luận / drama | red or mono | `Newspaper` headline (only real headlines, summarized) | `Stamp`, `Callouts`, `CommentsDrop`, `NotifyStack`, `fx bw` for the past, `IncomingCall` | 5–7 | made-up quotes or screenshots presented as real |
| Vlog / đời sống | any (brand or user's favourite) | hook clip + `KineticTitle` | `Polaroids`, `TitleCard` chapters, `fx film`, `TearAway` between scenes | 3–5 | dense UI |

## General rules
- **Honesty.** Prices, numbers, specs and quotes come from the footage or the user. Never invent them. A `Newspaper` must summarize a real article in your own words and never copy it.
- **Hook (first 2 s).** Pair the strongest claim with a camera move (HOOK zoom or snap) and one VIP effect.
- **CTA (last 3 s).** Use `FollowCard` with the page name the user gives, or a `BlueBig` with the address or phone number for a local shop.
- **Sounds.** Map them to the industry:
  - **soft UI** (whoosh / pop / tick) for education, spa, real estate and finance;
  - **punchy** (impact / bass_hit / riser) for gym, cars, sales and news;
  - **cartoon** sounds (boing, rimshot, vine_boom) only for comedy.
- **Music.** Use royalty-free tracks only. If the user has none, run `make_music.py --mood upbeat|calm|news` or use no music. Never use copyrighted songs.
