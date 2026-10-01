/* estado dos filtros */
import { LS } from './armazenamento-local.js';
import { currentPeriod } from './vocabulario.js';

export const S = { layer: 'percepcao', userLayer: false, period: 'todos', tipo: 'todos', cat: 'n', selected: null, route: null, routeMode: false, pick: null, view: 'mapa', showAll: false,
  apoio: LS.get('apoio', true) !== false, apSel: null };
export const activePeriod = () => (S.period === 'agora' ? currentPeriod() : S.period);
export function periodOk(r) { const p = activePeriod(); return p === 'todos' || r.periodo === p; }
