// VIP Editor — front end. Plain ES module, no build step.
import JASSUB from '/static/vendor/jassub/jassub.es.js';

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const r3 = (x) => Math.round(x * 1000) / 1000;
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

async function api(path, body) {
  const opt = body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: typeof body === 'string' ? body : JSON.stringify(body),
  };
  const r = await fetch(path, opt);
  const j = await r.json();
  if (j && j.ok === false) throw new Error(j.error || 'Lỗi server');
  return j;
}

// ------------------------------------------------------------------ constants
const ASS_TYPES = new Set(['text', 'label', 'title', 'badge', 'price', 'progress']);
const MEDIA_TYPES = new Set(['image', 'video', 'motion']);   // drawn as HTML elements (motion = Remotion .mov)
const MOTION_COMPS = ['BlueText', 'BlueBig', 'Tiles', 'Checklist', 'ScreenCard', 'NumberTitle', 'FollowCard',
  // Blue VIP (motion/src/blue/Vip.tsx)
  'Stamp', 'KineticTitle', 'GravityText', 'GiantCaption', 'SplitFlap', 'Highlighter', 'CircleDraw', 'Cursor', 'FloatButton',
  'IncomingCall', 'TypeBar', 'FileDrop', 'FocusBrackets', 'ChapterPanel', 'NotifyStack', 'ChatBubbles', 'CommentsDrop', 'BarChart',
  'EditTimeline', 'JiggleChips', 'Eyedropper', 'CompareHandle', 'VhsHud', 'NumberList', 'VsCards', 'Callouts', 'CountUp', 'IconSlam',
  'OrbitIcons', 'ScanLines', 'CardStack', 'Polaroids', 'PostWall', 'Newspaper', 'TearAway', 'BlowAway', 'InkSpread', 'TitleCard',
  'Intertitle', 'ScriptPage', 'CodeLayer', 'OrbitRing', 'Portal', 'Shockwave', 'Cracks', 'PhoneFrame', 'VideoCard', 'OrbitCarousel', 'VisionCarousel', 'BarChartRace', 'LineGraph', 'ExplodedStack', 'DeviceSplay', 'ConstellationHub', 'HeadlineWall', 'DoodleStickers', 'NameTag', 'PriceSlash', 'Receipt', 'MapPin', 'DecodeText', 'Countdown', 'EvidenceBoard', 'Audiogram', 'Text3D', 'WeaveText', 'ProjectText', 'MetalText', 'GlassText', 'NeonText', 'WriteOn', 'SliceText', 'WeightPulse', 'DustText', 'PunchWord', 'DocLabel', 'QuoteCard', 'MarqueeRows', 'TrackLabel', 'RiseText', 'MirrorText', 'FocusText', 'Odometer', 'SealBadge', 'CubeFlip', 'RaysTitle', 'InkText', 'RansomText', 'AIChat', 'BeatText', 'HudChapter', 'NeonTunnel', 'GeoMap', 'Building3D', 'FloorPlan2D', 'LotCard', 'GlobeIntro', 'KnockoutText', 'InvertTitle', 'LensFlare', 'TrackedPlot', 'LuxLabel', 'StatTitle', 'StepTimeline', 'CtaChecklist', 'TagLabel', 'PlotSpotlight', 'RunTitle', 'ExplainCanvas', 'WordStack'];
const MOTION_DEF_Y = { BlueText: 0.66, BlueBig: 0.42, Tiles: 0.15, Checklist: 0.2, ScreenCard: 0.33, NumberTitle: 0.17, FollowCard: 0.2 };
const FROST_TINT = { light: 'rgba(238,242,255,0.62)', blue: 'rgba(42,68,200,0.40)', dark: 'rgba(11,16,32,0.45)', white: 'rgba(255,255,255,0.7)', navy: 'rgba(11,30,94,0.86)', solid: 'rgba(238,241,248,1)', none: 'rgba(0,0,0,0)' };
const isTextLike = (o) => ASS_TYPES.has(o.type || 'text') || o.type === 'motion';
const NAMED_POS = {
  top: [0.5, 0.12], upper: [0.5, 0.25], center: [0.5, 0.5], middle: [0.5, 0.5], lower: [0.5, 0.68], bottom: [0.5, 0.86],
  'top-left': [0.22, 0.12], 'top-right': [0.78, 0.12], 'bottom-left': [0.22, 0.86], 'bottom-right': [0.78, 0.86],
  left: [0.25, 0.45], right: [0.75, 0.45],
};
const NAMED = {
  white: '#FFFFFF', black: '#000000', red: '#E53935', yellow: '#FFD600', orange: '#FF8A00', green: '#22C55E',
  blue: '#2563EB', gold: '#F5C542', pink: '#FF4D8D', purple: '#7C3AED', gray: '#9CA3AF', navy: '#0B1F4B', cyan: '#06B6D4',
};
const TYPE_NAME = { text: 'Chữ', label: 'Nhãn giá', title: 'Tiêu đề', badge: 'Badge', price: 'Thẻ giá',
  progress: 'Thanh tiến độ', image: 'Ảnh', video: 'Video', motion: 'Thẻ Blue', frost: 'Mờ kính' };
const TYPE_ICON = { text: 'T', label: '🏷', title: 'H', badge: '◉', price: '₫', progress: '━', image: '🖼', video: '🎞', motion: '✦', frost: '❄' };
const ANIMS = ['', 'blurin', 'pop', 'bounce', 'fade', 'slide-left', 'slide-right', 'slide-up', 'slide-down', 'wipe', 'zoom', 'shake', 'none'];
const MEDIA_ANIMS = ['', 'slide-up', 'slide-down', 'drop', 'slide-left', 'slide-right'];
const XFADES = ['cut', 'fade', 'fadeblack', 'fadewhite', 'dissolve', 'slideleft', 'slideright', 'slideup', 'slidedown',
  'smoothleft', 'smoothright', 'smoothup', 'smoothdown', 'wipeleft', 'wiperight', 'wipeup', 'wipedown', 'circleopen',
  'circleclose', 'radial', 'zoomin', 'pixelize', 'hblur', 'coverleft', 'revealleft', 'fadegrays'];
const GRADES = ['', 'bright', 'vivid', 'warm', 'cool', 'cinematic', 'vintage', 'pastel', 'moody', 'bw'];
const SUB_STYLES = ['tiktok', 'box', 'clean', 'karaoke', 'news', 'minimal'];
const COLOR_KEYS = ['color', 'bg', 'title_bg', 'title_color', 'highlight_bg', 'highlight_color', 'icon_color', 'outline_color', 'track'];
const SUB_COLOR_KEYS = ['color', 'highlight', 'bg', 'outline_color'];
const PALETTE = ['#E11D2E', '#FF4D8D', '#A855F7', '#2563EB', '#06B6D4', '#22C55E', '#84CC16', '#FFD600', '#F5C542', '#FF8A00', '#111111', '#FFFFFF'];

// ------------------------------------------------------------------ state
let ST = null;            // /api/state
let plan = null;          // the plan being edited (relative paths, exactly what gets saved)
let savedJSON = '';
let P = null;             // preview data from /api/preview
let sel = null;           // {k:'ov'|'seg'|'sfx'|'clip'|'music'|'vo'|'subcfg', ...}
let undoStack = [], redoStack = [], lastKey = null, lastKeyT = 0;
let jassub = null;
const fontsLoaded = new Set();
let pps = 40, listFilter = 'all', tlDrag = null;
const video = $('#base');
const stage = $('#stage');

// ------------------------------------------------------------------ utils
function parseTime(t) {
  if (t == null || t === '') return 0;
  if (typeof t === 'number') return t;
  const parts = String(t).split(':').map(Number);
  return parts.reduce((a, b) => a * 60 + b, 0);
}
function fmt(t, short = false) {
  t = Math.max(0, t || 0);
  const m = Math.floor(t / 60), s = t - m * 60;
  return short ? `${m}:${String(Math.floor(s)).padStart(2, '0')}` : `${m}:${s.toFixed(2).padStart(5, '0')}`;
}
const CW = () => (P ? P.canvas.width : 1080);
const CH = () => (P ? P.canvas.height : 1920);
const BASE = () => Math.min(CW(), CH());
const mediaUrl = (src) => '/media?src=' + encodeURIComponent(src);
function normColor(c) {
  if (!c || typeof c !== 'string') return null;
  let s = NAMED[c.toLowerCase()] || c;
  if (!s.startsWith('#')) return null;
  s = s.toUpperCase();
  if (s.length === 4) s = '#' + s[1] + s[1] + s[2] + s[2] + s[3] + s[3];
  return s;
}
function toast(msg, ms = 2600) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add('hidden'), ms);
}
function estWidth(text, size) {
  let w = 0;
  for (const ch of String(text)) w += size * (ch === ' ' ? 0.32 : (ch !== ch.toLowerCase() || /\d/.test(ch)) ? 0.62 : 0.52);
  return w;
}
function resolvePos(pos, def = 'center') {
  pos = pos ?? def;
  let fx, fy;
  if (typeof pos === 'string') [fx, fy] = NAMED_POS[pos] || NAMED_POS[def];
  else[fx, fy] = pos;
  return [fx <= 1 ? fx * CW() : fx, fy <= 1 ? fy * CH() : fy];
}
const ovs = () => (plan.overlays = plan.overlays || []);
const sfxs = () => (plan.sfx = plan.sfx || []);
function clipOff(o) { return o.clip != null && P && P.starts[o.clip] != null ? P.starts[o.clip] : 0; }
function ovRaw(o) {
  const s = parseTime(o.start ?? 0) + clipOff(o);
  let e;
  if (o.end != null) e = parseTime(o.end) + clipOff(o);
  else if (o.duration != null) e = s + parseTime(o.duration);
  else e = MEDIA_TYPES.has(o.type) || o.type === 'frost' ? P.total : s + 3;
  return [s, e];
}
function ovTimes(o) {
  let [s, e] = ovRaw(o);
  if (ASS_TYPES.has(o.type || 'text') && o.clip != null && !o.span && o.clip + 1 < P.starts.length)
    e = Math.min(e, P.starts[o.clip + 1] + 0.04);
  return [s, e];
}
function setOvTimes(o, s, e) {
  const off = clipOff(o);
  o.start = r3(Math.max(0, s) - off);
  if (o.end != null || o.duration == null) o.end = r3(e - off);
  else o.duration = r3(e - s);
}
function defPos(o) { return MEDIA_TYPES.has(o.type) ? 'top-right' : ({ label: 'left', title: 'top' }[o.type] || 'center'); }
function upperOf(o) { return o.uppercase ?? (o.type === 'label' || o.type === 'title'); }

