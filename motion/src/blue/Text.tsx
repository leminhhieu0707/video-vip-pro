// TEXT pack (11/2026) — 26 premium text effects. Colours via T() (theme). Some need render.py / vipfx help:
//   behind: true            Text3D, MarqueeRows (person occludes them)       WeaveText (auto back/front halves, RING_COMPS)
//   "blend": "overlay"      ProjectText (text takes the wall's light and texture)
//   "fill": "glass"         GlassText (blurred video seen through the letters)
//   track                   TrackLabel (render.py tracks a box -> per-frame points)
//   beats                   BeatText (render.py detects the music beats)
//   FocusText               render.py adds the matching rack-focus frost
import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {C, EASE_IN, EASE_OUT, exit, SANS, SERIF, SHADOW_CARD, T} from './theme';
import {At, CL, lerp, P, Photo, pop, useT} from './Vip';

const SCRIPT = 'DSC, "Segoe Script", cursive';
const rnd = (i: number) => {
  const v = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return v - Math.floor(v);
};
const fit = (size: number, text: string, W: number, k = 0.62, room = 0.86) =>
  Math.min(size, (W * room) / Math.max(1, Array.from(text).length * k));
const shadowStack = (n: number, col: string, dx = 1, dy = 1) =>
  Array.from({length: n}).map((_, i) => `${(i + 1) * dx}px ${(i + 1) * dy}px 0 ${col}`).join(',');

// ================================================================ 1. Text3D — big extruded words standing in the room
/** {text, plane: "wall" | "table", rx, ry, y, behind: true} — perspective + extrusion + floor shadow. */
export const Text3D: React.FC<P> = ({duration, text = 'IPHONE 17', sub = '', plane = 'wall', x = 0.5, y = 0.36, size = 200, rx, ry = -14, at = 0,
  color = '#FFFFFF', side = T('#1C2A6B')}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const s = pop(frame, fps, at, 12);
  const sz = fit(size, text, W, 0.66, 0.9);
  const tilt = rx ?? (plane === 'table' ? 58 : 6);
  const drift = interpolate(t, [0, duration], [0, -4], CL);
  return <At x={x} y={y} style={{opacity: o * Math.min(1, s * 1.4), perspective: 1400}}>
    <div style={{transform: `rotateX(${tilt}deg) rotateY(${ry + drift}deg) translateY(${(1 - s) * 80}px)`, transformStyle: 'preserve-3d', textAlign: 'center'}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 0.95, letterSpacing: '-0.02em', color, whiteSpace: 'nowrap',
        textShadow: `${shadowStack(14, side, 0.9, 1.4)}, 0 40px 60px rgba(0,0,0,0.45)`}}>{text}</div>
      {sub ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: sz * 0.26, color, letterSpacing: '0.3em', marginTop: sz * 0.08,
        textShadow: shadowStack(4, side, 0.6, 0.8)}}>{sub}</div> : null}
    </div>
  </At>;
};

// ================================================================ 2. WeaveText — a ribbon of text wrapping around the speaker
/** {text, y, rx, ry, tilt} — the back half goes behind the speaker automatically (render.py RING_COMPS). */
export const WeaveText: React.FC<P> = ({duration, text = 'MINH ĐỨC STORE • ', x = 0.5, y = 0.56, rx = 0.46, ry = 0.06, size = 70, half = 'front', speed = 0.22,
  tilt = -10, color = '#FFFFFF', band = T('#3158FF')}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * lerp(t, 0, 0.3);
  const chars = Array.from(String(text).repeat(Math.max(1, Math.ceil(40 / Math.max(1, Array.from(String(text)).length)))));
  const N = chars.length;
  const spin = t * speed * Math.PI * 2;
  return <AbsoluteFill style={{opacity: o, transform: `rotate(${tilt}deg)`, transformOrigin: `${x * 100}% ${y * 100}%`}}>
    {chars.map((ch, i) => {
      const a = (i / N) * Math.PI * 2 + spin;
      const front = Math.sin(a) > 0;
      if ((half === 'back') === front && half !== 'all') return null;
      const sc = 0.72 + 0.28 * (Math.sin(a) + 1) / 2;
      return <div key={i} style={{position: 'absolute', left: (x + Math.cos(a) * rx) * W, top: (y + Math.sin(a) * ry) * H,
        transform: `translate(-50%,-50%) scale(${sc}) rotateY(${Math.cos(a) * -60}deg)`, fontFamily: SANS, fontWeight: 800, fontSize: size, color,
        background: band, padding: `0 ${size * 0.04}px`, lineHeight: 1.25, opacity: front ? 1 : 0.85}}>{ch === ' ' ? ' ' : ch}</div>;
    })}
  </AbsoluteFill>;
};

// ================================================================ 3. ProjectText — projected onto the wall (use "blend": "overlay")
export const ProjectText: React.FC<P> = ({duration, text = 'SỰ THẬT', sub = '', x = 0.5, y = 0.22, size = 190, at = 0, color = '#FFFFFF'}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration, 0.4);
  const flick = t < at + 0.35 ? (Math.floor(frame / 2) % 3 === 0 ? 0.35 : 1) * lerp(t, at, at + 0.35) : 1;
  const sz = fit(size, text, W, 0.64);
  return <At x={x} y={y} style={{opacity: o * flick, textAlign: 'center', filter: 'blur(1.2px)'}}>
    <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, color, letterSpacing: '0.04em', whiteSpace: 'nowrap', textShadow: '0 0 30px rgba(255,255,255,0.8)'}}>{text}</div>
    {sub ? <div style={{fontFamily: SANS, fontWeight: 600, fontSize: sz * 0.24, color, letterSpacing: '0.25em'}}>{sub}</div> : null}
  </At>;
};

