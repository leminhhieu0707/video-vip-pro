// ESTATE pack — real-estate graphics on real data.
//   GeoMap:     satellite fly-in (Google-Earth style tilt) on mosaics from scripts/geo.py; the site boundary draws with a
//               running light, road routes to amenities draw with distance / time cards, km rings, pins, compass, credit.
//   Building3D: a building extruded from its footprint (bản vẽ): outline draws, floors rise one by one, glass or white
//               finish, the camera orbits. Several blocks = a 3D masterplan.
//   FloorPlan2D: a floor plan draws in 2D (walls, rooms filled with name + m², dimension lines), then tilts into 3D and the
//               walls rise ("2D → 3D").
// All full-screen. Lengths are metres; the 3D comps use a small perspective projector (no WebGL), so they render fast.
import React from 'react';
import {AbsoluteFill, continueRender, delayRender, Img, interpolate, OffthreadVideo, spring, staticFile} from 'remotion';
import {EASE_IN, EASE_OUT, exit, SANS, SERIF, T} from './theme';
import {CL, lerp, P, useT} from './Vip';

const url = (s: string) => (s.startsWith('http') ? s : staticFile(s));
const smooth = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const fmt = (n: number, d = 1) => n.toLocaleString('vi-VN', {maximumFractionDigits: d, minimumFractionDigits: 0});
const GOLD = '#FFC93C';

// ================================================================ GeoMap
type Cam = {t: number; u: number; v: number; z: number; tilt?: number; rot?: number};
function camAt(keys: Cam[], t: number): Required<Cam> {
  const k = [...keys].sort((a, b) => a.t - b.t);
  if (t <= k[0].t) return {tilt: 0, rot: 0, ...k[0]} as Required<Cam>;
  for (let i = 0; i < k.length - 1; i++) {
    const a = k[i], b = k[i + 1];
    if (t <= b.t) {
      const p = smooth((t - a.t) / Math.max(0.001, b.t - a.t));
      return {t, u: a.u + (b.u - a.u) * p, v: a.v + (b.v - a.v) * p, z: a.z + (b.z - a.z) * p,
        tilt: (a.tilt || 0) + ((b.tilt || 0) - (a.tilt || 0)) * p, rot: (a.rot || 0) + ((b.rot || 0) - (a.rot || 0)) * p};
    }
  }
  const l = k[k.length - 1];
  return {tilt: 0, rot: 0, ...l} as Required<Cam>;
}
const pathLen = (pts: number[][]) => pts.reduce((s, p, i) => (i ? s + Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]) : 0), 0);
/** point + heading at fraction f (0..1) along a polyline */
function along(pts: number[][], f: number): [number, number, number] {
  const L = pathLen(pts);
  let d = Math.max(0, Math.min(1, f)) * L;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i], l = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (d <= l || i === pts.length - 1) {
      const r = l ? Math.min(1, d / l) : 0;
      return [a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r, Math.atan2(b[1] - a[1], b[0] - a[0])];
    }
    d -= l;
  }
  return [pts[0][0], pts[0][1], 0];
}
/** CSS matrix3d that maps a w×h box onto the quad q (TL, TR, BR, BL) — projective, for warping a plan image onto the map */
function quadMatrix(w: number, h: number, q: number[][]): string {
  const [x0, y0] = q[0], [x1, y1] = q[1], [x2, y2] = q[2], [x3, y3] = q[3];
  const dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2;
  const sx = x0 - x1 + x2 - x3, sy = y0 - y1 + y2 - y3;
  const det = dx1 * dy2 - dx2 * dy1 || 1e-9;
  const g = (sx * dy2 - dx2 * sy) / det, hh = (dx1 * sy - sx * dy1) / det;
  const a = x1 - x0 + g * x1, b = x3 - x0 + hh * x3, c = x0;
  const d = y1 - y0 + g * y1, e = y3 - y0 + hh * y3, f = y0;
  // unit square -> quad, then scale the box to the unit square
  const m = [a / w, d / w, 0, g / w, b / h, e / h, 0, hh / h, 0, 0, 1, 0, c, f, 0, 1];
  return `matrix3d(${m.map((x) => +x.toFixed(10)).join(',')})`;
}
/** a CSS-3D prism standing on the plane (walls + roof), used for lifted plots and houses on lots */
function prism(ring: number[][], z0: number, h: number, wall: string, roof: React.ReactNode, key: string): React.ReactNode {
  return <React.Fragment key={key}>
    {ring.map((a, i) => {
      const b = ring[(i + 1) % ring.length];
      const len = Math.hypot(b[0] - a[0], b[1] - a[1]), ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
      return <div key={`${key}w${i}`} style={{position: 'absolute', left: a[0], top: a[1], width: len, height: h, transformOrigin: '0 0',
        transform: `translateZ(${z0}px) rotateZ(${ang}rad) rotateX(90deg)`, background: wall, borderTop: '1.5px solid rgba(255,255,255,0.85)'}} />;
    })}
    <div style={{position: 'absolute', inset: 0, transform: `translateZ(${z0 + h}px)`, clipPath: `polygon(${ring.map((q) => `${q[0]}px ${q[1]}px`).join(', ')})`}}>{roof}</div>
  </React.Fragment>;
}
// AGENCY look (measured on top VN real-estate reels): huge metallic numbers, bold white caps captions, copper pin cards.
// Type scale on a 1080-wide frame: number 190–230 px, unit 0.38×, caption 44 px, pin name 34 px + kicker 22 px.
const COPPER = 'linear-gradient(180deg, #FFF1DE 0%, #F6CDA4 30%, #D8996A 62%, #9A5E3C 100%)';
const GOLDG = 'linear-gradient(180deg, #FFF7D6 0%, #F7DC8A 35%, #D9A441 68%, #94661F 100%)';
const METAL: Record<string, string> = {copper: COPPER, gold: GOLDG, white: 'linear-gradient(180deg, #FFFFFF 0%, #E6ECF5 100%)',
  champagne: 'linear-gradient(180deg, #FFFBEF 0%, #F3E2B8 34%, #D2B072 66%, #8F7038 100%)',
  ivory: 'linear-gradient(180deg, #FFFFFF 0%, #FFFDF7 45%, #EFE4CB 100%)'};
const ACCENT: Record<string, string> = {ivory: '#E3C88F', champagne: '#E3C88F', copper: '#E9B48A', gold: '#E8C25E', navy: '#9FB6E8', brand: T('#8EB3FF'), white: '#FFFFFF'};
const CARD_BG: Record<string, string> = {copper: 'linear-gradient(180deg, #9C6A4A 0%, #7A4B31 100%)', gold: 'linear-gradient(180deg, #A9853C 0%, #7C5F22 100%)',
  navy: 'linear-gradient(180deg, #24344F 0%, #152238 100%)', champagne: 'linear-gradient(180deg, #24344F 0%, #152238 100%)',
  brand: T('linear-gradient(180deg, #2A3B7A 0%, #152238 100%)')};
// marker colours per tone (pin teardrop + icon bubbles)
const MARK: Record<string, [string, string, string]> = {copper: ['#B07A55', '#6E4128', 'rgba(255,235,210,0.6)'], gold: ['#C9A24E', '#7C5F22', 'rgba(255,240,200,0.6)'],
  navy: ['#33486E', '#152238', 'rgba(220,230,255,0.5)'], champagne: ['#D9BF86', '#8F7038', 'rgba(255,248,230,0.7)'], brand: [T('#3E5BD0'), T('#152238'), 'rgba(220,230,255,0.5)']};
const metalText = (g: string): React.CSSProperties => ({backgroundImage: g, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
  WebkitTextFillColor: 'transparent', filter: 'drop-shadow(0 4px 10px rgba(0,0,0,0.55)) drop-shadow(0 1px 1px rgba(0,0,0,0.6))'});
/** tiny line icons for pins / checklists (24×24, white) */
export const ICON: Record<string, string> = {
  pin: 'M12 3a6 6 0 016 6c0 4.5-6 11-6 11S6 13.5 6 9a6 6 0 016-6zm0 3.5A2.5 2.5 0 1012 11.5 2.5 2.5 0 0012 6.5z',
  cart: 'M4 5h2l2 10h9l2-7H7M10 19a1 1 0 100 .1M17 19a1 1 0 100 .1', star: 'M12 3l2.6 5.6 6 .7-4.5 4.1 1.2 6L12 16.5 6.7 19.4l1.2-6L3.4 9.3l6-.7z',
  bridge: 'M3 16h18M5 16V10m14 6v-6M3 10c4 0 5-4 9-4s5 4 9 4M9 16v-3m6 3v-3', wave: 'M3 14c2 0 2-2 4.5-2S10 14 12 14s2-2 4.5-2S19 14 21 14M3 18c2 0 2-2 4.5-2S10 18 12 18s2-2 4.5-2S19 18 21 18',
  plane: 'M3 13l8-2 4-7 2 1-2 7 6 2v2l-7-1-3 5H9l1-5-6-1z', school: 'M3 9l9-5 9 5-9 5zm3 2v4c2 2 10 2 12 0v-4', hospital: 'M5 4h14v16H5zM12 8v6M9 11h6',
  tree: 'M12 3l5 7h-3l4 6H6l4-6H7zM12 16v5', train: 'M7 3h10a2 2 0 012 2v9a3 3 0 01-3 3H8a3 3 0 01-3-3V5a2 2 0 012-2zM5 10h14M8 20l-2 2M16 20l2 2',
  flag: 'M6 21V4m0 0h11l-2 4 2 4H6', tag: 'M3 12l9-9h8v8l-9 9zM16 8a1 1 0 100 .1', plan: 'M4 4h16v16H4zM4 12h8V4M12 16h8',
  calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4', chat: 'M4 5h16v11H9l-5 4z', key: 'M8 14a4 4 0 114-4l8 0v3h-2v2h-3v-2h-3a4 4 0 01-4 1z',
  pool: 'M3 17c2 0 2-1.5 4.5-1.5S10 17 12 17s2-1.5 4.5-1.5S19 17 21 17M7 14V5a2 2 0 014 0M13 14V5a2 2 0 014 0M7 8h6M7 11h6',
  home: 'M3 11l9-7 9 7v9h-6v-6H9v6H3z', check: 'M5 12l4 4 10-10', search: 'M11 4a7 7 0 100 14 7 7 0 000-14zM21 21l-5-5',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2', money: 'M3 7h18v10H3zM12 9.5a2.5 2.5 0 100 5 2.5 2.5 0 000-5zM6 10v4M18 10v4',
  users: 'M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2 20c0-3.5 3-6 7-6s7 2.5 7 6M16 4.5a3.5 3.5 0 010 6.5M18 14c2.5.7 4 2.8 4 6',
  bolt: 'M13 2L4 14h7l-1 8 9-12h-7z', shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z', heart: 'M12 20s-7-4.5-7-10a4 4 0 017-2.6A4 4 0 0119 10c0 5.5-7 10-7 10z',
  car: 'M5 16V11l2-5h10l2 5v5M5 16h14M7 16v2M17 16v2M7.5 12.5h.01M16.5 12.5h.01', clock: 'M12 3a9 9 0 100 18 9 9 0 000-18zM12 7v5l3 2',
  sun: 'M12 8a4 4 0 100 8 4 4 0 000-8zM12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5',
  doc: 'M6 3h9l4 4v14H6zM14 3v5h5M9 13h7M9 17h5', phone: 'M8 3h8v18H8zM11 18h2'};
const Icon24: React.FC<{name?: string; size?: number; color?: string}> = ({name = 'pin', size = 24, color = '#fff'}) =>
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round">
    <path d={ICON[name] || ICON.pin} /></svg>;
/**
 * GlassPin — the premium place card: frosted dark glass, a real photo of the place (or an icon), a gold category line,
 * the name, a meta line ("🚗 5 phút · 4,1 km"), and a hairline leader down to a glowing ground dot. No cartoon teardrop.
 */
const GlassPin: React.FC<{name: string; kicker?: string; meta?: string; photo?: string; icon?: string; tone?: string; p?: number; t?: number; leader?: number}> =
  ({name, kicker, meta, photo, icon, tone = 'ivory', p = 1, t = 0, leader = 70}) => {
    const acc = ACCENT[tone] || ACCENT.ivory;
    return <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: Math.min(1, p * 1.6), transform: `translateY(${(1 - p) * 26}px)`}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 18, padding: 12, paddingRight: 30, borderRadius: 24, whiteSpace: 'nowrap',
        background: 'linear-gradient(160deg, rgba(22,30,46,0.78), rgba(8,12,22,0.82))', backdropFilter: 'blur(14px)', WebkitBackdropFilter: 'blur(14px)',
        border: '1px solid rgba(255,255,255,0.16)', boxShadow: `0 18px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.12)`, position: 'relative'}}>
        <div style={{position: 'absolute', left: 0, top: 18, bottom: 18, width: 4, borderRadius: 4, background: acc}} />
        {photo ? <div style={{width: 150, height: 150, borderRadius: 18, overflow: 'hidden', flex: 'none', marginLeft: 6, boxShadow: '0 6px 14px rgba(0,0,0,0.4)'}}>
          <Img src={url(photo)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.12 - 0.06 * Math.min(1, t / 3)})`}} /></div>
          : <div style={{width: 76, height: 76, borderRadius: 99, flex: 'none', marginLeft: 10, display: 'grid', placeItems: 'center',
            background: 'rgba(255,255,255,0.08)', border: `1.5px solid ${acc}`}}><Icon24 name={icon} size={36} color={acc} /></div>}
        <div style={{display: 'flex', flexDirection: 'column', gap: 4}}>
          {kicker ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 21, letterSpacing: '0.14em', textTransform: 'uppercase', color: acc}}>{kicker}</div> : null}
          <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 44, lineHeight: 1.08, color: '#fff', letterSpacing: '-0.005em'}}>{name}</div>
          {meta ? <div style={{display: 'flex', alignItems: 'center', gap: 10, fontFamily: SANS, fontWeight: 600, fontSize: 28, color: 'rgba(255,255,255,0.88)'}}>
            <svg width={26} height={26} viewBox="0 0 24 24" fill="none" stroke={acc} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
              <path d="M5 16V11l2-5h10l2 5v5M5 16h14M7 16v2M17 16v2M7.5 12.5h.01M16.5 12.5h.01" /></svg>{meta}</div> : null}
        </div>
      </div>
      {leader ? <>
        <div style={{width: 2, height: leader * Math.min(1, p * 1.3), background: `linear-gradient(${acc}, rgba(255,255,255,0.25))`}} />
        <div style={{width: 18, height: 18, borderRadius: 99, background: '#fff', boxShadow: `0 0 0 ${6 + 4 * Math.abs(Math.sin(t * 3))}px ${acc}55, 0 0 18px ${acc}`}} />
      </> : null}
    </div>;
  };
/** the agency pin: copper card (kicker + NAME) above a teardrop marker with an icon */
const AgencyPin: React.FC<{name: string; kicker?: string; icon?: string; tone?: string; p?: number}> = ({name, kicker, icon, tone = 'copper', p = 1}) =>
  <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: Math.min(1, p * 1.5), transform: `scale(${0.7 + 0.3 * p})`, transformOrigin: '50% 100%'}}>
    <div style={{background: CARD_BG[tone] || CARD_BG.copper, borderRadius: 8, padding: kicker ? '10px 26px 12px' : '14px 26px', textAlign: 'center', whiteSpace: 'nowrap',
      boxShadow: '0 10px 24px rgba(0,0,0,0.45)', border: tone === 'champagne' ? '1.5px solid #D2B072' : '1px solid rgba(255,230,200,0.35)'}}>
      {kicker ? <div style={{fontFamily: SANS, fontWeight: 500, fontSize: 22, color: 'rgba(255,240,225,0.9)'}}>{kicker}</div> : null}
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 34, color: '#fff', letterSpacing: '0.01em', textTransform: 'uppercase'}}>{name}</div>
    </div>
    <svg width={60} height={78} viewBox="0 0 60 78" style={{marginTop: 10, filter: 'drop-shadow(0 6px 8px rgba(0,0,0,0.5))'}}>
      <defs><linearGradient id={`pinG${tone}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={(MARK[tone] || MARK.copper)[0]} />
        <stop offset="1" stopColor={(MARK[tone] || MARK.copper)[1]} /></linearGradient></defs>
      <path d="M30 2C14.5 2 3 13.5 3 28c0 19 27 47 27 47s27-28 27-47C57 13.5 45.5 2 30 2z" fill={`url(#pinG${tone})`} stroke={(MARK[tone] || MARK.copper)[2]} strokeWidth={1.5} />
    </svg>
    <div style={{marginTop: -70, height: 52, display: 'flex', alignItems: 'center'}}><Icon24 name={icon} size={30} /></div>
    <div style={{marginTop: 14, width: 26, height: 8, borderRadius: 99, background: 'rgba(0,0,0,0.35)', filter: 'blur(2px)'}} />
  </div>;