// bounding box of an overlay in canvas pixels {x,y (center), w, h}
function ovBox(o, i, full = false) {
  const W = CW(), b = BASE();
  if (o.type === 'frost' || (o.type === 'motion' && full)) return { x: W / 2, y: CH() / 2, w: W, h: CH() };
  if (o.type === 'motion') {  // where the motion graphic's content sits (props.x / props.y), for picking + dragging
    const pr = o.props || {};
    const left = ['Checklist', 'NumberTitle'].includes(o.comp) || pr.align === 'left';
    const big = o.comp === 'BlueBig' ? 0.24 : o.comp === 'ScreenCard' ? 0.4 : o.comp === 'Tiles' ? 0.14 : 0.13;
    const w = W * (left ? 0.8 : 0.84) * (pr.scale || 1);
    const cx = (pr.x ?? (left ? 0.08 : 0.5)) * W + (left ? w / 2 : 0);
    return { x: cx, y: (pr.y ?? MOTION_DEF_Y[o.comp] ?? 0.5) * CH(), w, h: CH() * big * (pr.scale || 1) };
  }
  const [x, y] = resolvePos(o.pos, defPos(o));
  if (MEDIA_TYPES.has(o.type)) {
    const wf = o.width ?? (o.type === 'image' ? 0.25 : 0.4);
    const w = wf <= 1 ? wf * W : wf;
    const nat = P.sizes[P.abs.overlays[i]] || [];
    const h = nat[0] ? (w * nat[1]) / nat[0] : w * 0.5625;
    return { x, y, w, h };
  }
  const U = (s) => (upperOf(o) ? String(s ?? '').toUpperCase() : String(s ?? ''));
  const t = o.type || 'text';
  if (t === 'label') {
    const tsz = o.title_size ?? b * 0.05, vsz = o.size ?? b * 0.095;
    const title = U(o.title), val = String(o.text ?? '');
    const w = Math.max(estWidth(val, vsz), estWidth(title, tsz)) + vsz * 0.6;
    const th = title ? tsz * 1.25 + tsz * 0.7 : 0, vh = vsz * 1.25 + vsz * 0.56;
    return { x, y: y - th / 2, w, h: vh + th };
  }
  if (t === 'title') {
    const sz = o.size ?? b * 0.08;
    let w = estWidth(U(o.text), sz) + sz * 0.4, h = sz * 1.35, cy = y;
    if (o.highlight) {
      const hs = o.highlight_size ?? sz;
      w = Math.max(w, estWidth(U(o.highlight), hs) + hs * 0.5);
      const extra = hs * 1.3 + hs * 0.44 + 6;
      h += extra; cy = y + extra / 2;
    }
    return { x, y: cy, w, h };
  }
  if (t === 'badge') {
    const sz = o.size ?? b * 0.055;
    return { x, y, w: estWidth(U(o.text), sz) + sz * 0.8 + (o.icon ? sz : 0), h: sz * 2.05 };
  }
  if (t === 'progress') return { x: W / 2, y, w: W, h: (o.height ?? b * 0.011) + 6 };
  if (t === 'price') return { x, y, w: W * 0.62, h: CH() * 0.12 };
  const sz = o.size ?? b * 0.06;
  const lines = U(o.text).split('\n');
  const w = Math.max(...lines.map((l) => estWidth(l, sz))) + (o.bg ? sz * 0.6 : sz * 0.2);
  return { x, y, w, h: sz * 1.3 * lines.length + (o.bg ? sz * 0.6 : 0) };
}
function subBox() {
  const s = plan.subtitles || {};
  const portrait = CH() > CW();
  const [x, y] = resolvePos(s.pos, portrait ? 'lower' : 'bottom');
  const size = s.size ?? BASE() * (portrait ? 0.075 : 0.06);
  return { x, y, w: CW() * 0.84, h: size * 1.6 };
}

// ------------------------------------------------------------------ mutation / undo / save
function pushUndo(snapshot) {
  undoStack.push(snapshot ?? JSON.stringify(plan));
  if (undoStack.length > 200) undoStack.shift();
  redoStack = [];
}
function mutate(fn, key) {
  const now = performance.now();
  if (!(key && key === lastKey && now - lastKeyT < 1500)) pushUndo();
  lastKey = key; lastKeyT = now;
  fn(plan);
  afterChange();
}
function afterChange(refreshMs = 90) {
  updateStatus();
  scheduleRefresh(refreshMs);
  scheduleDraft();
}
function undo() {
  if (!undoStack.length) return toast('Hết bước để hoàn tác');
  redoStack.push(JSON.stringify(plan));
  plan = JSON.parse(undoStack.pop());
  lastKey = null; validateSel(); afterChange(10); renderProps();
}
function redo() {
  if (!redoStack.length) return;
  undoStack.push(JSON.stringify(plan));
  plan = JSON.parse(redoStack.pop());
  lastKey = null; validateSel(); afterChange(10); renderProps();
}
const isDirty = () => JSON.stringify(plan) !== savedJSON;
function updateStatus() {
  const s = $('#status');
  if (isDirty()) { s.textContent = '● Chưa lưu (nháp tự lưu)'; s.classList.add('dirty'); }
  else { s.textContent = '✓ Đã lưu'; s.classList.remove('dirty'); }
  $('#btnUndo').disabled = !undoStack.length;
  $('#btnRedo').disabled = !redoStack.length;
}
let draftT = null;
function scheduleDraft() {
  clearTimeout(draftT);
  // back to the saved state (e.g. after Ctrl+Z) → an empty body tells the server to drop the stale draft
  draftT = setTimeout(() => { api('/api/draft', isDirty() ? JSON.stringify(plan) : '').catch(() => { }); }, 1500);
}
async function save() {
  await api('/api/save', plan);
  savedJSON = JSON.stringify(plan);
  updateStatus();
  toast('Đã lưu plan.json (bản cũ cất trong Lịch sử)');
}
function validateSel() {
  if (!sel) return;
  if (sel.k === 'ov' && !ovs()[sel.i]) sel = null;
  else if (sel.k === 'sfx' && !sfxs()[sel.i]) sel = null;
  else if (sel.k === 'clip' && !plan.clips[sel.i]) sel = null;
}

// ------------------------------------------------------------------ preview refresh
let refreshT = null, refreshing = false, refreshAgain = false;
function scheduleRefresh(ms = 90) { clearTimeout(refreshT); refreshT = setTimeout(refresh, ms); }
async function refresh() {
  if (refreshing) { refreshAgain = true; return; }
  refreshing = true;
  try {
    const np = await api('/api/preview', plan);
    const baseChanged = !P || np.base_v !== P.base_v || np.has_base !== P.has_base;
    const sizeChanged = !P || np.canvas.width !== P.canvas.width || np.canvas.height !== P.canvas.height;
    P = np;
    applyPreview(baseChanged, sizeChanged);
  } catch (e) { toast('Lỗi xem trước: ' + e.message, 5000); }
  refreshing = false;
  if (refreshAgain) { refreshAgain = false; refresh(); }
}
function applyPreview(baseChanged, sizeChanged) {
  if (sizeChanged) layoutStage();
  if (baseChanged) loadBase();
  updateAss();
  syncMediaEls();
  pruneAudio();
  renderList();
  renderTimeline();
  syncPropValues();
  $('#btnBase').classList.toggle('hidden', !(P.has_base && !P.fresh));
  if (P.ass_error) toast('Chữ lỗi: ' + P.ass_error, 5000);
  $('#tlInfo').textContent = `${fmt(P.total)} · ${P.clips.length} cảnh · ${ovs().length} lớp · ${sfxs().length} tiếng` +
    (P.motion_pending ? ` · ✦ đang dựng ${P.motion_pending} thẻ Blue…` : '');
  const errs = Object.values(P.motion_err || {});
  if (errs.length && errs.join() !== applyPreview._err) toast('Thẻ Blue lỗi: ' + errs[0].slice(0, 160), 6000);
  applyPreview._err = errs.join();
  if (P.motion_pending) scheduleRefresh(2500);  // pick the new .mov up as soon as the background render lands
  drawHandles(true);
}

// ------------------------------------------------------------------ base video + libass
function layoutStage() {
  const wrap = $('#stageWrap');
  const k = Math.min((wrap.clientWidth - 30) / CW(), (wrap.clientHeight - 30) / CH());
  stage.style.width = Math.max(50, CW() * k) + 'px';
  stage.style.height = Math.max(50, CH() * k) + 'px';
  drawHandles(true);
}
function loadBase() {
  const msg = $('#stageMsg');
  if (!P.has_base) {
    msg.innerHTML = 'Đang dựng video nền lần đầu (ghép các cảnh, chưa có chữ)…<br><small>Xong sẽ tự hiện, thường mất vài chục giây.</small>';
    msg.classList.remove('hidden');
    pollJob(true);
    return;
  }
  msg.classList.add('hidden');
  const t = video.currentTime || 0;
  video.src = '/base.mp4?v=' + P.base_v;
  video.addEventListener('loadedmetadata', () => {
    video.currentTime = Math.min(t, video.duration || t);
    ensureJassub();
  }, { once: true });
}
function emptyAss() {
  return `[Script Info]\nScriptType: v4.00+\nPlayResX: ${CW()}\nPlayResY: ${CH()}\n\n[V4+ Styles]\n` +
    'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n' +
    'Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1\n\n' +
    '[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n';
}
function ensureJassub() {
  if (jassub || !video.videoWidth || !P) return;
  P.fonts.forEach((f) => fontsLoaded.add(f));
  const v = '/static/vendor/jassub/';
  try {
    jassub = new JASSUB({
      video, subContent: P.ass || emptyAss(),
      workerUrl: v + 'jassub-worker.js', wasmUrl: v + 'jassub-worker.wasm', modernWasmUrl: v + 'jassub-worker-modern.wasm',
      legacyWasmUrl: v + 'jassub-worker.wasm.js', availableFonts: { 'liberation sans': v + 'default.woff2' },
      fallbackFont: 'liberation sans', fonts: P.fonts.map((f) => '/fonts/' + encodeURIComponent(f)),
    });
    setTimeout(forceSubRender, 600);
  } catch (e) { toast('Không chạy được libass: ' + e.message, 6000); }
}
function updateAss() {
  if (!jassub) return ensureJassub();
  for (const f of P.fonts) if (!fontsLoaded.has(f)) { jassub.addFont('/fonts/' + encodeURIComponent(f)); fontsLoaded.add(f); }
  jassub.setTrack(P.ass || emptyAss());
  forceSubRender();
}
function forceSubRender() {
  if (!jassub || !video.videoWidth) return;
  try { jassub._demandRender({ mediaTime: video.currentTime, width: video.videoWidth, height: video.videoHeight }); } catch { }
}

// ------------------------------------------------------------------ image / video overlays (HTML)
const mediaEls = new Map();
function syncMediaEls() {
  const keep = new Set();
  ovs().forEach((o, i) => {
    let src = o.src;
    if (o.type === 'motion') src = P.motion?.[i];
    if (o.type !== 'frost' && (!MEDIA_TYPES.has(o.type) || !src)) return;
    const key = o.type + '|' + (src || '') + '|' + (o.type === 'frost' ? JSON.stringify(o.window || null) : '');
    keep.add(i);
    let m = mediaEls.get(i);
    if (m && m.key !== key) { m.el.remove(); m = null; }
    if (!m) {
      const el = document.createElement('div');
      el.className = 'ov' + (o.type === 'frost' ? ' frost' : '');
      let inner = null;
      if (o.type === 'image') { inner = new Image(); inner.src = mediaUrl(src); inner.draggable = false; }
      else if (o.type === 'frost') { if (o.window) { inner = document.createElement('canvas'); inner.className = 'fwin'; } }
      else { inner = document.createElement('video'); inner.muted = true; inner.playsInline = true; inner.preload = 'auto'; }
      if (inner) el.appendChild(inner);
      $('#media').appendChild(el);
      m = { el, inner, key, src: src ? mediaUrl(src) : null };
      mediaEls.set(i, m);
    }
    m.el.style.zIndex = i + 1;
  });
  for (const [i, m] of mediaEls) if (!keep.has(i)) { m.el.remove(); mediaEls.delete(i); }
}
function drawMedia(t) {
  if (!P) return;
  const W = CW(), H = CH(), playing = !video.paused;
  ovs().forEach((o, i) => {
    const m = mediaEls.get(i);
    if (!m) return;
    const [s, e] = ovTimes(o);
    const isVid = o.type === 'video' || o.type === 'motion';
    if (isVid && !m.inner.src && t > s - 2 && t < e) m.inner.src = m.src;
    const active = t >= s && t < e;
    if (!active) {
      if (m.el.style.display !== 'none') m.el.style.display = 'none';
      if (isVid && !m.inner.paused) m.inner.pause();
      return;
    }
    m.el.style.display = 'block';
    if (o.type === 'frost') { drawFrost(o, m, t, s, e); return; }
    const bx = ovBox(o, i, true);
    if (o.type === 'motion') { o = { ...o, fade: 0, anim: null, in: 0, radius: 0, opacity: 1 }; }
    const dt = t - s;
    let dx = 0, dy = 0;
    const ease = dt < 0.35 ? Math.pow(1 - dt / 0.35, 3) : 0;
    if (o.anim === 'slide-up') dy = H * 0.06 * ease;
    else if (o.anim === 'slide-down') dy = -H * 0.08 * ease;
    else if (o.anim === 'slide-left') dx = W * 0.25 * ease;
    else if (o.anim === 'slide-right') dx = -W * 0.25 * ease;
    else if (o.anim === 'drop' && dt < 0.45) {
      const p = dt / 0.45, eb = 1 + 2.70158 * Math.pow(p - 1, 3) + 1.70158 * Math.pow(p - 1, 2);
      dy = -(bx.y + bx.h) * (1 - eb);
    }
    const fd = o.fade ?? 0.3;
    let op = o.opacity ?? 1;
    if (fd) { op *= Math.min(1, dt / fd); if (e < P.total) op *= Math.min(1, (e - t) / fd); }
    const st = m.el.style;
    st.left = ((bx.x - bx.w / 2 + dx) / W) * 100 + '%';
    st.top = ((bx.y - bx.h / 2 + dy) / H) * 100 + '%';
    st.width = (bx.w / W) * 100 + '%';
    st.height = (bx.h / H) * 100 + '%';
    st.opacity = clamp(op, 0, 1);
    const r = o.radius ? Math.min(o.radius, bx.w / 2 - 1) : 0;
    st.borderRadius = r ? `${(r / bx.w) * 100}% / ${(r / bx.h) * 100}%` : '';
    st.mixBlendMode = o.key && /^#?0{6}/.test(o.key) ? 'screen' : '';
    if (isVid) {
      const v = m.inner;
      let want = parseTime(o.in || 0) + dt;
      if (o.loop && v.duration) want = want % v.duration;
      if (!playing) {
        if (!v.paused) v.pause();
        if (Math.abs(v.currentTime - want) > 0.04 && v.readyState > 0) v.currentTime = want;
      } else if (v.paused) {
        if (v.readyState > 0) v.currentTime = want;
        v.play().catch(() => { });
      } else if (Math.abs(v.currentTime - want) > 0.3) v.currentTime = want;
    }
  });
}

