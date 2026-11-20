// Blue style pack — transparent overlays rendered as ProRes 4444 and laid over the edit by render.py.
// Every composition takes: duration (s), x/y (0–1 centre), scale, plus its own content props.
import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Rich, TopLine} from './Rich';
import {blurIn, C, EASE_IN, enter, exit, GRAD, GRAD_WHITE, gradText, SANS, SHADOW_CARD, SHADOW_TEXT, T} from './theme';

export type Base = {duration: number; x?: number; y?: number; scale?: number; width?: number; height?: number};

const isFile = (s?: string) => !!s && /\.(png|jpe?g|webp|svg|gif)$/i.test(s);

/** Positions children so their centre sits at (x, y) of the frame. */
const Place: React.FC<{x?: number; y?: number; scale?: number; maxW?: number; children: React.ReactNode; align?: 'center' | 'left'}> =
  ({x = 0.5, y = 0.5, scale = 1, maxW = 0.88, children, align = 'center'}) => {
    const {width, height} = useVideoConfig();
    return (
      <AbsoluteFill>
        <div style={{position: 'absolute', left: x * width, top: y * height, width: maxW * width,
          transform: `translate(${align === 'left' ? 0 : -50}%, -50%) scale(${scale})`, transformOrigin: align === 'left' ? 'left center' : 'center',
          textAlign: align}}>
          {children}
        </div>
      </AbsoluteFill>
    );
  };

// ------------------------------------------------------------------ 1. BlueText: 2-tier caption
export type BlueTextProps = Base & {top?: string; text: string; size?: number; topSize?: number; times?: number[];
  topAt?: number; textAt?: number; align?: 'center' | 'left'; tone?: 'video' | 'light'};
export const BlueText: React.FC<BlueTextProps> = ({duration, x, y = 0.66, scale, top, text, size = 92, topSize = 42,
  times, topAt = 0, textAt, align = 'center', tone = 'video'}) => (
  <Place x={x ?? (align === 'left' ? 0.08 : 0.5)} y={y} scale={scale} align={align}>
    {top ? <TopLine text={top} size={topSize} at={topAt} total={duration} align={align} tone={tone} /> : null}
    <Rich text={text} size={size} at={textAt ?? (top ? 0.22 : 0)} times={times} total={duration} align={align} tone={tone} />
  </Place>
);

// ------------------------------------------------------------------ 2. BlueBig: headline on a frosted scene
export type BlueBigProps = Base & {top?: string; text: string; sub?: string; tone?: 'light' | 'dark'; size?: number};
export const BlueBig: React.FC<BlueBigProps> = ({duration, x, y = 0.42, scale, top, text, sub, tone = 'light', size = 150}) => {
  const tn = tone === 'light' ? 'light' : 'video';
  return (
    <Place x={x} y={y} scale={scale}>
      {top ? <TopLine text={top} size={size * 0.3} total={duration} tone={tn} /> : null}
      <Rich text={text} size={size} at={top ? 0.25 : 0} total={duration} tone={tn} stagger={0.1} />
      {sub ? <div style={{marginTop: size * 0.08}}><Rich text={sub} size={size * 0.5} at={Math.min(0.75, duration * 0.28)} total={duration} tone={tn} /></div> : null}
    </Place>
  );
};

