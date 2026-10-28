import { janelaTxt } from '../config.js';
import { $, h, icon } from '../shared/dom.js';
import { plural } from '../shared/formato.js';
import { PER } from '../shared/vocabulario.js';
import { D } from '../shared/dados.js';
import { cellCenter, grossa, ehFina, dentro } from '../shared/grade.js';
import { areaName } from '../shared/bairros.js';
import { S } from '../shared/estado.js';
import { renderSelection } from './mapa.js';
import { subirGaveta } from './gaveta.js';
import { clearRoute, renderRoutePanel } from './trajeto.js';
import { APOIO, fmtDist, nearestByNeed } from '../apoio/rede.js';
import { renderApoio, apRow } from '../apoio/camada-apoio.js';
import { recentReports } from '../relatos/relatos.js';
import { reportItem } from '../relatos/item-relato.js';

/* ------------------------------------------------------------------ painel da área */
export function closePanel() { $('#panel').hidden = true; S.selected = null; renderSelection(); if (S.apSel) { S.apSel = null; renderApoio(); } }
export function openPanel(id, atualizando = false) {
  if (S.route && S.route.cells) clearRoute(true);
  S.selected = id; renderSelection();
  if (S.apSel) { S.apSel = null; renderApoio(); }
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; P.dataset.cell = id; P.dataset.kind = 'area';
  P.append(h('header', null,
    h('div', null, h('small', null, ehFina(id) ? 'Área · célula de ~150 m' : 'Área · célula de ~1 km'), h('h3', { text: areaName(id) })),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: closePanel }, icon('x'))));
  const body = h('div', { class: 'body' });
  const reps = recentReports().filter(r => dentro(r.cell, id));
  const sec1 = h('div', { class: 'psec' }, h('h4', null, 'Relatos recentes', h('span', { class: 'tag', text: reps.length ? plural(reps.length, 'em ' + janelaTxt(), 'em ' + janelaTxt()) : '' })));
  if (reps.length) {
    const night = reps.filter(r => ['18-20', '20-22', '22-00', 'madrugada'].includes(r.periodo)).length;
    if (reps.length > 1) sec1.append(h('p', null, plural(reps.length, 'relato', 'relatos') + ' nesta área' + (night ? ', ' + night + ' à noite ou de madrugada' : '') + '.'));
    const ul = h('ul', { class: 'reports' }); for (const r of reps.slice(0, 12)) ul.append(reportItem(r)); sec1.append(ul);
  } else sec1.append(h('p', null, 'Nenhum relato nos últimos ' + janelaTxt() + ' nesta área.'));
  body.append(sec1);
  const pc = D.pesq.cells[grossa(id)];
  if (pc) {
    const hh = pc.h || {}, maxH = Math.max(1, ...['18-20', '20-22', '22-00', 'madrugada'].map(k => hh[k] || 0));
    const bars = h('div', { class: 'hbars' });
    for (const k of ['18-20', '20-22', '22-00', 'madrugada']) bars.append(h('div', { class: 'hbar' }, h('span', { text: PER[k].label }), h('i', { style: 'width:' + (100 * (hh[k] || 0) / maxH) + '%' }), h('em', { class: 'num', text: hh[k] || 0 })));
    body.append(h('div', { class: 'psec' }, h('h4', null, 'Percepção da pesquisa'),
      h('p', null, h('b', { text: plural(pc.n, 'mulher citou', 'mulheres citaram') }), ' esta região como insegura (' + pc.a.map(x => x[0]).join(', ') + ').'),
      h('small', null, 'Horários em que a região gera mais insegurança, segundo quem a citou:'), bars));
  }
  if (!pc && !reps.length) body.append(h('p', { class: 'muted', style: 'padding:14px 0' }, 'Ainda não há relatos ou menções na pesquisa nesta área.'));
  if (APOIO.length) body.append(h('div', { class: 'psec' }, h('h4', null, 'Ajuda mais perto', h('span', { class: 'tag', text: 'do centro da área, em linha reta' })),
    h('ul', { class: 'aplist' }, nearestByNeed(cellCenter(id)).map(({ p, d }) => apRow(p, fmtDist(d)))),
    h('small', null, 'Em perigo agora, ligue 190.')));
  P.append(body);
  if (!atualizando) subirGaveta();
}
export function refreshPanel() {
  const P = $('#panel'); if (P.hidden) return;
  if (P.dataset.kind === 'area' && P.dataset.cell) { const sc = P.querySelector('.body').scrollTop; openPanel(P.dataset.cell, true); P.querySelector('.body').scrollTop = sc; }
  else if (P.dataset.kind === 'route' && S.route && S.route.cells) renderRoutePanel();
}