// frosted-glass scene: the browser blurs what's below (base video + earlier overlays), libass text stays on top
function drawFrost(o, m, t, s, e) {
  const st = m.el.style;
  const k = stage.clientWidth / CW();
  const fd = o.fade ?? 0.25;
  let op = fd ? Math.min(1, (t - s) / fd) : 1;
  if (fd && e < P.total) op *= Math.min(1, (e - t) / fd);
  st.left = '0'; st.top = '0'; st.width = '100%'; st.height = '100%';
  st.opacity = clamp(op, 0, 1);
  const blur = (o.blur ?? 36) * k;
  st.backdropFilter = st.webkitBackdropFilter = `blur(${blur.toFixed(1)}px)`;
  st.background = FROST_TINT[o.mode || 'light'] || FROST_TINT.light;
  const w = o.window, cv = m.inner;
  if (w && cv) {  // sharp crop of the base video in a rounded window (split layout)
    const [cx, cy, cw, ch] = w.crop || [0, 0.18, 1, 0.42];
    const ww = w.width ?? 0.8;
    const ow = ww <= 1 ? ww * CW() : ww;
    const oh = ow * (ch * CH()) / (cw * CW());
    const [px, py] = resolvePos(w.pos || [0.5, 0.74]);
    Object.assign(cv.style, { position: 'absolute', left: ((px - ow / 2) / CW()) * 100 + '%', top: ((py - oh / 2) / CH()) * 100 + '%',
      width: (ow / CW()) * 100 + '%', height: (oh / CH()) * 100 + '%', borderRadius: `${(w.radius ?? 40) * k}px` });
    const dw = Math.max(2, Math.round(ow * k)), dh = Math.max(2, Math.round(oh * k));
    if (cv.width !== dw) cv.width = dw;
    if (cv.height !== dh) cv.height = dh;
    if (video.videoWidth) {
      const vw = video.videoWidth, vh = video.videoHeight;
      cv.getContext('2d').drawImage(video, cx * vw, cy * vh, cw * vw, ch * vh, 0, 0, dw, dh);
    }
  }
}

// ------------------------------------------------------------------ audio preview (voice-over, music, sfx)
const audioEls = new Map();
function audioItems() {
  const au = plan.audio || {};
  let vos = au.voiceover || [];
  if (!Array.isArray(vos)) vos = [vos];
  const items = vos.map((v, j) => (v && v.src ? { kind: 'vo', j, v } : null)).filter(Boolean);
  if (au.music && au.music.src) items.push({ kind: 'music', v: au.music });
  return items;
}
function pruneAudio() {
  const keys = new Set(audioItems().map((it) => it.kind + (it.j ?? '') + '|' + it.v.src));
  for (const [k, m] of audioEls) if (!keys.has(k)) { m.a.pause(); audioEls.delete(k); }
}
function syncAudio(t) {
  if (!P) return;
  const sound = $('#chkSound').checked, playing = !video.paused;
  video.muted = !sound;
  video.volume = clamp((plan.audio || {}).original_volume ?? 1, 0, 1);
  for (const it of audioItems()) {
    const key = it.kind + (it.j ?? '') + '|' + it.v.src;
    let m = audioEls.get(key);
    if (!m) { m = { a: new Audio(mediaUrl(it.v.src)) }; m.a.preload = 'auto'; audioEls.set(key, m); }
    const v = it.v;
    let start, inn, len;
    if (it.kind === 'vo') {
      start = parseTime(v.start || 0) + (v.clip != null ? P.starts[v.clip] || 0 : 0);
      inn = parseTime(v.in || 0);
      len = v.out != null ? parseTime(v.out) - inn : Infinity;
    } else {
      start = parseTime(v.start || 0); inn = parseTime(v.in || 0);
      len = (v.end != null ? parseTime(v.end) : P.total) - start;
    }
    const rel = t - start;
    const active = rel >= 0 && rel < len;
    let want = inn + rel;
    if (it.kind === 'music' && m.a.duration) want = inn + (rel % Math.max(0.1, m.a.duration - inn));
    m.a.volume = clamp((v.volume ?? (it.kind === 'music' ? 0.18 : 1)) * (it.kind === 'music' ? 1.6 : 1), 0, 1);
    if (!sound || !playing || !active) { if (!m.a.paused) m.a.pause(); continue; }
    if (m.a.paused) { m.a.currentTime = want; m.a.play().catch(() => { }); }
    else if (Math.abs(m.a.currentTime - want) > 0.25) m.a.currentTime = want;
  }
}
let lastSfxT = 0;
function playSfx(t) {
  if (!P || video.paused || !$('#chkSound').checked || t < lastSfxT || t - lastSfxT > 0.5) { lastSfxT = t; return; }
  for (const s of P.sfx) {
    if (s.at >= lastSfxT && s.at < t) {
      const a = new Audio(mediaUrl(s.src));
      // s.vol is the export gain (already levelled per file); the export also ducks effects ~5 dB under speech,
      // so play at half to sound like the finished video instead of every effect at full blast
      a.volume = clamp(s.vol * 0.5, 0, 1);
      a.play().catch(() => { });
      setTimeout(() => a.pause(), (s.len || 3) * 1000);
    }
  }
  lastSfxT = t;
}

// ------------------------------------------------------------------ frame loop
let lastDrawT = -1;
function tick() {
  const t = video.currentTime || 0;
  drawMedia(t);
  syncAudio(t);
  playSfx(t);
  if (P) {
    $('#tc').textContent = `${fmt(t)} / ${fmt(P.total)}`;
    $('#playhead').style.left = t * pps + 'px';
    if (!video.paused) followPlayhead(t);
  }
  if (Math.abs(t - lastDrawT) > 0.02) { drawHandles(); lastDrawT = t; }
  $('#btnPlay').textContent = video.paused ? '▶' : '❚❚';
  requestAnimationFrame(tick);
}
function followPlayhead(t) {
  const sc = $('#tlScroll'), x = t * pps;
  if (x > sc.scrollLeft + sc.clientWidth - 60 || x < sc.scrollLeft) sc.scrollLeft = x - 80;
}
function seek(t) {
  if (!P) return;
  video.currentTime = clamp(t, 0, Math.max(0, (video.duration || P.total) - 0.01));
  lastSfxT = video.currentTime;
}
function togglePlay() {
  if (!video.src) return;
  if (video.paused) {
    if (video.currentTime >= (video.duration || P.total) - 0.05) seek(0);
    video.play().catch(() => { });
  } else video.pause();
}

// ------------------------------------------------------------------ selection boxes + dragging on the stage
function activeOverlays(t) {
  const out = [];
  ovs().forEach((o, i) => { const [s, e] = ovTimes(o); if (t >= s && t < e) out.push(i); });
  return out;
}
function drawHandles(force) {
  if (!P) return;
  const hd = $('#handles');
  const t = video.currentTime || 0;
  const show = $('#chkBox').checked;
  const W = CW(), H = CH();
  let html = '';
  const box = (b, cls, tag, rs) => `<div class="box ${cls}" style="left:${((b.x - b.w / 2) / W) * 100}%;top:${((b.y - b.h / 2) / H) * 100}%;` +
    `width:${(b.w / W) * 100}%;height:${(b.h / H) * 100}%">${tag ? `<div class="tag">${esc(tag)}</div>` : ''}${rs ? '<div class="rs"></div>' : ''}</div>`;
  for (const i of activeOverlays(t)) {
    const o = ovs()[i];
    const isSel = sel && sel.k === 'ov' && sel.i === i;
    if ((!show && !isSel) || (o.type === 'frost' && !isSel)) continue;
    const pend = o.type === 'motion' && !P.motion?.[i] ? ' · đang dựng…' : '';
    html += box(ovBox(o, i), isSel ? 'sel' : '', isSel ? (o.type === 'motion' ? o.comp : TYPE_NAME[o.type || 'text'] || o.type) + pend : pend.slice(3),
      isSel && (o.type === 'image' || o.type === 'video'));
  }
  if (sel && (sel.k === 'subcfg' || sel.k === 'seg') && plan.subtitles) html += box(subBox(), 'sel', 'Phụ đề');
  if (force || hd._html !== html) { hd.innerHTML = html; hd._html = html; }
}
function stagePoint(ev) {
  const r = stage.getBoundingClientRect();
  return [((ev.clientX - r.left) / r.width) * CW(), ((ev.clientY - r.top) / r.height) * CH()];
}
function hitTest(px, py) {
  const t = video.currentTime || 0;
  const act = activeOverlays(t);
  const inside = (b) => Math.abs(px - b.x) <= b.w / 2 + 8 && Math.abs(py - b.y) <= b.h / 2 + 8;
  // text is drawn above images/videos, so test text first, topmost (last) first
  for (const i of [...act].reverse()) if (isTextLike(ovs()[i]) && inside(ovBox(ovs()[i], i))) return { k: 'ov', i };
  if (plan.subtitles && P.lines.some((l) => t >= l.start && t < l.end) && inside(subBox())) return { k: 'subcfg' };
  let best = null;  // smallest media box under the cursor wins (so a logo on top of a big video is clickable)
  for (const i of act) {
    const o = ovs()[i];
    if (o.type !== 'image' && o.type !== 'video') continue;
    const b = ovBox(o, i);
    if (inside(b) && (!best || b.w * b.h < best.a)) best = { i, a: b.w * b.h };
  }
  return best ? { k: 'ov', i: best.i } : null;
}
$('#handles').addEventListener('pointerdown', (ev) => {
  if (!P) return;
  const [px, py] = stagePoint(ev);
  const resizing = ev.target.classList.contains('rs');
  let target = resizing ? sel : hitTest(px, py);
  if (!target) { select(null); return; }
  if (!sameSel(target, sel)) select(target, false);
  const hd = $('#handles');
  hd.setPointerCapture(ev.pointerId);
  const key = 'stage' + Date.now();
  let start = null;
  if (target.k === 'ov') {
    const o = ovs()[target.i], b = ovBox(o, target.i);
    start = { b, wf: o.width ?? (o.type === 'image' ? 0.25 : 0.4) };
  } else if (target.k === 'subcfg') start = { b: subBox() };
  const ox = start.b.x - px, oy = start.b.y - py;
  const move = (e) => {
    const [mx, my] = stagePoint(e);
    if (resizing && target.k === 'ov') {
      const neww = Math.max(20, Math.abs(mx - start.b.x) * 2);
      const val = start.wf <= 1 ? r3(neww / CW()) : Math.round(neww);
      mutate((p) => { p.overlays[target.i].width = val; }, key);
    } else {
      let nx = (mx + ox) / CW(), ny = (my + oy) / CH();
      if (Math.abs(nx - 0.5) < 0.012) nx = 0.5;  // snap to the vertical centre line
      const pos = [r3(clamp(nx, 0, 1)), r3(clamp(ny, 0, 1))];
      mutate((p) => {
        const o = target.k === 'ov' ? p.overlays[target.i] : null;
        if (o && o.type === 'motion') {  // motion graphics are re-rendered at the new place (a few seconds)
          o.props = o.props || {};
          const left = ['Checklist', 'NumberTitle'].includes(o.comp) || o.props.align === 'left';
          if (!left) o.props.x = pos[0];
          o.props.y = pos[1];
        } else if (o) o.pos = pos;
        else p.subtitles.pos = pos;
      }, key);
    }
    drawHandles(true);
  };
  const up = () => { hd.removeEventListener('pointermove', move); hd.removeEventListener('pointerup', up); renderProps(); };
  hd.addEventListener('pointermove', move);
  hd.addEventListener('pointerup', up);
});
function sameSel(a, b) { return a && b && JSON.stringify(a) === JSON.stringify(b); }

