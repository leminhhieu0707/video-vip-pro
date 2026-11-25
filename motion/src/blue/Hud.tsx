// HUD pack — agency-style full-screen motion-graphics chapters (measured on a top "xây kênh" agency reel, 11/2026).
//   HudChapter: a run of scenes inside one HUD frame (corner brackets, brand label, running timecode, chapter label),
//               titles whose letters fly in scattered and lock into place, a 3D card (browser / phone / REC / clapper /
//               target) holding a screenshot or a B-roll video, floating chips, step pill + progress, marquee row.
//   NeonTunnel: dark neon tunnel (perspective lines rushing past, zig-zag light), a phone card flies in from the
//               vanishing point and swaps B-roll clips; logo + two-tier question on top.
// Both are full-screen (opaque). Brand colour comes from theme.ts (design blue → plan "theme"); NeonTunnel's neon
// keeps its own `color` (default orange) so it contrasts with any brand.
import React from 'react';
import {AbsoluteFill, Img, interpolate, OffthreadVideo, random, Sequence, spring, staticFile} from 'remotion';
import {EASE_IN, EASE_OUT, exit, SANS, SERIF, T} from './theme';
import {CL, lerp, P, useT} from './Vip';

const MONO = 'Consolas, "Cascadia Mono", "Courier New", monospace';
const SCRIPT = 'DSC, "Dancing Script", cursive';
const isVid = (s?: string) => !!s && /\.(mp4|mov|webm|m4v)$/i.test(s);
const isImg = (s?: string) => !!s && /\.(png|jpe?g|webp|svg|gif)$/i.test(s);
const url = (s: string) => (s.startsWith('http') ? s : staticFile(s));

/** Screenshot, B-roll video (plays from the moment the card appears, muted) or a soft placeholder. */
const Media: React.FC<{s?: string; style?: React.CSSProperties}> = ({s, style}) => {
  const st: React.CSSProperties = {width: '100%', height: '100%', objectFit: 'cover', display: 'block', ...style};
  if (isVid(s)) return <OffthreadVideo src={url(s!)} muted style={st} />;
  if (isImg(s)) return <Img src={url(s!)} style={st} />;
  return <div style={{...st, background: T('linear-gradient(160deg,#c9d6ff,#6E92FF)')}} />;
};

