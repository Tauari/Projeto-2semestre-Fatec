/* "Alertas ao vivo" no mapa, como os avisos do Waze: um título padrão por tipo, onde e há quanto tempo.
   Tocando no alerta aparece a descrição que a usuária deixou (já sem dados pessoais) e o botão para ver a área no mapa. */
import { CONFIG } from '../config.js';
import { $, h } from '../shared/dom.js';
import { areaName } from '../shared/bairros.js';
import { TIPO } from '../shared/vocabulario.js';
import { focusCell } from '../mapa/lista-areas.js';
import { alertasAoVivo, tipoDoAlerta, tituloAlerta, haQuanto } from './alerta.js';

const MAX_VISIVEIS = 3;
const abertos = new Set();
let verTodos = false;

export function renderAoVivo() {
  const el = $('#liveAlerts'); if (!el) return;
  const lista = alertasAoVivo();
  el.replaceChildren();
  if (!lista.length) { el.hidden = true; return; }
  el.hidden = false;
  el.append(h('p', { class: 'live-label', text: 'Alertas ao vivo · últimas ' + CONFIG.alertasAoVivoHoras + ' h' }));
  for (const r of verTodos ? lista : lista.slice(0, MAX_VISIVEIS)) {
    const aberto = abertos.has(r.id);
    const card = h('div', { class: 'live-card', style: '--c:' + TIPO[tipoDoAlerta(r.tipos)].cor });
    card.append(h('button', { type: 'button', class: 'live-head', 'aria-expanded': aberto ? 'true' : 'false',
      onclick: () => { if (abertos.has(r.id)) abertos.delete(r.id); else abertos.add(r.id); renderAoVivo(); } },
      h('span', { class: 'live-ico', 'aria-hidden': 'true' }),
      h('span', { class: 'live-txt' }, h('b', { text: tituloAlerta(r.tipos) }), h('small', { text: areaName(r.cell) + ' · ' + haQuanto(r.criado) }))));
    if (aberto) card.append(h('div', { class: 'live-detail' },
      r.texto ? h('p', { class: 'txt', text: r.texto }) : null,
      h('p', { class: 'meta', text: 'Relato de uma usuária · não verificado' }),
      h('button', { type: 'button', class: 'btn sm', onclick: () => focusCell(r.cell) }, 'Ver no mapa')));
    el.append(card);
  }
  if (lista.length > MAX_VISIVEIS) el.append(h('button', { type: 'button', class: 'linkbtn live-more', onclick: () => { verTodos = !verTodos; renderAoVivo(); } },
    verTodos ? 'Mostrar menos' : 'Ver mais ' + (lista.length - MAX_VISIVEIS)));
}
