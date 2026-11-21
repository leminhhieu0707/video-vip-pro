// TREND pack (11/2026) — name tag for the freeze-frame character intro, price slash, printing receipt, map fly-in with
// a dropping pin. Colours via T() (theme): the reference blue becomes the brand colour.
import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {C, EASE_IN, EASE_OUT, exit, SANS, SERIF, SHADOW_CARD, T} from './theme';
import {At, CL, lerp, P, Photo, pop, useT} from './Vip';

const easeInOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const rnd = (i: number) => {
  const v = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return v - Math.floor(v);
};

/** NameTag: freeze-frame "character intro" label — kicker line, big name rising letter by letter, role pill.
 *  Use on top of {"type":"freeze"} (render.py adds it automatically when the freeze has "name"). */
export const NameTag: React.FC<P> = ({duration, name = 'Tên nhân vật', role = '', kicker = '', x = 0.08, y = 0.66, size = 120, at = 0.12, align = 'left'}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  const bar = lerp(t, at, at + 0.35, 0, 1);
  const chars = Array.from(String(name));
  const right = align === 'right';
  return <AbsoluteFill style={{opacity: o}}>
    <div style={{position: 'absolute', left: right ? undefined : x * W, right: right ? x * W : undefined, top: y * H,
      display: 'flex', flexDirection: 'column', alignItems: right ? 'flex-end' : 'flex-start', gap: size * 0.12}}>
      {kicker ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: size * 0.26, letterSpacing: '0.28em', color: T('#B4CBFF'),
        opacity: lerp(t, at, at + 0.3), transform: `translateX(${(1 - lerp(t, at, at + 0.3)) * -30}px)`, textShadow: '0 2px 10px rgba(0,0,0,0.6)'}}>{kicker}</div> : null}
      <div style={{display: 'flex', whiteSpace: 'pre', fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 1, letterSpacing: '-0.02em', color: '#fff',
        textShadow: '0 4px 24px rgba(0,0,0,0.55)', overflow: 'hidden', paddingBottom: size * 0.08}}>
        {chars.map((ch, i) => {
          const p = lerp(t, at + 0.1 + i * 0.03, at + 0.45 + i * 0.03, 0, 1);
          return <span key={i} style={{display: 'inline-block', transform: `translateY(${(1 - p) * 110}%)`, opacity: p}}>{ch}</span>;
        })}
      </div>
      <div style={{height: size * 0.07, width: size * 3.2 * bar, background: T('linear-gradient(90deg,#3158FF,#8EB3FF)'), borderRadius: 99,
        boxShadow: T('0 0 18px rgba(60,100,255,0.8)')}} />
      {role ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: size * 0.32, color: C.ink, background: '#fff', borderRadius: 999,
        padding: `${size * 0.07}px ${size * 0.24}px`, boxShadow: SHADOW_CARD, transform: `scale(${pop(frame, fps, at + 0.45, 11)})`,
        transformOrigin: right ? 'right center' : 'left center'}}>{role}</div> : null}
    </div>
  </AbsoluteFill>;
};

/** PriceSlash: old price is struck through and drops back, the new price slams in with a sparkle burst, then a badge.
 *  {old: "25.990.000", new: "22.490.000", unit: "đ", label: "GIÁ HÔM NAY", badge: "-3,5 TRIỆU"} */
