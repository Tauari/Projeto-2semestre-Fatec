/* formatação de texto, números e datas */
export const DAY = 864e5;
export const norm = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
export const escRe = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
export const fmtN = n => Number(n).toLocaleString('pt-BR');
export const pct = (v, n) => Math.round(100 * v / n);
export const plural = (n, s, p) => fmtN(n) + ' ' + (n === 1 ? s : p);
export const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
export const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
export function fmtDate(iso) { const [y, m, d] = iso.split('-').map(Number); return d + ' ' + MESES[m - 1] + ' ' + y; }
export function ago(ts) {
  const ms = Date.now() - ts, d = Math.floor(ms / DAY);
  if (d <= 0) { const hr = Math.floor(ms / 36e5); return hr <= 0 ? 'agora há pouco' : 'há ' + plural(hr, 'hora', 'horas'); }
  return d === 1 ? 'ontem' : 'há ' + d + ' dias';
}
