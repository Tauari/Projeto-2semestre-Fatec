import { CONFIG } from '../config.js';
import { DAY } from '../shared/formato.js';
import { TIPO, PER, QUANDO } from '../shared/vocabulario.js';
import { Store } from '../shared/store.js';
import { S, periodOk } from '../shared/estado.js';

/* relatos: validação (dado compartilhado não é confiável) e visibilidade */
export const CELL_RE = /^-?\d{1,3}_-?\d{1,3}$/;
export function cleanReport(r) {
  if (!r || typeof r !== 'object') return null;
  const tipos = Array.isArray(r.tipos) ? r.tipos.filter(t => TIPO[t]).slice(0, CONFIG.tiposMax) : [];
  if (!tipos.length || typeof r.cell !== 'string' || !CELL_RE.test(r.cell) || typeof r.criado !== 'number') return null;
  return {
    id: String(r.id), tipos, cell: r.cell,
    quando: QUANDO[r.quando] ? r.quando : null, periodo: PER[r.periodo] ? r.periodo : null,
    texto: typeof r.texto === 'string' ? r.texto.slice(0, Math.max(320, CONFIG.textoMax)) : '', criado: r.criado,
    origem: r.origem === 'chat-ia' ? 'chat-ia' : 'chat'
  };
}
export function allReports() { const out = []; for (const r of Store.reports.values()) { const c = cleanReport(r); if (c) out.push(c); } return out.sort((a, b) => b.criado - a.criado); }
export function isHidden(r) { if (Store.mod.verificado[r.id]) return false; if (Store.mod.oculto[r.id]) return true; const v = Store.votes[r.id]; return !!(v && v.f >= 3); }
export function recentReports() { const lim = Date.now() - CONFIG.janelaDias * DAY; return allReports().filter(r => r.criado >= lim && !isHidden(r)); }
export function filteredReports() { return recentReports().filter(r => periodOk(r) && (S.tipo === 'todos' || r.tipos.includes(S.tipo))); }