export const PriceSlash: React.FC<P> = ({duration, old = '25.990.000', new: nw = '22.490.000', unit = 'đ', label = '', badge = '', x = 0.5, y = 0.18,
  size = 150, slashAt = 0.3, newAt = 0.75, color = T('#FFFFFF'), strike = '#FF3B3B'}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  const inOld = lerp(t, 0, 0.3);
  const line = lerp(t, slashAt, slashAt + 0.22, 0, 1, EASE_OUT);
  const back = lerp(t, newAt - 0.05, newAt + 0.3, 0, 1);
  const s = pop(frame, fps, newAt, 9);
  const slam = interpolate(s, [0, 1], [1.9, 1]);
  const shake = t > newAt + 0.08 && t < newAt + 0.3 ? Math.sin(t * 110) * 7 * (1 - (t - newAt - 0.08) / 0.22) : 0;
  const burst = lerp(t, newAt + 0.05, newAt + 0.6, 0, 1);
  return <AbsoluteFill style={{opacity: o}}>
    {label ? <At x={x} y={y - (size / H) * 1.05}><div style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 0.24, letterSpacing: '0.2em', color: '#fff',
      background: T('rgba(14,21,48,0.78)'), borderRadius: 999, padding: `${size * 0.05}px ${size * 0.2}px`, opacity: inOld * (1 - back)}}>{label}</div></At> : null}
    {/* old price */}
    <At x={x} y={y - (size / H) * 0.72 * back} style={{transform: `translate(-50%,-50%) scale(${1 - 0.45 * back})`, opacity: inOld * (1 - 0.35 * back)}}>
      <div style={{position: 'relative', fontFamily: SANS, fontWeight: 800, fontSize: size * 0.72, color: back > 0 ? '#D9DEEA' : color, whiteSpace: 'nowrap',
        textShadow: '0 3px 16px rgba(0,0,0,0.5)'}}>
        {old}<span style={{fontSize: size * 0.4, marginLeft: 6}}>{unit}</span>
        <div style={{position: 'absolute', left: '-4%', top: '52%', height: size * 0.09, width: `${108 * line}%`, background: strike, borderRadius: 99,
          transform: 'rotate(-8deg)', transformOrigin: 'left center', boxShadow: '0 0 14px rgba(255,40,40,0.7)'}} />
      </div>
    </At>
    {/* sparkle burst */}
    {t > newAt ? Array.from({length: 12}).map((_, i) => {
      const a = (i / 12) * Math.PI * 2 + 0.3;
      const r = (0.12 + 0.22 * burst) * W * (0.8 + rnd(i) * 0.4);
      return <div key={i} style={{position: 'absolute', left: x * W + Math.cos(a) * r, top: (y + 0.02) * H + Math.sin(a) * r * 0.55,
        width: 16, height: 16, borderRadius: 99, background: i % 2 ? T('#8EB3FF') : '#FFD84D', opacity: 1 - burst, transform: `scale(${1.4 - burst})`}} />;
    }) : null}
    {/* new price */}
    {t >= newAt ? <At x={x} y={y + 0.02} style={{transform: `translate(-50%,-50%) translateX(${shake}px) scale(${slam})`}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 1, whiteSpace: 'nowrap', letterSpacing: '-0.02em',
        backgroundImage: 'linear-gradient(180deg,#FFF6C8 0%,#FFD84D 45%,#F2A900 100%)', WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
        filter: 'drop-shadow(0 4px 14px rgba(0,0,0,0.6)) drop-shadow(0 0 24px rgba(255,200,40,0.55))'}}>
        {nw}<span style={{fontSize: size * 0.5, marginLeft: 8}}>{unit}</span>
      </div>
    </At> : null}
    {badge ? <At x={Math.min(0.8, x + 0.24)} y={y + 0.02 + (size / H) * 0.78} style={{transform: `translate(-50%,-50%) rotate(${-12 + (1 - pop(frame, fps, newAt + 0.3, 10)) * 30}deg) scale(${pop(frame, fps, newAt + 0.3, 10)})`}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 0.26, color: '#fff', background: '#E5303C', borderRadius: 14, padding: `${size * 0.05}px ${size * 0.14}px`,
        border: '4px solid #fff', boxShadow: '0 8px 24px rgba(0,0,0,0.4)', whiteSpace: 'nowrap'}}>{badge}</div>
    </At> : null}
  </AbsoluteFill>;
};

/** Receipt: a paper bill prints out of a slot line by line, ends with the total (and an optional stamp).
 *  {title: "HOÁ ĐƠN", items: [{t: "iPhone 17 Pro 256GB", v: "28.990.000"}, ...], total: "27.490.000đ", stamp: "ĐÃ THANH TOÁN"} */
