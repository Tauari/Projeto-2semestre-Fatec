/* pedido de rota em linguagem natural: "uma rota da Rua 7 até a Avenida 29 de bicicleta".
   Com modelo, o servidor entende o pedido; sem modelo (ou se falhar), uma regra simples dá conta das frases comuns. */
import { norm, escRe } from '../shared/formato.js';
import { apiPost } from '../shared/api.js';
import { OSM } from '../shared/dados.js';
import { matchBairro, findBairroInText } from '../shared/bairros.js';
import { APOIO } from '../apoio/rede.js';

export const pedeRota = texto => { const t = norm(texto); return /\b(rota|trajeto|caminho|chegar|como (eu )?(vou|chego|ir)|quero ir|preciso ir)\b/.test(t) && /\b(ate|para|pra)\b/.test(t); };

const MODO = [['bike', /\b(bike|bicicleta|pedal\w*|ciclo\w*)\b/], ['carro', /\b(carro|moto|dirigindo|uber|de van)\b/], ['pe', /\b(a pe|caminhando|andando|pe)\b/]];
const modoDe = t => (MODO.find(([, re]) => re.test(t)) || [null])[0];

/* sem modelo: separa "da X até a Y" */
export function rotaLocal(texto) {
  const t = norm(texto).replace(/[?!.]+$/, '').trim(), modo = modoDe(t);
  const corpo = t.replace(/\s+(?:de|na|no|em|com|usando|indo|andando|caminhando|a)\s+(?:bike|bicicleta|carro|moto|pe|a pe)\b.*$/, '').replace(/\s+(?:a pe|caminhando|andando)$/, '');
  const m = corpo.match(/(?:^|\b)(?:d[aeo]s?\s+)?(.+?)\s+(?:ate|para|pra)\s+(?:a |o |as |os )?(.+)$/);
  if (!m) return { origem: null, destino: null, modo };
  const origem = m[1].replace(/^.*\b(?:rota|trajeto|caminho|ir|chegar|chego|vou)\s+(?:d[aeo]s?\s+)?/, '').replace(/^d[aeo]s?\s+/, '').trim();
  return { origem: origem || null, destino: m[2].trim() || null, modo };
}

/* com modelo: o servidor devolve { origem, destino, modo }; qualquer falha cai na regra local */
export async function entenderRota(texto, comModelo) {
  if (comModelo) {
    try {
      const r = await apiPost('/ia/rota', { texto });
      if (r && r.origem && r.destino) return { origem: r.origem, destino: r.destino, modo: r.modo || modoDe(norm(texto)) };
    } catch (e) { /* sem servidor ou sem modelo: usa a regra local */ }
  }
  return rotaLocal(texto);
}

/* endereço escrito livremente ("Rua 4, 123, Cidade Jardim") -> ponto no mapa. Acha a rua pelo nome no mapa de ruas embutido; existem
   várias ruas com o mesmo nome (Rua 4 em vários bairros), então o bairro citado escolhe qual. O número da casa não é usado para
   posicionar: o ponto é o trecho da rua mais perto do bairro (ou o rótulo mais importante dela), não a casa. */
let ruas = null;
const ABREV = [[/\bav\.?\s/g, 'avenida '], [/\br\.?\s/g, 'rua '], [/\brod\.?\s/g, 'rodovia ']];
const limpa = s => ABREV.reduce((t, [re, x]) => t.replace(re, x), norm(s).replace(/[,;.]/g, ' ')).replace(/\s+/g, ' ').trim();
const dist = (p, q) => Math.hypot(p.lat - q.lat, p.lng - q.lng);
/* lugar conhecido ("fatec", "rodoviária", "santa casa"): vale cada palavra do pedido começar uma palavra do nome do lugar.
   Nota 3 = nome inteiro, 2 = começa igual, 1 = só contém; entre empates, o nome mais curto. */
