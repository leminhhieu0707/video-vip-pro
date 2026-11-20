// PRO pack — creator-trend effects: 3D photo orbit, cover-flow carousel, bar-chart race, line graph, exploded stack,
// device splay, constellation hub, headline wall (behind the speaker), doodle stickers. Colours via T() (theme).
import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {Rich} from './Rich';
import {C, EASE_IN, EASE_OUT, enter, exit, SANS, SERIF, SHADOW_CARD, SHADOW_TEXT, T} from './theme';
import {At, CL, lerp, P, Photo, pop, useT} from './Vip';

const easeInOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const tag = (label: string, size = 26) => (
  <div style={{display: 'inline-block', padding: `${size * 0.25}px ${size * 0.7}px`, borderRadius: 999, background: T('rgba(14,21,48,0.78)'),
    color: T('#fff'), fontFamily: SANS, fontWeight: 700, fontSize: size, letterSpacing: '0.02em', whiteSpace: 'nowrap', border: T('1px solid rgba(255,255,255,0.25)')}}>{label}</div>
);

/** OrbitCarousel: photos ride a tilted 3D ring around the speaker's head (back half goes behind — ring comp). */
export const OrbitCarousel: React.FC<P> = ({duration, items = [], x = 0.5, y = 0.3, rx = 0.42, ry = 0.1, size = 230, speed = 0.18, half = 'front', label}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0, 0.5);
  const list: string[] = items.length ? items : ['', '', '', '', '', ''];
  const N = Math.max(4, list.length);
  const spin = t * speed * Math.PI * 2 + lerp(t, 0, 0.8, -1.2, 0, EASE_IN);
  return <AbsoluteFill style={{opacity: o}}>
    {Array.from({length: N}).map((_, i) => {
      const a = (i / N) * Math.PI * 2 + spin;
      const depth = Math.sin(a); // >0 front
      const back = depth < 0;
      if ((half === 'back') !== back && half !== 'all') return null;
      const sc = 0.62 + 0.38 * (depth + 1) / 2;
      const px = (x + Math.cos(a) * rx) * W, py = (y + depth * ry) * H;
      return <div key={i} style={{position: 'absolute', left: px, top: py, width: size, height: size * 1.25, transform: `translate(-50%,-50%) scale(${sc}) rotateY(${Math.cos(a) * -35}deg)`,
        borderRadius: 14, overflow: 'hidden', boxShadow: SHADOW_CARD, border: T('3px solid rgba(255,255,255,0.95)'), opacity: back ? 0.75 : 1, zIndex: Math.round(sc * 100)}}>
        <Photo s={list[i % list.length]} />
      </div>;
    })}
    {label && half !== 'back' ? <At x={0.5} y={0.08}>{tag(label)}</At> : null}
  </AbsoluteFill>;
};

/** VisionCarousel: big cards in cover-flow; the centre card changes every `step` s with a fast-slow ease. */
export const VisionCarousel: React.FC<P> = ({duration, items = [], y = 0.3, w = 0.5, h = 0.32, step = 1.1, label}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0, 0.35);
  const list: string[] = items.length ? items : ['', '', '', ''];
  const k = Math.floor(t / step), f = easeInOut(Math.min(1, (t % step) / (step * 0.45)));
  const pos = k + f;
  return <AbsoluteFill style={{opacity: o, perspective: 1600}}>
    {list.map((s0, i) => {
      const d = i - (pos % list.length);
      const dd = ((d + list.length * 1.5) % list.length) - list.length / 2;
      if (Math.abs(dd) > 2.2) return null;
      const sc = 1 - Math.min(1, Math.abs(dd)) * 0.22;
      return <div key={i} style={{position: 'absolute', left: (0.5 + dd * 0.36) * W, top: y * H, width: w * W, height: h * H,
        transform: `translate(-50%,-50%) rotateY(${-dd * 38}deg) scale(${sc})`, borderRadius: 26, overflow: 'hidden', boxShadow: SHADOW_CARD,
        border: T('3px solid rgba(255,255,255,0.9)'), zIndex: 100 - Math.round(Math.abs(dd) * 10), filter: `brightness(${1 - Math.min(0.45, Math.abs(dd) * 0.3)})`}}>
        <Photo s={s0} />
      </div>;
    })}
    {label ? <At x={0.5} y={Math.max(0.05, y - h / 2 - 0.035)}>{tag(label)}</At> : null}
  </AbsoluteFill>;
};