const LUX = {cap: {fontFamily: SANS, fontWeight: 600, letterSpacing: '0.26em', textTransform: 'uppercase' as const},
  num: {fontFamily: SERIF, fontStyle: 'italic' as const, fontWeight: 500}, shadow: '0 2px 14px rgba(0,0,0,0.75), 0 0 2px rgba(0,0,0,0.6)'};

/**
 * GeoMap: props = geo.py's geomap.json (levels, camera, site, pois, rings, credit, scale) plus cues:
 * site_at (s, when the boundary starts drawing), site_draw (2), site_label, site_sub, routes [{name, at}] (which POI
 * routes draw, when), pins_at (other POIs pop), rings_at, color (lines, gold), camera (override keys {t, u, v, z, tilt}),
 * fill ('rgba(255,201,60,0.18)'), compass.
 * Plot cues: lots (geo.py "lots") + lots_at (the subdivision pops, coloured by status, with a legend), site_edges (true: the
 * length of every edge + the area in the middle once the boundary is drawn), lift_at / lift_m (4: the plot rises out of the
 * map as a 3D block), roads (geo.py "roads") + roads_at (a measuring arrow across the road with its width).
 */
const LOT_ST: Record<string, [string, string]> = {available: ['#22C55E', 'Còn trống'], sold: ['#EF4444', 'Đã bán'], reserved: ['#F59E0B', 'Đang giữ chỗ']};
export const GeoMap: React.FC<P> = ({duration, levels = [], camera = [], site = {}, pois = [], rings = [], scale = 1.5, credit = '', mpu = 38000000,
  site_at, site_draw = 2, site_label, site_sub, routes = [], pins_at, rings_at, color = GOLD, fill = 'rgba(255,201,60,0.18)', compass = true,
  lots = [], lots_at, legend = true, site_edges = false, lift_at, lift_m = 4, roads = [], roads_at,
  look = 'luxury', handheld = 0, volna = false, focus_at, houses = [], follow, vector, basemap = 'satellite', vector_at = 0, streets_at,
  plans = [], plans_at, plans_opacity = 0.72, iso = [], iso_at, osm3d_at, osm3d_color = '#E8ECF2', basemap_opacity = 0.7, tone = 'ivory', pin_style = 'glass'}) => {
  const {frame, fps, t, W, H} = useT();
  const cam = camAt(camera.length ? camera : [{t: 0, u: site.u ?? 0.5, v: site.v ?? 0.5, z: 14}], t);
  if (follow && t >= follow.from) { // camera rides along a route (bay dọc đường vào lô), road ahead pointing up the screen
    const poi = pois.find((x: any) => x.name === follow.name);
    if (poi && poi.line) {
      const line = follow.reverse === false ? poi.line : [...poi.line].reverse(); // routes start at the site; default flies towards it
      const f = smooth(Math.min(1, (t - follow.from) / Math.max(0.1, follow.to - follow.from)));
      const [u, v, hd] = along(line, f);
      const [, , hd2] = along(line, Math.min(1, f + 0.04));
      cam.u = u; cam.v = v; cam.z = follow.z ?? 17.5; cam.tilt = follow.tilt ?? 55;
      cam.rot = -((hd + hd2) / 2) * 180 / Math.PI - 90;
    }
  }
  if (handheld) { // a hand-held / drone drift so the map never moves like a machine
    const kk0 = 256 * scale * Math.pow(2, cam.z);
    cam.u += ((Math.sin(t * 1.31) + 0.5 * Math.sin(t * 2.87 + 1.3)) * handheld * 6) / kk0;
    cam.v += ((Math.sin(t * 1.07 + 2.1) + 0.5 * Math.sin(t * 3.11)) * handheld * 6) / kk0;
    cam.rot += Math.sin(t * 0.73) * handheld * 0.35;
    cam.tilt += Math.sin(t * 0.91 + 0.7) * handheld * 0.4;
  }
  const k = 256 * scale * Math.pow(2, cam.z); // screen px per mercator unit
  const PW = W * 2.2, PH = H * 2.2; // the tilted plane is bigger than the screen so its edges never show
  const X = (u: number) => PW / 2 + (u - cam.u) * k, Y = (v: number) => PH / 2 + (v - cam.v) * k;
  const o = Math.min(interpolate(t, [0, 0.25], [0, 1], CL), exit(frame, fps, duration, 0.25));
  const counter = `rotateZ(${-cam.rot}deg) rotateX(${-cam.tilt}deg)`; // labels stand up
  const label = (x: number, y: number, p: number, node: React.ReactNode, key: string, dx = 0, dy = 0) => <div key={key} style={{position: 'absolute', left: x, top: y,
    transform: `translate(-50%, -100%) ${counter} translate(${dx}px, ${dy + (1 - p) * 30}px) scale(${0.6 + 0.4 * p})`, transformOrigin: '50% 100%', opacity: Math.min(1, p * 1.5)}}>{node}</div>;
  const lux = look === 'luxury' || look === 'agency';
  const agency = look === 'agency';
  const card = (a: React.ReactNode, b?: React.ReactNode, big = false, icon?: string, kicker?: string, photo?: string, meta?: string) => agency
    ? (pin_style === 'glass'
      ? <GlassPin name={String(a)} kicker={kicker} meta={meta ?? (b && !kicker ? String(b) : undefined)} photo={photo} icon={icon || (big ? 'home' : 'pin')} tone={tone} t={t} />
      : <AgencyPin name={String(a)} kicker={kicker ?? (b ? String(b) : undefined)} icon={icon || (big ? 'home' : 'pin')} tone={tone} />)
    : lux ? <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textShadow: LUX.shadow}}>
    <div style={{...LUX.cap, fontSize: big ? 30 : 21, color: '#fff', whiteSpace: 'nowrap', paddingLeft: '0.26em'}}>{a}</div>
    {b ? <div style={{...LUX.num, fontSize: big ? 46 : 40, color, whiteSpace: 'nowrap', marginTop: 2}}>{b}</div> : null}
    <div style={{width: 1.5, height: big ? 120 : 90, marginTop: 8, background: 'linear-gradient(rgba(255,255,255,0.95), rgba(255,255,255,0.15))'}} />
    <div style={{width: 12, height: 12, borderRadius: 99, border: '1.5px solid #fff', marginTop: -2, boxShadow: `0 0 12px ${color}`}} />
  </div> : <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
    <div style={{padding: big ? '18px 30px' : '12px 22px', borderRadius: big ? 22 : 16, background: 'rgba(10,14,24,0.82)', border: `2px solid ${color}`,
      boxShadow: `0 10px 30px rgba(0,0,0,0.45), 0 0 24px ${color}55`, color: '#fff', fontFamily: SANS, textAlign: 'center', whiteSpace: 'nowrap'}}>
      <div style={{fontWeight: 800, fontSize: big ? 46 : 32, letterSpacing: '-0.01em'}}>{a}</div>
      {b ? <div style={{fontWeight: 600, fontSize: big ? 28 : 24, color, marginTop: 4}}>{b}</div> : null}
    </div>
    <div style={{width: 3, height: big ? 70 : 40, background: `linear-gradient(${color}, transparent)`}} />
  </div>;
  const ring: number[][] = (site.ring || []).map((p: number[]) => [X(p[0]), Y(p[1])]);
  const sp = site_at == null ? 0 : lerp(t, site_at, site_at + site_draw, 0, 1, (x) => smooth(x));
  const sl = ring.length ? pathLen([...ring, ring[0]]) : 0;
  const sd = ring.map((p) => p.join(',')).join(' ');
  return <AbsoluteFill style={{background: '#0B1520', overflow: 'hidden', opacity: o}}>
    <div style={{position: 'absolute', left: W / 2 - PW / 2, top: H / 2 - PH / 2, width: PW, height: PH, transformOrigin: '50% 50%',
      transform: `perspective(${H * 1.25}px) rotateX(${cam.tilt}deg) rotateZ(${cam.rot}deg)`, transformStyle: 'preserve-3d'}}>
      {levels.map((L: any, i: number) => {
        const op = i === 0 ? 1 : interpolate(cam.z, [L.z - 1.4, L.z - 0.8], [0, 1], CL);
        if (op <= 0) return null;
        return <Img key={i} src={url(L.src)} style={{position: 'absolute', left: X(L.u0), top: Y(L.v0), width: L.du * k, height: L.dv * k, opacity: op,
          imageRendering: 'auto'}} />;
      })}
      {basemap !== 'satellite' ? <div style={{position: 'absolute', inset: 0, background: basemap === 'light' ? '#EEF1F4' : '#08111F',
        opacity: lerp(t, vector_at, vector_at + 0.8) * (basemap === 'blend' ? basemap_opacity : 1)}} /> : null}
      {vector ? (() => {
        const vp = lerp(t, vector_at, vector_at + 1.0);
        const dark = basemap !== 'light';
        const pts = (a: number[][]) => a.map((q) => `${X(q[0]).toFixed(1)},${Y(q[1]).toFixed(1)}`).join(' ');
        return <svg width={PW} height={PH} style={{position: 'absolute', inset: 0, overflow: 'visible', opacity: vp}}>
          <defs>{(vector.roads || []).filter((r: any) => r.name && r.major).slice(0, 40).map((r: any, i: number) =>
            <path key={i} id={`st${i}`} d={'M' + (X(r.pts[0][0]) > X(r.pts[r.pts.length - 1][0]) ? [...r.pts].reverse() : r.pts)
              .map((q: number[]) => `${X(q[0]).toFixed(1)} ${Y(q[1]).toFixed(1)}`).join(' L')} />)}</defs>
          {(vector.water || []).map((w: any, i: number) => <polygon key={`wa${i}`} points={pts(w)} fill={dark ? '#0E2C4A' : '#BFD9F2'} />)}
          {(vector.parks || []).map((w: any, i: number) => <polygon key={`pk${i}`} points={pts(w)} fill={dark ? '#0F2A22' : '#D5ECD9'} />)}
          {basemap !== 'satellite' ? (vector.buildings || []).map((b: any, i: number) => <polygon key={`bd${i}`} points={pts(b.pts)} fill={dark ? '#1A2740' : '#D9DEE5'} />) : null}
          {(vector.roads || []).map((r: any, i: number) => <polyline key={`rd${i}`} points={pts(r.pts)} fill="none" strokeLinecap="round" strokeLinejoin="round"
            stroke={r.major ? (dark ? '#F2C66B' : '#FFFFFF') : (dark ? '#3B4E6E' : '#FFFFFF')} strokeOpacity={r.major ? 0.85 : 0.7}
            strokeWidth={(r.major ? 7 : 3.5) * Math.max(0.6, Math.min(2.2, Math.pow(2, cam.z - 16)))} />)}
          {streets_at != null ? (vector.roads || []).filter((r: any) => r.name && r.major).slice(0, 40).map((r: any, i: number) => {
            const sp2 = lerp(t, streets_at + i * 0.05, streets_at + i * 0.05 + 0.6);
            return sp2 > 0 ? <text key={`sn${i}`} opacity={sp2} fill="#fff" fontFamily="BVP, sans-serif" fontWeight={600} fontSize={26} letterSpacing="5"
              style={{textShadow: '0 1px 6px #000', paintOrder: 'stroke'}} stroke="rgba(0,0,0,0.55)" strokeWidth={5}>
              <textPath href={`#st${i}`} startOffset="50%" textAnchor="middle">{String(r.name).toUpperCase()}</textPath></text> : null;
          }) : null}
        </svg>;
      })() : null}
      {plans_at != null ? plans.map((pl: any, i: number) => {
        const pp = lerp(t, plans_at + i * 0.4, plans_at + i * 0.4 + 1.0);
        if (pp <= 0 || !pl.quad) return null;
        const q = pl.quad.map((c: number[]) => [X(c[0]), Y(c[1])]);
        return <Img key={`pl${i}`} src={url(pl.src)} style={{position: 'absolute', left: 0, top: 0, width: pl.w, height: pl.h, transformOrigin: '0 0',
          transform: quadMatrix(pl.w, pl.h, q), opacity: pp * (pl.opacity ?? plans_opacity), mixBlendMode: 'multiply'}} />;
      }) : null}
      {iso_at != null && iso.length ? <svg width={PW} height={PH} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        {[...iso].reverse().map((band: any, i: number) => {
          const j = iso.length - 1 - i;
          const ip = lerp(t, iso_at + j * 0.45, iso_at + j * 0.45 + 0.8, 0, 1, EASE_IN);
          const c = ['#22C55E', '#FACC15', '#F97316', '#EF4444'][j % 4];
          return ip > 0 ? <g key={`iso${j}`} opacity={ip}>{band.polys.map((poly: number[][], m: number) =>
            <polygon key={m} points={poly.map((q) => `${X(q[0])},${Y(q[1])}`).join(' ')} fill={c} fillOpacity={0.16} stroke={c} strokeWidth={3} strokeDasharray="10 8" />)}</g> : null;
        })}
      </svg> : null}
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 50%, transparent 30%, rgba(5,10,20,0.45) 75%)'}} />
      <svg width={PW} height={PH} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
        {rings.map((r: any, i: number) => {
          const p = rings_at == null ? 0 : lerp(t, rings_at + i * 0.25, rings_at + i * 0.25 + 0.7, 0, 1, EASE_IN);
          if (p <= 0) return null;
          return <g key={i} opacity={p * 0.9}>
            <circle cx={X(site.u)} cy={Y(site.v)} r={r.r * k * p} fill="none" stroke="#fff" strokeWidth={lux ? 1.6 : 3} strokeDasharray={lux ? '2 10' : '14 12'} strokeLinecap="round" />
          </g>;
        })}
        {routes.map((rr: any, i: number) => {
          const poi = pois.find((x: any) => x.name === rr.name);
          if (!poi || !poi.line) return null;
          const pts = poi.line.map((q: number[]) => [X(q[0]), Y(q[1])]);
          const L = pathLen(pts);
          const p = lerp(t, rr.at, rr.at + (rr.dur || 1.6), 0, 1, (x) => smooth(x));
          if (p <= 0) return null;
          const d = pts.map((q: number[]) => q.join(',')).join(' ');
          return <g key={i}>
            <polyline points={d} fill="none" stroke="rgba(0,0,0,0.45)" strokeWidth={14} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${L * p} ${L}`} />
            <polyline points={d} fill="none" stroke={rr.color || color} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${L * p} ${L}`} filter="url(#glow)" />
            <polyline points={d} fill="none" stroke="#fff" strokeWidth={4} strokeLinecap="round" strokeDasharray={`${L * 0.03} ${L}`}
              strokeDashoffset={-L * Math.max(0, p - 0.03)} opacity={p < 1 ? 1 : 0} />
          </g>;
        })}
        {focus_at != null && ring.length ? <path fillRule="evenodd" fill="#02060C" opacity={0.58 * lerp(t, focus_at, focus_at + 0.8)}
          d={`M0 0 H${PW} V${PH} H0 Z M${ring.map((q) => `${q[0]} ${q[1]}`).join(' L')} Z`} /> : null}
        {volna ? routes.map((rr: any, i: number) => {
          const poi = pois.find((x: any) => x.name === rr.name);
          if (!poi || !poi.line) return null;
          const pts = poi.line.map((q: number[]) => [X(q[0]), Y(q[1])]);
          const L = pathLen(pts), d = pts.map((q: number[]) => q.join(',')).join(' ');
          const t0 = rr.at + (rr.dur || 1.6) * 0.6;
          if (t < t0) return null;
          return <g key={`vo${i}`}>{[0, 1, 2].map((m) => {
            const ph = (((t - t0) * 0.42 + m / 3) % 1);
            return <g key={m}>
              <polyline points={d} fill="none" stroke={rr.color || color} strokeWidth={16} strokeLinecap="round" strokeOpacity={0.35}
                strokeDasharray={`${L * 0.12} ${L * 2}`} strokeDashoffset={-L * ph + L * 0.12} filter="url(#glow)" />
              <polyline points={d} fill="none" stroke="#FFFFFF" strokeWidth={5} strokeLinecap="round"
                strokeDasharray={`${L * 0.05} ${L * 2}`} strokeDashoffset={-L * ph + L * 0.05} />
            </g>;
          })}</g>;
        }) : null}
        {lots_at != null ? lots.map((l: any, i: number) => {
          const p = lerp(t, lots_at + i * 0.05, lots_at + i * 0.05 + 0.35);
          if (p <= 0) return null;
          const c = (LOT_ST[l.status] || LOT_ST.available)[0];
          return <polygon key={`lot${i}`} points={l.ring.map((q: number[]) => `${X(q[0])},${Y(q[1])}`).join(' ')} fill={c} fillOpacity={0.4 * p}
            stroke="#fff" strokeWidth={2.5} strokeOpacity={0.95 * p} />;
        }) : null}
        {roads_at != null ? roads.map((r: any, i: number) => {
          const p = lerp(t, roads_at + i * 0.3, roads_at + i * 0.3 + 0.6, 0, 1, EASE_IN);
          if (p <= 0) return null;
          const ax = X(r.a[0]), ay = Y(r.a[1]), bx = X(r.b[0]), by = Y(r.b[1]);
          const mx = (ax + bx) / 2, my = (ay + by) / 2;
          const A = [mx + (ax - mx) * p, my + (ay - my) * p], B = [mx + (bx - mx) * p, my + (by - my) * p];
          const L = Math.hypot(bx - ax, by - ay) || 1, ux = (bx - ax) / L, uy = (by - ay) / L, nx = -uy * 12, ny = ux * 12;
          const head = (q: number[], dir: number) => `${q[0]},${q[1]} ${q[0] - dir * ux * 22 + nx},${q[1] - dir * uy * 22 + ny} ${q[0] - dir * ux * 22 - nx},${q[1] - dir * uy * 22 - ny}`;
          return <g key={`rd${i}`}>
            <line x1={A[0]} y1={A[1]} x2={B[0]} y2={B[1]} stroke="#fff" strokeWidth={5} />
            <polygon points={head(A, -1)} fill="#fff" /><polygon points={head(B, 1)} fill="#fff" />
          </g>;
        }) : null}
        {ring.length && lift_at != null ? <polygon points={sd} fill="#000" opacity={0.45 * lerp(t, lift_at, lift_at + 0.6)} /> : null}
        {lux && site_edges && ring.length && site_at != null && t > site_at + site_draw ? (() => {
          const dp = lerp(t, site_at + site_draw, site_at + site_draw + 0.6);
          const c = centroid(ring);
          return <g opacity={dp} stroke="#fff" strokeWidth={1.6}>{ring.map((a, i) => {
            const b = ring[(i + 1) % ring.length];
            const mx2 = (a[0] + b[0]) / 2 - c[0], my2 = (a[1] + b[1]) / 2 - c[1], ml = Math.hypot(mx2, my2) || 1;
            const ox = (mx2 / ml) * 26, oy = (my2 / ml) * 26;
            const ex = b[0] - a[0], ey = b[1] - a[1], el = Math.hypot(ex, ey) || 1, tx = (-ey / el) * 7, ty = (ex / el) * 7;
            return <g key={`dl${i}`}><line x1={a[0] + ox} y1={a[1] + oy} x2={b[0] + ox} y2={b[1] + oy} strokeDasharray={`${el * dp} ${el}`} />
              <line x1={a[0] + ox - tx} y1={a[1] + oy - ty} x2={a[0] + ox + tx} y2={a[1] + oy + ty} /><line x1={b[0] + ox - tx} y1={b[1] + oy - ty} x2={b[0] + ox + tx} y2={b[1] + oy + ty} /></g>;
          })}</g>;
        })() : null}
        {ring.length && sp > 0 ? <g>
          <polygon points={sd} fill={fill} opacity={lerp(t, (site_at || 0) + site_draw * 0.7, (site_at || 0) + site_draw + 0.4)} />
          <polygon points={sd} fill="none" stroke={color} strokeWidth={7} strokeLinejoin="round" strokeDasharray={`${sl * sp} ${sl}`} filter="url(#glow)" />
          <polygon points={sd} fill="none" stroke="#fff" strokeWidth={5} strokeLinejoin="round" strokeDasharray={`${sl * 0.05} ${sl}`}
            strokeDashoffset={-((sl * (sp < 1 ? sp : 1 + ((t - (site_at || 0) - site_draw) * 0.35) % 1)) % sl)} />
        </g> : null}
      </svg>
      {ring.length && lift_at != null && t >= lift_at ? (() => {
        const lp = lerp(t, lift_at, lift_at + 1.1, 0, 1, (x) => smooth(x));
        const hpx = (lift_m / mpu) * k * lp;
        const clip = `polygon(${ring.map((q) => `${q[0]}px ${q[1]}px`).join(', ')})`;
        return <>
          {ring.map((a, i) => {
            const b = ring[(i + 1) % ring.length];
            const len = Math.hypot(b[0] - a[0], b[1] - a[1]), ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
            return <div key={`wall${i}`} style={{position: 'absolute', left: a[0], top: a[1], width: len, height: hpx, transformOrigin: '0 0',
              transform: `rotateZ(${ang}rad) rotateX(90deg)`, background: `linear-gradient(0deg, ${color}EE, ${color}55)`, borderTop: '2px solid #fff'}} />;
          })}
          <div style={{position: 'absolute', inset: 0, transform: `translateZ(${hpx}px)`, clipPath: clip}}>
            {levels.map((L: any, i: number) => {
              const op = i === 0 ? 1 : interpolate(cam.z, [L.z - 1.4, L.z - 0.8], [0, 1], CL);
              return op > 0 ? <Img key={i} src={url(L.src)} style={{position: 'absolute', left: X(L.u0), top: Y(L.v0), width: L.du * k, height: L.dv * k, opacity: op}} /> : null;
            })}
            <div style={{position: 'absolute', inset: 0, background: `${color}33`}} />
          </div>
          <svg width={PW} height={PH} style={{position: 'absolute', inset: 0, overflow: 'visible', transform: `translateZ(${hpx + 0.5}px)`}}>
            <polygon points={sd} fill="none" stroke={color} strokeWidth={6} filter="url(#glow)" />
          </svg>
        </>;
      })() : null}
      {osm3d_at != null && vector && vector.buildings ? vector.buildings.slice(0, 160).map((bd: any, i: number) => { // OSM footprints extruded
        if (t < osm3d_at + (i % 20) * 0.04) return null;
        const rp = bd.pts.map((q: number[]) => [X(q[0]), Y(q[1])]);
        const pr = smooth(Math.min(1, (t - osm3d_at - (i % 20) * 0.04) / 0.9));
        const hpx = (((bd.levels || 3) * 3.3) / mpu) * k * pr;
        return prism(rp.length > 2 && rp[0][0] === rp[rp.length - 1][0] && rp[0][1] === rp[rp.length - 1][1] ? rp.slice(0, -1) : rp, 0, Math.max(1, hpx),
          `linear-gradient(0deg, ${osm3d_color}, ${osm3d_color}CC)`, <div style={{position: 'absolute', inset: 0, background: '#FFFFFF'}} />, `ob${i}`);
      }) : null}
      {houses.map((hs: any, i: number) => { // houses rise (or drop from the sky) on lots: {lot | ring, floors, fh, at, drop, inset}
        const lot = hs.lot != null ? lots.find((l: any) => String(l.label) === String(hs.lot)) : null;
        const rr0 = hs.ring || (lot && lot.ring);
        if (!rr0 || t < hs.at) return null;
        const c0 = centroid(rr0), ins = hs.inset ?? 0.12;
        const rpx = rr0.map((q: number[]) => [X(c0[0] + (q[0] - c0[0]) * (1 - ins)), Y(c0[1] + (q[1] - c0[1]) * (1 - ins))]);
        const fullH = ((hs.floors || 3) * (hs.fh || 3.4) / mpu) * k;
        let z0 = 0, hh = fullH;
        if (hs.drop) {
          const dp = spring({frame: frame - hs.at * fps, fps, config: {damping: 9, stiffness: 90, mass: 1.1}});
          z0 = (1 - dp) * fullH * 6;
        } else {
          hh = fullH * smooth(Math.min(1, (t - hs.at) / 1.2));
        }
        const wall = `repeating-linear-gradient(180deg, rgba(244,241,234,0.97) 0 ${fullH / (hs.floors || 3) * 0.3}px, rgba(70,95,130,0.92) ${fullH / (hs.floors || 3) * 0.3}px ${fullH / (hs.floors || 3) * 0.85}px, rgba(244,241,234,0.97) ${fullH / (hs.floors || 3) * 0.85}px ${fullH / (hs.floors || 3)}px)`;
        return prism(rpx, z0, Math.max(1, hh), wall, <div style={{position: 'absolute', inset: 0, background: '#E9E4D8'}} />, `hs${i}`);
      })}
      {lots_at != null ? lots.map((l: any, i: number) => {
        const p = lerp(t, lots_at + i * 0.05 + 0.15, lots_at + i * 0.05 + 0.45);
        const pts = l.ring.map((q: number[]) => [X(q[0]), Y(q[1])]);
        const c = centroid(pts);
        const wpx = Math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]);
        return p > 0 && wpx > 26 ? <div key={`ll${i}`} style={{position: 'absolute', left: c[0], top: c[1], transform: `translate(-50%,-50%) ${counter}`, opacity: p,
          fontFamily: SANS, fontWeight: 800, fontSize: Math.min(30, wpx * 0.55), color: '#fff', textShadow: '0 2px 6px #000'}}>{l.label}</div> : null;
      }) : null}
      {roads_at != null ? roads.map((r: any, i: number) => {
        const p = lerp(t, roads_at + i * 0.3 + 0.4, roads_at + i * 0.3 + 0.8);
        return p > 0 ? <div key={`rl${i}`} style={{position: 'absolute', left: (X(r.a[0]) + X(r.b[0])) / 2, top: (Y(r.a[1]) + Y(r.b[1])) / 2,
          transform: `translate(-50%,-50%) ${counter} scale(${0.7 + 0.3 * p})`, opacity: p, whiteSpace: 'nowrap',
          ...(lux ? {...LUX.cap, fontSize: 20, color: '#fff', textShadow: LUX.shadow}
            : {padding: '8px 18px', borderRadius: 99, background: '#fff', color: '#111', fontFamily: SANS, fontWeight: 800, fontSize: 28, boxShadow: '0 6px 20px rgba(0,0,0,0.4)'})}}>{lux ? r.label : `↔ ${r.label}`}</div> : null;
      }) : null}
      {site_edges && ring.length && site_at != null ? (() => {
        const p = lerp(t, site_at + site_draw, site_at + site_draw + 0.5);
        if (p <= 0) return null;
        const c = centroid(ring);
        const narrow = Math.min(...ring.map((q, i) => Math.hypot(ring[(i + 1) % ring.length][0] - q[0], ring[(i + 1) % ring.length][1] - q[1]))) < 240; // thin plot: area label above it
        const lift = lift_at != null ? (lift_m / mpu) * k * lerp(t, lift_at, lift_at + 1.1, 0, 1, (x) => smooth(x)) : 0;
        return <>
          {ring.map((a, i) => {
            const b = ring[(i + 1) % ring.length], m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
            const dx = m[0] - c[0], dy = m[1] - c[1], dl = Math.hypot(dx, dy) || 1;
            const e = (site.edges_m || [])[i];
            return e ? <div key={`ed${i}`} style={{position: 'absolute', left: m[0] + (dx / dl) * 58, top: m[1] + (dy / dl) * 58,
              transform: `translateZ(${lift}px) translate(-50%,-50%) ${counter}`, opacity: p, whiteSpace: 'nowrap',
              ...(lux ? {...LUX.num, fontSize: 38, color: '#fff', textShadow: LUX.shadow}
                : {padding: '4px 12px', borderRadius: 10, background: 'rgba(10,14,24,0.85)', border: `2px solid ${color}`, color: '#fff', fontFamily: SANS, fontWeight: 800, fontSize: 26})}}>{fmt(e)} m</div> : null;
          })}
          {site.area_m2 ? <div style={{position: 'absolute', left: c[0], top: narrow ? Math.min(...ring.map((q) => q[1])) - 120 : c[1],
            transform: `translateZ(${lift + 1}px) translate(-50%,-50%) ${counter}`, opacity: p,
            textAlign: 'center', fontFamily: SANS, color: '#fff', textShadow: '0 2px 10px #000'}}>
            <div style={lux ? {...LUX.num, fontSize: 64, textShadow: LUX.shadow} : {fontWeight: 800, fontSize: 44}}>{fmt(site.area_m2, 0)} m²</div>
            {site.facing ? <div style={lux ? {...LUX.cap, fontSize: 20, color, textShadow: LUX.shadow} : {fontWeight: 700, fontSize: 24, color}}>Hướng {site.facing}</div> : null}
          </div> : null}
        </>;
      })() : null}
      {rings.map((r: any, i: number) => {
        const p = rings_at == null ? 0 : lerp(t, rings_at + i * 0.25 + 0.4, rings_at + i * 0.25 + 0.8);
        return p > 0 ? label(X(site.u), Y(site.v) - r.r * k, p, <div style={lux ? {...LUX.num, fontSize: 34, color: '#fff', textShadow: LUX.shadow}
          : {padding: '6px 16px', borderRadius: 99, background: '#fff', color: '#111', fontFamily: SANS, fontWeight: 800, fontSize: 26}}>{fmt(r.km, 0)} km</div>, `rl${i}`) : null;
      })}
      {routes.map((rr: any, i: number) => {
        const poi = pois.find((x: any) => x.name === rr.name);
        if (!poi) return null;
        const p = spring({frame: frame - (rr.at + (rr.dur || 1.6) - 0.1) * fps, fps, config: {damping: 12, stiffness: 160, mass: 0.6}});
        return p > 0.01 ? label(X(poi.u), Y(poi.v), p, card(lux ? poi.name : `${poi.icon || '📍'} ${poi.name}`, poi.km ? `${fmt(poi.km)} km · ~${poi.min} phút` : `${fmt(poi.km_air)} km`, false, rr.icon || poi.glyph,
          pin_style === 'glass' ? poi.kicker : (poi.km ? `~${poi.min} phút · ${fmt(poi.km)} km` : undefined), poi.photo,
          poi.km ? `~${poi.min} phút · ${fmt(poi.km)} km` : undefined), `pr${i}`, rr.dx || 0, rr.dy || 0) : null;
      })}
      {pins_at != null ? pois.filter((x: any) => !routes.find((r: any) => r.name === x.name)).map((poi: any, i: number) => {
        const p = spring({frame: frame - (pins_at + i * 0.2) * fps, fps, config: {damping: 12, stiffness: 160, mass: 0.6}});
        return p > 0.01 ? label(X(poi.u), Y(poi.v), p, card(lux ? poi.name : `${poi.icon || '📍'} ${poi.name}`, poi.kicker || `cách ${fmt(poi.km_air)} km`, false, poi.glyph,
          pin_style === 'glass' ? poi.kicker : (poi.kicker || `cách ${fmt(poi.km_air)} km`), poi.photo, poi.meta || `cách ${fmt(poi.km_air)} km`), `pp${i}`, poi.dx || 0, poi.dy || 0) : null;
      }) : null}
      {site_label && site_at != null ? (() => {
        const p = spring({frame: frame - (site_at + site_draw * 0.6) * fps, fps, config: {damping: 12, stiffness: 140, mass: 0.7}});
        const top = ring.length ? Math.min(...ring.map((q) => q[1])) : Y(site.v);
        return p > 0.01 ? label(X(site.u), top - 10, p, card(site_label, site_sub, true, 'home', pin_style === 'glass' ? 'Dự án' : site_sub, site.photo, site_sub), 'site') : null;
      })() : null}
    </div>
    {legend && lots_at != null && lots.length ? (() => {
      const p = lerp(t, lots_at + 0.3, lots_at + 0.8);
      const cnt: Record<string, number> = {};
      lots.forEach((l: any) => { cnt[l.status] = (cnt[l.status] || 0) + 1; });
      return <div style={{position: 'absolute', left: 0, right: 0, bottom: 90, display: 'flex', justifyContent: 'center', gap: 14, opacity: p,
        transform: `translateY(${(1 - p) * 20}px)`}}>
        {Object.keys(LOT_ST).filter((kk) => cnt[kk]).map((kk) => <div key={kk} style={lux
          ? {display: 'flex', alignItems: 'center', gap: 10, color: '#fff', ...LUX.cap, fontSize: 19, textShadow: LUX.shadow, padding: '0 10px'}
          : {display: 'flex', alignItems: 'center', gap: 10, padding: '10px 18px', borderRadius: 99, background: 'rgba(10,14,24,0.82)', color: '#fff', fontFamily: SANS, fontWeight: 700, fontSize: 26}}>
          <span style={{width: lux ? 10 : 18, height: lux ? 10 : 18, borderRadius: lux ? 99 : 5, background: LOT_ST[kk][0], boxShadow: lux ? `0 0 10px ${LOT_ST[kk][0]}` : undefined}} />{LOT_ST[kk][1]} · {cnt[kk]}</div>)}
      </div>;
    })() : null}
    {/* haze towards the horizon hides the mosaic edge when tilted (Google-Earth look) */}
    <AbsoluteFill style={{background: lux ? 'linear-gradient(180deg, rgba(150,175,205,1) 0%, rgba(120,150,185,0.75) 10%, rgba(60,80,110,0) 30%)'
      : 'linear-gradient(180deg, rgba(178,204,232,1) 0%, rgba(178,204,232,0.85) 12%, rgba(178,204,232,0) 34%)',
      opacity: interpolate(cam.tilt, [8, 40], [0, 1], CL), pointerEvents: 'none'}} />
    {compass ? <div style={{position: 'absolute', top: 120, right: 70, width: 96, height: 96, borderRadius: 99, background: 'rgba(10,14,24,0.6)',
      border: '2px solid rgba(255,255,255,0.6)', transform: `rotate(${-cam.rot}deg)`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <svg width={60} height={60} viewBox="-30 -30 60 60"><polygon points="0,-26 8,0 -8,0" fill="#FF4D4D" /><polygon points="0,26 8,0 -8,0" fill="#fff" />
        <text x={0} y={-30} fill="#fff" fontSize={14} fontFamily="sans-serif" fontWeight={800} textAnchor="middle">N</text></svg>
    </div> : null}
    {credit ? <div style={{position: 'absolute', bottom: 26, left: 0, right: 0, textAlign: 'center', fontFamily: SANS, fontSize: 20, color: 'rgba(255,255,255,0.75)',
      textShadow: '0 1px 4px #000'}}>{credit}</div> : null}
  </AbsoluteFill>;
};

// ================================================================ tiny 3D projector
type V3 = [number, number, number];
type View = {yaw: number; pitch: number; dist: number; tx: number; ty: number; tz: number; f: number; cx: number; cy: number};
function project(p: V3, v: View): [number, number, number] {
  const cy = Math.cos(v.yaw), sy = Math.sin(v.yaw);
  const x0 = p[0] - v.tx, y0 = p[1] - v.ty, z0 = p[2] - v.tz;
  const x1 = x0 * cy - y0 * sy, y1 = x0 * sy + y0 * cy;
  const cp = Math.cos(v.pitch), sp = Math.sin(v.pitch);
  const X = x1, Y = y1 * sp + z0 * cp;
  const depth = v.dist + y1 * cp - z0 * sp;
  const s = v.f / Math.max(1, depth);
  return [v.cx + X * s, v.cy - Y * s, depth];
}
const ccw = (pts: number[][]) => {
  let a = 0;
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], q = pts[(i + 1) % pts.length];
    a += p[0] * q[1] - q[0] * p[1];
  }
  return a > 0 ? pts : [...pts].reverse();
};
const polyArea = (pts: number[][]) => Math.abs(pts.reduce((s, p, i) => {
  const q = pts[(i + 1) % pts.length];
  return s + p[0] * q[1] - q[0] * p[1];
}, 0)) / 2;
const centroid = (pts: number[][]) => [pts.reduce((s, p) => s + p[0], 0) / pts.length, pts.reduce((s, p) => s + p[1], 0) / pts.length];
const camDir = (v: View): V3 => { // unit vector from the scene towards the camera, in world coordinates
  const cp = Math.cos(v.pitch), sp = Math.sin(v.pitch), cy = Math.cos(v.yaw), sy = Math.sin(v.yaw);
  const y1 = -cp, z = sp; // in the yawed frame the camera sits at (0, -cos, sin)
  return [y1 * sy, y1 * cy, z];
};
const shade = (hex: string, k: number) => {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16);
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((x) => Math.max(0, Math.min(255, Math.round(x * k))));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
};
const bg3d = (dark: boolean) => dark ? 'radial-gradient(ellipse at 50% 35%, #1f2a44 0%, #0A0F1C 70%)' : T('radial-gradient(ellipse at 50% 35%, #FFFFFF 0%, #DCE4F5 75%)');