export const Receipt: React.FC<P> = ({duration, title = 'HOÁ ĐƠN', sub = '', items = [], total = '', totalLabel = 'TỔNG', stamp = '', x = 0.5, y = 0.07,
  w = 0.8, size = 44, at = 0, step}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  const list: Array<{t: string; v: string; at?: number}> = items.length ? items : [{t: 'Món 1', v: '100.000'}, {t: 'Món 2', v: '250.000'}];
  const st = step ?? Math.max(0.28, Math.min(0.7, (duration - at - 1.4) / (list.length + 1)));
  const lineH = size * 1.55;
  const n = list.length;
  const tTotal = at + 0.35 + n * st;
  // printed length grows line by line (smooth feed)
  const shown = interpolate(t, [at, at + 0.35, ...list.map((_, i) => at + 0.35 + (i + 1) * st), tTotal + 0.35], [0, 1.6, ...list.map((_, i) => 1.6 + (i + 1)), n + 1.6 + 1.9], CL);
  const fullH = (n + 1.6 + 1.9) * lineH + size;
  const visH = Math.min(fullH, shown * lineH + size * 0.5);
  const pw = w * W;
  const slotY = y * H;
  const zig = `polygon(0 0,100% 0,100% calc(100% - 14px),${Array.from({length: 24}).map((_, i) => `${100 - (i + 0.5) * 100 / 24}% ${i % 2 ? 'calc(100% - 14px)' : '100%'}`).join(',')},0 calc(100% - 14px))`;
  const row = (l: string, r: string, key: React.Key, opts: React.CSSProperties = {}) => (
    <div key={key} style={{display: 'flex', alignItems: 'baseline', gap: 10, height: lineH, fontFamily: SANS, fontWeight: 600, fontSize: size, color: '#22252D', ...opts}}>
      <span style={{whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '72%'}}>{l}</span>
      <span style={{flex: 1, borderBottom: '3px dotted rgba(0,0,0,0.25)', transform: 'translateY(-8px)'}} />
      <span style={{whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums', fontWeight: 700}}>{r}</span>
    </div>);
  return <AbsoluteFill style={{opacity: o * lerp(t, at, at + 0.2)}}>
    {/* paper: content is anchored to the slot and fed downwards */}
    <div style={{position: 'absolute', left: x * W - pw / 2, top: slotY + 10, width: pw, height: visH, overflow: 'hidden', clipPath: zig,
      filter: 'drop-shadow(0 18px 30px rgba(0,0,0,0.35))'}}>
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: fullH, background: 'linear-gradient(180deg,#FFFFFF,#F4F1EA)', padding: `${size * 0.6}px ${size * 0.8}px`,
        boxSizing: 'border-box', transform: `translateY(${fullH - visH}px)`}}>
        <div style={{height: lineH * 1.6, textAlign: 'center', fontFamily: SANS}}>
          <div style={{fontWeight: 800, fontSize: size * 1.2, letterSpacing: '0.18em', color: C.ink}}>{title}</div>
          {sub ? <div style={{fontWeight: 600, fontSize: size * 0.62, color: '#6B7080'}}>{sub}</div> : null}
        </div>
        {list.map((it, i) => row(it.t, it.v, i))}
        <div style={{borderTop: '4px dashed rgba(0,0,0,0.3)', marginTop: lineH * 0.3}} />
        {row(totalLabel, total, 'tot', {fontSize: size * 1.25, fontWeight: 800, color: C.blue, height: lineH * 1.6, alignItems: 'center'})}
      </div>
    </div>
    {/* printer slot on top of the paper */}
    <div style={{position: 'absolute', left: x * W - pw * 0.56, top: slotY - 18, width: pw * 1.12, height: 34, borderRadius: 17,
      background: T('linear-gradient(180deg,#2A3566,#0E1530)'), boxShadow: '0 10px 24px rgba(0,0,0,0.45)'}} />
    {stamp && t > tTotal + 0.45 ? <At x={x + w * 0.18} y={(slotY + visH - lineH * 2.2) / H} style={{transform: `translate(-50%,-50%) rotate(-14deg) scale(${2 - Math.min(1, (t - tTotal - 0.45) / 0.14)})`,
      opacity: Math.min(1, (t - tTotal - 0.45) / 0.14)}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 0.95, color: '#E5303C', border: `${size * 0.12}px solid #E5303C`, borderRadius: 12,
        padding: `0 ${size * 0.3}px`, whiteSpace: 'nowrap', mixBlendMode: 'multiply'}}>{stamp}</div>
    </At> : null}
  </AbsoluteFill>;
};

