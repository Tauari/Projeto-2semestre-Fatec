/* grade hexagonal (~1 km) */
export let HX, MLNG;
export const S3 = Math.sqrt(3), MLAT = 110574;
export function configurarGrade(hex) { HX = hex; MLNG = 111320 * Math.cos(HX.lat0 * Math.PI / 180); }
export const toXY = (lat, lng) => [(lng - HX.lng0) * MLNG, (lat - HX.lat0) * MLAT];
export const toLL = (x, y) => [HX.lat0 + y / MLAT, HX.lng0 + x / MLNG];
export function cellOf(lat, lng) {
  const [x, y] = toXY(lat, lng);
  const q = (S3 / 3 * x - y / 3) / HX.R, r = (2 / 3 * y) / HX.R, s = -q - r;
  let rq = Math.round(q), rr = Math.round(r); const rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs; else if (dr > ds) rr = -rq - rs;
  return (rq || 0) + '_' + (rr || 0);
}
export function cellXY(id) { const [q, r] = id.split('_').map(Number); return [HX.R * S3 * (q + r / 2), HX.R * 1.5 * r]; }
export const cellCenter = id => toLL(...cellXY(id));
export function cellPoly(id) {
  const [cx, cy] = cellXY(id), pts = [];
  for (let k = 0; k < 6; k++) { const a = Math.PI / 180 * (60 * k - 30); pts.push(toLL(cx + HX.R * Math.cos(a), cy + HX.R * Math.sin(a))); }
  return pts;
}
export function distM(a, b) { const [x1, y1] = toXY(a[0], a[1]), [x2, y2] = toXY(b[0], b[1]); return Math.hypot(x2 - x1, y2 - y1); }