/**
 * Building3D: buildings [{pts: [[x,y],…] m (footprint from the drawing), floors, fh 3.3, color, at, name, base (m, podium
 * start height)}], style 'glass' | 'white' | 'wire', yaw0 / yaw1 (deg, orbit), pitch (deg, 28), zoom (1), dark (true),
 * title, sub, label_at.
 */
export const Building3D: React.FC<P> = ({duration, buildings = [], style = 'glass', yaw0 = -35, yaw1 = 25, pitch = 26, zoom = 1, dark = true,
  title, sub, label_at = 1.2}) => {
  const {frame, fps, t, W, H} = useT();
  const list = (buildings.length ? buildings : [{pts: [[0, 0], [24, 0], [24, 18], [0, 18]], floors: 20}]).map((b: any) => ({fh: 3.3, at: 0, base: 0, ...b, pts: ccw(b.pts)}));
  const all = list.flatMap((b: any) => b.pts);
  const minx = Math.min(...all.map((p: number[]) => p[0])), maxx = Math.max(...all.map((p: number[]) => p[0]));
  const miny = Math.min(...all.map((p: number[]) => p[1])), maxy = Math.max(...all.map((p: number[]) => p[1]));
  const topH = Math.max(...list.map((b: any) => b.base + b.floors * b.fh));
  const ext = Math.max(maxx - minx, maxy - miny, topH * 0.9);
  const yaw = ((yaw0 + (yaw1 - yaw0) * smooth(Math.min(1, t / Math.max(0.1, duration)))) * Math.PI) / 180;
  const view: View = {yaw, pitch: (pitch * Math.PI) / 180, dist: ext * 2.15 / zoom, tx: (minx + maxx) / 2, ty: (miny + maxy) / 2, tz: topH * 0.4,
    f: W * 1.25, cx: W / 2, cy: H * 0.6};
  const cd = camDir(view);
  const light: V3 = [-0.45, -0.6, 0.66];
  const faces: Array<{d: number; el: React.ReactNode}> = [];
  const o = Math.min(interpolate(t, [0, 0.2], [0, 1], CL), exit(frame, fps, duration, 0.25));
  const P2 = (p: V3) => project(p, view);
  // ground grid
  const grid: React.ReactNode[] = [];
  const g = Math.ceil(ext * 1.2 / 10) * 10, cxm = view.tx, cym = view.ty;
  for (let s = -g; s <= g; s += 10) {
    const a = P2([cxm + s, cym - g, 0]), b = P2([cxm + s, cym + g, 0]), c = P2([cxm - g, cym + s, 0]), d = P2([cxm + g, cym + s, 0]);
    grid.push(<line key={`gx${s}`} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={dark ? 'rgba(120,160,255,0.16)' : 'rgba(30,50,110,0.12)'} strokeWidth={1.5} />);
    grid.push(<line key={`gy${s}`} x1={c[0]} y1={c[1]} x2={d[0]} y2={d[1]} stroke={dark ? 'rgba(120,160,255,0.16)' : 'rgba(30,50,110,0.12)'} strokeWidth={1.5} />);
  }
  list.forEach((b: any, bi: number) => {
    const wire = lerp(t, b.at, b.at + 0.6, 0, 1, EASE_IN);
    const rise = (t - b.at - 0.4) / 0.11; // floors appear one every 0.11 s
    const nf = Math.max(0, Math.min(b.floors, rise));
    const h = b.base + nf * b.fh;
    const solid = style === 'wire' ? 0 : lerp(t, b.at + 0.3, b.at + 0.9);
    const col = b.color || (style === 'white' ? '#F4F6FA' : T('#6E92FF'));
    const n = b.pts.length;
    // shadow
    const sh = b.pts.map((p: number[]) => P2([p[0] + h * 0.35, p[1] - h * 0.25, 0]));
    if (h > 0) faces.push({d: 1e9 - bi, el: <polygon key={`s${bi}`} points={sh.map((q) => `${q[0]},${q[1]}`).join(' ')} fill="rgba(0,0,0,0.28)" />});
    // footprint outline (wire stage)
    const fp = b.pts.map((p: number[]) => P2([p[0], p[1], b.base]));
    const fl = pathLen([...fp, fp[0]].map((q) => [q[0], q[1]]));
    faces.push({d: 1e9 - 10 - bi, el: <polygon key={`fp${bi}`} points={fp.map((q) => `${q[0]},${q[1]}`).join(' ')} fill="none" stroke={dark ? '#9FC0FF' : T('#3158FF')}
      strokeWidth={3} strokeDasharray={`${fl * wire} ${fl}`} />});
    if (h <= b.base) return;
    for (let i = 0; i < n; i++) {
      const a = b.pts[i], c = b.pts[(i + 1) % n];
      const ex = c[0] - a[0], ey = c[1] - a[1], len = Math.hypot(ex, ey) || 1;
      const nrm: V3 = [ey / len, -ex / len, 0];
      if (nrm[0] * cd[0] + nrm[1] * cd[1] <= 0) continue; // back face
      const q = [P2([a[0], a[1], b.base]), P2([c[0], c[1], b.base]), P2([c[0], c[1], h]), P2([a[0], a[1], h])];
      const lit = 0.55 + 0.45 * Math.max(0, nrm[0] * light[0] + nrm[1] * light[1]);
      const fillc = style === 'glass' ? `url(#glass${bi})` : shade(col, lit);
      const lines: React.ReactNode[] = [];
      for (let f = 1; f <= Math.floor(nf); f++) {  // floor slabs
        const zz = b.base + f * b.fh;
        const p1 = P2([a[0], a[1], zz]), p2 = P2([c[0], c[1], zz]);
        lines.push(<line key={`f${f}`} x1={p1[0]} y1={p1[1]} x2={p2[0]} y2={p2[1]} stroke={style === 'white' ? '#FFFFFF' : 'rgba(220,235,255,0.7)'} strokeWidth={style === 'white' ? 7 : 2} />);
      }
      const mull = Math.max(1, Math.round(len / 2.6));
      if (style !== 'wire') for (let f = 0; f < Math.floor(nf); f++) for (let m = 0; m < mull; m++) {  // one window per bay per floor
        const r0 = (m + 0.16) / mull, r1 = (m + 0.84) / mull;
        const z0 = b.base + f * b.fh + b.fh * 0.22, z1 = b.base + f * b.fh + b.fh * 0.86;
        const wq = [P2([a[0] + ex * r0, a[1] + ey * r0, z0]), P2([a[0] + ex * r1, a[1] + ey * r1, z0]), P2([a[0] + ex * r1, a[1] + ey * r1, z1]), P2([a[0] + ex * r0, a[1] + ey * r0, z1])];
        lines.push(<polygon key={`wn${f}_${m}`} points={wq.map((x) => `${x[0]},${x[1]}`).join(' ')} fill={`url(#win${bi})`} opacity={solid} stroke="rgba(255,255,255,0.5)" strokeWidth={1} />);
      }
      const dd = (q[0][2] + q[1][2] + q[2][2] + q[3][2]) / 4;
      faces.push({d: dd, el: <g key={`w${bi}_${i}`}>
        <polygon points={q.map((p) => `${p[0]},${p[1]}`).join(' ')} fill={fillc} fillOpacity={0.25 + 0.75 * solid} stroke={dark ? '#CFE0FF' : T('#3158FF')}
          strokeWidth={2} strokeOpacity={0.9} style={{filter: style === 'glass' ? `brightness(${lit + 0.15})` : undefined}} />
        {lines}
      </g>});
    }
    const roof = b.pts.map((p: number[]) => P2([p[0], p[1], h]));
    faces.push({d: -1e6 + bi, el: <polygon key={`r${bi}`} points={roof.map((q) => `${q[0]},${q[1]}`).join(' ')} fill={style === 'glass' ? shade('#9DB4E6', 1) : shade(col, 1.05)}
      fillOpacity={0.3 + 0.7 * solid} stroke={dark ? '#E4EEFF' : T('#3158FF')} strokeWidth={2} />});
  });
  faces.sort((a, b) => b.d - a.d);
  const lp = title ? spring({frame: frame - label_at * fps, fps, config: {damping: 14, stiffness: 140}}) : 0;
  return <AbsoluteFill style={{background: bg3d(dark), opacity: o}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      <defs>{list.map((b: any, bi: number) => <linearGradient key={bi} id={`glass${bi}`} x1="0" y1="0" x2="0.4" y2="1">
        <stop offset="0" stopColor="#BFD6FF" /><stop offset="0.45" stopColor={b.color || '#4F78C9'} /><stop offset="1" stopColor="#1B2C55" />
      </linearGradient>)}{list.map((b: any, bi: number) => <linearGradient key={`w${bi}`} id={`win${bi}`} x1="0" y1="0" x2="0.6" y2="1">
        <stop offset="0" stopColor={style === 'glass' ? '#E6F0FF' : '#7FA3C9'} /><stop offset="0.5" stopColor={style === 'glass' ? '#8FB0E8' : '#2B3F5C'} /><stop offset="1" stopColor="#16233A" />
      </linearGradient>)}</defs>
      {grid}
      {faces.map((f) => f.el)}
    </svg>
    {title ? <div style={{position: 'absolute', top: H * 0.1, left: 0, right: 0, textAlign: 'center', opacity: Math.min(1, lp * 1.4),
      transform: `translateY(${(1 - lp) * 30}px)`}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 84, color: dark ? '#fff' : T('#0E1530'), letterSpacing: '-0.02em'}}>{title}</div>
      {sub ? <div style={{fontFamily: SANS, fontWeight: 600, fontSize: 36, color: dark ? GOLD : T('#3158FF'), marginTop: 8}}>{sub}</div> : null}
    </div> : null}
  </AbsoluteFill>;
};

