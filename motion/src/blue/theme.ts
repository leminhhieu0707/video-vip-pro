// Blue style pack — design tokens, fonts and motion helpers.
import {loadFont} from '@remotion/fonts';
import {Easing, getInputProps, interpolate, staticFile} from 'remotion';

const fonts: Array<[string, string, string, string]> = [
  ['BVP', 'fonts/BeVietnamPro-Medium.ttf', '500', 'normal'],
  ['BVP', 'fonts/BeVietnamPro-SemiBold.ttf', '600', 'normal'],
  ['BVP', 'fonts/BeVietnamPro-Bold.ttf', '700', 'normal'],
  ['BVP', 'fonts/BeVietnamPro-ExtraBold.ttf', '800', 'normal'],
  ['PFI', 'fonts/PlayfairDisplay-Italic-VF.ttf', '400 900', 'italic'],
  ['DSC', 'fonts/DancingScript-VF.ttf', '400 700', 'normal'],  // handwriting (OFL), Vietnamese
];
for (const [family, file, weight, style] of fonts) {
  loadFont({family, url: staticFile(file), weight, style}).catch(() => undefined);
}


// ------------------------------------------------------------------ brand colour (plan "theme")
// Everything is designed in a reference blue; scripts/theme.py puts {primary, dark} into props.theme and T()
// re-maps every blue-ish colour (hex or rgba, also inside gradients) to it. Keep mapRGB identical to theme.py.
type Th = {primary: string; dark: string} | null;
const TH: Th = (() => {
  try {
    const t = (getInputProps() as {theme?: Th}).theme;
    return t && t.primary && t.dark ? t : null;
  } catch {
    return null;
  }
})();
const hex2rgb = (h: string): [number, number, number] => {
  let x = h.replace('#', '');
  if (x.length === 3) x = x.split('').map((c) => c + c).join('');
  return [0, 2, 4].map((i) => parseInt(x.slice(i, i + 2), 16) / 255) as [number, number, number];
};
const rgb2hls = (r: number, g: number, b: number): [number, number, number] => {
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx === mn) return [0, l, 0];
  const d = mx - mn, s = l <= 0.5 ? d / (mx + mn) : d / (2 - mx - mn);
  let h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [(h * 60) % 360, l, s];
};
const hls2rgb = (h: number, l: number, s: number): [number, number, number] => {
  if (s === 0) return [l, l, l];
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const f = (t: number) => {
    t = ((t % 1) + 1) % 1;
    return t < 1 / 6 ? p + (q - p) * 6 * t : t < 0.5 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p;
  };
  const hh = h / 360;
  return [f(hh + 1 / 3), f(hh), f(hh - 1 / 3)];
};
const hlsOf = (hx: string) => rgb2hls(...hex2rgb(hx));
const REF = hlsOf('#3158FF'), REFD = hlsOf('#0E1530');
export function mapRGB(r: number, g: number, b: number, th: Th = TH): [number, number, number] {
  if (!th) return [r, g, b];
  const [h, l, s] = rgb2hls(r, g, b);
  if (s < 0.12 || h < 195 || h > 265) return [r, g, b];
  const [ph, pl, ps] = hlsOf(th.primary), [dh, dl, ds] = hlsOf(th.dark);
  let nh, nl, ns;
  if (l >= 0.32) {
    nh = ph + (h - 229) * 0.4;
    ns = Math.min(1, (s * ps) / REF[2]);
    const w = Math.max(0, 1 - Math.abs(l - REF[1]) / 0.36);
    nl = Math.min(0.98, Math.max(0, l + (pl - REF[1]) * w));
  } else {
    nh = dh + (h - 228) * 0.3;
    ns = Math.min(1, s * (REFD[2] ? ds / REFD[2] : 0), ds + 0.1);
    nl = Math.max(0, Math.min(0.45, l + (dl - REFD[1]) * 0.8));
  }
  return hls2rgb(((nh % 360) + 360) % 360, nl, ns);
}
const to255 = (v: number) => Math.max(0, Math.min(255, Math.round(v * 255)));
const CACHE = new Map<string, string>();
/** Theme a colour string — a bare colour, or any CSS value containing #hex / rgb() / rgba() (gradients, shadows). */
export function T(css: string): string;
export function T(css: string | undefined): string | undefined;
export function T(css: string | undefined): string | undefined {
  if (!TH || !css || typeof css !== 'string') return css;
  const hit = CACHE.get(css);
  if (hit !== undefined) return hit;
  const out = css
    .replace(/#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b/g, (m) => {
      const [r, g, b] = mapRGB(...hex2rgb(m));
      return '#' + [r, g, b].map((v) => to255(v).toString(16).padStart(2, '0')).join('').toUpperCase();
    })
    .replace(/rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(,\s*[\d.]+\s*)?\)/g, (_m, r, g, b, a) => {
      const [nr, ng, nb] = mapRGB(+r / 255, +g / 255, +b / 255);
      return a ? `rgba(${to255(nr)},${to255(ng)},${to255(nb)}${a.replace(/\s/g, '')})` : `rgb(${to255(nr)},${to255(ng)},${to255(nb)})`;
    });
  CACHE.set(css, out);
  return out;
}

