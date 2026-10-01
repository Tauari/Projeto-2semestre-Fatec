import { $ } from '../shared/dom.js';
import { S } from '../shared/estado.js';
import { map, renderEmptyHint } from './mapa.js';
import { closePanel } from './painel-area.js';
import { clearRoute } from './trajeto.js';

/* ------------------------------------------------------------------ marcar local para o chat */
export function startPick(cb) {
  if (S.routeMode || (S.route && S.route.a)) clearRoute();
  closePanel(); S.pick = cb;
  $('#pickbar').hidden = false; map.getContainer().classList.add('picking');
  $('#chat').classList.add('picking');
  document.body.style.overflow = '';
  renderEmptyHint();
  $('#mapwrap').scrollIntoView({ behavior: 'smooth', block: 'center' });
}
export function stopPick() {
  S.pick = null; $('#pickbar').hidden = true;
  if (map) map.getContainer().classList.remove('picking');
  $('#chat').classList.remove('picking'); renderEmptyHint();
}
