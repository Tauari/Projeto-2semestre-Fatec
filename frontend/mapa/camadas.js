import { janelaTxt } from '../config.js';
import { D } from '../shared/dados.js';
import { S, activePeriod } from '../shared/estado.js';
import { filteredReports } from '../relatos/relatos.js';

/* ------------------------------------------------------------------ camadas: valor de cada célula e escala de cores */
export function percValue(c) {
  const p = activePeriod(); if (p === 'todos') return c.n;
  const hh = c.h || {}; let v = (hh[p] || 0) + (hh.todo || 0);
  if (p === 'manha' || p === 'tarde') v += hh.dia || 0;
  return Math.min(v, c.n);
}
export function layerValues(layer = S.layer) {
  const m = new Map();
  if (layer === 'relatos') for (const r of filteredReports()) m.set(r.cell, (m.get(r.cell) || 0) + 1);
  else if (layer === 'percepcao') for (const [id, c] of Object.entries(D.pesq.cells)) { const v = percValue(c); if (v > 0) m.set(id, v); }
  else for (const [id, c] of Object.entries(D.bo.cells)) { const v = S.cat === 'n' ? c.n : c[S.cat]; if (v > 0) m.set(id, v); }
  return m;
}
export const SCALES = {
  relatos: { vars: ['--amb-1', '--amb-2', '--amb-3', '--amb-4'], breaks: [1, 2, 3, 5], labels: ['1', '2', '3–4', '5+'], get title() { return 'Relatos nos últimos ' + janelaTxt(); } },
  percepcao: { vars: ['--lil-1', '--lil-2', '--lil-3', '--lil-4'], breaks: [1, 2, 4, 9], labels: ['1', '2–3', '4–8', '9+'], title: 'Mulheres que citaram a área' },
  historico: { vars: ['--rose-1', '--rose-2', '--rose-3', '--rose-4'], breaks: [1, 5, 10, 20], labels: ['1–4', '5–9', '10–19', '20+'], title: 'Registros de B.O. por área' }
};
export function classOf(v, breaks) { let k = -1; for (let i = 0; i < breaks.length; i++) if (v >= breaks[i]) k = i; return k; }
