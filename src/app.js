/* Aurora · MVP 02 — mapa colaborativo de segurança para mulheres em Rio Claro (SP)
   Um único arquivo roda em dois modos:
   - link publicado (claude.ai): relatos num banco compartilhado, IA no chat;
   - arquivo hospedado (GitHub Pages etc.): alerta por GPS, dados só no aparelho.
   Nos dois, o mapa de ruas (OpenStreetMap) e a rede de apoio vêm embutidos no próprio arquivo. */
(() => {
'use strict';

/* ------------------------------------------------------------------ utilidades */
const D = window.AURORA_DATA;
const HAS_CLAUDE = !!(window.claude && typeof window.claude.use === 'function');
const STANDALONE = !HAS_CLAUDE;
const DAY = 864e5, RECENT_DAYS = 30;

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k === 'text') e.textContent = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v);
    else if (k === 'style') e.style.cssText = v;
    else e.setAttribute(k, v === true ? '' : v);
  }
  for (const k of kids.flat(Infinity)) if (k != null && k !== false) e.append(k.nodeType ? k : document.createTextNode(String(k)));
  return e;
}
function icon(id, cls = 'i') {
  const NS = 'http://www.w3.org/2000/svg';
  const s = document.createElementNS(NS, 'svg'); s.setAttribute('class', cls); s.setAttribute('aria-hidden', 'true');
  const u = document.createElementNS(NS, 'use'); u.setAttribute('href', '#i-' + id); s.append(u); return s;
}
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const escRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const fmtN = n => Number(n).toLocaleString('pt-BR');
const pct = (v, n) => Math.round(100 * v / n);
const plural = (n, s, p) => fmtN(n) + ' ' + (n === 1 ? s : p);
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
function fmtDate(iso) { const [y, m, d] = iso.split('-').map(Number); return d + ' ' + MESES[m - 1] + ' ' + y; }
function ago(ts) {
  const ms = Date.now() - ts, d = Math.floor(ms / DAY);
  if (d <= 0) { const hr = Math.floor(ms / 36e5); return hr <= 0 ? 'agora há pouco' : 'há ' + plural(hr, 'hora', 'horas'); }
  return d === 1 ? 'ontem' : 'há ' + d + ' dias';
}
const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function toast(msg, ms = 3400) { const t = $('#toast'); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => { t.hidden = true; }, ms); }
const LS = {
  get(k, d) { try { const v = localStorage.getItem('aurora.v1.' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('aurora.v1.' + k, JSON.stringify(v)); } catch (e) { /* armazenamento indisponível */ } }
};
const isMobile = () => matchMedia('(max-width: 999px)').matches;

/* ------------------------------------------------------------------ vocabulário */
const TIPOS = [
  { id: 'assedio', label: 'Assédio verbal', kw: /assedi|cantada|mexeu comigo|falou (coisa|besteira|gracinha)|gracinha|obscen|buzin/ },
  { id: 'perseguicao', label: 'Perseguição', long: 'Perseguição / me seguiram', kw: /segui(u|ram|ndo|da)|persegu|atras de mim|me acompanh/ },
  { id: 'abordagem', label: 'Abordagem indesejada', kw: /abord|chegou em mim|puxou conversa|tentou (falar|conversar|pegar)|insist/ },
  { id: 'intimidacao', label: 'Intimidação', long: 'Encarar ou intimidar', kw: /encar|olhando|observ|intimid|me medindo/ },
  { id: 'exposicao', label: 'Exposição sexual', kw: /exposi|mostrou (as partes|o penis|o orgao)|se masturb|nudez|pelado/ },
  { id: 'roubo', label: 'Roubo ou furto', kw: /roub|furt|assalt|levaram|puxaram (meu|minha)/ },
  { id: 'violencia', label: 'Violência física', kw: /agred|bateu|empurr|soco|tapa|violencia fisica|me pegou|agarr/ },
  { id: 'veiculo', label: 'Situação com veículo', kw: /\bcarro\b|\bmoto\b|veiculo|\buber\b|\b99\b|motorista|\bvan\b|caminhao/ },
  { id: 'ambiente', label: 'Rua escura ou deserta', kw: /escur|desert|sem luz|iluminac|apagad|vazi[ao]/ },
  { id: 'outra', label: 'Outra situação', kw: null }
];
const TIPO = Object.fromEntries(TIPOS.map(t => [t.id, t]));
const PERIODOS = [
  { id: 'manha', label: 'Manhã', long: 'Manhã (6h–12h)', from: 6, to: 12 },
  { id: 'tarde', label: 'Tarde', long: 'Tarde (12h–18h)', from: 12, to: 18 },
  { id: '18-20', label: '18–20h', long: '18h–20h', from: 18, to: 20 },
  { id: '20-22', label: '20–22h', long: '20h–22h', from: 20, to: 22 },
  { id: '22-00', label: '22–00h', long: '22h–00h', from: 22, to: 24 },
  { id: 'madrugada', label: 'Madrugada', long: 'Madrugada (0h–6h)', from: 0, to: 6 }
];
const PER = Object.fromEntries(PERIODOS.map(p => [p.id, p]));
const QUANDO = { hoje: 'hoje', ontem: 'ontem', semana: 'nesta semana', antes: 'há mais de uma semana' };
const periodOfHour = hr => (PERIODOS.find(p => hr >= p.from && hr < p.to) || PERIODOS[5]).id;
const currentPeriod = () => periodOfHour(new Date().getHours());

/* ------------------------------------------------------------------ grade hexagonal (~1 km) */
const HX = D.hex, S3 = Math.sqrt(3), MLAT = 110574, MLNG = 111320 * Math.cos(HX.lat0 * Math.PI / 180);
const toXY = (lat, lng) => [(lng - HX.lng0) * MLNG, (lat - HX.lat0) * MLAT];
const toLL = (x, y) => [HX.lat0 + y / MLAT, HX.lng0 + x / MLNG];
function cellOf(lat, lng) {
  const [x, y] = toXY(lat, lng);
  const q = (S3 / 3 * x - y / 3) / HX.R, r = (2 / 3 * y) / HX.R, s = -q - r;
  let rq = Math.round(q), rr = Math.round(r); const rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs; else if (dr > ds) rr = -rq - rs;
  return (rq || 0) + '_' + (rr || 0);
}
function cellXY(id) { const [q, r] = id.split('_').map(Number); return [HX.R * S3 * (q + r / 2), HX.R * 1.5 * r]; }
const cellCenter = id => toLL(...cellXY(id));
function cellPoly(id) {
  const [cx, cy] = cellXY(id), pts = [];
  for (let k = 0; k < 6; k++) { const a = Math.PI / 180 * (60 * k - 30); pts.push(toLL(cx + HX.R * Math.cos(a), cy + HX.R * Math.sin(a))); }
  return pts;
}
function distM(a, b) { const [x1, y1] = toXY(a[0], a[1]), [x2, y2] = toXY(b[0], b[1]); return Math.hypot(x2 - x1, y2 - y1); }

/* ------------------------------------------------------------------ bairros e nomes de áreas */
const BAIRROS = D.bairros.map(([nome, lat, lng, n]) => ({ nome, lat, lng, n, key: norm(nome) }));
const BYNAME = Object.fromEntries(BAIRROS.map(b => [b.nome, b]));
const nameCache = new Map();
function areaName(id) {
  if (nameCache.has(id)) return nameCache.get(id);
  let nm;
  const bo = D.bo.cells[id];
  if (bo && bo.b.length) nm = bo.b[0][0] + ' e arredores';
  else {
    const c = cellCenter(id); let best = null, bd = Infinity;
    for (const b of BAIRROS) { const d = distM(c, [b.lat, b.lng]); if (d < bd) { bd = d; best = b; } }
    nm = best && bd < 1800 ? 'Perto de ' + best.nome : 'Zona rural de Rio Claro';
  }
  nameCache.set(id, nm); return nm;
}
function cellSearchText(id) {
  const parts = [areaName(id)];
  const bo = D.bo.cells[id]; if (bo) parts.push(...bo.b.map(x => x[0]));
  const pc = D.pesq.cells[id]; if (pc) parts.push(...pc.a.map(x => x[0]));
  return norm(parts.join(' '));
}
function searchBairros(q) {
  q = norm(q).trim(); if (!q) return [];
  return BAIRROS.filter(b => b.key.includes(q)).sort((a, b) => (b.key.startsWith(q) - a.key.startsWith(q)) || b.n - a.n);
}
const LANDMARKS = [[/\bunesp\b/, 'Bela Vista'], [/lago azul/, 'Vila Operária'], [/rodoviaria/, 'Jardim Claret'], [/estacao|jardim publico/, 'Centro']];
function findBairroInText(text) {
  const t = ' ' + norm(text) + ' ';
  let best = null;
  for (const b of BAIRROS) {
    if (b.key.length < 4) continue;
    if (new RegExp('(^|[^a-z0-9])' + escRe(b.key) + '([^a-z0-9]|$)').test(t) && (!best || b.key.length > best.key.length)) best = b;
  }
  if (best) return best;
  for (const [re, nome] of LANDMARKS) if (re.test(t)) return BYNAME[nome] || null;
  if (/\bcentro\b|zona central/.test(t)) return BYNAME['Centro'] || null;
  return null;
}
function matchBairro(name) {
  const k = norm(name).trim(); if (!k) return null;
  return BAIRROS.find(b => b.key === k) || BAIRROS.find(b => b.key.includes(k) || k.includes(b.key)) || findBairroInText(name);
}

/* ------------------------------------------------------------------ texto: tira dados pessoais */
function scrub(s) {
  let t = String(s || '');
  const removed = new Set();
  const rep = (re, label, token) => { t = t.replace(re, () => { removed.add(label); return token; }); };
  rep(/[\w.+-]+@[\w-]+\.[\w.-]+/g, 'e-mail', '[e-mail]');
  rep(/\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g, 'documento', '[documento]');
  rep(/(\+?55\s?)?\(?\b\d{2}\)?\s?9?\d{4}[-\s.]?\d{4}\b/g, 'telefone', '[telefone]');
  rep(/\b9?\d{4}-\d{4}\b/g, 'telefone', '[telefone]');
  rep(/\b[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}\b/g, 'placa', '[placa]');
  rep(/(^|\s)@[A-Za-z0-9_.]{3,}/g, 'perfil de rede social', ' [perfil]');
  rep(/\b(n[ºo°]\.?|n[uú]mero|casa|apto|apartamento|ap\.)\s?\d{1,5}\b/gi, 'número de endereço', '[número]');
  t = t.replace(/((?:chamad[oa]|se chama|nome (?:é|e|dele|dela)|conhecid[oa] como|apelid[oa](?: de)?)\s+)([A-ZÀ-Ý][\wÀ-ÿ]+(?:\s[A-ZÀ-Ý][\wÀ-ÿ]+)?)/g,
    (m, p1) => { removed.add('nome'); return p1 + '[nome]'; });
  return { text: t.replace(/\s{2,}/g, ' ').trim(), removed: [...removed] };
}

/* ------------------------------------------------------------------ armazenamento (banco do link ou aparelho) */
const Store = {
  mode: 'local', ready: false, uid: null, canWrite: true, canEdit: false, db: null,
  reports: new Map(), votes: {}, myVotes: {}, mod: { oculto: {}, verificado: {} },
  perfil: { areas: [], meus: [], visto: 0 },
  subs: new Set(), queues: {},
  on(f) { this.subs.add(f); },
  emit() { for (const f of this.subs) { try { f(); } catch (e) { console.error(e); } } },
  queue(key, fn) { const p = (this.queues[key] || Promise.resolve()).then(fn, fn); this.queues[key] = p.catch(() => {}); return p; },
  loadLocal() {
    this.reports = new Map(LS.get('relatos', []).map(r => [r.id, r]));
    this.myVotes = LS.get('votos', {});
    this.votes = this.localVoteCounts(this.myVotes);
    const m = LS.get('mod', {}); this.mod = { oculto: m.oculto || {}, verificado: m.verificado || {} };
    this.perfil = Object.assign({ areas: [], meus: [], visto: 0 }, LS.get('perfil', {}));
  },
  localVoteCounts(mine) { const v = {}; for (const [id, x] of Object.entries(mine)) v[id] = { c: +(x === 'c'), p: +(x === 'p'), f: +(x === 'f') }; return v; },
  async init() {
    this.loadLocal();
    if (!HAS_CLAUDE) { this.ready = true; this.emit(); return; }
    let db = null, user = null;
    try { [db, user] = await Promise.all([window.claude.use('db'), window.claude.use('user')]); } catch (e) { /* sem capacidades */ }
    if (user) { try { this.canEdit = !!(await user.canEdit()); } catch (e) { /* segue */ } }
    if (!db) { this.ready = true; this.emit(); return; }
    this.db = db; this.mode = 'db';
    this.reports = new Map(); this.votes = {}; this.myVotes = {}; this.mod = { oculto: {}, verificado: {} };
    if (user) {
      try { this.uid = await user.id(); } catch (e) { this.uid = null; }
      try { if ((await user.can('data.write')) === false) this.canWrite = false; } catch (e) { /* decide na escrita */ }
    }
    const fail = e => { console.warn('banco:', e && e.code); if (e && e.code === 'revoked') { this.mode = 'local'; this.loadLocal(); this.emit(); } };
    db.collection('relatos').onSnapshot(s => {
      const m = new Map();
      for (const d of s.docs) { const r = d.data(); if (r) m.set(d.id, Object.assign({}, r, { id: d.id })); }
      this.reports = m; this.ready = true; this.emit();
    }, fail);
    db.collection('votos').onSnapshot(s => {
      const agg = {}; let mine = {};
      for (const d of s.docs) {
        const r = (d.data() || {}).r || {};
        if (d.id === this.uid) mine = Object.assign({}, r);
        for (const [id, v] of Object.entries(r)) { const a = agg[id] || (agg[id] = { c: 0, p: 0, f: 0 }); if (v in a) a[v]++; }
      }
      this.votes = agg; this.myVotes = mine; this.emit();
    }, fail);
    db.doc('moderacao/estado').onSnapshot(d => {
      const m = (d.exists && d.data()) || {};
      this.mod = { oculto: Object.assign({}, m.oculto), verificado: Object.assign({}, m.verificado) }; this.emit();
    }, fail);
    if (this.uid) {
      try { const p = await db.doc('data/users/' + this.uid + '/perfil').get(); if (p.exists) this.perfil = Object.assign({ areas: [], meus: [], visto: 0 }, p.data()); } catch (e) { /* usa o do aparelho */ }
    }
    this.emit();
  },
  async addReport(r) {
    if (this.mode === 'db') {
      const ref = await this.db.collection('relatos').add(r);
      this.perfil.meus = [...this.perfil.meus, ref.id]; this.savePerfil(); return ref.id;
    }
    const id = 'l' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    this.reports.set(id, Object.assign({}, r, { id }));
    LS.set('relatos', [...this.reports.values()]);
    this.perfil.meus = [...this.perfil.meus, id]; this.savePerfil(); this.emit(); return id;
  },
  async deleteReport(id) {
    if (this.mode === 'db') await this.db.doc('relatos/' + id).delete();
    else { this.reports.delete(id); LS.set('relatos', [...this.reports.values()]); }
    this.perfil.meus = this.perfil.meus.filter(x => x !== id); this.savePerfil(); this.emit();
  },
  canVote() { return this.mode === 'local' || (!!this.uid && this.canWrite); },
  async vote(id, v) {
    const mine = Object.assign({}, this.myVotes);
    if (mine[id] === v) delete mine[id]; else mine[id] = v;
    if (this.mode === 'db') { this.myVotes = mine; this.emit(); await this.queue('votos', () => this.db.doc('votos/' + this.uid).set({ r: mine })); return; }
    this.myVotes = mine; this.votes = this.localVoteCounts(mine); LS.set('votos', mine); this.emit();
  },
  async setMod(id, key, on) {
    const m = { oculto: Object.assign({}, this.mod.oculto), verificado: Object.assign({}, this.mod.verificado) };
    if (on) m[key][id] = true; else delete m[key][id];
    if (this.mode === 'db') { await this.queue('mod', () => this.db.doc('moderacao/estado').set(m)); return; }
    this.mod = m; LS.set('mod', m); this.emit();
  },
  savePerfil() {
    const p = { areas: this.perfil.areas.slice(0, 40), meus: this.perfil.meus.slice(-200), visto: this.perfil.visto || 0 };
    if (this.mode === 'db' && this.uid) return this.queue('perfil', () => this.db.doc('data/users/' + this.uid + '/perfil').set(p)).catch(() => LS.set('perfil', p));
    LS.set('perfil', p); return Promise.resolve();
  }
};

/* relatos: validação (dado compartilhado não é confiável) e visibilidade */
const CELL_RE = /^-?\d{1,3}_-?\d{1,3}$/;
function cleanReport(r) {
  if (!r || typeof r !== 'object') return null;
  const tipos = Array.isArray(r.tipos) ? r.tipos.filter(t => TIPO[t]).slice(0, 4) : [];
  if (!tipos.length || typeof r.cell !== 'string' || !CELL_RE.test(r.cell) || typeof r.criado !== 'number') return null;
  return {
    id: String(r.id), tipos, cell: r.cell,
    quando: QUANDO[r.quando] ? r.quando : null, periodo: PER[r.periodo] ? r.periodo : null,
    texto: typeof r.texto === 'string' ? r.texto.slice(0, 320) : '', criado: r.criado,
    origem: r.origem === 'chat-ia' ? 'chat-ia' : 'chat'
  };
}
function allReports() { const out = []; for (const r of Store.reports.values()) { const c = cleanReport(r); if (c) out.push(c); } return out.sort((a, b) => b.criado - a.criado); }
function isHidden(r) { if (Store.mod.verificado[r.id]) return false; if (Store.mod.oculto[r.id]) return true; const v = Store.votes[r.id]; return !!(v && v.f >= 3); }
function recentReports() { const lim = Date.now() - RECENT_DAYS * DAY; return allReports().filter(r => r.criado >= lim && !isHidden(r)); }

/* ------------------------------------------------------------------ estado dos filtros */
const S = { layer: 'percepcao', userLayer: false, period: 'todos', tipo: 'todos', cat: 'n', selected: null, route: null, routeMode: false, pick: null, view: 'mapa', showAll: false,
  apoio: LS.get('apoio', true) !== false, apSel: null };
const activePeriod = () => (S.period === 'agora' ? currentPeriod() : S.period);
function periodOk(r) { const p = activePeriod(); return p === 'todos' || r.periodo === p; }
function filteredReports() { return recentReports().filter(r => periodOk(r) && (S.tipo === 'todos' || r.tipos.includes(S.tipo))); }
function percValue(c) {
  const p = activePeriod(); if (p === 'todos') return c.n;
  const hh = c.h || {}; let v = (hh[p] || 0) + (hh.todo || 0);
  if (p === 'manha' || p === 'tarde') v += hh.dia || 0;
  return Math.min(v, c.n);
}
function layerValues(layer = S.layer) {
  const m = new Map();
  if (layer === 'relatos') for (const r of filteredReports()) m.set(r.cell, (m.get(r.cell) || 0) + 1);
  else if (layer === 'percepcao') for (const [id, c] of Object.entries(D.pesq.cells)) { const v = percValue(c); if (v > 0) m.set(id, v); }
  else for (const [id, c] of Object.entries(D.bo.cells)) { const v = S.cat === 'n' ? c.n : c[S.cat]; if (v > 0) m.set(id, v); }
  return m;
}
const SCALES = {
  relatos: { vars: ['--amb-1', '--amb-2', '--amb-3', '--amb-4'], breaks: [1, 2, 3, 5], labels: ['1', '2', '3–4', '5+'], title: 'Relatos nos últimos 30 dias' },
  percepcao: { vars: ['--lil-1', '--lil-2', '--lil-3', '--lil-4'], breaks: [1, 2, 4, 9], labels: ['1', '2–3', '4–8', '9+'], title: 'Mulheres que citaram a área' },
  historico: { vars: ['--rose-1', '--rose-2', '--rose-3', '--rose-4'], breaks: [1, 5, 10, 20], labels: ['1–4', '5–9', '10–19', '20+'], title: 'Registros de B.O. por área' }
};
function classOf(v, breaks) { let k = -1; for (let i = 0; i < breaks.length; i++) if (v >= breaks[i]) k = i; return k; }

/* ------------------------------------------------------------------ mapa */
let map, renderer, baseRenderer, hexLayer, labelLayer, pinLayer, routeLayer, selLayer, boundaryLine, meMarker, C = {};
const hexes = new Map();
const OSM = window.AURORA_OSM || null;
const mq = matchMedia('(prefers-color-scheme: dark)');
function isDark() { const t = document.documentElement.getAttribute('data-theme'); return t ? t === 'dark' : mq.matches; }
function readColors() {
  C = { ink: cssVar('--ink'), boundary: cssVar('--boundary'), brand: cssVar('--brand'), ground: cssVar('--map-ground'),
    road: cssVar('--map-road'), roadCase: cssVar('--map-road-case'), major: cssVar('--map-road-major'), majorCase: cssVar('--map-road-major-case'),
    water: cssVar('--map-water'), green: cssVar('--map-green'), park: cssVar('--map-park'), campus: cssVar('--map-campus'),
    campusLine: cssVar('--map-campus-line'), rail: cssVar('--map-rail') };
}
function decodePoly(str) {
  const pts = []; let i = 0, lat = 0, lng = 0;
  while (i < str.length) {
    let b, shift = 0, res = 0;
    do { b = str.charCodeAt(i++) - 63; res |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
    lat += (res & 1) ? ~(res >> 1) : (res >> 1);
    shift = 0; res = 0;
    do { b = str.charCodeAt(i++) - 63; res |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
    lng += (res & 1) ? ~(res >> 1) : (res >> 1);
    pts.push([lat / 1e5, lng / 1e5]);
  }
  return pts;
}

/* mapa de ruas desenhado a partir do OpenStreetMap embutido: funciona sem servidor de mapas */
const BL = {};
const ROAD_W = { // [contorno, via] em pixels, do zoom 12 ao 17
  major: [[2.6, 1.4], [3.6, 2.2], [5.2, 3.4], [7.4, 5.2], [10.5, 7.8], [15, 11.5]],
  sec: [[2, 1], [2.8, 1.6], [4.2, 2.8], [5.8, 4.2], [8.4, 6.2], [11.5, 8.8]],
  ter: [[1.6, 0.8], [2.3, 1.3], [3.5, 2.3], [5, 3.6], [7.2, 5.4], [10.5, 7.8]],
  minor: [[0, 0.55], [1.2, 0.75], [2.2, 1.4], [3.5, 2.5], [5.6, 4.2], [8.4, 6.4]]
};
function zInterp(tab, z) { const zc = Math.max(12, Math.min(17, z)), i = Math.min(4, Math.floor(zc - 12)), t = zc - 12 - i; return tab[i].map((v, j) => v + (tab[i + 1][j] - v) * t); }
function initBaseMap() {
  if (!OSM) return;
  const g = k => (OSM.layers[k] || []).map(decodePoly);
  const opt = { renderer: baseRenderer, interactive: false, smoothFactor: 1.5 };
  const polys = k => L.polygon(g(k).map(r => [r]), Object.assign({ stroke: false, fillRule: 'nonzero' }, opt));
  BL.green = polys('green'); BL.park = polys('park'); BL.campus = polys('campus'); BL.water = polys('water');
  BL.river = L.polyline(g('river'), opt); BL.stream = L.polyline(g('stream'), opt);
  const rail = g('rail');
  BL.railCase = L.polyline(rail, opt); BL.railDash = L.polyline(rail, Object.assign({ dashArray: '5 7', lineCap: 'butt' }, opt));
  const R = {}; for (const k of ['minor', 'ter', 'sec', 'major']) R[k] = g(k);
  for (const k of ['minor', 'ter', 'sec', 'major']) { const o = k === 'minor' ? Object.assign({}, opt, { smoothFactor: 2 }) : opt; BL['c_' + k] = L.polyline(R[k], o); BL['f_' + k] = L.polyline(R[k], o); }
  for (const k of ['green', 'park', 'campus', 'water', 'river', 'stream', 'railCase', 'c_minor', 'c_ter', 'c_sec', 'c_major', 'f_minor', 'f_ter', 'f_sec', 'f_major', 'railDash']) BL[k].addTo(map);
}
function styleBaseMap() {
  if (!map) return;
  if (boundaryLine) boundaryLine.setStyle({ color: C.boundary });
  if (!BL.f_major) return;
  const z = map.getZoom();
  BL.green.setStyle({ fillColor: C.green, fillOpacity: 1 });
  BL.park.setStyle({ fillColor: C.park, fillOpacity: 1 });
  BL.campus.setStyle({ fillColor: C.campus, fillOpacity: 1, stroke: true, color: C.campusLine, weight: 1, opacity: 1 });
  BL.water.setStyle({ fillColor: C.water, fillOpacity: 1 });
  BL.river.setStyle({ color: C.water, weight: zInterp([[1.6], [2], [2.8], [3.6], [4.6], [6]], z)[0], opacity: 1 });
  BL.stream.setStyle({ color: C.water, weight: zInterp([[0.8], [1], [1.4], [2], [2.6], [3.2]], z)[0], opacity: 1 });
  const rw = zInterp([[1.2], [1.6], [2.2], [2.8], [3.6], [4.4]], z)[0];
  BL.railCase.setStyle({ color: C.rail, weight: rw, opacity: 0.8 });
  BL.railDash.setStyle({ color: C.ground, weight: Math.max(0.6, rw - 1.4), opacity: z >= 14 ? 1 : 0 });
  for (const k of ['minor', 'ter', 'sec', 'major']) {
    const [cw, fw] = zInterp(ROAD_W[k], z), big = k === 'major' || k === 'sec';
    BL['c_' + k].setStyle({ color: big ? C.majorCase : C.roadCase, weight: cw, opacity: cw > fw ? 1 : 0 });
    BL['f_' + k].setStyle({ color: k === 'major' ? C.major : C.road, weight: fw, opacity: 1 });
  }
}

/* rótulos: bairros, lugares e ruas, por prioridade e sem sobreposição */
const LBL = [];
function addLabel(o) {
  o.m = L.marker([o.lat, o.lng], { icon: L.divIcon({ className: 'lbl ' + o.cls, html: o.html, iconSize: [0, 0] }), interactive: false, keyboard: false, pane: 'labels' });
  o.on = false; LBL.push(o);
}
function buildLabels() {
  for (const [nome, lat, lng, tier] of D.labels) {
    const n = (BYNAME[nome] || {}).n || 0;
    addLabel({ lat, lng, html: '<span>' + esc(nome) + '</span>', cls: 'bairro t' + tier, prio: tier === 1 ? 20 : 46 - Math.min(8, n / 3), minZ: tier === 1 ? 11 : 13.5, w: nome.length * (tier === 1 ? 8.2 : 7.4) + 12, h: 16 });
  }
  if (!OSM) return;
  for (const [nome, lat, lng, kind, minZ] of OSM.poi) {
    addLabel({ lat, lng, html: '<span>' + esc(nome) + '</span>', cls: 'poi ' + kind, prio: minZ <= 13.5 ? 18 : 40, minZ, w: nome.length * 6.9 + 12, h: 16 });
  }
  const PRIO = { 1: 26, 2: 34, 3: 50, 4: 64 }, MINZ = { 1: 14, 2: 14.5, 3: 15, 4: 16 };
  for (const [ni, lat, lng, ang, tier] of OSM.streetLabels) {
    const nome = OSM.streetNames[ni], w0 = nome.length * 6.1 + 8, h0 = 13, rad = ang * Math.PI / 180;
    const w = Math.abs(w0 * Math.cos(rad)) + Math.abs(h0 * Math.sin(rad)), hh = Math.abs(w0 * Math.sin(rad)) + Math.abs(h0 * Math.cos(rad));
    addLabel({ lat, lng, html: '<span style="transform:translate(-50%,-50%) rotate(' + ang + 'deg)">' + esc(nome) + '</span>', cls: 'rua r' + tier, prio: PRIO[tier], minZ: MINZ[tier], w, h: hh, key: 'r' + ni });
  }
}
function placeLabels() {
  if (!map || !labelLayer) return;
  const z = map.getZoom(), bounds = map.getBounds().pad(0.2), placed = [], seen = {}, want = new Set();
  for (const a of APV) { const p = map.latLngToLayerPoint(a.ll); placed.push([p.x + a.x0, p.y - 18, p.x + a.x1, p.y + 18]); } // rótulos das ruas desviam dos pontos de apoio
  const cand = LBL.filter(l => l.minZ <= z + 0.01 && bounds.contains([l.lat, l.lng])).sort((a, b) => a.prio - b.prio);
  for (const l of cand) {
    const p = map.latLngToLayerPoint([l.lat, l.lng]);
    const box = [p.x - l.w / 2, p.y - l.h / 2, p.x + l.w / 2, p.y + l.h / 2];
    if (placed.some(q => !(box[2] < q[0] || box[0] > q[2] || box[3] < q[1] || box[1] > q[3]))) continue;
    if (l.key) { const sn = seen[l.key] || (seen[l.key] = []); if (sn.some(q => Math.hypot(q.x - p.x, q.y - p.y) < 320)) continue; sn.push(p); }
    placed.push(box); want.add(l);
  }
  for (const l of LBL) {
    const on = want.has(l);
    if (on && !l.on) { l.m.addTo(labelLayer); l.on = true; }
    else if (!on && l.on) { labelLayer.removeLayer(l.m); l.on = false; }
  }
}

/* células de ~1 km com os dados, por cima das ruas */
const baseStyle = () => ({ stroke: false, fill: false, opacity: 0, fillOpacity: 0 });
function ensureHex(id) {
  if (hexes.has(id)) return hexes.get(id);
  const p = L.polygon(cellPoly(id), Object.assign({ renderer, bubblingMouseEvents: true }, baseStyle()));
  if (matchMedia('(hover: hover)').matches) p.bindTooltip(() => tipFor(id), { className: 'hex-tip', sticky: true, direction: 'top', opacity: 1 });
  p.addTo(hexLayer); hexes.set(id, p); return p;
}
function tipFor(id) {
  const v = layerValues().get(id) || 0, nm = esc(areaName(id));
  if (!v) return nm;
  const lbl = S.layer === 'relatos' ? plural(v, 'relato', 'relatos') : S.layer === 'percepcao' ? plural(v, 'menção', 'menções') : plural(v, 'registro', 'registros');
  return '<b>' + nm + '</b><br>' + lbl;
}
function initMap() {
  readColors();
  map = L.map('map', { zoomControl: false, attributionControl: true, preferCanvas: true, minZoom: 11, maxZoom: 17.5, zoomSnap: 0.5,
    maxBounds: [[-22.62, -47.84], [-22.18, -47.38]], maxBoundsViscosity: 0.8 });
  map.attributionControl.setPrefix(false);
  map.attributionControl.addAttribution('Mapa © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> · células de ~1 km');
  map.fitBounds([[-22.456, -47.622], [-22.364, -47.528]], { padding: [8, 8], animate: false });
  for (const [name, zi, pe] of [['base', 250, 'none'], ['cells', 420, ''], ['labels', 460, 'none'], ['apoio', 610, '']]) {
    const pane = map.createPane(name); pane.style.zIndex = zi; if (pe) pane.style.pointerEvents = pe;
  }
  baseRenderer = L.canvas({ pane: 'base', padding: 0.25 });
  renderer = L.canvas({ pane: 'cells', padding: 0.3, tolerance: 2 });
  initBaseMap();
  boundaryLine = L.polygon(D.boundary, { renderer: baseRenderer, interactive: false, fill: false, color: C.boundary, weight: 1.6, dashArray: '6 6' }).addTo(map);
  hexLayer = L.layerGroup().addTo(map);
  selLayer = L.layerGroup().addTo(map);
  routeLayer = L.layerGroup().addTo(map);
  labelLayer = L.layerGroup().addTo(map);
  buildLabels();
  pinLayer = L.layerGroup().addTo(map);
  apLayer = L.layerGroup().addTo(map);
  styleBaseMap(); renderApoio(); placeLabels();
  map.on('zoomend', () => { styleBaseMap(); styleHexes(); renderApoio(); placeLabels(); });
  map.on('moveend', placeLabels);
  map.on('click', onMapClick);
  $('#legend').addEventListener('click', e => { if (e.target.closest('.apkey')) setApoio(!S.apoio); });
  $('#zin').onclick = () => map.zoomIn();
  $('#zout').onclick = () => map.zoomOut();
  $('#btnRoute').onclick = () => (S.routeMode || (S.route && S.route.a) ? clearRoute() : startRoute());
  $('#routeClose').onclick = clearRoute;
  $('#pickCancel').onclick = () => { stopPick(); openChat(); Chat.bot('Tudo bem. Você pode buscar o bairro pelo nome.'); };
  if (STANDALONE && 'geolocation' in navigator) {
    const b = $('#btnLocate'); b.hidden = false;
    b.onclick = () => navigator.geolocation.getCurrentPosition(p => { const ll = [p.coords.latitude, p.coords.longitude]; showMe(ll); if (S.apoio && APOIO.length) openNearMe(ll); flyToVisible(ll, 15.5); },
      () => toast('Não consegui acessar sua localização. Verifique a permissão do navegador.'), { enableHighAccuracy: true, timeout: 15000 });
  }
}
function onMapClick(e) {
  const id = cellOf(e.latlng.lat, e.latlng.lng);
  if (S.pick) { const cb = S.pick; stopPick(); cb(id); return; }
  if (S.routeMode) { routeClick(e.latlng); return; }
  openPanel(id);
}
function renderMap() {
  if (!map) return;
  const prevGround = C.ground; readColors();
  if (C.ground !== prevGround) styleBaseMap();
  styleHexes(layerValues());
  renderPins(); renderSelection(); renderLegend(); renderNote(); renderAreaList(); renderEmptyHint(); updateCounts();
}
/* as células ficam mais transparentes de perto para as ruas continuarem legíveis */
function styleHexes(vals) {
  if (!map) return;
  vals = vals || layerValues();
  const sc = SCALES[S.layer], ramp = sc.vars.map(cssVar), z = map.getZoom();
  const op = (isDark() ? 0.62 : 0.5) * Math.max(0.42, Math.min(1, 1 - (z - 13) * 0.2)), w = z >= 15 ? 1.8 : 1.2;
  for (const id of vals.keys()) ensureHex(id);
  for (const [id, poly] of hexes) {
    const v = vals.get(id) || 0, k = v ? classOf(v, sc.breaks) : -1;
    poly.setStyle(k < 0 ? baseStyle() : { stroke: true, color: ramp[3], weight: w, opacity: 0.9, fill: true, fillColor: ramp[k], fillOpacity: op });
  }
}
function renderPins() {
  pinLayer.clearLayers();
  const reps = S.layer === 'relatos' ? filteredReports() : recentReports().filter(periodOk);
  const by = new Map(); for (const r of reps) by.set(r.cell, (by.get(r.cell) || 0) + 1);
  const faint = S.layer !== 'relatos';
  for (const [id, n] of by) {
    const ic = L.divIcon({ className: '', html: '<span class="pin' + (faint ? ' faint' : '') + '">' + n + '</span>', iconSize: [0, 0] });
    const m = L.marker(cellCenter(id), { icon: ic, keyboard: false, riseOnHover: true, title: plural(n, 'relato recente', 'relatos recentes') + ' · ' + areaName(id) });
    m.on('click', ev => { L.DomEvent.stopPropagation(ev); if (S.pick || S.routeMode) { onMapClick(ev); return; } openPanel(id); });
    m.addTo(pinLayer);
  }
}

/* ------------------------------------------------------------------ rede de apoio: onde pedir ajuda */
const AP = window.AURORA_APOIO || { tipos: {}, grupos: [], pontos: [] };
const APBY = Object.fromEntries(AP.pontos.map(p => [p.id, p]));
const APOIO = AP.pontos.filter(p => typeof p.lat === 'number' && typeof p.lng === 'number');
const AP_ORDER = ['policia', 'mulher', 'justica', 'social', 'saude'];
const AP_CORE = ['ddm', 'gcm', 'mulher', 'creas', 'defensoria', 'santacasa', 'upa29'];
let apLayer = null, APV = [];
const PREC = {
  exata: 'Ponto do prédio no OpenStreetMap.',
  endereco: 'Ponto calculado pelo endereço, sobre as ruas do OpenStreetMap. Margem de uns 30 metros.',
  aproximada: 'Posição aproximada, com margem de até 100 metros. Confira o endereço antes de ir.'
};
/* os CRAS dividem a mesma descrição, horário e fonte */
function apInfo(p) { return p && p.grupo === 'cras' && AP.cras ? Object.assign({}, AP.cras, { sub: 'Centro de Referência de Assistência Social' }, p) : p; }
const apSvg = (tipo, cls = 'i') => '<svg class="' + cls + '" aria-hidden="true"><use href="#i-' + ((AP.tipos[tipo] || {}).icone || 'pin') + '"/></svg>';
function fmtDist(m) { return m < 950 ? 'a ' + Math.max(50, Math.round(m / 50) * 50) + ' m' : 'a ' + (m / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' km'; }
function nearestApoio(ll, n = 3, tipos) {
  return APOIO.filter(p => !tipos || tipos.includes(p.tipo)).map(p => ({ p, d: distM(ll, [p.lat, p.lng]) })).sort((a, b) => a.d - b.d).slice(0, n);
}
/* o ponto mais perto para registrar ocorrência, para conversar e para a saúde */
function nearestByNeed(ll) {
  return [['policia'], ['mulher', 'social'], ['saude']].map(t => nearestApoio(ll, 1, t)[0]).filter(Boolean);
}
/* quanto do mapa o painel cobre: à direita no computador, embaixo no celular */
function panelInset() {
  const P = $('#panel'); if (!P || P.hidden) return [0, 0];
  const w = $('#mapwrap').getBoundingClientRect(), r = P.getBoundingClientRect();
  return r.width >= w.width - 40 ? [0, Math.max(0, w.bottom - r.top)] : [Math.max(0, w.right - r.left), 0];
}
function flyToVisible(ll, z) {
  const [dx, dy] = panelInset(); z = Math.min(map.getMaxZoom(), z == null ? map.getZoom() : z);
  map.flyTo(map.unproject(map.project(ll, z).add([dx / 2, dy / 2]), z), z, { duration: 0.6 });
}
function isVisible(ll, m = 36) {
  const [dx, dy] = panelInset(), s = map.getSize(), p = map.latLngToContainerPoint(ll);
  return p.x > m && p.y > m && p.x < s.x - dx - m && p.y < s.y - dy - m;
}
function telHref(n) { const d = n.replace(/\D/g, ''); return 'tel:' + (d.length >= 10 && d[0] !== '0' ? '+55' + d : d); }
function apDirections(p) {
  const dest = p.precisao === 'aproximada' ? encodeURIComponent(p.end + ', ' + p.bairro + ', Rio Claro - SP') : p.lat + ',' + p.lng;
  return 'https://www.google.com/maps/dir/?api=1&destination=' + dest;
}
function setApoio(on) {
  S.apoio = on; LS.set('apoio', on);
  if (!on && S.apSel) closePanel();
  renderApoio(); renderLegend(); placeLabels();
}
/* pontos muito próximos na tela viram um círculo com o número de serviços */
function apClusters() {
  const R = map.getZoom() >= 15 ? 26 : 32, cl = [];
  const pts = APOIO.map(p => ({ p, xy: map.latLngToLayerPoint([p.lat, p.lng]) })).sort((a, b) => AP_ORDER.indexOf(a.p.tipo) - AP_ORDER.indexOf(b.p.tipo));
  for (const it of pts) {
    const c = cl.find(q => Math.hypot(q.xy.x - it.xy.x, q.xy.y - it.xy.y) < R);
    if (c) { c.items.push(it.p); const k = c.items.length; c.xy = L.point((c.xy.x * (k - 1) + it.xy.x) / k, (c.xy.y * (k - 1) + it.xy.y) / k); }
    else cl.push({ items: [it.p], xy: it.xy });
  }
  for (const c of cl) c.ll = c.items.length === 1 ? L.latLng(c.items[0].lat, c.items[0].lng) : map.layerPointToLatLng(c.xy);
  return cl;
}
function renderApoio() {
  if (!map || !apLayer) return;
  apLayer.clearLayers(); APV = [];
  const cont = map.getContainer(), z = map.getZoom(), lbl = z >= 15;
  cont.classList.toggle('ap-lbl', lbl); cont.classList.toggle('ap-sm', z < 13);
  if (!S.apoio || !APOIO.length) return;
  const cls = apClusters();
  /* nomes ao lado dos ícones (de perto): à direita, à esquerda ou escondidos se não couberem */
  const occ = cls.map(c => [c.xy.x - 17, c.xy.y - 17, c.xy.x + 17, c.xy.y + 17]);
  const hit = b => occ.some(q => !(b[2] < q[0] || b[0] > q[2] || b[3] < q[1] || b[1] > q[3]));
  for (const c of cls) {
    const one = c.items.length === 1, p = c.items[0];
    const name = one ? (p.curto || p.nome) : (p.curto || p.nome) + ' e mais ' + (c.items.length - 1);
    let side = '', x0 = -18, x1 = 18;
    if (lbl) {
      const w = 6 + name.length * 6.9, y = c.xy.y, x = c.xy.x;
      const right = [x + 18, y - 9, x + 18 + w, y + 9], left = [x - 18 - w, y - 9, x - 18, y + 9];
      if (!hit(right)) { side = ''; occ.push(right); x1 = 18 + w; }
      else if (!hit(left)) { side = ' l'; occ.push(left); x0 = -18 - w; }
      else side = ' nl';
    }
    let html;
    if (one) html = '<span class="ap t-' + p.tipo + (p.precisao === 'aproximada' ? ' approx' : '') + (S.apSel === p.id ? ' sel' : '') + side + '"><span class="d">' + apSvg(p.tipo) + '</span><em>' + esc(name) + '</em></span>';
    else {
      const n = c.items.length, ring = 'conic-gradient(' + c.items.map((q, i) => 'var(--ap-' + q.tipo + ') ' + (i * 360 / n).toFixed(1) + 'deg ' + ((i + 1) * 360 / n).toFixed(1) + 'deg').join(',') + ')';
      html = '<span class="ap cl' + (c.items.some(q => q.id === S.apSel) ? ' sel' : '') + side + '" style="--ring:' + ring + '"><span class="d"><b>' + n + '</b></span><em>' + esc(name) + '</em></span>';
    }
    const title = one ? p.nome : 'Serviços de apoio: ' + c.items.map(q => q.curto || q.nome).join(', ');
    const m = L.marker(c.ll, { icon: L.divIcon({ className: 'ap-icon', html, iconSize: [30, 30], iconAnchor: [15, 15] }), pane: 'apoio', keyboard: true, title, riseOnHover: true });
    m.on('click', ev => {
      L.DomEvent.stopPropagation(ev);
      if (S.pick || S.routeMode) { onMapClick(ev); return; }
      if (one) openApoio(p.id, { reveal: true }); else openApoioList(c.items.map(q => q.id));
    });
    m.addTo(apLayer);
    APV.push({ ll: c.ll, x0: side === ' nl' ? -18 : x0, x1: side === ' nl' ? 18 : x1 });
  }
}
function flyToApoio(ids) {
  const pts = ids.map(id => APBY[id]).filter(p => p && p.lat != null);
  if (!pts.length) return;
  if (pts.length === 1) { flyToVisible([pts[0].lat, pts[0].lng], Math.max(map.getZoom(), 16)); return; }
  const [dx, dy] = panelInset();
  map.flyToBounds(L.latLngBounds(pts.map(p => [p.lat, p.lng])), { paddingTopLeft: [48, 64], paddingBottomRight: [48 + dx, 48 + dy], maxZoom: 16, duration: 0.6 });
}
/* abre o mapa (se estava em outra página) e depois executa fn, quando o mapa já tem tamanho */
function withMap(fn) {
  const was = S.view;
  showView('mapa'); closeChat();
  if (!S.apoio) setApoio(true);
  const go = () => { map.invalidateSize(); fn(); $('#mapwrap').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' }); };
  if (was !== 'mapa') setTimeout(go, 90); else go();
}
function focusApoio(id) {
  const p = APBY[id]; if (!p || p.lat == null) return;
  withMap(() => { openApoio(id); flyToApoio([id]); });
}
function showApoioOnMap() { withMap(() => { closePanel(); flyToApoio(AP_CORE); }); }
function telRows(tel) {
  return (tel || []).map(([n, l]) => h('div', { class: 'telrow' },
    h('div', null, h('a', { href: telHref(n), class: 'num', text: n }), l ? h('small', { text: l }) : null),
    h('button', { class: 'btn sm', type: 'button', 'data-copy': n, 'aria-label': 'Copiar ' + n }, icon('copy', 'i sm'), 'Copiar')));
}
function srcLine(p) {
  const fs = p.fontes || [];
  return h('p', { class: 'srcs' }, fs.length ? 'Fonte: ' : '', fs.map((f, i) => [i ? '; ' : '', h('a', { href: f[1], target: '_blank', rel: 'noopener', text: f[0] })]), fs.length ? '. ' : '', 'Mapa © OpenStreetMap.');
}
function openApoio(id, { reveal = false } = {}) {
  const p = apInfo(APBY[id]); if (!p) return;
  const T = AP.tipos[p.tipo] || { nome: '' };
  if (S.route && S.route.cells) clearRoute(true);
  S.selected = null; renderSelection();
  S.apSel = id; renderApoio();
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; P.dataset.kind = 'apoio'; P.dataset.ap = id; delete P.dataset.cell;
  P.append(h('header', { class: 'ap-head t-' + p.tipo },
    h('div', null, h('small', null, h('span', { class: 'ap-dot', html: apSvg(p.tipo, 'i sm') }), T.nome), h('h3', { text: p.nome }), p.sub ? h('p', { class: 'ap-subt', text: p.sub }) : null),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: closePanel }, icon('x'))));
  const body = h('div', { class: 'body' });
  body.append(h('div', { class: 'psec' },
    h('p', { class: 'addr' }, h('b', { text: p.end }), p.bairro ? h('span', { text: ' · ' + p.bairro }) : null),
    p.horario ? h('p', { class: 'when' }, icon('clock', 'i sm'), h('span', { text: p.horario })) : null,
    p.precisao ? h('p', { class: 'prec' }, icon('pin', 'i sm'), h('span', { text: PREC[p.precisao] })) : null));
  if ((p.tel || []).length || p.link) body.append(h('div', { class: 'psec' }, telRows(p.tel),
    p.link ? h('a', { class: 'btn sm', href: p.link[1], target: '_blank', rel: 'noopener', style: 'justify-self:start' }, p.link[0], icon('out', 'i sm')) : null));
  if ((p.faz || []).length || p.desc) body.append(h('div', { class: 'psec' }, h('h4', null, 'O que você encontra aqui'),
    p.faz && p.faz.length ? fazList(p.faz) : null, p.desc ? h('p', { text: p.desc }) : null,
    p.dica ? h('p', { class: 'tip', text: p.dica }) : null));
  body.append(h('div', { class: 'psec' }, srcLine(p),
    h('button', { class: 'linkbtn', type: 'button', 'data-view': 'apoio', style: 'justify-self:start;font-size:13.5px' }, 'Ver toda a rede de apoio', icon('chev', 'i sm'))));
  P.append(body);
  P.append(h('div', { class: 'actions two' },
    h('a', { class: 'btn primary', href: apDirections(p), target: '_blank', rel: 'noopener' }, icon('nav'), 'Como chegar'),
    h('button', { class: 'btn', type: 'button', 'data-copy': p.end + (p.bairro ? ', ' + p.bairro : '') + ', Rio Claro - SP' }, icon('copy'), 'Copiar endereço')));
  if (reveal && p.lat != null && !isVisible([p.lat, p.lng])) flyToVisible([p.lat, p.lng]);
}
function apRow(p, extra) {
  p = apInfo(p);
  return h('li', null, h('button', { type: 'button', class: 't-' + p.tipo, onclick: () => openApoio(p.id, { reveal: true }) },
    h('span', { class: 'ic', html: apSvg(p.tipo, 'i sm') }),
    h('span', null, h('b', { text: p.curto || p.nome }), h('span', { class: 's', text: p.end + (p.bairro ? ' · ' + p.bairro : '') })),
    extra ? h('span', { class: 'dist', text: extra }) : icon('chev')));
}
/* versão arquivo: depois de "Mostrar onde estou", os serviços mais perto de onde ela está */
function openNearMe(ll) {
  if (S.route && S.route.cells) clearRoute(true);
  S.selected = null; renderSelection(); if (S.apSel) { S.apSel = null; renderApoio(); }
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; P.dataset.kind = 'perto'; delete P.dataset.cell; delete P.dataset.ap;
  P.append(h('header', null,
    h('div', null, h('small', null, 'Onde pedir ajuda'), h('h3', null, 'Mais perto de você')),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: closePanel }, icon('x'))));
  P.append(h('div', { class: 'body' }, h('div', { class: 'psec' },
    h('ul', { class: 'aplist' }, nearestByNeed(ll).map(({ p, d }) => apRow(p, fmtDist(d)))),
    h('small', null, 'Distância em linha reta. Sua localização fica só neste aparelho.')),
    h('div', { class: 'psec' }, h('p', null, h('b', null, 'Em perigo agora?'), ' Ligue 190 (Polícia Militar) ou 153 (Guarda Civil).'))));
}
function openApoioList(ids) {
  if (S.route && S.route.cells) clearRoute(true);
  S.selected = null; renderSelection(); S.apSel = null; renderApoio();
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; P.dataset.kind = 'apoio-lista'; delete P.dataset.cell; delete P.dataset.ap;
  const same = ids.every(id => APBY[id].lat === APBY[ids[0]].lat && APBY[id].lng === APBY[ids[0]].lng);
  P.append(h('header', null,
    h('div', null, h('small', null, 'Onde pedir ajuda'), h('h3', { text: plural(ids.length, 'serviço', 'serviços') + (same ? ' no mesmo prédio' : ' aqui perto') })),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: closePanel }, icon('x'))));
  P.append(h('div', { class: 'body' }, h('div', { class: 'psec' }, h('ul', { class: 'aplist' }, ids.map(id => apRow(APBY[id]))))));
  if (!same) P.append(h('div', { class: 'actions one' }, h('button', { class: 'btn', type: 'button', onclick: () => flyToApoio(ids) }, icon('plus'), 'Aproximar o mapa')));
}
/* página Apoio: a mesma lista, agrupada pelo que a mulher precisa fazer */
const fazList = faz => h('ul', { class: 'faz' }, faz.map(f => h('li', null, icon('check', 'i sm'), h('span', { text: f }))));
const eyebrow = tipo => h('p', { class: 'eyebrow' }, h('span', { class: 'ap-dot', html: apSvg(tipo, 'i sm') }), (AP.tipos[tipo] || {}).nome || '');
function apCard(p0) {
  const p = apInfo(p0), card = h('div', { class: 'card place-card ap-card t-' + p.tipo });
  card.append(eyebrow(p.tipo), h('h3', { text: p.nome }));
  if (p.sub) card.append(h('p', { class: 'ap-sub', text: p.sub }));
  if (p.faz && p.faz.length) card.append(fazList(p.faz));
  if (p.desc) card.append(h('p', { text: p.desc }));
  if (p.end) card.append(h('p', null, h('b', { text: p.end }), p.bairro ? ' · ' + p.bairro : ''));
  if (p.horario) card.append(h('p', { class: 'when' }, icon('clock', 'i sm'), h('span', { text: p.horario })));
  if (p.tel) card.append(...telRows(p.tel));
  if (p.dica) card.append(h('p', { class: 'tip', text: p.dica }));
  const acts = h('div', { class: 'acts' });
  if (p.lat != null) acts.append(h('button', { class: 'btn sm primary', type: 'button', onclick: () => focusApoio(p.id) }, icon('map', 'i sm'), 'Ver no mapa'),
    h('a', { class: 'btn sm', href: apDirections(p), target: '_blank', rel: 'noopener' }, icon('nav', 'i sm'), 'Como chegar'));
  if (p.link) acts.append(h('a', { class: 'btn sm' + (p.lat == null ? ' primary' : ''), href: p.link[1], target: '_blank', rel: 'noopener' }, p.link[0], icon('out', 'i sm')));
  if (acts.childNodes.length) card.append(acts);
  return card;
}
function crasCard() {
  const C0 = AP.cras || {}, units = AP.pontos.filter(p => p.grupo === 'cras');
  const card = h('div', { class: 'card place-card ap-card t-social' });
  card.append(eyebrow('social'), h('h3', { text: 'CRAS · ' + units.length + ' unidades' }));
  if (C0.sub) card.append(h('p', { class: 'ap-sub', text: C0.sub }));
  if (C0.faz) card.append(fazList(C0.faz));
  if (C0.desc) card.append(h('p', { text: C0.desc }));
  if (C0.horario) card.append(h('p', { class: 'when' }, icon('clock', 'i sm'), h('span', { text: C0.horario })));
  card.append(h('ul', { class: 'cras-list' }, units.map(u => h('li', null,
    h('div', null, h('b', { text: u.nome }), h('span', { class: 's', text: u.end + ' · ' + u.bairro }),
      h('span', { class: 'tels' }, u.tel.map(([n], i) => [i ? ' · ' : '', h('a', { href: telHref(n), class: 'num', text: n })]))),
    u.lat != null ? h('button', { class: 'btn sm', type: 'button', onclick: () => focusApoio(u.id), 'aria-label': 'Ver ' + u.nome + ' no mapa' }, icon('map', 'i sm'), 'Mapa')
      : h('span', { class: 'badge-soft', text: 'sem ponto no mapa' })))));
  return card;
}
function renderApoioPage() {
  const el = $('#apoioDir'); if (!el) return;
  el.replaceChildren();
  for (const g of AP.grupos || []) {
    const grid = h('div', { class: 'grid2', style: 'margin-top:12px' });
    for (const id of g.itens) {
      if (id === 'cras') grid.append(crasCard());
      else if (id === 'online' && AP.online) grid.append(apCard(AP.online));
      else if (APBY[id]) grid.append(apCard(APBY[id]));
    }
    el.append(h('div', { class: 'sec' }, h('h2', { text: g.titulo }), grid));
  }
}
function renderSelection() {
  if (!selLayer) return;
  selLayer.clearLayers();
  if (S.route && S.route.cells) for (const id of S.route.cells) L.polygon(cellPoly(id), { renderer, interactive: false, color: C.ink, weight: 1.6, dashArray: '3 4', fill: false }).addTo(selLayer);
  if (S.selected) L.polygon(cellPoly(S.selected), { renderer, interactive: false, color: C.ink, weight: 3, fill: false }).addTo(selLayer);
}
function renderLegend() {
  const sc = SCALES[S.layer], el = $('#legend');
  const anyRecent = recentReports().some(periodOk);
  el.innerHTML = '<b>' + sc.title + '</b><div class="ramp">' + sc.vars.map((v, i) => '<span><i style="background:var(' + v + ')"></i>' + sc.labels[i] + '</span>').join('') + '</div>' +
    (S.layer !== 'relatos' && anyRecent ? '<div class="pinkey"><span class="pin faint" style="position:static;transform:none"></span>relatos recentes</div>' : '') +
    (APOIO.length ? '<button type="button" class="apkey' + (S.apoio ? ' on' : '') + '" aria-pressed="' + S.apoio + '" title="' + (S.apoio ? 'Esconder' : 'Mostrar') + ' delegacia, Guarda, assistência social, Justiça e saúde 24h">' +
      '<span class="sw">' + (S.apoio ? '<svg class="i" aria-hidden="true"><use href="#i-check"/></svg>' : '') + '</span>Onde pedir ajuda<span class="ics">' +
      AP_ORDER.map(t => '<span class="t-' + t + '">' + apSvg(t) + '</span>').join('') + '</span></button>' : '');
}
function renderNote() {
  const span = $('#mapNote span'), g = D.bo.grupos, p = D.pesq;
  if (S.layer === 'relatos') {
    const n = filteredReports().length;
    span.textContent = plural(n, 'relato', 'relatos') + ' nos últimos 30 dias com esses filtros. Cada relato mostra quando foi enviado e quantas mulheres confirmaram que ainda acontece.';
  } else if (S.layer === 'percepcao') {
    span.textContent = p.mapeadas + ' das ' + p.n + ' respostas citaram regiões que conseguimos localizar. Mostra onde as mulheres se sentem inseguras, não onde houve ocorrência.';
  } else {
    const fora = g.rural.n + D.bo.semGeo.n + g.placeholder.n + g.naoinf.n;
    span.textContent = fmtN(g.mapeado.n) + ' registros em áreas exibidas (outros ' + fora + ' não têm posição de bairro). São B.O. de violência doméstica e feminicídio: não indicam risco atual nem perigo na rua.';
  }
}
function renderEmptyHint() {
  const el = $('#emptyHint');
  if (S.layer !== 'relatos' || filteredReports().length || S.pick || S.routeMode) { el.hidden = true; return; }
  const none = !recentReports().length;
  el.replaceChildren(
    h('h3', null, none ? 'Ainda não há relatos nos últimos 30 dias' : 'Nenhum relato com esses filtros'),
    h('p', null, none ? 'Seja a primeira a avisar outras mulheres. Enquanto isso, veja onde 51 mulheres disseram se sentir inseguras.' : 'Tente outro horário ou tipo de situação.'),
    h('div', null,
      none ? h('button', { class: 'btn primary sm', type: 'button', onclick: relatar }, 'Registrar relato')
        : h('button', { class: 'btn primary sm', type: 'button', onclick: () => { S.period = 'todos'; S.tipo = 'todos'; syncControls(); renderMap(); } }, 'Limpar filtros'),
      h('button', { class: 'btn sm', type: 'button', onclick: () => setLayer('percepcao') }, 'Ver percepção'))
  );
  el.hidden = false;
}
function updateCounts() {
  const n = recentReports().length;
  $('#stRel').textContent = fmtN(n); $('#cntRel').textContent = fmtN(n);
  const badge = alertCount();
  for (const b of $$('[data-badge]')) { b.hidden = !badge; b.textContent = badge; }
}
function setLayer(l, user = true) { S.layer = l; if (user) S.userLayer = true; closePanel(); syncControls(); renderMap(); }

