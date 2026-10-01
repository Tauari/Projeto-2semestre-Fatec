import { distM } from '../shared/grade.js';

/* ------------------------------------------------------------------ rede de apoio: onde pedir ajuda */
/* a rede chega depois do carregamento (servidor ou arquivo estático): configurarApoio() preenche os três */
export let AP = { tipos: {}, grupos: [], pontos: [] }, APBY = {}, APOIO = [];
export function configurarApoio(ap) {
  AP = ap || { tipos: {}, grupos: [], pontos: [] };
  APBY = Object.fromEntries(AP.pontos.map(p => [p.id, p]));
  APOIO = AP.pontos.filter(p => typeof p.lat === 'number' && typeof p.lng === 'number');
}
export const AP_ORDER = ['policia', 'mulher', 'justica', 'social', 'saude'];
export const AP_CORE = ['ddm', 'gcm', 'mulher', 'creas', 'defensoria', 'santacasa', 'upa29'];
export const PREC = {
  exata: 'Ponto do prédio no OpenStreetMap.',
  endereco: 'Ponto calculado pelo endereço, sobre as ruas do OpenStreetMap. Margem de uns 30 metros.',
  aproximada: 'Posição aproximada, com margem de até 100 metros. Confira o endereço antes de ir.'
};
/* os CRAS dividem a mesma descrição, horário e fonte */
export function apInfo(p) { return p && p.grupo === 'cras' && AP.cras ? Object.assign({}, AP.cras, { sub: 'Centro de Referência de Assistência Social' }, p) : p; }
export const apSvg = (tipo, cls = 'i') => '<svg class="' + cls + '" aria-hidden="true"><use href="#i-' + ((AP.tipos[tipo] || {}).icone || 'pin') + '"/></svg>';
export function fmtDist(m) { return m < 950 ? 'a ' + Math.max(50, Math.round(m / 50) * 50) + ' m' : 'a ' + (m / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' km'; }
export function nearestApoio(ll, n = 3, tipos) {
  return APOIO.filter(p => !tipos || tipos.includes(p.tipo)).map(p => ({ p, d: distM(ll, [p.lat, p.lng]) })).sort((a, b) => a.d - b.d).slice(0, n);
}
/* o ponto mais perto para registrar ocorrência, para conversar e para a saúde */
export function nearestByNeed(ll) {
  return [['policia'], ['mulher', 'social'], ['saude']].map(t => nearestApoio(ll, 1, t)[0]).filter(Boolean);
}
export function telHref(n) { const d = n.replace(/\D/g, ''); return 'tel:' + (d.length >= 10 && d[0] !== '0' ? '+55' + d : d); }
export function apDirections(p) {
  const dest = p.precisao === 'aproximada' ? encodeURIComponent(p.end + ', ' + p.bairro + ', Rio Claro - SP') : p.lat + ',' + p.lng;
  return 'https://www.google.com/maps/dir/?api=1&destination=' + dest;
}
