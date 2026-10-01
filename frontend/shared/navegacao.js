/* páginas */
import { $, $$ } from './dom.js';
import { S } from './estado.js';
import { renderDados } from '../dashboard/dados-pesquisa.js';
import { renderAlertas } from '../relatos/alertas.js';
import { renderMod, canModerate } from '../moderacao/moderacao.js';
import { map, placeLabels } from '../mapa/mapa.js';

export function showView(v) {
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
