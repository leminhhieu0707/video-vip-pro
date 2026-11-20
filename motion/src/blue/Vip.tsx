// VIP pack — ~45 extra motion comps (stamps, kinetic text, UI mockups, stills, rings, transitions). Colours come from theme.ts.
// Every comp: duration (s) + its own props; positions are 0–1 fractions of the frame. Transparent unless noted
// "full-screen". Times inside props (at, clickAt, …) are seconds from the overlay start.
import React from 'react';
import {AbsoluteFill, Img, interpolate, random, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Rich} from './Rich';
import {C, EASE_IN, EASE_OUT, enter, exit, GRAD, gradText, SANS, SERIF, SHADOW_CARD, SHADOW_TEXT, T} from './theme';

const MONO = 'Consolas, "Cascadia Mono", "Courier New", monospace';
export const CL = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const isFile = (s?: string) => !!s && /\.(png|jpe?g|webp|svg|gif)$/i.test(s);
export const src = (s: string) => (s.startsWith('http') ? s : staticFile(s));

export function useT() {
  const frame = useCurrentFrame();
  const {fps, width: W, height: H} = useVideoConfig();
  return {frame, fps, W, H, t: frame / fps};
}
export const lerp = (t: number, a: number, b: number, from = 0, to = 1, ease = EASE_IN) =>
  interpolate(t, [a, b], [from, to], {...CL, easing: ease});
export const pop = (frame: number, fps: number, at: number, damping = 12) =>
  spring({frame: frame - at * fps, fps, config: {damping, stiffness: 190, mass: 0.6}});

export type P = {duration: number; [k: string]: any};

export const Glass: React.FC<{style?: React.CSSProperties; children?: React.ReactNode; dark?: boolean}> = ({style, children, dark}) => (
  <div style={{background: dark ? T('linear-gradient(160deg, rgba(20,34,90,0.92), rgba(11,22,64,0.92))') : T('linear-gradient(160deg,#FFFFFF,#EEF2FF)'),
    border: dark ? T('1.5px solid rgba(140,170,255,0.35)') : T('2px solid rgba(255,255,255,0.95)'), boxShadow: SHADOW_CARD,
    borderRadius: 28, color: dark ? T('#fff') : C.ink, fontFamily: SANS, ...style}}>{children}</div>
);
export const At: React.FC<{x: number; y: number; children: React.ReactNode; style?: React.CSSProperties; anchor?: string}> =
  ({x, y, children, style, anchor = '-50%, -50%'}) => {
    const {W, H} = useT();
    return <div style={{position: 'absolute', left: x * W, top: y * H, transform: `translate(${anchor})`, ...style}}>{children}</div>;
  };
const Icon: React.FC<{v: string; size: number}> = ({v, size}) => isFile(v)
  ? <Img src={src(v)} style={{width: size, height: size, objectFit: 'contain'}} />
  : <span style={{fontSize: size * 0.86, lineHeight: 1}}>{v}</span>;
export const Photo: React.FC<{s?: string; style?: React.CSSProperties}> = ({s, style}) => s
  ? <Img src={src(s)} style={{width: '100%', height: '100%', objectFit: 'cover', ...style}} />
  : <div style={{width: '100%', height: '100%', background: T('linear-gradient(160deg,#c9d6ff,#8ea6ff)'), ...style}} />;

// ================================================================ captions / titles
/** Stamp: rubber stamp text slams in (scale 2.2 → 1, slight shake). */
export const Stamp: React.FC<P> = ({duration, text = 'ĐÓNG DẤU', x = 0.5, y = 0.12, size = 110, color = T('#E5303C'), rotate = -7, at = 0}) => {
  const {frame, fps, t} = useT();
  const p = lerp(t, at, at + 0.16, 0, 1, EASE_OUT);
  const shake = t > at + 0.16 && t < at + 0.36 ? Math.sin(t * 120) * 6 * (1 - (t - at - 0.16) / 0.2) : 0;
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} style={{opacity: p * o, transform: `translate(-50%,-50%) translateX(${shake}px) rotate(${rotate}deg) scale(${2.2 - 1.2 * p})`}}>
    <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size, color, border: `${size * 0.07}px solid ${color}`, borderRadius: size * 0.14,
      padding: `${size * 0.02}px ${size * 0.22}px`, letterSpacing: '0.02em', whiteSpace: 'nowrap', mixBlendMode: 'multiply',
      maskImage: T('radial-gradient(circle at 30% 40%, #000 55%, rgba(0,0,0,0.75) 70%, #000 85%)')}}>{text}</div>
  </At>;
};

/** KineticTitle: big steps one after another; each finished step shrinks into the small line above. */
export const KineticTitle: React.FC<P> = ({duration, steps = [], x = 0.08, y = 0.1, size = 120}) => {
  const {frame, fps, t} = useT();
  const o = exit(frame, fps, duration);
  const list: Array<{text: string; at: number}> = steps.map((s: any, i: number) => (typeof s === 'string' ? {text: s, at: i * 0.7} : s));
  const cur = Math.max(0, list.filter((s) => t >= s.at).length - 1);
  const done = list.slice(0, cur).map((s) => s.text.replace(/[*_=[\]{}~]/g, '')).join(' ');
  return <At x={x} y={y} anchor="0,0" style={{opacity: o, width: '84%'}}>
    {done ? <div style={{fontFamily: SANS, fontWeight: 600, fontSize: size * 0.32, color: T('#fff'), textShadow: SHADOW_TEXT, marginBottom: size * 0.1}}>{done}</div> : null}
    {list[cur] ? <Rich key={cur} text={list[cur].text} size={size} at={list[cur].at} total={duration} align="left" stagger={0.06} /> : null}
  </At>;
};

/** GravityText: words drop from above, bounce and settle tilted (chữ rơi có trọng lực). */
export const GravityText: React.FC<P> = ({duration, words = [], x = 0.5, y = 0.5, size = 110, at = 0, gap = 0.12, color = T('#fff')}) => {
  const {frame, fps, H} = useT();
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} style={{opacity: o, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', width: '86%', gap: size * 0.15}}>
    {words.map((w: string, i: number) => {
      const s = spring({frame: frame - (at + i * gap) * fps, fps, config: {damping: 9, stiffness: 120, mass: 0.9}});
      const rot = (random(`r${i}${w}`) - 0.5) * 22;
      return <span key={i} style={{display: 'inline-block', fontFamily: SANS, fontWeight: 800, fontSize: size, color, textShadow: SHADOW_TEXT,
        letterSpacing: '-0.04em', transform: `translateY(${(1 - s) * -H * 0.7}px) rotate(${rot * s}deg)`}}>{w}</span>;
    })}
  </At>;
};

/** GiantCaption: one or two words filling the width, punch-scales in. */
export const GiantCaption: React.FC<P> = ({duration, text = '', top, y = 0.62, size = 230, at = 0}) => {
  const {frame, fps} = useT();
  const s = pop(frame, fps, at, 11);
  const o = exit(frame, fps, duration);
  return <At x={0.5} y={y} style={{opacity: Math.min(1, s * 2) * o, textAlign: 'center', width: '98%'}}>
    {top ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: size * 0.24, color: T('#fff'), textShadow: SHADOW_TEXT}}>{top}</div> : null}
    <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size, lineHeight: 0.95, letterSpacing: '-0.05em', transform: `scale(${1.5 - 0.5 * s})`,
      ...gradText(T('linear-gradient(180deg,#FFFFFF 35%,#B8CCFF 100%)')), filter: T('drop-shadow(0 6px 22px rgba(0,0,0,0.5)) drop-shadow(0 0 30px rgba(60,100,255,0.55))')}}>{text}</div>
  </At>;
};

/** SplitFlap: airport departure board letters flipping into place. */
export const SplitFlap: React.FC<P> = ({duration, text = 'SÂN BAY', x = 0.5, y = 0.1, size = 92, at = 0}) => {
  const {frame, fps, t} = useT();
  const o = exit(frame, fps, duration);
  const A = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  return <At x={x} y={y} style={{opacity: o, display: 'flex', gap: size * 0.08}}>
    {[...text].map((ch, i) => {
      const lock = at + 0.25 + i * 0.07;
      const flipping = t < lock;
      const c = ch === ' ' ? ' ' : flipping ? A[Math.floor(random(`f${i}${Math.floor(t * 18)}`) * A.length)] : ch;
      const ph = (t * 18) % 1;
      return <div key={i} style={{width: size * 0.78, height: size * 1.1, borderRadius: size * 0.1, position: 'relative', overflow: 'hidden',
        background: ch === ' ' ? 'transparent' : T('linear-gradient(180deg,#1b2350 0 49%,#0c1336 51% 100%)'), boxShadow: ch === ' ' ? 'none' : SHADOW_CARD,
        display: 'grid', placeItems: 'center', fontFamily: MONO, fontWeight: 700, fontSize: size * 0.8, color: T('#F4F7FF'),
        opacity: t < at ? 0 : 1, transform: flipping && ch !== ' ' ? `scaleY(${0.75 + 0.25 * Math.cos(ph * Math.PI)})` : 'none'}}>
        {c}<div style={{position: 'absolute', left: 0, right: 0, top: '50%', height: 2, background: T('rgba(0,0,0,0.55)')}} />
      </div>;
    })}
  </At>;
};

/** Highlighter: white note card, a highlighter stroke sweeps under `mark`. */
export const Highlighter: React.FC<P> = ({duration, text = 'chỗ quan trọng thì tô', mark = 'bút dạ quang', x = 0.6, y = 0.14, size = 46, at = 0, color = T('rgba(120,160,255,0.75)')}) => {
  const {frame, fps, t} = useT();
  const p = enter(frame, fps, at);
  const m = lerp(t, at + 0.45, at + 0.95);
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} style={{opacity: p * o, transform: `translate(-50%,-50%) translateY(${(1 - p) * 20}px) rotate(-2deg)`}}>
    <Glass style={{padding: `${size * 0.5}px ${size * 0.7}px`, fontSize: size, fontWeight: 700, lineHeight: 1.35, maxWidth: 640}}>
      {text}<br />
      <span style={{backgroundImage: `linear-gradient(transparent 45%, ${color} 45%, ${color} 92%, transparent 92%)`, backgroundRepeat: 'no-repeat',
        backgroundSize: `${m * 100}% 100%`, fontWeight: 800}}>{mark}</span>
    </Glass>
  </At>;
};

