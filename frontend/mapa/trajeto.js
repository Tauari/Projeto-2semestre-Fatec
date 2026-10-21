import { $, h, icon } from '../shared/dom.js';
import { plural } from '../shared/formato.js';
import { PER } from '../shared/vocabulario.js';
import { D } from '../shared/dados.js';
import { toXY, toLL, cellOf, grossa } from '../shared/grade.js';
import { rotear, MODOS } from './roteador.js';
import { subirGaveta } from './gaveta.js';
import { areaName } from '../shared/bairros.js';
import { S, activePeriod, periodOk } from '../shared/estado.js';
import { percValue } from './camadas.js';
import { map, renderer, routeLayer, C, renderSelection, renderEmptyHint } from './mapa.js';
import { closePanel, openPanel } from './painel-area.js';
import { stopPick } from './selecao.js';
import { recentReports } from '../relatos/relatos.js';

/* ------------------------------------------------------------------ trajeto pelas ruas */
export function startRoute() {
  closePanel(); stopPick();
  S.routeMode = true; S.route = { a: null, b: null, cells: null };
  routeLayer.clearLayers();
  $('#routebar').hidden = false; $('#routeMsg').textContent = 'Toque no ponto de partida';
  $('#btnRoute').classList.add('on'); map.getContainer().classList.add('picking');
  renderEmptyHint();
}
export function endMarker(ll, t) { return L.marker(ll, { icon: L.divIcon({ className: '', html: '<span class="route-end">' + t + '</span>', iconSize: [0, 0] }), interactive: false, keyboard: false }); }
export function routeClick(ll) {
  if (!S.route.a) { S.route.a = ll; endMarker(ll, 'A').addTo(routeLayer); $('#routeMsg').textContent = 'Agora toque no destino'; return; }
  S.route.b = ll; S.routeMode = false; map.getContainer().classList.remove('picking');
  $('#routebar').hidden = true; S.route.modo = S.route.modo || 'pe';
  calcular();
}
const fmtTempo = s => { const m = Math.max(1, Math.round(s / 60)); return m < 60 ? m + ' min' : Math.floor(m / 60) + ' h ' + String(m % 60).padStart(2, '0') + ' min'; };
const fmtKm = m => (m / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' km';
/* células de 150 m por onde a rota passa, de ~20 em ~20 m */
function celulasDe(pontos) {
  const cs = new Set();
  for (let i = 1; i < pontos.length; i++) {
    const [x1, y1] = toXY(...pontos[i - 1]), [x2, y2] = toXY(...pontos[i]), n = Math.max(1, Math.ceil(Math.hypot(x2 - x1, y2 - y1) / 20));
    for (let k = 0; k <= n; k++) cs.add(cellOf(...toLL(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n), true));
  }
  return [...cs];
}
export async function calcular() {
  const R = S.route; R.cells = []; R.res = null; R.erro = null; routeLayer.clearLayers(); subirGaveta();
  endMarker(R.a, 'A').addTo(routeLayer); endMarker(R.b, 'B').addTo(routeLayer);
  renderSelection(); renderRoutePanel();
  const relatos = new Map(); for (const r of recentReports().filter(periodOk)) relatos.set(r.cell, (relatos.get(r.cell) || 0) + 1);
  let res;
  try { res = await rotear(R.a, R.b, R.modo, relatos); } catch (e) { console.warn('rota:', e); res = { erro: 'grafo' }; }
  if (S.route !== R) return; // o trajeto foi trocado ou fechado enquanto calculava
  if (res.erro) { R.erro = res.erro; renderRoutePanel(); return; }
  for (const r of [res.rapida, res.segura]) { r.cells = celulasDe(r.pontos); r.nrel = r.cells.reduce((s, c) => s + (relatos.get(c) || 0), 0); }
  R.res = res; R.cells = res.segura.cells; R.relatos = relatos;
  if (!res.igual) L.polyline(res.rapida.pontos, { renderer, interactive: false, color: C.ink, weight: 3, dashArray: '8 7', opacity: 0.8 }).addTo(routeLayer);
  L.polyline(res.segura.pontos, { renderer, interactive: false, color: C.brand, weight: 5, opacity: 0.95 }).addTo(routeLayer);
  map.fitBounds(L.latLngBounds(res.segura.pontos).pad(0.25), { maxZoom: 16 });
  renderSelection(); renderRoutePanel();
}
const ERROS = { longe: 'Um dos pontos está longe das ruas para esse modo. Escolha pontos mais perto de uma rua.', 'sem-caminho': 'Não achei caminho entre os dois pontos para esse modo.', grafo: 'Não consegui carregar as ruas para calcular a rota.' };
export function renderRoutePanel() {
  const P = $('#panel'), R = S.route; P.replaceChildren(); P.hidden = false; P.dataset.kind = 'route'; delete P.dataset.cell;
  const per = activePeriod(), res = R.res;
  P.append(h('header', null,
    h('div', null, h('small', null, MODOS[R.modo].nome + ' · ' + (per === 'todos' ? 'qualquer horário' : PER[per].long)),
      h('h3', { text: res ? fmtTempo(res.segura.segundos) + ' · ' + fmtKm(res.segura.metros) : R.erro ? 'Sem rota' : 'Calculando a rota…' })),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: () => clearRoute() }, icon('x'))));
  const body = h('div', { class: 'body' });
  body.append(h('div', { class: 'psec' }, h('div', { class: 'seg', role: 'group', 'aria-label': 'Como você vai' },
    ...Object.entries(MODOS).map(([k, m]) => h('button', { type: 'button', class: k === R.modo ? 'on' : '', 'aria-pressed': k === R.modo ? 'true' : 'false', onclick: () => { if (k !== R.modo) { R.modo = k; calcular(); } } }, m.nome)))));
  if (R.erro) body.append(h('div', { class: 'psec' }, h('p', null, ERROS[R.erro])));
  if (res) {
    const lin = (r, rot, estilo) => h('p', null, h('span', { style: 'display:inline-block;width:26px;border-top:' + estilo + ';vertical-align:middle;margin-right:8px' }), h('b', { text: rot }), ' ' + fmtTempo(r.segundos) + ' · ' + fmtKm(r.metros) + ' · ' + plural(r.nrel, 'relato', 'relatos') + ' no caminho');
    body.append(h('div', { class: 'psec' },
      lin(res.segura, res.igual ? (res.segura.nrel ? 'Sem alternativa que evite os relatos:' : 'Mais rápida, sem precisar desviar:') : 'Evitando relatos:', '4px solid ' + C.brand),
      res.igual ? null : lin(res.rapida, 'Mais rápida:', '3px dashed ' + C.ink)));
    const rows = res.segura.cells.filter(c => R.relatos.get(c)), pq = new Set(res.segura.cells.map(grossa).filter(g => D.pesq.cells[g] && percValue(D.pesq.cells[g])));
    body.append(h('div', { class: 'psec' }, h('p', null, h('b', { text: plural(res.segura.cells.length, 'área de 150 m no caminho', 'áreas de 150 m no caminho') }),
      pq.size ? ' · ' + plural(pq.size, 'região citada', 'regiões citadas') + ' na pesquisa' : '')));
    const ul = h('ul', { class: 'reports' });
    for (const id of rows) ul.append(h('li', { class: 'rep', style: 'border-color:var(--amb-3)' },
      h('div', { style: 'display:flex;justify-content:space-between;gap:8px;align-items:center' }, h('b', { text: areaName(id) }), h('button', { class: 'btn sm ghost', type: 'button', onclick: () => openPanel(id) }, 'Ver')),
      h('div', { class: 'meta', text: plural(R.relatos.get(id), 'relato recente', 'relatos recentes') })));
    body.append(h('div', { class: 'psec' }, rows.length ? ul : h('p', null, 'Nenhum relato recente no caminho.')));
  }
  P.append(body);
  P.append(h('div', { class: 'actions' },
    h('button', { class: 'btn', type: 'button', onclick: startRoute }, icon('route'), 'Novo trajeto'),
    h('button', { class: 'btn', type: 'button', onclick: () => clearRoute() }, 'Limpar')));
}
export function clearRoute(keepPanel) {
  S.routeMode = false; S.route = null; routeLayer.clearLayers();
  $('#routebar').hidden = true; $('#btnRoute').classList.remove('on'); map.getContainer().classList.remove('picking');
  if (!keepPanel) $('#panel').hidden = true;
  renderSelection(); renderEmptyHint();
}
