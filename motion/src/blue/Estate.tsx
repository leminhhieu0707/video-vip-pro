// ESTATE pack — real-estate graphics on real data.
//   GeoMap:     satellite fly-in (Google-Earth style tilt) on mosaics from scripts/geo.py; the site boundary draws with a
//               running light, road routes to amenities draw with distance / time cards, km rings, pins, compass, credit.
//   Building3D: a building extruded from its footprint (bản vẽ): outline draws, floors rise one by one, glass or white
//               finish, the camera orbits. Several blocks = a 3D masterplan.
//   FloorPlan2D: a floor plan draws in 2D (walls, rooms filled with name + m², dimension lines), then tilts into 3D and the
//               walls rise ("2D → 3D").
// All full-screen. Lengths are metres; the 3D comps use a small perspective projector (no WebGL), so they render fast.
import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile} from 'remotion';
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

/**
 * GeoMap: props = geo.py's geomap.json (levels, camera, site, pois, rings, credit, scale) plus cues:
 * site_at (s, when the boundary starts drawing), site_draw (2), site_label, site_sub, routes [{name, at}] (which POI
 * routes draw, when), pins_at (other POIs pop), rings_at, color (lines, gold), camera (override keys {t, u, v, z, tilt}),
 * fill ('rgba(255,201,60,0.18)'), title / title_at (big text on top).
 */