// ================================================================ 4. MetalText — gold / silver / chrome with a light sweep
const METALS: Record<string, [string, string, string]> = {
  gold: ['linear-gradient(180deg,#FFF6C8 0%,#FFD95A 32%,#B8860B 52%,#FFE58A 68%,#8A6100 100%)', '#5A3E00', 'rgba(255,210,90,0.55)'],
  silver: ['linear-gradient(180deg,#FFFFFF 0%,#D9DEE6 35%,#7D8794 52%,#E9EDF2 70%,#5C6570 100%)', '#2E343B', 'rgba(220,230,255,0.5)'],
  chrome: ['linear-gradient(180deg,#F4FAFF 0%,#A9C2DA 45%,#2B3A4A 50%,#9FB9D2 62%,#EAF4FF 100%)', '#18222C', 'rgba(170,210,255,0.55)'],
  red: ['linear-gradient(180deg,#FFD0D0 0%,#FF4B4B 40%,#9E0000 55%,#FF6A6A 70%,#5E0000 100%)', '#3E0000', 'rgba(255,80,80,0.5)'],
};
export const MetalText: React.FC<P> = ({duration, text = 'GIÁ SỐC', sub = '', metal = 'gold', x = 0.5, y = 0.18, size = 190, at = 0, sweepAt = 0.45}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const s = pop(frame, fps, at, 11);
  const [grad, deep, glow] = METALS[metal] || METALS.gold;
  const sz = fit(size, text, W, 0.66);
  const sw = lerp(t, at + sweepAt, at + sweepAt + 0.7, -40, 140, EASE_OUT);
  const face: React.CSSProperties = {fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1, letterSpacing: '-0.01em', whiteSpace: 'nowrap'};
  return <At x={x} y={y} style={{opacity: o, transform: `translate(-50%,-50%) scale(${interpolate(s, [0, 1], [1.5, 1])})`, textAlign: 'center'}}>
    <div style={{position: 'relative'}}>
      <div style={{...face, color: deep, position: 'absolute', inset: 0, textShadow: `${shadowStack(10, deep, 0, 1.2)}, 0 18px 36px rgba(0,0,0,0.55)`}}>{text}</div>
      <div style={{...face, position: 'relative', backgroundImage: grad, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent',
        WebkitTextStroke: `2px ${deep}`, filter: `drop-shadow(0 0 22px ${glow})`}}>{text}</div>
      <div style={{...face, position: 'absolute', inset: 0, color: 'transparent', backgroundImage: `linear-gradient(105deg, transparent ${sw - 12}%, rgba(255,255,255,0.95) ${sw}%, transparent ${sw + 12}%)`,
        WebkitBackgroundClip: 'text', backgroundClip: 'text', mixBlendMode: 'screen'}}>{text}</div>
    </div>
    {sub ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: sz * 0.24, letterSpacing: '0.24em', color: '#fff', marginTop: sz * 0.1,
      textShadow: '0 3px 12px rgba(0,0,0,0.6)'}}>{sub}</div> : null}
  </At>;
};

// ================================================================ 5. GlassText — frosted glass letters (use "fill": "glass")
/** Draws the letters (alpha = glass shape) plus a bright rim; vipfx fills the shape with the blurred video. */
export const GlassText: React.FC<P> = ({duration, text = 'PREMIUM', sub = '', x = 0.5, y = 0.2, size = 220, at = 0}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * lerp(t, at, at + 0.35);
  const sz = fit(size, text, W, 0.66);
  const rise = lerp(t, at, at + 0.5, 40, 0);
  return <At x={x} y={y} style={{opacity: o, transform: `translate(-50%,-50%) translateY(${rise}px)`, textAlign: 'center'}}>
    <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1, whiteSpace: 'nowrap', color: 'rgba(255,255,255,0.16)',
      WebkitTextStroke: '3px rgba(255,255,255,0.9)', textShadow: '0 2px 0 rgba(255,255,255,0.35), 0 18px 40px rgba(0,0,0,0.35)'}}>{text}</div>
    {sub ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: sz * 0.2, color: '#fff', letterSpacing: '0.3em', marginTop: sz * 0.08}}>{sub}</div> : null}
  </At>;
};

// ================================================================ 6. NeonText — neon sign switching on with flicker
export const NeonText: React.FC<P> = ({duration, text = 'OPEN 24/7', x = 0.5, y = 0.2, size = 150, at = 0, color = '#FF3FD8', script = true}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const seq = [0, 1, 0, 0, 1, 1, 0, 1, 1, 1];
  const k = Math.floor((t - at) * 20);
  const on = t < at ? 0 : k < seq.length ? seq[k] : 1;
  const hum = 0.94 + 0.06 * Math.sin(t * 50);
  const sz = fit(size, text, W, script ? 0.52 : 0.64);
  return <At x={x} y={y} style={{opacity: o}}>
    <div style={{fontFamily: script ? SCRIPT : SANS, fontWeight: 700, fontSize: sz, whiteSpace: 'nowrap', color: on ? '#FFF6FD' : 'rgba(255,255,255,0.12)',
      WebkitTextStroke: `${on ? 2 : 3}px ${on ? color : 'rgba(255,255,255,0.25)'}`, opacity: on ? hum : 1,
      textShadow: on ? `0 0 6px #fff, 0 0 16px ${color}, 0 0 34px ${color}, 0 0 70px ${color}` : 'none'}}>{text}</div>
  </At>;
};

