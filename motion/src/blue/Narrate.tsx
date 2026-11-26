// NARRATE pack — cutaway scenes for talking-head videos, any industry.
//   ExplainCanvas: the speaker shrinks into a live bubble in the corner (never leaves the frame), a clean paper / dark /
//                  brand canvas opens behind them and the idea is drawn: a search bar typing, numbered icon tiles on a
//                  ribbon, icons orbiting a word, a before → after comparison, or a single step card. Then the speaker
//                  grows back to full frame. Trend cutaways usually drop the face; keeping it alive is our twist.
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, spring, staticFile} from 'remotion';
import {exit, SANS, SERIF, T} from './theme';
import {lerp, P, useT} from './Vip';
import {ICON} from './Estate';

const url = (s: string) => (s.startsWith('http') ? s : staticFile(s));
const smooth = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const isVid = (s?: string) => !!s && /\.(mp4|mov|webm|m4v)$/i.test(s);
const BG: Record<string, {bg: string; ink: string; sub: string; card: string; line: string}> = {
  paper: {bg: 'radial-gradient(120% 80% at 50% 30%, #FFFDF8 0%, #F4EEE2 60%, #E9E0CF 100%)', ink: '#141A26', sub: '#6B6252', card: '#FFFFFF', line: 'rgba(20,26,38,0.18)'},
  dark: {bg: 'radial-gradient(120% 80% at 50% 30%, #1A2436 0%, #0B1220 70%, #060A12 100%)', ink: '#FFFFFF', sub: 'rgba(255,255,255,0.7)', card: '#18233A', line: 'rgba(255,255,255,0.2)'},
  brand: {bg: T('radial-gradient(120% 80% at 50% 30%, #3A5BD6 0%, #1D2F86 70%, #101A52 100%)'), ink: '#FFFFFF', sub: 'rgba(255,255,255,0.78)', card: 'rgba(255,255,255,0.12)', line: 'rgba(255,255,255,0.25)'},
};
const Ico: React.FC<{name?: string; size?: number; color?: string; sw?: number}> = ({name = 'star', size = 48, color = '#fff', sw = 1.9}) =>
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d={ICON[name] || ICON.star} /></svg>;
/** "**word**" → accent serif italic; the rest stays sans bold */
const rich = (s: string, acc: string) => String(s || '').split(/(\*\*[^*]+\*\*)/).map((part, i) => part.startsWith('**')
  ? <span key={i} style={{fontFamily: SERIF, fontStyle: 'italic', fontWeight: 500, color: acc}}>{part.slice(2, -2)}</span> : <span key={i}>{part}</span>);

/**
 * ExplainCanvas props: src (the speaker footage of this overlay; render.py cuts it from the timeline when omitted),
 * face [x, y] (0–1 face centre in the frame), bubble {x, y, r} (where the live face bubble sits; default top-right),
 * keep_face (false = cut the speaker away fully), back (grow back to full frame at the end, default true),
 * bg paper | dark | brand, accent (colour), title ("Người mua đang **tìm** gì?"), mode + its data:
 *   search  {query, items: ["kết quả 1", …]}             tiles   {items: [{icon, label, t}] ≤4; t = pop time (s) on the spoken word}
 *   orbit   {center, items: [{icon | photo, label}]}      compare {a: {label, value, photo|icon}, b: {…}}
 *   card    {kicker: "BƯỚC 01", text}
 */