/**
 * FloorPlan2D: rooms [{name, pts: [[x,y],…] m, color}], wall_h 2.8, extrude_at (s, when it tilts into 3D; null = stays 2D),
 * yaw (deg, 3D view), title, sub, dims (true: overall width / depth dimension lines), dark (false),
 * doors / windows [{pts: [[x1,y1],[x2,y2]]}] (m, lying on a wall; a door swings from pts[0]). scripts/floorplan.py makes all of
 * this from a photo of the drawing.
 */
export const FloorPlan2D: React.FC<P> = ({duration, rooms = [], doors = [], windows = [], wall_h = 2.8, extrude_at = 3.2, yaw = -30, title, sub, dims = true, dark = false}) => {
  const {frame, fps, t, W, H} = useT();
  const R = (rooms.length ? rooms : [{name: 'Phòng khách', pts: [[0, 0], [5, 0], [5, 6], [0, 6]]}, {name: 'Bếp', pts: [[0, 6], [5, 6], [5, 9], [0, 9]]},
    {name: 'Ngủ', pts: [[0, 9], [5, 9], [5, 13], [0, 13]]}]).map((r: any) => ({...r, pts: ccw(r.pts)}));
  const all = R.flatMap((r: any) => r.pts);
  const minx = Math.min(...all.map((p: number[]) => p[0])), maxx = Math.max(...all.map((p: number[]) => p[0]));
  const miny = Math.min(...all.map((p: number[]) => p[1])), maxy = Math.max(...all.map((p: number[]) => p[1]));
  const ext = Math.max(maxx - minx, maxy - miny);
  const e3 = extrude_at == null ? 0 : lerp(t, extrude_at, extrude_at + 1.6, 0, 1, (x) => smooth(x));
  const pitchDeg = 90 - 52 * e3, yawDeg = yaw * e3;
  const fit = Math.min((W * 0.78) / Math.max(1, maxx - minx), (H * 0.6) / Math.max(1, maxy - miny)); // px per metre in the 2D view
  const view: View = {yaw: (yawDeg * Math.PI) / 180, pitch: (pitchDeg * Math.PI) / 180, dist: ((W * 1.05) / fit) * (1 + 0.55 * e3), tx: (minx + maxx) / 2, ty: (miny + maxy) / 2, tz: 0,
    f: W * 1.05, cx: W / 2, cy: H * (0.47 + 0.03 * e3)};
  const P2 = (p: V3) => project(p, view);
  const o = Math.min(interpolate(t, [0, 0.2], [0, 1], CL), exit(frame, fps, duration, 0.25));
  const wallP = lerp(t, 0.15, 1.4, 0, 1, (x) => smooth(x));
  const h = wall_h * e3;
  const ink = dark ? '#EAF0FF' : '#1B2333';
  const pal = ['#FFE7B8', '#D8ECFF', '#DFF5E1', '#FCE1E4', '#EDE3FF', '#FFF3D6'];
  // unique wall segments
  const segs: Array<[number[], number[]]> = [];
  const seen = new Set<string>();
  R.forEach((r: any) => r.pts.forEach((p: number[], i: number) => {
    const q = r.pts[(i + 1) % r.pts.length];
    const kk = [p, q].map((x) => `${x[0].toFixed(2)},${x[1].toFixed(2)}`).sort().join('|');
    if (!seen.has(kk)) {
      seen.add(kk);
      segs.push([p, q]);
    }
  }));
  const floorEls = R.map((r: any, i: number) => {
    const fp = lerp(t, 1.2 + i * 0.18, 1.6 + i * 0.18);
    const q = r.pts.map((p: number[]) => P2([p[0], p[1], 0]));
    return <polygon key={`fl${i}`} points={q.map((x) => `${x[0]},${x[1]}`).join(' ')} fill={r.color || pal[i % pal.length]} fillOpacity={fp} />;
  });
  const cd = camDir(view);
  // openings cut the walls they sit on: doors leave a gap (+ swing arc, lintel in 3D), windows keep a sill + header
  const opens: Array<{pts: number[][]; kind: 'door' | 'window'}> = [
    ...doors.map((d: any) => ({pts: d.pts || d, kind: 'door' as const})), ...windows.map((w: any) => ({pts: w.pts || w, kind: 'window' as const}))];
  type Piece = {a: number[]; b: number[]; kind: 'wall' | 'door' | 'window'};
  const pieces: Piece[] = [];
  segs.forEach(([a, b]) => {
    const ex = b[0] - a[0], ey = b[1] - a[1], len = Math.hypot(ex, ey) || 1;
    const ux = ex / len, uy = ey / len;
    const cuts: Array<[number, number, 'door' | 'window']> = [];
    opens.forEach((o) => {
      const [p, q] = o.pts;
      const off = (pt: number[]) => Math.abs((pt[0] - a[0]) * uy - (pt[1] - a[1]) * ux);
      if (off(p) > 0.2 || off(q) > 0.2) return;
      let t1 = (p[0] - a[0]) * ux + (p[1] - a[1]) * uy, t2 = (q[0] - a[0]) * ux + (q[1] - a[1]) * uy;
      if (t1 > t2) [t1, t2] = [t2, t1];
      t1 = Math.max(0, t1);
      t2 = Math.min(len, t2);
      if (t2 - t1 > 0.2) cuts.push([t1, t2, o.kind]);
    });
    cuts.sort((x, y) => x[0] - y[0]);
    let cur = 0;
    const at = (s: number) => [a[0] + ux * s, a[1] + uy * s];
    cuts.forEach(([t1, t2, kind]) => {
      if (t1 > cur + 0.01) pieces.push({a: at(cur), b: at(t1), kind: 'wall'});
      pieces.push({a: at(Math.max(cur, t1)), b: at(t2), kind});
      cur = Math.max(cur, t2);
    });
    if (len > cur + 0.01) pieces.push({a: at(cur), b: at(len), kind: 'wall'});
  });
  const opP = lerp(t, 1.3, 1.8);
  const quad = (a: number[], b: number[], z0: number, z1: number) => [P2([a[0], a[1], z0]), P2([b[0], b[1], z0]), P2([b[0], b[1], z1]), P2([a[0], a[1], z1])];
  const pts = (q: number[][]) => q.map((x) => `${x[0]},${x[1]}`).join(' ');
  const walls = pieces.map(({a, b, kind}, i) => {
    const q = quad(a, b, 0, h);
    const dd = (q[0][2] + q[1][2]) / 2;
    const ex = b[0] - a[0], ey = b[1] - a[1], len = Math.hypot(ex, ey) || 1;
    const lit = 0.8 + 0.2 * Math.abs((ey / len) * cd[0] - (ex / len) * cd[1]);
    const wallFill = shade(dark ? '#3A4766' : '#E9EDF4', lit);
    if (kind === 'door') {
      const nx = -ey / len, ny = ex / len; // swing towards the left normal, quarter circle from b around a
      const arc: number[][] = [];
      for (let s = 0; s <= 12; s++) {
        const th = (s / 12) * (Math.PI / 2);
        arc.push(P2([a[0] + (ex * Math.cos(th) + nx * len * Math.sin(th)), a[1] + (ey * Math.cos(th) + ny * len * Math.sin(th)), 0.02]));
      }
      const leaf = P2([a[0] + nx * len, a[1] + ny * len, 0.02]), hinge = P2([a[0], a[1], 0.02]);
      return {d: dd, el: <g key={`dr${i}`} opacity={opP}>
        <polyline points={pts(arc)} fill="none" stroke={ink} strokeWidth={2} strokeDasharray="6 5" strokeOpacity={0.7} />
        <line x1={hinge[0]} y1={hinge[1]} x2={leaf[0]} y2={leaf[1]} stroke={ink} strokeWidth={3} />
        {h > 2.15 ? <polygon points={pts(quad(a, b, 2.1, h))} fill={wallFill} fillOpacity={0.42} stroke={ink} strokeWidth={1.2} strokeOpacity={0.5} /> : null}
      </g>};
    }
    if (kind === 'window') {
      const nx = (-ey / len) * 0.07, ny = (ex / len) * 0.07;
      const l1 = [P2([a[0] + nx, a[1] + ny, Math.min(h, 0.9)]), P2([b[0] + nx, b[1] + ny, Math.min(h, 0.9)])];
      const l2 = [P2([a[0] - nx, a[1] - ny, Math.min(h, 0.9)]), P2([b[0] - nx, b[1] - ny, Math.min(h, 0.9)])];
      return {d: dd, el: <g key={`wd${i}`} opacity={opP}>
        {h > 0.05 ? <polygon points={pts(quad(a, b, 0, Math.min(h, 0.9)))} fill={wallFill} fillOpacity={0.42} stroke={ink} strokeWidth={1.2} strokeOpacity={0.5} /> : null}
        {h > 0.95 ? <polygon points={pts(quad(a, b, 0.9, Math.min(h, 2.1)))} fill="#9CCBFF" fillOpacity={0.35} stroke="#3C8DFF" strokeWidth={1.5} /> : null}
        {h > 2.15 ? <polygon points={pts(quad(a, b, 2.1, h))} fill={wallFill} fillOpacity={0.42} stroke={ink} strokeWidth={1.2} strokeOpacity={0.5} /> : null}
        {[l1, l2].map((l, k) => <line key={k} x1={l[0][0]} y1={l[0][1]} x2={l[1][0]} y2={l[1][1]} stroke="#3C8DFF" strokeWidth={3} />)}
      </g>};
    }
    return {d: dd, el: <g key={`wl${i}`}>
      {h > 0.05 ? <polygon points={pts(q)} fill={wallFill} fillOpacity={0.42} stroke={ink} strokeWidth={1.2} strokeOpacity={0.5} /> : null}
      <line x1={q[3][0]} y1={q[3][1]} x2={q[2][0]} y2={q[2][1]} stroke={ink} strokeWidth={h > 0.05 ? 5 : 9} strokeLinecap="square"
        strokeDasharray={`${Math.hypot(q[2][0] - q[3][0], q[2][1] - q[3][1]) * wallP} 9999`} />
    </g>};
  }).sort((a, b) => b.d - a.d);
  const labels = R.map((r: any, i: number) => {
    const c = centroid(r.pts);
    const p = P2([c[0], c[1], h * 0.02]);
    const lp = spring({frame: frame - (1.4 + i * 0.18) * fps, fps, config: {damping: 13, stiffness: 160, mass: 0.6}});
    const rw = Math.max(...r.pts.map((q: number[]) => q[0])) - Math.min(...r.pts.map((q: number[]) => q[0]));
    const fs = Math.max(16, Math.min(34, (rw * fit * 0.9) / Math.max(4, String(r.name).length * 0.58))); // narrow rooms get smaller text
    return <div key={`lb${i}`} style={{position: 'absolute', left: p[0], top: p[1], transform: `translate(-50%,-50%) scale(${0.6 + 0.4 * lp})`, opacity: Math.min(1, lp * 1.5),
      textAlign: 'center', fontFamily: SANS, color: ink, whiteSpace: 'nowrap', textShadow: dark ? '0 2px 8px #000' : '0 1px 6px rgba(255,255,255,0.9)'}}>
      <div style={{fontWeight: 800, fontSize: fs}}>{r.name}</div>
      <div style={{fontWeight: 600, fontSize: fs * 0.8, opacity: 0.75}}>{fmt(polyArea(r.pts))} m²</div>
    </div>;
  });
  const dimOp = dims ? lerp(t, 1.0, 1.5) * (1 - e3) : 0;
  const d1a = P2([minx, miny - ext * 0.06, 0]), d1b = P2([maxx, miny - ext * 0.06, 0]);
  const d2a = P2([maxx + ext * 0.06, miny, 0]), d2b = P2([maxx + ext * 0.06, maxy, 0]);
  const tp = title ? spring({frame: frame - 0.3 * fps, fps, config: {damping: 14, stiffness: 140}}) : 0;
  return <AbsoluteFill style={{background: dark ? bg3d(true) : 'linear-gradient(180deg,#FFFFFF,#EEF1F6)', opacity: o}}>
    <AbsoluteFill style={{backgroundImage: `linear-gradient(${dark ? 'rgba(255,255,255,0.05)' : 'rgba(20,40,90,0.06)'} 2px, transparent 2px), linear-gradient(90deg, ${dark ? 'rgba(255,255,255,0.05)' : 'rgba(20,40,90,0.06)'} 2px, transparent 2px)`,
      backgroundSize: '60px 60px', opacity: 1 - e3 * 0.6}} />
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      {floorEls}
      {walls.map((w) => w.el)}
      <g opacity={dimOp} stroke={ink} strokeWidth={2} fill={ink} fontFamily="sans-serif" fontWeight={700} fontSize={30}>
        <line x1={d1a[0]} y1={d1a[1]} x2={d1b[0]} y2={d1b[1]} /><line x1={d2a[0]} y1={d2a[1]} x2={d2b[0]} y2={d2b[1]} />
        {[d1a, d1b, d2a, d2b].map((p, i) => <circle key={i} cx={p[0]} cy={p[1]} r={5} />)}
        <text x={(d1a[0] + d1b[0]) / 2} y={d1a[1] + 44} textAnchor="middle" stroke="none">{fmt(maxx - minx)} m</text>
        <text x={d2a[0] + 18} y={(d2a[1] + d2b[1]) / 2} stroke="none">{fmt(maxy - miny)} m</text>
      </g>
    </svg>
    {labels}
    {title ? <div style={{position: 'absolute', top: H * 0.07, left: 0, right: 0, textAlign: 'center', opacity: Math.min(1, tp * 1.4), transform: `translateY(${(1 - tp) * 24}px)`}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 76, color: dark ? '#fff' : T('#0E1530'), letterSpacing: '-0.02em'}}>{title}</div>
      {sub ? <div style={{fontFamily: SERIF, fontStyle: 'italic', fontSize: 40, color: dark ? GOLD : T('#3158FF'), marginTop: 6}}>{sub}</div> : null}
    </div> : null}
  </AbsoluteFill>;
};