// ================================================================ 7. WriteOn — handwritten signature drawing itself
export const WriteOn: React.FC<P> = ({duration, text = 'Minh Đức', x = 0.5, y = 0.2, size = 170, at = 0, dur = 1.4, color = '#FFFFFF', underline = true}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const p = lerp(t, at, at + dur, 0, 1, EASE_OUT);
  const fillP = lerp(t, at + dur * 0.7, at + dur + 0.2, 0, 1);
  const sz = fit(size, text, W, 0.48);
  const w = Math.min(W * 0.92, Array.from(text).length * sz * 0.5 + sz);
  const h = sz * 1.5;
  return <At x={x} y={y} style={{opacity: o}}>
    <svg width={w} height={h * (underline ? 1.25 : 1)} style={{overflow: 'visible', filter: 'drop-shadow(0 3px 10px rgba(0,0,0,0.5))'}}>
      <text x={w / 2} y={h * 0.72} textAnchor="middle" fontFamily={SCRIPT} fontWeight={700} fontSize={sz} fill={color} fillOpacity={fillP}
        stroke={color} strokeWidth={2.2} strokeDasharray={4000} strokeDashoffset={4000 * (1 - p)}>{text}</text>
      {underline ? <path d={`M ${w * 0.12} ${h * 1.0} Q ${w * 0.5} ${h * 0.88} ${w * 0.9} ${h * 0.98}`} fill="none" stroke={color} strokeWidth={5} strokeLinecap="round"
        strokeDasharray={w} strokeDashoffset={w * (1 - lerp(t, at + dur * 0.85, at + dur + 0.35))} /> : null}
    </svg>
  </At>;
};

// ================================================================ 8. SliceText — bands slide in from alternate sides and lock together
export const SliceText: React.FC<P> = ({duration, text = 'SIÊU SALE', x = 0.5, y = 0.18, size = 190, at = 0, slices = 4, color = '#FFFFFF', accent = T('#3158FF')}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const sz = fit(size, text, W, 0.66);
  const hgt = sz * 1.1;
  return <At x={x} y={y} style={{opacity: o}}>
    <div style={{position: 'relative', height: hgt}}>
      <div style={{visibility: 'hidden', fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1.1, whiteSpace: 'nowrap'}}>{text}</div>
      {Array.from({length: slices}).map((_, i) => {
        const p = lerp(t, at + i * 0.06, at + 0.42 + i * 0.06, 0, 1);
        const dx = (1 - p) * (i % 2 ? 1 : -1) * W * 0.7;
        return <div key={i} style={{position: 'absolute', inset: 0, clipPath: `inset(${(i / slices) * 100}% 0 ${100 - ((i + 1) / slices) * 100}% 0)`,
          transform: `translateX(${dx}px)`, fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1.1, whiteSpace: 'nowrap',
          color: p < 1 ? accent : color, textShadow: '0 4px 18px rgba(0,0,0,0.45)'}}>{text}</div>;
      })}
    </div>
  </At>;
};

// ================================================================ 9. WeightPulse — a sentence whose keyword thickens as it is said
export const WeightPulse: React.FC<P> = ({duration, text = 'giá tốt nhất **Đà Nẵng**', x = 0.5, y = 0.76, size = 84, at = 0.35, color = '#FFFFFF', accent = T('#8EB3FF')}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * lerp(t, 0, 0.3);
  const parts = String(text).split(/(\*\*[^*]+\*\*)/).filter(Boolean);
  const p = lerp(t, at, at + 0.5, 0, 1, EASE_OUT);
  const sz = fit(size, String(text).replace(/\*/g, ''), W, 0.56);
  return <At x={x} y={y} style={{opacity: o}}>
    <div style={{fontFamily: SANS, fontSize: sz, color, whiteSpace: 'pre', textShadow: '0 3px 14px rgba(0,0,0,0.55)', fontWeight: 500}}>
      {parts.map((pt, i) => pt.startsWith('**')
        ? <span key={i} style={{display: 'inline-block', fontWeight: 800, color: accent, WebkitTextStroke: `${p * sz * 0.045}px ${accent}`,
            transform: `scale(${1 + 0.12 * p})`, margin: `0 ${sz * 0.12 * p}px`}}>{pt.slice(2, -2)}</span>
        : <span key={i} style={{opacity: 1 - 0.25 * p}}>{pt}</span>)}
    </div>
  </At>;
};

// ================================================================ 10. DustText — text blows away into dust on exit
export const DustText: React.FC<P> = ({duration, text = 'HẾT HÀNG', x = 0.5, y = 0.2, size = 170, at = 0, dustAt, color = '#FFFFFF'}) => {
  const {frame, fps, t, W, H} = useT();
  const d0 = dustAt ?? Math.max(at + 0.6, duration - 1.0);
  const p = lerp(t, d0, d0 + 0.9, 0, 1, EASE_OUT);
  const sz = fit(size, text, W, 0.66);
  const id = `dust${Math.round(x * 100)}${Math.round(y * 100)}`;
  return <AbsoluteFill style={{opacity: lerp(t, at, at + 0.25)}}>
    <svg width={0} height={0}><filter id={id}><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" />
      <feDisplacementMap in="SourceGraphic" scale={p * 160} xChannelSelector="R" yChannelSelector="G" /></filter></svg>
    <At x={x + p * 0.12} y={y - p * 0.03} style={{filter: `url(#${id})`, opacity: 1 - p}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, color, whiteSpace: 'nowrap', textShadow: '0 4px 16px rgba(0,0,0,0.5)'}}>{text}</div>
    </At>
    {p > 0 ? Array.from({length: 60}).map((_, i) => {
      const a = rnd(i) * 0.9 - 0.2, sp = 0.15 + rnd(i + 7) * 0.35;
      return <div key={i} style={{position: 'absolute', left: (x - 0.3 + rnd(i + 3) * 0.6 + p * sp) * W, top: (y - 0.02 + rnd(i + 5) * 0.05 - p * a * 0.15) * H,
        width: 4 + rnd(i + 9) * 6, height: 4 + rnd(i + 9) * 6, background: color, borderRadius: 2, opacity: (1 - p) * 0.9}} />;
    }) : null}
  </AbsoluteFill>;
};