/** MapPin: camera flies into a map (drawn, or your own map screenshot via `src`), a pin drops with a bounce and ripples,
 *  then a label card pops. Card in the top half by default; full: true fills the frame.
 *  {place: "Minh Đức Store", sub: "419 Điện Biên Phủ, Đà Nẵng", src?: "map.png", pin: [0.55, 0.5] (on the map)} */
export const MapPin: React.FC<P> = ({duration, place = 'Địa điểm', sub = '', src: map, pin = [0.55, 0.52], full = false, y = 0.27, w = 0.88, h = 0.36,
  zoom = 2.4, fly = 1.1, color = T('#3158FF'), at = 0}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * lerp(t, at, at + 0.3);
  const cw = full ? W : w * W, ch = full ? H : h * H;
  const cx = W / 2 - cw / 2, cy = full ? 0 : y * H - ch / 2;
  const p = easeInOut(Math.min(1, Math.max(0, (t - at) / fly)));
  const sc = interpolate(p, [0, 1], [1, zoom]);
  // keep the pin point moving to the card centre while zooming
  const [px, py] = pin as [number, number];
  const tx = (0.5 - px) * cw * p, ty = (0.5 - py) * ch * p;
  const tDrop = at + fly - 0.1;
  const drop = pop(frame, fps, tDrop, 8);
  const ripple = (k: number) => Math.max(0, Math.min(1, (t - tDrop - 0.15 - k * 0.35) / 1.1));
  const card = pop(frame, fps, tDrop + 0.35, 11);
  const land = T('#E9EEF8'), road = '#FFFFFF', water = T('#A9C4FF'), park = '#CFE8C6', major = '#FFE6A8';
  const drawn = () => {
    const rows = Array.from({length: 14});
    return <svg width={cw} height={ch} viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice" style={{display: 'block'}}>
      <rect width="1000" height="1000" fill={land} />
      {Array.from({length: 7}).map((_, i) => <rect key={i} x={rnd(i) * 900} y={rnd(i + 9) * 900} width={60 + rnd(i + 3) * 90} height={50 + rnd(i + 5) * 80} rx={14} fill={park} />)}
      <path d="M-50 760 C 200 680, 330 860, 520 760 S 860 600, 1050 660 L 1050 820 C 860 760, 700 900, 520 900 S 160 860, -50 920 Z" fill={water} />
      <g transform="rotate(-18 500 500)">
        {rows.map((_, i) => <line key={'h' + i} x1={-300} x2={1300} y1={i * 95 - 200} y2={i * 95 - 200} stroke={road} strokeWidth={i % 4 === 1 ? 22 : 9} />)}
        {rows.map((_, i) => <line key={'v' + i} y1={-300} y2={1300} x1={i * 110 - 250} x2={i * 110 - 250} stroke={road} strokeWidth={i % 5 === 2 ? 22 : 9} />)}
      </g>
      <path d="M-50 300 C 300 260, 600 420, 1050 340" stroke={major} strokeWidth={26} fill="none" />
      <path d="M-50 300 C 300 260, 600 420, 1050 340" stroke="#F2C66B" strokeWidth={4} fill="none" strokeDasharray="1 0" />
    </svg>;
  };
  return <AbsoluteFill style={{opacity: o}}>
    <div style={{position: 'absolute', left: cx, top: cy, width: cw, height: ch, overflow: 'hidden', borderRadius: full ? 0 : 34,
      boxShadow: full ? undefined : SHADOW_CARD, border: full ? undefined : '4px solid rgba(255,255,255,0.95)', background: land}}>
      <div style={{position: 'absolute', inset: 0, transform: `translate(${tx}px,${ty}px) scale(${sc})`, transformOrigin: `${px * 100}% ${py * 100}%`}}>
        {map ? <Photo s={map} /> : drawn()}
      </div>
      {/* ripples + pin at the card centre (where the pin point ends up) */}
      {[0, 1, 2].map((k) => ripple(k) > 0 && ripple(k) < 1 ? <div key={k} style={{position: 'absolute', left: cw / 2, top: ch / 2, width: 40 + ripple(k) * cw * 0.5,
        height: (40 + ripple(k) * cw * 0.5) * 0.42, transform: 'translate(-50%,-50%)', borderRadius: '50%', border: `5px solid ${color}`, opacity: 1 - ripple(k)}} /> : null)}
      {t > tDrop ? <div style={{position: 'absolute', left: cw / 2, top: ch / 2, transform: `translate(-50%,-100%) translateY(${(1 - drop) * -ch * 0.35}px)`}}>
        <svg width={110} height={150} viewBox="0 0 110 150"><path d="M55 146 C 30 108, 6 82, 6 52 A 49 49 0 0 1 104 52 C 104 82, 80 108, 55 146 Z" fill={color} stroke="#fff" strokeWidth={6} />
          <circle cx={55} cy={52} r={18} fill="#fff" /></svg>
      </div> : null}
      {t > tDrop ? <div style={{position: 'absolute', left: cw / 2, top: ch / 2, width: 46 * drop, height: 14 * drop, transform: 'translate(-50%,-50%)', borderRadius: '50%',
        background: 'rgba(0,0,0,0.3)'}} /> : null}
    </div>
    {t > tDrop + 0.3 ? <div style={{position: 'absolute', left: W / 2, top: cy + ch * (full ? 0.62 : 0.5) + (full ? 0 : ch * 0.5) + (full ? 0 : 26),
      transform: `translate(-50%,${full ? '0' : '-50%'}) scale(${card})`, transformOrigin: 'center top', background: '#fff', borderRadius: 26, padding: '22px 36px',
      boxShadow: SHADOW_CARD, textAlign: 'center', fontFamily: SANS, width: 'max-content', maxWidth: W * 0.84}}>
      <div style={{fontWeight: 800, fontSize: 58, color: C.ink, lineHeight: 1.1}}>📍 {place}</div>
      {sub ? <div style={{fontWeight: 600, fontSize: 36, color: '#5B6274', marginTop: 6}}>{sub}</div> : null}
    </div> : null}
  </AbsoluteFill>;
};