/** CircleDraw: hand-drawn ellipse around something (khoanh tròn). */
export const CircleDraw: React.FC<P> = ({duration, x = 0.5, y = 0.4, w = 0.5, h = 0.2, color = T('#4C6FFF'), stroke = 10, at = 0, label}) => {
  const {frame, fps, t, W, H} = useT();
  const d = lerp(t, at, at + 0.55);
  const o = exit(frame, fps, duration);
  const rx = (w * W) / 2, ry = (h * H) / 2;
  const path = `M ${rx * 2 + 10} ${ry + 5} C ${rx * 2 + 10} ${-ry * 0.15}, ${-10} ${-ry * 0.1}, 8 ${ry} C ${20} ${ry * 2.2}, ${rx * 2 + 16} ${ry * 2.1}, ${rx * 2 - 6} ${ry * 0.55}`;
  return <At x={x} y={y} style={{opacity: o}}>
    <svg width={rx * 2 + 40} height={ry * 2 + 40} viewBox={`-10 -10 ${rx * 2 + 40} ${ry * 2 + 40}`} style={{overflow: 'visible', filter: T('drop-shadow(0 3px 8px rgba(0,0,0,0.35))')}}>
      <path d={path} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - d} />
    </svg>
    {label ? <div style={{position: 'absolute', left: '100%', top: 0, opacity: lerp(t, at + 0.5, at + 0.8), fontFamily: SANS, fontWeight: 800, fontSize: 48, color: T('#fff'), textShadow: SHADOW_TEXT, whiteSpace: 'nowrap'}}>{label}</div> : null}
  </At>;
};

// ================================================================ UI widgets
/** Cursor: arrow glides from `from` to `to`, clicks (ripple); optional chip at the target that presses. */
export const Cursor: React.FC<P> = ({duration, from = [0.8, 0.6], to = [0.5, 0.12], at = 0.1, clickAt = 0.75, label, x, y}) => {
  const {frame, fps, t, W, H} = useT();
  const m = lerp(t, at, clickAt - 0.05, 0, 1, (k) => 1 - Math.pow(1 - k, 3));
  const cx = (from[0] + (to[0] - from[0]) * m) * W, cy = (from[1] + (to[1] - from[1]) * m) * H + Math.sin(m * Math.PI) * -60;
  const press = t > clickAt && t < clickAt + 0.18;
  const rip = lerp(t, clickAt, clickAt + 0.45);
  const o = exit(frame, fps, duration);
  const lp = enter(frame, fps, 0);
  return <AbsoluteFill style={{opacity: o}}>
    {label ? <At x={x ?? to[0]} y={y ?? to[1]} style={{opacity: lp, transform: `translate(-50%,-50%) scale(${press ? 0.94 : 1})`}}>
      <Glass style={{padding: '18px 34px', fontSize: 56, fontWeight: 800, letterSpacing: '-0.02em', whiteSpace: 'nowrap',
        background: t > clickAt ? `linear-gradient(180deg,${T('#4C6FFF')},${C.blue})` : undefined, color: t > clickAt ? T('#fff') : C.ink}}>{label}</Glass>
    </At> : null}
    {rip > 0 && rip < 1 ? <div style={{position: 'absolute', left: cx - 60, top: cy - 60, width: 120, height: 120, borderRadius: '50%',
      border: T('4px solid rgba(255,255,255,0.9)'), transform: `scale(${0.3 + rip})`, opacity: 1 - rip}} /> : null}
    <svg width={64} height={78} viewBox="0 0 24 30" style={{position: 'absolute', left: cx - 8, top: cy - 4, transform: `scale(${press ? 0.85 : 1})`,
      filter: T('drop-shadow(0 4px 8px rgba(0,0,0,0.45))')}}>
      <path d="M2 2 L2 24 L8 18 L12 28 L16 26 L12 17 L20 17 Z" fill={T("#fff")} stroke={T("#0E1530")} strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  </AbsoluteFill>;
};

/** FloatButton: frosted glass button floating in the frame; pulses when tapped (pair with a zoom on the finger). */
export const FloatButton: React.FC<P> = ({duration, icon = '✳️', label, x = 0.36, y = 0.5, size = 150, tapAt = 0.6, at = 0}) => {
  const {frame, fps, t} = useT();
  const s = pop(frame, fps, at);
  const pulse = lerp(t, tapAt, tapAt + 0.6);
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} style={{opacity: Math.min(1, s * 1.5) * o, transform: `translate(-50%,-50%) scale(${(0.6 + 0.4 * s) * (t > tapAt && t < tapAt + 0.15 ? 0.9 : 1)})`, textAlign: 'center'}}>
    {label ? <Glass style={{display: 'inline-block', padding: '8px 18px', fontSize: size * 0.17, fontWeight: 700, marginBottom: 14, borderRadius: 16}}>{label}</Glass> : null}
    <div style={{position: 'relative', width: size, height: size, margin: '0 auto'}}>
      {pulse > 0 && pulse < 1 ? <div style={{position: 'absolute', inset: 0, borderRadius: '50%', border: T('4px solid rgba(140,175,255,0.9)'), transform: `scale(${1 + pulse * 0.9})`, opacity: 1 - pulse}} /> : null}
      <div style={{width: size, height: size, borderRadius: '50%', display: 'grid', placeItems: 'center', background: T('radial-gradient(circle at 35% 30%, rgba(255,255,255,0.75), rgba(160,185,255,0.45) 60%, rgba(90,120,230,0.5))'),
        border: T('2px solid rgba(255,255,255,0.8)'), boxShadow: T('0 14px 40px rgba(20,40,120,0.4), inset 0 2px 0 rgba(255,255,255,0.7)')}}><Icon v={icon} size={size * 0.5} /></div>
    </div>
  </At>;
};

/** IncomingCall: dynamic-island style call pill sliding down. */
export const IncomingCall: React.FC<P> = ({duration, name = 'Claude', sub = 'đang gọi...', initial, y = 0.06}) => {
  const {frame, fps} = useT();
  const s = pop(frame, fps, 0, 14);
  const o = exit(frame, fps, duration);
  return <At x={0.5} y={y} anchor="-50%, 0" style={{opacity: o, transform: `translate(-50%, ${(1 - s) * -140}px) scale(${0.7 + 0.3 * s}, ${0.5 + 0.5 * s})`}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 26, background: T('#05070F'), borderRadius: 80, padding: '20px 26px 20px 20px', boxShadow: SHADOW_CARD, fontFamily: SANS, width: 760}}>
      <div style={{width: 92, height: 92, borderRadius: '50%', background: GRAD, display: 'grid', placeItems: 'center', color: T('#fff'), fontWeight: 800, fontSize: 48}}>{initial || name[0]}</div>
      <div style={{flex: 1}}><div style={{color: T('#9AA3BF'), fontSize: 28, fontWeight: 600}}>{sub}</div><div style={{color: T('#fff'), fontSize: 48, fontWeight: 800}}>{name}</div></div>
      <div style={{width: 92, height: 92, borderRadius: '50%', background: T('#FF3B30'), display: 'grid', placeItems: 'center', fontSize: 44}}>📞</div>
      <div style={{width: 92, height: 92, borderRadius: '50%', background: T('#30D158'), display: 'grid', placeItems: 'center', fontSize: 44, transform: `rotate(${Math.sin(frame / 2) * 12}deg)`}}>📞</div>
    </div>
  </At>;
};

/** TypeBar: search / command bar typing `text`, ghost `suggest` completes it ("Tab" hint) or a send button. */
export const TypeBar: React.FC<P> = ({duration, text = 'gõ phím', suggest = ' gợi ý', mode = 'search', label, x = 0.5, y = 0.1, w = 0.84, at = 0, cps = 14}) => {
  const {frame, fps, t, W} = useT();
  const p = enter(frame, fps, at);
  const o = exit(frame, fps, duration);
  const n = Math.max(0, Math.floor((t - at - 0.25) * cps));
  const typed = text.slice(0, n);
  const doneAt = at + 0.25 + text.length / cps;
  const acc = t > doneAt + 0.45;
  return <At x={x} y={y} style={{opacity: p * o, transform: `translate(-50%,-50%) translateY(${(1 - p) * 20}px)`}}>
    {label ? <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 26, color: T('#fff'), background: C.blue, display: 'inline-block', padding: '4px 14px', borderRadius: 10, marginBottom: 10}}>{label}</div> : null}
    <Glass style={{width: w * W, padding: '26px 34px', borderRadius: 60, fontSize: 52, fontWeight: 700, display: 'flex', alignItems: 'center'}}>
      <span style={{flex: 1, whiteSpace: 'nowrap', overflow: 'hidden'}}>{typed}{mode === 'search' && t > doneAt ? <span style={{color: acc ? C.ink : T('#9AA6C8')}}>{suggest}</span> : null}
        <span style={{opacity: Math.floor(t * 3) % 2 ? 1 : 0, color: C.blue}}>|</span></span>
      {mode === 'command' ? <div style={{width: 76, height: 76, borderRadius: '50%', background: GRAD, color: T('#fff'), display: 'grid', placeItems: 'center', fontSize: 40,
        transform: `scale(${t > doneAt && t < doneAt + 0.2 ? 0.85 : 1})`}}>↑</div> : null}
    </Glass>
    {mode === 'search' ? <div style={{marginTop: 14, opacity: lerp(t, doneAt, doneAt + 0.2) * (acc ? 0 : 1), fontFamily: SANS, fontSize: 32, color: T('#fff'), textShadow: SHADOW_TEXT}}>
      <span style={{background: C.blue, padding: '4px 14px', borderRadius: 10, fontWeight: 800, marginRight: 12}}>Tab ➔</span>để nhận gợi ý</div> : null}
  </At>;
};