// ================================================================ 11. PunchWord — one word fills the screen, then shrinks into place
export const PunchWord: React.FC<P> = ({duration, word = 'XỊN', x = 0.5, y = 0.16, size = 150, at = 0, hold = 0.3, color = '#FFFFFF', bg = T('rgba(14,21,48,0.85)')}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  const big = fit(900, word, W, 0.62, 0.95);
  const p = lerp(t, at + hold, at + hold + 0.35, 0, 1, EASE_IN);
  const sz = big + (size - big) * p;
  const yy = 0.5 + (y - 0.5) * p;
  return <AbsoluteFill style={{opacity: o}}>
    <AbsoluteFill style={{background: bg, opacity: (1 - p) * lerp(t, at, at + 0.06)}} />
    <At x={x} y={yy}><div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1, color, whiteSpace: 'nowrap', letterSpacing: '-0.03em',
      textShadow: '0 6px 26px rgba(0,0,0,0.5)', transform: `scale(${t < at + 0.08 ? 1.15 : 1})`}}>{word}</div></At>
  </AbsoluteFill>;
};

// ================================================================ 12. DocLabel — documentary place / date line with a typewriter
export const DocLabel: React.FC<P> = ({duration, place = 'ĐÀ NẴNG', date = '21/11/2026', sub = '', x = 0.07, y = 0.78, size = 46, at = 0.1, cps = 18}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const line = lerp(t, at, at + 0.4, 0, 1, EASE_OUT);
  const full = `${place}${date ? '  ·  ' + date : ''}`;
  const n = Math.max(0, Math.floor((t - at - 0.3) * cps));
  const n2 = Math.max(0, Math.floor((t - at - 0.3 - full.length / cps) * cps));
  const cursor = Math.floor(t * 2.5) % 2 === 0;
  return <AbsoluteFill style={{opacity: o}}>
    <div style={{position: 'absolute', left: x * W, top: `${y * 100}%`}}>
      <div style={{width: W * 0.32 * line, height: 4, background: T('#8EB3FF'), marginBottom: 14, boxShadow: '0 0 10px rgba(0,0,0,0.5)'}} />
      <div style={{fontFamily: SANS, fontWeight: 700, fontSize: size, letterSpacing: '0.16em', color: '#fff', textShadow: '0 2px 10px rgba(0,0,0,0.75)', whiteSpace: 'pre'}}>
        {full.slice(0, n)}{n < full.length && cursor ? '▍' : ''}</div>
      {sub ? <div style={{fontFamily: SERIF, fontStyle: 'italic', fontSize: size * 0.8, color: '#E6ECFF', marginTop: 6, textShadow: '0 2px 10px rgba(0,0,0,0.75)'}}>
        {sub.slice(0, n2)}</div> : null}
    </div>
  </AbsoluteFill>;
};

// ================================================================ 13. QuoteCard — big quote marks, the quote line by line, who said it
export const QuoteCard: React.FC<P> = ({duration, quote = 'Làm ăn phải giữ chữ tín.', who = '', source = '', x = 0.5, y = 0.2, w = 0.84, size = 62, at = 0}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * lerp(t, at, at + 0.3);
  const words = String(quote).split(' ');
  const per = Math.max(0.04, Math.min(0.16, (duration - at - 1.2) / Math.max(1, words.length)));
  return <At x={x} y={y} style={{opacity: o}}>
    <div style={{width: w * W, padding: '40px 46px 34px', boxSizing: 'border-box', borderRadius: 30, background: T('rgba(10,16,40,0.72)'),
      border: T('1.5px solid rgba(142,179,255,0.3)'), boxShadow: SHADOW_CARD, position: 'relative'}}>
      <div style={{position: 'absolute', left: 26, top: -70, fontFamily: SERIF, fontStyle: 'italic', fontWeight: 900, fontSize: 220, color: T('#8EB3FF'),
        lineHeight: 1, transform: `scale(${pop(frame, fps, at, 10)})`}}>“</div>
      <div style={{fontFamily: SERIF, fontStyle: 'italic', fontSize: size, lineHeight: 1.3, color: '#fff'}}>
        {words.map((wd, i) => <span key={i} style={{opacity: lerp(t, at + 0.25 + i * per, at + 0.45 + i * per)}}>{wd} </span>)}</div>
      {who ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: size * 0.5, color: T('#B4CBFF'), marginTop: 18,
        opacity: lerp(t, at + 0.4 + words.length * per, at + 0.7 + words.length * per)}}>— {who}{source ? <span style={{fontWeight: 500, color: '#C8D2EA'}}> · {source}</span> : null}</div> : null}
    </div>
  </At>;
};