// ------------------------------------------------------------------ selection
function select(s, doSeek = false) {
  sel = s;
  renderProps();
  renderList();
  renderTimeline();
  drawHandles(true);
  if (doSeek && s) {
    const t = selTime(s);
    if (t != null) seek(t + seekPad(s));
  }
}
// land a little after an overlay's start so its entrance animation (pop/fade) has finished
function seekPad(s) {
  if (s.k !== 'ov') return 0.03;
  const [a, b] = ovTimes(ovs()[s.i]);
  return Math.min(0.4, Math.max(0.03, (b - a) / 3));
}
function selTime(s) {
  if (s.k === 'ov') return ovTimes(ovs()[s.i])[0];
  if (s.k === 'sfx') { const x = sfxs()[s.i]; return parseTime(x.at) + clipOff(x); }
  if (s.k === 'clip') return P.starts[s.i];
  if (s.k === 'seg') { const g = P.segments.find((g) => g.ti === s.ti && g.seg === s.seg); return g ? g.start : null; }
  return null;
}

// ------------------------------------------------------------------ left list
const plainMarkup = (s) => String(s || '').replace(/\*\*|[_~[\]]/g, '');
function ovName(o) {
  if (o.type === 'frost') return `Mờ kính · ${o.mode || 'light'}${o.window ? ' · chia đôi' : ''}`;
  if (o.type === 'motion') {
    const pr = o.props || {};
    const txt = [pr.top, pr.text, pr.sub, pr.n, pr.name].filter(Boolean).map(plainMarkup).join(' · ')
      || (pr.items || []).map((x) => plainMarkup(x.label || x.t)).join(' · ');
    return `${o.comp}: ${txt}`;
  }
  if (MEDIA_TYPES.has(o.type)) return (o.src || '').split(/[\\/]/).pop();
  const t = [o.title, o.text, o.highlight].filter(Boolean).join(' · ');
  return t.replace(/\n/g, ' ') || TYPE_NAME[o.type] || o.type;
}
function listEntries() {
  const out = [];
  const f = listFilter;
  if (f === 'all' || f === 'text' || f === 'media') {
    ovs().forEach((o, i) => {
      const isMedia = !isTextLike(o);
      if ((f === 'text' && isMedia) || (f === 'media' && !isMedia)) return;
      const [s, e] = ovTimes(o);
      out.push({ s, sel: { k: 'ov', i }, ic: TYPE_ICON[o.type || 'text'] || '•', name: ovName(o),
        meta: (TYPE_NAME[o.type || 'text'] || o.type) + (o.clip != null ? ` · neo cảnh ${o.clip + 1}` : ''), t: `${fmt(s, true)}–${fmt(e, true)}` });
    });
  }
  if (f === 'sub') {
    if (plan.subtitles) out.push({ s: -1, sel: { k: 'subcfg' }, ic: '⚙', name: 'Cài đặt phụ đề chung', meta: `Kiểu ${plan.subtitles.style || 'tiktok'}`, t: '' });
    for (const g of P.segments) out.push({ s: g.start, sel: { k: 'seg', ti: g.ti, seg: g.seg }, ic: '💬', name: g.text, meta: g.rel, t: fmt(g.start, true) });
  }
  if (f === 'audio' || f === 'all') {
    audioItems().forEach((it) => out.push({ s: f === 'all' ? 1e6 : -1, sel: it.kind === 'vo' ? { k: 'vo', j: it.j } : { k: 'music' },
      ic: it.kind === 'vo' ? '🎙' : '🎵', name: String(it.v.src).split(/[\\/]/).pop(), meta: it.kind === 'vo' ? 'Giọng' : 'Nhạc nền', t: '' }));
  }
  if (f === 'audio') {
    sfxs().forEach((x, i) => { const at = parseTime(x.at) + clipOff(x); out.push({ s: at, sel: { k: 'sfx', i }, ic: '🔊', name: String(x.sfx).split(/[\\/]/).pop(), meta: `Âm lượng ${x.volume ?? 0.3}`, t: fmt(at, true) }); });
  }
  if (f === 'clip') P.clips.forEach((c, i) => out.push({ s: c.start, sel: { k: 'clip', i }, ic: '🎬', name: c.name, meta: `${c.dur.toFixed(2)}s`, t: fmt(c.start, true) }));
  const q = $('#search').value.trim().toLowerCase();
  return out.filter((x) => !q || (x.name + ' ' + x.meta).toLowerCase().includes(q)).sort((a, b) => a.s - b.s);
}
function renderList() {
  if (!P) return;
  const el = $('#list');
  const items = listEntries();
  el.innerHTML = items.map((x, n) => `<div class="item${sameSel(x.sel, sel) ? ' sel' : ''}" data-n="${n}">` +
    `<div class="ic">${x.ic}</div><div class="txt"><div class="name">${esc(x.name)}</div><div class="meta">${esc(x.meta)}</div></div>` +
    `<div class="t">${x.t}</div></div>`).join('') || '<div class="note">Không có mục nào.</div>';
  el.querySelectorAll('.item').forEach((d) => d.addEventListener('click', () => select(items[+d.dataset.n].sel, true)));
  const s = el.querySelector('.item.sel');
  if (s && !el._noScroll) s.scrollIntoView({ block: 'nearest' });
}
$('#listTabs').addEventListener('click', (e) => {
  const b = e.target.closest('button'); if (!b) return;
  listFilter = b.dataset.f;
  document.querySelectorAll('#listTabs button').forEach((x) => x.classList.toggle('on', x === b));
  renderList();
});
$('#search').addEventListener('input', renderList);

// ------------------------------------------------------------------ timeline
function pack(items) {
  const lanes = [];
  for (const it of items.sort((a, b) => a.s - b.s)) {
    let k = lanes.findIndex((end) => end <= it.s + 0.001);
    if (k < 0) { k = lanes.length; lanes.push(0); }
    lanes[k] = it.e;
    it.lane = k;
  }
  return Math.max(1, lanes.length);
}
function renderTimeline() {
  if (!P || tlDrag) return;
  const total = P.total;
  const groups = [];
  groups.push({ label: 'Cảnh', items: P.clips.map((c, i) => ({ s: c.start, e: c.start + c.dur, cls: 'clip', text: c.name, sel: { k: 'clip', i } })) });
  if (P.lines.length) groups.push({ label: 'Phụ đề', items: P.lines.map((l) => ({ s: l.start, e: l.end, cls: 'sub', text: l.text, sel: { k: 'seg', ti: l.ti, seg: l.seg } })) });
  const txt = [], med = [];
  ovs().forEach((o, i) => {
    const [s, e] = ovTimes(o);
    (isTextLike(o) ? txt : med).push({ s, e, cls: o.type || 'text', text: ovName(o), sel: { k: 'ov', i }, drag: true });
  });
  if (txt.length) groups.push({ label: 'Chữ', items: txt });
  if (med.length) groups.push({ label: 'Ảnh / Video', items: med });
  const au = audioItems().map((it) => {
    const v = it.v;
    let s, e;
    if (it.kind === 'vo') {
      s = parseTime(v.start || 0) + (v.clip != null ? P.starts[v.clip] || 0 : 0);
      e = v.out != null ? s + parseTime(v.out) - parseTime(v.in || 0) : total;
    } else { s = parseTime(v.start || 0); e = v.end != null ? parseTime(v.end) : total; }
    return { s, e: Math.min(e, total), cls: it.kind === 'vo' ? 'audio' : 'music', text: (it.kind === 'vo' ? '🎙 ' : '🎵 ') + String(v.src).split(/[\\/]/).pop(),
      sel: it.kind === 'vo' ? { k: 'vo', j: it.j } : { k: 'music' } };
  });
  if (au.length) groups.push({ label: 'Giọng / Nhạc', items: au });
  groups.push({ label: 'Tiếng (SFX)', sfx: true, items: sfxs().map((x, i) => ({ s: parseTime(x.at) + clipOff(x), e: parseTime(x.at) + clipOff(x) + 0.01, text: String(x.sfx).split(/[\\/]/).pop().replace(/\.(wav|mp3)$/, ''), sel: { k: 'sfx', i } })) });

  let labels = '', lanesHtml = '';
  const all = [];
  for (const g of groups) {
    const n = g.sfx ? 1 : pack(g.items);
    for (let k = 0; k < n; k++) {
      labels += `<div>${k === 0 ? esc(g.label) : ''}</div>`;
      let row = '';
      for (const it of g.items.filter((x) => (g.sfx ? true : x.lane === k))) {
        const idx = all.push(it) - 1;
        const isSel = sameSel(it.sel, sel);
        if (g.sfx) row += `<div class="sfxm${isSel ? ' sel' : ''}" data-i="${idx}" style="left:${it.s * pps}px" title="${esc(it.text)}"><span>${esc(it.text)}</span></div>`;
        else row += `<div class="blk ${it.cls}${isSel ? ' sel' : ''}" data-i="${idx}" style="left:${it.s * pps}px;width:${Math.max(4, (it.e - it.s) * pps)}px" title="${esc(it.text)} (${fmt(it.s)}–${fmt(it.e)})">` +
          `${it.drag ? '<div class="eh l"></div>' : ''}${esc(it.text)}${it.drag ? '<div class="eh r"></div>' : ''}</div>`;
      }
      lanesHtml += `<div class="lane">${row}</div>`;
    }
  }
  $('#tlLabels').innerHTML = labels;
  $('#tracks').innerHTML = lanesHtml;
  $('#tlInner').style.width = total * pps + 80 + 'px';
  renderRuler();
  $('#tracks').querySelectorAll('[data-i]').forEach((d) => d.addEventListener('pointerdown', (ev) => tlPointer(ev, all[+d.dataset.i], d)));
}
function renderRuler() {
  const total = P.total;
  const steps = [0.5, 1, 2, 5, 10, 15, 30, 60, 120];
  const step = steps.find((s) => s * pps >= 70) || 300;
  let h = '';
  for (let t = 0; t <= total + 0.001; t += step) {
    h += `<div class="tick" style="left:${t * pps}px">${fmt(t, true)}</div>`;
    for (let k = 1; k < 5; k++) if (t + (k * step) / 5 < total) h += `<div class="tick minor" style="left:${(t + (k * step) / 5) * pps}px"></div>`;
  }
  $('#ruler').innerHTML = h;
}
function tlTimeAt(ev) {
  const r = $('#tlInner').getBoundingClientRect();
  return clamp((ev.clientX - r.left) / pps, 0, P.total);
}
function tlPointer(ev, it, el) {
  ev.stopPropagation();
  if (!sameSel(it.sel, sel)) select(it.sel, false);
  const canDrag = it.sel.k === 'ov' || it.sel.k === 'sfx';
  if (!canDrag) { seek(selTime(it.sel) + seekPad(it.sel)); return; }
  const mode = ev.target.classList.contains('l') ? 'l' : ev.target.classList.contains('r') ? 'r' : 'move';
  const x0 = ev.clientX;
  let raw0;
  if (it.sel.k === 'ov') raw0 = ovRaw(ovs()[it.sel.i]);
  else { const x = sfxs()[it.sel.i]; const at = parseTime(x.at) + clipOff(x); raw0 = [at, at]; }
  const key = 'tl' + Date.now();
  let moved = false;
  el.setPointerCapture(ev.pointerId);
  tlDrag = true;
  const move = (e) => {
    const d = (e.clientX - x0) / pps;
    if (Math.abs(e.clientX - x0) > 2) moved = true;
    if (!moved) return;
    let [s, en] = raw0;
    if (mode === 'move') { const dd = Math.max(-s, d); s += dd; en += dd; }
    else if (mode === 'l') s = clamp(s + d, 0, en - 0.1);
    else en = Math.max(s + 0.1, en + d);
    s = Math.round(s * 100) / 100; en = Math.round(en * 100) / 100;
    if (it.sel.k === 'ov') {
      mutate((p) => setOvTimes(p.overlays[it.sel.i], s, en), key);
      const [vs, ve] = ovTimes(ovs()[it.sel.i]);
      el.style.left = vs * pps + 'px'; el.style.width = Math.max(4, (ve - vs) * pps) + 'px';
    } else {
      mutate((p) => { const x = p.sfx[it.sel.i]; x.at = r3(s - clipOff(x)); }, key);
      el.style.left = s * pps + 'px';
    }
  };
  const up = () => {
    el.removeEventListener('pointermove', move); el.removeEventListener('pointerup', up);
    tlDrag = false;
    if (!moved) seek(selTime(it.sel) + seekPad(it.sel));
    renderTimeline(); syncPropValues();
  };
  el.addEventListener('pointermove', move);
  el.addEventListener('pointerup', up);
}
$('#tlScroll').addEventListener('pointerdown', (ev) => {
  if (ev.target.closest('.blk,.sfxm')) return;
  const sc = $('#tlScroll');
  sc.setPointerCapture(ev.pointerId);
  seek(tlTimeAt(ev));
  const move = (e) => seek(tlTimeAt(e));
  const up = () => { sc.removeEventListener('pointermove', move); sc.removeEventListener('pointerup', up); };
  sc.addEventListener('pointermove', move);
  sc.addEventListener('pointerup', up);
});
$('#tlScroll').addEventListener('scroll', () => { $('#tlLabels').scrollTop = $('#tlScroll').scrollTop; });
function setZoom() {
  if (!P) return;
  const fit = ($('#tlScroll').clientWidth - 90) / Math.max(1, P.total);
  const z = +$('#zoom').value / 100;
  pps = fit * Math.pow(400 / Math.max(fit, 1), z);
  renderTimeline();
}
$('#zoom').addEventListener('input', setZoom);