/** FileDrop: dashed drop zone, a file lands, card turns into "Đã nhận clip.mp4 ✓". */
export const FileDrop: React.FC<P> = ({duration, name = 'clip.mp4', meta = '94 giây · 622 MB', x = 0.3, y = 0.1, at = 0, dropAt = 0.6}) => {
  const {frame, fps, t} = useT();
  const p = enter(frame, fps, at);
  const got = t > dropAt;
  const s = pop(frame, fps, dropAt, 10);
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} style={{opacity: p * o}}>
    <div style={{width: 520, height: 170, borderRadius: 26, position: 'relative', fontFamily: SANS, display: 'flex', alignItems: 'center', gap: 22, padding: '0 30px',
      border: got ? T('2px solid rgba(255,255,255,0.9)') : T('4px dashed rgba(255,255,255,0.85)'), background: got ? T('linear-gradient(160deg,#FFFFFF,#E8EEFF)') : T('rgba(10,20,60,0.45)'),
      boxShadow: got ? SHADOW_CARD : 'none', transform: `scale(${got ? 0.9 + 0.1 * s : 1})`}}>
      {got ? <><div style={{width: 92, height: 112, borderRadius: 12, background: GRAD, color: T('#fff'), fontWeight: 800, fontSize: 24, display: 'grid', placeItems: 'end center', paddingBottom: 12, position: 'relative'}}>.MP4
        <div style={{position: 'absolute', right: -14, top: -14, width: 44, height: 44, borderRadius: '50%', background: T('#30D158'), color: T('#fff'), display: 'grid', placeItems: 'center', fontSize: 28}}>✓</div></div>
        <div><div style={{fontWeight: 800, fontSize: 40, color: C.ink}}>Đã nhận {name}</div><div style={{fontSize: 28, color: T('#6B7699')}}>{meta}</div></div></>
        : <div style={{width: '100%', textAlign: 'center', color: T('#fff')}}><div style={{fontWeight: 800, fontSize: 40}}>Thả file vào đây</div><div style={{fontSize: 26, opacity: 0.8}}>MP4, MOV</div></div>}
    </div>
    {!got ? <div style={{position: 'absolute', left: 200, top: lerp(t, at + 0.1, dropAt, -300, 30, EASE_OUT), width: 80, height: 100, borderRadius: 10, background: GRAD, boxShadow: SHADOW_CARD,
      transform: `rotate(${lerp(t, at, dropAt, -18, 0)}deg)`}} /> : null}
  </At>;
};

/** FocusBrackets: four corners snap around a box (face focus / "chuyển nét"); optional label chip. */
export const FocusBrackets: React.FC<P> = ({duration, x = 0.5, y = 0.32, w = 0.42, h = 0.24, label, color = T('#fff'), at = 0}) => {
  const {frame, fps, W, H} = useT();
  const s = pop(frame, fps, at, 14);
  const o = exit(frame, fps, duration);
  const bw = w * W * (1.25 - 0.25 * s), bh = h * H * (1.25 - 0.25 * s), L = 70;
  const c = (st: React.CSSProperties) => <div style={{position: 'absolute', width: L, height: L, borderColor: color, borderStyle: 'solid', borderWidth: 0, ...st}} />;
  return <At x={x} y={y} style={{opacity: Math.min(1, s * 2) * o, width: bw, height: bh, filter: T('drop-shadow(0 2px 6px rgba(0,0,0,0.5))')}}>
    {c({left: 0, top: 0, borderLeftWidth: 7, borderTopWidth: 7, borderTopLeftRadius: 18})}{c({right: 0, top: 0, borderRightWidth: 7, borderTopWidth: 7, borderTopRightRadius: 18})}
    {c({left: 0, bottom: 0, borderLeftWidth: 7, borderBottomWidth: 7, borderBottomLeftRadius: 18})}{c({right: 0, bottom: 0, borderRightWidth: 7, borderBottomWidth: 7, borderBottomRightRadius: 18})}
    {label ? <div style={{position: 'absolute', left: '50%', top: -96, transform: 'translateX(-50%)'}}><Glass style={{padding: '10px 24px', fontSize: 36, fontWeight: 800, whiteSpace: 'nowrap', borderRadius: 18}}>{label}</Glass></div> : null}
  </At>;
};

/** ChapterPanel: "TRONG VIDEO NÀY 03/12" list on the side, current item highlighted (scrolls with long lists). */
export const ChapterPanel: React.FC<P> = ({duration, title = 'TRONG VIDEO NÀY', items = [], current = 0, x = 0.79, y = 0.3, more}) => {
  const {frame, fps} = useT();
  const p = enter(frame, fps, 0, 0.3);
  const o = exit(frame, fps, duration);
  const win = 12, start = Math.max(0, Math.min(items.length - win, current - 3));
  return <At x={x} y={y} style={{opacity: p * o, transform: `translate(-50%,-50%) translateX(${(1 - p) * 60}px)`}}>
    <div style={{width: 400, borderRadius: 22, padding: '22px 18px', background: T('linear-gradient(170deg, rgba(23,38,110,0.94), rgba(10,20,64,0.94))'), border: T('1.5px solid rgba(140,170,255,0.3)'), boxShadow: SHADOW_CARD, fontFamily: SANS}}>
      <div style={{display: 'flex', justifyContent: 'space-between', color: T('#AFC3FF'), fontWeight: 800, fontSize: 20, letterSpacing: '0.12em', marginBottom: 12}}>
        <span>{title}</span><span style={{color: T('#fff')}}>{String(current + 1).padStart(2, '0')} / {items.length}</span></div>
      {items.slice(start, start + win).map((it: string, j: number) => {
        const i = start + j, on = i === current;
        return <div key={i} style={{display: 'flex', gap: 12, alignItems: 'center', padding: '7px 12px', borderRadius: 10, marginBottom: 3, fontSize: 25, fontWeight: on ? 800 : 600,
          background: on ? T('#fff') : 'transparent', color: on ? C.navy : i < current ? T('rgba(255,255,255,0.45)') : T('rgba(255,255,255,0.85)')}}>
          <span style={{fontSize: 18, opacity: 0.7, width: 24}}>{String(i + 1).padStart(2, '0')}</span>{it}</div>;
      })}
      {more ? <div style={{marginTop: 10, color: T('#8EB3FF'), fontWeight: 800, fontSize: 22, paddingLeft: 12}}>{more}</div> : null}
    </div>
  </At>;
};

/** NotifyStack: notifications pile in fast from the top (thông báo dồn dập). */
export const NotifyStack: React.FC<P> = ({duration, items = [], x = 0.36, y = 0.05, gap = 0.22}) => {
  const {frame, fps} = useT();
  const o = exit(frame, fps, duration);
  const list = items.map((it: any) => (typeof it === 'string' ? {t: it} : it));
  const n = list.filter((_: any, i: number) => frame >= i * gap * fps).length;
  return <At x={x} y={y} anchor="-50%, 0" style={{opacity: o}}>
    {list.slice(0, n).map((it: any, i: number) => {
      const s = pop(frame, fps, i * gap, 14), depth = n - 1 - i;
      return <div key={i} style={{position: 'absolute', left: -330, top: depth * 22 + (1 - s) * -120, width: 660, transform: `scale(${1 - depth * 0.05})`, zIndex: i, opacity: depth > 3 ? 0 : 1}}>
        <Glass style={{display: 'flex', gap: 18, alignItems: 'center', padding: '20px 24px', borderRadius: 26}}>
          <div style={{width: 64, height: 64, borderRadius: 16, background: GRAD, display: 'grid', placeItems: 'center', fontSize: 34}}>{it.icon || '🔔'}</div>
          <div><div style={{fontSize: 22, color: T('#6B7699'), fontWeight: 600}}>{it.app || 'TikTok'} · bây giờ</div><div style={{fontSize: 32, fontWeight: 800}}>{it.t}</div></div>
        </Glass>
      </div>;
    })}
  </At>;
};

/** ChatBubbles: chat with AI — bubbles pop in left/right, typing dots before AI replies. */
export const ChatBubbles: React.FC<P> = ({duration, items = [], x = 0.5, y = 0.08, w = 0.86}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} anchor="-50%, 0" style={{opacity: o, width: w * W, display: 'flex', flexDirection: 'column', gap: 14}}>
    {items.map((it: any, i: number) => {
      const at = it.at ?? i * 0.7, me = !!it.me;
      if (t < at - (me ? 0 : 0.4)) return null;
      const typing = !me && t < at;
      const s = pop(frame, fps, me ? at : at - 0.4, 14);
      return <div key={i} style={{alignSelf: me ? 'flex-end' : 'flex-start', transform: `scale(${0.8 + 0.2 * s})`, transformOrigin: me ? 'right' : 'left', opacity: s,
        maxWidth: '78%', padding: '18px 26px', borderRadius: 30, fontFamily: SANS, fontWeight: 700, fontSize: 38, boxShadow: SHADOW_CARD,
        background: me ? `linear-gradient(180deg,${T('#4C6FFF')},${C.blue})` : T('#fff'), color: me ? T('#fff') : C.ink, borderBottomRightRadius: me ? 8 : 30, borderBottomLeftRadius: me ? 30 : 8}}>
        {typing ? <span style={{letterSpacing: 6}}>{'•••'.slice(0, 1 + (Math.floor(t * 6) % 3))}</span> : <>{!me && it.who ? <span style={{color: C.blue}}>{it.who} · </span> : null}{it.t}</>}
      </div>;
    })}
  </At>;
};