let lugares = null;
const CENTRO = { lat: -22.411, lng: -47.561 };
const DE = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'em', 'na', 'no', 'rio', 'claro']);
const raiz = w => (w.length > 4 ? w.replace(/[aeiosu]+$/, '') : w); // rodoviária = rodoviário
const palavras = s => limpa(s).split(' ').filter(w => w && !DE.has(w));
function indiceLugares() {
  if (!lugares) {
    lugares = [];
    const add = (nome, lat, lng) => lugares.push({ nome, lat, lng, k: palavras(nome) });
    if (OSM) { for (const [n, la, ln] of OSM.poi) add(n, la, ln); for (const [n, la, ln] of OSM.lugares || []) add(n, la, ln); }
    for (const p of APOIO) { add(p.nome, p.lat, p.lng); if (p.curto) add(p.curto, p.lat, p.lng); }
  }
  return lugares;
}
function lugar(texto) {
  const q = palavras(texto); let melhor = null;
  if (!q.length) return null;
  for (const l of indiceLugares()) {
    if (!l.k.length || !q.every(w => l.k.some(x => raiz(x).startsWith(raiz(w))))) continue;
    const nota = (l.k.join(' ') === q.join(' ') ? 3 : raiz(l.k[0]).startsWith(raiz(q[0])) ? 2 : 1) - l.k.length * 0.01 - dist(l, CENTRO) * 0.3; // empate: nome mais curto e mais perto do centro
    if (!melhor || nota > melhor.nota) melhor = { nota, lat: l.lat, lng: l.lng, nome: l.nome, curto: l.k.join(' ') };
  }
  return melhor;
}
export function geocodificar(texto) {
  const l = lugar(texto);
  if (l && l.nota >= 2.9) return { lat: l.lat, lng: l.lng, nome: l.nome };
  return ruaOuBairro(texto, !!l) || (l && { lat: l.lat, lng: l.lng, nome: l.nome }); // com um lugar parecido, não cai no bairro "mais ou menos igual"
}
function ruaOuBairro(texto, temLugar) {
  if (!ruas) {
    ruas = new Map();
    if (OSM) for (const [ni, lat, lng, , tier] of OSM.streetLabels) { const k = limpa(OSM.streetNames[ni]); (ruas.get(k) || ruas.set(k, []).get(k)).push({ lat, lng, tier }); }
    ruas.nomes = [...ruas.keys()].sort((a, b) => b.length - a.length); // o nome mais longo primeiro: "rua 4 jn" antes de "rua 4"
  }
  const t = ' ' + limpa(texto) + ' ', bairro = findBairroInText(texto), rua = ruas.nomes.find(n => t.includes(' ' + n + ' '));
  if (rua) {
    const c = ruas.get(rua), p = c.reduce((a, b) => (bairro ? dist(b, bairro) < dist(a, bairro) : b.tier < a.tier) ? b : a);
    return { lat: p.lat, lng: p.lng, nome: texto };
  }
  const b = bairro || (temLugar ? null : matchBairro(texto));
  return b ? { lat: b.lat, lng: b.lng, nome: texto } : null;
}

/* ------------------------------------------------------------------ relato por extenso: de onde é?
   Acha no texto (e no que o modelo apontou) cruzamentos, lugares conhecidos, ruas e bairros, e devolve o melhor ponto para o mapa
   mostrar e a pessoa confirmar. O ponto só serve para marcar a região (~150 m); a rua e o ponto de referência não são guardados. */
let cruz = null;
function indiceRuas() {
  if (cruz) return cruz;
  cruz = { nomes: new Map(), pares: new Map(), porRua: new Map(), variantes: new Map(), chaves: [] };
  const c = OSM && OSM.cruzamentos; if (!c) return cruz;
  const k = c.nomes.map(limpa), add = (m, chave, p) => (m.get(chave) || m.set(chave, []).get(chave)).push(p);
  c.nomes.forEach((n, i) => cruz.nomes.set(k[i], n));
  // o OpenStreetMap escreve "Rua 3 JN", "Rua 3 CJ"...: o código é o bairro. Quem diz só "rua 3" pode estar em qualquer uma
  c.nomes.forEach((n, i) => {
    const m = k[i].match(/^(.+\d)\s+[a-z]{1,6}$/); if (!m) return;
    (cruz.variantes.get(m[1]) || cruz.variantes.set(m[1], []).get(m[1])).push(k[i]);
    if (!cruz.nomes.has(m[1])) cruz.nomes.set(m[1], n.replace(/\s+\S+$/, ''));
  });
  for (const [i, j, lat, lng] of c.pontos) {
    const p = { lat, lng };
    add(cruz.pares, k[i] + '|' + k[j], p); add(cruz.pares, k[j] + '|' + k[i], p); add(cruz.porRua, k[i], p); add(cruz.porRua, k[j], p);
  }
  cruz.chaves = [...cruz.nomes.keys()].sort((a, b) => b.length - a.length); // nome mais longo primeiro: "rua 5 jn" antes de "rua 5"
  return cruz;
}
/* ruas citadas: as que o modelo apontou e as que aparecem no texto (na ordem em que aparecem) */
function ruasCitadas(texto, daIA = []) {
  const ix = indiceRuas(), out = [], vistos = new Set();
  const poe = chave => { if (ix.nomes.has(chave) && !vistos.has(chave)) { vistos.add(chave); out.push({ chave, nome: ix.nomes.get(chave) }); } };
  for (const x of daIA) poe(limpa(x));
  let t = ' ' + limpa(texto) + ' '; const achadas = [];
  for (const chave of ix.chaves) {
    const i = t.indexOf(' ' + chave + ' ');
    if (i >= 0) { achadas.push([i, chave]); t = t.slice(0, i) + ' '.repeat(chave.length + 2) + t.slice(i + chave.length + 2); }
  }
  for (const [, chave] of achadas.sort((a, b) => a[0] - b[0])) poe(chave);
  return out;
}
const GENERICAS = new Set(['praca', 'igreja', 'escola', 'hospital', 'farmacia', 'banco', 'padaria', 'mercado', 'restaurante', 'posto', 'clinica', 'centro', 'parque',
  'hotel', 'lanchonete', 'supermercado', 'academia', 'creche', 'capela', 'cemiterio', 'ponto', 'terminal', 'estacao', 'quadra', 'campo']);
