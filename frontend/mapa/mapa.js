import { janelaTxt } from '../config.js';
import { $, $$, h, esc, cssVar, toast } from '../shared/dom.js';
import { fmtN, plural } from '../shared/formato.js';
import { STANDALONE } from '../shared/ambiente.js';
import { isDark } from '../shared/tema.js';
import { D, OSM } from '../shared/dados.js';
import { cellOf, cellCenter, cellPoly } from '../shared/grade.js';
import { BYNAME, areaName } from '../shared/bairros.js';
import { S, periodOk } from '../shared/estado.js';
import { showView } from '../shared/navegacao.js';
import { layerValues, SCALES, classOf, tipoPorCelula } from './camadas.js';
import { TIPO, TIPOS as TIPOS_ORD } from '../shared/vocabulario.js';
import { closePanel, openPanel } from './painel-area.js';
import { renderAreaList } from './lista-areas.js';
import { startRoute, routeClick, clearRoute } from './trajeto.js';
import { stopPick } from './selecao.js';
import { showMe } from './localizacao.js';
import { syncControls } from './controles.js';
import { APOIO, AP_ORDER, apSvg } from '../apoio/rede.js';
import { APV, initApoioLayer, setApoio, renderApoio, openNearMe } from '../apoio/camada-apoio.js';
import { recentReports, filteredReports } from '../relatos/relatos.js';
import { alertCount } from '../relatos/alertas.js';
import { Chat, relatar, openChat, closeChat } from '../chatbot/chat.js';