/** CommentsDrop: viewer comment cards drop in from the top and stack. */
export const CommentsDrop: React.FC<P> = ({duration, items = [], x = 0.36, y = 0.06, gap = 0.3}) => {
  const {frame, fps} = useT();
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} anchor="-50%, 0" style={{opacity: o, width: 620, display: 'flex', flexDirection: 'column', gap: 12}}>
    {items.map((it: any, i: number) => {
      const c = typeof it === 'string' ? {t: it} : it;
      const s = spring({frame: frame - (c.at ?? i * gap) * fps, fps, config: {damping: 11, stiffness: 150, mass: 0.8}});
      return <div key={i} style={{transform: `translateY(${(1 - s) * -260}px) rotate(${(1 - s) * (i % 2 ? 6 : -6)}deg)`, opacity: Math.min(1, s * 3)}}>
        <Glass style={{display: 'flex', gap: 16, alignItems: 'center', padding: '14px 20px', borderRadius: 22}}>
          <div style={{width: 52, height: 52, borderRadius: '50%', background: `hsl(${(i * 67) % 360},55%,78%)`}} />
          <div style={{flex: 1}}><div style={{fontSize: 20, color: T('#7A84A6')}}>{c.name || 'người xem'}</div><div style={{fontSize: 30, fontWeight: 800}}>{c.t}</div></div>
          <span style={{fontSize: 28, color: T('#C3CAE0')}}>♡</span>
        </Glass>
      </div>;
    })}
  </At>;
};

/** BarChart: bars grow one by one with values counting; last bar highlighted. */
export const BarChart: React.FC<P> = ({duration, bars = [], title, x = 0.5, y = 0.22, w = 0.8, h = 0.24, at = 0, unit = ''}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  const max = Math.max(1, ...bars.map((b: any) => b.v));
  return <At x={x} y={y} style={{opacity: o * enter(frame, fps, at, 0.3)}}>
    <Glass style={{width: w * W, padding: 34, borderRadius: 34}}>
      {title ? <div style={{fontSize: 40, fontWeight: 800, marginBottom: 20, letterSpacing: '-0.02em'}}>{title}</div> : null}
      <div style={{display: 'flex', alignItems: 'flex-end', gap: 24, height: h * H}}>
        {bars.map((b: any, i: number) => {
          const g = lerp(t, at + 0.2 + i * 0.18, at + 0.75 + i * 0.18, 0, 1, EASE_OUT), last = i === bars.length - 1;
          return <div key={i} style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: '100%'}}>
            <div style={{fontSize: 30, fontWeight: 800, color: last ? C.blue : C.navy, opacity: g}}>{Math.round(b.v * g)}{unit}</div>
            <div style={{width: '100%', height: `${(b.v / max) * 82 * g}%`, borderRadius: 14, background: last ? GRAD : T('linear-gradient(180deg,#C9D6FF,#9DB2F5)')}} />
            <div style={{fontSize: 24, fontWeight: 700, color: T('#6B7699'), marginTop: 8, whiteSpace: 'nowrap'}}>{b.label}</div>
          </div>;
        })}
      </div>
    </Glass>
  </At>;
};

/** EditTimeline: editing-software timeline (chữ / hình / tiếng / nhạc tracks), clips appear, playhead runs. */
export const EditTimeline: React.FC<P> = ({duration, tracks = ['chữ', 'hình', 'tiếng', 'nhạc'], x = 0.3, y = 0.72, w = 0.56}) => {
  const {frame, fps, t, W} = useT();
  const o = exit(frame, fps, duration);
  const cols = [T('#8EB3FF'), T('#F5C542'), T('#FFFFFF'), T('#FF7EB3')];
  return <At x={x} y={y} style={{opacity: o * enter(frame, fps, 0, 0.3)}}>
    <div style={{width: w * W, background: T('rgba(10,14,32,0.92)'), borderRadius: 18, padding: '16px 18px', fontFamily: MONO, boxShadow: SHADOW_CARD, position: 'relative'}}>
      <div style={{display: 'flex', justifyContent: 'space-between', color: T('#7E89AE'), fontSize: 16, marginLeft: 70, marginBottom: 8}}>{['00:00', '00:10', '00:20', '00:30'].map((s) => <span key={s}>{s}</span>)}</div>
      {tracks.map((tr: string, r: number) => <div key={r} style={{display: 'flex', alignItems: 'center', height: 34, gap: 8}}>
        <span style={{width: 62, color: T('#C9D2F0'), fontSize: 18, fontFamily: SANS, fontWeight: 700}}>{tr}</span>
        <div style={{flex: 1, position: 'relative', height: 22}}>{[0, 1, 2].map((c) => {
          const a = 0.15 + r * 0.12 + c * 0.2, g = lerp(t, a, a + 0.25);
          const l = (r === 3 ? 0 : c * 34 + (r % 2) * 6), wd = r === 3 ? 100 : 26 + ((r + c) % 3) * 4;
          return r === 3 && c > 0 ? null : <div key={c} style={{position: 'absolute', left: `${l}%`, width: `${wd * g}%`, top: 0, bottom: 0, borderRadius: 6, background: cols[r % 4], opacity: 0.9}} />;
        })}</div></div>)}
      <div style={{position: 'absolute', top: 10, bottom: 10, left: 88 + (w * W - 110) * lerp(t, 0.2, duration, 0, 1, (k) => k), width: 3, background: T('#FF3B5C'), borderRadius: 2}} />
    </div>
  </At>;
};

/** JiggleChips: chips wobble like iOS edit mode, an ✕ appears and `remove` chip pops away. */
export const JiggleChips: React.FC<P> = ({duration, items = ['cắt', 'lọc', 'màu'], remove = 1, removeAt = 0.9, x = 0.3, y = 0.1, size = 52}) => {
  const {frame, fps, t} = useT();
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} style={{opacity: o * enter(frame, fps, 0, 0.3), display: 'flex', gap: 16}}>
    {items.map((it: string, i: number) => {
      const gone = i === remove ? lerp(t, removeAt, removeAt + 0.25) : 0;
      const jig = t > 0.3 && t < removeAt + 0.2 ? Math.sin(t * 38 + i * 2) * 3 : 0;
      return <div key={i} style={{position: 'relative', transform: `rotate(${jig}deg) scale(${1 - gone})`, opacity: 1 - gone, width: gone ? `${(1 - gone) * 100}%` : undefined}}>
        <Glass style={{padding: `${size * 0.25}px ${size * 0.45}px`, fontSize: size, fontWeight: 800, borderRadius: size * 0.4}}>{it}</Glass>
        {i === remove && t > 0.35 ? <div style={{position: 'absolute', left: -10, top: -10, width: 34, height: 34, borderRadius: '50%', background: T('#FF3B5C'), color: T('#fff'), fontSize: 22, display: 'grid', placeItems: 'center', fontFamily: SANS, fontWeight: 800}}>✕</div> : null}
      </div>;
    })}
  </At>;
};

/** Eyedropper: dropper moves to a point, picks a colour; swatch + hex chip appear. */
export const Eyedropper: React.FC<P> = ({duration, from = [0.2, 0.55], to = [0.5, 0.5], color = T('#A9A2F2'), at = 0.1, pickAt = 0.7}) => {
  const {frame, fps, t, W, H} = useT();
  const m = lerp(t, at, pickAt);
  const px = (from[0] + (to[0] - from[0]) * m) * W, py = (from[1] + (to[1] - from[1]) * m) * H;
  const sw = pop(frame, fps, pickAt, 12);
  const o = exit(frame, fps, duration);
  return <AbsoluteFill style={{opacity: o}}>
    <svg width={90} height={90} viewBox="0 0 24 24" style={{position: 'absolute', left: px - 6, top: py - 84, filter: T('drop-shadow(0 4px 8px rgba(0,0,0,0.5))')}}>
      <path d="M3 21l1.5-4.5L14 7l3 3-9.5 9.5z" fill={T("#fff")} stroke={T("#0E1530")} strokeWidth="1.3" /><path d="M14 7l2-2a2.1 2.1 0 013 3l-2 2" fill={T("#0E1530")} />
    </svg>
    {t > pickAt ? <div style={{position: 'absolute', left: px + 30, top: py + 20, display: 'flex', alignItems: 'center', gap: 14, transform: `scale(${sw})`, transformOrigin: 'left'}}>
      <div style={{width: 96, height: 96, borderRadius: '50%', background: color, border: T('6px solid #fff'), boxShadow: SHADOW_CARD}} />
      <Glass style={{padding: '8px 18px', fontFamily: MONO, fontSize: 32, fontWeight: 700, borderRadius: 14}}>{color.toUpperCase()}</Glass>
    </div> : null}
  </AbsoluteFill>;
};

/** CompareHandle: before/after split handle + "SAU" / "TRƯỚC" chips (pair with fx "compare" over the same range). */
export const CompareHandle: React.FC<P> = ({duration, from = 0, to = 1, left = 'SAU', right = 'TRƯỚC'}) => {
  const {frame, fps, t, W, H} = useT();
  const sp = from + (to - from) * (1 - Math.pow(1 - Math.min(1, t / Math.max(0.1, duration)), 2));
  const o = exit(frame, fps, duration);
  const chip = (s: string, st: React.CSSProperties) => <div style={{position: 'absolute', top: 60, fontFamily: SANS, fontWeight: 800, fontSize: 30, padding: '6px 18px', borderRadius: 16, ...st}}>{s}</div>;
  return <AbsoluteFill style={{opacity: o}}>
    {chip(left, {left: 40, background: T('#fff'), color: C.navy})}{chip(right, {right: 40, background: T('rgba(10,20,60,0.75)'), color: T('#fff')})}
    <div style={{position: 'absolute', left: sp * W - 32, top: H * 0.62, width: 64, height: 64, borderRadius: '50%', background: T('#fff'), boxShadow: SHADOW_CARD, display: 'grid', placeItems: 'center', fontFamily: SANS, fontWeight: 800, color: C.navy, fontSize: 28}}>‹›</div>
  </AbsoluteFill>;
};

