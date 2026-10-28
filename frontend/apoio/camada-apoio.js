import { subirGaveta } from '../mapa/gaveta.js';
import { $, h, icon, esc } from '../shared/dom.js';
import { plural } from '../shared/formato.js';
import { LS } from '../shared/armazenamento-local.js';
import { S } from '../shared/estado.js';
import { map, placeLabels, renderLegend, renderSelection, onMapClick, panelInset, flyToVisible, isVisible, withMap } from '../mapa/mapa.js';
import { closePanel } from '../mapa/painel-area.js';
import { clearRoute } from '../mapa/trajeto.js';
import { AP, APBY, APOIO, AP_ORDER, AP_CORE, PREC, apInfo, apSvg, fmtDist, nearestByNeed, telHref, apDirections } from './rede.js';

export let apLayer = null, APV = [];
/* chamada pelo initMap, no lugar em que o legado criava a camada */
export function initApoioLayer() { apLayer = L.layerGroup().addTo(map); }
export function setApoio(on) {
  S.apoio = on; LS.set('apoio', on);
  if (!on && S.apSel) closePanel();
  renderApoio(); renderLegend(); placeLabels();
}
/* pontos muito próximos na tela viram um círculo com o número de serviços */
export function apClusters() {
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
export function renderApoio() {
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
export function flyToApoio(ids) {
  const pts = ids.map(id => APBY[id]).filter(p => p && p.lat != null);
  if (!pts.length) return;
  if (pts.length === 1) { flyToVisible([pts[0].lat, pts[0].lng], Math.max(map.getZoom(), 16)); return; }
  const [dx, dy] = panelInset();
  map.flyToBounds(L.latLngBounds(pts.map(p => [p.lat, p.lng])), { paddingTopLeft: [48, 64], paddingBottomRight: [48 + dx, 48 + dy], maxZoom: 16, duration: 0.6 });
}
export function focusApoio(id) {
  const p = APBY[id]; if (!p || p.lat == null) return;
  withMap(() => { openApoio(id); flyToApoio([id]); });
}
export function showApoioOnMap() { withMap(() => { closePanel(); flyToApoio(AP_CORE); }); }
export function telRows(tel) {
  return (tel || []).map(([n, l]) => h('div', { class: 'telrow' },
    h('div', null, h('a', { href: telHref(n), class: 'num', text: n }), l ? h('small', { text: l }) : null),
    h('div', { class: 'acts' },
      h('a', { href: telHref(n), class: 'btn primary sm', 'aria-label': 'Ligar para ' + n }, icon('phone', 'i sm'), 'Ligar'),
      h('button', { class: 'btn sm', type: 'button', 'data-copy': n, 'aria-label': 'Copiar ' + n }, icon('copy', 'i sm'), 'Copiar'))));
}
export function srcLine(p) {
  const fs = p.fontes || [];
  return h('p', { class: 'srcs' }, fs.length ? 'Fonte: ' : '', fs.map((f, i) => [i ? '; ' : '', h('a', { href: f[1], target: '_blank', rel: 'noopener', text: f[0] })]), fs.length ? '. ' : '', 'Mapa © OpenStreetMap.');
}
export function openApoio(id, { reveal = false } = {}) {
  const p = apInfo(APBY[id]); if (!p) return;
  const T = AP.tipos[p.tipo] || { nome: '' };
  if (S.route && S.route.cells) clearRoute(true);
  S.selected = null; renderSelection();
  S.apSel = id; renderApoio();
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; subirGaveta(); P.dataset.kind = 'apoio'; P.dataset.ap = id; delete P.dataset.cell;
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
export function apRow(p, extra) {
  p = apInfo(p);
  return h('li', null, h('button', { type: 'button', class: 't-' + p.tipo, onclick: () => openApoio(p.id, { reveal: true }) },
    h('span', { class: 'ic', html: apSvg(p.tipo, 'i sm') }),
    h('span', null, h('b', { text: p.curto || p.nome }), h('span', { class: 's', text: p.end + (p.bairro ? ' · ' + p.bairro : '') })),
    extra ? h('span', { class: 'dist', text: extra }) : icon('chev')));
}
/* versão arquivo: depois de "Mostrar onde estou", os serviços mais perto de onde ela está */
export function openNearMe(ll) {
  if (S.route && S.route.cells) clearRoute(true);
  S.selected = null; renderSelection(); if (S.apSel) { S.apSel = null; renderApoio(); }
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; subirGaveta(); P.dataset.kind = 'perto'; delete P.dataset.cell; delete P.dataset.ap;
  P.append(h('header', null,
    h('div', null, h('small', null, 'Onde pedir ajuda'), h('h3', null, 'Mais perto de você')),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: closePanel }, icon('x'))));
  P.append(h('div', { class: 'body' }, h('div', { class: 'psec' },
    h('ul', { class: 'aplist' }, nearestByNeed(ll).map(({ p, d }) => apRow(p, fmtDist(d)))),
    h('small', null, 'Distância em linha reta. Sua localização fica só neste aparelho.')),
    h('div', { class: 'psec' }, h('p', null, h('b', null, 'Em perigo agora?'), ' Ligue 190 (Polícia Militar) ou 153 (Guarda Civil).'))));
}
export function openApoioList(ids) {
  if (S.route && S.route.cells) clearRoute(true);
  S.selected = null; renderSelection(); S.apSel = null; renderApoio();
  const P = $('#panel'); P.replaceChildren(); P.hidden = false; subirGaveta(); P.dataset.kind = 'apoio-lista'; delete P.dataset.cell; delete P.dataset.ap;
  const same = ids.every(id => APBY[id].lat === APBY[ids[0]].lat && APBY[id].lng === APBY[ids[0]].lng);
  P.append(h('header', null,
    h('div', null, h('small', null, 'Onde pedir ajuda'), h('h3', { text: plural(ids.length, 'serviço', 'serviços') + (same ? ' no mesmo prédio' : ' aqui perto') })),
    h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fechar', onclick: closePanel }, icon('x'))));
  P.append(h('div', { class: 'body' }, h('div', { class: 'psec' }, h('ul', { class: 'aplist' }, ids.map(id => apRow(APBY[id]))))));
  if (!same) P.append(h('div', { class: 'actions one' }, h('button', { class: 'btn', type: 'button', onclick: () => flyToApoio(ids) }, icon('plus'), 'Aproximar o mapa')));
}
export const fazList = faz => h('ul', { class: 'faz' }, faz.map(f => h('li', null, icon('check', 'i sm'), h('span', { text: f }))));