/** BarChartRace: frames [{label: "Tháng 2", bars: [{label, v}]}] — bars grow and swap ranks between frames. */
export const BarChartRace: React.FC<P> = ({duration, frames = [], title, unit = '', x = 0.5, y = 0.2, w = 0.84, at = 0.2}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0, 0.35);
  const F = frames.length ? frames : [{label: '', bars: [{label: 'A', v: 1}]}];
  const span = Math.max(0.5, duration - at - 0.6) / Math.max(1, F.length - 1);
  const p = Math.max(0, (t - at) / span), i0 = Math.min(F.length - 1, Math.floor(p)), i1 = Math.min(F.length - 1, i0 + 1);
  const f = easeInOut(Math.min(1, p - i0));
  const names: string[] = Array.from(new Set(F.flatMap((fr: any) => fr.bars.map((b: any) => b.label))));
  const val = (fr: any, n: string) => Number(fr.bars.find((b: any) => b.label === n)?.v ?? 0);
  const cur = names.map((n) => ({n, v: val(F[i0], n) + (val(F[i1], n) - val(F[i0], n)) * f}));
  const grow = lerp(t, at, at + 0.7, 0, 1, EASE_IN);
  const max = Math.max(...cur.map((c) => c.v), 1);
  const ranked = [...cur].sort((a, b) => b.v - a.v);
  const rowH = 58, bw = w * W * 0.5;
  return <At x={x} y={y} style={{opacity: o}} anchor="-50%, 0">
    <div style={{width: w * W, background: T('rgba(255,255,255,0.96)'), borderRadius: 26, padding: '26px 30px', boxShadow: SHADOW_CARD, fontFamily: SANS}}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14}}>
        <div style={{fontWeight: 800, fontSize: 30, color: C.ink}}>{title}</div>
        <div style={{fontWeight: 800, fontSize: 40, color: C.blue}}>{F[f > 0.5 ? i1 : i0].label}</div>
      </div>
      <div style={{position: 'relative', height: rowH * names.length}}>
        {cur.map((c) => {
          const r = ranked.findIndex((q) => q.n === c.n);
          return <div key={c.n} style={{position: 'absolute', left: 0, top: r * rowH, display: 'flex', alignItems: 'center', gap: 14, transition: 'none', width: '100%'}}>
            <div style={{width: 190, textAlign: 'right', fontWeight: 700, fontSize: 22, whiteSpace: 'nowrap', color: T('#5B6584')}}>{c.n}</div>
            <div style={{height: rowH * 0.62, width: Math.max(6, (c.v / max) * bw * grow), borderRadius: 8,
              background: r === 0 ? T('linear-gradient(90deg,#3158FF,#8EB3FF)') : T('#0E1530')}} />
            <div style={{fontWeight: 800, fontSize: 24, color: C.ink}}>{Math.round(c.v).toLocaleString('vi-VN')}{unit}</div>
          </div>;
        })}
      </div>
    </div>
  </At>;
};

/** LineGraph: series [{points: [..], label}] over labels [..]; the line draws on, values pop at each point. */
export const LineGraph: React.FC<P> = ({duration, series = [], labels = [], title, x = 0.5, y = 0.2, w = 0.84, h = 0.22, at = 0.2, dur = 1.6}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0, 0.35);
  const S = series.length ? series : [{points: [3, 5, 4, 8, 12]}];
  const n = Math.max(...S.map((s: any) => s.points.length));
  const all = S.flatMap((s: any) => s.points.map(Number));
  const lo = Math.min(...all), hi = Math.max(...all, lo + 1);
  const cw = w * W - 160, ch = h * H - 70;
  const g = lerp(t, at, at + dur, 0, 1, EASE_OUT);
  const colors = [T('#3158FF'), T('#E5303C'), T('#19B46B')];
  const px = (i: number) => 80 + (i / Math.max(1, n - 1)) * cw, py = (v: number) => 62 + (ch - 34) - ((v - lo) / (hi - lo)) * (ch - 34);
  return <At x={x} y={y} style={{opacity: o}} anchor="-50%, 0">
    <div style={{width: w * W, height: h * H + 50, background: T('rgba(255,255,255,0.96)'), borderRadius: 26, boxShadow: SHADOW_CARD, position: 'relative', fontFamily: SANS}}>
      {title ? <div style={{position: 'absolute', left: 30, top: 18, fontWeight: 800, fontSize: 28, color: C.ink}}>{title}</div> : null}
      <svg width={w * W} height={h * H + 50} style={{position: 'absolute', left: 0, top: 30}}>
        {S.map((s: any, si: number) => {
          const d = s.points.map((v: number, i: number) => `${i ? 'L' : 'M'} ${px(i)} ${py(v)}`).join(' ');
          return <g key={si}>
            <path d={d} fill="none" stroke={colors[si % 3]} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" pathLength={1}
              strokeDasharray="1" strokeDashoffset={1 - g} />
            {s.points.map((v: number, i: number) => {
              const show = g >= i / Math.max(1, n - 1) - 0.01;
              return show ? <g key={i}><circle cx={px(i)} cy={py(v)} r={9} fill={T('#fff')} stroke={colors[si % 3]} strokeWidth={5} />
                <text x={px(i)} y={py(v) - 20} textAnchor="middle" fontFamily={SANS} fontWeight={800} fontSize={26} fill={C.ink}>{v}</text></g> : null;
            })}
          </g>;
        })}
        {labels.map((l: string, i: number) => <text key={i} x={px(i)} y={ch + 62} textAnchor="middle" fontFamily={SANS} fontWeight={600} fontSize={22} fill={T('#6B7699')}>{l}</text>)}
      </svg>
    </div>
  </At>;
};