/** DecodeText: characters scramble through random glyphs and lock in left to right (hacker / AI reveal). */
export const DecodeText: React.FC<P> = ({duration, text = 'SỰ THẬT LÀ...', x = 0.5, y = 0.16, size = 104, at = 0.05, cps = 22, color = '#FFFFFF', accent = T('#8EB3FF'), box = true}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const chars = Array.from(String(text));
  size = Math.min(size, (W * 0.84) / Math.max(1, chars.length * 0.68 + (box ? 0.6 : 0)));
  const glyph = 'ABCDEFGHKMNPQRSTUVWXYZ0123456789#$%&@*+=<>/ĐƯƠÂ';
  const done = (t - at) * cps;
  return <At x={x} y={y} style={{opacity: o * lerp(t, at - 0.05, at + 0.1)}}>
    <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 1.1, whiteSpace: 'pre', letterSpacing: '0.04em', color,
      padding: box ? `${size * 0.12}px ${size * 0.3}px` : 0, background: box ? T('rgba(10,16,40,0.72)') : undefined, borderRadius: size * 0.16,
      border: box ? T('2px solid rgba(142,179,255,0.45)') : undefined, textShadow: '0 3px 14px rgba(0,0,0,0.5)', fontVariantNumeric: 'tabular-nums'}}>
      {chars.map((ch, i) => {
        const locked = done > i + 3 || ch === ' ';
        const g = locked ? ch : glyph[Math.floor(rnd(i * 31 + Math.floor(frame / 2)) * glyph.length)];
        return <span key={i} style={{color: locked ? color : accent, opacity: done > i - 4 ? 1 : 0}}>{g}</span>;
      })}
    </div>
  </At>;
};