/* lista de áreas */
function areaSub(id, v) {
  if (S.layer === 'relatos') {
    const reps = filteredReports().filter(r => r.cell === id);
    const cnt = {}; for (const r of reps) for (const t of r.tipos) cnt[t] = (cnt[t] || 0) + 1;
    const top = Object.entries(cnt).sort((a, b) => b[1] - a[1])[0];
    return (top ? TIPO[top[0]].label : 'Relatos') + ' · mais recente ' + ago(reps[0].criado);
  }
  if (S.layer === 'percepcao') {
    const c = D.pesq.cells[id], hh = c.h || {};
    const topH = ['18-20', '20-22', '22-00', 'madrugada'].sort((a, b) => (hh[b] || 0) - (hh[a] || 0))[0];
    return c.a.map(x => x[0]).join(', ') + (hh[topH] ? ' · mais citado ' + PER[topH].long : '');
  }
  const c = D.bo.cells[id];
  const extra = [c.fe ? plural(c.fe, 'feminicídio', 'feminicídios') : '', c.te ? plural(c.te, 'tentativa', 'tentativas') : ''].filter(Boolean).join(', ');
  return 'B.O. · ' + c.b.slice(0, 2).map(x => x[0]).join(', ') + (extra ? ' · ' + extra : '');
}
function renderAreaList() {
  const ol = $('#areaList'), q = norm($('#areaSearch').value).trim(), sc = SCALES[S.layer];
  $('#areasTitle').textContent = { relatos: 'Áreas com relatos', percepcao: 'Áreas citadas na pesquisa', historico: 'Áreas com registros de B.O.' }[S.layer];
  let items = [...layerValues().entries()].map(([id, v]) => ({ id, v }));
  if (q) items = items.filter(it => cellSearchText(it.id).includes(q));
  items.sort((a, b) => b.v - a.v || areaName(a.id).localeCompare(areaName(b.id)));
  const lim = S.showAll || q ? items.length : 6;
  ol.replaceChildren();
  if (!items.length) ol.append(h('li', { class: 'none' }, q ? 'Nenhuma área encontrada com esse nome.' : 'Nenhuma área com dados para esse filtro.'));
  for (const it of items.slice(0, lim)) {
    const k = classOf(it.v, sc.breaks);
    ol.append(h('li', null, h('button', { type: 'button', onclick: () => focusCell(it.id) },
      h('span', { class: 'sw', style: 'background:var(' + sc.vars[Math.max(0, k)] + ')' }),
      h('span', null, h('span', { class: 'an', text: areaName(it.id) }), h('span', { class: 'as', text: areaSub(it.id, it.v) })),
      h('span', { class: 'av num', text: fmtN(it.v) }), icon('chev'))));
  }
  const more = $('#areaMore');
  more.hidden = items.length <= 6 || !!q;
  more.textContent = S.showAll ? 'Mostrar menos' : 'Mostrar todas as ' + items.length + ' áreas';
}
function focusCell(id) {
  showView('mapa');
  const c = cellCenter(id);
  map.flyTo(c, Math.max(map.getZoom(), 14), { duration: 0.6 });
  openPanel(id);
  if (isMobile()) $('#mapwrap').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/* ------------------------------------------------------------------ painel da área */
function closePanel() { $('#panel').hidden = true; S.selected = null; renderSelection(); if (S.apSel) { S.apSel = null; renderApoio(); } }
function voteRow(r) {
  const v = Store.votes[r.id] || { c: 0, p: 0, f: 0 }, mine = Store.myVotes[r.id];
  const mk = (key, ic, label, count) => h('button', { type: 'button', class: 'vote' + (mine === key ? ' on' : ''), 'aria-pressed': mine === key ? 'true' : 'false',
    title: Store.canVote() ? '' : 'Entre com uma conta com acesso de participação para confirmar',
    onclick: async () => {
      if (!Store.canVote()) { toast('Para confirmar relatos, é preciso acesso de participação a este protótipo.'); return; }
      try { await Store.vote(r.id, key); if (Store.myVotes[r.id] === key) toast(key === 'f' ? 'Obrigada. A equipe vai revisar este relato.' : 'Obrigada. Sua confirmação ajuda outras mulheres.'); }
      catch (e) { toast('Não consegui registrar agora. Tente de novo.'); }
    } }, icon(ic), label, count != null ? h('span', { class: 'num', text: '(' + count + ')' }) : null);
  return h('div', { class: 'votes' },
    mk('c', 'check', 'Ainda acontece', v.c),
    mk('p', 'clock', 'Não acontece mais', v.p),
    mk('f', 'flag', 'Informação falsa', Store.canEdit ? v.f : null));
}
function reportItem(r, { votes = true, preview = false, tag = 'li' } = {}) {
  const box = h(tag, { class: 'rep' });
  box.append(h('div', { class: 'tipos' }, r.tipos.map(t => h('span', { class: 'tipo', text: TIPO[t].label }))));
  const meta = [];
  if (!preview) meta.push('Relatado ' + ago(r.criado));
  if (r.quando) meta.push('aconteceu ' + QUANDO[r.quando]);
  if (r.periodo) meta.push(PER[r.periodo].long);
  if (meta.length) box.append(h('div', { class: 'meta', text: cap(meta.join(' · ')) }));
  if (r.texto) box.append(h('p', { class: 'txt', text: r.texto }));
  if (!preview) {
    const flags = h('div', { class: 'flags' });
    if (Store.mod.verificado[r.id]) flags.append(h('span', { class: 'badge-ok' }, icon('shield', 'i sm'), 'Verificado pela equipe'));
    else flags.append(h('span', { class: 'badge-soft', text: 'Relato de uma usuária · não verificado' }));
    if (isHidden(r)) flags.append(h('span', { class: 'badge-warn', text: 'Fora do mapa até revisão' }));
    if (Store.perfil.meus.includes(r.id)) flags.append(h('span', { class: 'badge-soft', text: 'Enviado por você' }));
    box.append(flags);
    if (votes) box.append(voteRow(r));
  }
  return box;
}
function openPanel(id) {
  if (S.route && S.route.cells) clearRoute(true);
  S.selected = id; renderSelection();
  if (S.apSel) { S.apSel = null; renderApoio(); }
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; P.dataset.cell = id; P.dataset.kind = 'area';
  const follow = Store.perfil.areas.includes(id);
  P.append(h('header', null,
    h('div', null, h('small', null, 'Área · célula de ~1 km'), h('h3', { text: areaName(id) })),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: closePanel }, icon('x'))));
  const body = h('div', { class: 'body' });
  const reps = recentReports().filter(r => r.cell === id);
  const sec1 = h('div', { class: 'psec' }, h('h4', null, 'Relatos recentes', h('span', { class: 'tag', text: reps.length ? plural(reps.length, 'em 30 dias', 'em 30 dias') : '' })));
  if (reps.length) {
    const night = reps.filter(r => ['18-20', '20-22', '22-00', 'madrugada'].includes(r.periodo)).length;
    if (reps.length > 1) sec1.append(h('p', null, plural(reps.length, 'relato', 'relatos') + ' nesta área' + (night ? ', ' + night + ' à noite ou de madrugada' : '') + '.'));
    const ul = h('ul', { class: 'reports' }); for (const r of reps.slice(0, 12)) ul.append(reportItem(r)); sec1.append(ul);
  } else sec1.append(h('p', null, 'Nenhum relato nos últimos 30 dias nesta área.'));
  body.append(sec1);
  const pc = D.pesq.cells[id];
  if (pc) {
    const hh = pc.h || {}, maxH = Math.max(1, ...['18-20', '20-22', '22-00', 'madrugada'].map(k => hh[k] || 0));
    const bars = h('div', { class: 'hbars' });
    for (const k of ['18-20', '20-22', '22-00', 'madrugada']) bars.append(h('div', { class: 'hbar' }, h('span', { text: PER[k].label }), h('i', { style: 'width:' + (100 * (hh[k] || 0) / maxH) + '%' }), h('em', { class: 'num', text: hh[k] || 0 })));
    body.append(h('div', { class: 'psec' }, h('h4', null, 'Percepção da pesquisa'),
      h('p', null, h('b', { text: plural(pc.n, 'mulher citou', 'mulheres citaram') }), ' esta região como insegura (' + pc.a.map(x => x[0]).join(', ') + ').'),
      h('small', null, 'Horários em que a região gera mais insegurança, segundo quem a citou:'), bars));
  }
  const bo = D.bo.cells[id];
  if (bo) {
    body.append(h('div', { class: 'psec' }, h('h4', null, 'Registros de B.O.', h('span', { class: 'tag', text: 'jan 2025 – abr 2026' })),
      h('p', null, h('b', { text: plural(bo.n, 'registro', 'registros') }), ': ' + [bo.vd ? plural(bo.vd, 'de violência doméstica', 'de violência doméstica') : '', bo.fe ? plural(bo.fe, 'feminicídio', 'feminicídios') : '', bo.te ? plural(bo.te, 'tentativa de feminicídio', 'tentativas de feminicídio') : ''].filter(Boolean).join(', ') + '.'),
      h('p', null, 'Bairros: ' + bo.b.slice(0, 5).map(x => x[0] + ' (' + x[1] + ')').join(', ') + (bo.b.length > 5 ? '…' : '')),
      h('small', null, 'Violência doméstica acontece sobretudo dentro de casa. Esses números mostram onde a rede de apoio é mais necessária, não perigo na rua.')));
  }
  if (!pc && !bo && !reps.length) body.append(h('p', { class: 'muted', style: 'padding:14px 0' }, 'Ainda não há relatos, menções na pesquisa ou registros de B.O. nesta área.'));
  if (APOIO.length) body.append(h('div', { class: 'psec' }, h('h4', null, 'Ajuda mais perto', h('span', { class: 'tag', text: 'do centro da área, em linha reta' })),
    h('ul', { class: 'aplist' }, nearestByNeed(cellCenter(id)).map(({ p, d }) => apRow(p, fmtDist(d)))),
    h('small', null, 'Em perigo agora, ligue 190.')));
  P.append(body);
  P.append(h('div', { class: 'actions' },
    h('button', { class: 'btn primary', type: 'button', onclick: () => { Chat.startWithCell(id); openChat(); } }, icon('chat'), 'Registrar relato aqui'),
    h('button', { class: 'btn' + (follow ? ' soft' : ''), type: 'button', onclick: () => toggleFollow(id) }, icon(follow ? 'check' : 'bell'), follow ? 'Acompanhando' : 'Acompanhar'),
    h('button', { class: 'btn', type: 'button', onclick: () => routeFrom(id) }, icon('route'), 'Trajeto daqui')));
}
function refreshPanel() {
  const P = $('#panel'); if (P.hidden) return;
  if (P.dataset.kind === 'area' && P.dataset.cell) { const sc = P.querySelector('.body').scrollTop; openPanel(P.dataset.cell); P.querySelector('.body').scrollTop = sc; }
  else if (P.dataset.kind === 'route' && S.route && S.route.cells) renderRoutePanel();
}
function toggleFollow(id, force) {
  const a = new Set(Store.perfil.areas), on = force != null ? force : !a.has(id);
  if (on) a.add(id); else a.delete(id);
  Store.perfil.areas = [...a]; Store.savePerfil(); Store.emit();
  toast(on ? 'Você está acompanhando ' + areaName(id) + '. As novidades aparecem em Meus alertas.' : 'Você parou de acompanhar esta área.');
}