/** VhsHud: PLAY ▶, REC dot and running timecode (pair with fx "vhs"). */
export const VhsHud: React.FC<P> = ({duration, start = '0:17:11', label = 'PLAY ▶'}) => {
  const {t} = useT();
  const [h, m, s] = start.split(':').map(Number);
  const tot = h * 3600 + m * 60 + s + Math.floor(t);
  const tc = `${Math.floor(tot / 3600)}:${String(Math.floor(tot / 60) % 60).padStart(2, '0')}:${String(tot % 60).padStart(2, '0')}`;
  const st: React.CSSProperties = {position: 'absolute', fontFamily: MONO, fontWeight: 700, color: T('#F2F2F2'), fontSize: 58, textShadow: T('3px 0 rgba(255,0,80,0.6), -3px 0 rgba(0,200,255,0.6)')};
  return <AbsoluteFill>
    <div style={{...st, left: 60, top: 150}}>{label}</div>
    <div style={{...st, right: 60, top: 150, opacity: Math.floor(t * 2) % 2 ? 1 : 0.2}}>● REC</div>
    <div style={{...st, right: 60, bottom: 160}}>SP {tc}</div>
  </AbsoluteFill>;
};

// ================================================================ cards / structures
/** NumberList: "1 | chỉnh sửa / 2 | render thoải mái" with a vertical rule (navy grid scene). */
export const NumberList: React.FC<P> = ({duration, title, items = [], x = 0.12, y = 0.32, size = 64, tone = 'video'}) => {
  const {frame, fps} = useT();
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} anchor="0,0" style={{opacity: o}}>
    {title ? <div style={{marginBottom: size * 0.6, marginLeft: -size * 0.3}}><Rich text={title} size={size * 1.25} total={duration} align="left" tone={tone} /></div> : null}
    <div style={{display: 'flex', flexDirection: 'column', gap: size * 0.55, borderLeft: T('3px solid rgba(255,255,255,0.35)'), paddingLeft: size * 0.6, marginLeft: size * 0.85, position: 'relative'}}>
      {items.map((it: any, i: number) => {
        const c = typeof it === 'string' ? {t: it, at: 0.3 + i * 0.5} : it;
        const p = enter(frame, fps, c.at ?? 0.3 + i * 0.5);
        return <div key={i} style={{display: 'flex', alignItems: 'center', position: 'relative', opacity: Math.max(0.25, p), filter: `blur(${(1 - p) * 8}px)`}}>
          <span style={{position: 'absolute', left: -size * 1.65, fontFamily: SANS, fontWeight: 800, fontSize: size * 1.15, ...gradText(T('linear-gradient(180deg,#FFFFFF,#9DB6FF)'))}}>{i + 1}</span>
          {p > 0.02 ? <span style={{fontFamily: SANS, fontWeight: 700, fontSize: size, color: T('#fff'), textShadow: SHADOW_TEXT, transform: `translateX(${(1 - p) * 20}px)`}}>{c.t}</span> : null}
        </div>;
      })}
    </div>
  </At>;
};

/** VsCards: two glass cards "hơn nửa tiếng" vs "5–10 phút" with labels under, B highlighted. */
export const VsCards: React.FC<P> = ({duration, a = {v: 'hơn nửa tiếng', label: 'CHỜ', sub: ''}, b = {v: '5–10 phút', label: 'THÊM', sub: ''}, vs = 'vs', y = 0.4, bAt = 0.7}) => {
  const {frame, fps} = useT();
  const o = exit(frame, fps, duration);
  const card = (c: any, at: number, hi: boolean) => {
    const s = pop(frame, fps, at, 13);
    return <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, opacity: Math.min(1, s * 2), transform: `scale(${0.75 + 0.25 * s})`}}>
      <div style={{width: 300, height: 260, borderRadius: 26, display: 'grid', placeItems: 'center', textAlign: 'center', padding: 20, fontFamily: SANS, fontWeight: 800, fontSize: hi ? 66 : 46,
        color: T('#fff'), background: hi ? T('linear-gradient(160deg,#3D63FF,#2140D8)') : T('linear-gradient(160deg,rgba(60,90,220,0.6),rgba(30,50,150,0.6))'),
        border: T('2px solid rgba(170,195,255,0.7)'), boxShadow: hi ? T('0 0 50px rgba(70,110,255,0.6)') : SHADOW_CARD}}>{c.v}</div>
      <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 52, letterSpacing: '0.12em', color: T('#fff')}}>{c.label}</div>
      {c.sub ? <div style={{fontFamily: SANS, fontWeight: 600, fontSize: 28, color: T('#AFC3FF')}}>{c.sub}</div> : null}
    </div>;
  };
  return <At x={0.5} y={y} style={{opacity: o, display: 'flex', alignItems: 'flex-start', gap: 30}}>
    {card(a, 0, false)}<div style={{alignSelf: 'center', marginTop: -90, fontFamily: SERIF, fontStyle: 'italic', fontSize: 52, color: T('#fff'), opacity: enter(frame, fps, bAt)}}>{vs}</div>{card(b, bAt, true)}
  </At>;
};

/** Callouts: product labels with a dot and leader line ("2 cổng USB-C"). items: [{t, x, y, to:[x,y], at}] */
export const Callouts: React.FC<P> = ({duration, items = []}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration);
  return <AbsoluteFill style={{opacity: o}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      {items.map((c: any, i: number) => {
        const at = c.at ?? i * 0.35, g = lerp(t, at, at + 0.35);
        const [tx, ty] = c.to || [c.x, c.y];
        return <g key={i} opacity={g > 0 ? 1 : 0}>
          <line x1={tx * W} y1={ty * H} x2={(tx + (c.x - tx) * g) * W} y2={(ty + (c.y - ty) * g) * H} stroke={T("#fff")} strokeWidth={4} />
          <circle cx={tx * W} cy={ty * H} r={11 * Math.min(1, g * 3)} fill={T("#fff")} stroke={C.blue} strokeWidth={5} />
        </g>;
      })}
    </svg>
    {items.map((c: any, i: number) => {
      const at = c.at ?? i * 0.35, p = enter(frame, fps, at + 0.25, 0.3);
      return <At key={i} x={c.x} y={c.y} style={{opacity: p, transform: `translate(-50%,-50%) scale(${0.85 + 0.15 * p})`}}>
        <Glass style={{padding: '10px 20px', fontSize: 34, fontWeight: 800, borderRadius: 14, whiteSpace: 'nowrap', textAlign: 'center'}}>{c.t}</Glass>
      </At>;
    })}
  </AbsoluteFill>;
};

/** CountUp: big number counting from → to (with suffix), optional small top line and a ring sweep. */
export const CountUp: React.FC<P> = ({duration, from = 0, to = 100, suffix = '', top, x = 0.5, y = 0.16, size = 170, at = 0.1, dur = 0.9, ring = false}) => {
  const {frame, fps, t} = useT();
  const g = lerp(t, at, at + dur, 0, 1, EASE_OUT);
  const o = exit(frame, fps, duration);
  const v = Math.round(from + (to - from) * g);
  return <At x={x} y={y} style={{opacity: o * enter(frame, fps, 0, 0.3), textAlign: 'center'}}>
    {top ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: size * 0.28, color: T('#fff'), textShadow: SHADOW_TEXT}}>{top}</div> : null}
    <div style={{position: 'relative', display: 'inline-block'}}>
      {ring ? <svg width={size * 2.2} height={size * 2.2} style={{position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)'}} viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="46" fill="none" stroke={T("rgba(255,255,255,0.18)")} strokeWidth="2" />
        <circle cx="50" cy="50" r="46" fill="none" stroke={T("#8EB3FF")} strokeWidth="2.5" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - g} transform="rotate(-90 50 50)" />
      </svg> : null}
      <span style={{fontFamily: SANS, fontWeight: 800, fontSize: size, letterSpacing: '-0.04em', ...gradText(T('linear-gradient(180deg,#FFFFFF 40%,#B8CCFF)')),
        filter: T('drop-shadow(0 6px 20px rgba(0,0,0,0.45)) drop-shadow(0 0 24px rgba(60,100,255,0.5))'), fontVariantNumeric: 'tabular-nums'}}>{v}{suffix}</span>
    </div>
  </At>;
};

/** IconSlam: icons slam in around the head with an impact squash. items: [{icon, x, y, at}] */
export const IconSlam: React.FC<P> = ({duration, items = [], size = 120}) => {
  const {frame, fps, t} = useT();
  const o = exit(frame, fps, duration);
  return <AbsoluteFill style={{opacity: o}}>
    {items.map((c: any, i: number) => {
      const at = c.at ?? i * 0.2, p = lerp(t, at, at + 0.14, 0, 1, EASE_OUT);
      const sq = t > at + 0.14 && t < at + 0.32 ? Math.sin(((t - at - 0.14) / 0.18) * Math.PI) * 0.15 : 0;
      return <At key={i} x={c.x} y={c.y} style={{opacity: p, transform: `translate(-50%,-50%) scale(${(2.4 - 1.4 * p) * (1 + sq)}, ${(2.4 - 1.4 * p) * (1 - sq)}) rotate(${c.rot ?? (i % 2 ? 8 : -8)}deg)`}}>
        <Glass style={{width: size, height: size, borderRadius: size * 0.26, display: 'grid', placeItems: 'center'}}><Icon v={c.icon} size={size * 0.56} /></Glass>
      </At>;
    })}
  </AbsoluteFill>;
};