// ================================================================ 14. MarqueeRows — huge rows sliding opposite ways (use "behind": true)
export const MarqueeRows: React.FC<P> = ({duration, text = 'IPHONE CHÍNH HÃNG', rows = 3, y = 0.3, size = 210, speed = 260, color = '#FFFFFF', gap = 1.0}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * lerp(t, 0, 0.35);
  const line = `${text} • `.repeat(6);
  return <AbsoluteFill style={{opacity: o, overflow: 'hidden'}}>
    {Array.from({length: rows}).map((_, i) => {
      const dir = i % 2 ? 1 : -1;
      const off = ((t * speed * dir) % (W * 2)) - W;
      const solid = i % 2 === 0;
      return <div key={i} style={{position: 'absolute', top: y * H + (i - (rows - 1) / 2) * size * gap, left: off, whiteSpace: 'nowrap', transform: 'translateY(-50%)',
        fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 1, letterSpacing: '-0.02em',
        color: solid ? color : 'transparent', WebkitTextStroke: solid ? undefined : `3px ${color}`, opacity: solid ? 0.95 : 0.8}}>{line}</div>;
    })}
  </AbsoluteFill>;
};

// ================================================================ 15. TrackLabel — a label that follows a tracked hand / product
/** {text, sub, track: [[x, y], ...] (per frame, filled by render.py from "track": {"box": [x, y, w, h]}), dx, dy} */
export const TrackLabel: React.FC<P> = ({duration, text = '24.990.000đ', sub = '', track = [], dx = 0.16, dy = -0.1, at = 0, color = T('#3158FF')}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  const pt: [number, number] = track.length ? track[Math.min(track.length - 1, frame)] : [0.5, 0.5];
  const s = pop(frame, fps, at, 11);
  const lx = pt[0] + dx, ly = pt[1] + dy;
  return <AbsoluteFill style={{opacity: o}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      <circle cx={pt[0] * W} cy={pt[1] * H} r={12 * s} fill="#fff" stroke={color} strokeWidth={5} />
      <line x1={pt[0] * W} y1={pt[1] * H} x2={pt[0] * W + (lx - pt[0]) * W * s} y2={pt[1] * H + (ly - pt[1]) * H * s} stroke="#fff" strokeWidth={4} />
    </svg>
    <At x={lx} y={ly} anchor={dx >= 0 ? '0%, -50%' : '-100%, -50%'} style={{transform: `translate(${dx >= 0 ? '0%' : '-100%'},-50%) scale(${s})`,
      transformOrigin: dx >= 0 ? 'left center' : 'right center'}}>
      <div style={{background: '#fff', borderRadius: 18, padding: '10px 22px', boxShadow: SHADOW_CARD, borderLeft: `8px solid ${color}`, whiteSpace: 'nowrap'}}>
        <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 52, color: C.ink, lineHeight: 1.1}}>{text}</div>
        {sub ? <div style={{fontFamily: SANS, fontWeight: 600, fontSize: 30, color: '#5B6274'}}>{sub}</div> : null}
      </div>
    </At>
  </AbsoluteFill>;
};

// ================================================================ 16. RiseText — rises from behind an edge (table top, product box)
/** {text, edge: 0.62 (y of the edge the text hides behind), x, size} */
export const RiseText: React.FC<P> = ({duration, text = 'MỚI VỀ', sub = '', x = 0.5, edge = 0.6, size = 170, at = 0, color = '#FFFFFF'}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  const p = lerp(t, at, at + 0.55, 0, 1, EASE_IN);
  const sz = fit(size, text, W, 0.66);
  const blockH = sz * (sub ? 1.45 : 1.1);
  return <AbsoluteFill style={{opacity: o, clipPath: `inset(0 0 ${(1 - edge) * 100}% 0)`}}>
    <div style={{position: 'absolute', left: x * W, top: edge * H - blockH * p, transform: 'translateX(-50%)', textAlign: 'center'}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1.05, color, whiteSpace: 'nowrap', textShadow: '0 6px 22px rgba(0,0,0,0.45)'}}>{text}</div>
      {sub ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: sz * 0.26, color, letterSpacing: '0.22em'}}>{sub}</div> : null}
    </div>
  </AbsoluteFill>;
};

// ================================================================ 17. MirrorText — standing on a glossy table with a reflection
export const MirrorText: React.FC<P> = ({duration, text = 'IPHONE 17 PRO', sub = '', x = 0.5, y = 0.6, size = 140, at = 0, color = '#FFFFFF'}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const s = pop(frame, fps, at, 13);
  const sz = fit(size, text, W, 0.64);
  const face: React.CSSProperties = {fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1, color, whiteSpace: 'nowrap', letterSpacing: '0.01em'};
  return <At x={x} y={y} anchor="-50%, -100%" style={{opacity: o * Math.min(1, s * 1.3)}}>
    <div style={{textAlign: 'center', transform: `translateY(${(1 - s) * 40}px)`}}>
      {sub ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: sz * 0.24, color, letterSpacing: '0.3em', marginBottom: 8, textShadow: '0 2px 10px rgba(0,0,0,0.5)'}}>{sub}</div> : null}
      <div style={{...face, textShadow: '0 4px 14px rgba(0,0,0,0.35)'}}>{text}</div>
      <div style={{...face, transform: 'scaleY(-1)', opacity: 0.32, filter: 'blur(1.5px)', marginTop: 4,
        maskImage: 'linear-gradient(to top, rgba(0,0,0,0.9), transparent 75%)', WebkitMaskImage: 'linear-gradient(to top, rgba(0,0,0,0.9), transparent 75%)'}}>{text}</div>
    </div>
  </At>;
};