/** Countdown: label + big 3-2-1 that punches in each step with a ring draining around it. */
export const Countdown: React.FC<P> = ({duration, from = 3, label = 'ĐỢI ĐÃ...', x = 0.5, y = 0.2, size = 220, at = 0, color = T('#3158FF')}) => {
  const {frame, fps, t, H} = useT();
  const o = exit(frame, fps, duration);
  const step = Math.max(0.4, (duration - at - 0.35) / from);
  const k = Math.min(from - 1, Math.max(0, Math.floor((t - at) / step)));
  const f = Math.max(0, Math.min(1, (t - at - k * step) / step));
  const s = pop(frame, fps, at + k * step, 9);
  const R = size * 0.62, C2 = 2 * Math.PI * R;
  return <AbsoluteFill style={{opacity: o * lerp(t, at, at + 0.15)}}>
    {label ? <At x={x} y={y - (R + size * 0.3) / H}><div style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 0.22, letterSpacing: '0.18em', color: '#fff',
      textShadow: '0 3px 14px rgba(0,0,0,0.6)', whiteSpace: 'nowrap'}}>{label}</div></At> : null}
    <At x={x} y={y}>
      <div style={{position: 'relative', width: R * 2 + 30, height: R * 2 + 30, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <svg width={R * 2 + 30} height={R * 2 + 30} style={{position: 'absolute', inset: 0, transform: 'rotate(-90deg)'}}>
          <circle cx={R + 15} cy={R + 15} r={R} fill={T('rgba(10,16,40,0.55)')} stroke="rgba(255,255,255,0.18)" strokeWidth={14} />
          <circle cx={R + 15} cy={R + 15} r={R} fill="none" stroke={color} strokeWidth={14} strokeLinecap="round" strokeDasharray={C2} strokeDashoffset={C2 * f} />
        </svg>
        <div style={{position: 'relative', fontFamily: SANS, fontWeight: 800, fontSize: size, color: '#fff', lineHeight: 1, transform: `scale(${interpolate(s, [0, 1], [1.8, 1])})`,
          opacity: Math.min(1, s * 1.5), textShadow: '0 6px 26px rgba(0,0,0,0.5)'}}>{from - k}</div>
      </div>
    </At>
  </AbsoluteFill>;
};

/** EvidenceBoard: cork board fills the frame; photos / clippings get pinned one by one and red strings connect them.
 *  {items: [{src, label, x, y, at?}], links: [[0, 1], [1, 2]], title} — x/y are 0–1 on the board (defaults spread). */
export const EvidenceBoard: React.FC<P> = ({duration, items = [], links, title = '', bg = '#6B4A2E', w = 300}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * lerp(t, 0, 0.25);
  const L: any[] = items.length ? items : [{label: 'A'}, {label: 'B'}, {label: 'C'}];
  const pos = (i: number) => {
    const it: any = L[i];
    const dflt = [[0.28, 0.26], [0.72, 0.32], [0.32, 0.56], [0.7, 0.64], [0.5, 0.44], [0.27, 0.84], [0.73, 0.88]][i % 7];
    return [it.x ?? dflt[0], it.y ?? dflt[1]] as [number, number];
  };
  const span = Math.max(0.3, (duration - 1.2) / (L.length + 1));
  const atOf = (i: number) => (L[i] as any).at ?? 0.25 + i * span;
  const lk: number[][] = links ?? L.slice(1).map((_, i) => [i, i + 1]);
  const cam = interpolate(t, [0, duration], [1.0, 1.06], CL);
  const pinY = (i: number) => pos(i)[1] * H - w * 0.5;
  return <AbsoluteFill style={{opacity: o, background: `radial-gradient(circle at 50% 40%, ${bg}, #2E1E12 95%)`, transform: `scale(${cam})`}}>
    <AbsoluteFill style={{opacity: 0.25, backgroundImage: 'radial-gradient(rgba(0,0,0,0.5) 1.5px, transparent 1.6px)', backgroundSize: '9px 9px'}} />
    {L.map((it: any, i) => {
      const s = pop(frame, fps, atOf(i), 11);
      if (t < atOf(i)) return null;
      const [px, py] = pos(i);
      const rot = (rnd(i + 3) - 0.5) * 12;
      return <div key={i} style={{position: 'absolute', left: px * W, top: py * H, width: w, transform: `translate(-50%,-50%) rotate(${rot}deg) scale(${interpolate(s, [0, 1], [1.4, 1])})`,
        opacity: Math.min(1, s * 1.4), background: '#F7F3EA', padding: 12, paddingBottom: it.label ? 8 : 12, boxShadow: '0 14px 26px rgba(0,0,0,0.45)'}}>
        <div style={{width: '100%', height: w * 0.78, overflow: 'hidden', background: '#d8d2c4'}}>{it.src ? <Photo s={it.src} /> : null}</div>
        {it.label ? <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 30, color: '#1E1E1E', textAlign: 'center', marginTop: 6, lineHeight: 1.15}}>{it.label}</div> : null}
      </div>;
    })}
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      {lk.map(([a, b], j) => {
        const ta = Math.max(atOf(a), atOf(b)) + 0.25;
        const p = lerp(t, ta, ta + 0.45, 0, 1);
        if (p <= 0) return null;
        const X1 = pos(a)[0] * W, Y1 = pinY(a), X2 = X1 + (pos(b)[0] * W - X1) * p, Y2 = Y1 + (pinY(b) - Y1) * p;
        return <line key={j} x1={X1} y1={Y1} x2={X2} y2={Y2} stroke="#D7262E" strokeWidth={6} strokeLinecap="round" />;
      })}
      {L.map((_, i) => t >= atOf(i) ? <circle key={'p' + i} cx={pos(i)[0] * W} cy={pinY(i)} r={15} fill="#C4161F" stroke="#7A0A10" strokeWidth={3} /> : null)}
    </svg>
    {title ? <At x={0.5} y={0.07}><div style={{fontFamily: SANS, fontWeight: 800, fontSize: 64, color: '#fff', background: '#B5121B', padding: '8px 26px',
      transform: `rotate(-2deg) scale(${pop(frame, fps, 0.1, 11)})`, boxShadow: '0 10px 20px rgba(0,0,0,0.4)', whiteSpace: 'nowrap'}}>{title}</div></At> : null}
  </AbsoluteFill>;
};