/** OrbitIcons: small glass icons orbiting around the head. */
export const OrbitIcons: React.FC<P> = ({duration, icons = ['🎬', '💻', '📄', '🤖'], x = 0.5, y = 0.33, rx = 0.36, ry = 0.08, size = 96, speed = 0.5}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0);
  return <AbsoluteFill style={{opacity: o}}>
    {icons.map((ic: string, i: number) => {
      const a = (i / icons.length) * Math.PI * 2 + t * speed * Math.PI;
      const z = Math.sin(a);
      return <div key={i} style={{position: 'absolute', left: (x + Math.cos(a) * rx) * W - size / 2, top: (y + z * ry) * H - size / 2, transform: `scale(${0.8 + 0.25 * (z + 1) / 2})`, zIndex: Math.round(z * 10)}}>
        <Glass style={{width: size, height: size, borderRadius: size * 0.26, display: 'grid', placeItems: 'center', opacity: 0.75 + 0.25 * z}}><Icon v={ic} size={size * 0.55} /></Glass>
      </div>;
    })}
  </AbsoluteFill>;
};

/** ScanLines: two thin horizontal lines with a light streak running. */
export const ScanLines: React.FC<P> = ({duration, ys = [0.3, 0.62], color = T('#8EB3FF')}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0);
  return <AbsoluteFill style={{opacity: o}}>
    {ys.map((yy: number, i: number) => {
      const run = ((t * 0.9 + i * 0.5) % 1.4) - 0.2;
      return <div key={i} style={{position: 'absolute', left: 0, width: W * lerp(t, i * 0.1, 0.5 + i * 0.1), top: yy * H, height: 2, background: T('rgba(255,255,255,0.55)')}}>
        <div style={{position: 'absolute', left: run * W - 150, width: 300, top: -3, height: 8, borderRadius: 8, background: `linear-gradient(90deg, transparent, ${color}, ${T('#fff')}, ${color}, transparent)`, filter: 'blur(2px)'}} />
      </div>;
    })}
  </AbsoluteFill>;
};

// ================================================================ cards that hold stills ("frame:12.3")
/** CardStack: storyboard cards fan out (xấp phân cảnh). items: [{src, label}] */
export const CardStack: React.FC<P> = ({duration, items = [], x = 0.3, y = 0.1, w = 220, at = 0}) => {
  const {frame, fps} = useT();
  const o = exit(frame, fps, duration);
  return <At x={x} y={y} style={{opacity: o, width: w, height: w * 0.62}}>
    {items.map((c: any, i: number) => {
      const s = pop(frame, fps, at + i * 0.09, 14), n = items.length;
      const rot = (i - (n - 1) / 2) * 9 * s, dx = (i - (n - 1) / 2) * w * 0.32 * s;
      return <div key={i} style={{position: 'absolute', inset: 0, transform: `translateX(${dx}px) rotate(${rot}deg) translateY(${(1 - s) * -80}px)`, transformOrigin: '50% 140%', opacity: Math.min(1, s * 2),
        borderRadius: 14, overflow: 'hidden', border: T('5px solid #fff'), boxShadow: SHADOW_CARD, background: T('#fff')}}>
        <Photo s={typeof c === 'string' ? c : c.src} />
        <div style={{position: 'absolute', left: 6, top: 6, background: C.navy, color: T('#fff'), fontFamily: SANS, fontWeight: 800, fontSize: 18, padding: '2px 8px', borderRadius: 6}}>C{i + 1}</div>
      </div>;
    })}
  </At>;
};

/** Polaroids: freeze-frame photos of the speaker in a row, slightly tilted, label under each. */
export const Polaroids: React.FC<P> = ({duration, items = [], y = 0.1, w = 230, gap = 26}) => {
  const {frame, fps} = useT();
  const o = exit(frame, fps, duration);
  return <At x={0.5} y={y} style={{opacity: o, display: 'flex', gap}}>
    {items.map((c: any, i: number) => {
      const s = pop(frame, fps, c.at ?? i * 0.45, 13);
      return <div key={i} style={{width: w, background: T('#fff'), padding: 10, paddingBottom: 44, borderRadius: 10, boxShadow: SHADOW_CARD, opacity: Math.min(1, s * 2),
        transform: `rotate(${(c.rot ?? (i % 2 ? 4 : -4)) * s}deg) scale(${0.7 + 0.3 * s}) translateY(${(1 - s) * -40}px)`, position: 'relative'}}>
        <div style={{width: '100%', height: w * 0.85, borderRadius: 6, overflow: 'hidden'}}><Photo s={c.src} /></div>
        <div style={{position: 'absolute', left: 0, right: 0, bottom: 8, textAlign: 'center', fontFamily: SANS, fontWeight: 700, fontSize: 22, color: C.ink}}>{c.label}</div>
      </div>;
    })}
  </At>;
};

/** PostWall: full-screen — starts on one tile, pulls back to a wall of tiles (tường bài đăng / lưới video). */
export const PostWall: React.FC<P> = ({duration, items = [], label, bg = T('#0B1430'), cols = 3}) => {
  const {frame, fps, t, W, H} = useT();
  const z = lerp(t, 0.15, 0.85, 0, 1, EASE_IN);
  const o = exit(frame, fps, duration);
  const n = Math.max(cols * 3, items.length), tw = W / cols, th = H / 3;
  const scale = 1 + (cols - 1) * (1 - z);
  return <AbsoluteFill style={{background: bg, opacity: o, overflow: 'hidden'}}>
    <div style={{position: 'absolute', left: 0, top: 0, width: W, height: H, transform: `scale(${scale})`, transformOrigin: '50% 50%'}}>
      {Array.from({length: Math.min(n, cols * 3)}).map((_, i) => {
        const c = items[i % Math.max(1, items.length)] || {};
        return <div key={i} style={{position: 'absolute', left: (i % cols) * tw + 8, top: Math.floor(i / cols) * th + 8, width: tw - 16, height: th - 16, borderRadius: 18, overflow: 'hidden', background: T('#1B2550')}}>
          <Photo s={typeof c === 'string' ? c : c.src} /></div>;
      })}
    </div>
    {label ? <div style={{position: 'absolute', left: 0, right: 0, bottom: H * 0.1, textAlign: 'center', opacity: z}}><Rich text={label} size={80} total={duration} /></div> : null}
  </AbsoluteFill>;
};

/** Newspaper: full-screen — front page spins in and lands (trang nhất), with a B&W still of the speaker. */
export const Newspaper: React.FC<P> = ({duration, name = 'Nhật Báo AI', headline = 'TIN NÓNG', sub = '', photo, date = '', bg = T('#1A1F2E')}) => {
  const {frame, fps, t, W} = useT();
  const s = lerp(t, 0, 0.75, 0, 1, EASE_IN);
  const o = exit(frame, fps, duration);
  return <AbsoluteFill style={{background: bg, opacity: o, display: 'grid', placeItems: 'center'}}>
    <div style={{width: W * 0.82, background: T('#F3EEE2'), padding: 40, boxShadow: T('0 30px 80px rgba(0,0,0,0.6)'), transform: `rotate(${(1 - s) * 720 - 3 * s}deg) scale(${0.1 + 0.9 * s})`, fontFamily: SERIF, color: T('#111')}}>
      <div style={{textAlign: 'center', fontStyle: 'italic', fontWeight: 800, fontSize: 64, borderBottom: T('3px solid #111'), paddingBottom: 8}}>{name}</div>
      <div style={{display: 'flex', justifyContent: 'space-between', fontFamily: SANS, fontSize: 18, fontWeight: 700, padding: '6px 0', borderBottom: T('1px solid #111')}}><span>SỐ 01</span><span>{date}</span><span>TRANG NHẤT</span></div>
      <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 108, lineHeight: 0.95, textAlign: 'center', margin: '18px 0', letterSpacing: '-0.04em'}}>{headline}</div>
      {sub ? <div style={{textAlign: 'center', fontStyle: 'italic', fontSize: 34, marginBottom: 16}}>{sub}</div> : null}
      <div style={{display: 'flex', gap: 20}}>
        <div style={{flex: 1.3, height: 420, overflow: 'hidden', border: T('2px solid #111')}}><Photo s={photo} style={{filter: 'grayscale(1) contrast(1.15)'}} /></div>
        <div style={{flex: 1, display: 'flex', flexDirection: 'column', gap: 10}}>{Array.from({length: 16}).map((_, i) => <div key={i} style={{height: 10, background: T('#555'), width: `${70 + random(`n${i}`) * 30}%`}} />)}</div>
      </div>
    </div>
  </AbsoluteFill>;
};

/** TearAway: transition — a still of the previous moment rips along a jagged line, halves fly apart. */
export const TearAway: React.FC<P> = ({duration, src: s0, at = 0.15}) => {
  const {t, W, H} = useT();
  const g = lerp(t, at, Math.min(duration, at + 0.6), 0, 1, (k) => k * k);
  const crack = lerp(t, 0, at + 0.05);
  const pts = Array.from({length: 14}).map((_, i) => `${50 + (random(`t${i}`) - 0.5) * 14}% ${(i / 13) * 100}%`);
  const left = `polygon(0 0, ${pts.join(', ')}, 0 100%)`;
  const right = `polygon(100% 0, ${pts.join(', ')}, 100% 100%)`;
  const half = (clip: string, dir: number) => <div style={{position: 'absolute', inset: 0, clipPath: clip, transform: `translateX(${dir * g * W * 0.75}px) rotate(${dir * g * 10}deg)`,
    filter: `drop-shadow(${-dir * 8}px 0 12px ${T('rgba(0,0,0,0.5)')})`}}><Photo s={s0} /></div>;
  return <AbsoluteFill style={{opacity: t < duration - 0.02 ? 1 : 0}}>
    {half(left, -1)}{half(right, 1)}
    {g === 0 ? <svg width={W} height={H} style={{position: 'absolute', inset: 0}}><polyline points={pts.map((p) => { const [a, b] = p.split(' ').map((v) => parseFloat(v)); return `${(a / 100) * W},${(b / 100) * H * crack}`; }).join(' ')}
      fill="none" stroke={T("#fff")} strokeWidth={5} /></svg> : null}
  </AbsoluteFill>;
};