// ------------------------------------------------------------------ properties panel
function target() {
  if (!sel) return plan;
  if (sel.k === 'ov') return ovs()[sel.i];
  if (sel.k === 'sfx') return sfxs()[sel.i];
  if (sel.k === 'clip') return plan.clips[sel.i];
  if (sel.k === 'subcfg') return plan.subtitles;
  if (sel.k === 'music') return (plan.audio || {}).music;
  if (sel.k === 'vo') { const v = (plan.audio || {}).voiceover; return Array.isArray(v) ? v[sel.j] : v; }
  return null;
}
function getPath(obj, path) { return path.split('.').reduce((o, k) => (o == null ? undefined : o[k]), obj); }
function setPath(obj, path, val) {
  const ks = path.split('.');
  let o = obj;
  for (const k of ks.slice(0, -1)) { if (o[k] == null || typeof o[k] !== 'object') o[k] = {}; o = o[k]; }
  const last = ks[ks.length - 1];
  if (val === undefined) delete o[last]; else o[last] = val;
}
// f = [path, label, type, opts]
function fieldHtml(f, n) {
  const [path, label, type, opt = {}] = f;
  const id = 'f' + n;
  const ph = opt.ph != null ? ` placeholder="${esc(opt.ph)}"` : '';
  let inp;
  if (type === 'textarea') inp = `<textarea id="${id}" rows="${opt.rows || 2}"${ph}></textarea>`;
  else if (type === 'num') inp = `<input id="${id}" type="number" step="${opt.step ?? 0.01}"${ph}>`;
  else if (type === 'bool') inp = `<label class="boolf"><input id="${id}" type="checkbox"> ${esc(opt.text || 'Bật')}</label>`;
  else if (type === 'select') inp = `<select id="${id}">${opt.options.map((o) => `<option value="${esc(o)}">${esc(o === '' ? (opt.empty || '(mặc định)') : (opt.names?.[o] ?? o))}</option>`).join('')}</select>`;
  else if (type === 'color') inp = `<div class="colorf"><input type="color" id="${id}c"><input id="${id}"${ph}></div>`;
  else if (type === 'json') inp = `<textarea id="${id}" rows="${opt.rows || 3}" spellcheck="false"${ph}></textarea>`;
  else inp = `<input id="${id}"${ph}${opt.list ? ` list="${opt.list}"` : ''}>`;
  return type === 'bool' ? `<div class="f">${inp}</div>` : `<div class="f"><label for="${id}">${esc(label)}</label>${inp}</div>`;
}
let FIELDS = [];
function bindFields(fields, root) {
  FIELDS = fields.map((f, n) => ({ f, n, el: root.querySelector('#f' + n), cel: root.querySelector('#f' + n + 'c') }));
  const sk = JSON.stringify(sel);
  for (const F of FIELDS) {
    const [path, , type, opt = {}] = F.f;
    if (!F.el) continue;
    const write = () => {
      let v;
      if (type === 'bool') v = F.el.checked;
      else if (type === 'num') v = F.el.value === '' ? undefined : parseFloat(F.el.value);
      else if (type === 'json') {
        const s = F.el.value.trim();
        if (!s) v = undefined;
        else { try { v = JSON.parse(s); F.el.style.borderColor = ''; } catch { F.el.style.borderColor = 'var(--red)'; return; } }
      } else if (type === 'select') v = F.el.value === '' ? undefined : F.el.value;
      else v = F.el.value === '' && !opt.keepEmpty ? undefined : F.el.value;
      if (opt.parse) v = opt.parse(v);
      mutate(() => { const tg = target(); if (tg) (opt.set ? opt.set(tg, v) : setPath(tg, path, v)); }, sk + path);
      if (opt.rerender) renderProps();
    };
    F.el.addEventListener(type === 'bool' || type === 'select' ? 'change' : 'input', write);
    if (F.cel) F.cel.addEventListener('input', () => {
      const old = F.el.value || '';
      const alpha = /^#[0-9a-f]{8}$/i.test(old) ? old.slice(7) : '';
      F.el.value = F.cel.value.toUpperCase() + alpha;
      write();
    });
  }
  syncPropValues(true);
}
function syncPropValues(all = false) {
  const tg = target();
  for (const F of FIELDS) {
    if (!F.el || (!all && document.activeElement === F.el)) continue;
    const [path, , type, opt = {}] = F.f;
    let v = tg ? (opt.get ? opt.get(tg) : getPath(tg, path)) : undefined;
    if (type === 'bool') F.el.checked = v ?? opt.def ?? false;
    else if (type === 'json') F.el.value = v === undefined ? '' : JSON.stringify(v, null, 1);
    else if (type === 'num') F.el.value = v === undefined || v === null || v === '' ? '' : r3(Number(v));
    else F.el.value = v ?? '';
    if (F.cel) { const c = normColor(v) || normColor(opt.def) || '#FFFFFF'; F.cel.value = c.slice(0, 7); }
  }
}
const posX = ['pos.x', 'Vị trí ngang (0–1)', 'num', { step: 0.01, get: (o) => posGet(o, 0), set: (o, v) => posSet(o, 0, v) }];
const posY = ['pos.y', 'Vị trí dọc (0–1)', 'num', { step: 0.01, get: (o) => posGet(o, 1), set: (o, v) => posSet(o, 1, v) }];
function posGet(o, k) {
  const p = o.pos ?? defPosOf(o);
  if (typeof p === 'string') return (NAMED_POS[p] || NAMED_POS.center)[k];
  return p[k] > 1 ? r3(p[k] / (k ? CH() : CW())) : p[k];
}
function defPosOf(o) { return o === plan.subtitles ? (CH() > CW() ? 'lower' : 'bottom') : defPos(o); }
function posSet(o, k, v) {
  if (v === undefined || isNaN(v)) return;
  const cur = [posGet(o, 0), posGet(o, 1)];
  cur[k] = r3(v);
  o.pos = cur;
}
function anchorField() {
  const names = { '': 'Không neo (giờ tuyệt đối)' };
  const opts = [''];
  P.clips.forEach((c, i) => { opts.push(String(i)); names[String(i)] = `Cảnh ${i + 1}: ${c.name}`; });
  return ['clip', 'Neo theo cảnh', 'select', {
    options: opts, names, empty: names[''], rerender: true,
    get: (o) => (o.clip == null ? '' : String(o.clip)),
    set: (o, v) => {  // keep the same place on the timeline when re-anchoring
      const isSfx = sel.k === 'sfx';
      const absS = isSfx ? parseTime(o.at) + clipOff(o) : ovRaw(o)[0];
      const absE = isSfx ? 0 : ovRaw(o)[1];
      if (v === undefined) delete o.clip; else o.clip = +v;
      if (isSfx) o.at = r3(absS - clipOff(o)); else setOvTimes(o, absS, absE);
    },
  }];
}
const timeFields = () => [
  ['start', 'Bắt đầu (s)', 'num', { get: (o) => r3(ovRaw(o)[0]), set: (o, v) => { if (v === undefined) return; const [, e] = ovRaw(o); setOvTimes(o, v, Math.max(v + 0.1, e)); } }],
  ['end', 'Kết thúc (s)', 'num', { get: (o) => r3(ovRaw(o)[1]), set: (o, v) => { if (v === undefined) return; const [s] = ovRaw(o); setOvTimes(o, s, Math.max(s + 0.1, v)); } }],
];
const fontF = ['font', 'Font chữ', 'text', { list: 'dlFonts', ph: 'mặc định của video' }];
const sfxF = ['sfx', 'Tiếng khi hiện', 'text', { list: 'dlSfx', ph: 'theo auto_sfx' }];
function ovFields(o) {
  const t = o.type || 'text';
  const common = [...timeFields(), anchorField()];
  const anim = ['anim', 'Hiệu ứng vào', 'select', { options: ANIMS }];
  const look = [['rotate', 'Xoay (độ)', 'num', { step: 1 }], ['pulse', '', 'bool', { text: 'Nhịp thở (phóng nhẹ)' }], ['uppercase', '', 'bool', { text: 'Viết HOA', get: upperOf }], fontF, sfxF];
  const B = BASE();
  if (t === 'text') return [['text', 'Nội dung', 'textarea', { keepEmpty: true }], ...common, posX, posY,
    ['size', 'Cỡ chữ', 'num', { step: 1, ph: Math.round(B * 0.06) }], ['color', 'Màu chữ', 'color', { def: 'white' }],
    ['bg', 'Màu nền hộp (trống = chữ viền)', 'color'], ['outline_color', 'Màu viền', 'color', { def: 'black' }],
    ['bold', '', 'bool', { text: 'Đậm' }], anim, ...look];
  if (t === 'label') return [['title', 'Dòng nhỏ (tiêu đề)', 'text'], ['text', 'Giá trị lớn', 'text', { keepEmpty: true }], ...common, posX, posY,
    ['size', 'Cỡ giá trị', 'num', { step: 1, ph: Math.round(B * 0.095) }], ['title_size', 'Cỡ tiêu đề', 'num', { step: 1, ph: Math.round(B * 0.05) }],
    ['title_bg', 'Nền tiêu đề', 'color', { def: 'red' }], ['title_color', 'Chữ tiêu đề', 'color', { def: 'white' }],
    ['bg', 'Nền giá trị', 'color', { def: 'white' }], ['color', 'Chữ giá trị', 'color', { def: '#111111' }], anim, ...look];
  if (t === 'title') return [['text', 'Tiêu đề', 'text', { keepEmpty: true }], ['highlight', 'Dòng nhấn (hộp màu)', 'text'], ...common, posX, posY,
    ['size', 'Cỡ chữ', 'num', { step: 1, ph: Math.round(B * 0.08) }], ['color', 'Màu chữ', 'color', { def: 'white' }],
    ['outline_color', 'Màu viền', 'color', { def: 'black' }], ['highlight_bg', 'Nền dòng nhấn', 'color', { def: 'red' }],
    ['highlight_color', 'Chữ dòng nhấn', 'color', { def: 'white' }], anim, ...look];
  if (t === 'badge') return [['text', 'Nội dung', 'text', { keepEmpty: true }], ...common, posX, posY,
    ['size', 'Cỡ chữ', 'num', { step: 1, ph: Math.round(B * 0.055) }], ['bg', 'Màu nền', 'color', { def: 'blue' }],
    ['color', 'Màu chữ', 'color', { def: 'white' }], ['icon', 'Biểu tượng', 'select', { options: ['', 'dot'], names: { dot: '● chấm' }, empty: 'Không' }],
    ['icon_color', 'Màu chấm', 'color', { def: '#22C55E' }], anim, ...look];
  if (t === 'motion') {
    const c = o.comp;
    const P_ = (k, label, type = 'text', opt = {}) => ['props.' + k, label, type, opt];
    const f = [['comp', 'Mẫu thẻ', 'select', { options: MOTION_COMPS, rerender: true }], ...common];
    if (c === 'BlueText') f.push(P_('top', 'Dòng nhỏ'), P_('text', 'Dòng to (**xanh** _nghiêng_ [hộp] ~navy~)', 'textarea', { keepEmpty: true }),
      P_('size', 'Cỡ dòng to', 'num', { step: 1, ph: 92 }), P_('align', 'Canh', 'select', { options: ['', 'center', 'left'] }));
    if (c === 'BlueBig') f.push(P_('top', 'Dòng nhỏ'), P_('text', 'Chữ to (**xanh** _nghiêng_)', 'text', { keepEmpty: true }), P_('sub', 'Dòng dưới'),
      P_('tone', 'Nền', 'select', { options: ['light', 'dark'], names: { light: 'Sáng (mờ kính trắng)', dark: 'Tối (mờ kính xanh/đen)' } }),
      P_('size', 'Cỡ chữ to', 'num', { step: 1, ph: 150 }));
    if (c === 'NumberTitle') f.push(P_('n', 'Số'), P_('top', 'Dòng nhỏ'), P_('text', 'Dòng to', 'text', { keepEmpty: true }));
    if (c === 'FollowCard') f.push(P_('name', 'Tên trang'), P_('handle', 'Tên phụ (@...)'), P_('avatar', 'Ảnh đại diện (đường dẫn)'),
      P_('clickAt', 'Giây con trỏ bấm', 'num', { step: 0.1, ph: 1.1 }));
    if (c === 'ScreenCard') f.push(P_('src', 'Ảnh chụp màn hình'), P_('url', 'Địa chỉ trên thanh'), P_('title', 'Tiêu đề trên thẻ'));
    f.push(P_('x', 'Vị trí ngang (0–1)', 'num', { step: 0.01 }), P_('y', 'Vị trí dọc (0–1)', 'num', { step: 0.01, ph: MOTION_DEF_Y[c] }),
      P_('scale', 'Phóng to', 'num', { step: 0.05, ph: 1 }), ['props', 'Toàn bộ thông số (JSON)', 'json', { rows: 6 }], sfxF);
    return f;
  }
  if (t === 'frost') return [...common,
    ['mode', 'Màu kính', 'select', { options: ['light', 'blue', 'dark', 'white'], names: { light: 'Trắng xanh', blue: 'Xanh dương', dark: 'Tối', white: 'Trắng' } }],
    ['blur', 'Độ mờ', 'num', { step: 1, ph: 36 }], ['fade', 'Mờ dần vào/ra (s)', 'num', { step: 0.05, ph: 0.25 }],
    ['hide_subs', '', 'bool', { text: 'Ẩn phụ đề trong cảnh này', def: true, get: (o) => o.hide_subs ?? true }],
    ['window', 'Khung người nói (JSON: crop [x,y,w,h], pos, width, radius) — trống = không chia đôi', 'json', { rows: 4 }]];
  if (t === 'image' || t === 'video') {
    const f = [['src', 'File', 'text', { keepEmpty: true }], ...common, posX, posY,
      ['width', 'Rộng (0–1 = tỉ lệ khung, >1 = pixel)', 'num', { step: 0.01, ph: t === 'image' ? 0.25 : 0.4 }],
      ['opacity', 'Độ đậm (0–1)', 'num', { step: 0.05, ph: 1 }], ['radius', 'Bo góc (px)', 'num', { step: 1 }],
      ['fade', 'Mờ dần vào/ra (s)', 'num', { step: 0.05, ph: 0.3 }], ['anim', 'Hiệu ứng vào', 'select', { options: MEDIA_ANIMS }], sfxF];
    if (t === 'video') f.splice(f.length - 1, 0, ['in', 'Bắt đầu từ giây (trong file)', 'num'], ['loop', '', 'bool', { text: 'Lặp lại' }],
      ['key', 'Xoá màu nền (#00FF00 phông xanh, #000000 nền đen)', 'text']);
    return f;
  }
  return [...common, posX, posY];
}
function renderProps() {
  const el = $('#props');
  FIELDS = [];
  if (!P) { el.innerHTML = ''; return; }
  const tg = target();
  let head = '', fields = [], extra = '', notes = '';
  if (!sel) {
    head = '<h3>Cài đặt video</h3>';
    fields = [['font', 'Font mặc định', 'text', { list: 'dlFonts' }], ['fade_in', 'Hiện dần đầu video (s)', 'num'], ['fade_out', 'Tối dần cuối video (s)', 'num'],
      ['quality', 'Chất lượng xuất', 'select', { options: ['', 'draft', 'high', 'max'], empty: 'high (mặc định)' }],
      ['audio.original_volume', 'Âm lượng tiếng gốc các cảnh', 'num', { step: 0.05, ph: 1 }], ['audio.normalize', 'Chuẩn âm lượng (LUFS)', 'num', { step: 1, ph: -14 }],
      ['output', 'Tên file xuất', 'text'], ['auto_sfx', 'Tiếng tự động (auto_sfx, JSON)', 'json']];
    notes = `<div class="note">Khung ${CW()}×${CH()} · dài ${fmt(P.total)} · ${P.clips.length} cảnh · ${ovs().length} lớp chữ/ảnh · ${P.segments.length} câu phụ đề.<br>
      Bấm vào chữ/ảnh trên khung hình hoặc timeline để sửa. <b>Space</b> phát/dừng, <b>Ctrl+Z</b> hoàn tác, <b>Ctrl+S</b> lưu, <b>Delete</b> xoá, <b>Ctrl+D</b> nhân đôi.</div>`;
  } else if (sel.k === 'ov') {
    head = `<h3>${esc(TYPE_NAME[tg.type || 'text'] || tg.type)}</h3><span class="badge-type">#${sel.i + 1}</span>`;
    fields = ovFields(tg);
    if (!ASS_TYPES.has(tg.type || 'text') && !MEDIA_TYPES.has(tg.type)) notes = '<div class="note">Loại này chỉ sửa được thời gian, vị trí và JSON.</div>';
    if (tg.type === 'image' && /cards?[\\/]/i.test(tg.src || '')) notes = '<div class="note">Đây là thẻ ảnh PNG làm sẵn: đổi được vị trí, cỡ, thời gian. Muốn đổi chữ/màu bên trong thẻ thì nhờ Claude dựng lại thẻ.</div>';
    extra = `<div class="btns"><button id="bJump">⏵ Tới đây</button><button id="bDup">Nhân đôi</button><button id="bUp" title="Đưa lên trên">↑ Lên trên</button><button id="bDown" title="Đưa xuống dưới">↓ Xuống dưới</button><button id="bDel" class="danger">Xoá</button></div>
      <div class="sec">JSON (nâng cao)</div><textarea id="rawJson" rows="6" spellcheck="false"></textarea><div class="btns"><button id="bRaw">Áp dụng JSON</button></div>`;
  } else if (sel.k === 'seg') {
    const g = P.segments.find((g) => g.ti === sel.ti && g.seg === sel.seg);
    head = '<h3>Câu phụ đề</h3>';
    extra = g ? `<div class="note">${fmt(g.start)} – ${fmt(g.end)} · ${esc(g.rel)}</div>
      <div class="f"><label>Nội dung (sửa chính tả, giữ nguyên số từ thì từng chữ giữ đúng thời gian)</label><textarea id="segText" rows="4">${esc(g.text)}</textarea></div>
      <div class="btns"><button id="bSeg" class="primary">Lưu câu này</button><button id="bJump">⏵ Tới đây</button><button id="bSubCfg">⚙ Kiểu phụ đề</button></div>
      <div class="note">Sửa phụ đề ghi thẳng vào file transcript (bản gốc cất ở Lịch sử), không hoàn tác bằng Ctrl+Z.</div>` : '<div class="note">Không tìm thấy câu.</div>';
  } else if (sel.k === 'subcfg') {
    head = '<h3>Phụ đề chung</h3>';
    fields = [['style', 'Kiểu', 'select', { options: SUB_STYLES }], posX, posY, ['size', 'Cỡ chữ', 'num', { step: 1, ph: Math.round(BASE() * (CH() > CW() ? 0.075 : 0.06)) }],
      ['color', 'Màu chữ', 'color', { def: 'white' }], ['highlight', 'Màu chữ đang đọc', 'color', { def: '#FFD600' }], ['bg', 'Màu hộp nền', 'color'],
      ['outline_color', 'Màu viền', 'color', { def: 'black' }], ['words_per_line', 'Số từ mỗi dòng', 'num', { step: 1 }], ['max_chars', 'Số ký tự tối đa / dòng', 'num', { step: 1 }],
      ['uppercase', '', 'bool', { text: 'Viết HOA' }], fontF, ['offset', 'Lệch thời gian (s)', 'num'], ['keywords', 'Từ khoá tô màu (JSON: {"từ": "#màu"})', 'json']];
  } else if (sel.k === 'clip') {
    head = `<h3>Cảnh ${sel.i + 1}</h3><span class="badge-type">${esc(P.clips[sel.i]?.name || '')}</span>`;
    notes = '<div class="note warn">Đổi cảnh (cắt, tốc độ, chuyển cảnh, màu) cần bấm <b>⟳ Dựng lại nền</b> mới thấy đúng trong khung xem trước. Bản xuất thì luôn đúng.</div>';
    fields = [['in', 'Cắt từ giây', 'num'], ['out', 'Đến giây', 'num'], ['speed', 'Tốc độ', 'num', { step: 0.05, ph: 1 }], ['volume', 'Âm lượng', 'num', { step: 0.05, ph: 1 }],
      ['mute', '', 'bool', { text: 'Tắt tiếng cảnh này' }], ['fit', 'Cách lấp khung', 'select', { options: ['', 'auto', 'crop', 'blur', 'pad'] }],
      ['focus', 'Tâm cắt ngang (0–1)', 'num', { step: 0.05 }], ['punch', 'Phóng tĩnh (vd 1.15)', 'num', { step: 0.05 }],
      ['zoom', 'Zoom chậm', 'select', { options: ['', 'in', 'out', 'none'] }], ['grade', 'Màu (preset)', 'select', { options: GRADES, get: (o) => (typeof o.grade === 'string' ? o.grade : '') }],
      ['beauty', 'Mịn da (0–1)', 'num', { step: 0.05 }],
      ['transition', 'Chuyển cảnh vào', 'select', { options: XFADES, get: (o) => (typeof o.transition === 'string' ? o.transition : o.transition?.type || 'cut'),
        set: (o, v) => { if (!v || v === 'cut') delete o.transition; else o.transition = { type: v, duration: (typeof o.transition === 'object' && o.transition.duration) || 0.4 }; } }],
      ['transition.duration', 'Thời lượng chuyển cảnh (s)', 'num', { step: 0.05 }]];
  } else if (sel.k === 'sfx') {
    head = '<h3>Tiếng (SFX)</h3>';
    fields = [['sfx', 'Tiếng', 'text', { list: 'dlSfx', keepEmpty: true }], ['at', 'Thời điểm (s)', 'num', { get: (o) => r3(parseTime(o.at) + clipOff(o)), set: (o, v) => { if (v !== undefined) o.at = r3(v - clipOff(o)); } }],
      anchorField(), ['volume', 'Âm lượng', 'num', { step: 0.05, ph: 0.3 }], ['len', 'Cắt dài tối đa (s)', 'num', { step: 0.1, ph: 3 }]];
    extra = '<div class="btns"><button id="bPlaySfx">▶ Nghe thử</button><button id="bJump">⏵ Tới đây</button><button id="bDup">Nhân đôi</button><button id="bDel" class="danger">Xoá</button></div>';
  } else if (sel.k === 'music') {
    head = '<h3>Nhạc nền</h3>';
    fields = [['src', 'File nhạc', 'text', { keepEmpty: true }], ['volume', 'Âm lượng (0.12–0.2 khi có giọng)', 'num', { step: 0.01, ph: 0.18 }], ['start', 'Bắt đầu (s)', 'num'],
      ['end', 'Kết thúc (s)', 'num'], ['in', 'Bắt đầu từ giây trong file', 'num'], ['fade_in', 'Hiện dần (s)', 'num', { ph: 0.5 }], ['fade_out', 'Tắt dần (s)', 'num', { ph: 2 }],
      ['duck', '', 'bool', { text: 'Tự nhỏ lại khi có giọng nói', def: true }]];
    notes = '<div class="note">Xem trước không mô phỏng tự nhỏ nhạc khi có giọng; bản xuất thì có.</div>';
  } else if (sel.k === 'vo') {
    head = '<h3>Giọng đọc / lồng tiếng</h3>';
    fields = [['src', 'File', 'text', { keepEmpty: true }], ['start', 'Bắt đầu trên timeline (s)', 'num'], anchorField(), ['in', 'Cắt từ giây', 'num'], ['out', 'Đến giây', 'num'],
      ['volume', 'Âm lượng', 'num', { step: 0.05, ph: 1 }]];
    fields[2][3].set = (o, v) => { if (v === undefined) delete o.clip; else o.clip = +v; };
  }
  el.innerHTML = `<div class="ph">${head}</div>${notes}${fields.map(fieldHtml).join('')}${extra}
    <datalist id="dlFonts">${(ST.fonts || []).map((f) => `<option value="${esc(f)}">`).join('')}</datalist>
    <datalist id="dlSfx">${(ST.sfxLib || []).map((f) => `<option value="${esc(f)}">`).join('')}</datalist>`;
  bindFields(fields, el);
  const on = (id, fn) => { const b = el.querySelector('#' + id); if (b) b.addEventListener('click', fn); };
  on('bJump', () => { const t = selTime(sel); if (t != null) seek(t + seekPad(sel)); });
  on('bDel', delSelected);
  on('bDup', dupSelected);
  on('bUp', () => moveLayer(1));
  on('bDown', () => moveLayer(-1));
  on('bSubCfg', () => select({ k: 'subcfg' }));
  on('bPlaySfx', () => { const x = target(); const f = P.sfx.find((s) => Math.abs(s.at - (parseTime(x.at) + clipOff(x))) < 0.002); new Audio(mediaUrl(f ? f.src : x.sfx)).play().catch(() => toast('Không phát được')); });
  on('bSeg', saveSeg);
  const segT = el.querySelector('#segText');
  if (segT) segT.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.ctrlKey) saveSeg(); });
  const raw = el.querySelector('#rawJson');
  if (raw) {
    raw.value = JSON.stringify(tg, null, 1);
    on('bRaw', () => {
      try { const v = JSON.parse(raw.value); mutate((p) => { p.overlays[sel.i] = v; }); renderProps(); }
      catch (e) { toast('JSON sai: ' + e.message); }
    });
  }
}
async function saveSeg() {
  const g = P.segments.find((g) => g.ti === sel.ti && g.seg === sel.seg);
  const text = $('#segText').value.trim();
  if (!g || !text) return;
  try { await api('/api/transcript', { path: g.path, seg: g.seg, text }); toast('Đã sửa phụ đề'); refresh(); }
  catch (e) { toast('Lỗi: ' + e.message); }
}
function delSelected() {
  if (!sel) return;
  if (sel.k === 'ov') { const i = sel.i; mutate((p) => p.overlays.splice(i, 1)); }
  else if (sel.k === 'sfx') { const i = sel.i; mutate((p) => p.sfx.splice(i, 1)); }
  else return;
  sel = null; renderProps();
}
function dupSelected() {
  if (!sel || (sel.k !== 'ov' && sel.k !== 'sfx')) return;
  const t = video.currentTime || 0;
  if (sel.k === 'ov') {
    const o = JSON.parse(JSON.stringify(ovs()[sel.i]));
    const [s, e] = ovRaw(o);
    mutate((p) => { p.overlays.push(o); setOvTimes(o, t, t + (e - s)); });
    sel = { k: 'ov', i: ovs().length - 1 };
  } else {
    const x = JSON.parse(JSON.stringify(sfxs()[sel.i]));
    delete x.clip; x.at = r3(t);
    mutate((p) => p.sfx.push(x));
    sel = { k: 'sfx', i: sfxs().length - 1 };
  }
  renderProps(); toast('Đã nhân đôi tại vị trí đầu phát');
}
function moveLayer(dir) {
  if (!sel || sel.k !== 'ov') return;
  const i = sel.i, j = i + dir;
  if (j < 0 || j >= ovs().length) return;
  mutate((p) => { const a = p.overlays; [a[i], a[j]] = [a[j], a[i]]; });
  sel = { k: 'ov', i: j };
  syncMediaEls(); renderProps();
}