/** Audiogram: bars that move with the real voice (render.py fills `levels` from the edit's audio), in a glass pill. */
export const Audiogram: React.FC<P> = ({duration, levels = [], x = 0.5, y = 0.8, w = 0.62, h = 0.07, bars = 34, label = '', color = T('#8EB3FF')}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * lerp(t, 0, 0.25);
  const lv = (k: number) => (levels.length ? levels[Math.max(0, Math.min(levels.length - 1, frame - k))] : 0.3 + 0.3 * Math.abs(Math.sin(t * 7 + k)));
  const bw = (w * W) / bars;
  return <At x={x} y={y} style={{opacity: o}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 22, padding: '18px 30px', borderRadius: 999, background: T('rgba(10,16,40,0.6)'),
      border: T('1.5px solid rgba(142,179,255,0.35)'), boxShadow: SHADOW_CARD}}>
      {label ? <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 34, color: '#fff', whiteSpace: 'nowrap'}}>{label}</div> : null}
      <div style={{display: 'flex', alignItems: 'center', height: h * H, gap: bw * 0.3}}>
        {Array.from({length: bars}).map((_, i) => {
          const d = Math.abs(i - (bars - 1) / 2) / (bars / 2);
          const v = lv(Math.round(d * 6)) * (1 - d * 0.55) * (0.75 + 0.5 * rnd(i + Math.floor(frame / 3)));
          return <div key={i} style={{width: bw * 0.7, height: Math.max(6, v * h * H), borderRadius: 99, background: color, boxShadow: T('0 0 12px rgba(60,100,255,0.6)')}} />;
        })}
      </div>
    </div>
  </At>;
};

export const TREND_COMPS: Record<string, React.FC<any>> = {NameTag, PriceSlash, Receipt, MapPin, DecodeText, Countdown, EvidenceBoard, Audiogram};
