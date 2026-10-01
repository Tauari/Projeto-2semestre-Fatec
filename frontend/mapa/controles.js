import { janelaTxt } from '../config.js';
import { $, $$, h } from '../shared/dom.js';
import { fmtDate } from '../shared/formato.js';
import { TIPOS, PERIODOS, PER, currentPeriod } from '../shared/vocabulario.js';
import { D } from '../shared/dados.js';
import { S } from '../shared/estado.js';
import { renderMap } from './mapa.js';
import { refreshPanel } from './painel-area.js';

/* ------------------------------------------------------------------ controles */
export function renderChips() {
  const el = $('#periodChips'); el.replaceChildren();
  const now = currentPeriod(), dis = S.layer === 'historico';
  const list = [{ id: 'todos', label: 'Qualquer horário' }, { id: 'agora', label: 'Agora · ' + PER[now].label, cls: 'now' }, ...PERIODOS];
  for (const p of list) el.append(h('button', { type: 'button', class: 'chip' + (p.cls ? ' ' + p.cls : '') + (S.period === p.id ? ' on' : ''), 'aria-pressed': S.period === p.id ? 'true' : 'false', disabled: dis,
    onclick: () => { S.period = p.id; renderChips(); renderMap(); refreshPanel(); } }, p.label));
  el.style.opacity = dis ? 0.45 : 1; el.title = dis ? 'A base de B.O. não informa horário' : '';
}
export function renderTypeSel() {
  const sel = $('#typeSel'); sel.replaceChildren();
  if (S.layer === 'relatos') { sel.hidden = false; sel.append(new Option('Todos os tipos', 'todos'), ...TIPOS.map(t => new Option(t.label, t.id))); sel.value = S.tipo; }
  else if (S.layer === 'historico') { sel.hidden = false; for (const [v, l] of [['n', 'Todas as categorias'], ['vd', 'Violência doméstica'], ['fe', 'Feminicídio'], ['te', 'Tentativa de feminicídio']]) sel.append(new Option(l, v)); sel.value = S.cat; }
  else sel.hidden = true;
  $('#rangeLbl').textContent = { relatos: 'Últimos ' + janelaTxt(), percepcao: 'Pesquisa de ' + fmtDate(D.pesq.de) + ' a ' + fmtDate(D.pesq.ate), historico: 'Jan 2025 – abr 2026 · sem horário' }[S.layer];
}
export function syncControls() {
  for (const b of $$('#layerSeg button')) { const on = b.dataset.layer === S.layer; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); }
  renderChips(); renderTypeSel();
}