// ------------------------------------------------------------------ add elements
document.querySelector('.add-row').addEventListener('click', (e) => {
  const b = e.target.closest('button'); if (!b || !P) return;
  const t = r3(video.currentTime || 0);
  const kind = b.dataset.add;
  if (kind === 'image') { $('#fileImg').click(); return; }
  if (kind === 'sfx') {
    mutate((p) => { p.sfx = p.sfx || []; p.sfx.push({ sfx: 'pop', at: t, volume: 0.35 }); });
    select({ k: 'sfx', i: sfxs().length - 1 }); listFilter === 'audio' || toast('Đã thêm tiếng "pop" tại đầu phát');
    return;
  }
  const tpl = {
    blue: { type: 'motion', comp: 'BlueText', props: { top: 'dòng nhỏ', text: 'chữ **xanh** _nghiêng_', y: 0.72 } },
    tiles: { type: 'motion', comp: 'Tiles', props: { y: 0.16, items: [{ icon: '🎬', label: 'Mục 1' }, { icon: '✨', label: 'Mục 2' }, { icon: '✅', label: 'Mục 3' }] } },
    frost: { type: 'frost', mode: 'light' },
    text: { type: 'text', text: 'Chữ mới', pos: [0.5, 0.3], size: 80, color: 'white', anim: 'pop' },
    title: { type: 'title', text: 'Tiêu đề', highlight: 'Dòng nhấn', pos: 'top' },
    label: { type: 'label', title: 'Giá', text: '9.990k', pos: [0.3, 0.42] },
    badge: { type: 'badge', text: 'Freeship', bg: 'blue', pos: [0.5, 0.45] },
  }[kind];
  const t0 = Math.floor((video.currentTime || 0) * 100) / 100;
  const o = { ...tpl, start: t0, end: r3(t0 + 2.5) };
  mutate((p) => { p.overlays = p.overlays || []; p.overlays.push(o); });
  select({ k: 'ov', i: ovs().length - 1 }, true);
});
$('#fileImg').addEventListener('change', async (e) => {
  const f = e.target.files[0]; if (!f) return;
  e.target.value = '';
  toast('Đang chép file vào thư mục video…');
  try {
    const r = await fetch('/api/upload?name=' + encodeURIComponent(f.name), { method: 'POST', body: f });
    const j = await r.json();
    if (!j.ok) throw new Error(j.error);
    const t = r3(video.currentTime || 0);
    const isVid = f.type.startsWith('video');
    const o = { type: isVid ? 'video' : 'image', src: j.src, start: t, end: r3(t + 3), pos: [0.5, 0.35], width: 0.6, fade: 0.2 };
    mutate((p) => { p.overlays = p.overlays || []; p.overlays.push(o); });
    select({ k: 'ov', i: ovs().length - 1 });
  } catch (err) { toast('Lỗi tải file: ' + err.message); }
});