const tc = (sec: number, fps: number) => {
  const f = Math.max(0, Math.round(sec * fps));
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(Math.floor(f / (3600 * fps)))}:${p(Math.floor(f / (60 * fps)) % 60)}:${p(Math.floor(f / fps) % 60)}:${p(f % fps)}`;
};

type Tone = 'light' | 'dark' | 'brand';
const PAL: Record<Tone, {bg: string; ink: string; accent: string; soft: string; grid: string}> = {
  light: {bg: T('#EEF2FF'), ink: T('#0E1530'), accent: T('#3158FF'), soft: T('rgba(14,21,48,0.55)'), grid: T('rgba(14,21,48,0.06)')},
  dark: {bg: T('#0B1233'), ink: T('#FFFFFF'), accent: T('#6E92FF'), soft: T('rgba(255,255,255,0.6)'), grid: T('rgba(255,255,255,0.05)')},
  brand: {bg: T('#2A4FF0'), ink: T('#FFFFFF'), accent: T('#0E1530'), soft: T('rgba(255,255,255,0.75)'), grid: T('rgba(255,255,255,0.07)')},
};
const mix = (a: string, b: string, k: number) => (k <= 0 ? a : k >= 1 ? b : `color-mix(in srgb, ${a} ${Math.round((1 - k) * 100)}%, ${b})`);

/**
 * ScatterText: every letter starts somewhere random (offset, spun in 3D, scaled, blurred) and springs into place;
 * `out` (0→1) throws the letters away again. Words never break across lines.
 */
const ScatterText: React.FC<{text: string; at: number; out?: number; size: number; color: string; seed: string;
  spread?: number; weight?: number; box?: string; boxAt?: number}> = ({text, at, out = 0, size, color, seed, spread = 1, weight = 800, box, boxAt}) => {
  const {frame, fps, t} = useT();
  let idx = 0;
  const words = text.split(/\s+/).filter(Boolean);
  const bp = box ? lerp(t, boxAt ?? at + 0.25, (boxAt ?? at + 0.25) + 0.4, 0, 1, EASE_IN) : 0;
  return <div style={{position: 'relative', display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: size * 0.26, lineHeight: 1.02,
    padding: box ? `${size * 0.02}px ${size * 0.2}px` : 0}}>
    {box ? <div style={{position: 'absolute', inset: 0, background: box, transformOrigin: 'left center', transform: `scaleX(${bp * (1 - out)})`,
      borderRadius: size * 0.08}} /> : null}
    {words.map((w, wi) => <span key={wi} style={{display: 'inline-flex', whiteSpace: 'nowrap', position: 'relative'}}>
      {Array.from(w).map((ch) => {
        const i = idx++;
        const r = (k: string) => random(`${seed}${k}${i}`) - 0.5;
        const s = spring({frame: frame - (at + i * 0.022 + (r('d') + 0.5) * 0.12) * fps, fps, config: {damping: 14, stiffness: 150, mass: 0.7}});
        const g = 1 - s + out * 1.4;
        const o = Math.min(1, s * 1.6) * (1 - Math.min(1, out * 1.6));
        return <span key={i} style={{display: 'inline-block', fontFamily: SANS, fontWeight: weight, fontSize: size, color, letterSpacing: '-0.02em',
          opacity: o, filter: `blur(${Math.min(14, g * 10)}px)`,
          transform: `translate3d(${r('x') * 900 * spread * g}px, ${r('y') * 700 * spread * g}px, 0) rotateZ(${r('r') * 120 * g}deg) ` +
            `rotateY(${r('ry') * 160 * g}deg) scale(${1 + r('s') * 1.4 * g})`}}>{ch}</span>;
      })}
    </span>)}
  </div>;
};

const Pill: React.FC<{text: string; bg: string; color: string; size?: number; dot?: string}> = ({text, bg, color, size = 26, dot}) => (
  <div style={{display: 'inline-flex', alignItems: 'center', gap: size * 0.4, padding: `${size * 0.32}px ${size * 0.7}px`, borderRadius: size * 0.35,
    background: bg, color, fontFamily: SANS, fontWeight: 800, fontSize: size, letterSpacing: '0.04em', whiteSpace: 'nowrap',
    boxShadow: '0 10px 30px rgba(0,0,0,0.18)'}}>
    {dot ? <span style={{width: size * 0.42, height: size * 0.42, borderRadius: 99, background: dot}} /> : null}{text}
  </div>
);

const Brackets: React.FC<{color: string; inset: number; len: number; w: number}> = ({color, inset, len, w}) => <>
  {[[0, 0], [1, 0], [0, 1], [1, 1]].map(([rx, ry], i) => <div key={i} style={{position: 'absolute', width: len, height: len,
    [rx ? 'right' : 'left']: inset, [ry ? 'bottom' : 'top']: inset,
    [`border${ry ? 'Bottom' : 'Top'}`]: `${w}px solid ${color}`, [`border${rx ? 'Right' : 'Left'}`]: `${w}px solid ${color}`} as React.CSSProperties} />)}
</>;

/** The card that holds the picture. kind: browser | phone | rec | plain | clap | target | none. */
const Card: React.FC<{kind: string; media?: string; W: number; H: number; u: number; out: number; pal: typeof PAL.light; sub?: string;
  fps: number; frameNo: number; tcStart: number}> = ({kind, media, W, H, u, out, pal, sub, fps, frameNo, tcStart}) => {
  const s = spring({frame: u * fps - 4, fps, config: {damping: 15, stiffness: 120, mass: 0.8}});
  const float = Math.sin(u * 1.6) * 6;
  const ry = interpolate(s, [0, 1], [-38, -9]) + Math.sin(u * 0.9) * 3;
  const o = Math.min(1, s * 1.5) * (1 - out);
  const wrap = (w: number, h: number, inner: React.ReactNode) => <div style={{position: 'absolute', left: W / 2, top: H * 0.6,
    width: w, height: h, transform: `translate(-50%,-50%) perspective(1600px) translateY(${(1 - s) * 260 + float + out * 120}px) rotateY(${ry}deg) ` +
      `rotateX(${(1 - s) * 18 + 4}deg) scale(${(0.72 + 0.28 * s) * (1 - out * 0.25)})`, opacity: o, filter: `blur(${out * 10}px)`}}>
    {inner}
    <div style={{position: 'absolute', left: 0, right: 0, top: '100%', height: h * 0.35, marginTop: 14, transform: 'scaleY(-1)', opacity: 0.18,
      maskImage: 'linear-gradient(to top, #000, transparent 70%)', WebkitMaskImage: 'linear-gradient(to top, #000, transparent 70%)', overflow: 'hidden',
      borderRadius: 26}}>{kind === 'phone' || kind === 'rec' || kind === 'plain' ? <Media s={media} /> : null}</div>
  </div>;
  const shadow = '0 40px 90px rgba(0,0,0,0.35), 0 8px 20px rgba(0,0,0,0.2)';
  if (kind === 'none') return null;
  if (kind === 'browser') {
    const w = W * 0.62, h = w * 0.78;
    return wrap(w, h, <div style={{width: '100%', height: '100%', borderRadius: 22, overflow: 'hidden', background: '#fff', boxShadow: shadow,
      border: '1.5px solid rgba(0,0,0,0.08)', display: 'flex', flexDirection: 'column'}}>
      <div style={{height: 54, display: 'flex', alignItems: 'center', gap: 12, padding: '0 20px', background: '#F4F5F8', borderBottom: '1px solid #E2E4EA'}}>
        {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <span key={c} style={{width: 15, height: 15, borderRadius: 99, background: c}} />)}
        <div style={{flex: 1, height: 28, marginLeft: 16, borderRadius: 8, background: '#E6E8EE'}} />
      </div>
      <div style={{flex: 1, overflow: 'hidden'}}><Media s={media} style={{objectPosition: 'top'}} /></div>
    </div>);
  }
  if (kind === 'phone') {
    const w = W * 0.4, h = w * 1.95;
    return wrap(w, h, <div style={{width: '100%', height: '100%', borderRadius: 54, padding: 12, background: '#111', boxShadow: shadow,
      border: '2px solid rgba(255,255,255,0.18)'}}>
      <div style={{width: '100%', height: '100%', borderRadius: 44, overflow: 'hidden', position: 'relative'}}>
        <Media s={media} />
        <div style={{position: 'absolute', top: 14, left: '50%', transform: 'translateX(-50%)', width: 110, height: 32, borderRadius: 99, background: '#000'}} />
      </div>
    </div>);
  }
  if (kind === 'rec' || kind === 'plain') {
    const w = W * 0.44, h = w * 1.55;
    const blink = Math.floor(u * 2) % 2 === 0;
    return wrap(w, h, <div style={{width: '100%', height: '100%', borderRadius: 30, overflow: 'hidden', position: 'relative', boxShadow: shadow,
      border: '6px solid rgba(255,255,255,0.95)'}}>
      <Media s={media} />
      {kind === 'rec' ? <>
        <div style={{position: 'absolute', inset: 0, background: 'linear-gradient(180deg, rgba(0,0,0,0.35), transparent 22%, transparent 78%, rgba(0,0,0,0.35))'}} />
        <Brackets color="rgba(255,255,255,0.9)" inset={22} len={46} w={4} />
        <div style={{position: 'absolute', top: 34, left: 40, display: 'flex', alignItems: 'center', gap: 10, fontFamily: MONO, fontWeight: 700, fontSize: 26, color: '#fff'}}>
          <span style={{width: 16, height: 16, borderRadius: 99, background: '#FF3B30', opacity: blink ? 1 : 0.25}} />REC</div>
        <div style={{position: 'absolute', top: 34, right: 40, fontFamily: MONO, fontWeight: 700, fontSize: 24, color: '#fff'}}>{tc(tcStart + frameNo / fps, fps).slice(3)}</div>
        <div style={{position: 'absolute', left: '50%', top: '46%', width: 120, height: 120, transform: 'translate(-50%,-50%)', border: '2px solid rgba(255,255,255,0.75)'}} />
        {sub ? <div style={{position: 'absolute', bottom: 34, left: 40, fontFamily: MONO, fontWeight: 700, fontSize: 24, color: '#fff'}}>{sub}</div> : null}
      </> : null}
    </div>);
  }
  if (kind === 'clap') {
    const w = W * 0.56, h = w * 0.62;
    const snap = lerp(u, 0.35, 0.5, -24, 0, EASE_OUT);
    const lines = (sub || 'PROD — STUDIO\nSCENE 01 · TAKE 01').split('\n');
    const stripes = (r: number) => <div style={{height: h * 0.2, borderRadius: 10, background: `repeating-linear-gradient(${r}deg, #111 0 38px, #fff 38px 76px)`,
      border: '4px solid #111'}} />;
    return wrap(w, h, <div style={{width: '100%', height: '100%', filter: 'drop-shadow(0 30px 60px rgba(0,0,0,0.35))'}}>
      <div style={{transformOrigin: '0% 100%', transform: `rotate(${snap}deg)`}}>{stripes(-60)}</div>
      <div style={{marginTop: 8}}>{stripes(60)}</div>
      <div style={{marginTop: 8, height: h * 0.5, borderRadius: 14, background: '#111', padding: '22px 30px', color: '#fff', fontFamily: MONO,
        fontWeight: 700, fontSize: 30, lineHeight: 1.5}}>{lines.map((l, i) => <div key={i}>{l}</div>)}</div>
    </div>);
  }
  if (kind === 'target') {
    const sz = W * 0.56;
    return wrap(sz, sz, <svg viewBox="-100 -100 200 200" width={sz} height={sz} style={{overflow: 'visible'}}>
      <line x1={-98} y1={0} x2={98} y2={0} stroke={pal.ink} strokeWidth={1.4} />
      <line x1={0} y1={-98} x2={0} y2={98} stroke={pal.ink} strokeWidth={1.4} />
      {[80, 52, 30, 12].map((r, i) => <circle key={r} r={r * (0.9 + 0.1 * Math.sin(u * 3 - i))} fill="none" stroke={i % 2 ? pal.accent : pal.ink}
        strokeWidth={i % 2 ? 2.4 : 3.2} strokeDasharray={i % 2 ? '5 5' : undefined} transform={`rotate(${u * (i % 2 ? 40 : -20)})`} />)}
      <circle r={4} fill={pal.accent} />
    </svg>);
  }
  return null;
};