/** BlowAway: transition — the still flies off to a side with motion blur and spin (thổi bay). */
export const BlowAway: React.FC<P> = ({duration, src: s0, dir = 1, at = 0}) => {
  const {t, W} = useT();
  const g = lerp(t, at, Math.min(duration, at + 0.45), 0, 1, (k) => k * k * k);
  return <AbsoluteFill style={{transform: `translateX(${dir * g * W * 1.3}px) rotate(${dir * g * 25}deg) scale(${1 - g * 0.3})`, filter: `blur(${g * 18}px)`, opacity: 1 - g * 0.3}}>
    <Photo s={s0} />
  </AbsoluteFill>;
};

/** InkSpread: transition — an ink blob grows from a point to cover the frame, then (optionally) clears. */
export const InkSpread: React.FC<P> = ({duration, x = 0.3, y = 0.4, color = T('#0B1E5E'), hold = 0.3}) => {
  const {t, W, H} = useT();
  const grow = lerp(t, 0, duration * 0.45, 0, 1, EASE_IN);
  const back = lerp(t, duration * 0.45 + hold, duration, 0, 1, EASE_OUT);
  const R = Math.hypot(W, H) * 1.1 * grow * (1 - back);
  const blobs = Array.from({length: 7}).map((_, i) => ({a: (i / 7) * Math.PI * 2, r: 0.55 + random(`i${i}`) * 0.4}));
  return <AbsoluteFill>
    <svg width={W} height={H}><g fill={color}>
      <circle cx={x * W} cy={y * H} r={R} />
      {blobs.map((b, i) => <circle key={i} cx={x * W + Math.cos(b.a) * R * 0.75} cy={y * H + Math.sin(b.a) * R * 0.75} r={R * b.r * 0.6} />)}
    </g></svg>
  </AbsoluteFill>;
};

/** TitleCard: full-screen title card (cream / navy); with `iris` a hole opens at that point and flies into it (lao vào thẻ). */
export const TitleCard: React.FC<P> = ({duration, title = 'Thẻ tiêu đề', sub = '', theme = 'navy', iris, size = 190}) => {
  const {frame, fps, t, W, H} = useT();
  const cream = theme === 'cream';
  const p = enter(frame, fps, 0.05, 0.5);
  const fly = iris ? lerp(t, duration - 0.55, duration, 0, 1, (k) => k * k * k) : 0;
  const R = fly * Math.hypot(W, H) * 1.2;
  const mask = iris ? `radial-gradient(circle at ${iris[0] * 100}% ${iris[1] * 100}%, transparent ${R}px, ${T('#000')} ${R + 2}px)` : undefined;
  return <AbsoluteFill style={{background: cream ? T('#F3EEE2') : T('radial-gradient(circle at 30% 20%, #23399A, #0B1747 70%)'), WebkitMaskImage: mask, maskImage: mask,
    transform: `scale(${1 + fly * 2.5})`, transformOrigin: iris ? `${iris[0] * 100}% ${iris[1] * 100}%` : 'center', opacity: iris ? 1 : exit(frame, fps, duration)}}>
    {!cream ? <AbsoluteFill style={{backgroundImage: T('linear-gradient(rgba(255,255,255,0.06) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.06) 2px, transparent 2px)'), backgroundSize: '54px 54px'}} /> : null}
    <div style={{position: 'absolute', left: W * 0.09, top: H * 0.28, right: W * 0.08, opacity: p, filter: `blur(${(1 - p) * 10}px)`}}>
      <div style={{width: 80, height: 6, background: cream ? C.navy : T('#8EB3FF'), marginBottom: 30}} />
      <div style={{fontFamily: cream ? SERIF : SANS, fontWeight: 800, fontSize: size, lineHeight: 1, letterSpacing: '-0.04em', color: cream ? T('#13183A') : undefined,
        ...(cream ? {} : gradText(T('linear-gradient(180deg,#FFFFFF 40%,#B8CCFF)')))}}>{title}</div>
      {sub ? <div style={{marginTop: 30, fontFamily: SANS, fontWeight: 700, fontSize: 34, letterSpacing: '0.16em', color: cream ? C.navy : T('#AFC3FF')}}>{sub}</div> : null}
    </div>
  </AbsoluteFill>;
};