// ------------------------------------------------------------------ 3. Tiles: glass app/icon tiles with labels + optional rank badges
export type Tile = {icon: string; label?: string; badge?: string; badgeAt?: number; at?: number};
export type TilesProps = Base & {items: Tile[]; size?: number; gap?: number; tone?: 'video' | 'light'};
export const Tiles: React.FC<TilesProps> = ({duration, x, y = 0.15, scale, items = [], size = 190, gap = 64, tone = 'video'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const out = exit(frame, fps, duration);
  return (
    <Place x={x} y={y} scale={scale} maxW={0.96}>
      <div style={{display: 'flex', justifyContent: 'center', gap, alignItems: 'flex-start'}}>
        {items.map((it, i) => {
          const at = it.at ?? i * 0.12;
          const s = spring({frame: frame - at * fps, fps, config: {damping: 14, stiffness: 170, mass: 0.7}});
          const p = enter(frame, fps, at, 0.3);
          const b = it.badge ? enter(frame, fps, it.badgeAt ?? at + 0.4, 0.35) : 0;
          return (
            <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: size * 0.1,
              opacity: p * out, filter: `blur(${(1 - p) * 10 + (1 - out) * 6}px)`, transform: `scale(${0.7 + 0.3 * s})`}}>
              <div style={{width: size, height: size, borderRadius: size * 0.24, background: T('linear-gradient(160deg,#FFFFFF,#EEF2FF)'),
                border: T('2px solid rgba(255,255,255,0.95)'), boxShadow: SHADOW_CARD, display: 'grid', placeItems: 'center'}}>
                {isFile(it.icon)
                  ? <Img src={staticFile(it.icon)} style={{width: size * 0.62, height: size * 0.62, objectFit: 'contain'}} />
                  : <span style={{fontSize: size * 0.52, lineHeight: 1}}>{it.icon}</span>}
              </div>
              {it.label ? <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 0.21, color: tone === 'light' ? C.navy : T('#fff'),
                textShadow: tone === 'light' ? T('0 1px 8px rgba(255,255,255,0.9)') : SHADOW_TEXT,
                letterSpacing: '-0.02em', whiteSpace: 'nowrap'}}>{it.label}</div> : null}
              {it.badge ? <div style={{opacity: b, transform: `translateY(${(1 - b) * -20}px)`, minWidth: size * 0.62, padding: `${size * 0.04}px ${size * 0.14}px`,
                borderRadius: size * 0.12, background: T('rgba(255,255,255,0.92)'), boxShadow: SHADOW_CARD, textAlign: 'center',
                fontFamily: SANS, fontWeight: 800, fontSize: size * 0.42, lineHeight: 1.1, ...gradText(GRAD)}}>{it.badge}</div> : null}
            </div>
          );
        })}
      </div>
    </Place>
  );
};

// ------------------------------------------------------------------ 4. Checklist: ticks that appear as each point is said
export type ChecklistProps = Base & {items: Array<{t: string; at?: number}>; size?: number; tone?: 'video' | 'light'};
export const Checklist: React.FC<ChecklistProps> = ({duration, x = 0.08, y = 0.2, scale, items = [], size = 56, tone = 'video'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const out = exit(frame, fps, duration);
  return (
    <Place x={x} y={y} scale={scale} align="left" maxW={0.86}>
      <div style={{display: 'flex', flexDirection: 'column', gap: size * 0.38}}>
        {items.map((it, i) => {
          const at = it.at ?? i * 0.5;
          const p = enter(frame, fps, at);
          const tick = enter(frame, fps, at + 0.12, 0.3);
          return (
            <div key={i} style={{display: 'flex', alignItems: 'center', gap: size * 0.32, ...blurIn(p, out, 0, 12),
              transform: `translateX(${(1 - p) * -30}px)`}}>
              <svg width={size * 0.9} height={size * 0.9} viewBox="0 0 24 24" style={{flex: 'none', filter: T('drop-shadow(0 3px 8px rgba(0,0,0,0.3))')}}>
                <circle cx="12" cy="12" r="11" fill={T("#fff")} />
                <circle cx="12" cy="12" r="11" fill={C.blue} opacity={tick} />
                <path d="M7 12.5l3.2 3.2L17 9" fill="none" stroke={T("#fff")} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"
                  strokeDasharray="16" strokeDashoffset={16 * (1 - tick)} />
              </svg>
              <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size, color: T('#fff'), letterSpacing: '-0.03em', textShadow: SHADOW_TEXT}}>
                <Rich text={it.t} size={size} at={at} total={duration} align="left" stagger={0.04} tone={tone} />
              </div>
            </div>
          );
        })}
      </div>
    </Place>
  );
};