/** ExplodedStack: a tilted screen splits into 3D layers with callouts, then merges back. */
export const ExplodedStack: React.FC<P> = ({duration, src: s0, layers = 3, labels = [], x = 0.36, y = 0.22, w = 0.34}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0, 0.35);
  const open = lerp(t, 0.35, 0.95, 0, 1, EASE_IN) * (1 - lerp(t, duration - 0.9, duration - 0.35, 0, 1, EASE_OUT));
  const pw = w * W, ph = pw * 1.9;
  return <At x={x} y={y} style={{opacity: o, perspective: 1800}}>
    <div style={{position: 'relative', width: pw, height: ph, transform: 'rotateX(52deg) rotateZ(-32deg)', transformStyle: 'preserve-3d'}}>
      {Array.from({length: layers}).map((_, i) => {
        const z = (i - (layers - 1) / 2) * 120 * open;
        return <div key={i} style={{position: 'absolute', inset: 0, borderRadius: pw * 0.12, overflow: 'hidden', transform: `translateZ(${z}px)`,
          border: T(`${i === layers - 1 ? 10 : 3}px solid ${i === layers - 1 ? '#121420' : 'rgba(255,255,255,0.8)'}`), boxShadow: SHADOW_CARD,
          background: i === layers - 1 ? 'transparent' : T(`rgba(${i ? '140,175,255' : '255,255,255'},${0.25 + i * 0.15})`)}}>
          {i === 0 ? <Photo s={s0} /> : null}
        </div>;
      })}
    </div>
    {labels.slice(0, layers).map((l: string, i: number) => (
      <div key={i} style={{position: 'absolute', left: pw * 0.95, top: ph * (0.05 + i * 0.22), opacity: open, transform: `translateX(${(1 - open) * -30}px)`}}>
        {tag(l, 24)}
      </div>
    ))}
  </At>;
};

/** DeviceSplay: phone, tablet and laptop pop out one after another, all showing the same screenshot. */
export const DeviceSplay: React.FC<P> = ({duration, src: s0, y = 0.2, size = 1, label}) => {
  const {frame, fps, W} = useT();
  const o = exit(frame, fps, duration);
  const dev = [
    {k: 'phone', w: 0.19, h: 0.4, x: 0.2, at: 0.0, r: 0.16},
    {k: 'tablet', w: 0.3, h: 0.4, x: 0.47, at: 0.3, r: 0.07},
    {k: 'laptop', w: 0.42, h: 0.27, x: 0.78, at: 0.6, r: 0.03},
  ];
  return <AbsoluteFill style={{opacity: o}}>
    {dev.map((d) => {
      const s = pop(frame, fps, d.at, 13);
      const pw = d.w * W * size, ph = d.h * pw / d.w * 0.55;
      return <At key={d.k} x={d.x} y={y} style={{transform: `translate(-50%,-50%) scale(${s}) rotate(${(1 - s) * -8}deg)`}}>
        <div style={{width: pw, height: ph, borderRadius: pw * d.r, border: `${pw * 0.035}px solid ${T('#121420')}`, overflow: 'hidden', boxShadow: SHADOW_CARD, background: T('#fff')}}>
          <Photo s={s0} />
        </div>
        {d.k === 'laptop' ? <div style={{width: pw * 1.12, height: pw * 0.04, marginLeft: -pw * 0.06, borderRadius: '0 0 18px 18px', background: T('#C3CAE0')}} /> : null}
      </At>;
    })}
    {label ? <At x={0.5} y={Math.max(0.05, y - 0.15)}>{tag(label)}</At> : null}
  </AbsoluteFill>;
};