/* ------------------------------------------------------------------ trajeto (linha reta) */
function startRoute() {
  closePanel(); stopPick();
  S.routeMode = true; S.route = { a: null, b: null, cells: null };
  routeLayer.clearLayers();
  $('#routebar').hidden = false; $('#routeMsg').textContent = 'Toque no ponto de partida';
  $('#btnRoute').classList.add('on'); map.getContainer().classList.add('picking');
  renderEmptyHint();
}
function routeFrom(id) { startRoute(); routeClick(L.latLng(...cellCenter(id))); }
function endMarker(ll, t) { return L.marker(ll, { icon: L.divIcon({ className: '', html: '<span class="route-end">' + t + '</span>', iconSize: [0, 0] }), interactive: false, keyboard: false }); }
function routeClick(ll) {
  if (!S.route.a) { S.route.a = ll; endMarker(ll, 'A').addTo(routeLayer); $('#routeMsg').textContent = 'Agora toque no destino'; return; }
  S.route.b = ll; S.routeMode = false; map.getContainer().classList.remove('picking');
  endMarker(ll, 'B').addTo(routeLayer);
  L.polyline([S.route.a, S.route.b], { renderer, interactive: false, color: C.ink, weight: 3, dashArray: '8 7', opacity: 0.85 }).addTo(routeLayer);
  const a = toXY(S.route.a.lat, S.route.a.lng), b = toXY(S.route.b.lat, S.route.b.lng);
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]), steps = Math.max(2, Math.ceil(len / 60)), cells = [];
  for (let i = 0; i <= steps; i++) { const t = i / steps; const id = cellOf(...toLL(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)); if (!cells.includes(id)) cells.push(id); }
  S.route.cells = cells; S.route.len = len;
  $('#routebar').hidden = true;
  map.fitBounds(L.latLngBounds([S.route.a, S.route.b]).pad(0.35), { maxZoom: 15 });
  renderSelection(); renderRoutePanel();
}
function renderRoutePanel() {
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; P.dataset.kind = 'route'; delete P.dataset.cell;
  const cells = S.route.cells, reps = recentReports().filter(periodOk), per = activePeriod();
  const rows = cells.map(id => ({ id, rel: reps.filter(r => r.cell === id).length, pc: D.pesq.cells[id] ? percValue(D.pesq.cells[id]) : 0, bo: (D.bo.cells[id] || {}).n || 0 }));
  const withRel = rows.filter(r => r.rel), withPc = rows.filter(r => r.pc);
  P.append(h('header', null,
    h('div', null, h('small', null, (S.route.len / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' km em linha reta · ' + (per === 'todos' ? 'qualquer horário' : PER[per].long)), h('h3', { text: plural(cells.length, 'área no caminho', 'áreas no caminho') })),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: () => clearRoute() }, icon('x'))));
  const body = h('div', { class: 'body' });
  body.append(h('div', { class: 'psec' },
    h('p', null, h('b', { text: withRel.length ? plural(withRel.length, 'área com relatos recentes', 'áreas com relatos recentes') : 'Nenhum relato recente no caminho' }), withPc.length ? ' · ' + plural(withPc.length, 'área citada', 'áreas citadas') + ' na pesquisa' : ''),
    h('small', null, 'Linha reta aproximada entre os dois pontos. Não indica uma rota segura: use como referência antes de sair. Mude o horário nos filtros acima para comparar.')));
  const ul = h('ul', { class: 'reports' });
  for (const r of rows) {
    const bits = [r.rel ? plural(r.rel, 'relato recente', 'relatos recentes') : '', r.pc ? plural(r.pc, 'menção na pesquisa', 'menções na pesquisa') : '', r.bo ? plural(r.bo, 'registro de B.O.', 'registros de B.O.') : ''].filter(Boolean);
    ul.append(h('li', { class: 'rep', style: r.rel ? 'border-color:var(--amb-3)' : '' },
      h('div', { style: 'display:flex;justify-content:space-between;gap:8px;align-items:center' }, h('b', { text: areaName(r.id) }), h('button', { class: 'btn sm ghost', type: 'button', onclick: () => openPanel(r.id) }, 'Ver')),
      h('div', { class: 'meta', text: bits.length ? bits.join(' · ') : 'Sem dados nesta área' })));
  }
  body.append(h('div', { class: 'psec' }, ul));
  P.append(body);
  P.append(h('div', { class: 'actions' },
    h('button', { class: 'btn', type: 'button', onclick: startRoute }, icon('route'), 'Novo trajeto'),
    h('button', { class: 'btn', type: 'button', onclick: () => clearRoute() }, 'Limpar')));
}
function clearRoute(keepPanel) {
  S.routeMode = false; S.route = null; routeLayer.clearLayers();
  $('#routebar').hidden = true; $('#btnRoute').classList.remove('on'); map.getContainer().classList.remove('picking');
  if (!keepPanel) $('#panel').hidden = true;
  renderSelection(); renderEmptyHint();
}