export const SANS = 'BVP, "Segoe UI", sans-serif';
export const SERIF = 'PFI, Georgia, serif';

export const C = {
  blue: T('#3158FF'),
  blue2: T('#8EB3FF'),
  navy: T('#1C2A6B'),
  navy2: T('#4A5FB8'),
  white: T('#FFFFFF'),
  ink: T('#0E1530'),
  glass: T('rgba(255,255,255,0.82)'),
  glassBorder: T('rgba(255,255,255,0.9)'),
};

// keep the light end readable on bright rooms: blue → periwinkle, not pastel
export const GRAD = `linear-gradient(95deg, ${T('#2448F5')} 0%, ${C.blue} 40%, ${T('#6E92FF')} 100%)`;
// keywords over live footage: near-white with a blue glow, readable on any shirt colour (red, black, white)
export const GRAD_ONVIDEO = T('linear-gradient(95deg, #FFFFFF 0%, #E4ECFF 45%, #B4CBFF 100%)');
export const GLOW_ONVIDEO = T('drop-shadow(0 3px 10px rgba(0,0,0,0.55)) drop-shadow(0 0 20px rgba(60,100,255,0.7))');
export const GRAD_NAVY = `linear-gradient(95deg, ${C.navy} 0%, ${C.navy2} 100%)`;
export const GRAD_WHITE = T('linear-gradient(180deg, #FFFFFF 30%, #C9DAFF 100%)');
export const SHADOW_TEXT = T('0 2px 18px rgba(0,0,0,0.35), 0 1px 3px rgba(0,0,0,0.25)');
export const SHADOW_CARD = T('0 18px 50px rgba(20,30,80,0.28), 0 2px 8px rgba(20,30,80,0.18)');

// "Premium" motion personality (motion-design skill): 350–500 ms, stagger 80 ms, decelerating entrance
export const EASE_IN = Easing.bezier(0.05, 0.7, 0.1, 1);
export const EASE_OUT = Easing.bezier(0.3, 0, 1, 1);
export const ENTER = 0.42; // seconds
export const STAGGER = 0.08;
export const EXIT = 0.28;

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

/** 0→1 entrance progress for an element appearing at `at` seconds. */
export function enter(frame: number, fps: number, at: number, dur = ENTER) {
  return interpolate(frame, [at * fps, (at + dur) * fps], [0, 1], {...clamp, easing: EASE_IN});
}
/** 1→0 exit factor so everything leaves together at the end of the clip. */
export function exit(frame: number, fps: number, total: number, dur = EXIT) {
  return interpolate(frame, [(total - dur) * fps, total * fps], [1, 0], {...clamp, easing: EASE_OUT});
}
/** Blur-in style: blurred + lower + transparent → sharp. */
export function blurIn(p: number, out = 1, dy = 22, blur = 16): React.CSSProperties {
  return {
    opacity: p * out,
    filter: `blur(${(1 - p) * blur + (1 - out) * 8}px)`,
    transform: `translateY(${(1 - p) * dy}px)`,
  };
}
export const gradText = (bg: string): React.CSSProperties => ({
  backgroundImage: bg,
  WebkitBackgroundClip: 'text',
  backgroundClip: 'text',
  color: 'transparent',
  WebkitTextFillColor: 'transparent',
});