export const ExplainCanvas: React.FC<P> = ({duration, src, face = [0.5, 0.3], bubble = {}, keep_face = true, back = true, bg = 'paper',
  accent, title, mode = 'tiles', query = '', items = [], center, a = {}, b = {}, kicker = 'BƯỚC 01', text = '', at = 0.45}) => {
  const {frame, fps, t, W, H} = useT();
  const C = BG[bg] || BG.paper;
  const acc = accent || (bg === 'brand' ? '#FFD36B' : '#C29A4E');
  const inP = lerp(t, 0, 0.5, 0, 1, (x) => smooth(x));
  const outP = back ? lerp(t, duration - 0.5, duration - 0.04, 0, 1, (x) => smooth(x)) : 0;
  // iris first (a circle closes around the face at full size), then the bubble flies to its corner; reversed on the way back
  const D = duration, ez = (x: number) => smooth(x);
  const kc = Math.min(lerp(t, 0, 0.3, 0, 1, ez), back ? 1 - lerp(t, D - 0.3, D - 0.02, 0, 1, ez) : 1);
  const km = Math.min(lerp(t, 0.12, 0.52, 0, 1, ez), back ? 1 - lerp(t, D - 0.52, D - 0.14, 0, 1, ez) : 1);
  const k = km;
  const bx = (bubble.x ?? 0.79) * W, by = (bubble.y ?? 0.135) * H, br = bubble.r ?? 150, bs = bubble.s ?? 0.5;
  const fx = face[0] * W, fy = face[1] * H;
  const s = 1 + ((keep_face ? bs : 1) - 1) * km;
  const Rl = Math.hypot(W, H) * (1 - kc) + (keep_face ? br / bs : 0) * kc;
  const Rs = Rl * s;
  const cxs = fx + (bx - fx) * (keep_face ? km : 0), cys = fy + (by - fy) * (keep_face ? km : 0);
  const tx = cxs - fx * s, ty = cys - fy * s;
  const T0 = at; // canvas content clock
  const tt = t - T0;
  const gone = 1 - outP; // content fades as the speaker grows back
  const pop = (d: number, damp = 13) => spring({frame: frame - (T0 + d) * fps, fps, config: {damping: damp, stiffness: 150, mass: 0.7}});
  const titleEl = title ? <div style={{position: 'absolute', left: 70, right: keep_face ? W - (bx - br) + 36 : 70, top: H * 0.085, fontFamily: SANS, fontWeight: 800,
    fontSize: 86, lineHeight: 1.08, letterSpacing: '-0.02em', color: C.ink, opacity: lerp(tt, 0, 0.35) * gone, transform: `translateY(${(1 - lerp(tt, 0, 0.35)) * 20}px)`}}>
    {rich(title, acc)}</div> : null;

  let body: React.ReactNode = null;
  if (mode === 'search') {
    const typed = Math.max(0, Math.floor(tt * 16));
    const q = String(query).slice(0, typed), done = typed >= String(query).length;
    const tDone = String(query).length / 16;
    body = <div style={{position: 'absolute', left: W * 0.07, width: W * 0.86, top: H * 0.4}}>
      <div style={{height: 140, borderRadius: 70, background: C.card, display: 'flex', alignItems: 'center', gap: 22, padding: '0 40px',
        boxShadow: '0 22px 50px rgba(20,26,38,0.18), 0 2px 0 rgba(255,255,255,0.8) inset', border: `1px solid ${C.line}`,
        transform: `scale(${0.9 + 0.1 * pop(0)})`, opacity: pop(0)}}>
        <Ico name="search" size={52} color={acc} sw={2.4} />
        <div style={{fontFamily: SANS, fontWeight: 600, fontSize: 50, color: C.ink, whiteSpace: 'nowrap', overflow: 'hidden', flex: 1}}>
          {q}<span style={{display: 'inline-block', width: 4, height: 50, marginLeft: 4, verticalAlign: 'middle', background: acc, opacity: Math.floor(t * 2.4) % 2 ? 0 : 1}} /></div>
      </div>
      <div style={{marginTop: 34, display: 'flex', flexDirection: 'column', gap: 18}}>
        {done ? items.slice(0, 4).map((it: string, i: number) => {
          const p = pop(tDone + 0.25 + i * 0.22, 15);
          return <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, padding: '22px 30px', borderRadius: 24, background: C.card,
            border: `1px solid ${C.line}`, boxShadow: '0 10px 24px rgba(20,26,38,0.10)', opacity: p, transform: `translateY(${(1 - p) * 24}px)`}}>
            <div style={{width: 14, height: 14, borderRadius: 99, background: acc, flex: 'none'}} />
            <div style={{fontFamily: SANS, fontWeight: 600, fontSize: 44, color: C.ink}}>{rich(it, acc)}</div></div>;
        }) : null}
      </div>
    </div>;
  } else if (mode === 'tiles') {
    const n = Math.max(1, Math.min(4, items.length)), tw = n > 3 ? 222 : 268, gap = n > 3 ? 20 : 40, row = n * tw + (n - 1) * gap, x0 = (W - row) / 2, y0 = H * 0.43;
    const rib = lerp(tt, 0.1, 1.1, 0, 1, (x) => smooth(x));
    const ribPath = `M ${-80} ${y0 + tw * 1.2} C ${W * 0.25} ${y0 + tw * 1.9}, ${W * 0.45} ${y0 - tw * 0.3}, ${W * 0.7} ${y0 + tw * 0.55} S ${W + 120} ${y0 + tw * 0.1}, ${W + 160} ${y0 - tw * 0.6}`;
    body = <>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <defs><linearGradient id="ecrib" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor={acc} stopOpacity={0.05} /><stop offset="0.5" stopColor={acc} stopOpacity={0.55} />
          <stop offset="1" stopColor={acc} stopOpacity={0.15} /></linearGradient></defs>
        <path d={ribPath} fill="none" stroke="url(#ecrib)" strokeWidth={96} strokeLinecap="round" pathLength={1} strokeDasharray={`${rib} 1`} opacity={gone} />
      </svg>
      {items.slice(0, 4).map((it: any, i: number) => {
        const p = it.t != null ? spring({frame: frame - it.t * fps, fps, config: {damping: 11, stiffness: 150, mass: 0.7}}) : pop(0.15 + i * 0.32, 11);
        return <div key={i} style={{position: 'absolute', left: x0 + i * (tw + gap), top: y0, width: tw, opacity: Math.min(1, p * 1.4) * gone,
          transform: `translateY(${(1 - p) * 60}px) rotate(${(1 - p) * -8}deg)`}}>
          <div style={{width: tw, height: tw, borderRadius: 48, position: 'relative', overflow: 'hidden', display: 'grid', placeItems: 'center',
            background: `linear-gradient(150deg, ${acc}, ${acc}CC 55%, ${acc}99)`, boxShadow: `0 24px 46px ${acc}55, inset 0 2px 0 rgba(255,255,255,0.45)`}}>
            <Ico name={it.icon} size={tw * 0.44} color="#fff" sw={1.7} />
            <div style={{position: 'absolute', left: 18, bottom: 6, fontFamily: SERIF, fontStyle: 'italic', fontSize: tw * 0.3, lineHeight: 1, color: 'rgba(255,255,255,0.42)'}}>
              {String(i + 1).padStart(2, '0')}</div>
          </div>
          <div style={{marginTop: 24, marginLeft: -gap / 2, width: tw + gap, textAlign: 'center', fontFamily: SANS, fontWeight: 800, fontSize: n > 3 ? 34 : 42, lineHeight: 1.12, color: C.ink}}>{it.label}</div>
        </div>;
      })}
    </>;
  } else if (mode === 'orbit') {
    const cx = W / 2, cy = H * 0.55, r1 = W * 0.26, r2 = W * 0.41;
    const ring = (r: number, d: number) => <circle cx={cx} cy={cy} r={r} fill="none" stroke={C.line} strokeWidth={2.5} strokeDasharray="10 14"
      transform={`rotate(${t * d} ${cx} ${cy})`} opacity={lerp(tt, 0, 0.4) * gone} />;
    body = <>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>{ring(r1, 14)}{ring(r2, -9)}</svg>
      <div style={{position: 'absolute', left: cx, top: cy, transform: `translate(-50%,-50%) scale(${0.8 + 0.2 * pop(0)})`, opacity: pop(0) * gone, textAlign: 'center',
        width: r1 * 1.5, fontFamily: SANS, fontWeight: 800, fontSize: 54, lineHeight: 1.1, color: C.ink}}>{rich(center || '', acc)}</div>
      {items.slice(0, 7).map((it: any, i: number) => {
        const onOuter = i % 2 === 1, r = onOuter ? r2 : r1, n = items.length;
        const ang = -Math.PI / 2 + (i / n) * Math.PI * 2 + t * 0.16; // one slow spin for the whole system, so icons never bunch up
        const p = it.t != null ? spring({frame: frame - it.t * fps, fps, config: {damping: 12, stiffness: 150, mass: 0.7}}) : pop(0.2 + i * 0.16, 12), sz = 128;
        return <div key={i} style={{position: 'absolute', left: cx + Math.cos(ang) * r, top: cy + Math.sin(ang) * r, transform: `translate(-50%,-50%) scale(${p})`,
          opacity: gone, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8}}>
          <div style={{width: sz, height: sz, borderRadius: 99, overflow: 'hidden', display: 'grid', placeItems: 'center', background: it.photo ? '#000' : C.card,
            border: `3px solid ${acc}`, boxShadow: '0 14px 30px rgba(20,26,38,0.22)'}}>
            {it.photo ? <Img src={url(it.photo)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : <Ico name={it.icon} size={60} color={acc} sw={2} />}</div>
          {it.label ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 28, color: C.ink, whiteSpace: 'nowrap', background: C.card, padding: '4px 14px', borderRadius: 99,
            border: `1px solid ${C.line}`}}>{it.label}</div> : null}
        </div>;
      })}
    </>;
  } else if (mode === 'compare') {
    const side = (d: any, x: number, y: number, glow: string, delay: number) => {
      const p = pop(delay, 12);
      const num = String(d.value || '');
      const m = num.match(/^([^\d]*)([\d.,]+)(.*)$/);
      const cp = lerp(tt, delay + 0.1, delay + 0.9, 0, 1, (q) => 1 - Math.pow(1 - q, 3));
      let shown = num;
      if (m) {
        const v = parseFloat(m[2].replace(/\./g, '').replace(',', '.'));
        const dec = (m[2].split(',')[1] || '').length;
        shown = m[1] + (v * cp).toLocaleString('vi-VN', {minimumFractionDigits: dec, maximumFractionDigits: dec}) + m[3];
      }
      return <div style={{position: 'absolute', left: x, top: y, transform: 'translate(-50%,-50%)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, opacity: gone}}>
        <div style={{position: 'absolute', width: 420, height: 420, borderRadius: 999, background: glow, filter: 'blur(60px)', opacity: 0.55 * p, top: -60}} />
        <div style={{width: 210, height: 210, borderRadius: 999, overflow: 'hidden', border: '5px solid #fff', boxShadow: '0 18px 40px rgba(0,0,0,0.25)', position: 'relative',
          transform: `scale(${p})`, display: 'grid', placeItems: 'center', background: C.card}}>
          {d.photo ? <Img src={url(d.photo)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : <Ico name={d.icon || 'home'} size={96} color={acc} />}</div>
        <div style={{position: 'relative', fontFamily: SANS, fontWeight: 800, fontSize: 86, color: C.ink, letterSpacing: '-0.02em', opacity: p}}>{shown}</div>
        <div style={{position: 'relative', fontFamily: SANS, fontWeight: 700, fontSize: 30, color: C.sub, textTransform: 'uppercase', letterSpacing: '0.12em', opacity: p}}>{d.label}</div>
      </div>;
    };
    const ar = lerp(tt, 0.7, 1.3, 0, 1, (x) => smooth(x));
    body = <>
      {side(a, W * 0.3, H * 0.44, '#E0605A', 0.1)}
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: gone}}>
        <path d={`M ${W * 0.36} ${H * 0.57} C ${W * 0.48} ${H * 0.66}, ${W * 0.55} ${H * 0.6}, ${W * 0.6} ${H * 0.58}`} fill="none" stroke={acc} strokeWidth={6}
          strokeLinecap="round" pathLength={1} strokeDasharray={`${ar} 1`} />
        {ar > 0.95 ? <path d={`M ${W * 0.6 - 26} ${H * 0.58 - 16} L ${W * 0.6 + 4} ${H * 0.58} L ${W * 0.6 - 22} ${H * 0.58 + 20}`} fill="none" stroke={acc} strokeWidth={6}
          strokeLinecap="round" strokeLinejoin="round" /> : null}
      </svg>
      {side(b, W * 0.7, H * 0.67, acc, 0.9)}
    </>;
  } else if (mode === 'card') {
    const p = pop(0.05, 14);
    const cx = W / 2, cy = H * 0.52;
    body = <>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: lerp(tt, 0, 0.4) * gone}}>
        {[0.3, 0.42, 0.56].map((r, i) => <circle key={i} cx={cx} cy={cy} r={W * r} fill="none" stroke={C.line} strokeWidth={2.5} strokeDasharray={i === 1 ? '2 0' : '10 14'}
          transform={`rotate(${t * (i % 2 ? -10 : 12)} ${cx} ${cy})`} />)}
      </svg>
      <div style={{position: 'absolute', left: cx, top: cy, width: W * 0.74, transform: `translate(-50%,-50%) perspective(1200px) rotateX(${(1 - p) * 26}deg) translateY(${(1 - p) * 80}px)`,
        opacity: Math.min(1, p * 1.5) * gone, borderRadius: 40, padding: '46px 52px', background: 'linear-gradient(160deg, #222B3D, #0E1422)',
        boxShadow: '0 40px 80px rgba(10,16,30,0.45), inset 0 1px 0 rgba(255,255,255,0.14)'}}>
        <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 26, letterSpacing: '0.2em', color: acc, marginBottom: 16}}>{kicker}</div>
        <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 54, lineHeight: 1.16, color: '#fff'}}>{rich(text, acc)}</div>
      </div>
    </>;
  }

  return <AbsoluteFill style={{opacity: exit(frame, fps, duration, back ? 0.01 : 0.3)}}>
    <AbsoluteFill style={{background: C.bg}} />
    {bg === 'paper' ? <AbsoluteFill style={{opacity: 0.35, backgroundImage: 'radial-gradient(rgba(60,45,20,0.10) 1px, transparent 1px)', backgroundSize: '22px 22px'}} /> : null}
    {titleEl}
    {body}
    {src ? <>
      {keep_face && kc > 0.6 ? <div style={{position: 'absolute', left: cxs - Rs, top: cys - Rs, width: Rs * 2, height: Rs * 2, borderRadius: 9999,
        boxShadow: `0 18px 40px rgba(0,0,0,${0.35 * kc})`}} /> : null}
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0', transform: `translate(${tx}px, ${ty}px) scale(${s})`,
        clipPath: `circle(${Rl}px at ${fx}px ${fy}px)`, WebkitClipPath: `circle(${Rl}px at ${fx}px ${fy}px)`}}>
        {isVid(src) ? <OffthreadVideo src={url(src)} muted style={{width: W, height: H, objectFit: 'cover'}} />
          : <Img src={url(src)} style={{width: W, height: H, objectFit: 'cover'}} />}
      </div>
      {keep_face && kc > 0.6 ? <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        <circle cx={cxs} cy={cys} r={Rs} fill="none" stroke="#fff" strokeWidth={6} opacity={(kc - 0.6) / 0.4} />
        <circle cx={cxs} cy={cys} r={Rs + 9} fill="none" stroke={acc} strokeWidth={3} opacity={k} strokeDasharray={`${Rs * 0.9} ${Rs * 0.35}`}
          transform={`rotate(${t * 40} ${cxs} ${cys})`} />
      </svg> : null}
    </> : null}
  </AbsoluteFill>;
};