// ================================================================ 18. FocusText — sharp while the room is soft, then focus pulls to the speaker
/** {text, swap: 1.4} — render.py adds a frost "mode": "none" that un-blurs the video at `swap`. */
export const FocusText: React.FC<P> = ({duration, text = 'CÂU CHUYỆN', sub = '', x = 0.5, y = 0.3, size = 170, at = 0, swap = 1.4, color = '#FFFFFF'}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * lerp(t, at, at + 0.3);
  const b = lerp(t, swap, swap + 0.55, 0, 1, EASE_OUT);
  const sz = fit(size, text, W, 0.64);
  return <At x={x} y={y} style={{opacity: o * (1 - 0.65 * b), filter: `blur(${b * 16}px)`, transform: `translate(-50%,-50%) scale(${1 + b * 0.08})`, textAlign: 'center'}}>
    <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, color, whiteSpace: 'nowrap', textShadow: '0 4px 18px rgba(0,0,0,0.4)'}}>{text}</div>
    {sub ? <div style={{fontFamily: SERIF, fontStyle: 'italic', fontSize: sz * 0.32, color}}>{sub}</div> : null}
  </At>;
};

// ================================================================ 19. Odometer — digits roll like a mechanical counter and land
export const Odometer: React.FC<P> = ({duration, value = '24.990.000', unit = 'đ', label = '', x = 0.5, y = 0.18, size = 150, at = 0.1, dur = 1.3, color = '#FFFFFF'}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * lerp(t, at - 0.1, at + 0.1);
  const chars = Array.from(String(value));
  const sz = fit(size, value + unit, W, 0.64);
  const nd = chars.filter((c) => /\d/.test(c)).length;
  let di = 0;
  return <At x={x} y={y} style={{opacity: o, textAlign: 'center'}}>
    {label ? <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz * 0.22, letterSpacing: '0.22em', color: '#fff', marginBottom: 10, textShadow: '0 2px 10px rgba(0,0,0,0.6)'}}>{label}</div> : null}
    <div style={{display: 'flex', alignItems: 'flex-end', justifyContent: 'center', fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1, color,
      fontVariantNumeric: 'tabular-nums', filter: 'drop-shadow(0 4px 14px rgba(0,0,0,0.55))'}}>
      {chars.map((c, i) => {
        if (!/\d/.test(c)) return <span key={i}>{c}</span>;
        const k = di++;
        const end = at + dur * (0.45 + 0.55 * (k / Math.max(1, nd - 1)));  // left digits land first
        const target = Number(c) + 10 * (3 + (nd - k));
        const p = lerp(t, at, end, 0, 1, EASE_IN);
        const pos = target * p;
        return <span key={i} style={{display: 'inline-block', height: sz, overflow: 'hidden', position: 'relative', width: '0.62em'}}>
          <span style={{position: 'absolute', left: 0, right: 0, top: -(pos % 10) * sz, display: 'flex', flexDirection: 'column'}}>
            {Array.from({length: 11}).map((_, j) => <span key={j} style={{height: sz, filter: p < 1 ? `blur(${Math.min(4, (1 - p) * 8)}px)` : undefined}}>{j % 10}</span>)}
          </span>
        </span>;
      })}
      <span style={{fontSize: sz * 0.5, marginLeft: 6}}>{unit}</span>
    </div>
  </At>;
};

// ================================================================ 20. SealBadge — round seal with rotating ring text and a centre value
export const SealBadge: React.FC<P> = ({duration, ring = 'GIẢM GIÁ • HỌC SINH SINH VIÊN • ', center = '-1TR', sub = '', x = 0.8, y = 0.2, size = 300, at = 0, color = T('#3158FF'), speed = 18}) => {
  const {frame, fps, t} = useT();
  const o = exit(frame, fps, duration);
  const s = pop(frame, fps, at, 10);
  const R = size / 2;
  const id = `seal${Math.round(x * 100)}${Math.round(y * 100)}`;
  return <At x={x} y={y} style={{opacity: o, transform: `translate(-50%,-50%) scale(${s}) rotate(${(1 - s) * -90}deg)`}}>
    <div style={{position: 'relative', width: size, height: size}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: '50%', background: color, boxShadow: '0 14px 30px rgba(0,0,0,0.4)', border: '6px solid #fff'}} />
      <svg width={size} height={size} style={{position: 'absolute', inset: 0, transform: `rotate(${t * speed}deg)`}}>
        <defs><path id={id} d={`M ${R},${R} m -${R * 0.78},0 a ${R * 0.78},${R * 0.78} 0 1,1 ${R * 1.56},0 a ${R * 0.78},${R * 0.78} 0 1,1 -${R * 1.56},0`} /></defs>
        <text fontFamily={SANS} fontWeight={800} fontSize={size * 0.085} fill="#fff" letterSpacing={size * 0.012}>
          <textPath href={`#${id}`}>{ring.repeat(Math.max(1, Math.round(60 / ring.length)))}</textPath></text>
      </svg>
      <div style={{position: 'absolute', inset: size * 0.2, borderRadius: '50%', border: '3px dashed rgba(255,255,255,0.7)', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', color: '#fff', fontFamily: SANS, fontWeight: 800}}>
        <div style={{fontSize: size * 0.2, lineHeight: 1}}>{center}</div>
        {sub ? <div style={{fontSize: size * 0.07, letterSpacing: '0.1em'}}>{sub}</div> : null}
      </div>
    </div>
  </At>;
};

// ================================================================ 21. CubeFlip — words on the faces of a 3D cube that flips to the next word
export const CubeFlip: React.FC<P> = ({duration, words = ['RẺ', 'BỀN', 'XỊN'], prefix = '', x = 0.5, y = 0.18, size = 150, at = 0, step, color = '#FFFFFF', face = T('#3158FF')}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * lerp(t, at, at + 0.2);
  const st = step ?? Math.max(0.45, (duration - at - 0.4) / words.length);
  const k = Math.min(words.length - 1, Math.max(0, Math.floor((t - at) / st)));
  const f = Math.min(1, Math.max(0, ((t - at) - k * st) / 0.32));
  const e = f < 1 ? 1 - Math.pow(1 - f, 3) : 1;
  const longest = words.reduce((a: string, b: string) => (b.length > a.length ? b : a), '');
  const sz = fit(size, (prefix ? prefix + '   ' : '') + longest, W, prefix ? 0.56 : 0.68, 0.84);
  const h = sz * 1.3, w = Math.max(...words.map((wd: string) => Array.from(wd).length)) * sz * 0.7 + sz * 0.6;
  const fc = (wd: string, rot: number): React.CSSProperties => ({position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
    background: face, color, fontFamily: SANS, fontWeight: 800, fontSize: sz, borderRadius: 18, backfaceVisibility: 'hidden',
    transform: `rotateX(${rot}deg) translateZ(${h / 2}px)`, boxShadow: 'inset 0 -8px 0 rgba(0,0,0,0.2)'});
  return <At x={x} y={y} style={{opacity: o}}>
    <div style={{display: 'flex', alignItems: 'center', gap: sz * 0.25}}>
      {prefix ? <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz * 0.7, color: '#fff', whiteSpace: 'nowrap', textShadow: '0 3px 14px rgba(0,0,0,0.5)'}}>{prefix}</div> : null}
      <div style={{width: w, height: h, perspective: 900}}>
        <div style={{position: 'relative', width: '100%', height: '100%', transformStyle: 'preserve-3d', transform: `translateZ(-${h / 2}px) rotateX(${-90 * (k > 0 ? e : 0)}deg)`}}>
          {k > 0 && f < 1 ? <div style={fc(words[k - 1], 0)}>{words[k - 1]}</div> : null}
          <div style={fc(words[k], k > 0 && f < 1 ? 90 : 0)}>{words[k]}</div>
        </div>
      </div>
    </div>
  </At>;
};