type Scene = {at?: number; kicker?: string; title?: string; title2?: string; box?: boolean; chapter?: string; step?: string; media?: string;
  card?: string; chips?: Array<string | {t: string; at?: number}>; tone?: Tone; sub?: string; script?: string};

/**
 * HudChapter: full-screen agency chapter. props: scenes [{at, title, title2, kicker, script, box, chapter, step, media, card, chips,
 * tone, sub}], brand, footer, tc (timecode start, s), marquee, size (title px, 128). Scene `at` = seconds from the overlay start
 * (defaults: equal split). card defaults: media → "plain", step → "browser". tone defaults rotate light → brand → light → dark.
 */
export const HudChapter: React.FC<P> = ({duration, scenes = [], brand = 'STUDIO', footer = '', tc: tcStart = 0, marquee, size = 128}) => {
  const {frame, fps, t, W, H} = useT();
  const list: Scene[] = scenes.length ? scenes : [{title: 'TIÊU ĐỀ', title2: 'CHƯƠNG MỚI', kicker: 'BƯỚC 01'}];
  const n = list.length;
  const starts = list.map((s, i) => (typeof s.at === 'number' ? s.at : (duration / n) * i));
  const cur = Math.max(0, starts.filter((a) => t >= a).length - 1);
  const rot: Tone[] = ['light', 'brand', 'light', 'dark'];
  const toneOf = (i: number): Tone => list[i].tone || rot[i % rot.length];
  const endOf = (i: number) => (i + 1 < n ? starts[i + 1] : duration);
  // background crossfade into the next scene's tone over the last 0.25 s of each scene
  const nx = Math.min(n - 1, cur + 1);
  const k = cur === nx ? 0 : lerp(t, endOf(cur) - 0.25, endOf(cur), 0, 1, EASE_OUT);
  const pa = PAL[toneOf(cur)], pb = PAL[toneOf(nx)];
  const bg = mix(pa.bg, pb.bg, k), ink = k > 0.5 ? pb.ink : pa.ink, soft = k > 0.5 ? pb.soft : pa.soft, grid = k > 0.5 ? pb.grid : pa.grid;
  const fadeAll = Math.min(enterFade(t), exit(frame, fps, duration, 0.2));
  const steps = list.filter((s) => s.step).length;
  return <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
    <AbsoluteFill style={{backgroundImage: `linear-gradient(${grid} 2px, transparent 2px), linear-gradient(90deg, ${grid} 2px, transparent 2px)`,
      backgroundSize: '72px 72px', backgroundPosition: `${-t * 6}px ${-t * 10}px`}} />
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 45%, transparent 45%, rgba(0,0,0,0.18) 100%)'}} />
    {marquee ? <div style={{position: 'absolute', top: H * 0.84, left: 0, whiteSpace: 'nowrap', fontFamily: SANS, fontWeight: 800, fontSize: 64,
      color: 'transparent', WebkitTextStroke: `2px ${soft}`, opacity: 0.6 * fadeAll, transform: `translateX(${-((t * 140) % 1400)}px)`}}>
      {Array(8).fill(marquee).join('  ✦  ')}</div> : null}
    {list.map((sc, i) => {
      if (i < cur - 0 && i !== cur) return null;
      if (i > cur) return null;
      const a = starts[i], e = endOf(i), u = t - a;
      const out = i + 1 < n ? lerp(t, e - 0.3, e, 0, 1, EASE_OUT) : 0;
      const pal = PAL[toneOf(i)];
      const kind = sc.card || (sc.media ? 'plain' : sc.step ? 'browser' : 'none');
      const ty = kind === 'none' ? 0.4 : 0.2;
      const chips = (sc.chips || []).map((c, ci) => (typeof c === 'string' ? {t: c, at: 0.6 + ci * 0.35} : {at: 0.6 + ci * 0.35, ...c}));
      return <AbsoluteFill key={i}>
        <Sequence from={Math.round(a * fps)} layout="none">
          <Card kind={kind} media={sc.media} W={W} H={H} u={u} out={out} pal={pal} sub={sc.sub} fps={fps} frameNo={frame} tcStart={tcStart} />
        </Sequence>
        <div style={{position: 'absolute', left: 0, right: 0, top: H * ty, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18,
          transform: 'translateY(-50%)', perspective: 1200}}>
          {sc.step || sc.kicker ? <div style={{opacity: lerp(u, 0, 0.3) * (1 - out), transform: `translateY(${(1 - lerp(u, 0, 0.35)) * -30}px)`}}>
            <Pill text={sc.step ? `BƯỚC ${sc.step.replace('/', ' / ')}` : sc.kicker!} bg={pal.ink} color={pal.bg} size={sc.step ? 30 : 26} />
          </div> : null}
          {sc.script ? <div style={{fontFamily: SCRIPT, fontSize: size * 0.5, color: pal.soft, opacity: lerp(u, 0.05, 0.45) * (1 - out),
            marginBottom: -size * 0.15}}>{sc.script}</div> : null}
          {sc.title ? <ScatterText text={sc.title} at={a + 0.05} out={out} size={sc.title.length > 12 ? size * 0.82 : size} color={pal.ink} seed={`t${i}`} /> : null}
          {sc.title2 ? <ScatterText text={sc.title2} at={a + 0.2} out={out} size={sc.title2.length > 12 ? size * 0.82 : size}
            color={sc.box ? '#fff' : pal.accent} seed={`u${i}`} box={sc.box ? T('#3158FF') : undefined} /> : null}
          {sc.kicker && sc.step ? <div style={{fontFamily: SANS, fontWeight: 700, fontSize: 34, color: pal.soft, opacity: lerp(u, 0.5, 0.8) * (1 - out)}}>{sc.kicker}</div> : null}
        </div>
        {chips.map((c, ci) => {
          const p = spring({frame: (u - c.at) * fps, fps, config: {damping: 11, stiffness: 170, mass: 0.6}});
          const left = ci % 2 === 0;
          const y = 0.5 + (ci >> 1) * 0.17 + (left ? 0 : 0.08);
          return <div key={ci} style={{position: 'absolute', top: H * y, [left ? 'left' : 'right']: W * 0.06, opacity: Math.min(1, p * 1.5) * (1 - out),
            transform: `translateY(${Math.sin(u * 2 + ci) * 8}px) scale(${0.5 + 0.5 * p}) rotate(${left ? -4 : 4}deg)`} as React.CSSProperties}>
            <Pill text={c.t} bg="#FFFFFF" color={T('#0E1530')} size={30} dot={T('#3158FF')} />
          </div>;
        })}
        {sc.step && steps > 1 ? <div style={{position: 'absolute', top: H * 0.83, left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: 14,
          opacity: 1 - out}}>
          {Array.from({length: steps}).map((_, si) => {
            const mine = list.slice(0, i + 1).filter((s) => s.step).length - 1;
            const fill = si < mine ? 1 : si === mine ? lerp(u, 0.1, 0.8) : 0;
            return <div key={si} style={{width: 110, height: 8, borderRadius: 9, background: T('rgba(14,21,48,0.12)'), overflow: 'hidden'}}>
              <div style={{width: `${fill * 100}%`, height: '100%', background: pal.accent === T('#0E1530') ? '#fff' : pal.accent}} /></div>;
          })}
        </div> : null}
      </AbsoluteFill>;
    })}
    {/* HUD frame on top of everything */}
    <AbsoluteFill style={{opacity: fadeAll}}>
      <Brackets color={ink} inset={44} len={64} w={4} />
      <div style={{position: 'absolute', top: 92, left: 92, display: 'flex', alignItems: 'center', gap: 12, fontFamily: SANS, fontWeight: 800, fontSize: 26,
        letterSpacing: '0.08em', color: ink}}>{brand.toUpperCase()}<span style={{width: 10, height: 10, borderRadius: 99, background: ink, opacity: 0.6}} /></div>
      <div style={{position: 'absolute', top: 92, right: 92, fontFamily: MONO, fontWeight: 700, fontSize: 28, color: ink}}>{tc(tcStart + t, fps)}</div>
      <div style={{position: 'absolute', bottom: 92, left: 92, fontFamily: SANS, fontWeight: 800, fontSize: 24, letterSpacing: '0.06em', color: ink}}>
        {(list[cur].chapter || '').toUpperCase()}</div>
      <div style={{position: 'absolute', bottom: 92, right: 92, fontFamily: SANS, fontWeight: 800, fontSize: 24, letterSpacing: '0.06em', color: ink}}>
        {String(footer).toUpperCase()}</div>
    </AbsoluteFill>
  </AbsoluteFill>;
};
const enterFade = (t: number) => interpolate(t, [0, 0.15], [0, 1], CL);

