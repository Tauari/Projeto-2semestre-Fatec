/* dados do mapa: do servidor da Aurora (modo api) ou dos arquivos de dados/ (modo estatico) */
import { CONFIG, aplicarConfigServidor } from '../config.js';
import { apiGet } from './api.js';

export let D = null, OSM = null, AP = null, MODO_DADOS = null;

async function lerJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error('HTTP ' + r.status + ' ao ler ' + url);
  return r.json();
}
/* o mapa de ruas e a rede de apoio podem faltar: o app já funciona sem eles */
const opcional = p => p.catch(() => null);

async function carregarDaApi() {
  const cfg = await apiGet('/config');
  aplicarConfigServidor(cfg);
  const cp = cfg.conjuntos_padrao;
  const [geo, oficial, percepcao, apoio, base] = await Promise.all([
    apiGet('/mapa/geografia'),
    apiGet('/dados-oficiais/' + encodeURIComponent(cp.dado_oficial)),
    apiGet('/percepcao/' + encodeURIComponent(cp.percepcao)),
    opcional(apiGet('/apoio')),
    opcional(apiGet('/mapa/base?v=4'))
  ]);
  return { D: { ...geo.dados, bo: oficial.dados, pesq: percepcao.dados }, AP: apoio ? apoio.dados : null, OSM: base };
}
async function carregarEstatico() {
  const E = CONFIG.estatico;
  const [dados, apoio, base] = await Promise.all([lerJSON(E.dados), opcional(lerJSON(E.apoio)), opcional(lerJSON(E.mapaBase))]);
  return { D: dados, AP: apoio, OSM: base };
}
export async function carregarDados() {
  let saude = null;
  try { saude = await apiGet('/saude'); } catch (e) { /* sem servidor: usa os arquivos */ }
  if (saude && saude.status === 'ok') {
    try {
      const r = await carregarDaApi();
      D = r.D; AP = r.AP; OSM = r.OSM; MODO_DADOS = 'api'; return;
    } catch (e) { console.warn('api:', e && (e.code || e.message)); }
  }
  let r;
  try { r = await carregarEstatico(); } catch (e) { throw new Error('Não foi possível carregar os dados do mapa, nem pelo servidor nem pelos arquivos estáticos.'); }
  D = r.D; AP = r.AP; OSM = r.OSM; MODO_DADOS = 'estatico';
}