/** Intertitle: full-screen silent-film card "Trong khi đó..." with ornament frame. */
export const Intertitle: React.FC<P> = ({duration, text = 'Trong khi đó...', sub = '', theme = 'navy'}) => {
  const {frame, fps, W, H} = useT();
  const p = enter(frame, fps, 0.05, 0.45);
  const o = exit(frame, fps, duration);
  const bg = theme === 'black' ? T('#0A0A0C') : theme === 'cream' ? T('#F3EEE2') : T('#0C1A52');
  const fg = theme === 'cream' ? T('#13183A') : T('#F4F6FF');
  return <AbsoluteFill style={{background: bg, opacity: o}}>
    <div style={{position: 'absolute', left: W * 0.06, top: H * 0.06, right: W * 0.06, bottom: H * 0.06, border: `3px solid ${fg}`, outline: `1px solid ${fg}`, outlineOffset: -14, opacity: 0.85}} />
    <div style={{position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', textAlign: 'center', opacity: p, filter: `blur(${(1 - p) * 8}px)`}}>
      <div><div style={{fontFamily: SERIF, fontStyle: 'italic', fontWeight: 700, fontSize: 120, color: fg}}>{text}</div>
        <div style={{fontFamily: SERIF, fontSize: 50, color: fg, margin: '20px 0'}}>~ ❦ ~</div>
        {sub ? <div style={{fontFamily: SANS, fontWeight: 600, fontSize: 28, letterSpacing: '0.2em', color: fg, opacity: 0.8}}>{sub}</div> : null}</div>
    </div>
  </AbsoluteFill>;
};

/** ScriptPage: screenplay page (Courier) typing out a scene heading, character and line. */
export const ScriptPage: React.FC<P> = ({duration, scene = 'CẢNH 1. NỘI. PHÒNG LÀM VIỆC - NGÀY', character = 'MAI', paren = '(nói vào máy)', line = '', x = 0.27, y = 0.2, w = 0.5, cps = 22}) => {
  const {frame, fps, t, W} = useT();
  const p = enter(frame, fps, 0, 0.35);
  const o = exit(frame, fps, duration);
  const full = `${scene}\n\n${character}\n${paren}\n${line}`;
  const shown = full.slice(0, Math.floor(Math.max(0, t - 0.25) * cps));
  return <At x={x} y={y} style={{opacity: p * o, transform: `translate(-50%,-50%) rotate(-1.5deg) translateY(${(1 - p) * 30}px)`}}>
    <div style={{width: w * W, minHeight: w * W * 0.5, background: T('#FBFAF6'), boxShadow: SHADOW_CARD, padding: 40, fontFamily: '"Courier New", Courier, monospace', fontSize: 28, color: T('#111'), whiteSpace: 'pre-wrap', lineHeight: 1.45}}>
      {shown.split('\n').map((l, i) => <div key={i} style={{textAlign: i >= 2 && i <= 3 ? 'center' : 'left', fontWeight: i === 0 || i === 2 ? 700 : 400}}>{l || ' '}</div>)}
      <span style={{opacity: Math.floor(t * 3) % 2}}>▍</span>
    </div>
  </At>;
};

/** CodeLayer: full-frame monospace code scrolling (use "behind": true so it sits behind the speaker). */
export const CodeLayer: React.FC<P> = ({duration, color = T('#9DB8FF'), size = 34, opacity = 0.85, code}) => {
  const {t, H} = useT();
  const lines: string[] = (code || `const cue = cues.find((c) => t >= c.start && t < c.end);\nif (cue.text === 'người phủ code') play(codeBody);\nexport const Episode: React.FC = () => {\n  const frame = useCurrentFrame();\n  const wins = windows(ep);\n  return (<AbsoluteFill style={{background: bg}}>\n    <OffthreadVideo src={staticFile('base.mp4')} />\n    <Captions wins={wins} />\n  </AbsoluteFill>);\n};\nconst m = w.fx.mods ? w.fx.mods(fr - w.from) : {};`).split('\n');
  const all = Array.from({length: 60}).map((_, i) => lines[i % lines.length]);
  return <AbsoluteFill style={{opacity: opacity * lerp(t, 0, 0.3) * lerp(t, duration - 0.3, duration, 1, 0)}}>
    <div style={{position: 'absolute', left: 30, right: 10, top: -((t * 120) % (size * 1.4 * lines.length)), fontFamily: MONO, fontSize: size, lineHeight: 1.4, color, whiteSpace: 'pre', textShadow: `0 0 12px ${color}88`}}>
      {all.map((l, i) => <div key={i}>{l}</div>)}
    </div>
  </AbsoluteFill>;
};

/** OrbitRing: a ring band of text orbiting the head; render.py draws the back half behind the speaker. */
export const OrbitRing: React.FC<P> = ({duration, text = 'VÒNG QUỸ ĐẠO • ', x = 0.5, y = 0.2, rx = 0.3, ry = 0.045, size = 38, half = 'front', speed = 0.35, tilt = -8, color = T('#3158FF')}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0);
  const chars = [...text.repeat(Math.max(1, Math.ceil(60 / text.length)))].slice(0, 60);
  const N = chars.length;
  return <AbsoluteFill style={{opacity: o, transform: `rotate(${tilt}deg)`, transformOrigin: `${x * 100}% ${y * 100}%`}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      {Array.from({length: 72}).map((_, i) => {
        const a0 = (i / 72) * Math.PI * 2, a1 = ((i + 1.05) / 72) * Math.PI * 2;
        const back = Math.sin((a0 + a1) / 2) < 0;
        if ((half === 'back') !== back && half !== 'all') return null;
        return <path key={i} d={`M ${(x + Math.cos(a0) * rx) * W} ${(y + Math.sin(a0) * ry) * H} L ${(x + Math.cos(a1) * rx) * W} ${(y + Math.sin(a1) * ry) * H}`}
          stroke={color} strokeWidth={size * 1.35} strokeOpacity={back ? 0.75 : 0.95} />;
      })}
    </svg>
    {chars.map((ch, i) => {
      const a = (i / N) * Math.PI * 2 + t * speed * Math.PI * 2;
      const back = Math.sin(a) < 0;
      if ((half === 'back') !== back && half !== 'all') return null;
      const px = (x + Math.cos(a) * rx) * W, py = (y + Math.sin(a) * ry) * H;
      return <span key={i} style={{position: 'absolute', left: px, top: py, transform: `translate(-50%,-50%) scaleX(${Math.max(0.15, Math.abs(Math.sin(a + Math.PI / 2)))})`,
        fontFamily: SANS, fontWeight: 800, fontSize: size, color: T('#fff'), opacity: back ? 0.7 : 1}}>{ch}</span>;
    })}
  </AbsoluteFill>;
};

/** Portal: glowing energy ring around the whole speaker (cổng không gian); back half behind the speaker. */
export const Portal: React.FC<P> = ({duration, x = 0.4, y = 0.5, rx = 0.36, ry = 0.3, half = 'front', color = T('#5B8BFF')}) => {
  const {frame, fps, t, W, H} = useT();
  const g = lerp(t, 0, 0.5, 0, 1, EASE_IN) * exit(frame, fps, duration);
  return <AbsoluteFill style={{opacity: g}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      <defs><filter id="pg"><feGaussianBlur stdDeviation="14" /></filter></defs>
      {Array.from({length: 96}).map((_, i) => {
        const a0 = (i / 96) * Math.PI * 2, a1 = ((i + 1.1) / 96) * Math.PI * 2;
        const back = Math.sin((a0 + a1) / 2) < 0 && Math.cos((a0 + a1) / 2) > -2;
        const isBack = Math.cos((a0 + a1) / 2) * 0 + Math.sin((a0 + a1) / 2) < -0.2;
        if ((half === 'back') !== isBack && half !== 'all') return null;
        const flick = 0.7 + 0.3 * Math.sin(t * 20 + i);
        const d = `M ${(x + Math.cos(a0) * rx * g) * W} ${(y + Math.sin(a0) * ry * g) * H} L ${(x + Math.cos(a1) * rx * g) * W} ${(y + Math.sin(a1) * ry * g) * H}`;
        return <g key={i} opacity={back ? 1 : 1}><path d={d} stroke={color} strokeWidth={70} opacity={0.6 * flick} filter="url(#pg)" /><path d={d} stroke={T("#E6EEFF")} strokeWidth={16} opacity={flick} /></g>;
      })}
      {Array.from({length: 26}).map((_, i) => {
        const a = random(`s${i}`) * Math.PI * 2 + t * 3, life = (t * 2 + random(`l${i}`)) % 1;
        const isBack = Math.sin(a) < -0.2;
        if ((half === 'back') !== isBack && half !== 'all') return null;
        const r = 1 + life * 0.25;
        return <circle key={`p${i}`} cx={(x + Math.cos(a) * rx * r * g) * W} cy={(y + Math.sin(a) * ry * r * g) * H} r={6 * (1 - life)} fill={T("#fff")} opacity={1 - life} />;
      })}
    </svg>
  </AbsoluteFill>;
};

/** Shockwave: rings blast out from a point (sóng xung kích). */
export const Shockwave: React.FC<P> = ({duration, x = 0.5, y = 0.3, at = 0, color = T('#FFFFFF')}) => {
  const {t, W, H} = useT();
  return <AbsoluteFill>
    {[0, 0.12, 0.24].map((d, i) => {
      const g = lerp(t, at + d, at + d + 0.7, 0, 1, EASE_IN);
      if (g <= 0 || g >= 1) return null;
      const r = g * Math.hypot(W, H) * 0.6;
      return <div key={i} style={{position: 'absolute', left: x * W - r, top: y * H - r, width: r * 2, height: r * 2, borderRadius: '50%', border: `${(1 - g) * 60 + 8}px solid ${color}`,
        opacity: (1 - g) * 0.85, boxShadow: `0 0 40px ${color}`, filter: 'blur(1px)'}} />;
    })}
  </AbsoluteFill>;
};

/** Cracks: glass cracks spread from an impact point (kính vỡ). */
export const Cracks: React.FC<P> = ({duration, x = 0.4, y = 0.3, at = 0}) => {
  const {frame, fps, t, W, H} = useT();
  const g = lerp(t, at, at + 0.25, 0, 1, EASE_OUT);
  const o = exit(frame, fps, duration);
  const rays = Array.from({length: 11}).map((_, i) => {
    const a = (i / 11) * Math.PI * 2 + random(`a${i}`) * 0.5;
    const pts: string[] = [];
    let px = x * W, py = y * H;
    pts.push(`${px},${py}`);
    for (let k = 1; k <= 5; k++) {
      const L = (Math.hypot(W, H) * 0.16) * (0.6 + random(`l${i}${k}`) * 0.8);
      px += Math.cos(a + (random(`j${i}${k}`) - 0.5) * 0.6) * L;
      py += Math.sin(a + (random(`j${i}${k}`) - 0.5) * 0.6) * L;
      pts.push(`${px},${py}`);
    }
    return pts.join(' ');
  });
  return <AbsoluteFill style={{opacity: o}}>
    <svg width={W} height={H}>
      {rays.map((p, i) => <polyline key={i} points={p} fill="none" stroke={T("#fff")} strokeWidth={3} strokeOpacity={0.9} pathLength={1} strokeDasharray="1" strokeDashoffset={1 - g} />)}
      {[0.06, 0.14, 0.24].map((r, i) => <circle key={i} cx={x * W} cy={y * H} r={r * W * g} fill="none" stroke={T("#fff")} strokeWidth={2} strokeOpacity={0.55} strokeDasharray="30 18" />)}
    </svg>
  </AbsoluteFill>;
};

// ================================================================ frames for video windows (pair with frost "solid" + window)
/** PhoneFrame: phone bezel around a window (frost mode "solid" + window at the same place); side icons like Reels. */
export const PhoneFrame: React.FC<P> = ({duration, x = 0.5, y = 0.5, w = 0.62, h = 0.66, icons = true}) => {
  const {frame, fps, W, H} = useT();
  const s = pop(frame, fps, 0, 15);
  const o = exit(frame, fps, duration);
  const pw = w * W, ph = h * H;
  return <At x={x} y={y} style={{opacity: o, transform: `translate(-50%,-50%) scale(${0.9 + 0.1 * s})`}}>
    <div style={{width: pw, height: ph, borderRadius: pw * 0.13, border: `${pw * 0.035}px solid ${T('#121420')}`, boxShadow: T('0 30px 80px rgba(0,0,0,0.45)'), position: 'relative'}}>
      <div style={{position: 'absolute', left: '50%', top: pw * 0.03, transform: 'translateX(-50%)', width: pw * 0.3, height: pw * 0.075, borderRadius: 40, background: T('#121420')}} />
      {icons ? <div style={{position: 'absolute', right: pw * 0.05, bottom: ph * 0.18, display: 'flex', flexDirection: 'column', gap: pw * 0.05}}>
        {['♥', '💬', '↗'].map((c, i) => <div key={i} style={{width: pw * 0.11, height: pw * 0.11, borderRadius: '50%', background: T('rgba(255,255,255,0.85)'), display: 'grid', placeItems: 'center', fontSize: pw * 0.05}}>{c}</div>)}
      </div> : null}
    </div>
  </At>;
};

/** VideoCard: player chrome over a window — title above, ▶ time and progress bar under. */
export const VideoCard: React.FC<P> = ({duration, title = 'thẻ video', x = 0.5, y = 0.5, w = 0.74, h = 0.6, total = '0:21', start = 12}) => {
  const {frame, fps, t, W, H} = useT();
  const o = exit(frame, fps, duration) * enter(frame, fps, 0);
  const cur = start + t;
  const tot = total.split(':').reduce((a: number, b: string) => a * 60 + Number(b), 0);
  return <At x={x} y={y} style={{opacity: o, width: w * W, height: h * H}}>
    <div style={{position: 'absolute', top: -70, left: 0, right: 0, textAlign: 'center', fontFamily: SANS, fontWeight: 800, fontSize: 40, color: C.ink}}>{title}</div>
    <div style={{position: 'absolute', left: 30, right: 30, bottom: 36, fontFamily: MONO, color: T('#fff'), fontSize: 26, textShadow: SHADOW_TEXT}}>
      ▶ {Math.floor(cur / 60)}:{String(Math.floor(cur % 60)).padStart(2, '0')} / {total}
      <div style={{marginTop: 12, height: 6, borderRadius: 3, background: T('rgba(255,255,255,0.4)')}}><div style={{width: `${Math.min(100, (cur / tot) * 100)}%`, height: '100%', borderRadius: 3, background: T('#fff'), position: 'relative'}}>
        <div style={{position: 'absolute', right: -9, top: -6, width: 18, height: 18, borderRadius: '50%', background: T('#fff')}} /></div></div>
    </div>
  </At>;
};

export const VIP_COMPS: Record<string, React.FC<any>> = {
  Stamp, KineticTitle, GravityText, GiantCaption, SplitFlap, Highlighter, CircleDraw, Cursor, FloatButton, IncomingCall, TypeBar, FileDrop,
  FocusBrackets, ChapterPanel, NotifyStack, ChatBubbles, CommentsDrop, BarChart, EditTimeline, JiggleChips, Eyedropper, CompareHandle, VhsHud,
  NumberList, VsCards, Callouts, CountUp, IconSlam, OrbitIcons, ScanLines, CardStack, Polaroids, PostWall, Newspaper, TearAway, BlowAway,
  InkSpread, TitleCard, Intertitle, ScriptPage, CodeLayer, OrbitRing, Portal, Shockwave, Cracks, PhoneFrame, VideoCard,
};