/**
 * LotCard: the plot's data sheet sliding in over the map. props: title ("LÔ 07"), rows [{k: "Diện tích", v: "100 m²"}, …]
 * (each row ticks in, every `step` s), price, price_note, facing ("Tây Bắc": a compass needle points there), y (0.6), at.
 */
export const LotCard: React.FC<P> = ({duration, title = 'LÔ 01', rows = [], price, price_note, facing, y = 0.6, at = 0, step = 0.22, color = GOLD, look = 'luxury'}) => {
  const {frame, fps, t, W, H} = useT();
  const s = spring({frame: frame - at * fps, fps, config: {damping: 15, stiffness: 140, mass: 0.7}});
  const o = exit(frame, fps, duration, 0.3);
  const DEG: Record<string, number> = {'Bắc': 0, 'Đông Bắc': 45, 'Đông': 90, 'Đông Nam': 135, 'Nam': 180, 'Tây Nam': 225, 'Tây': 270, 'Tây Bắc': 315};
  const needle = facing && DEG[facing] != null ? DEG[facing] : null;
  const np = lerp(t, at + 0.4, at + 1.2, 0, 1, (x) => smooth(x));
  return <AbsoluteFill style={{opacity: o}}>
    {look === 'luxury' ? <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, top: H * (y - 0.12),
      background: 'linear-gradient(180deg, rgba(4,8,14,0) 0%, rgba(4,8,14,0.72) 28%, rgba(4,8,14,0.9) 100%)', opacity: Math.min(1, s * 1.4)}} /> : null}
    <div style={{position: 'absolute', left: W * 0.07, right: W * 0.07, top: H * y, transform: `translateY(${(1 - s) * 140}px)`, opacity: Math.min(1, s * 1.4),
      ...(look === 'luxury' ? {padding: '10px 6px', textShadow: LUX.shadow}
        : {borderRadius: 30, background: 'rgba(10,14,24,0.88)', border: `2px solid ${color}88`, boxShadow: '0 30px 80px rgba(0,0,0,0.5)', padding: '30px 38px'}),
      fontFamily: SANS, color: '#fff'}}>
      <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 18}}>
        <div style={look === 'luxury' ? {...LUX.num, fontSize: 92, lineHeight: 1} : {fontWeight: 800, fontSize: 54, letterSpacing: '-0.01em'}}>{title}</div>
        {needle != null ? <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
          <svg width={74} height={74} viewBox="-37 -37 74 74"><circle r={34} fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth={2} />
            <text x={0} y={-22} fill="#fff" fontSize={13} fontWeight={800} textAnchor="middle" fontFamily="sans-serif">B</text>
            <g transform={`rotate(${needle * np})`}><polygon points="0,-26 7,4 -7,4" fill={color} /><circle r={4} fill="#fff" /></g></svg>
          <div style={{fontWeight: 700, fontSize: 28, color}}>{facing}</div>
        </div> : null}
      </div>
      {rows.map((r: any, i: number) => {
        const p = lerp(t, at + 0.35 + i * step, at + 0.6 + i * step);
        return look === 'luxury' ? <div key={i} style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', padding: '14px 0',
          borderTop: `1px solid ${i ? 'rgba(255,255,255,0.22)' : color}`, opacity: p, transform: `translateX(${(1 - p) * 30}px)`}}>
          <span style={{...LUX.cap, fontSize: 23, color: 'rgba(255,255,255,0.78)'}}>{r.k}</span><span style={{...LUX.num, fontSize: 48}}>{r.v}</span></div>
          : <div key={i} style={{display: 'flex', justifyContent: 'space-between', padding: '12px 0', borderTop: '1px solid rgba(255,255,255,0.12)',
          opacity: p, transform: `translateX(${(1 - p) * 30}px)`, fontSize: 32}}>
          <span style={{color: 'rgba(255,255,255,0.7)', fontWeight: 600}}>{r.k}</span><span style={{fontWeight: 800}}>{r.v}</span></div>;
      })}
      {price ? (() => {
        const p = lerp(t, at + 0.45 + rows.length * step, at + 0.8 + rows.length * step);
        return <div style={{marginTop: 14, paddingTop: 16, borderTop: `2px solid ${color}66`, opacity: p, transform: `scale(${0.9 + 0.1 * p})`, transformOrigin: 'left center'}}>
          <div style={look === 'luxury' ? {...LUX.num, fontSize: 84, color, lineHeight: 1.05} : {fontWeight: 800, fontSize: 58, color}}>{price}</div>
          {price_note ? <div style={{fontWeight: 600, fontSize: 24, color: 'rgba(255,255,255,0.6)'}}>{price_note}</div> : null}
        </div>;
      })() : null}
    </div>
  </AbsoluteFill>;
};


// ================================================================ globe, knockout / invert titles, lens flare
const TEX: Record<string, ImageData> = {};
/**
 * GlobeIntro: the Earth (textured from geo.py's world mosaic, Web-Mercator) spins to the site and the camera dives in
 * through a cloud layer — the "Zoom Earth" opener. props: world (image), lat, lon, spin (deg of rotation, 140),
 * dive_at (s, 0.45 of the clip), title, sub. Put the GeoMap fly-in right after it (cut on the cloud flash).
 */