// ================================================================ 22. RaysTitle — poster title with light rays bursting behind it
export const RaysTitle: React.FC<P> = ({duration, title = 'CHƯƠNG 1', sub = '', x = 0.5, y = 0.3, size = 170, at = 0, color = '#FFFFFF', ray = T('#8EB3FF')}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  const p = lerp(t, at, at + 0.6, 0, 1, EASE_IN);
  const sz = fit(size, title, W, 0.66);
  return <AbsoluteFill style={{opacity: o}}>
    <div style={{position: 'absolute', left: x * W, top: y * H, width: W * 2.2, height: W * 2.2, transform: `translate(-50%,-50%) rotate(${t * 6}deg) scale(${0.4 + 0.6 * p})`,
      opacity: 0.55 * p, background: `repeating-conic-gradient(from 0deg, ${ray} 0deg 4deg, transparent 4deg 14deg)`,
      maskImage: 'radial-gradient(circle, #000 0%, rgba(0,0,0,0.6) 25%, transparent 55%)', WebkitMaskImage: 'radial-gradient(circle, #000 0%, rgba(0,0,0,0.6) 25%, transparent 55%)'}} />
    <At x={x} y={y} style={{textAlign: 'center', transform: `translate(-50%,-50%) scale(${interpolate(p, [0, 1], [1.25, 1])})`, opacity: p}}>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, color, whiteSpace: 'nowrap', textShadow: `0 0 40px ${ray}, 0 6px 22px rgba(0,0,0,0.5)`}}>{title}</div>
      {sub ? <div style={{fontFamily: SERIF, fontStyle: 'italic', fontSize: sz * 0.3, color}}>{sub}</div> : null}
    </At>
  </AbsoluteFill>;
};

// ================================================================ 23. InkText — text bleeding out of an ink blot
export const InkText: React.FC<P> = ({duration, text = 'Hương vị xưa', x = 0.5, y = 0.22, size = 150, at = 0, color = '#FFFFFF', script = true}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const p = lerp(t, at, at + 1.1, 0, 1, EASE_OUT);
  const sz = fit(size, text, W, script ? 0.5 : 0.64);
  const id = `ink${Math.round(x * 100)}${Math.round(y * 100)}`;
  return <AbsoluteFill style={{opacity: o}}>
    <svg width={0} height={0}><filter id={id}><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="8" />
      <feDisplacementMap in="SourceGraphic" scale={60 * (1 - p) + 6} xChannelSelector="R" yChannelSelector="G" /></filter></svg>
    <At x={x} y={y} style={{filter: `url(#${id})`}}>
      <div style={{fontFamily: script ? SCRIPT : SERIF, fontStyle: script ? 'normal' : 'italic', fontWeight: 700, fontSize: sz, color, whiteSpace: 'nowrap',
        maskImage: `radial-gradient(circle at 40% 55%, #000 ${p * 70}%, transparent ${p * 70 + 18}%)`,
        WebkitMaskImage: `radial-gradient(circle at 40% 55%, #000 ${p * 70}%, transparent ${p * 70 + 18}%)`, textShadow: '0 3px 12px rgba(0,0,0,0.45)'}}>{text}</div>
    </At>
  </AbsoluteFill>;
};

