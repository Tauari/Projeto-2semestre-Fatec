import { $, h, icon } from '../shared/dom.js';
import { plural } from '../shared/formato.js';
import { PER } from '../shared/vocabulario.js';
import { D } from '../shared/dados.js';
import { toXY, toLL, cellOf, cellCenter } from '../shared/grade.js';
import { areaName } from '../shared/bairros.js';
import { S, activePeriod, periodOk } from '../shared/estado.js';
import { percValue } from './camadas.js';
import { map, renderer, routeLayer, C, renderSelection, renderEmptyHint } from './mapa.js';
import { closePanel, openPanel } from './painel-area.js';
import { stopPick } from './selecao.js';
import { recentReports } from '../relatos/relatos.js';

/* ------------------------------------------------------------------ trajeto (linha reta) */
export function startRoute() {
  closePanel(); stopPick();
  S.routeMode = true; S.route = { a: null, b: null, cells: null };
  routeLayer.clearLayers();
  $('#routebar').hidden = false; $('#routeMsg').textContent = 'Toque no ponto de partida';
  $('#btnRoute').classList.add('on'); map.getContainer().classList.add('picking');
  renderEmptyHint();
}
export function routeFrom(id) { startRoute(); routeClick(L.latLng(...cellCenter(id))); }
export function endMarker(ll, t) { return L.marker(ll, { icon: L.divIcon({ className: '', html: '<span class="route-end">' + t + '</span>', iconSize: [0, 0] }), interactive: false, keyboard: false }); }
export function routeClick(ll) {
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
export function renderRoutePanel() {
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
export function clearRoute(keepPanel) {
  S.routeMode = false; S.route = null; routeLayer.clearLayers();
  $('#routebar').hidden = true; $('#btnRoute').classList.remove('on'); map.getContainer().classList.remove('picking');
  if (!keepPanel) $('#panel').hidden = true;
  renderSelection(); renderEmptyHint();
}
