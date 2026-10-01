import { $, h, icon, isMobile } from '../shared/dom.js';
import { norm, fmtN, plural, ago } from '../shared/formato.js';
import { TIPO, PER } from '../shared/vocabulario.js';
import { D } from '../shared/dados.js';
import { cellCenter } from '../shared/grade.js';
import { areaName, cellSearchText } from '../shared/bairros.js';
import { S } from '../shared/estado.js';
import { showView } from '../shared/navegacao.js';
import { layerValues, SCALES, classOf } from './camadas.js';
import { map } from './mapa.js';
import { openPanel } from './painel-area.js';
import { filteredReports } from '../relatos/relatos.js';

/* lista de áreas */
export function areaSub(id, v) {
  if (S.layer === 'relatos') {
    const reps = filteredReports().filter(r => r.cell === id);
    const cnt = {}; for (const r of reps) for (const t of r.tipos) cnt[t] = (cnt[t] || 0) + 1;
    const top = Object.entries(cnt).sort((a, b) => b[1] - a[1])[0];
    return (top ? TIPO[top[0]].label : 'Relatos') + ' · mais recente ' + ago(reps[0].criado);
  }
  if (S.layer === 'percepcao') {
    const c = D.pesq.cells[id], hh = c.h || {};
    const topH = ['18-20', '20-22', '22-00', 'madrugada'].sort((a, b) => (hh[b] || 0) - (hh[a] || 0))[0];
    return c.a.map(x => x[0]).join(', ') + (hh[topH] ? ' · mais citado ' + PER[topH].long : '');
  }
  const c = D.bo.cells[id];
  const extra = [c.fe ? plural(c.fe, 'feminicídio', 'feminicídios') : '', c.te ? plural(c.te, 'tentativa', 'tentativas') : ''].filter(Boolean).join(', ');
  return 'B.O. · ' + c.b.slice(0, 2).map(x => x[0]).join(', ') + (extra ? ' · ' + extra : '');
}
export function renderAreaList() {
  const ol = $('#areaList'), q = norm($('#areaSearch').value).trim(), sc = SCALES[S.layer];
  $('#areasTitle').textContent = { relatos: 'Áreas com relatos', percepcao: 'Áreas citadas na pesquisa', historico: 'Áreas com registros de B.O.' }[S.layer];
  let items = [...layerValues().entries()].map(([id, v]) => ({ id, v }));
  if (q) items = items.filter(it => cellSearchText(it.id).includes(q));
  items.sort((a, b) => b.v - a.v || areaName(a.id).localeCompare(areaName(b.id)));
  const lim = S.showAll || q ? items.length : 6;
  ol.replaceChildren();
  if (!items.length) ol.append(h('li', { class: 'none' }, q ? 'Nenhuma área encontrada com esse nome.' : 'Nenhuma área com dados para esse filtro.'));
  for (const it of items.slice(0, lim)) {
    const k = classOf(it.v, sc.breaks);
    ol.append(h('li', null, h('button', { type: 'button', onclick: () => focusCell(it.id) },
      h('span', { class: 'sw', style: 'background:var(' + sc.vars[Math.max(0, k)] + ')' }),
      h('span', null, h('span', { class: 'an', text: areaName(it.id) }), h('span', { class: 'as', text: areaSub(it.id, it.v) })),
      h('span', { class: 'av num', text: fmtN(it.v) }), icon('chev'))));
  }
  const more = $('#areaMore');
  more.hidden = items.length <= 6 || !!q;
  more.textContent = S.showAll ? 'Mostrar menos' : 'Mostrar todas as ' + items.length + ' áreas';
}
export function focusCell(id) {
  showView('mapa');
  const c = cellCenter(id);
  map.flyTo(c, Math.max(map.getZoom(), 14), { duration: 0.6 });
  openPanel(id);
  if (isMobile()) $('#mapwrap').scrollIntoView({ behavior: 'smooth', block: 'center' });
}