/* ------------------------------------------------------------------ marcar local para o chat */
function startPick(cb) {
  if (S.routeMode || (S.route && S.route.a)) clearRoute();
  closePanel(); S.pick = cb;
  $('#pickbar').hidden = false; map.getContainer().classList.add('picking');
  $('#chat').classList.add('picking');
  document.body.style.overflow = '';
  renderEmptyHint();
  $('#mapwrap').scrollIntoView({ behavior: 'smooth', block: 'center' });
}
function stopPick() {
  S.pick = null; $('#pickbar').hidden = true;
  if (map) map.getContainer().classList.remove('picking');
  $('#chat').classList.remove('picking'); renderEmptyHint();
}
function showMe(ll) {
  if (!meMarker) meMarker = L.marker(ll, { icon: L.divIcon({ className: '', html: '<span class="youare"></span>', iconSize: [0, 0] }), interactive: false, keyboard: false }).addTo(map);
  else meMarker.setLatLng(ll);
}

/* ------------------------------------------------------------------ chat da Aurora */
const Chat = {
  log: null, quick: null, draft: null, step: 'inicio', busy: false, sample: null, aiOn: false, lastCell: null,
  init() {
    this.log = $('#chatLog'); this.quick = $('#chatQuick');
    const ta = $('#chatText');
    $('#chatForm').addEventListener('submit', e => { e.preventDefault(); this.submit(); });
    ta.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.submit(); } });
    ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = Math.min(120, ta.scrollHeight) + 'px'; });
    this.start();
    if (HAS_CLAUDE) window.claude.use('sample').then(s => { this.sample = s || null; this.setAI(!!s); }).catch(() => this.setAI(false));
  },
  setAI(on) { this.aiOn = on; const el = $('#aiState'); el.classList.toggle('on', on); el.textContent = on ? 'Texto livre com IA' : 'Texto livre: modo simples'; },
  newDraft() { return { tipos: [], cell: null, sug: null, quando: null, periodo: null, periodoAsked: false, texto: '', removidos: [], detalhesAsked: false, origem: 'chat' }; },
  bot(content, cls = '') {
    const m = h('div', { class: 'msg bot ' + cls });
    if (typeof content === 'string') m.textContent = content; else m.append(...[].concat(content));
    this.log.append(m); this.scroll(); return m;
  },
  me(text) { this.log.append(h('div', { class: 'msg me', text })); this.scroll(); },
  card(node) { const m = h('div', { class: 'msg card' }, node); this.log.append(m); this.scroll(); return m; },
  scroll() { requestAnimationFrame(() => { this.log.scrollTop = this.log.scrollHeight; }); },
  clearQuick() { this.quick.replaceChildren(); },
  options(list, grid = false) {
    this.clearQuick();
    const wrap = grid ? h('div', { class: 'qgrid' }) : this.quick;
    for (const o of list) wrap.append(h('button', { type: 'button', class: 'qr' + (o.primary ? ' primary' : '') + (o.quiet ? ' quiet' : ''), onclick: () => o.go() }, o.label));
    if (grid) this.quick.append(wrap);
  },
  start() {
    this.draft = this.newDraft(); this.step = 'inicio'; this.busy = false;
    this.log.replaceChildren(); this.clearQuick();
    this.bot([h('span', null, 'Oi! Eu sou a Aurora. Te ajudo a registrar uma situação em Rio Claro para alertar outras mulheres. Você escolhe o que compartilhar.'),
      h('span', { class: 'note', text: 'Este relato não é um boletim de ocorrência. Em emergência, ligue 190.' })]);
    this.options([
      { label: 'Registrar uma situação', primary: true, go: () => { this.me('Quero registrar uma situação'); this.askTipo(); } },
      { label: 'Estou em perigo agora', go: () => { this.me('Estou em perigo agora'); this.emergency(false); } },
      { label: 'Onde buscar apoio', go: () => { this.me('Onde buscar apoio?'); this.support(); } }
    ]);
  },
  startWithCell(id) {
    this.draft = this.newDraft(); this.draft.cell = id; this.step = 'tipo';
    this.bot('Vamos registrar um relato em ' + areaName(id) + '.');
    this.askTipo();
  },
  next() {
    const d = this.draft;
    if (!d.tipos.length) return this.askTipo();
    if (!d.cell) return this.askOnde();
    if (!d.quando) return this.askQuando();
    if (!d.periodo && !d.periodoAsked) return this.askPeriodo();
    if (!d.detalhesAsked) return this.askDetalhes();
    return this.review();
  },
  askTipo() {
    this.step = 'tipo';
    this.bot('Qual foi o tipo de situação? Pode escolher mais de uma.');
    const sel = new Set(this.draft.tipos), grid = h('div', { class: 'qgrid' });
    const go = h('button', { type: 'button', class: 'qr primary' }, 'Continuar');
    const upd = () => { go.disabled = !sel.size; };
    go.onclick = () => { if (!sel.size) return; this.draft.tipos = TIPOS.filter(t => sel.has(t.id)).map(t => t.id); this.me(this.draft.tipos.map(t => TIPO[t].label).join(', ')); this.next(); };
    for (const t of TIPOS) {
      const b = h('button', { type: 'button', class: 'qr' + (sel.has(t.id) ? ' on' : ''), 'aria-pressed': sel.has(t.id) ? 'true' : 'false' }, t.long || t.label);
      b.onclick = () => { if (sel.has(t.id)) sel.delete(t.id); else if (sel.size < 4) sel.add(t.id); b.classList.toggle('on', sel.has(t.id)); b.setAttribute('aria-pressed', sel.has(t.id) ? 'true' : 'false'); upd(); };
      grid.append(b);
    }
    upd(); this.clearQuick(); this.quick.append(grid, go);
  },
  askOnde() {
    this.step = 'onde';
    const s = this.draft.sug;
    this.clearQuick();
    if (s) {
      this.bot('Pelo que você contou, foi perto de ' + s.nome + '. Posso marcar a área "' + areaName(s.cell) + '"?');
      S.selected = s.cell; renderSelection();
      this.quick.append(
        h('button', { type: 'button', class: 'qr primary', onclick: () => { this.draft.sug = null; this.setCell(s.cell, 'Sim, pode marcar'); } }, 'Sim, pode marcar essa área'),
        h('button', { type: 'button', class: 'qr', onclick: () => { this.draft.sug = null; this.pickOnMap(); } }, 'Prefiro marcar no mapa'),
        this.bairroSearch());
      return;
    }
    this.bot([h('span', null, 'Onde foi? Marque no mapa ou busque o bairro.'), h('span', { class: 'note', text: 'Eu guardo só a região, uma célula de cerca de 1 km. Nunca o endereço.' })]);
    this.quick.append(h('button', { type: 'button', class: 'qr primary', onclick: () => this.pickOnMap() }, 'Marcar no mapa'), this.bairroSearch());
  },
  bairroSearch() {
    const wrap = h('div', { class: 'bsearch' });
    const inp = h('input', { type: 'search', id: 'bairroInput', placeholder: 'Ou busque o bairro (ex.: Bela Vista)', 'aria-label': 'Buscar bairro' });
    const ul = h('ul');
    inp.addEventListener('input', () => {
      ul.replaceChildren(); const q = inp.value.trim(); if (q.length < 2) return;
      const res = searchBairros(q).slice(0, 6);
      for (const b of res) ul.append(h('li', null, h('button', { type: 'button', onclick: () => { this.draft.sug = null; this.setCell(cellOf(b.lat, b.lng), b.nome); } }, b.nome)));
      if (!res.length) ul.append(h('li', { class: 'muted', style: 'font-size:14px;padding:6px 2px' }, 'Não achei esse bairro. Tente marcar no mapa.'));
    });
    wrap.append(inp, ul); return wrap;
  },
  pickOnMap() {
    showView('mapa');
    this.bot('Toque no mapa na área onde aconteceu.');
    startPick(id => { openChat(); this.setCell(id); });
  },
  setCell(id, via) {
    this.draft.cell = id; S.selected = id; renderSelection();
    this.me(via ? via : 'Marquei no mapa');
    this.bot('Anotado: ' + areaName(id) + '. No mapa aparece só essa região.');
    this.next();
  },
  askQuando() {
    this.step = 'quando';
    this.bot('Quando aconteceu?');
    this.options(Object.entries(QUANDO).map(([k, lbl]) => ({ label: cap(lbl), go: () => { this.draft.quando = k; this.me(cap(lbl)); this.next(); } })), true);
  },
  askPeriodo() {
    this.step = 'periodo';
    this.bot('E em que horário, mais ou menos?');
    const opts = PERIODOS.map(p => ({ label: p.long, go: () => { this.draft.periodo = p.id; this.draft.periodoAsked = true; this.me(p.long); this.next(); } }));
    opts.push({ label: 'Não lembro', quiet: true, go: () => { this.draft.periodoAsked = true; this.me('Não lembro'); this.next(); } });
    this.options(opts, true);
  },
  askDetalhes() {
    this.step = 'detalhes';
    const d = this.draft;
    if (d.texto) {
      const q = h('span', { style: 'display:block;margin:8px 0;font-style:italic' }); q.textContent = '“' + d.texto + '”';
      this.bot([h('span', null, 'Vou usar esta descrição, já sem dados pessoais:'), q, h('span', null, 'Quer manter?')]);
      this.options([
        { label: 'Manter', primary: true, go: () => { d.detalhesAsked = true; this.me('Manter'); this.next(); } },
        { label: 'Escrever outra', go: () => { d.texto = ''; d.removidos = []; this.me('Escrever outra'); this.askDetalhes(); } },
        { label: 'Publicar sem descrição', quiet: true, go: () => { d.texto = ''; d.removidos = []; d.detalhesAsked = true; this.me('Sem descrição'); this.next(); } }
      ]);
      return;
    }
    this.bot([h('span', null, 'Quer contar algo que ajude outras mulheres? É opcional.'),
      h('span', { class: 'note', text: 'Escreva abaixo. Evite nomes, telefones, placas e endereço exato: eu tiro o que escapar antes de publicar.' })]);
    this.options([{ label: 'Pular esta parte', quiet: true, go: () => { d.detalhesAsked = true; this.me('Pular'); this.next(); } }]);
    if (!isMobile()) $('#chatText').focus();
  },
  async submit() {
    const ta = $('#chatText'), text = ta.value.trim();
    if (!text || this.busy) return;
    ta.value = ''; ta.style.height = 'auto';
    this.me(text);
    if (this.step === 'fim' || this.step === 'inicio') this.draft = this.newDraft();
    if (this.step === 'onde') {
      const b = findBairroInText(text);
      if (b) { this.draft.sug = { cell: cellOf(b.lat, b.lng), nome: b.nome }; return this.askOnde(); }
    }
    if (this.step === 'detalhes') return this.processDetails(text);
    if (this.step === 'revisao') { this.draft.texto = ''; this.draft.removidos = []; this.bot('Vou usar o que você escreveu como nova descrição.'); return this.processDetails(text); }
    return this.understand(text);
  },
  async understand(text) {
    this.busy = true;
    const typing = this.aiOn ? this.bot('Lendo o que você escreveu…', 'typing') : null;
    const heur = heuristic(text);
    let res = this.aiOn ? await aiExtract(text, this) : null;
    if (typing) typing.remove();
    if (res) { if (!res.bairro) res.bairro = heur.bairro; if (!res.tipos.length) res.tipos = heur.tipos; }
    else res = heur;
    this.busy = false;
    if (res.urgente) this.emergency(true);
    const d = this.draft, got = [];
    if (res.tipos.length && !d.tipos.length) { d.tipos = res.tipos; got.push(res.tipos.map(t => TIPO[t].label).join(', ')); }
    if (res.quando && !d.quando) { d.quando = res.quando; got.push('aconteceu ' + QUANDO[res.quando]); }
    if (res.periodo && !d.periodo) { d.periodo = res.periodo; d.periodoAsked = true; got.push(PER[res.periodo].long); }
    if (res.descricao && !d.texto) { const sc = scrub(res.descricao); d.texto = sc.text.slice(0, 300); d.removidos = [...new Set([...(res.removidos || []), ...sc.removed])]; }
    if (res.fromAI) d.origem = 'chat-ia';
    if (res.bairro && !d.cell) { d.sug = { cell: cellOf(res.bairro.lat, res.bairro.lng), nome: res.bairro.nome }; got.push('perto de ' + res.bairro.nome); }
    if (res.resposta) this.bot(res.resposta);
    if (got.length) this.bot('Anotei: ' + got.join(' · ') + '. Agora faltam alguns detalhes.');
    else if (!res.resposta) this.bot('Obrigada por contar. Vou te fazer perguntas rápidas para organizar o relato.');
    this.next();
  },
  async processDetails(text) {
    this.busy = true;
    const d = this.draft;
    let texto = text.slice(0, 700), removidos = [];
    if (this.aiOn) {
      const t = this.bot('Revisando o texto para tirar dados pessoais…', 'typing');
      const res = await aiExtract(text, this);
      t.remove();
      if (res && res.descricao) {
        texto = res.descricao; removidos = res.removidos; d.origem = 'chat-ia';
        if (res.urgente) this.emergency(true);
        if (!d.periodo && res.periodo) { d.periodo = res.periodo; d.periodoAsked = true; }
      }
    }
    const sc = scrub(texto);
    d.texto = sc.text.slice(0, 300); d.removidos = [...new Set([...removidos, ...sc.removed])]; d.detalhesAsked = true;
    this.busy = false;
    this.next();
  },
  review() {
    this.step = 'revisao';
    const d = this.draft;
    const r = { id: 'preview', tipos: d.tipos, cell: d.cell, quando: d.quando, periodo: d.periodo, texto: d.texto, criado: Date.now() };
    const box = h('div', { class: 'preview' }, h('h5', null, 'Como vai aparecer no mapa'), h('b', { text: areaName(d.cell) }), reportItem(r, { preview: true, tag: 'div' }));
    if (d.removidos.length) box.append(h('p', { class: 'removed' }, icon('shield', 'i sm'), 'Tirei do texto: ' + d.removidos.join(', ') + '.'));
    box.append(h('p', { class: 'muted', style: 'font-size:13px' }, 'Publicado sem nome, contato ou local exato. Fica visível no mapa por 30 dias.'));
    this.bot('Confira antes de publicar:');
    this.card(box);
    this.clearQuick();
    const pub = h('button', { class: 'qr primary', type: 'button' }, 'Publicar relato');
    pub.onclick = () => this.publish(pub);
    const edit = (label, fn) => h('button', { class: 'qr quiet', type: 'button', onclick: fn }, label);
    this.quick.append(pub, h('div', { class: 'qgrid' },
      edit('Mudar tipo', () => { d.tipos = []; this.askTipo(); }),
      edit('Mudar local', () => { d.cell = null; d.sug = null; this.askOnde(); }),
      edit('Mudar horário', () => { d.quando = null; d.periodo = null; d.periodoAsked = false; this.askQuando(); }),
      edit('Mudar texto', () => { d.texto = ''; d.removidos = []; d.detalhesAsked = false; this.askDetalhes(); })));
    if (Store.mode === 'db' && !Store.canWrite) this.bot('Atenção: sua conta pode ver o mapa, mas talvez não possa publicar neste protótipo. Se der erro, peça à equipe acesso de participação.');
  },
  async publish(btn) {
    btn.disabled = true; btn.textContent = 'Publicando…';
    const d = this.draft;
    const r = { v: 1, tipos: d.tipos, cell: d.cell, quando: d.quando, periodo: d.periodo || null, texto: scrub(d.texto).text.slice(0, 300), criado: Date.now(), origem: d.origem };
    try {
      await Store.addReport(r);
      this.lastCell = d.cell; this.done();
    } catch (e) {
      btn.disabled = false; btn.textContent = 'Publicar relato';
      const c = e && e.code;
      this.bot(c === 'invalid_argument' ? 'Sua conta pode ver o mapa, mas não tem permissão para publicar relatos neste protótipo. Peça à equipe acesso de participação.'
        : c === 'quota_exceeded' ? 'O protótipo atingiu o limite de relatos guardados. Avise a equipe responsável.'
        : 'Não consegui publicar agora. Tente de novo em instantes.');
    }
  },
  done() {
    this.step = 'fim';
    this.bot([h('b', null, 'Relato publicado.'), ' Obrigada por avisar outras mulheres. Ele aparece no mapa por 30 dias.']);
    S.period = 'todos'; S.tipo = 'todos'; setLayer('relatos');
    const cell = this.lastCell;
    this.options([
      { label: 'Ver no mapa', primary: true, go: () => { closeChat(); focusCell(cell); } },
      { label: 'Acompanhar esta área', go: () => { toggleFollow(cell, true); this.bot('Pronto. As novidades dessa área aparecem em Meus alertas.'); } },
      { label: 'Fazer um B.O. online', go: () => { this.me('Quero fazer um B.O. online'); this.boOnline(); } },
      { label: 'Onde buscar apoio', go: () => { this.me('Onde buscar apoio?'); this.support(); } },
      { label: 'Registrar outra situação', quiet: true, go: () => this.start() }
    ]);
  },
  emergency(auto) {
    const row = (n, l) => h('div', { class: 'num-row' }, h('div', null, h('strong', { class: 'num', text: n }), ' ', h('span', { text: l })),
      h('button', { class: 'btn sm', type: 'button', 'data-copy': n }, icon('copy', 'i sm'), 'Copiar'));
    this.card(h('div', { class: 'emerg' }, h('b', null, 'Se você está em perigo agora, peça ajuda:'),
      row('190', 'Polícia Militar'), row('180', 'Central de Atendimento à Mulher'), row('153', 'Guarda Civil Municipal'),
      h('span', { style: 'font-size:14px;color:var(--ink-2)' }, 'Se puder, vá para um lugar movimentado e iluminado e avise alguém de confiança.')));
    if (!auto) this.options([{ label: 'Registrar uma situação', go: () => this.askTipo() }, { label: 'Voltar ao início', quiet: true, go: () => this.start() }]);
  },
  support() {
    this.bot('Em Rio Claro, a Delegacia da Mulher fica na Av. 23, 1300, no Bairro do Estádio, e registra boletim e pedido de medida protetiva. Para conversar e ter acompanhamento, há o CREAS (Rua 6, 640) e a Secretaria da Mulher (Rua 7, 830, WhatsApp (19) 99956-3042). O 180 orienta 24 horas, de graça.');
    this.options([
      { label: 'Ver os pontos no mapa', primary: true, go: () => showApoioOnMap() },
      { label: 'Ver todos os contatos', go: () => { closeChat(); showView('apoio'); } },
      { label: 'Voltar', quiet: true, go: () => this.resume() }
    ]);
  },
  boOnline() {
    this.bot([h('span', null, 'O boletim de ocorrência pode ser feito pela internet, 24 horas, na Delegacia Eletrônica da Polícia Civil de SP. '),
      h('a', { href: 'https://www.delegaciaeletronica.policiacivil.sp.gov.br', target: '_blank', rel: 'noopener' }, 'Abrir o site da Polícia Civil'),
      h('span', { class: 'note', text: 'O relato na Aurora não é enviado à polícia.' })]);
    this.options([{ label: 'Voltar', quiet: true, go: () => this.resume() }]);
  },
  resume() { if (this.step === 'fim' || this.step === 'inicio') this.start(); else this.next(); }
};