export const GlobeIntro: React.FC<P> = ({duration, world, lat = 16, lon = 108, spin = 140, dive_at, title, sub, color = GOLD}) => {
  const {frame, fps, t, W, H} = useT();
  const ref = React.useRef<HTMLCanvasElement>(null);
  const [ready, setReady] = React.useState(!!(world && TEX[world]));
  const [h0] = React.useState(() => (world && !TEX[world] ? delayRender('globe texture') : null));
  React.useEffect(() => {
    if (!world || TEX[world]) return;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = img.width; c.height = img.height;
      const g = c.getContext('2d')!;
      g.drawImage(img, 0, 0);
      TEX[world] = g.getImageData(0, 0, img.width, img.height);
      setReady(true);
      if (h0 != null) continueRender(h0);
    };
    img.onerror = () => { if (h0 != null) continueRender(h0); };
    img.src = url(world);
  }, [world, h0]);
  const da = dive_at ?? duration * 0.45;
  const sp = smooth(Math.min(1, t / Math.max(0.1, da + 0.6)));
  const lon0 = lon - spin * (1 - sp), lat0 = lat * (0.4 + 0.6 * sp);
  const dive = Math.max(0, (t - da) / Math.max(0.1, duration - da));
  const R = W * 0.36 * Math.pow(9, Math.pow(dive, 1.6)); // sphere radius in px, grows ~9× during the dive
  React.useEffect(() => {
    const cv = ref.current;
    if (!cv || !ready || !world) return;
    const hd = delayRender('globe frame');
    const S = 2, cw = Math.ceil(W / S), ch = Math.ceil(H / S);
    const g = cv.getContext('2d')!;
    const out = g.createImageData(cw, ch);
    const tex = TEX[world], tw = tex.width, th = tex.height, td = tex.data, od = out.data;
    const r = R / S, cx = cw / 2, cy = ch * 0.5;
    const phi0 = (lat0 * Math.PI) / 180, lam0 = (lon0 * Math.PI) / 180, sp0 = Math.sin(phi0), cp0 = Math.cos(phi0);
    for (let y = 0; y < ch; y++) {
      const ny = (cy - y) / r;
      for (let x = 0; x < cw; x++) {
        const nx = (x - cx) / r, rho2 = nx * nx + ny * ny, o = (y * cw + x) * 4;
        if (rho2 > 1) {
          const glow = Math.max(0, 1 - (Math.sqrt(rho2) - 1) * 6); // atmosphere rim
          od[o] = 60 * glow; od[o + 1] = 140 * glow; od[o + 2] = 255 * glow; od[o + 3] = 255 * glow;
          continue;
        }
        const cz = Math.sqrt(1 - rho2);
        const phi = Math.asin(cz * sp0 + ny * cp0);
        const lam = lam0 + Math.atan2(nx, cz * cp0 - ny * sp0);
        const u = (((lam * 180) / Math.PI + 180) / 360) % 1;
        const latc = Math.max(-1.48, Math.min(1.48, phi));
        const v = 0.5 - Math.log(Math.tan(Math.PI / 4 + latc / 2)) / (2 * Math.PI);
        const ti = (Math.min(th - 1, Math.max(0, Math.floor(v * th))) * tw + Math.floor(((u + 1) % 1) * tw)) * 4;
        const shade = 0.35 + 0.65 * Math.max(0, cz * 0.8 + nx * -0.25 + ny * 0.25); // sun from the upper left
        od[o] = td[ti] * shade; od[o + 1] = td[ti + 1] * shade; od[o + 2] = td[ti + 2] * shade; od[o + 3] = 255;
      }
    }
    g.putImageData(out, 0, 0);
    continueRender(hd);
  }, [frame, ready, R, lat0, lon0, W, H, world]);
  const cloud = interpolate(dive, [0.55, 0.85, 1], [0, 1, 0.9], CL);
  const tp = title ? spring({frame: frame - 0.4 * fps, fps, config: {damping: 16, stiffness: 120}}) * (1 - interpolate(dive, [0, 0.3], [0, 1], CL)) : 0;
  return <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 50%, #0B1630 0%, #02040A 70%)', overflow: 'hidden'}}>
    {Array.from({length: 90}).map((_, i) => <div key={i} style={{position: 'absolute', left: `${(i * 97.3) % 100}%`, top: `${(i * 53.7) % 100}%`, width: i % 7 ? 2 : 3,
      height: i % 7 ? 2 : 3, borderRadius: 9, background: '#fff', opacity: 0.25 + ((i * 31) % 10) / 16}} />)}
    <canvas ref={ref} width={Math.ceil(W / 2)} height={Math.ceil(H / 2)} style={{position: 'absolute', inset: 0, width: W, height: H}} />
    <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 50%, rgba(255,255,255,${cloud}) 0%, rgba(235,242,250,${cloud * 0.95}) 45%, rgba(200,215,235,${cloud * 0.8}) 100%)`}} />
    {title ? <div style={{position: 'absolute', top: H * 0.14, left: 0, right: 0, textAlign: 'center', opacity: tp, textShadow: LUX.shadow}}>
      <div style={{...LUX.cap, fontSize: 30, color: '#fff', paddingLeft: '0.26em'}}>{title}</div>
      {sub ? <div style={{...LUX.num, fontSize: 52, color, marginTop: 6}}>{sub}</div> : null}
    </div> : null}
  </AbsoluteFill>;
};

/**
 * KnockoutText: a solid card with the words cut out, the video showing through the letters; then the camera flies
 * through a letter into the scene. props: text, sub, bg ('#F7F4EE'), ink (sub colour), size (300), at, fly_at, fly_x / fly_y
 * (where the dive goes, 0–1), fly_dur (1.0).
 */
export const KnockoutText: React.FC<P> = ({duration, text = 'LÀNG VÂN', sub, bg = '#F7F4EE', ink = '#1B2333', size = 300, at = 0, fly_at, fly_x = 0.5, fly_y = 0.47, fly_dur = 1.0}) => {
  const {frame, fps, t, W, H} = useT();
  const fa = fly_at ?? duration - fly_dur - 0.1;
  const f = Math.max(0, Math.min(1, (t - fa) / fly_dur));
  const sc = Math.pow(40, Math.pow(f, 2.2));
  const op = interpolate(t, [at, at + 0.35], [0, 1], CL) * (1 - interpolate(f, [0.7, 1], [0, 1], CL));
  const lines = String(text).split('\n');
  const fs = Math.min(size, (W * 0.9) / Math.max(...lines.map((l) => l.length * 0.62)));
  const id = `ko${frame}`;
  return <AbsoluteFill style={{opacity: op}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, transformOrigin: `${fly_x * 100}% ${fly_y * 100}%`, transform: `scale(${sc})`}}>
      <defs><mask id={id}><rect width={W} height={H} fill="#fff" />
        {lines.map((l, i) => <text key={i} x={W / 2} y={H * fly_y + (i - (lines.length - 1) / 2) * fs * 0.95 + fs * 0.35} textAnchor="middle"
          fontFamily="BVP, sans-serif" fontWeight={800} fontSize={fs} letterSpacing={-fs * 0.02} fill="#000">{l}</text>)}
      </mask></defs>
      <rect width={W} height={H} fill={bg} mask={`url(#${id})`} />
    </svg>
    {sub ? <div style={{position: 'absolute', top: H * fly_y + (lines.length / 2) * fs * 0.95 + 30, left: 0, right: 0, textAlign: 'center', ...LUX.cap,
      fontSize: 28, color: ink, paddingLeft: '0.26em', opacity: 1 - f * 3}}>{sub}</div> : null}
  </AbsoluteFill>;
};

/**
 * InvertTitle: huge words sliding across the frame. Use the overlay with "blend": "difference" so the letters invert
 * whatever is behind them (chữ âm bản: dark over the sky, light over the buildings). props: text, size (260), y (0.45),
 * dir (1 = right to left), speed (frame widths per clip, 0.5), weight.
 */
export const InvertTitle: React.FC<P> = ({duration, text = 'SIÊU DỰ ÁN', size = 260, y = 0.45, dir = 1, speed = 0.5, weight = 800, sub}) => {
  const {frame, fps, t, W, H} = useT();
  const x = (0.5 + dir * (0.25 - (t / duration) * speed)) * W;
  const op = Math.min(interpolate(t, [0, 0.25], [0, 1], CL), exit(frame, fps, duration, 0.3));
  return <AbsoluteFill style={{opacity: op}}>
    <div style={{position: 'absolute', left: x, top: H * y, transform: 'translate(-50%,-50%)', whiteSpace: 'nowrap', fontFamily: SANS, fontWeight: weight,
      fontSize: size, letterSpacing: '-0.03em', color: '#fff', lineHeight: 1}}>{text}</div>
    {sub ? <div style={{position: 'absolute', left: 0, right: 0, top: H * y + size * 0.62, textAlign: 'center', ...LUX.cap, fontSize: 30, color: '#fff',
      paddingLeft: '0.26em'}}>{sub}</div> : null}
  </AbsoluteFill>;
};

/**
 * LensFlare: anamorphic streak + ghosts that slide as if the sun moved past the lens. Use with "blend": "screen".
 * props: x0 → x1, y (0–1), at, dur, color ('#FFB561'), size (1).
 */
export const LensFlare: React.FC<P> = ({duration, x0 = 0.15, x1 = 0.85, y = 0.22, at = 0, dur, color = '#FFB561', size = 1}) => {
  const {t, W, H} = useT();
  const d = dur ?? duration;
  const p = smooth(Math.max(0, Math.min(1, (t - at) / d)));
  const a = Math.sin(Math.PI * Math.max(0, Math.min(1, (t - at) / d)));
  const sx = (x0 + (x1 - x0) * p) * W, sy = y * H, cx = W / 2, cy = H / 2;
  const ghosts = [0.35, 0.7, 1.25, 1.6];
  return <AbsoluteFill style={{opacity: a}}>
    <div style={{position: 'absolute', left: sx, top: sy, width: W * 1.6 * size, height: 10 * size, transform: 'translate(-50%,-50%)',
      background: `linear-gradient(90deg, transparent, ${color}55 30%, #fff 50%, ${color}55 70%, transparent)`, filter: 'blur(3px)'}} />
    <div style={{position: 'absolute', left: sx, top: sy, width: 260 * size, height: 260 * size, transform: 'translate(-50%,-50%)', borderRadius: '50%',
      background: `radial-gradient(circle, #fff 0%, ${color}cc 12%, ${color}33 40%, transparent 70%)`}} />
    {ghosts.map((g, i) => {
      const gx = sx + (cx - sx) * g * 2, gy = sy + (cy - sy) * g * 2, r = (40 + i * 34) * size;
      return <div key={i} style={{position: 'absolute', left: gx, top: gy, width: r, height: r, transform: 'translate(-50%,-50%)', borderRadius: '50%',
        border: `2px solid ${i % 2 ? '#7FD3FF55' : color + '55'}`, background: `radial-gradient(circle, transparent 55%, ${i % 2 ? '#7FD3FF22' : color + '22'} 100%)`}} />;
    })}
  </AbsoluteFill>;
};

// ================================================================ on real footage
/**
 * TrackedPlot: graphics glued to the ground of a drone shot. render.py fills `frames` (one homography per frame) from
 * props.track = {corners: [[x, y] ×4]} (fractions of the frame at the overlay start: the plot). props: ring (defaults to the
 * corners), draw_at (0.2), draw (1.4), edges ["5 m", "20 m", …] (one per edge), area ("100 m²"), facing, labels
 * [{at: [x, y], text, sub, t}], ground {text, sub} (big text lying on the plot), drops [{src (PNG cut-out), at: [x, y],
 * w (fraction of the frame width at the start), t}], focus (darken outside the plot), color.
 */
export const TrackedPlot: React.FC<P> = ({duration, frames = [], track = {}, ring, draw_at = 0.2, draw = 1.4, edges = [], area, facing, labels = [],
  ground, drops = [], focus = 0, color = GOLD}) => {
  const {frame, fps, t, W, H} = useT();
  const M = frames.length ? frames[Math.min(frame, frames.length - 1)] : [1, 0, 0, 0, 1, 0, 0, 0, 1];
  const ref = (ring || track.corners || [[0.3, 0.55], [0.7, 0.55], [0.72, 0.72], [0.28, 0.72]]).map((q: number[]) => [q[0] * W, q[1] * H]);
  const P2 = (q: number[]) => {
    const w = M[6] * q[0] + M[7] * q[1] + M[8];
    return [(M[0] * q[0] + M[1] * q[1] + M[2]) / w, (M[3] * q[0] + M[4] * q[1] + M[5]) / w];
  };
  const scaleAt = (q: number[]) => { // local size change of the ground around q
    const a = P2(q), b = P2([q[0] + 10, q[1]]), c = P2([q[0], q[1] + 10]);
    return Math.sqrt(Math.abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))) / 10;
  };
  const rp = ref.map(P2);
  const L = pathLen([...rp, rp[0]]);
  const dp = lerp(t, draw_at, draw_at + draw, 0, 1, (x) => smooth(x));
  const after = lerp(t, draw_at + draw, draw_at + draw + 0.5);
  const d = rp.map((q: number[]) => q.join(',')).join(' ');
  const c = centroid(rp);
  const mat = `matrix3d(${M[0]},${M[3]},0,${M[6]},${M[1]},${M[4]},0,${M[7]},0,0,1,0,${M[2]},${M[5]},0,${M[8]})`;
  const o = exit(frame, fps, duration, 0.3);
  const rc = centroid(ref);
  return <AbsoluteFill style={{opacity: o}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      <defs><filter id="tglow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5" result="b" />
        <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
      {focus ? <path fillRule="evenodd" fill="#02060C" opacity={focus * after} d={`M0 0 H${W} V${H} H0 Z M${rp.map((q: number[]) => q.join(' ')).join(' L')} Z`} /> : null}
      <polygon points={d} fill={color} fillOpacity={0.16 * after} />
      <polygon points={d} fill="none" stroke={color} strokeWidth={5} strokeLinejoin="round" strokeDasharray={`${L * dp} ${L}`} filter="url(#tglow)" />
      <polygon points={d} fill="none" stroke="#fff" strokeWidth={3.5} strokeDasharray={`${L * 0.05} ${L}`} strokeDashoffset={-((L * (dp < 1 ? dp : 1 + (t - draw_at - draw) * 0.3)) % L)} />
      {rp.map((q: number[], i: number) => <circle key={i} cx={q[0]} cy={q[1]} r={5 + 3 * Math.sin(t * 5 + i)} fill="#fff" opacity={after} />)}
    </svg>
    {ground ? <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0', transform: mat, opacity: after}}>
      <div style={{position: 'absolute', left: rc[0], top: rc[1], transform: 'translate(-50%,-50%)', textAlign: 'center', whiteSpace: 'nowrap', textShadow: '0 2px 12px rgba(0,0,0,0.6)'}}>
        <div style={{...LUX.cap, fontSize: ground.size || 64, color: '#fff', paddingLeft: '0.26em'}}>{ground.text}</div>
        {ground.sub ? <div style={{...LUX.num, fontSize: (ground.size || 64) * 0.7, color}}>{ground.sub}</div> : null}
      </div>
    </div> : null}
    {edges.map((e: string, i: number) => {
      const a = rp[i], b = rp[(i + 1) % rp.length];
      if (!a || !b || !e) return null;
      const m = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], dx = m[0] - c[0], dy = m[1] - c[1], dl = Math.hypot(dx, dy) || 1;
      return <div key={`e${i}`} style={{position: 'absolute', left: m[0] + (dx / dl) * 44, top: m[1] + (dy / dl) * 44, transform: 'translate(-50%,-50%)',
        opacity: after, ...LUX.num, fontSize: 36, color: '#fff', textShadow: LUX.shadow, whiteSpace: 'nowrap'}}>{e}</div>;
    })}
    {area ? <div style={{position: 'absolute', left: c[0], top: Math.min(...rp.map((q: number[]) => q[1])) - 70, transform: 'translate(-50%,-100%)', opacity: after,
      textAlign: 'center', textShadow: LUX.shadow}}>
      <div style={{...LUX.num, fontSize: 64, color: '#fff'}}>{area}</div>
      {facing ? <div style={{...LUX.cap, fontSize: 20, color}}>Hướng {facing}</div> : null}
    </div> : null}
    {labels.map((lb: any, i: number) => {
      const q = P2([lb.at[0] * W, lb.at[1] * H]);
      const lp = spring({frame: frame - (lb.t ?? draw_at + draw) * fps, fps, config: {damping: 13, stiffness: 150, mass: 0.6}});
      return lp > 0.01 ? <div key={`l${i}`} style={{position: 'absolute', left: q[0], top: q[1], transform: `translate(-50%,-100%) translateY(${(1 - lp) * 30}px)`,
        opacity: Math.min(1, lp * 1.5), display: 'flex', flexDirection: 'column', alignItems: 'center', textShadow: LUX.shadow}}>
        <div style={{...LUX.cap, fontSize: 21, color: '#fff', whiteSpace: 'nowrap', paddingLeft: '0.26em'}}>{lb.text}</div>
        {lb.sub ? <div style={{...LUX.num, fontSize: 40, color, whiteSpace: 'nowrap'}}>{lb.sub}</div> : null}
        <div style={{width: 1.5, height: 110, marginTop: 8, background: 'linear-gradient(rgba(255,255,255,0.95), rgba(255,255,255,0.15))'}} />
        <div style={{width: 12, height: 12, borderRadius: 99, border: '1.5px solid #fff', marginTop: -2, boxShadow: `0 0 12px ${color}`}} />
      </div> : null;
    })}
    {drops.map((dr: any, i: number) => {
      const at0 = [dr.at[0] * W, dr.at[1] * H], q = P2(at0), sc = scaleAt(at0);
      const sp = spring({frame: frame - (dr.t ?? 0.5) * fps, fps, config: {damping: 9, stiffness: 90, mass: 1.1}});
      if (sp <= 0.001) return null;
      return <Img key={`d${i}`} src={url(dr.src)} style={{position: 'absolute', left: q[0], top: q[1] - (1 - sp) * H * 0.7, width: (dr.w || 0.3) * W * sc,
        transform: 'translate(-50%,-100%)', filter: 'drop-shadow(0 18px 18px rgba(0,0,0,0.45))'}} />;
    })}
  </AbsoluteFill>;
};