// ================================================================ 24. RansomText — every letter cut from a different newspaper scrap
export const RansomText: React.FC<P> = ({duration, text = 'DRAMA', x = 0.5, y = 0.16, size = 120, at = 0, cps = 14}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const chars = Array.from(String(text));
  const sz = fit(size, text, W, 0.78, 0.9);
  const papers = ['#FFFFFF', '#F3E9C8', '#111111', '#E5303C', '#FFD84D', '#DDE6F7'];
  const fonts = [SANS, SERIF, SANS, SERIF];
  return <At x={x} y={y} style={{opacity: o}}>
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: sz * 0.06, maxWidth: W * 0.9}}>
      {chars.map((c, i) => {
        if (c === ' ') return <span key={i} style={{width: sz * 0.3}} />;
        const s = pop(frame, fps, at + i / cps, 9);
        const bg = papers[Math.floor(rnd(i + 1) * papers.length)];
        const dark = bg === '#111111' || bg === '#E5303C';
        return <span key={i} style={{display: 'inline-block', background: bg, color: dark ? '#fff' : '#111', fontFamily: fonts[i % 4],
          fontStyle: rnd(i + 4) > 0.6 ? 'italic' : 'normal', fontWeight: rnd(i + 2) > 0.4 ? 800 : 600, fontSize: sz * (0.85 + rnd(i + 6) * 0.3),
          padding: `${sz * 0.04}px ${sz * 0.1}px`, lineHeight: 1.05, transform: `rotate(${(rnd(i + 8) - 0.5) * 16}deg) scale(${s})`,
          boxShadow: '0 6px 12px rgba(0,0,0,0.35)', clipPath: `polygon(${rnd(i) * 6}% 0, 100% ${rnd(i + 1) * 8}%, ${100 - rnd(i + 2) * 6}% 100%, 0 ${100 - rnd(i + 3) * 8}%)`}}>{c}</span>;
      })}
    </div>
  </At>;
};

// ================================================================ 25. AIChat — a prompt, then the AI answer streaming word by word
export const AIChat: React.FC<P> = ({duration, prompt = 'Viết caption bán iPhone', answer = 'Đây là 3 caption...', name = 'Claude', x = 0.5, y = 0.1, w = 0.86, size = 46, at = 0, wps = 7}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * lerp(t, at, at + 0.25);
  const words = String(answer).split(' ');
  const tA = at + 0.7;
  const n = Math.max(0, Math.floor((t - tA - 0.5) * wps));
  const thinking = t > tA && t < tA + 0.5;
  const cursor = Math.floor(t * 3) % 2 === 0;
  return <At x={x} y={y} anchor="-50%, 0%" style={{opacity: o}}>
    <div style={{width: w * W, display: 'flex', flexDirection: 'column', gap: 18, fontFamily: SANS}}>
      <div style={{alignSelf: 'flex-end', maxWidth: '78%', background: T('#3158FF'), color: '#fff', fontWeight: 600, fontSize: size, padding: '16px 24px',
        borderRadius: '26px 26px 6px 26px', transform: `scale(${pop(frame, fps, at, 12)})`, transformOrigin: 'right bottom', boxShadow: SHADOW_CARD}}>{prompt}</div>
      {t > tA ? <div style={{alignSelf: 'flex-start', maxWidth: '92%', background: '#fff', color: C.ink, fontWeight: 500, fontSize: size, lineHeight: 1.35, padding: '18px 26px',
        borderRadius: '26px 26px 26px 6px', boxShadow: SHADOW_CARD, transform: `scale(${pop(frame, fps, tA, 12)})`, transformOrigin: 'left top'}}>
        <div style={{fontWeight: 800, fontSize: size * 0.7, color: '#D97757', marginBottom: 6}}>✳ {name}</div>
        {thinking ? <span style={{letterSpacing: 6}}>{'•••'.slice(0, 1 + (Math.floor(t * 6) % 3))}</span>
          : <span>{words.slice(0, n).join(' ')}{n < words.length && cursor ? ' ▍' : ''}</span>}
      </div> : null}
    </div>
  </At>;
};

// ================================================================ 26. BeatText — words pop on the music beats
/** {text: "MỘT|HAI|BA", beats: [s...] relative to the overlay (render.py fills them from the music)} */
export const BeatText: React.FC<P> = ({duration, text = 'SALE|SALE|SALE', beats = [], x = 0.5, y = 0.2, size = 200, color = '#FFFFFF', accent = T('#3158FF')}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const words = String(text).split('|');
  const bt: number[] = beats.length ? beats : words.map((_, i) => 0.15 + i * 0.5);
  let k = -1;
  bt.forEach((b, i) => { if (t >= b) k = i; });
  if (k < 0) return null;
  const wd = words[k % words.length];
  const since = t - bt[k];
  const sc = 1 + 0.35 * Math.exp(-since * 14);
  const sz = fit(size, wd, W, 0.66);
  return <At x={x} y={y} style={{opacity: o, transform: `translate(-50%,-50%) scale(${sc}) rotate(${(k % 2 ? 1 : -1) * 3}deg)`}}>
    <div style={{fontFamily: SANS, fontWeight: 800, fontSize: sz, lineHeight: 1, whiteSpace: 'nowrap', color: k % 2 ? accent : color,
      WebkitTextStroke: k % 2 ? '3px #fff' : undefined, textShadow: '0 6px 22px rgba(0,0,0,0.45)'}}>{wd}</div>
  </At>;
};

export const TEXT_COMPS: Record<string, React.FC<any>> = {
  Text3D, WeaveText, ProjectText, MetalText, GlassText, NeonText, WriteOn, SliceText, WeightPulse, DustText, PunchWord, DocLabel, QuoteCard,
  MarqueeRows, TrackLabel, RiseText, MirrorText, FocusText, Odometer, SealBadge, CubeFlip, RaysTitle, InkText, RansomText, AIChat, BeatText,
};