/* extração de campos sem IA (palavras-chave) */
function heuristic(text) {
  const t = norm(text);
  const tipos = TIPOS.filter(x => x.kw && x.kw.test(t)).map(x => x.id).slice(0, 3);
  let quando = null;
  if (/\bhoje\b|agora ha pouco|agorinha|agora pouco/.test(t)) quando = 'hoje';
  else if (/\bontem\b/.test(t)) quando = 'ontem';
  else if (/semana passada|mes passado|\bmeses\b|faz tempo|ano passado|ha \d+ semanas/.test(t)) quando = 'antes';
  else if (/(essa|esta|nesta) semana|anteontem|segunda|terca|quarta|quinta|sexta|sabado|domingo/.test(t)) quando = 'semana';
  let periodo = null;
  const hm = t.match(/\b(\d{1,2})\s?(?:h\b|hs\b|horas|:\d{2}|da (noite|manha|tarde))/);
  if (hm) { let hr = +hm[1]; if ((hm[2] === 'noite' || hm[2] === 'tarde' || /\bnoite\b/.test(t)) && hr < 12 && hr >= 1) hr += 12; if (hr === 24) hr = 0; if (hr >= 0 && hr < 24) periodo = periodOfHour(hr); }
  if (!periodo) { if (/madrugada/.test(t)) periodo = 'madrugada'; else if (/meia[- ]?noite/.test(t)) periodo = '22-00'; else if (/de manha|pela manha|\bmanha\b/.test(t)) periodo = 'manha'; else if (/a tarde|de tarde|\btarde\b/.test(t)) periodo = 'tarde'; }
  const sc = scrub(text);
  const urgente = /(estou|to|estamos) (sendo seguid|em perigo|com medo agora)|socorro|me ajud(a|em) agora|agora mesmo/.test(t);
  return { urgente, tipos, bairro: findBairroInText(text), quando, periodo, descricao: sc.text.slice(0, 300), removidos: sc.removed, resposta: '', fromAI: false };
}