/* ------------------------------------------------------------------ mapa */
export let map, renderer, baseRenderer, hexLayer, labelLayer, pinLayer, routeLayer, selLayer, boundaryLine;
export let C = {};
export const hexes = new Map();
export function readColors() {
  C = { ink: cssVar('--ink'), boundary: cssVar('--boundary'), brand: cssVar('--brand'), ground: cssVar('--map-ground'),
    road: cssVar('--map-road'), roadCase: cssVar('--map-road-case'), major: cssVar('--map-road-major'), majorCase: cssVar('--map-road-major-case'),
    water: cssVar('--map-water'), green: cssVar('--map-green'), park: cssVar('--map-park'), campus: cssVar('--map-campus'),
    campusLine: cssVar('--map-campus-line'), rail: cssVar('--map-rail') };
}
export function decodePoly(str) {
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
export const BL = {};
export const ROAD_W = { // [contorno, via] em pixels, do zoom 12 ao 17
  major: [[2.6, 1.4], [3.6, 2.2], [5.2, 3.4], [7.4, 5.2], [10.5, 7.8], [15, 11.5]],
  sec: [[2, 1], [2.8, 1.6], [4.2, 2.8], [5.8, 4.2], [8.4, 6.2], [11.5, 8.8]],
  ter: [[1.6, 0.8], [2.3, 1.3], [3.5, 2.3], [5, 3.6], [7.2, 5.4], [10.5, 7.8]],
  minor: [[0, 0.55], [1.2, 0.75], [2.2, 1.4], [3.5, 2.5], [5.6, 4.2], [8.4, 6.4]]
};
export function zInterp(tab, z) { const zc = Math.max(12, Math.min(17, z)), i = Math.min(4, Math.floor(zc - 12)), t = zc - 12 - i; return tab[i].map((v, j) => v + (tab[i + 1][j] - v) * t); }
export function initBaseMap() {
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
export function styleBaseMap() {
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
export const LBL = [];
export function addLabel(o) {
  o.m = L.marker([o.lat, o.lng], { icon: L.divIcon({ className: 'lbl ' + o.cls, html: o.html, iconSize: [0, 0] }), interactive: false, keyboard: false, pane: 'labels' });
  o.on = false; LBL.push(o);
}
export function buildLabels() {
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
export function placeLabels() {
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

/* células (1 km nos dados, 150 m nos relatos) por cima das ruas */
export const baseStyle = () => ({ stroke: false, fill: false, opacity: 0, fillOpacity: 0 });
export function ensureHex(id) {
  if (hexes.has(id)) return hexes.get(id);
  const p = L.polygon(cellPoly(id), Object.assign({ renderer, bubblingMouseEvents: true }, baseStyle()));
  if (matchMedia('(hover: hover)').matches) p.bindTooltip(() => tipFor(id), { className: 'hex-tip', sticky: true, direction: 'top', opacity: 1 });
  p.addTo(hexLayer); hexes.set(id, p); return p;
}
export function tipFor(id) {
  const v = layerValues().get(id) || 0, nm = esc(areaName(id));
  if (!v) return nm;
  const lbl = S.layer === 'relatos' ? plural(v, 'relato', 'relatos') : S.layer === 'percepcao' ? plural(v, 'menção', 'menções') : plural(v, 'registro', 'registros');
  return '<b>' + nm + '</b><br>' + lbl;
}
export function initMap() {
  readColors();
  map = L.map('map', { zoomControl: false, attributionControl: false, preferCanvas: true, minZoom: 11, maxZoom: 17.5, zoomSnap: 0.5,
    maxBounds: [[-22.62, -47.84], [-22.18, -47.38]], maxBoundsViscosity: 0.8 });
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
  initApoioLayer();
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
export function onMapClick(e) {
  const id = cellOf(e.latlng.lat, e.latlng.lng, S.layer === 'relatos' || !!S.pick);
  if (S.pick) { const cb = S.pick; stopPick(); cb(id); return; }
  if (S.routeMode) { routeClick(e.latlng); return; }
  openPanel(id);
}
export function renderMap() {
  if (!map) return;
  const prevGround = C.ground; readColors();
  if (C.ground !== prevGround) styleBaseMap();
  styleHexes(layerValues());
  renderPins(); renderSelection(); renderLegend(); renderNote(); renderAreaList(); renderEmptyHint(); updateCounts();
}
/* as células ficam mais transparentes de perto para as ruas continuarem legíveis */
export function styleHexes(vals) {
  if (!map) return;
  vals = vals || layerValues();
  const sc = SCALES[S.layer], ramp = sc.vars.map(cssVar), z = map.getZoom();
  const op = (isDark() ? 0.62 : 0.5) * Math.max(0.42, Math.min(1, 1 - (z - 13) * 0.2)), w = z >= 15 ? 1.8 : 1.2;
  for (const id of vals.keys()) ensureHex(id);
  const tipos = S.layer === 'relatos' ? tipoPorCelula() : null;
  for (const [id, poly] of hexes) {
    const v = vals.get(id) || 0, k = v ? classOf(v, sc.breaks) : -1;
    if (k < 0) { poly.setStyle(baseStyle()); continue; }
    const cor = tipos ? TIPO[tipos.get(id)].cor : null;
    poly.setStyle(cor ? { stroke: true, color: cor, weight: w, opacity: 0.95, fill: true, fillColor: cor, fillOpacity: Math.min(0.85, op * (0.7 + 0.25 * k)) }
      : { stroke: true, color: ramp[3], weight: w, opacity: 0.9, fill: true, fillColor: ramp[k], fillOpacity: op });
  }
}
export function renderPins() {
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
/* quanto do mapa o painel cobre: à direita no computador, embaixo no celular */
export function panelInset() {
  const P = $('#panel'); if (!P || P.hidden) return [0, 0];
  const w = $('#mapwrap').getBoundingClientRect(), r = ($('#gaveta') || P).getBoundingClientRect();
  return r.width >= w.width - 40 ? [0, Math.max(0, w.bottom - r.top)] : [Math.max(0, w.right - r.left), 0];
}
export function flyToVisible(ll, z) {
  const [dx, dy] = panelInset(); z = Math.min(map.getMaxZoom(), z == null ? map.getZoom() : z);
  map.flyTo(map.unproject(map.project(ll, z).add([dx / 2, dy / 2]), z), z, { duration: 0.6 });
}
export function isVisible(ll, m = 36) {
  const [dx, dy] = panelInset(), s = map.getSize(), p = map.latLngToContainerPoint(ll);
  return p.x > m && p.y > m && p.x < s.x - dx - m && p.y < s.y - dy - m;
}
/* abre o mapa (se estava em outra página) e depois executa fn, quando o mapa já tem tamanho */
export function withMap(fn) {
  const was = S.view;
  showView('mapa'); closeChat();
  if (!S.apoio) setApoio(true);
  const go = () => { map.invalidateSize(); fn(); $('#mapwrap').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' }); };
  if (was !== 'mapa') setTimeout(go, 90); else go();
}
export function renderSelection() {
  if (!selLayer) return;
  selLayer.clearLayers();
  if (S.route && S.route.cells) for (const id of S.route.cells) L.polygon(cellPoly(id), { renderer, interactive: false, color: C.brand, weight: 1.2, opacity: 0.6, fill: false }).addTo(selLayer);
  if (S.selected) L.polygon(cellPoly(S.selected), { renderer, interactive: false, color: C.ink, weight: 3, fill: false }).addTo(selLayer);
}
export function renderLegend() {
  const sc = SCALES[S.layer], el = $('#legend');
  const anyRecent = recentReports().some(periodOk);
  const presentes = S.layer === 'relatos' ? new Set(tipoPorCelula().values()) : null;
  const chave = presentes ? (presentes.size ? '<div class="ramp tipos-leg">' + TIPOS_ORD.filter(t => presentes.has(t.id)).map(t => '<span><i style="background:' + t.cor + '"></i>' + esc(t.label) + '</span>').join('') + '</div><small>Cor: tipo mais relatado na área. Mais forte: mais relatos.</small>' : '')
    : '<div class="ramp">' + sc.vars.map((v, i) => '<span><i style="background:var(' + v + ')"></i>' + sc.labels[i] + '</span>').join('') + '</div>';
  el.innerHTML = '<b>' + sc.title + '</b>' + chave +
    (S.layer !== 'relatos' && anyRecent ? '<div class="pinkey"><span class="pin faint" style="position:static;transform:none"></span>relatos recentes</div>' : '') +
    (APOIO.length ? '<button type="button" class="apkey' + (S.apoio ? ' on' : '') + '" aria-pressed="' + S.apoio + '" title="' + (S.apoio ? 'Esconder' : 'Mostrar') + ' delegacia, Guarda, assistência social, Justiça e saúde 24h">' +
      '<span class="sw">' + (S.apoio ? '<svg class="i" aria-hidden="true"><use href="#i-check"/></svg>' : '') + '</span>Onde pedir ajuda<span class="ics">' +
      AP_ORDER.map(t => '<span class="t-' + t + '">' + apSvg(t) + '</span>').join('') + '</span></button>' : '');
}
export function renderNote() {
  const span = $('#mapNote span'), g = D.bo.grupos, p = D.pesq;
  if (S.layer === 'relatos') {
    const n = filteredReports().length;
    span.textContent = plural(n, 'relato', 'relatos') + ' nos últimos ' + janelaTxt() + ' com esses filtros. Cada relato mostra quando foi enviado e quantas mulheres confirmaram que ainda acontece.';
  } else if (S.layer === 'percepcao') {
    span.textContent = p.mapeadas + ' das ' + p.n + ' respostas citaram regiões que conseguimos localizar. Mostra onde as mulheres se sentem inseguras, não onde houve ocorrência.';
  } else {
    const fora = g.rural.n + D.bo.semGeo.n + g.placeholder.n + g.naoinf.n;
    span.textContent = fmtN(g.mapeado.n) + ' registros em áreas exibidas (outros ' + fora + ' não têm posição de bairro). São B.O. de violência doméstica e feminicídio: não indicam risco atual nem perigo na rua.';
  }
}
export function renderEmptyHint() {
  const el = $('#emptyHint');
  if (S.layer !== 'relatos' || filteredReports().length || S.pick || S.routeMode) { el.hidden = true; return; }
  const none = !recentReports().length;
  el.replaceChildren(
    h('h3', null, none ? 'Ainda não há relatos nos últimos ' + janelaTxt() : 'Nenhum relato com esses filtros'),
    h('p', null, none ? 'Seja a primeira a avisar outras mulheres. Enquanto isso, veja onde 51 mulheres disseram se sentir inseguras.' : 'Tente outro horário ou tipo de situação.'),
    h('div', null,
      none ? h('button', { class: 'btn primary sm', type: 'button', onclick: relatar }, 'Registrar relato')
        : h('button', { class: 'btn primary sm', type: 'button', onclick: () => { S.period = 'todos'; S.tipo = 'todos'; syncControls(); renderMap(); } }, 'Limpar filtros'),
      h('button', { class: 'btn sm', type: 'button', onclick: () => setLayer('percepcao') }, 'Ver percepção'))
  );
  el.hidden = false;
}
export function updateCounts() {
  const n = recentReports().length;
  $('#stRel').textContent = fmtN(n); $('#cntRel').textContent = fmtN(n);
  const badge = alertCount();
  for (const b of $$('[data-badge]')) { b.hidden = !badge; b.textContent = badge; }
}
export function setLayer(l, user = true) { S.layer = l; if (user) S.userLayer = true; closePanel(); syncControls(); renderMap(); }