/**
 * NeonTunnel: full-screen neon tunnel. props: items [{src, at}] (B-roll / screenshots shown in the flying phone), color
 * ('#FF5A1F'), logo (image), script ("Vậy"), text ("làm thế nào\ncó thể…?"), title (big line under the text, e.g. "VIDEO QUÁ ĐẸP?"),
 * titleAt (s), fly (s, 0.9).
 */
export const NeonTunnel: React.FC<P> = ({duration, items = [], color = '#FF5A1F', logo, script, text, title, titleAt = 0.6, fly = 0.9}) => {
  const {frame, fps, t, W, H} = useT();
  const cx = W / 2, cy = H * 0.52;
  const o = Math.min(enterFade(t), exit(frame, fps, duration, 0.2));
  // vertical lines rushing outward (walls passing)
  const N = 16;
  const vlines = Array.from({length: N}).map((_, k) => {
    const p = (((k / N) + t * 0.35) % 1);
    const d = Math.pow(p, 2.2);
    return {x1: cx - d * W * 0.75, x2: cx + d * W * 0.75, op: Math.min(1, p * 1.6) * 0.85, w: 1 + p * 3};
  });
  const amp = H * (0.2 + 0.025 * Math.sin(t * 3));
  const zig = (dir: number, ph: number) => {
    const pts: string[] = [];
    for (let i = -2; i <= 6; i++) {
      const x = ((i + ((t * 0.4 + ph) % 2)) / 4) * W;
      const y = cy + dir * (i % 2 === 0 ? -amp : amp * 0.35);
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return pts.join(' ');
  };
  const list: Array<{src?: string; at: number}> = (items.length ? items : [{src: undefined, at: 0}]).map((it: any, i: number) =>
    (typeof it === 'string' ? {src: it, at: i === 0 ? 0 : (duration / Math.max(1, items.length)) * i} : {at: 0, ...it}));
  const curI = Math.max(0, list.filter((x) => t >= x.at).length - 1);
  const swapU = t - list[curI].at;
  const flyP = interpolate(t, [0.05, fly], [0, 1], {...CL, easing: (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2)});
  const flip = curI > 0 ? interpolate(swapU, [0, 0.28], [90, 0], {...CL, easing: EASE_IN}) : 0;
  const cardW = W * 0.5, cardH = cardW * 1.78;
  const cardY = interpolate(flyP, [0, 1], [cy, H * 0.66]);
  const glow = (c: string, b: number) => `drop-shadow(0 0 ${b}px ${c}) drop-shadow(0 0 ${b * 2.5}px ${c})`;
  return <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 52%, #1a0d08 0%, #07070B 60%)', opacity: o}}>
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, filter: glow(color, 6)}}>
      {vlines.map((l, i) => <g key={i} opacity={l.op}>
        <line x1={l.x1} y1={0} x2={l.x1} y2={H} stroke={color} strokeWidth={l.w} />
        <line x1={l.x2} y1={0} x2={l.x2} y2={H} stroke={color} strokeWidth={l.w} />
      </g>)}
      <line x1={0} y1={cy} x2={W} y2={cy} stroke={color} strokeWidth={4} />
      <polyline points={zig(1, 0)} fill="none" stroke={color} strokeWidth={5} strokeLinejoin="miter" />
      <polyline points={zig(-1, 1)} fill="none" stroke={color} strokeWidth={3} opacity={0.6} />
      {[[0, 0], [W, 0], [0, H], [W, H]].map(([x, y], i) => <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={color} strokeWidth={1.5} opacity={0.35} />)}
    </svg>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 52%, rgba(0,0,0,0.0) 30%, rgba(0,0,0,0.55) 100%)'}} />
    {logo ? <div style={{position: 'absolute', top: H * 0.1, left: '50%', transform: 'translateX(-50%)', width: W * 0.42, filter: glow('rgba(80,255,120,0.55)', 10),
      opacity: lerp(t, 0, 0.4)}}><Img src={url(logo)} style={{width: '100%', objectFit: 'contain'}} /></div> : null}
    {script || text ? <div style={{position: 'absolute', top: H * (logo ? 0.25 : 0.14), left: 0, right: 0, display: 'flex', justifyContent: 'center',
      alignItems: 'center', gap: 26, opacity: lerp(t, 0.15, 0.5), transform: `translateY(${(1 - lerp(t, 0.15, 0.5)) * 20}px)`}}>
      {script ? <div style={{fontFamily: SERIF, fontStyle: 'italic', fontSize: 120, color: '#fff', textShadow: '0 4px 30px rgba(0,0,0,0.6)'}}>{script}</div> : null}
      {script && text ? <div style={{width: 3, height: 130, background: 'rgba(255,255,255,0.85)'}} /> : null}
      {text ? <div style={{fontFamily: SANS, fontWeight: 600, fontSize: String(text).split('\n').length > 3 ? 40 : 48, lineHeight: 1.3, color: '#fff', whiteSpace: 'pre-line'}}>{text}</div> : null}
    </div> : null}
    {title ? <div style={{position: 'absolute', top: H * (logo ? 0.35 : 0.25), left: 0, right: 0, textAlign: 'center'}}>
      <ScatterText text={title} at={titleAt} size={title.length > 14 ? 88 : 104} color="#FFF4D6" seed="nt" spread={0.6} />
    </div> : null}
    <div style={{position: 'absolute', left: cx, top: cardY, width: cardW, height: cardH,
      transform: `translate(-50%,-50%) perspective(1400px) scale(${0.04 + 0.96 * flyP}) rotateY(${(1 - flyP) * 40 + flip + Math.sin(t * 1.2) * 4}deg)`,
      borderRadius: 40, padding: 10, background: 'linear-gradient(160deg, #d9dde6, #8a8f9c)', boxShadow: `0 0 60px ${color}55, 0 40px 80px rgba(0,0,0,0.6)`}}>
      <div style={{width: '100%', height: '100%', borderRadius: 32, overflow: 'hidden', background: '#000'}}>
        {list.map((it, i) => i === curI ? <Sequence key={i} from={Math.round(it.at * fps)} layout="none"><Media s={it.src} /></Sequence> : null)}
      </div>
    </div>
  </AbsoluteFill>;
};

export const HUD_COMPS: Record<string, React.FC<any>> = {HudChapter, NeonTunnel};