/* extração com IA (capacidade "sample" do link publicado; roda na conta de quem usa) */
async function aiExtract(text, chat) {
  if (!chat.sample) return null;
  const nomes = BAIRROS.map(b => b.nome).join('; ');
  const prompt = 'Você é a Aurora, assistente de um mapa colaborativo de segurança para mulheres em Rio Claro (SP). Uma mulher escreveu a mensagem abaixo para registrar uma situação. Extraia os campos e reescreva a descrição sem dados pessoais.\n\n' +
    'Regras:\n' +
    '- descricao: 1 ou 2 frases em primeira pessoa, até 220 caracteres, em português, só com o que está na mensagem. Tire nomes, apelidos, telefones, e-mails, CPF, placas de veículos, perfis de redes sociais, números de casa, endereços exatos e nomes de estabelecimentos que identifiquem alguém. Tire características físicas muito específicas de uma pessoa (tatuagens, roupas únicas). Mantenha descrições genéricas, como "um homem de moto". Não acuse ninguém pelo nome e não invente detalhes. Se a mensagem não descreve uma situação, use "".\n' +
    '- tipos: ids desta lista, no máximo 3: assedio (assédio verbal), perseguicao (perseguição, me seguiram), abordagem (abordagem indesejada, insistência), intimidacao (encarar, intimidar), exposicao (exposição sexual), roubo (roubo ou furto), violencia (violência física), veiculo (carro, moto, app de transporte ou motorista envolvido), ambiente (rua escura, deserta, sem iluminação), outra.\n' +
    '- bairro: se a mensagem citar um lugar de Rio Claro, o nome mais próximo desta lista; senão null. Referências: Unesp = "Bela Vista"; Lago Azul = "Vila Operária"; Rodoviária = "Jardim Claret"; Estação ou Jardim Público = "Centro". Lista: ' + nomes + '\n' +
    '- quando: "hoje", "ontem", "semana" (nesta semana) ou "antes" (há mais de uma semana); null se não disser.\n' +
    '- periodo: "manha" (6h-12h), "tarde" (12h-18h), "18-20", "20-22", "22-00" ou "madrugada" (0h-6h); null se não der para saber ("à noite" sem hora = null).\n' +
    '- urgente: true só se ela disser que está em perigo neste momento.\n' +
    '- removidos: lista curta do que você tirou do texto (ex.: "nome", "placa", "telefone"); [] se nada.\n' +
    '- resposta: uma frase curta, acolhedora e sem julgamento, falando com ela.\n\n' +
    'Responda só com JSON neste formato:\n{"urgente":false,"tipos":[],"bairro":null,"quando":null,"periodo":null,"descricao":"","removidos":[],"resposta":""}\n\n' +
    'Mensagem:\n"""' + text.slice(0, 1500).replace(/"""/g, '"') + '"""';
  try {
    const o = await chat.sample.json(prompt, { modelTier: 'quick' });
    if (!o || typeof o !== 'object') return null;
    return {
      urgente: o.urgente === true,
      tipos: Array.isArray(o.tipos) ? o.tipos.map(String).filter(t => TIPO[t]).slice(0, 3) : [],
      bairro: typeof o.bairro === 'string' ? matchBairro(o.bairro) : null,
      quando: QUANDO[o.quando] ? o.quando : null,
      periodo: PER[o.periodo] ? o.periodo : null,
      descricao: typeof o.descricao === 'string' ? o.descricao.trim().slice(0, 300) : '',
      removidos: Array.isArray(o.removidos) ? o.removidos.map(x => String(x).slice(0, 30)).slice(0, 6) : [],
      resposta: typeof o.resposta === 'string' ? o.resposta.trim().slice(0, 220) : '',
      fromAI: true
    };
  } catch (e) {
    const c = e && e.code;
    if (['not_granted', 'sampling_disabled', 'not_declared', 'capability_disabled', 'capability_removed'].includes(c)) { chat.setAI(false); chat.sample = null; }
    else if (c === 'rate_limited') toast('A IA está ocupada agora. Segui no modo simples.');
    return null;
  }
}

function relatar() {
  showView('mapa');
  openChat();
  if (Chat.step === 'inicio' || Chat.step === 'fim') { if (Chat.step === 'fim') Chat.start(); Chat.me('Quero registrar uma situação'); Chat.askTipo(); }
}
function openChat() {
  const c = $('#chat'); c.classList.remove('picking');
  if (isMobile()) { c.classList.add('open'); document.body.style.overflow = 'hidden'; }
  else if (c.animate && !matchMedia('(prefers-reduced-motion: reduce)').matches) c.animate([{ boxShadow: 'inset 0 0 0 3px ' + cssVar('--brand') }, { boxShadow: 'inset 0 0 0 0 transparent' }], { duration: 900 });
}
function closeChat() { $('#chat').classList.remove('open'); document.body.style.overflow = ''; }

/* ------------------------------------------------------------------ páginas */
function showView(v) {
  if (v === 'moderacao' && !canModerate()) v = 'mapa';
  S.view = v;
  for (const sec of $$('.view')) sec.hidden = sec.id !== 'view-' + v;
  for (const b of $$('[data-view]')) b.classList.toggle('on', b.dataset.view === v);
  $('#crumb').textContent = $('#view-' + v).dataset.title;
  if (v === 'dados') renderDados();
  if (v === 'alertas') renderAlertas(true);
  if (v === 'moderacao') renderMod();
  if (v === 'mapa' && map) setTimeout(() => { map.invalidateSize(); placeLabels(); }, 60);
  window.scrollTo(0, 0);
}
const canModerate = () => Store.canEdit || Store.mode === 'local';

function barsCard(title, items, total, { cls = '', sub = '', max } = {}) {
  const m = max || Math.max(1, ...items.map(x => x[1]));
  return '<div class="card pad bars"><h3>' + esc(title) + '</h3>' + (sub ? '<p class="sub">' + esc(sub) + '</p>' : '') +
    items.map(([l, v]) => '<div class="bar ' + cls + '" title="' + v + ' de ' + total + '"><span class="l">' + esc(l) + ' <span class="muted num">· ' + v + '</span></span><span class="v num">' + pct(v, total) + '%</span><span class="t"><i style="width:' + (100 * v / m).toFixed(1) + '%"></i></span></div>').join('') + '</div>';
}
function renderDados() {
  const P = D.pesq, N = P.n, K = P.k, st = P.stats, B = D.bo, g = B.grupos;
  const get = (key, label) => (st[key].i.find(x => x[0] === label) || [0, 0])[1];
  const f = k => pct(get('funcoes', k), N), t = k => pct(get('confianca', k), N);
  const topBO = Object.entries(B.cells).sort((a, b) => b[1].n - a[1].n).slice(0, 8).map(([id, c]) => [areaName(id), c.n]);
  const reps = recentReports();
  const byT = {}; const byP = {};
  for (const r of reps) { for (const x of r.tipos) byT[x] = (byT[x] || 0) + 1; if (r.periodo) byP[r.periodo] = (byP[r.periodo] || 0) + 1; }
  const el = $('#view-dados');
  el.innerHTML =
    '<div class="page-head"><p class="eyebrow">Dados e pesquisa</p><h1>O que Rio Claro já contou</h1>' +
    '<p>Duas fontes alimentam o mapa: a pesquisa “Segurança e percepção das mulheres em Rio Claro”, com ' + N + ' respostas entre ' + fmtDate(P.de) + ' e ' + fmtDate(P.ate) + ', e ' + fmtN(B.total.n) + ' registros de boletins de ocorrência da SSP-SP. Os relatos da comunidade entram ao vivo.</p></div>' +
    '<div class="grid2">' +
    kfig(pct(K.evitam, N), 'evitam passar por certos lugares da cidade', K.evitam + ' de ' + N + ' respostas') +
    kfig(pct(K.viveram, N), 'já viveram uma situação que as fez se sentir inseguras ou ameaçadas', K.viveram + ' de ' + N) +
    kfig(pct(K.noite, N), 'se sentem menos seguras no início da noite, à noite ou de madrugada', K.noite + ' de ' + N) +
    kfig(pct(K.usariam, N), 'usariam um mapa colaborativo com relatos recentes', K.usariam + ' de ' + N + ' (com certeza ou provavelmente)') +
    '</div>' +
    '<div class="sec"><h2>Quando e por quê</h2><p class="lead">Respostas de múltipla escolha: cada barra mostra a parcela das ' + N + ' mulheres que marcou a opção.</p><div class="grid2">' +
    barsCard(st.periodo.t, st.periodo.i, N, { max: N }) + barsCard(st.motivo.t, st.motivo.i, N, { max: N }) + '</div></div>' +
    '<div class="sec"><h2>O que já viveram e onde</h2><div class="grid2">' +
    barsCard(st.situacao.t, st.situacao.i, N, { max: N, sub: 'Entre todas as respondentes.' }) +
    barsCard('Regiões citadas como inseguras', P.areas, P.comRegiao, { max: P.comRegiao, sub: P.comRegiao + ' mulheres responderam onde se sentem inseguras. Outros lugares citados: ' + P.outros.map(x => x[0]).join(', ') + '.' }) +
    barsCard(st.horario.t, st.horario.i, st.horario.n, { max: st.horario.n, sub: 'Entre as ' + st.horario.n + ' que responderam.' }) +
    barsCard(st.mudaria.t, st.mudaria.i, st.mudaria.n, { max: st.mudaria.n, sub: st.mudaria.n + ' respostas abertas, agrupadas por tema.' }) +
    '</div></div>' +
    '<div class="sec"><h2>Por que os grupos de WhatsApp não bastam</h2><p class="lead">' + pct(K.whats, N) + '% ficam sabendo de riscos por grupos de WhatsApp. Os problemas mais citados são justamente o que um mapa resolve.</p><div class="grid2">' +
    barsCard(st.whats.t, st.whats.i, N, { max: N }) + barsCard(st.sabe.t, st.sabe.i, N, { max: N }) + '</div></div>' +
    '<div class="sec"><h2>Do pedido ao MVP</h2><p class="lead">Cada função existe porque foi pedida na pesquisa.</p><div class="card tablewrap"><table class="maptable"><thead><tr><th>Pedido</th><th>Quem pediu</th><th>Como o MVP responde</th></tr></thead><tbody>' +
    trow('Mapa de alertas', f('Mapa de alertas'), 'Mapa com três camadas: relatos recentes, percepção da pesquisa e histórico de B.O.') +
    trow('Consultar antes de fazer um trajeto', f('Consultar informações antes de fazer um trajeto'), 'Checar trajeto: marca partida e destino e lista as áreas no caminho.') +
    trow('Visualizar alertas por horário', f('Visualizar alertas por horário'), 'Filtro de horário com as mesmas faixas da pesquisa, incluindo “Agora”.') +
    trow('Ver relatos próximos de um local', f('Ver relatos próximos de determinado local'), 'Toque numa área para ver relatos, percepção e registros dela.') +
    trow('Receber alertas de uma região', f('Receber alertas de uma região'), 'Acompanhar áreas em Meus alertas. Na versão instalada, aviso ao entrar na área.') +
    trow('Registrar um relato', f('Registrar um relato'), 'Chat da Aurora: botões ou texto livre, sem nome e sem endereço.') +
    trow('Encontrar serviços de apoio', f('Encontrar serviços de apoio'), 'Camada “Onde pedir ajuda” no mapa: Delegacia da Mulher, Guarda, CREAS, CRAS, Secretaria da Mulher, Defensoria e saúde 24h, com endereço, horário e telefone.') +
    '</tbody></table></div>' +
    '<div class="card tablewrap" style="margin-top:14px"><table class="maptable"><thead><tr><th>Para confiar, precisam de</th><th>Quem citou</th><th>Como o MVP responde</th></tr></thead><tbody>' +
    trow('Saber quantas relataram algo parecido', t('Saber quantas pessoas fizeram relatos semelhantes'), 'Contagem por área e confirmações “ainda acontece” em cada relato.') +
    trow('Instituição responsável', t('Saber que existe participação de uma instituição responsável'), 'Painel de moderação para a equipe e o Observatório.') +
    trow('Saber quando aconteceu', t('Saber quando o relato aconteceu'), 'Cada relato mostra quando foi enviado, quando aconteceu e a faixa de horário.') +
    trow('Moderação', t('Saber que existe moderação'), 'Três sinalizações de informação falsa tiram o relato do mapa até revisão.') +
    trow('Não identificar as pessoas', t('Saber que os relatos não identificam as pessoas'), 'Área de ~1 km, texto sem nomes, telefones e placas, relato gravado sem a conta de quem enviou.') +
    trow('Denunciar informação falsa', t('Poder denunciar informações falsas'), 'Botão “Informação falsa” em cada relato.') +
    trow('Não acusar pessoas individualmente', t('Saber que o sistema não acusa pessoas individualmente'), 'A Aurora reescreve o texto descrevendo a situação, sem identificar ninguém.') +
    '</tbody></table></div></div>' +
    '<div class="sec"><h2>Registros de boletins de ocorrência</h2><p class="lead">Base R.D.O. da SSP-SP obtida via FALASP, com ocorrências registradas de janeiro de 2025 a abril de 2026. São contagens por bairro, sem boletins individuais.</p><div class="grid2">' +
    '<div class="card pad"><dl class="dl">' +
    '<dt>Violência doméstica</dt><dd class="num">' + fmtN(B.total.vd) + '</dd><dt>Feminicídio</dt><dd class="num">' + B.total.fe + '</dd><dt>Tentativa de feminicídio</dt><dd class="num">' + B.total.te + '</dd>' +
    '<dt>Soma dos três</dt><dd class="num"><b>' + fmtN(B.total.n) + '</b></dd>' +
    '<dt>No mapa</dt><dd class="num">' + fmtN(g.mapeado.n) + ' em ' + g.mapeado.linhas + ' bairros com coordenada própria</dd>' +
    '<dt>Zona rural</dt><dd class="num">' + g.rural.n + ' (posição distribuída pela fonte, fora do mapa)</dd>' +
    '<dt>Sem bairro</dt><dd class="num">' + B.semGeo.n + ' + ' + g.naoinf.n + ' sem nome de bairro</dd>' +
    '<dt>Sem posição precisa</dt><dd class="num">' + g.placeholder.n + ' em ' + g.placeholder.linhas + ' bairros com coordenada genérica</dd>' +
    '</dl><p class="muted" style="font-size:13px;margin-top:12px">683 é a soma de três contadores e não garante 683 episódios ou pessoas distintas.</p></div>' +
    barsCard('Áreas com mais registros', topBO, g.mapeado.n, { cls: 'rose', sub: 'Parcela dos registros exibidos no mapa. Não é taxa por população.' }) +
    '</div></div>' +
    '<div class="sec"><h2>Relatos da comunidade</h2>' +
    (reps.length ? '<p class="lead">' + plural(reps.length, 'relato', 'relatos') + ' nos últimos 30 dias.</p><div class="grid2">' +
      barsCard('Tipos de situação', Object.entries(byT).sort((a, b) => b[1] - a[1]).map(([k, v]) => [TIPO[k].label, v]), reps.length, { cls: 'amb' }) +
      barsCard('Horário', PERIODOS.filter(p => byP[p.id]).map(p => [p.long, byP[p.id]]), reps.length, { cls: 'amb' }) + '</div>'
      : '<div class="card empty"><h3>Ainda não há relatos</h3><p>Quando as primeiras mulheres registrarem situações pelo chat, os tipos e horários aparecem aqui.</p></div>') +
    '</div>' +
    '<div class="sec note-box"><svg class="i"><use href="#i-info"/></svg><span>Percepção não é ocorrência, e registro de B.O. não é risco atual. As três camadas ficam separadas de propósito para que cada uma seja lida pelo que é. Detalhes em <button class="linkbtn" data-act="sobre" data-tab="fontes" style="text-decoration:underline">Fontes e método</button>.</span></div>';
}
function kfig(v, label, small) { return '<div class="card kfig"><b class="num">' + v + '%</b><span>' + esc(label) + '</span><small>' + esc(small) + '</small></div>'; }
function trow(a, p, b) { return '<tr><td>' + esc(a) + '</td><td class="p num">' + p + '%</td><td>' + esc(b) + '</td></tr>'; }

function alertCount() {
  const areas = new Set(Store.perfil.areas); if (!areas.size) return 0;
  const visto = Store.perfil.visto || 0, meus = new Set(Store.perfil.meus);
  return recentReports().filter(r => areas.has(r.cell) && r.criado > visto && !meus.has(r.id)).length;
}
function renderAlertas(markSeen) {
  const el = $('#view-alertas'), areas = Store.perfil.areas, visto = Store.perfil.visto || 0, meus = new Set(Store.perfil.meus);
  const rec = recentReports();
  el.replaceChildren();
  el.append(h('div', { class: 'page-head' }, h('p', { class: 'eyebrow' }, 'Meus alertas'), h('h1', null, 'As áreas por onde você passa'),
    h('p', null, 'Acompanhe as áreas do seu caminho. Quando alguém relata algo nelas, aparece aqui na próxima vez que você abrir a Aurora.')));
  const s1 = h('div', { class: 'sec' }, h('h2', null, 'Áreas que você acompanha'));
  if (!areas.length) {
    s1.append(h('div', { class: 'card empty' }, h('h3', null, 'Você ainda não acompanha nenhuma área'),
      h('p', null, 'No mapa, toque numa área (a da sua casa, do trabalho ou da faculdade) e escolha “Acompanhar”.'),
      h('div', null, h('button', { class: 'btn primary sm', type: 'button', 'data-view': 'mapa' }, icon('map', 'i sm'), 'Abrir o mapa'))));
  } else {
    const list = h('div', { class: 'follow' });
    for (const id of areas) {
      const rs = rec.filter(r => r.cell === id), n7 = rs.filter(r => r.criado > Date.now() - 7 * DAY).length, novos = rs.filter(r => r.criado > visto && !meus.has(r.id)).length;
      const pc = D.pesq.cells[id];
      const info = [plural(rs.length, 'relato em 30 dias', 'relatos em 30 dias') + (n7 ? ' (' + n7 + ' nesta semana)' : ''), pc ? 'citada por ' + plural(pc.n, 'mulher', 'mulheres') + ' na pesquisa' : ''].filter(Boolean).join(' · ');
      list.append(h('div', { class: 'card fcard' },
        h('div', null, h('h3', { text: areaName(id) }), h('p', null, info), novos ? h('p', { class: 'new' }, plural(novos, 'novo desde sua última visita', 'novos desde sua última visita')) : null),
        h('div', { class: 'acts' },
          h('button', { class: 'btn sm', type: 'button', onclick: () => focusCell(id) }, 'Ver no mapa'),
          h('button', { class: 'btn sm ghost', type: 'button', onclick: () => { toggleFollow(id, false); renderAlertas(false); } }, 'Parar de acompanhar'))));
    }
    s1.append(list);
    const novos = rec.filter(r => areas.includes(r.cell) && r.criado > visto && !meus.has(r.id));
    if (novos.length) {
      const ul = h('ul', { class: 'reports', style: 'margin-top:14px' });
      for (const r of novos.slice(0, 10)) { const li = reportItem(r); li.prepend(h('b', { text: areaName(r.cell) })); ul.append(li); }
      s1.append(h('h3', { style: 'margin-top:20px;font-size:17px' }, 'Novidades nas suas áreas'), ul);
    }
  }
  el.append(s1);
  const s2 = h('div', { class: 'sec' }, h('h2', null, 'Aviso ao passar por uma área'));
  if (STANDALONE && 'geolocation' in navigator) {
    const sw = h('button', { class: 'switch', type: 'button', role: 'switch', 'aria-checked': Watch.on ? 'true' : 'false', 'aria-label': 'Modo atenção' });
    sw.onclick = () => { if (Watch.on) Watch.stop(); else Watch.start(); renderAlertas(false); };
    s2.append(h('div', { class: 'card pad', style: 'display:grid;gap:10px' },
      h('div', { class: 'toggle' }, sw, h('div', null, h('b', null, 'Modo atenção'), h('p', { class: 'muted', style: 'font-size:14px' }, 'Com a Aurora aberta, avisa com vibração quando você entra numa área com relatos recentes, citada na pesquisa ou que você acompanha. Sua localização fica só neste aparelho.'))),
      Watch.on ? h('p', { style: 'font-size:14px;color:var(--ok)' }, Watch.cell ? 'Ligado. Você está em ' + areaName(Watch.cell) + '.' : 'Ligado. Procurando sua localização…') : null));
  } else {
    s2.append(h('div', { class: 'note-box' }, icon('info'), h('span', null, 'Neste link de demonstração o navegador não libera sua localização. Na versão instalada (o arquivo que a equipe hospeda), a Aurora avisa com vibração quando você entra numa área com relatos recentes.')));
  }
  el.append(s2);
  const mine = allReports().filter(r => meus.has(r.id));
  const s3 = h('div', { class: 'sec' }, h('h2', null, 'Meus relatos'), h('p', { class: 'lead' }, Store.mode === 'db' ? 'Esta lista fica num espaço privado da sua conta: nem a equipe vê quem enviou cada relato.' : 'Esta lista fica só neste aparelho.'));
  if (!mine.length) s3.append(h('p', { class: 'muted' }, 'Você ainda não enviou relatos.'));
  else {
    const ul = h('ul', { class: 'reports' });
    for (const r of mine) {
      const li = reportItem(r, { votes: false }); li.prepend(h('b', { text: areaName(r.cell) }));
      const del = h('button', { class: 'btn sm danger', type: 'button' }, icon('trash', 'i sm'), 'Apagar relato');
      del.onclick = async () => {
        if (!del.dataset.confirm) { del.dataset.confirm = '1'; del.lastChild.textContent = 'Confirmar: apagar de vez'; return; }
        try { await Store.deleteReport(r.id); toast('Relato apagado.'); renderAlertas(false); } catch (e) { toast('Não consegui apagar agora.'); }
      };
      li.append(h('div', null, del)); ul.append(li);
    }
    s3.append(ul);
  }
  el.append(s3);
  if (markSeen) { Store.perfil.visto = Date.now(); Store.savePerfil(); updateCounts(); }
}

function renderMod() {
  const el = $('#view-moderacao'); el.replaceChildren();
  el.append(h('div', { class: 'page-head' }, h('p', { class: 'eyebrow' }, 'Moderação'), h('h1', null, 'Revisar relatos'),
    h('p', null, 'Relatos com 3 ou mais sinalizações de informação falsa saem do mapa até alguém da equipe revisar. “Verificar” mantém o relato visível e mostra um selo.')));
  if (!canModerate()) { el.append(h('p', { class: 'muted' }, 'Só a equipe responsável vê esta página.')); return; }
  const all = allReports().sort((a, b) => ((Store.votes[b.id] || {}).f || 0) - ((Store.votes[a.id] || {}).f || 0) || b.criado - a.criado);
  if (!all.length) { el.append(h('div', { class: 'card empty' }, h('h3', null, 'Nenhum relato ainda'), h('p', null, 'Os relatos enviados pelo chat aparecem aqui.'))); return; }
  const list = h('div', { class: 'modlist' });
  for (const r of all) {
    const v = Store.votes[r.id] || { c: 0, p: 0, f: 0 }, oc = !!Store.mod.oculto[r.id], ver = !!Store.mod.verificado[r.id];
    const status = ver ? 'Verificado' : oc ? 'Oculto pela equipe' : v.f >= 3 ? 'Fora do mapa: ' + v.f + ' sinalizações' : 'Visível';
    const left = h('div', { style: 'display:grid;gap:6px' }, h('b', { text: areaName(r.cell) }),
      h('span', { class: 'muted', style: 'font-size:13px' }, status + ' · ' + v.c + ' ainda acontece · ' + v.p + ' parou · ' + v.f + ' falso'),
      reportItem(r, { votes: false, tag: 'div' }));
    const act = (label, fn) => h('button', { class: 'btn sm', type: 'button', onclick: async () => { try { await fn(); toast('Moderação salva.'); } catch (e) { toast('Não foi possível salvar. Só quem pode editar o protótipo modera.'); } } }, label);
    list.append(h('div', { class: 'card modrow' }, left, h('div', { class: 'acts' },
      oc ? act('Mostrar', () => Store.setMod(r.id, 'oculto', false)) : act('Ocultar', () => Store.setMod(r.id, 'oculto', true)),
      ver ? act('Tirar verificação', () => Store.setMod(r.id, 'verificado', false)) : act('Verificar', () => Store.setMod(r.id, 'verificado', true)))));
  }
  el.append(list);
}

/* ------------------------------------------------------------------ "Sobre os dados" */
function sobreHTML(tab) {
  const P = D.pesq, B = D.bo, g = B.grupos;
  if (tab === 'privacidade') return '<h3>O que um relato mostra</h3><ul><li>Tipo de situação, área de cerca de 1 km, quando aconteceu (hoje, ontem, nesta semana ou antes), faixa de horário e um texto opcional revisado.</li><li>Nunca mostra nome, contato, endereço ou a posição exata. O relato é gravado sem o nome ou o identificador da conta de quem enviou.</li></ul>' +
    '<h3>Como o texto é limpo</h3><ul><li>Regras automáticas tiram telefones, e-mails, CPF, placas de veículos, perfis de redes sociais, números de casa e nomes depois de “chamado”, “se chama” e parecidos.</li><li>' + (HAS_CLAUDE ? 'Com a IA ligada, a Aurora também reescreve o texto tirando nomes e detalhes que identifiquem alguém. A IA roda na sua conta Claude e só é chamada quando você escreve no campo livre; na primeira vez, o navegador pede sua permissão.' : 'Nesta versão, a limpeza é feita pelas regras automáticas, no próprio aparelho.') + '</li><li>Você revisa o relato antes de publicar e pode apagá-lo depois em Meus alertas.</li></ul>' +
    '<h3>O que fica guardado com você</h3><ul><li>' + (Store.mode === 'db' ? 'As áreas que você acompanha e a lista dos seus relatos ficam num espaço privado da sua conta. Nem a equipe vê.' : 'As áreas que você acompanha, seus relatos e confirmações ficam só neste aparelho.') + '</li><li>Confirmações (“ainda acontece”, “não acontece mais”, “informação falsa”) valem uma por pessoa e aparecem só como contagem.</li>' + (STANDALONE ? '<li>No modo atenção, sua localização é usada só no aparelho para saber em que área você está. Ela não é enviada a lugar nenhum.</li>' : '') + '</ul>' +
    '<h3>Segurança</h3><ul><li>O botão “Sair rápido” (ou Esc duas vezes) troca a tela na hora por uma página neutra.</li><li>A Aurora não é boletim de ocorrência e não envia nada à polícia. Em perigo, ligue 190.</li></ul>';
  if (tab === 'fontes') return '<h3>Pesquisa com mulheres de Rio Claro</h3><p>Formulário “Segurança e percepção das mulheres em Rio Claro”, ' + P.n + ' respostas entre ' + fmtDate(P.de) + ' e ' + fmtDate(P.ate) + '. No mapa, as ' + P.comRegiao + ' respostas sobre regiões inseguras foram ligadas aos bairros da base de B.O.; ' + P.mapeadas + ' citavam lugares localizáveis. Cada mulher conta uma vez por área. Unesp foi contada no Bela Vista, Lago Azul entre Vila Operária, Jardim Primavera e Vila Aparecida, e Rodoviária no Jardim Claret. Não entraram no mapa: ' + P.outros.map(x => esc(x[0])).join(', ') + '.</p>' +
    '<h3>Boletins de ocorrência (SSP-SP)</h3><p>Base R.D.O. obtida por pedido FALASP, com ocorrências registradas de janeiro de 2025 a abril de 2026, filtrada para o município de Rio Claro. Traz contagens por bairro de violência doméstica (' + fmtN(B.total.vd) + '), feminicídio (' + B.total.fe + ') e tentativa de feminicídio (' + B.total.te + '). A data de registro pode diferir da data do fato. As coordenadas são centros médios dos boletins de cada bairro.</p>' +
    '<p>O mapa mostra ' + fmtN(g.mapeado.n) + ' registros de ' + g.mapeado.linhas + ' bairros com coordenada própria, somados em células hexagonais de cerca de 1 km. Ficam fora: ' + g.rural.n + ' da zona rural (a fonte espalha esses pontos de forma aproximada), ' + B.semGeo.n + ' sem bairro, ' + g.placeholder.n + ' de ' + g.placeholder.linhas + ' bairros com coordenada genérica e ' + g.naoinf.n + ' sem nome de bairro. Não é taxa por população nem medida de risco atual.</p>' +
    '<h3>Relatos da comunidade</h3><p>Enviados pelo chat da Aurora. Aparecem por 30 dias. Não são verificados um a um: a equipe pode verificar ou ocultar, e três sinalizações de informação falsa tiram o relato do mapa até revisão.</p>' +
    '<h3>Mapa</h3><p>Ruas, ferrovia, rios, lagos, parques e campi vêm do OpenStreetMap (© colaboradores do OpenStreetMap, licença ODbL), extraídos em 24 de setembro de 2026 e guardados dentro do próprio app: o mapa abre sem depender de servidor de mapas. O contorno do município vem da base da SSP. Os nomes de bairros no mapa são referências aproximadas.</p>' +
    '<h3>Rede de apoio</h3><p>Endereços, telefones e horários reunidos em 24 de setembro de 2026 em páginas oficiais: Prefeitura de Rio Claro (Secretarias da Mulher, de Segurança e de Desenvolvimento Social), Tribunal de Justiça de SP, Defensoria Pública de SP e Fundação Municipal de Saúde. Cada ponto mostra a sua fonte.</p>' +
    '<p>A posição vem do OpenStreetMap quando o prédio está mapeado lá. Nos outros casos, foi calculada pelo endereço oficial, usando as esquinas citadas e os números de prédios já mapeados na mesma rua para achar a quadra e o lado da rua (margem de uns 30 m). CRAS Mãe Preta e CRAS Jardim Brasília estão marcados como aproximados, e o CRAS Panorama fica só na lista porque não foi possível confirmar a posição. Casas-abrigo nunca aparecem, para proteger quem está nelas. Confirme os contatos antes do lançamento.</p>';
  return '<h3>Relatos</h3><p>O que as mulheres registram pelo chat da Aurora: tipo de situação, área e horário. Ficam no mapa por 30 dias. O número no círculo é a quantidade de relatos na área; cada relato mostra quantas confirmaram que ainda acontece.</p>' +
    '<h3>Percepção</h3><p>Onde as ' + P.n + ' mulheres da pesquisa disseram se sentir inseguras e em que horário. A cor mostra quantas citaram cada área. Percepção não é ocorrência, mas mostra padrões: Bela Vista, a região da Unesp e o Centro à noite aparecem muito mais que o resto.</p>' +
    '<h3>Histórico B.O.</h3><p>Registros oficiais de violência doméstica, feminicídio e tentativa de feminicídio entre janeiro de 2025 e abril de 2026, por bairro. A violência doméstica acontece sobretudo dentro de casa: essa camada mostra onde a rede de apoio é mais necessária e serve ao Observatório e à Prefeitura. Ela não indica perigo na rua nem rota segura.</p>' +
    '<h3>Onde pedir ajuda</h3><p>Os ícones redondos mostram onde registrar ocorrência, pedir medida protetiva, conversar com alguém ou ser atendida na saúde: Delegacia da Mulher, Guarda Civil, CREAS, CRAS, Secretaria da Mulher, Defensoria, Anexo de Violência Doméstica, pronto-socorro ginecológico e prontos-atendimentos 24 horas. Toque num ícone para ver endereço, horário, telefone e como chegar. Um círculo com número junta serviços muito próximos. A caixa “Onde pedir ajuda” na legenda liga e desliga essa camada.</p>' +
    '<h3>Células de ~1 km</h3><p>A cidade é dividida em hexágonos de cerca de 1 km. Relatos e dados aparecem por célula, nunca num ponto exato, para proteger quem relata e para não expor endereços. Só os serviços públicos de apoio aparecem com endereço exato.</p>';
}
function openSobre(tab = 'camadas') {
  const m = $('#sobre'); m.hidden = false;
  for (const b of $$('#sobreTabs button')) b.classList.toggle('on', b.dataset.tab === tab);
  $('#sobreContent').innerHTML = sobreHTML(tab); $('#sobreContent').scrollTop = 0;
  m.querySelector('.box').focus();
}
function closeSobre() { $('#sobre').hidden = true; }

/* ------------------------------------------------------------------ modo atenção (GPS, só na versão arquivo) */
const Watch = {
  id: null, on: false, cell: null, last: {},
  start() {
    if (!('geolocation' in navigator)) return;
    this.on = true; this.cell = null;
    this.id = navigator.geolocation.watchPosition(p => this.onPos(p), () => { toast('Não consegui acessar sua localização. Verifique a permissão do navegador.'); this.stop(); renderAlertas(false); },
      { enableHighAccuracy: true, maximumAge: 15000, timeout: 30000 });
    try { if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission(); } catch (e) { /* opcional */ }
    toast('Modo atenção ligado.');
  },
  stop() { if (this.id != null) navigator.geolocation.clearWatch(this.id); this.id = null; this.on = false; this.cell = null; if (meMarker) { meMarker.remove(); meMarker = null; } },
  onPos(p) {
    const ll = [p.coords.latitude, p.coords.longitude]; showMe(ll);
    const id = cellOf(...ll); if (id === this.cell) return;
    this.cell = id; if (S.view === 'alertas') renderAlertas(false);
    const n = recentReports().filter(r => r.cell === id).length, pc = D.pesq.cells[id], fol = Store.perfil.areas.includes(id);
    if (!n && !(pc && pc.n >= 2) && !fol) return;
    if (this.last[id] && Date.now() - this.last[id] < 30 * 60e3) return;
    this.last[id] = Date.now();
    const body = [n ? plural(n, 'relato recente', 'relatos recentes') : '', pc && pc.n >= 2 ? 'citada por ' + pc.n + ' mulheres na pesquisa' : '', fol && !n ? 'área que você acompanha' : ''].filter(Boolean).join(' · ');
    const near = S.apoio ? nearestApoio(ll, 1)[0] : null;
    toast('Atenção: ' + areaName(id) + ' · ' + body + (near ? ' · ajuda mais perto: ' + (near.p.curto || near.p.nome) + ', ' + fmtDist(near.d) : ''), 8000);
    try { navigator.vibrate && navigator.vibrate([220, 120, 220]); } catch (e) { /* opcional */ }
    try { if ('Notification' in window && Notification.permission === 'granted' && document.hidden) new Notification('Aurora: ' + areaName(id), { body }); } catch (e) { /* opcional */ }
  }
};

/* ------------------------------------------------------------------ sair rápido */
function quickExit() {
  try { Chat.start(); closeSobre(); closeChat(); closePanel(); } catch (e) { /* segue */ }
  $('#cover').hidden = false; document.title = 'Lista de compras';
  if (STANDALONE) { try { window.location.replace('https://www.google.com/search?q=previs%C3%A3o+do+tempo'); } catch (e) { /* fica na capa */ } }
}
let lastEsc = 0;
document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const now = Date.now();
  if (now - lastEsc < 700) { quickExit(); lastEsc = 0; return; }
  lastEsc = now;
  if (!$('#sobre').hidden) closeSobre();
  else if (S.pick) { stopPick(); openChat(); }
  else if (S.routeMode) clearRoute();
  else if (!$('#panel').hidden) closePanel();
});