// ------------------------------------------------------------------ theme colour (đổi màu chủ đạo cả video)
function colorUses(p) {
  const uses = new Map();
  const add = (c) => { const n = normColor(c); if (n) uses.set(n.slice(0, 7), (uses.get(n.slice(0, 7)) || 0) + 1); };
  for (const o of p.overlays || []) if (ASS_TYPES.has(o.type || 'text')) for (const k of COLOR_KEYS) if (o[k]) add(o[k]);
  const s = p.subtitles;
  if (s) { for (const k of SUB_COLOR_KEYS) if (s[k]) add(s[k]); for (const v of Object.values(s.keywords || {})) add(v); }
  return [...uses.entries()].sort((a, b) => b[1] - a[1]);
}
function replaceColor(p, from, to) {
  const swap = (c) => { const n = normColor(c); return n && n.slice(0, 7) === from ? to + (n.length === 9 ? n.slice(7) : '') : c; };
  for (const o of p.overlays || []) if (ASS_TYPES.has(o.type || 'text')) for (const k of COLOR_KEYS) if (o[k]) o[k] = swap(o[k]);
  const s = p.subtitles;
  if (s) {
    for (const k of SUB_COLOR_KEYS) if (s[k]) s[k] = swap(s[k]);
    if (s.keywords) for (const k of Object.keys(s.keywords)) s.keywords[k] = swap(s.keywords[k]);
  }
}
const VIP_THEMES = [['blue', '#3158FF', 'Xanh'], ['orange', '#FF6A1A', 'Cam'], ['red', '#E5303C', 'Đỏ'], ['gold', '#E8B84A', 'Vàng kim'],
  ['blackgold', '#E8B84A', 'Đen vàng'], ['green', '#19B46B', 'Xanh lá'], ['pink', '#FF4F9A', 'Hồng'], ['purple', '#7B4DFF', 'Tím'],
  ['teal', '#10B5B0', 'Ngọc'], ['sky', '#1EA7FF', 'Da trời'], ['brown', '#B8743A', 'Nâu']];
