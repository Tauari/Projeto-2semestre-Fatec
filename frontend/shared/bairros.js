/* bairros e nomes de áreas */
import { D } from './dados.js';
import { norm, escRe } from './formato.js';
import { cellCenter, distM } from './grade.js';

export let BAIRROS = [], BYNAME = {};
export function configurarBairros() {
  BAIRROS = D.bairros.map(([nome, lat, lng, n]) => ({ nome, lat, lng, n, key: norm(nome) }));
  BYNAME = Object.fromEntries(BAIRROS.map(b => [b.nome, b]));
}
export const nameCache = new Map();
export function areaName(id) {
  if (nameCache.has(id)) return nameCache.get(id);
  let nm;
  const bo = D.bo.cells[id];
  if (bo && bo.b.length) nm = bo.b[0][0] + ' e arredores';
  else {
    const c = cellCenter(id); let best = null, bd = Infinity;
    for (const b of BAIRROS) { const d = distM(c, [b.lat, b.lng]); if (d < bd) { bd = d; best = b; } }
    nm = best && bd < 1800 ? 'Perto de ' + best.nome : 'Zona rural de Rio Claro';
  }
  nameCache.set(id, nm); return nm;
}
export function cellSearchText(id) {
  const parts = [areaName(id)];
  const bo = D.bo.cells[id]; if (bo) parts.push(...bo.b.map(x => x[0]));
  const pc = D.pesq.cells[id]; if (pc) parts.push(...pc.a.map(x => x[0]));
  return norm(parts.join(' '));
}
export function searchBairros(q) {
  q = norm(q).trim(); if (!q) return [];
  return BAIRROS.filter(b => b.key.includes(q)).sort((a, b) => (b.key.startsWith(q) - a.key.startsWith(q)) || b.n - a.n);
}
export const LANDMARKS = [[/\bunesp\b/, 'Bela Vista'], [/lago azul/, 'Vila Operária'], [/rodoviaria/, 'Jardim Claret'], [/estacao|jardim publico/, 'Centro']];
export function findBairroInText(text) {
  const t = ' ' + norm(text) + ' ';
  let best = null;
  for (const b of BAIRROS) {
    if (b.key.length < 4) continue;
    if (new RegExp('(^|[^a-z0-9])' + escRe(b.key) + '([^a-z0-9]|$)').test(t) && (!best || b.key.length > best.key.length)) best = b;
  }
  if (best) return best;
  for (const [re, nome] of LANDMARKS) if (re.test(t)) return BYNAME[nome] || null;
  if (/\bcentro\b|zona central/.test(t)) return BYNAME['Centro'] || null;
  return null;
}
export function matchBairro(name) {
  const k = norm(name).trim(); if (!k) return null;
  return BAIRROS.find(b => b.key === k) || BAIRROS.find(b => b.key.includes(k) || k.includes(b.key)) || findBairroInText(name);
}