/* ------------------------------------------------------------------ controles */
function renderChips() {
  const el = $('#periodChips'); el.replaceChildren();
  const now = currentPeriod(), dis = S.layer === 'historico';
  const list = [{ id: 'todos', label: 'Qualquer horário' }, { id: 'agora', label: 'Agora · ' + PER[now].label, cls: 'now' }, ...PERIODOS];
  for (const p of list) el.append(h('button', { type: 'button', class: 'chip' + (p.cls ? ' ' + p.cls : '') + (S.period === p.id ? ' on' : ''), 'aria-pressed': S.period === p.id ? 'true' : 'false', disabled: dis,
    onclick: () => { S.period = p.id; renderChips(); renderMap(); refreshPanel(); } }, p.label));
  el.style.opacity = dis ? 0.45 : 1; el.title = dis ? 'A base de B.O. não informa horário' : '';
}
function renderTypeSel() {
  const sel = $('#typeSel'); sel.replaceChildren();
  if (S.layer === 'relatos') { sel.hidden = false; sel.append(new Option('Todos os tipos', 'todos'), ...TIPOS.map(t => new Option(t.label, t.id))); sel.value = S.tipo; }
  else if (S.layer === 'historico') { sel.hidden = false; for (const [v, l] of [['n', 'Todas as categorias'], ['vd', 'Violência doméstica'], ['fe', 'Feminicídio'], ['te', 'Tentativa de feminicídio']]) sel.append(new Option(l, v)); sel.value = S.cat; }
  else sel.hidden = true;
  $('#rangeLbl').textContent = { relatos: 'Últimos 30 dias', percepcao: 'Pesquisa de ' + fmtDate(D.pesq.de) + ' a ' + fmtDate(D.pesq.ate), historico: 'Jan 2025 – abr 2026 · sem horário' }[S.layer];
}
function syncControls() {
  for (const b of $$('#layerSeg button')) { const on = b.dataset.layer === S.layer; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); }
  renderChips(); renderTypeSel();
}

