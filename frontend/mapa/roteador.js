/* roteador no próprio aparelho: menor tempo sobre o grafo de ruas (dados/rotas/grafo.json), com custo extra onde há relatos.
   Modos: 1 a pé, 2 bicicleta, 4 carro. Respeita mão única (carro e bicicleta). Não considera semáforo, trânsito nem obras. */
import { CONFIG } from '../config.js';
import { apiGet } from '../shared/api.js';
import { MODO_DADOS } from '../shared/dados.js';
import { cellXY, ehFina, toXY } from '../shared/grade.js';

export const MODOS = { pe: { bit: 1, nome: 'A pé', ms: 4.8 / 3.6 }, bike: { bit: 2, nome: 'Bicicleta', ms: 15 / 3.6 }, carro: { bit: 4, nome: 'Carro', ms: 0 } };
let G = null, carregando = null;

async function ler() {
  const raw = MODO_DADOS === 'api' ? await apiGet('/mapa/rotas') : await fetch(CONFIG.estatico.grafo).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); });
  const n = raw.nos.length / 3, m = raw.arestas.length / 6;
  const lat = new Float64Array(n), lng = new Float64Array(n), giga = new Uint8Array(n), grau = new Int32Array(n + 1);
  for (let i = 0; i < n; i++) { lat[i] = raw.nos[3 * i] / 1e5; lng[i] = raw.nos[3 * i + 1] / 1e5; giga[i] = raw.nos[3 * i + 2]; }
  for (let e = 0; e < m; e++) { grau[raw.arestas[6 * e] + 1]++; grau[raw.arestas[6 * e + 1] + 1]++; }
  for (let i = 0; i < n; i++) grau[i + 1] += grau[i];
  const pos = grau.slice(0, n), para = new Int32Array(2 * m), perm = new Uint8Array(2 * m), met = new Float32Array(2 * m), vel = new Uint8Array(2 * m), aresta = new Int32Array(2 * m), de = new Int32Array(2 * m);
  for (let e = 0; e < m; e++) {
    const [u, v, d, vai, volta, kmh] = raw.arestas.slice(6 * e, 6 * e + 6);
    for (const [a, b, p] of [[u, v, vai], [v, u, volta]]) { const k = pos[a]++; de[k] = a; para[k] = b; perm[k] = p; met[k] = d; vel[k] = kmh; aresta[k] = e; }
  }
  const balde = new Map();
  for (let i = 0; i < n; i++) { const k = Math.floor(lat[i] / 0.002) + ',' + Math.floor(lng[i] / 0.002); (balde.get(k) || balde.set(k, []).get(k)).push(i); }
  G = { n, m, lat, lng, giga, grau, de, para, perm, met, vel, aresta, balde };
}
export function carregarGrafo() { return G ? Promise.resolve(G) : (carregando = carregando || ler().then(() => G, e => { carregando = null; throw e; })); }

/* nó mais próximo do ponto, só entre os do maior trecho conexo do modo (nunca uma ilha de ruas) */
function ancorar(ll, bit) {
  const ci = Math.floor(ll.lat / 0.002), cj = Math.floor(ll.lng / 0.002); let melhor = -1, md = Infinity;
  for (let r = 0; r <= 3 && melhor < 0; r++) for (let i = ci - r; i <= ci + r; i++) for (let j = cj - r; j <= cj + r; j++) {
    for (const k of G.balde.get(i + ',' + j) || []) {
      if (!(G.giga[k] & bit)) continue;
      const d = Math.hypot((G.lat[k] - ll.lat) * 110574, (G.lng[k] - ll.lng) * 102000);
      if (d < md) { md = d; melhor = k; }
    }
  }
  return md < 400 ? melhor : -1;
}

/* custo extra: o hexágono de cada relato vira uma zona (círculo do hexágono + MARGEM de folga, para a rota não encostar na borda).
   Trecho de rua que passa por uma zona custa o tempo vezes (1 + 8 * relatos da zona, no máximo 3): só passa se não houver desvio razoável. */
const MARGEM = 40;
function pesos(relatos) {
  const z = []; for (const [cell, n] of relatos) if (ehFina(cell)) { const [x, y] = cellXY(cell); z.push({ x, y, n }); }
  if (!z.length) return null;
  const raio = CONFIG.hexRelatosM + MARGEM, f = new Float32Array(G.m).fill(-1);
  return k => {
    const e = G.aresta[k];
    if (f[e] < 0) {
      const u = G.de[k], v = G.para[k], [x1, y1] = toXY(G.lat[u], G.lng[u]), [x2, y2] = toXY(G.lat[v], G.lng[v]);
      const passos = Math.max(1, Math.ceil(Math.hypot(x2 - x1, y2 - y1) / 30)); let n = 0;
      for (const a of z) for (let i = 0; i <= passos; i++) if (Math.hypot(x1 + (x2 - x1) * i / passos - a.x, y1 + (y2 - y1) * i / passos - a.y) < raio) { n += a.n; break; }
      f[e] = 1 + 8 * Math.min(3, n);
    }
    return f[e];
  };
}

function menor(a, b, modo, fator) {
  const bit = MODOS[modo].bit, dist = new Float64Array(G.n).fill(Infinity), via = new Int32Array(G.n).fill(-1);
  const heap = [[0, a]]; dist[a] = 0;
  const sobe = i => { while (i > 0) { const p = (i - 1) >> 1; if (heap[p][0] <= heap[i][0]) break; [heap[p], heap[i]] = [heap[i], heap[p]]; i = p; } };
  const desce = i => { for (;;) { let m = i; for (const c of [2 * i + 1, 2 * i + 2]) if (c < heap.length && heap[c][0] < heap[m][0]) m = c; if (m === i) return; [heap[m], heap[i]] = [heap[i], heap[m]]; i = m; } };
  while (heap.length) {
    const [d, u] = heap[0], ult = heap.pop(); if (heap.length) { heap[0] = ult; desce(0); }
    if (d > dist[u]) continue; if (u === b) break;
    for (let k = G.grau[u]; k < G.grau[u + 1]; k++) {
      if (!(G.perm[k] & bit)) continue;
      const v = G.para[k], ms = bit === 4 ? G.vel[k] / 3.6 : MODOS[modo].ms, c = d + G.met[k] / ms * (fator ? fator(k) : 1);
      if (c < dist[v]) { dist[v] = c; via[v] = k; heap.push([c, v]); sobe(heap.length - 1); }
    }
  }
  if (via[b] < 0 && a !== b) return null;
  const nos = [b]; let t = 0, m = 0;
  for (let v = b; v !== a;) { const k = via[v]; t += G.met[k] / (bit === 4 ? G.vel[k] / 3.6 : MODOS[modo].ms); m += G.met[k]; v = G.de[k]; nos.push(v); }
  return { nos: nos.reverse(), segundos: t, metros: m };
}

/* rota mais rápida e rota que evita relatos; `relatos` é Map célula fina -> quantidade */
export async function rotear(a, b, modo, relatos) {
  await carregarGrafo();
  const bit = MODOS[modo].bit, na = ancorar(a, bit), nb = ancorar(b, bit);
  if (na < 0 || nb < 0) return { erro: 'longe' };
  const rapida = menor(na, nb, modo), segura = rapida && menor(na, nb, modo, pesos(relatos));
  if (!rapida) return { erro: 'sem-caminho' };
  const pontos = r => r.nos.map(i => [G.lat[i], G.lng[i]]);
  for (const r of [rapida, segura]) r.pontos = pontos(r);
  return { rapida, segura, igual: segura.nos.join() === rapida.nos.join() };
}
