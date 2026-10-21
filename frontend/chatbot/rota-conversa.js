/* pedido de rota em linguagem natural: "uma rota da Rua 7 até a Avenida 29 de bicicleta".
   Com modelo, o servidor entende o pedido; sem modelo (ou se falhar), uma regra simples dá conta das frases comuns. */
import { norm } from '../shared/formato.js';
import { apiPost } from '../shared/api.js';
import { OSM } from '../shared/dados.js';
import { matchBairro, findBairroInText } from '../shared/bairros.js';

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
export function geocodificar(texto) {
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
  const b = bairro || matchBairro(texto);
  return b ? { lat: b.lat, lng: b.lng, nome: texto } : null;
}