/** ConstellationHub: centre node, branches draw outwards; each item lights up at its `at` (seconds). */
export const ConstellationHub: React.FC<P> = ({duration, center = 'Ý chính', items = [], x = 0.5, y = 0.2, r = 0.3, size = 30}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0, 0.35);
  const list = items.length ? items : [{t: 'A'}, {t: 'B'}, {t: 'C'}, {t: 'D'}];
  const cx = x * W, cy = y * H;
  return <AbsoluteFill style={{opacity: o}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      {list.map((it: any, i: number) => {
        const a = -Math.PI / 2 + (i / list.length) * Math.PI * 2 + 0.35;
        const nx = cx + Math.cos(a) * r * W, ny = cy + Math.sin(a) * r * W * 0.55;
        const g = lerp(t, 0.2 + i * 0.12, 0.6 + i * 0.12, 0, 1, EASE_OUT);
        return <line key={i} x1={cx} y1={cy} x2={cx + (nx - cx) * g} y2={cy + (ny - cy) * g} stroke={T('rgba(255,255,255,0.7)')} strokeWidth={3} />;
      })}
    </svg>
    <At x={x} y={y} style={{transform: `translate(-50%,-50%) scale(${pop(frame, fps, 0, 14)})`}}>
      <div style={{padding: `${size * 0.5}px ${size}px`, borderRadius: 18, background: T('linear-gradient(135deg,#3158FF,#4C6FFF)'), color: T('#fff'),
        fontFamily: SANS, fontWeight: 800, fontSize: size * 1.15, boxShadow: T('0 0 40px rgba(60,100,255,0.6)')}}>{center}</div>
    </At>
    {list.map((it: any, i: number) => {
      const a = -Math.PI / 2 + (i / list.length) * Math.PI * 2 + 0.35;
      const lit = t >= (it.at ?? 0.6 + i * 0.6);
      const s = lerp(t, 0.4 + i * 0.12, 0.8 + i * 0.12, 0, 1, EASE_IN);
      return <At key={i} x={x + Math.cos(a) * r} y={y + (Math.sin(a) * r * W * 0.55) / H} style={{transform: `translate(-50%,-50%) scale(${0.6 + 0.4 * s})`, opacity: s}}>
        <div style={{padding: `${size * 0.35}px ${size * 0.7}px`, borderRadius: 14, fontFamily: SANS, fontWeight: 700, fontSize: size,
          background: lit ? T('#fff') : T('rgba(14,21,48,0.72)'), color: lit ? C.ink : T('rgba(255,255,255,0.75)'),
          boxShadow: lit ? T('0 0 34px rgba(140,175,255,0.9)') : 'none', border: T('1.5px solid rgba(255,255,255,0.35)')}}>{it.t}</div>
      </At>;
    })}
  </AbsoluteFill>;
};

/** HeadlineWall: rows of headline pills sliding sideways, filling the frame (use with "behind": true). */
export const HeadlineWall: React.FC<P> = ({duration, items = [], rows = 7, size = 44, bg = true}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0, 0.3);
  const list: string[] = items.length ? items : ['TIN NÓNG', 'XU HƯỚNG', 'MỚI NHẤT'];
  return <AbsoluteFill style={{opacity: o, background: bg ? T('linear-gradient(180deg,#F3EEE2,#E8EEFF)') : 'transparent', overflow: 'hidden'}}>
    {Array.from({length: rows}).map((_, r) => {
      const dir = r % 2 ? 1 : -1;
      const shift = (t * 90 * dir + r * 140) % (W * 0.8);
      const inAt = r * 0.06;
      const k = lerp(t, inAt, inAt + 0.45, 0, 1, EASE_IN);
      return <div key={r} style={{position: 'absolute', top: (r + 0.4) * (H / rows), left: shift - W * 0.4, display: 'flex', gap: 22,
        whiteSpace: 'nowrap', transform: `translateX(${(1 - k) * dir * -W}px)`}}>
        {Array.from({length: 6}).map((__, j) => {
          const txt = list[(r * 3 + j) % list.length];
          const dark = (r + j) % 3 === 0;
          return <div key={j} style={{padding: `${size * 0.3}px ${size * 0.55}px`, borderRadius: 12, fontFamily: SANS, fontWeight: 800, fontSize: size,
            background: dark ? C.blue : T('#fff'), color: dark ? T('#fff') : C.ink, border: T(`3px solid ${dark ? '#3158FF' : '#0E1530'}`),
            boxShadow: T('6px 6px 0 rgba(14,21,48,0.85)')}}>
            <span style={{fontSize: size * 0.42, opacity: 0.7, marginRight: 10}}>MỚI · 0{(r + j) % 9 + 1}</span>{txt}
          </div>;
        })}
      </div>;
    })}
  </AbsoluteFill>;
};

