/* páginas */
import { $, $$ } from './dom.js';
import { S } from './estado.js';
import { renderDados } from '../dashboard/dados-pesquisa.js';
import { renderAlertas } from '../relatos/alertas.js';
import { renderMod } from '../moderacao/moderacao.js';
import { map, placeLabels } from '../mapa/mapa.js';

export function showView(v) {
  if (!document.getElementById('view-' + v)) v = 'mapa';
  const hash = v === 'mapa' ? '' : '#' + v;
  if (location.hash !== hash) history.pushState(null, '', location.pathname + location.search + hash);
  S.view = v;
  document.body.classList.toggle('area-equipe', v === 'moderacao');
  if (v === 'moderacao') { $('#chat').classList.remove('open', 'picking'); document.body.style.overflow = ''; }
  for (const sec of $$('.view')) sec.hidden = sec.id !== 'view-' + v;
  for (const b of $$('[data-view]')) b.classList.toggle('on', b.dataset.view === v);
  $('#crumb').textContent = $('#view-' + v).dataset.title;
  if (v === 'dados') renderDados();
  if (v === 'alertas') renderAlertas(true);
  if (v === 'moderacao') renderMod();
  if (v === 'mapa' && map) setTimeout(() => { map.invalidateSize(); placeLabels(); }, 60);
  window.scrollTo(0, 0);
}

export function instalarNavegacao() {
  const abrir = () => showView(location.hash.slice(1) || 'mapa');
  window.addEventListener('popstate', abrir);
  window.addEventListener('hashchange', abrir);
  abrir();
}