/* lugares conhecidos citados: os que o modelo apontou e os cujo nome inteiro aparece no texto ("na frente da fatec") */
function pontosCitados(texto, daIA = []) {
  const out = [], vistos = new Set(), poe = p => { if (p && !vistos.has(p.nome)) { vistos.add(p.nome); out.push(p); } };
  for (const x of daIA) poe(lugar(x));
  const w = new Set(palavras(texto).map(raiz)); let melhor = null;
  for (const l of indiceLugares()) {
    if (!l.k.length || !l.k.every(x => w.has(raiz(x)))) continue;
    if (l.k.length === 1 && (l.k[0].length < 5 || GENERICAS.has(l.k[0]))) continue;
    const nota = l.k.length - dist(l, CENTRO) * 0.3;
    if (!melhor || nota > melhor.nota) melhor = { nota, lat: l.lat, lng: l.lng, nome: l.nome, curto: l.k.join(' ') };
  }
  poe(melhor);
  return out;
}
const perto = (pts, ref) => pts.reduce((a, b) => (dist(b, ref || CENTRO) < dist(a, ref || CENTRO) ? b : a));
/* { cand: { lat, lng, nome, como } | null, termos: [o que sai da descrição] }; como = cruzamento | lugar | rua | bairro */
export function achaLocal(texto, ia = {}) {
  const ix = indiceRuas(), ruas = ruasCitadas(texto, ia.ruas), pontos = pontosCitados(texto, ia.pontos), ref = pontos[0];
  const termos = [...ruas.map(r => r.nome), ...pontos.flatMap(p => [p.nome, p.curto]), ...(ia.ruas || []), ...(ia.pontos || [])].filter(Boolean);
  for (let i = 0; i < ruas.length; i++) for (let j = i + 1; j < ruas.length; j++) {
    const com = ch => [ch, ...(ix.variantes.get(ch) || [])], pts = [];
    for (const a of com(ruas[i].chave)) for (const b of com(ruas[j].chave)) pts.push(...(ix.pares.get(a + '|' + b) || []));
    if (pts.length) return { cand: { ...perto(pts, ref), como: 'cruzamento', nome: ruas[i].nome + ' com ' + ruas[j].nome }, termos };
  }
  if (ref) return { cand: { lat: ref.lat, lng: ref.lng, nome: ref.nome, como: 'lugar' }, termos };
  const daRua = ruas.length && [ruas[0].chave, ...(ix.variantes.get(ruas[0].chave) || [])].flatMap(ch => ix.porRua.get(ch) || []);
  if (daRua && daRua.length) return { cand: { ...perto(daRua, ref), como: 'rua', nome: ruas[0].nome }, termos };
  const b = findBairroInText(texto);
  return { cand: b ? { lat: b.lat, lng: b.lng, nome: b.nome, como: 'bairro' } : null, termos };
}
/* tira da descrição o que diz onde foi (rua, avenida, ponto de referência) e as palavras que ligam ("na", "na frente da", "esquina com") */
export function semLocal(texto, termos) {
  const n = norm(texto), spans = [];
  for (const termo of new Set(termos.map(norm).filter(t => t.length > 2))) {
    const re = new RegExp('(^|[^a-z0-9])(' + escRe(termo).replace(/ /g, '\\s+').replace(/\bavenida\b/g, '(?:avenida|av\\.?)').replace(/\brua\b/g, '(?:rua|r\\.?)') + ')(?![a-z0-9])', 'g');
    for (let m; (m = re.exec(n));) spans.push([m.index + m[1].length, m.index + m[1].length + m[2].length]);
  }
  if (!spans.length) return texto;
  const juntos = [];
  for (const s of spans.sort((x, y) => x[0] - y[0])) { const u = juntos[juntos.length - 1]; if (u && s[0] <= u[1]) u[1] = Math.max(u[1], s[1]); else juntos.push([...s]); }
  let t = texto;
  for (const [a, b] of juntos.reverse()) t = t.slice(0, a) + '\u0001' + t.slice(b);
  const lig = '(?:\\s*(?:\\b(?:na|no|em|perto|pertinho|na frente|em frente|esquina|cruzamento|com|e|da|do|de|das|dos|a|ao|à|que fica)\\b)\\s*)*';
  return t.replace(new RegExp(lig + '\\u0001(?:' + lig + '\\u0001)*', 'gi'), ' ').replace(/\s+([,.;!?])/g, '$1').replace(/([,;])\s*([,.;])/g, '$2').replace(/\s{2,}/g, ' ').trim();
}