/**
 * LuxLabel: a quiet luxury caption over footage: small wide-tracked caps, an optional serif italic line, a hairline that
 * draws under it, a soft dark glow for readability. props: text, sub, x (0.08), y (0.72), align (left | center | right), at,
 * line (true), size (26), color.
 */
export const LuxLabel: React.FC<P> = ({duration, text = 'NHÃN', sub, x = 0.08, y = 0.72, align = 'left', at = 0, line = true, size = 26, color = GOLD}) => {
  const {frame, fps, t, W, H} = useT();
  const p = lerp(t, at, at + 0.45, 0, 1, EASE_IN);
  const lp = lerp(t, at + 0.15, at + 0.75, 0, 1, (q) => smooth(q));
  const o = exit(frame, fps, duration, 0.3);
  const tx = align === 'center' ? '-50%' : align === 'right' ? '-100%' : '0';
  return <AbsoluteFill style={{opacity: o}}>
    <div style={{position: 'absolute', left: x * W, top: y * H, transform: `translate(${tx}, 0)`, textAlign: align as any, textShadow: LUX.shadow,
      opacity: Math.min(1, p * 1.4)}}>
      <div style={{...LUX.cap, fontSize: size, color: '#fff', whiteSpace: 'nowrap', transform: `translateY(${(1 - p) * 14}px)`,
        paddingLeft: align === 'center' ? '0.26em' : 0}}>{text}</div>
      {line ? <div style={{height: 1.5, marginTop: 10, width: `${lp * 100}%`, background: `linear-gradient(90deg, ${color}, rgba(255,255,255,0.4))`,
        marginLeft: align === 'right' ? 'auto' : align === 'center' ? 'auto' : 0, marginRight: align === 'center' ? 'auto' : 0}} /> : null}
      {sub ? <div style={{...LUX.num, fontSize: size * 1.5, color, whiteSpace: 'nowrap', marginTop: 6, opacity: lp}}>{sub}</div> : null}
    </div>
  </AbsoluteFill>;
};

// ================================================================ AGENCY pack: stat title, step timeline, CTA checklist, tag label
const parseNum = (str: string) => { // "7,9" → {v: 7.9, dec: 1, sep: ','}, "1.286" → 1286 (Vietnamese thousands dot)
  const m = String(str).match(/^(\D*)(\d[\d.,]*)(.*)$/);
  if (!m) return null;
  const raw = m[2];
  let v: number, dec = 0;
  if (/^\d{1,3}(\.\d{3})+$/.test(raw)) v = parseFloat(raw.replace(/\./g, ''));
  else if (raw.includes(',')) { v = parseFloat(raw.replace(',', '.')); dec = raw.split(',')[1].length; }
  else v = parseFloat(raw);
  return {pre: m[1], v, dec, post: m[3], thousands: /^\d{1,3}(\.\d{3})+$/.test(raw)};
};
const showNum = (n: ReturnType<typeof parseNum>, k: number) => {
  if (!n) return '';
  const x = n.v * k;
  const body = n.thousands ? Math.round(x).toLocaleString('de-DE') : n.dec ? x.toFixed(n.dec).replace('.', ',') : String(Math.round(x));
  return n.pre + body + n.post;
};
/**
 * StatTitle: the agency headline number. props: value ("7,9" | "42+" | "1.286" | "10–15%"), unit ("ha", "tháp", "triệu/m²"),
 * caption ("QUY MÔ DỰ ÁN"), kicker (small line above, e.g. "GIÁ THAM KHẢO TỪ"), y (0.1 = top of the block), size (210),
 * tone copper | gold | white, count (true: plain numbers count up), at, scrim (true: soft dark band behind for readability).
 */
export const StatTitle: React.FC<P> = ({duration, value = '42+', unit, caption, kicker, compare, y = 0.085, size = 210, tone = 'ivory', count = true, at = 0, scrim = true, x = 0.5}) => {
  const {frame, fps, t, W, H} = useT();
  const pIn = spring({frame: frame - at * fps, fps, config: {damping: 15, stiffness: 120, mass: 0.8}});
  const o = Math.min(1, pIn * 1.6) * exit(frame, fps, duration, 0.3);
  const n0 = count && !/[–-]/.test(String(value).slice(1)) ? parseNum(String(value)) : null;
  const n = n0 && (n0.v >= 10 || n0.dec) ? n0 : null; // single digits ("2 tòa tháp") just land, counting 1→2 looks odd
  const k = n ? 1 - Math.pow(1 - Math.min(1, Math.max(0, (t - at) / 0.9)), 3) : 1;
  const g = METAL[tone] || COPPER;
  const cp = lerp(t, at + 0.35, at + 0.8);
  return <AbsoluteFill style={{opacity: o}}>
    {scrim ? <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: H * (y + 0.24),
      background: 'linear-gradient(180deg, rgba(4,8,14,0.55) 0%, rgba(4,8,14,0.32) 55%, rgba(4,8,14,0) 100%)'}} /> : null}
    <div style={{position: 'absolute', left: x * W, top: H * y, transform: `translateX(-50%) translateY(${(1 - pIn) * 40}px)`, textAlign: 'center', whiteSpace: 'nowrap'}}>
      {kicker ? <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 0.24, color: '#fff', textTransform: 'uppercase', letterSpacing: '0.02em',
        textShadow: '0 3px 12px rgba(0,0,0,0.6)', marginBottom: -size * 0.06}}>{kicker}</div> : null}
      <div style={{display: 'inline-flex', alignItems: 'baseline', gap: size * 0.06}}>
        <span style={{fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 1, letterSpacing: '-0.03em', ...metalText(g)}}>{n ? showNum(n, k) : value}</span>
        {unit ? <span style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 0.38, lineHeight: 1,
          ...(tone === 'ivory' ? {color: ACCENT.ivory, textShadow: '0 3px 10px rgba(0,0,0,0.55)'} : metalText(g))}}>{unit}</span> : null}
      </div>
      {tone === 'ivory' && caption ? <div style={{width: 90 * cp, height: 3, borderRadius: 3, background: ACCENT.ivory, margin: '10px auto 4px'}} /> : null}
      {caption ? <div style={{fontFamily: SANS, fontWeight: 800, fontSize: Math.max(40, size * 0.21), color: '#fff', textTransform: 'uppercase', letterSpacing: tone === 'ivory' ? '0.06em' : '0.01em',
        textShadow: '0 3px 12px rgba(0,0,0,0.65)', marginTop: size * 0.02, opacity: cp, transform: `translateY(${(1 - cp) * 14}px)`}}>{caption}</div> : null}
      {(() => { // plain-language comparison under the number: "≈ 2,5 sân bóng đá" (auto for ha)
        let c = compare;
        if (compare === 'auto' && n && /^ha$/i.test(String(unit || ''))) c = `≈ ${(n.v / 0.714).toFixed(1).replace('.', ',')} sân bóng đá`;
        if (!c || c === 'auto') return null;
        const q = lerp(t, at + 0.9, at + 1.3);
        return <div style={{display: 'inline-block', marginTop: 16, padding: '8px 22px', borderRadius: 99, background: 'rgba(8,14,24,0.6)',
          border: `1.5px solid ${tone === 'champagne' ? '#D2B072' : 'rgba(246,205,164,0.7)'}`, fontFamily: SANS, fontWeight: 700, fontSize: 30, color: '#fff',
          opacity: q, transform: `translateY(${(1 - q) * 10}px)`}}>{c}</div>;
      })()}
    </div>
  </AbsoluteFill>;
};

/**
 * StepTimeline: payment policy / roadmap as a vertical gold line with numbered dots. props: title ("CHÍNH SÁCH THANH TOÁN"),
 * steps [{label: "KÝ HỢP ĐỒNG MUA BÁN", value: "10–15%", unit}], x (0.12), y (0.22), gap (0.17 of the height), step (0.6 s), tone.
 */
export const StepTimeline: React.FC<P> = ({duration, title, steps = [], x = 0.12, y = 0.22, gap = 0.17, step = 0.6, at = 0.2, tone = 'copper', size = 150}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration, 0.3);
  const g = METAL[tone] || COPPER;
  const lineP = lerp(t, at, at + step * Math.max(1, steps.length), 0, 1, (q) => smooth(q));
  return <AbsoluteFill style={{opacity: o}}>
    <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(90deg, rgba(4,8,14,0.6) 0%, rgba(4,8,14,0.25) 60%, rgba(4,8,14,0) 100%)', opacity: lerp(t, 0, 0.4)}} />
    {title ? <div style={{position: 'absolute', left: 0, right: 0, top: H * (y - 0.09), textAlign: 'center', fontFamily: SANS, fontWeight: 800, fontSize: 40,
      color: '#F6D9BD', textTransform: 'uppercase', textShadow: '0 3px 12px rgba(0,0,0,0.6)', opacity: lerp(t, 0, 0.35)}}>{title}</div> : null}
    <div style={{position: 'absolute', left: x * W, top: H * y, width: 4, height: H * gap * (steps.length - 0.4) * lineP, borderRadius: 4,
      background: 'linear-gradient(180deg, #F6CDA4, #9A5E3C)'}} />
    {steps.map((s: any, i: number) => {
      const p = spring({frame: frame - (at + i * step) * fps, fps, config: {damping: 14, stiffness: 130, mass: 0.7}});
      const top = H * (y + i * gap);
      return <div key={i} style={{position: 'absolute', left: x * W - 22, top: top + 30, display: 'flex', alignItems: 'flex-start', gap: 30, opacity: Math.min(1, p * 1.5),
        transform: `translateX(${(1 - p) * 40}px)`}}>
        <div style={{width: 48, height: 48, borderRadius: 99, background: 'radial-gradient(circle, #F6CDA4 0%, #B57B52 100%)', boxShadow: '0 0 0 6px rgba(246,205,164,0.25)',
          display: 'grid', placeItems: 'center', fontFamily: SANS, fontWeight: 800, fontSize: 24, color: '#4A2A18', flex: 'none', marginTop: size * 0.3}}>{i + 1}</div>
        <div>
          <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 30, color: '#F6D9BD', textTransform: 'uppercase', textShadow: '0 2px 8px rgba(0,0,0,0.6)'}}>{s.label}</div>
          <div style={{display: 'flex', alignItems: 'baseline', gap: 16, marginTop: -size * 0.04}}>
            <span style={{fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 1.02, letterSpacing: '-0.03em', ...metalText(g)}}>{s.value}</span>
            {s.unit ? <span style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 0.36, color: '#fff', textShadow: '0 3px 10px rgba(0,0,0,0.6)'}}>{s.unit}</span> : null}
          </div>
        </div>
      </div>;
    })}
  </AbsoluteFill>;
};

/**
 * CtaChecklist: "BÌNH LUẬN / NHẮN TIN NGAY · để nhận" + items with copper icon bubbles. props: title, sub ("để nhận"),
 * items [{t: "BẢNG GIÁ GỐC", icon: "tag"}], y (0.1), step (0.35), x (0.5 = centred block).
 */
export const CtaChecklist: React.FC<P> = ({duration, title = 'BÌNH LUẬN / NHẮN TIN NGAY', sub = 'để nhận', items = [], y = 0.08, step = 0.35, at = 0.1, tone = 'copper'}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration, 0.3);
  const p0 = spring({frame: frame - at * fps, fps, config: {damping: 14, stiffness: 130}});
  return <AbsoluteFill style={{opacity: o}}>
    <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: H * (y + 0.12 + items.length * 0.06),
      background: 'linear-gradient(180deg, rgba(4,8,14,0.7) 0%, rgba(4,8,14,0.45) 70%, rgba(4,8,14,0) 100%)'}} />
    <div style={{position: 'absolute', left: 0, right: 0, top: H * y, display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: Math.min(1, p0 * 1.5),
      transform: `translateY(${(1 - p0) * 30}px)`}}>
      <Icon24 name="chat" size={52} />
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 56, color: '#fff', textTransform: 'uppercase', textShadow: '0 3px 12px rgba(0,0,0,0.6)', marginTop: 8,
        whiteSpace: 'nowrap'}}>{title}</div>
      {sub ? <div style={{fontFamily: SANS, fontWeight: 500, fontSize: 28, color: 'rgba(255,240,225,0.85)', marginTop: 2}}>{sub}</div> : null}
      <div style={{display: 'flex', flexDirection: 'column', gap: 22, marginTop: 30, alignItems: 'flex-start'}}>
        {items.map((it: any, i: number) => {
          const p = spring({frame: frame - (at + 0.4 + i * step) * fps, fps, config: {damping: 13, stiffness: 150, mass: 0.6}});
          return <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, opacity: Math.min(1, p * 1.5), transform: `translateX(${(1 - p) * -40}px)`}}>
            <div style={{width: 58, height: 58, borderRadius: 99, background: CARD_BG[tone] || CARD_BG.copper, display: 'grid', placeItems: 'center', boxShadow: '0 6px 14px rgba(0,0,0,0.4)',
              border: tone === 'champagne' ? '1.5px solid #D2B072' : 'none'}}>
              <Icon24 name={it.icon || 'check'} size={30} /></div>
            <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 40, color: '#fff', textTransform: 'uppercase', textShadow: '0 3px 10px rgba(0,0,0,0.6)', whiteSpace: 'nowrap'}}>{it.t || it}</div>
          </div>;
        })}
      </div>
    </div>
  </AbsoluteFill>;
};

/**
 * TagLabel: the agency pin card over footage or a photo, pointing at something (a room feature, a tower). props: name, kicker,
 * icon, x, y (where the marker tip sits), at, tone (copper | gold | navy), pin (true: teardrop marker; false: card only).
 */
export const TagLabel: React.FC<P> = ({duration, name = 'NHÃN', kicker, meta, photo, icon, x = 0.5, y = 0.6, at = 0, tone = 'ivory', pin = true, style = 'glass'}) => {
  const {frame, fps, W, H, t} = useT();
  if (style === 'glass') {
    const pg = spring({frame: frame - at * fps, fps, config: {damping: 14, stiffness: 140, mass: 0.7}});
    return <AbsoluteFill style={{opacity: exit(frame, fps, duration, 0.3)}}>
      <div style={{position: 'absolute', left: x * W, top: y * H, transform: `translate(-50%, ${pin ? '-100%' : '-50%'})`}}>
        <GlassPin name={name} kicker={kicker} meta={meta} photo={photo} icon={icon} tone={tone} p={pg} t={t - at} leader={pin ? 70 : 0} />
      </div>
    </AbsoluteFill>;
  }
  const p = spring({frame: frame - at * fps, fps, config: {damping: 12, stiffness: 150, mass: 0.6}});
  const o = exit(frame, fps, duration, 0.3);
  return <AbsoluteFill style={{opacity: o}}>
    <div style={{position: 'absolute', left: x * W, top: y * H, transform: `translate(-50%, ${pin ? '-100%' : '-50%'})`}}>
      {pin ? <AgencyPin name={name} kicker={kicker} icon={icon} tone={tone} p={p} />
        : <div style={{background: CARD_BG[tone] || CARD_BG.copper, borderRadius: 8, padding: '12px 26px', textAlign: 'center', whiteSpace: 'nowrap', opacity: Math.min(1, p * 1.5),
          transform: `scale(${0.7 + 0.3 * p})`, boxShadow: '0 10px 24px rgba(0,0,0,0.45)'}}>
          {kicker ? <div style={{fontFamily: SANS, fontWeight: 500, fontSize: 22, color: 'rgba(255,240,225,0.9)'}}>{kicker}</div> : null}
          <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 34, color: '#fff', textTransform: 'uppercase'}}>{name}</div></div>}
    </div>
  </AbsoluteFill>;
};