/** DoodleStickers: hand-drawn crowns, stars, hearts, arrows and a word around the head, lines "boiling" every 3 frames.
 *  Pair with an {"type": "outline"} layer for the drawn line around the person. */
export const DoodleStickers: React.FC<P> = ({duration, x = 0.5, y = 0.28, word = 'WOW!', color = T('#FFD84D'), accent = T('#FF7EB3')}) => {
  const {frame, fps, W, H} = useT();
  const o = exit(frame, fps, duration);
  const seed = Math.floor(frame / 3);
  const j = (k: number) => Math.sin(seed * 12.9898 + k * 78.233) * 2.2;
  const ink = T('#0E1530');
  const items = [
    {k: 'crown', dx: 0, dy: -0.13, at: 0.0, s: 1.15},
    {k: 'star', dx: -0.22, dy: -0.05, at: 0.12, s: 0.8},
    {k: 'star', dx: 0.24, dy: -0.07, at: 0.2, s: 0.65},
    {k: 'heart', dx: -0.28, dy: 0.1, at: 0.28, s: 0.9},
    {k: 'heart', dx: 0.27, dy: 0.13, at: 0.36, s: 0.75},
    {k: 'word', dx: 0.22, dy: -0.15, at: 0.45, s: 1},
    {k: 'arrow', dx: -0.22, dy: -0.16, at: 0.5, s: 1},
  ];
  const shape = (k: string, s: number, i: number) => {
    const sw = 7;
    if (k === 'crown') return <svg width={190 * s} height={120 * s} viewBox="0 0 190 120"><path d={`M15 105 L${25 + j(i)} 30 L60 70 L95 ${12 + j(i + 1)} L130 70 L165 30 L175 105 Z`} fill={color} stroke={ink} strokeWidth={sw} strokeLinejoin="round" /></svg>;
    if (k === 'star') return <svg width={90 * s} height={90 * s} viewBox="0 0 90 90"><path d={`M45 ${6 + j(i)} L56 34 L86 36 L62 55 L71 84 L45 67 L19 84 L28 55 L4 36 L34 34 Z`} fill={T('#8EB3FF')} stroke={ink} strokeWidth={sw} strokeLinejoin="round" /></svg>;
    if (k === 'heart') return <svg width={90 * s} height={80 * s} viewBox="0 0 90 80"><path d={`M45 75 C${10 + j(i)} 50 4 30 18 14 C30 2 42 8 45 20 C48 8 60 2 72 14 C86 30 ${80 + j(i)} 50 45 75 Z`} fill={accent} stroke={ink} strokeWidth={sw} strokeLinejoin="round" /></svg>;
    if (k === 'arrow') return <svg width={140 * s} height={80 * s} viewBox="0 0 140 80"><path d={`M10 60 Q ${60 + j(i)} 10 120 30 M120 30 L100 18 M120 30 L104 46`} fill="none" stroke={ink} strokeWidth={sw} strokeLinecap="round" /></svg>;
    return <div style={{fontFamily: SERIF, fontStyle: 'italic', fontWeight: 900, fontSize: 70 * s, color: T('#fff'), WebkitTextStroke: `3px ${ink}`, transform: `rotate(${-10 + j(i)}deg)`}}>{word}</div>;
  };
  return <AbsoluteFill style={{opacity: o}}>
    {items.map((it, i) => {
      const s = pop(frame, fps, it.at, 10);
      return <At key={i} x={x + it.dx} y={y + it.dy} style={{transform: `translate(-50%,-50%) scale(${s}) rotate(${j(i * 3)}deg)`}}>{shape(it.k, it.s, i)}</At>;
    })}
  </AbsoluteFill>;
};

export const PRO_COMPS: Record<string, React.FC<any>> = {
  OrbitCarousel, VisionCarousel, BarChartRace, LineGraph, ExplodedStack, DeviceSplay, ConstellationHub, HeadlineWall, DoodleStickers,
};