/* ------------------------------------------------------------------ inicialização */
function boot() {
  $('#stBO').textContent = fmtN(D.bo.total.n);
  $('#stPesq').textContent = D.pesq.n;
  for (const b of $$('#layerSeg button')) b.onclick = () => setLayer(b.dataset.layer);
  $('#typeSel').onchange = e => { if (S.layer === 'relatos') S.tipo = e.target.value; else S.cat = e.target.value; renderMap(); };
  $('#areaSearch').addEventListener('input', renderAreaList);
  $('#areaMore').onclick = () => { S.showAll = !S.showAll; renderAreaList(); };
  for (const b of $$('#sobreTabs button')) b.onclick = () => openSobre(b.dataset.tab);
  $('#sobre').addEventListener('click', e => { if (e.target.id === 'sobre') closeSobre(); });
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-view],[data-act],[data-copy]'); if (!b) return;
    if (b.dataset.view) { showView(b.dataset.view); closeChat(); }
    const a = b.dataset.act;
    if (a === 'relatar') relatar();
    else if (a === 'sobre') openSobre(b.dataset.tab);
    else if (a === 'fecharSobre') closeSobre();
    else if (a === 'fecharChat') closeChat();
    else if (a === 'recomecar') Chat.start();
    else if (a === 'sair') quickExit();
    else if (a === 'apoioMapa') showApoioOnMap();
    if (b.dataset.copy) {
      const txt = b.dataset.copy;
      try { navigator.clipboard.writeText(txt).then(() => toast('Copiado: ' + txt), () => toast('Número: ' + txt)); } catch (err) { toast('Número: ' + txt); }
    }
  });
  syncControls();
  initMap();
  renderApoioPage();
  Chat.init();
  renderMap();
  Store.on(() => {
    const modNav = $('[data-modnav]'); if (modNav) modNav.hidden = !canModerate();
    if (!S.userLayer && Store.ready && recentReports().length && S.layer !== 'relatos') { S.layer = 'relatos'; syncControls(); }
    renderMap(); refreshPanel();
    if (S.view === 'dados') renderDados();
    if (S.view === 'alertas') renderAlertas(false);
    if (S.view === 'moderacao') renderMod();
  });
  Store.init();
  const onTheme = () => renderMap();
  if (mq.addEventListener) mq.addEventListener('change', onTheme);
  new MutationObserver(onTheme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  setInterval(() => { renderChips(); if (S.period === 'agora') { renderMap(); refreshPanel(); } }, 5 * 60e3);
}
if (!window.L) { document.getElementById('mapNote').lastChild.textContent = 'O mapa não carregou. Verifique a conexão e recarregue a página.'; return; }
boot();
})();