// ================================================================ PlotSpotlight
/** n points evenly spaced along a closed outline (so two different shapes can morph point by point) */
function resample(poly: number[][], n: number): number[][] {
  const pts = [...poly, poly[0]];
  return Array.from({length: n}, (_, i) => { const a = along(pts, i / n); return [a[0], a[1]]; });
}
const signedArea = (p: number[][]) => p.reduce((s, q, i) => { const r = p[(i + 1) % p.length]; return s + q[0] * r[1] - r[0] * q[1]; }, 0) / 2;
/** rotate / flip B so its points line up with A (same winding, least total travel) — the morph then looks like one line moving */
function alignTo(A: number[][], B: number[][]): number[][] {
  let b = signedArea(A) * signedArea(B) < 0 ? [...B].reverse() : B;
  const ca = centroid(A), cb = centroid(b);
  let best = 0, bestD = Infinity;
  for (let k = 0; k < b.length; k++) {
    let d = 0;
    for (let i = 0; i < A.length; i += 3) { const q = b[(i + k) % b.length]; d += Math.hypot(A[i][0] - ca[0] - (q[0] - cb[0]), A[i][1] - ca[1] - (q[1] - cb[1])); }
    if (d < bestD) { bestD = d; best = k; }
  }
  return b.map((_, i) => b[(i + best) % b.length]);
}
/**
 * PlotSpotlight — a plot on real footage (flycam / GES), told in three beats:
 *   1. the world around it drains to black & white while the plot keeps its colour, and a light runs the boundary;
 *   2. the plot LIFTS out of the ground like a cut slab (soil / glass / gold walls + a soft shadow), a glass name card
 *      stands on it;
 *   3. its outline peels off the ground and flies up into a "Thông tin khu đất" sheet: the same shape, edge lengths,
 *      area, facing and short rows.
 * src = this overlay's own footage (render.py cuts it from the timeline when src is omitted), frames = per-frame
 * homographies (render.py tracks them from `track`), ring = plot polygon in 0–1 of the frame at the overlay start.
 * sheet = {title, value, unit, rows: [[k, v]…], shape: [[x, y]…] (top-down, any units; default = ring), edges: ["20 m"…],
 *          facing}
 */
export const PlotSpotlight: React.FC<P> = ({duration, src, frames = [], track = {}, ring, desat_at = 0.1, desat = 0.92, dim = 0.22,
  draw_at = 0.35, draw = 1.3, lift_at, lift = 110, walls = 'soil', ground, label, label_at, sheet, sheet_at, color = '#F3D28B', tone = 'ivory'}) => {
  const {frame, fps, t, W, H} = useT();
  const M = frames.length ? frames[Math.min(frame, frames.length - 1)] : [1, 0, 0, 0, 1, 0, 0, 0, 1];
  const ref = (ring || track.corners || [[0.3, 0.55], [0.7, 0.55], [0.72, 0.72], [0.28, 0.72]]).map((q: number[]) => [q[0] * W, q[1] * H]);
  const P2 = (q: number[]) => {
    const w = M[6] * q[0] + M[7] * q[1] + M[8];
    return [(M[0] * q[0] + M[1] * q[1] + M[2]) / w, (M[3] * q[0] + M[4] * q[1] + M[5]) / w];
  };
  const rp = ref.map(P2);
  const c = centroid(rp);
  const a0 = P2(centroid(ref)), a1 = P2([centroid(ref)[0] + 10, centroid(ref)[1]]), a2 = P2([centroid(ref)[0], centroid(ref)[1] + 10]);
  const sc = Math.sqrt(Math.abs((a1[0] - a0[0]) * (a2[1] - a0[1]) - (a1[1] - a0[1]) * (a2[0] - a0[0]))) / 10;
  const gs = lerp(t, desat_at, desat_at + 0.7, 0, 1, (x) => smooth(x));
  const dp = lerp(t, draw_at, draw_at + draw, 0, 1, (x) => smooth(x));
  const after = lerp(t, draw_at + draw, draw_at + draw + 0.5);
  const lp = lift_at != null ? spring({frame: frame - lift_at * fps, fps, config: {damping: 15, stiffness: 90, mass: 0.9}}) : 0;
  const sp = sheet && sheet_at != null ? lerp(t, sheet_at, sheet_at + 1.1, 0, 1, (x) => smooth(x)) : 0;
  const h = lift * sc * lp;
  const up = rp.map((q: number[]) => [q[0], q[1] - h]);
  const o = exit(frame, fps, duration, 0.3);
  const acc = ACCENT[tone] || color;
  const vid = (style: React.CSSProperties) => src
    ? <OffthreadVideo src={url(src)} muted style={{position: 'absolute', left: 0, top: 0, width: W, height: H, objectFit: 'cover', ...style}} /> : null;
  const clip = `polygon(${rp.map((q: number[]) => `${q[0].toFixed(1)}px ${q[1].toFixed(1)}px`).join(',')})`;
  const L = pathLen([...up, up[0]]);
  const d = up.map((q: number[]) => q.join(',')).join(' ');
  const WALL: Record<string, [string, string]> = {soil: ['#A8774A', '#3A2412'], glass: ['rgba(190,220,255,0.55)', 'rgba(40,70,110,0.75)'], gold: ['#E7C27A', '#5E4318']};
  const wc = WALL[walls] || WALL.soil;
  // walls: edges whose outward normal faces the camera (points down the screen), far ones first
  const wallQuads = h > 0.5 ? rp.map((a: number[], i: number) => {
    const b = rp[(i + 1) % rp.length];
    let nx = -(b[1] - a[1]), ny = b[0] - a[0]; // edge normal, flipped to point away from the plot centre
    if (nx * ((a[0] + b[0]) / 2 - c[0]) + ny * ((a[1] + b[1]) / 2 - c[1]) < 0) { nx = -nx; ny = -ny; }
    return ny > 0 ? {i, a, b, y: (a[1] + b[1]) / 2, shade: Math.min(1, ny / (Math.hypot(b[0] - a[0], b[1] - a[1]) || 1))} : null;
  }).filter(Boolean).sort((p: any, q: any) => p.y - q.y) as any[] : [];
  // the sheet (beat 3)
  let sheetEl: React.ReactNode = null, morph: React.ReactNode = null;
  if (sheet && sp > 0) {
    const cw = W * 0.88, ch = H * 0.3, cx0 = (W - cw) / 2, cy0 = H * 0.075, box = ch - 70;
    const shp: number[][] = sheet.shape && sheet.shape.length > 2 ? sheet.shape : ref;
    const xs = shp.map((q) => q[0]), ys = shp.map((q) => q[1]);
    const bw = Math.max(...xs) - Math.min(...xs) || 1, bh = Math.max(...ys) - Math.min(...ys) || 1, k = box / Math.max(bw, bh);
    const ox = cx0 + 40 + (box - bw * k) / 2 - Math.min(...xs) * k, oy = cy0 + 35 + (box - bh * k) / 2 - Math.min(...ys) * k;
    const tgt = shp.map((q) => [ox + q[0] * k, oy + q[1] * k]);
    const N = 96, A = resample(up, N), B = alignTo(A, resample(tgt, N));
    const mid = A.map((q, i) => [q[0] + (B[i][0] - q[0]) * sp, q[1] + (B[i][1] - q[1]) * sp - Math.sin(sp * Math.PI) * H * 0.06]);
    const cardP = lerp(t, sheet_at + 0.55, sheet_at + 1.0, 0, 1, (x) => smooth(x));
    const rowP = (i: number) => lerp(t, sheet_at + 0.95 + i * 0.16, sheet_at + 1.3 + i * 0.16);
    const tc = centroid(tgt);
    morph = <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      <polygon points={mid.map((q) => q.join(',')).join(' ')} fill="#C9A24E" fillOpacity={0.22 * cardP} stroke={cardP > 0.5 ? '#A57C2C' : acc} strokeWidth={cardP > 0.5 ? 5 : 6}
        strokeLinejoin="round" filter={cardP > 0.5 ? undefined : 'url(#psglow)'} />
      {cardP > 0.5 ? tgt.map((q, i) => <circle key={`v${i}`} cx={q[0]} cy={q[1]} r={7} fill="#fff" stroke="#A57C2C" strokeWidth={3} opacity={rowP(0)} />) : null}
      {cardP > 0.5 ? (sheet.edges || []).map((e: string, i: number) => {
        const p = tgt[i], q = tgt[(i + 1) % tgt.length];
        if (!p || !q || !e) return null;
        const mx = (p[0] + q[0]) / 2, my = (p[1] + q[1]) / 2, nx = mx - tc[0], ny = my - tc[1], nl = Math.hypot(nx, ny) || 1;
        return <text key={i} x={mx + nx / nl * 26} y={my + ny / nl * 26 + 9} textAnchor="middle" fontFamily={SANS} fontWeight={700} fontSize={25}
          fill="#3B2F1C" opacity={rowP(0)}>{e}</text>;
      }) : null}
    </svg>;
    sheetEl = <div style={{position: 'absolute', left: cx0, top: cy0, width: cw, height: ch, borderRadius: 28, opacity: cardP, transform: `translateY(${(1 - cardP) * 30}px)`,
      background: 'linear-gradient(165deg, rgba(253,250,242,0.97), rgba(240,232,214,0.96))', border: `1.5px solid ${acc}`,
      boxShadow: '0 24px 60px rgba(0,0,0,0.45), inset 0 1px 0 #fff'}}>
      <div style={{position: 'absolute', left: box + 80, right: 36, top: 34, display: 'flex', flexDirection: 'column', gap: 10}}>
        <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 22, letterSpacing: '0.16em', textTransform: 'uppercase', color: '#9A7A3E'}}>{sheet.title || 'Thông tin khu đất'}</div>
        {sheet.value ? <div style={{display: 'flex', alignItems: 'baseline', gap: 12, opacity: rowP(0)}}>
          <span style={{fontFamily: SANS, fontWeight: 800, fontSize: 104, lineHeight: 0.95, color: '#141A26', letterSpacing: '-0.02em'}}>{sheet.value}</span>
          <span style={{fontFamily: SANS, fontWeight: 700, fontSize: 44, color: '#9A7A3E'}}>{sheet.unit}</span></div> : null}
        <div style={{width: 80 * rowP(0), height: 3, background: acc, borderRadius: 3, margin: '2px 0 6px'}} />
        {(sheet.rows || []).slice(0, 4).map((r: string[], i: number) => <div key={i} style={{display: 'flex', justifyContent: 'space-between', gap: 16,
          fontFamily: SANS, fontSize: 28, opacity: rowP(i + 1), transform: `translateX(${(1 - rowP(i + 1)) * 16}px)`, borderBottom: '1px solid rgba(60,45,20,0.12)', paddingBottom: 6}}>
          <span style={{color: '#6B5B40', fontWeight: 500}}>{r[0]}</span><span style={{color: '#141A26', fontWeight: 800}}>{r[1]}</span></div>)}
      </div>
      {sheet.facing ? <div style={{position: 'absolute', left: 40, bottom: 18, display: 'flex', alignItems: 'center', gap: 8, fontFamily: SANS, fontWeight: 700, fontSize: 22,
        color: '#6B5B40', opacity: rowP(1)}}>
        <svg width={26} height={26} viewBox="0 0 24 24"><path d="M12 2l4 10h-8z" fill="#B0412E" /><path d="M12 22l-4-10h8z" fill="#6B5B40" /></svg>{sheet.facing}</div> : null}
    </div>;
  }
  return <AbsoluteFill style={{opacity: o}}>
    {vid({filter: `grayscale(${desat * gs}) brightness(${1 - dim * gs}) contrast(${1 + 0.06 * gs})`})}
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      <defs>
        <filter id="psglow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        <filter id="psshadow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation={10 + h * 0.15} /></filter>
        <linearGradient id="pswall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={wc[0]} /><stop offset="1" stopColor={wc[1]} /></linearGradient>
      </defs>
      {h > 0.5 ? <polygon points={rp.map((q: number[]) => `${q[0] + h * 0.25},${q[1] + h * 0.18}`).join(' ')} fill="#000" opacity={0.5 * lp} filter="url(#psshadow)" /> : null}
      {wallQuads.map((w: any) => <g key={w.i}>
        <polygon points={`${w.a[0]},${w.a[1]} ${w.b[0]},${w.b[1]} ${w.b[0]},${w.b[1] - h} ${w.a[0]},${w.a[1] - h}`} fill="url(#pswall)" />
        <polygon points={`${w.a[0]},${w.a[1]} ${w.b[0]},${w.b[1]} ${w.b[0]},${w.b[1] - h} ${w.a[0]},${w.a[1] - h}`} fill="#000" opacity={0.35 * (1 - w.shade)} />
        {walls === 'soil' ? Array.from({length: 3}, (_, s) => <line key={s} x1={w.a[0]} y1={w.a[1] - h * (0.3 + s * 0.22)} x2={w.b[0]} y2={w.b[1] - h * (0.3 + s * 0.22)}
          stroke="rgba(0,0,0,0.25)" strokeWidth={1.5} />) : null}
      </g>)}
    </svg>
    <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transform: `translateY(${-h}px)`, clipPath: clip, WebkitClipPath: clip}}>
      {vid({filter: `saturate(${1 + 0.08 * gs}) brightness(${1 + 0.04 * gs})`})}
    </div>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 1 - sp * 0.75}}>
      <polygon points={d} fill={acc} fillOpacity={0.04 * after} />
      <polygon points={d} fill="none" stroke={acc} strokeWidth={5} strokeLinejoin="round" strokeDasharray={`${L * dp} ${L}`} filter="url(#psglow)" />
      <polygon points={d} fill="none" stroke="#fff" strokeWidth={4} strokeLinecap="round" strokeDasharray={`${L * 0.04} ${L}`}
        strokeDashoffset={-((L * (dp < 1 ? dp : 1 + (t - draw_at - draw) * 0.25)) % L)} filter="url(#psglow)" />
    </svg>
    {ground ? <div style={{position: 'absolute', left: 0, top: -h, width: W, height: H, transformOrigin: '0 0', opacity: after * (1 - sp),
      transform: `matrix3d(${M[0]},${M[3]},0,${M[6]},${M[1]},${M[4]},0,${M[7]},0,0,1,0,${M[2]},${M[5]},0,${M[8]})`}}>
      <div style={{position: 'absolute', left: centroid(ref)[0], top: centroid(ref)[1], transform: 'translate(-50%,-50%)', textAlign: 'center', whiteSpace: 'nowrap',
        textShadow: '0 2px 14px rgba(0,0,0,0.7)'}}>
        <div style={{...LUX.cap, fontSize: ground.size || 58, color: '#fff', paddingLeft: '0.26em'}}>{ground.text}</div>
        {ground.sub ? <div style={{...LUX.num, fontSize: (ground.size || 58) * 0.72, color: acc}}>{ground.sub}</div> : null}
      </div>
    </div> : null}
    {label ? (() => {
      const la = label_at ?? (lift_at != null ? lift_at + 0.35 : draw_at + draw);
      const pg = spring({frame: frame - la * fps, fps, config: {damping: 14, stiffness: 140, mass: 0.7}});
      const top = Math.min(...up.map((q: number[]) => q[1]));
      return pg > 0.01 ? <div style={{position: 'absolute', left: c[0] + (label.dx || 0), top: top - 6 + (label.dy || 0), transform: 'translate(-50%,-100%)', opacity: 1 - sp}}>
        <GlassPin name={label.name} kicker={label.kicker} meta={label.meta} photo={label.photo} icon={label.icon || 'home'} tone={tone} p={pg} t={t - la} leader={60} />
      </div> : null;
    })() : null}
    {sheetEl}
    {morph}
  </AbsoluteFill>;
};

export const ESTATE_COMPS: Record<string, React.FC<any>> = {GeoMap, Building3D, FloorPlan2D, LotCard, GlobeIntro, KnockoutText, InvertTitle, LensFlare, TrackedPlot, LuxLabel, StatTitle, StepTimeline, CtaChecklist, TagLabel, PlotSpotlight};