export const GeoMap: React.FC<P> = ({duration, levels = [], camera = [], site = {}, pois = [], rings = [], scale = 1.5, credit = '',
  site_at, site_draw = 2, site_label, site_sub, routes = [], pins_at, rings_at, color = GOLD, fill = 'rgba(255,201,60,0.18)', compass = true}) => {
  const {frame, fps, t, W, H} = useT();
  const cam = camAt(camera.length ? camera : [{t: 0, u: site.u ?? 0.5, v: site.v ?? 0.5, z: 14}], t);
  const k = 256 * scale * Math.pow(2, cam.z); // screen px per mercator unit
  const PW = W * 2.2, PH = H * 2.2; // the tilted plane is bigger than the screen so its edges never show
  const X = (u: number) => PW / 2 + (u - cam.u) * k, Y = (v: number) => PH / 2 + (v - cam.v) * k;
  const o = Math.min(interpolate(t, [0, 0.25], [0, 1], CL), exit(frame, fps, duration, 0.25));
  const counter = `rotateZ(${-cam.rot}deg) rotateX(${-cam.tilt}deg)`; // labels stand up
  const label = (x: number, y: number, p: number, node: React.ReactNode, key: string, dx = 0, dy = 0) => <div key={key} style={{position: 'absolute', left: x, top: y,
    transform: `translate(-50%, -100%) ${counter} translate(${dx}px, ${dy + (1 - p) * 30}px) scale(${0.6 + 0.4 * p})`, transformOrigin: '50% 100%', opacity: Math.min(1, p * 1.5)}}>{node}</div>;
  const card = (a: React.ReactNode, b?: React.ReactNode, big = false) => <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
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
      transform: `perspective(${H * 1.25}px) rotateX(${cam.tilt}deg) rotateZ(${cam.rot}deg)`}}>
      {levels.map((L: any, i: number) => {
        const op = i === 0 ? 1 : interpolate(cam.z, [L.z - 1.4, L.z - 0.8], [0, 1], CL);
        if (op <= 0) return null;
        return <Img key={i} src={url(L.src)} style={{position: 'absolute', left: X(L.u0), top: Y(L.v0), width: L.du * k, height: L.dv * k, opacity: op,
          imageRendering: 'auto'}} />;
      })}
      <div style={{position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 50%, transparent 30%, rgba(5,10,20,0.45) 75%)'}} />
      <svg width={PW} height={PH} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter></defs>
        {rings.map((r: any, i: number) => {
          const p = rings_at == null ? 0 : lerp(t, rings_at + i * 0.25, rings_at + i * 0.25 + 0.7, 0, 1, EASE_IN);
          if (p <= 0) return null;
          return <g key={i} opacity={p * 0.9}>
            <circle cx={X(site.u)} cy={Y(site.v)} r={r.r * k * p} fill="none" stroke="#fff" strokeWidth={3} strokeDasharray="14 12" />
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
        {ring.length && sp > 0 ? <g>
          <polygon points={sd} fill={fill} opacity={lerp(t, (site_at || 0) + site_draw * 0.7, (site_at || 0) + site_draw + 0.4)} />
          <polygon points={sd} fill="none" stroke={color} strokeWidth={7} strokeLinejoin="round" strokeDasharray={`${sl * sp} ${sl}`} filter="url(#glow)" />
          <polygon points={sd} fill="none" stroke="#fff" strokeWidth={5} strokeLinejoin="round" strokeDasharray={`${sl * 0.05} ${sl}`}
            strokeDashoffset={-((sl * (sp < 1 ? sp : 1 + ((t - (site_at || 0) - site_draw) * 0.35) % 1)) % sl)} />
        </g> : null}
      </svg>
      {rings.map((r: any, i: number) => {
        const p = rings_at == null ? 0 : lerp(t, rings_at + i * 0.25 + 0.4, rings_at + i * 0.25 + 0.8);
        return p > 0 ? label(X(site.u), Y(site.v) - r.r * k, p, <div style={{padding: '6px 16px', borderRadius: 99, background: '#fff', color: '#111',
          fontFamily: SANS, fontWeight: 800, fontSize: 26}}>{fmt(r.km, 0)} km</div>, `rl${i}`) : null;
      })}
      {routes.map((rr: any, i: number) => {
        const poi = pois.find((x: any) => x.name === rr.name);
        if (!poi) return null;
        const p = spring({frame: frame - (rr.at + (rr.dur || 1.6) - 0.1) * fps, fps, config: {damping: 12, stiffness: 160, mass: 0.6}});
        return p > 0.01 ? label(X(poi.u), Y(poi.v), p, card(`${poi.icon || '📍'} ${poi.name}`, poi.km ? `${fmt(poi.km)} km · ~${poi.min} phút` : `${fmt(poi.km_air)} km`), `pr${i}`, rr.dx || 0, rr.dy || 0) : null;
      })}
      {pins_at != null ? pois.filter((x: any) => !routes.find((r: any) => r.name === x.name)).map((poi: any, i: number) => {
        const p = spring({frame: frame - (pins_at + i * 0.2) * fps, fps, config: {damping: 12, stiffness: 160, mass: 0.6}});
        return p > 0.01 ? label(X(poi.u), Y(poi.v), p, card(`${poi.icon || '📍'} ${poi.name}`, `cách ${fmt(poi.km_air)} km`), `pp${i}`) : null;
      }) : null}
      {site_label && site_at != null ? (() => {
        const p = spring({frame: frame - (site_at + site_draw * 0.6) * fps, fps, config: {damping: 12, stiffness: 140, mass: 0.7}});
        const top = ring.length ? Math.min(...ring.map((q) => q[1])) : Y(site.v);
        return p > 0.01 ? label(X(site.u), top - 10, p, card(site_label, site_sub, true), 'site') : null;
      })() : null}
    </div>
    {/* haze towards the horizon hides the mosaic edge when tilted (Google-Earth look) */}
    <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(178,204,232,1) 0%, rgba(178,204,232,0.85) 12%, rgba(178,204,232,0) 34%)',
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
 * yaw (deg, 3D view), title, sub, dims (true: overall width / depth dimension lines), dark (false).
 */
export const FloorPlan2D: React.FC<P> = ({duration, rooms = [], wall_h = 2.8, extrude_at = 3.2, yaw = -30, title, sub, dims = true, dark = false}) => {
  const {frame, fps, t, W, H} = useT();
  const R = (rooms.length ? rooms : [{name: 'Phòng khách', pts: [[0, 0], [5, 0], [5, 6], [0, 6]]}, {name: 'Bếp', pts: [[0, 6], [5, 6], [5, 9], [0, 9]]},
    {name: 'Ngủ', pts: [[0, 9], [5, 9], [5, 13], [0, 13]]}]).map((r: any) => ({...r, pts: ccw(r.pts)}));
  const all = R.flatMap((r: any) => r.pts);
  const minx = Math.min(...all.map((p: number[]) => p[0])), maxx = Math.max(...all.map((p: number[]) => p[0]));
  const miny = Math.min(...all.map((p: number[]) => p[1])), maxy = Math.max(...all.map((p: number[]) => p[1]));
  const ext = Math.max(maxx - minx, maxy - miny);
  const e3 = extrude_at == null ? 0 : lerp(t, extrude_at, extrude_at + 1.6, 0, 1, (x) => smooth(x));
  const pitchDeg = 90 - 52 * e3, yawDeg = yaw * e3;
  const view: View = {yaw: (yawDeg * Math.PI) / 180, pitch: (pitchDeg * Math.PI) / 180, dist: ext * 1.3, tx: (minx + maxx) / 2, ty: (miny + maxy) / 2, tz: 0,
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
  const walls = segs.map(([a, b], i) => {
    const q = [P2([a[0], a[1], 0]), P2([b[0], b[1], 0]), P2([b[0], b[1], h]), P2([a[0], a[1], h])];
    const dd = (q[0][2] + q[1][2]) / 2;
    const ex = b[0] - a[0], ey = b[1] - a[1], len = Math.hypot(ex, ey) || 1;
    const lit = 0.8 + 0.2 * Math.abs((ey / len) * cd[0] - (ex / len) * cd[1]);
    return {d: dd, el: <g key={`wl${i}`}>
      {h > 0.05 ? <polygon points={q.map((x) => `${x[0]},${x[1]}`).join(' ')} fill={shade(dark ? '#3A4766' : '#E9EDF4', lit)} fillOpacity={0.42} stroke={ink} strokeWidth={1.2} strokeOpacity={0.5} /> : null}
      <line x1={q[3][0]} y1={q[3][1]} x2={q[2][0]} y2={q[2][1]} stroke={ink} strokeWidth={h > 0.05 ? 5 : 9} strokeLinecap="square"
        strokeDasharray={`${Math.hypot(q[2][0] - q[3][0], q[2][1] - q[3][1]) * wallP} 9999`} />
    </g>};
  }).sort((a, b) => b.d - a.d);
  const labels = R.map((r: any, i: number) => {
    const c = centroid(r.pts);
    const p = P2([c[0], c[1], h * 0.02]);
    const lp = spring({frame: frame - (1.4 + i * 0.18) * fps, fps, config: {damping: 13, stiffness: 160, mass: 0.6}});
    return <div key={`lb${i}`} style={{position: 'absolute', left: p[0], top: p[1], transform: `translate(-50%,-50%) scale(${0.6 + 0.4 * lp})`, opacity: Math.min(1, lp * 1.5),
      textAlign: 'center', fontFamily: SANS, color: ink, whiteSpace: 'nowrap', textShadow: dark ? '0 2px 8px #000' : '0 1px 6px rgba(255,255,255,0.9)'}}>
      <div style={{fontWeight: 800, fontSize: 30}}>{r.name}</div>
      <div style={{fontWeight: 600, fontSize: 24, opacity: 0.75}}>{fmt(polyArea(r.pts))} m²</div>
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

export const ESTATE_COMPS: Record<string, React.FC<any>> = {GeoMap, Building3D, FloorPlan2D};
