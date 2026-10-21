import { $, $$ } from '../shared/dom.js';
import { TIPOS, PERIODOS, PER, currentPeriod } from '../shared/vocabulario.js';
import { D } from '../shared/dados.js';
import { S } from '../shared/estado.js';

/* ------------------------------------------------------------------ controles */
export function renderPeriodSel() {
  const sel = $('#periodSel'), dis = S.layer === 'historico';
  sel.replaceChildren(new Option('Qualquer horário', 'todos'), new Option('Agora · ' + PER[currentPeriod()].label, 'agora'), ...PERIODOS.map(p => new Option(p.long, p.id)));
  sel.value = S.period; sel.disabled = dis; sel.title = dis ? 'A base de B.O. não informa horário' : '';
}
export function renderTypeSel() {
  const sel = $('#typeSel'); sel.replaceChildren();
  if (S.layer === 'relatos') { sel.hidden = false; sel.append(new Option('Todos os tipos', 'todos'), ...TIPOS.map(t => new Option(t.label, t.id))); sel.value = S.tipo; }
  else if (S.layer === 'historico') { sel.hidden = false; for (const [v, l] of [['n', 'Todas as categorias'], ['vd', 'Violência doméstica'], ['fe', 'Feminicídio'], ['te', 'Tentativa de feminicídio']]) sel.append(new Option(l, v)); sel.value = S.cat; }
  else sel.hidden = true;
}
export function syncControls() {
  for (const b of $$('#layerSeg button')) { const on = b.dataset.layer === S.layer; b.classList.toggle('on', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); }
  renderPeriodSel(); renderTypeSel();
}