// ------------------------------------------------------------------ 5. ScreenCard: screenshot in a browser frame + title + chips
export type ScreenCardProps = Base & {src: string; url?: string; title?: string; chips?: Array<{t: string; at?: number}>; w?: number};
export const ScreenCard: React.FC<ScreenCardProps> = ({duration, x, y = 0.33, scale, src, url, title, chips = [], w = 0.84}) => {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const out = exit(frame, fps, duration);
  const p = enter(frame, fps, title ? 0.2 : 0, 0.5);
  const push = interpolate(frame, [0, duration * fps], [1, 1.05], {extrapolateRight: 'clamp'});
  const W = w * width;
  return (
    <Place x={x} y={y} scale={scale} maxW={w}>
      {title ? <div style={{marginBottom: 26}}><Rich text={title} size={58} total={duration} tone="light" /></div> : null}
      <div style={{width: W, borderRadius: 26, overflow: 'hidden', background: T('#fff'), boxShadow: SHADOW_CARD,
        border: T('1px solid rgba(20,30,80,0.08)'), opacity: p * out, transform: `translateY(${(1 - p) * 60}px) scale(${0.96 + 0.04 * p})`,
        filter: `blur(${(1 - p) * 10}px)`}}>
        <div style={{height: 54, display: 'flex', alignItems: 'center', gap: 10, padding: '0 20px', background: T('#F4F6FB'),
          borderBottom: T('1px solid #E3E7F2')}}>
          {[T('#FF5F57'), T('#FEBC2E'), T('#28C840')].map((c) => <span key={c} style={{width: 15, height: 15, borderRadius: 99, background: c}} />)}
          {url ? <div style={{marginLeft: 16, flex: 1, height: 32, borderRadius: 9, background: T('#fff'), border: T('1px solid #E3E7F2'),
            fontFamily: SANS, fontWeight: 600, fontSize: 21, color: T('#5B6584'), display: 'flex', alignItems: 'center', padding: '0 14px'}}>{url}</div> : null}
        </div>
        <div style={{overflow: 'hidden', maxHeight: W * 0.62}}>
          <Img src={staticFile(src)} style={{width: '100%', display: 'block', transform: `scale(${push})`, transformOrigin: 'top center'}} />
        </div>
      </div>
      {chips.length ? <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 14, marginTop: -30, position: 'relative'}}>
        {chips.map((c, i) => {
          const cp = enter(frame, fps, c.at ?? 0.6 + i * 0.25, 0.35);
          return <div key={i} style={{...blurIn(cp, out, 16, 8), background: T('#fff'), borderRadius: 14, padding: '10px 20px', boxShadow: SHADOW_CARD,
            fontFamily: SANS, fontWeight: 700, fontSize: 30, color: C.navy, display: 'flex', alignItems: 'center', gap: 10}}>
            <span style={{width: 26, height: 26, borderRadius: 99, background: C.blue, color: T('#fff'), fontSize: 18, display: 'grid', placeItems: 'center'}}>✓</span>{c.t}
          </div>;
        })}
      </div> : null}
    </Place>
  );
};

