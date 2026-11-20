// Rich line: tiny markup → words that blur in one after another.
//   plain        bold white sans
//   **từ khoá**  blue gradient sans
//   _nghiêng_    serif italic
//   [hộp xanh]   white text on a blue pill (kept as one unit)
//   ~navy~       navy gradient sans (for light / frosted backgrounds)
//   ==mark==     bold white on a blue highlight bar (one unit)
//   {kính}       serif italic inside a frosted glass pill (one unit)
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {blurIn, C, enter, exit, GLOW_ONVIDEO, GRAD, GRAD_NAVY, GRAD_ONVIDEO, gradText, SANS, SERIF, SHADOW_TEXT, STAGGER, T} from './theme';

export type Kind = 'plain' | 'grad' | 'serif' | 'pill' | 'navy' | 'mark' | 'glass';
export type Tok = {t: string; k: Kind};

export function parse(src: string = ''): Tok[] {
  const out: Tok[] = [];
  const re = /\*\*(.+?)\*\*|_(.+?)_|\[(.+?)\]|~(.+?)~|==(.+?)==|\{(.+?)\}|([^*_[~={]+)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(src))) {
    const [, g, s, p, n, mk, gl, plain] = m;
    if (p) out.push({t: p, k: 'pill'});
    else if (mk) out.push({t: mk, k: 'mark'});
    else if (gl) out.push({t: gl, k: 'glass'});
    else {
      const k: Kind = g ? 'grad' : s ? 'serif' : n ? 'navy' : 'plain';
      for (const w of (g || s || n || plain || '').split(/\s+/).filter(Boolean)) out.push({t: w, k});
    }
  }
  return out;
}

type Props = {
  text: string;
  size: number;
  at?: number;            // when the first word starts (s)
  times?: number[];       // optional per-word start times (s), e.g. from the transcript
  total: number;          // clip length (s), for the shared exit
  tone?: 'video' | 'light' | 'dark';
  align?: 'center' | 'left';
  stagger?: number;
};

export const Rich: React.FC<Props> = ({text, size, at = 0, times, total, tone = 'video', align = 'center', stagger = STAGGER}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const toks = parse(text);
  const out = exit(frame, fps, total);
  const onLight = tone === 'light';
  return (
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: align === 'left' ? 'flex-start' : 'center',
      alignItems: 'baseline', columnGap: size * 0.24, rowGap: size * 0.05, lineHeight: 1.12}}>
      {toks.map((tk, i) => {
        const p = enter(frame, fps, times?.[i] ?? at + i * stagger);
        const base: React.CSSProperties = {...blurIn(p, out), display: 'inline-block', whiteSpace: 'nowrap',
          letterSpacing: '-0.035em', textShadow: onLight ? 'none' : SHADOW_TEXT};
        if (tk.k === 'serif')
          return <span key={i} style={{...base, fontFamily: SERIF, fontStyle: 'italic', fontWeight: 500,
            fontSize: size * 1.06, letterSpacing: '-0.01em', color: onLight ? C.navy : T('rgba(255,255,255,0.96)')}}>{tk.t}</span>;
        if (tk.k === 'pill')
          return <span key={i} style={{...base, fontFamily: SANS, fontWeight: 800, fontSize: size * 0.92, color: T('#fff'),
            background: `linear-gradient(180deg, ${T('#4C6FFF')}, ${C.blue})`, borderRadius: size * 0.2, padding: `${size * 0.02}px ${size * 0.2}px ${size * 0.06}px`,
            boxShadow: T('0 8px 24px rgba(49,88,255,0.45)'), textShadow: 'none'}}>{tk.t}</span>;
        if (tk.k === 'mark')
          return <span key={i} style={{...base, fontFamily: SANS, fontWeight: 800, fontSize: size, color: T('#fff'), position: 'relative',
            padding: `0 ${size * 0.12}px`, textShadow: T('0 2px 10px rgba(0,0,0,0.35)'),
            backgroundImage: `linear-gradient(transparent 52%, ${T('rgba(49,88,255,0.92)')} 52%, ${T('rgba(49,88,255,0.92)')} 92%, transparent 92%)`,
            backgroundSize: `${Math.min(1, p * 1.4) * 100}% 100%`, backgroundRepeat: 'no-repeat'}}>{tk.t}</span>;
        if (tk.k === 'glass')
          return <span key={i} style={{...base, fontFamily: SERIF, fontStyle: 'italic', fontWeight: 600, fontSize: size * 0.98,
            color: onLight ? C.navy : T('#fff'), background: T('linear-gradient(180deg, rgba(255,255,255,0.34), rgba(150,180,255,0.22))'),
            border: T('2px solid rgba(255,255,255,0.55)'), borderRadius: size * 0.3, padding: `${size * 0.02}px ${size * 0.3}px ${size * 0.08}px`,
            boxShadow: T('0 10px 30px rgba(20,40,120,0.35), inset 0 1px 0 rgba(255,255,255,0.6)'), backdropFilter: 'blur(6px)'}}>{tk.t}</span>;
        const fill = tk.k === 'grad' ? gradText(onLight ? GRAD : GRAD_ONVIDEO)
          : tk.k === 'navy' || onLight ? gradText(GRAD_NAVY) : {color: T('#fff')};
        // gradient text can't carry a text-shadow (it would show through), use drop-shadow filters instead
        const shadow = tk.k !== 'plain' || onLight
          ? {textShadow: 'none', filter: `${base.filter} ${onLight ? '' : tk.k === 'grad' ? GLOW_ONVIDEO : 'drop-shadow(0 2px 10px rgba(0,0,0,0.45))'}`} : {};
        return <span key={i} style={{...base, fontFamily: SANS, fontWeight: 800, fontSize: size, ...fill, ...shadow}}>{tk.t}</span>;
      })}
    </div>
  );
};

/** Small top line (white, medium) that leads into the big line. */
export const TopLine: React.FC<{text: string; size: number; at?: number; total: number; tone?: string; align?: string}> =
  ({text, size, at = 0, total, tone = 'video', align = 'center'}) => {
    const frame = useCurrentFrame();
    const {fps} = useVideoConfig();
    const p = enter(frame, fps, at, 0.36);
    const onLight = tone === 'light';
    return (
      <div style={{...blurIn(p, exit(frame, fps, total), 14, 10), fontFamily: SANS, fontWeight: 600, fontSize: size,
        letterSpacing: '-0.02em', textAlign: align as 'center', color: onLight ? C.navy : T('#fff'),
        textShadow: onLight ? 'none' : SHADOW_TEXT, marginBottom: size * 0.18}}>{text}</div>
    );
  };
