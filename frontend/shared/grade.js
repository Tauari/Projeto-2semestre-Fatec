import { CONFIG } from '../config.js';
/* grades hexagonais: 'q_r' = ~1 km (dados oficiais e pesquisa); 'fq_r' = ~150 m (relatos) */
export let HX, HXF, MLNG;
export const S3 = Math.sqrt(3), MLAT = 110574;
export function configurarGrade(hex) { HX = hex; HXF = { lat0: hex.lat0, lng0: hex.lng0, R: CONFIG.hexRelatosM }; MLNG = 111320 * Math.cos(HX.lat0 * Math.PI / 180); }
export const toXY = (lat, lng) => [(lng - HX.lng0) * MLNG, (lat - HX.lat0) * MLAT];
export const toLL = (x, y) => [HX.lat0 + y / MLAT, HX.lng0 + x / MLNG];
export const ehFina = id => id[0] === 'f';
const grade = id => (ehFina(id) ? HXF : HX);
export function cellOf(lat, lng, fina = false) {
  const G = fina ? HXF : HX, [x, y] = toXY(lat, lng);
  const q = (S3 / 3 * x - y / 3) / G.R, r = (2 / 3 * y) / G.R, s = -q - r;
  let rq = Math.round(q), rr = Math.round(r); const rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs; else if (dr > ds) rr = -rq - rs;
  return (fina ? 'f' : '') + (rq || 0) + '_' + (rr || 0);
}
export function cellXY(id) { const R = grade(id).R, [q, r] = id.replace('f', '').split('_').map(Number); return [R * S3 * (q + r / 2), R * 1.5 * r]; }
export const cellCenter = id => toLL(...cellXY(id));
/* a célula de 1 km que contém esta (os dados oficiais e da pesquisa só existem nessa grade) */
export const grossa = id => (ehFina(id) ? cellOf(...cellCenter(id)) : id);
/* o relato (célula `cell`) está na área `id`, seja ela de 150 m ou de 1 km */
export const dentro = (cell, id) => (ehFina(id) ? cell === id : grossa(cell) === id);
export function cellPoly(id) {
  const R = grade(id).R, [cx, cy] = cellXY(id), pts = [];
  for (let k = 0; k < 6; k++) { const a = Math.PI / 180 * (60 * k - 30); pts.push(toLL(cx + R * Math.cos(a), cy + R * Math.sin(a))); }
  return pts;
}
export function distM(a, b) { const [x1, y1] = toXY(a[0], a[1]), [x2, y2] = toXY(b[0], b[1]); return Math.hypot(x2 - x1, y2 - y1); }