let theme = null;
function openTheme() {
  const panel = $('#themePanel');
  const uses = colorUses(plan);
  const accent = uses.find(([c]) => c !== '#FFFFFF' && c !== '#000000' && c !== '#111111') || uses[0] || ['#3158FF'];
  theme = { base: JSON.stringify(plan), from: accent[0] };
  drawTheme();
  panel.classList.remove('hidden');
}
function drawTheme() {
  const panel = $('#themePanel');
  const uses = colorUses(JSON.parse(theme.base));
  panel.innerHTML = `<div style="display:flex;align-items:center"><h4 style="flex:1">🎨 Màu chủ đạo của cả video</h4><button id="thClose">✕</button></div>
    <div class="sec">Bộ màu VIP (đổi cả hiệu ứng chuyển động, cảnh kính mờ, nền)</div>
    <div class="sw-row">${VIP_THEMES.map(([k, c, label]) => `<div class="sw vt${(JSON.parse(theme.base).theme || 'blue') === k ? ' on' : ''}" data-k="${k}" style="background:${c}" title="${label}"><small>${label}</small></div>`).join('')}
      <input type="color" id="vtPick" value="#3158FF" title="Màu riêng"></div>
    <div class="note">Hiệu ứng chuyển động vẽ lại theo màu mới sau vài giây.</div>
    <div class="sec">Đổi từng màu chữ</div>
    <div class="note">1) Chọn màu đang dùng · 2) Rê chuột lên màu mới để xem trước trên khung hình · 3) Bấm để đổi toàn bộ chữ, nhãn, phụ đề đang dùng màu đó.</div>
    <div class="sec">Màu đang dùng (số chỗ dùng)</div>
    <div class="sw-row">${uses.map(([c, n]) => `<div class="sw from${c === theme.from ? ' on' : ''}" data-c="${c}" style="background:${c}" title="${c}"><small>${n}</small></div>`).join('')}</div>
    <div class="sec">Đổi thành</div>
    <div class="sw-row">${PALETTE.map((c) => `<div class="sw to" data-c="${c}" style="background:${c}" title="${c}"></div>`).join('')}
      <input type="color" id="thPick" value="${theme.from}" title="Màu khác"></div>
    <div class="note">Thẻ ảnh PNG làm sẵn giữ nguyên màu. Đổi xong vẫn Ctrl+Z được.</div>`;
  panel.querySelector('#thClose').onclick = closeTheme;
  const setVip = (k) => { pushUndo(theme.base); plan = JSON.parse(theme.base); if (k === 'blue') delete plan.theme; else plan.theme = k;
    theme.base = JSON.stringify(plan); afterChange(10); drawTheme(); toast('Đã đổi bộ màu cả video'); };
  panel.querySelectorAll('.sw.vt').forEach((d) => d.onclick = () => setVip(d.dataset.k));
  panel.querySelector('#vtPick').onchange = (e) => setVip(e.target.value.toUpperCase());
  panel.querySelectorAll('.sw.from').forEach((d) => d.onclick = () => { theme.from = d.dataset.c; drawTheme(); });
  const preview = (to) => { plan = JSON.parse(theme.base); replaceColor(plan, theme.from, to); scheduleRefresh(20); };
  const restore = () => { plan = JSON.parse(theme.base); scheduleRefresh(20); };
  const commit = (to) => {
    pushUndo(theme.base);
    plan = JSON.parse(theme.base); replaceColor(plan, theme.from, to);
    theme.base = JSON.stringify(plan); theme.from = to.toUpperCase();
    afterChange(10); drawTheme(); toast('Đã đổi màu cả video');
  };
  panel.querySelectorAll('.sw.to').forEach((d) => {
    d.onmouseenter = () => preview(d.dataset.c);
    d.onmouseleave = restore;
    d.onclick = () => commit(d.dataset.c);
  });
  const pick = panel.querySelector('#thPick');
  pick.oninput = () => preview(pick.value.toUpperCase());
  pick.onchange = () => commit(pick.value.toUpperCase());
}
function closeTheme() {
  if (theme) { plan = JSON.parse(theme.base); scheduleRefresh(10); }
  theme = null;
  $('#themePanel').classList.add('hidden');
  renderProps();
}

// ------------------------------------------------------------------ modal, history, render jobs
function showModal(title, html) {
  $('#mTitle').textContent = title;
  $('#mBody').innerHTML = html;
  $('#modal').classList.remove('hidden');
}
function hideModal() { $('#modal').classList.add('hidden'); $('#mBody').innerHTML = ''; jobModalOpen = false; }
$('#mClose').onclick = hideModal;
async function openHistory() {
  const h = await api('/api/history');
  showModal('Lịch sử bản lưu', h.length ? h.map((x) => `<div class="hist"><span>${new Date(x.time * 1000).toLocaleString('vi-VN')}</span>` +
    `<small style="color:var(--muted)">${(x.size / 1024).toFixed(1)} KB</small><button data-n="${esc(x.name)}">Khôi phục</button></div>`).join('') +
    '<div class="note">Mỗi lần bấm Lưu, bản plan.json cũ được cất ở đây. Khôi phục xong nhớ bấm Lưu.</div>' : '<div class="note">Chưa có bản lưu nào. Bấm 💾 Lưu là bản cũ được cất lại ở đây.</div>');
  $('#mBody').querySelectorAll('button[data-n]').forEach((b) => b.onclick = async () => {
    const data = await api('/api/history/get?name=' + encodeURIComponent(b.dataset.n));
    pushUndo(); plan = data; sel = null; afterChange(10); renderProps(); hideModal(); toast('Đã khôi phục, bấm Lưu để giữ');
  });
}
let jobModalOpen = false, polling = false;
async function doRender(mode) {
  try {
    if (isDirty()) await save();
    await api('/api/render', { mode });
    openJob(mode);
  } catch (e) { toast('Lỗi: ' + e.message, 5000); }
}
const MODE_NAME = { base: 'Dựng lại video nền', draft: 'Xuất bản nháp', final: 'Xuất video', preview: 'Xuất đoạn xem thử' };
function openJob(mode) {
  jobModalOpen = true;
  showModal(MODE_NAME[mode] || 'Đang xuất', `<div id="jobState">Đang chạy…</div><div class="prog"><div id="jobProg"></div></div>
    <pre class="log" id="jobLog"></pre><div class="btns"><button id="bStop" class="danger">Dừng</button></div>`);
  $('#bStop').onclick = () => api('/api/stop', {});
  pollJob();
}
async function pollJob(silent = false) {
  if (polling) return;
  polling = true;
  try {
    for (;;) {
      const j = await api('/api/job');
      if (jobModalOpen && $('#jobLog')) {
        const log = j.log || '';
        $('#jobLog').textContent = log;
        $('#jobLog').scrollTop = 1e9;
        const segs = [...log.matchAll(/segment (\d+)\/(\d+)/g)].pop();
        let pct = segs ? (60 * segs[1]) / segs[2] : 5;
        if (/timeline/.test(log)) pct = j.mode === 'base' ? 95 : 70;
        if (!j.running && j.code === 0) pct = 100;
        $('#jobProg').style.width = pct + '%';
        $('#jobState').textContent = j.running ? `${MODE_NAME[j.mode] || ''}… ${Math.round(Date.now() / 1000 - j.start)} giây` : '';
      }
      if (!j.running) {
        if (j.code === 0) {
          if (jobModalOpen && j.mode !== 'base' && j.out) {
            $('#jobState').innerHTML = `✅ Xong: <b>${esc(j.out)}</b> (${Math.round(j.end - j.start)} giây)`;
            $('#mBody .btns').innerHTML = `<button id="bOpen">📂 Mở thư mục</button><button id="bWatch" class="primary">▶ Xem video</button>`;
            $('#bOpen').onclick = () => api('/api/open', { path: j.out });
            $('#bWatch').onclick = () => { $('#mBody').innerHTML = `<video src="${mediaUrl(j.out)}" controls autoplay style="width:100%;max-height:70vh;background:#000;border-radius:8px"></video>`; };
          } else if (jobModalOpen) { hideModal(); toast('Đã dựng lại video nền'); }
        } else if (j.code != null) {
          if (jobModalOpen) $('#jobState').innerHTML = '❌ Lỗi khi xuất. Xem log bên dưới hoặc nhờ Claude xem giúp.';
          else if (!silent) toast('Lỗi khi dựng, mở log để xem');
        }
        break;
      }
      await new Promise((r) => setTimeout(r, 700));
    }
  } catch (e) { toast('Mất kết nối server: ' + e.message, 5000); }
  polling = false;
  refresh();
}

// ------------------------------------------------------------------ buttons + keys
$('#btnPlay').onclick = togglePlay;
$('#btnUndo').onclick = undo;
$('#btnRedo').onclick = redo;
$('#btnSave').onclick = () => save().catch((e) => toast('Lỗi lưu: ' + e.message));
$('#btnDraft').onclick = () => doRender('draft');
$('#btnFinal').onclick = () => doRender('final');
$('#btnBase').onclick = () => doRender('base');
$('#btnHistory').onclick = openHistory;
$('#btnTheme').onclick = () => (theme ? closeTheme() : openTheme());
$('#chkSafe').onchange = (e) => $('#safe').classList.toggle('hidden', !e.target.checked);
$('#chkBox').onchange = () => drawHandles(true);
window.addEventListener('resize', () => { layoutStage(); setZoom(); });
window.addEventListener('beforeunload', (e) => { if (plan && isDirty()) { e.preventDefault(); e.returnValue = ''; } });
document.addEventListener('keydown', (e) => {
  const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName || '') && document.activeElement.type !== 'checkbox' && document.activeElement.type !== 'range';
  const ctrl = e.ctrlKey || e.metaKey;
  if (ctrl && e.key.toLowerCase() === 's') { e.preventDefault(); save(); return; }
  if (typing) return;
  if (ctrl && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
  if (ctrl && e.key.toLowerCase() === 'y') { e.preventDefault(); redo(); return; }
  if (ctrl && e.key.toLowerCase() === 'd') { e.preventDefault(); dupSelected(); return; }
  if (e.key === ' ') { e.preventDefault(); togglePlay(); }
  else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    e.preventDefault();
    const fps = P ? P.canvas.fps || 30 : 30;
    const d = (e.shiftKey ? 1 : 1 / fps) * (e.key === 'ArrowLeft' ? -1 : 1);
    video.pause(); seek((video.currentTime || 0) + d);
  } else if (e.key === 'Delete' || e.key === 'Backspace') delSelected();
  else if (e.key === 'Escape') { if (theme) closeTheme(); else select(null); }
  else if (e.key === 'Home') seek(0);
  else if (e.key === 'End') seek(P ? P.total : 0);
});

// ------------------------------------------------------------------ boot
async function boot() {
  ST = await api('/api/state');
  plan = ST.plan;
  savedJSON = JSON.stringify(plan);
  plan.overlays = plan.overlays || [];
  $('#planName').textContent = ST.planName + ' — ' + ST.root;
  document.title = 'VIP Editor · ' + ST.planName;
  if (ST.draft && JSON.stringify(ST.draft) !== savedJSON) {
    pushUndo(); plan = ST.draft;  // Ctrl+Z goes back to the saved plan.json
    setTimeout(() => toast('Đã mở lại bản nháp chưa lưu lần trước · Ctrl+Z để về bản đã lưu', 6000), 500);
  }
  updateStatus();
  await refresh();
  layoutStage();
  setZoom();
  renderProps();
  if (ST.job && ST.job.running) openJob(ST.job.mode);
  requestAnimationFrame(tick);
}
boot().catch((e) => { $('#status').textContent = 'Lỗi: ' + e.message; });