// ------------------------------------------------------------------ 6. NumberTitle: big gradient number + two lines
export type NumberTitleProps = Base & {n: string; top?: string; text: string; size?: number; tone?: 'blue' | 'white'};
export const NumberTitle: React.FC<NumberTitleProps> = ({duration, x = 0.08, y = 0.17, scale, n, top, text, size = 72, tone = 'blue'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = enter(frame, fps, 0, 0.5);
  const out = exit(frame, fps, duration);
  return (
    <Place x={x} y={y} scale={scale} align="left" maxW={0.9}>
      <div style={{display: 'flex', alignItems: 'center', gap: size * 0.3}}>
        <div style={{fontFamily: SANS, fontWeight: 800, fontSize: size * 2.6, lineHeight: 0.9, letterSpacing: '-0.06em',
          ...gradText(tone === 'white' ? GRAD_WHITE : GRAD), ...blurIn(p, out, 40, 20),
          filter: `blur(${(1 - p) * 20}px) drop-shadow(0 4px 14px ${T('rgba(0,0,0,0.25)')})`}}>{n}</div>
        <div>
          {top ? <TopLine text={top} size={size * 0.52} at={0.15} total={duration} align="left" /> : null}
          <Rich text={text} size={size} at={0.3} total={duration} align="left" />
        </div>
      </div>
    </Place>
  );
};

// ------------------------------------------------------------------ 7. FollowCard: glass profile card, a cursor taps "Theo dõi"
export type FollowCardProps = Base & {name: string; handle?: string; avatar?: string; initial?: string; clickAt?: number;
  follow?: string; followed?: string};
export const FollowCard: React.FC<FollowCardProps> = ({duration, x, y = 0.2, scale = 1.3, name, handle, avatar, initial,
  clickAt = 1.1, follow = 'Theo dõi', followed = 'Đã theo dõi'}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = enter(frame, fps, 0, 0.5);
  const out = exit(frame, fps, duration);
  const cur = interpolate(frame, [(clickAt - 0.7) * fps, clickAt * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_IN});
  const press = interpolate(frame, [clickAt * fps, (clickAt + 0.08) * fps, (clickAt + 0.22) * fps], [1, 0.9, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const done = frame >= (clickAt + 0.06) * fps;
  return (
    <Place x={x} y={y} scale={scale} maxW={0.8}>
      <div style={{position: 'relative', ...blurIn(p, out, 30, 14)}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 22, padding: '24px 28px', borderRadius: 28,
          background: T('linear-gradient(135deg, rgba(40,56,130,0.92), rgba(18,26,70,0.9))'), border: T('1.5px solid rgba(170,190,255,0.45)'),
          boxShadow: T('0 20px 60px rgba(10,16,50,0.5), inset 0 1px 0 rgba(255,255,255,0.18)')}}>
          <div style={{width: 84, height: 84, borderRadius: 99, overflow: 'hidden', flex: 'none', display: 'grid', placeItems: 'center',
            background: GRAD, color: T('#fff'), fontFamily: SANS, fontWeight: 800, fontSize: 40}}>
            {avatar && isFile(avatar) ? <Img src={staticFile(avatar)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /> : (initial || name[0])}
          </div>
          <div style={{flex: 1, minWidth: 0}}>
            <div style={{fontFamily: SANS, fontWeight: 800, fontSize: 40, color: T('#fff'), letterSpacing: '-0.03em', whiteSpace: 'nowrap'}}>{name}</div>
            {handle ? <div style={{fontFamily: SANS, fontWeight: 500, fontSize: 26, color: T('rgba(220,228,255,0.8)')}}>{handle}</div> : null}
          </div>
          <div style={{transform: `scale(${press})`, padding: '14px 26px', borderRadius: 16, fontFamily: SANS, fontWeight: 800, fontSize: 28,
            whiteSpace: 'nowrap', background: done ? T('rgba(255,255,255,0.14)') : T('#fff'), color: done ? T('#fff') : C.navy,
            border: done ? T('1.5px solid rgba(255,255,255,0.4)') : T('1.5px solid #fff')}}>{done ? `✓ ${followed}` : follow}</div>
        </div>
        <svg width="58" height="58" viewBox="0 0 24 24" style={{position: 'absolute', right: 70 - (1 - cur) * 140, bottom: -34 - (1 - cur) * 160,
          opacity: cur > 0 ? Math.min(1, cur * 3) * out : 0, transform: `scale(${press})`, filter: T('drop-shadow(0 4px 10px rgba(0,0,0,0.45))')}}>
          <path d="M5 2l14 10.5-6.2 1.1 3.6 7.2-2.7 1.3-3.6-7.2L5 19.5z" fill={T("#fff")} stroke={T("#111")} strokeWidth="1.2" strokeLinejoin="round" />
        </svg>
      </div>
    </Place>
  );
};
