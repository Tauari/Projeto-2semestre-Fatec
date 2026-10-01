import { $, h, icon } from '../shared/dom.js';
import { AP, APBY, apInfo, apSvg, telHref, apDirections } from './rede.js';
import { fazList, telRows, focusApoio } from './camada-apoio.js';

/* página Apoio: a mesma lista, agrupada pelo que a mulher precisa fazer */
export const eyebrow = tipo => h('p', { class: 'eyebrow' }, h('span', { class: 'ap-dot', html: apSvg(tipo, 'i sm') }), (AP.tipos[tipo] || {}).nome || '');
export function apCard(p0) {
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
export function crasCard() {
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
export function renderApoioPage() {
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