/**
 * WordStack — word-by-word kinetic captions as a typographic LOCKUP (the look of the top talking-head editors, made ours):
 * small words in a hairline geometric face (light, big), the key phrase heavy + slanted with a gradient fill, lines kissing
 * each other and staggered (lead words hang left, tail words hang right), each word flying in on its syllable with motion
 * blur and a tracking squeeze, leaving with a blur lift. One overlay = one phrase; the builder makes them from the transcript.
 * Props: words [{w, t (s from overlay start), k (1 = key)}], x 0.5, y 0.5 (vertical centre of the lockup), key_size 170,
 * grad [c1, c2] (key fill), ink '#fff', max_w 0.88 (of the frame width), tilt -9 (° slant of the key), font 'GEO'.
 */
export const WordStack: React.FC<P> = ({duration, words = [], x = 0.5, y = 0.5, key_size = 170, grad = ['#FFE08A', '#FF8A1F'], ink = '#FFFFFF',
  max_w = 0.88, tilt = -9, font = 'GEO', accent}) => {
  const {frame, fps, t, W, H} = useT();
  const g = accent ? [accent, accent] : grad;
  const F = `${font}, BVP, sans-serif`;
  words = words.map((q: any) => ({...q, w: String(q.w).normalize('NFC')})); // transcripts can be NFD: decomposed marks drop out in many fonts
  const ki = words.findIndex((q: any) => q.k), has = ki >= 0;
  const pre = has ? words.slice(0, ki) : words, key = has ? words.filter((q: any) => q.k) : [], post = has ? words.slice(ki + key.length) : [];
  const ktxt = key.map((q: any) => q.w).join(' ');
  const K = Math.min(key_size, (W * max_w) / Math.max(1, ktxt.length * 0.6));     // fit the key line to the frame
  const preS = Math.min(K * 0.6, (W * max_w) / Math.max(1, pre.map((q: any) => q.w).join(' ').length * 0.5));
  const postS = Math.min(K * 0.42, (W * max_w) / Math.max(1, post.map((q: any) => q.w).join(' ').length * 0.5));
  const out = lerp(t, duration - 0.18, duration, 0, 1);
  const shadow = '0 6px 26px rgba(0,0,0,0.42), 0 1px 3px rgba(0,0,0,0.35)';
  const enter = (st: number, dir: number, heavy: boolean) => {
    const p = lerp(t, st - 0.02, st + (heavy ? 0.26 : 0.2), 0, 1, (q) => 1 - Math.pow(1 - q, 3));
    const b = (1 - p) * (heavy ? 16 : 12) + out * 10;
    return {p, style: {opacity: Math.min(1, p * 1.8) * (1 - out), filter: `blur(${b.toFixed(2)}px)`,
      transform: `translate(${(1 - p) * dir * 70}px, ${(1 - p) * (heavy ? 40 : 0) - out * 30}px)`} as React.CSSProperties};
  };
  const small = (list: any[], size: number, dir: number) => list.map((wd: any, i: number) => {
    const e = enter(wd.t ?? 0, dir, false);
    return <span key={i} style={{display: 'inline-block', whiteSpace: 'pre', fontFamily: F, fontWeight: 300, fontSize: size, lineHeight: 1, color: ink,
      letterSpacing: `${0.02 + (1 - e.p) * 0.12}em`, textShadow: shadow, marginRight: i < list.length - 1 ? size * 0.22 : 0, ...e.style}}>{wd.w}</span>;
  });
  return <AbsoluteFill>
    <div style={{position: 'absolute', left: x * W, top: y * H, transform: 'translate(-50%, -50%)', display: 'flex', flexDirection: 'column', alignItems: 'stretch'}}>
      {pre.length ? <div style={{display: 'flex', justifyContent: has ? 'flex-start' : 'center', paddingLeft: has ? K * 0.08 : 0, marginBottom: has ? -K * 0.12 : 0,
        position: 'relative', zIndex: 1}}>{small(pre, has ? preS : K * 0.62, -1)}</div> : null}
      {has ? <div style={{display: 'flex', justifyContent: 'center', position: 'relative', zIndex: 2}}>
        {key.map((wd: any, i: number) => {
          const e = enter(wd.t ?? 0, 0, true);
          const sw = lerp(t, (wd.t ?? 0) + 0.15, (wd.t ?? 0) + 0.75, -0.3, 1.3);
          return <span key={i} style={{display: 'inline-block', whiteSpace: 'pre', fontFamily: F, fontWeight: 700, fontSize: K, lineHeight: 0.92,
            letterSpacing: `${-0.03 + (1 - e.p) * 0.18}em`, padding: `${K * 0.16}px ${K * 0.06}px ${K * 0.22}px`, margin: `${-K * 0.16}px 0 ${-K * 0.22}px`,
            marginRight: i < key.length - 1 ? K * 0.12 : 0, // padded so the gradient (background-clip) also covers stacked marks above and the dot below (ộ, ệ, ặ)
            backgroundImage: `linear-gradient(100deg, rgba(255,255,255,0) ${sw * 100 - 14}%, rgba(255,255,255,0.85) ${sw * 100}%, rgba(255,255,255,0) ${sw * 100 + 14}%), linear-gradient(180deg, ${g[0]}, ${g[1]})`,
            WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', WebkitTextFillColor: 'transparent',
            ...e.style, transform: `${e.style.transform} skewX(${tilt}deg) scale(${1.18 - 0.18 * e.p})`,
            filter: `${e.style.filter} drop-shadow(0 8px 22px rgba(0,0,0,0.38))`}}>{wd.w}</span>;
        })}
      </div> : null}
      {post.length ? <div style={{display: 'flex', justifyContent: 'flex-end', paddingRight: K * 0.06, marginTop: -K * 0.08, position: 'relative', zIndex: 3}}>
        {small(post, postS, 1)}</div> : null}
    </div>
  </AbsoluteFill>;
};

export const NARRATE_COMPS: Record<string, React.FC<any>> = {ExplainCanvas, WordStack};
