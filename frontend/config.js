/* configuração do frontend: endereço da API e valores que o servidor pode ajustar */
const meta = document.querySelector('meta[name="aurora-api"]');
export const CONFIG = {
  apiBase: (meta && meta.content) || '/api/v1',
  janelaDias: 30,                 // relatos visíveis no mapa (vem de /config quando há servidor)
  tiposMax: 4,                    // tipos por relato
  textoMax: 300,                  // caracteres da descrição publicada
  precisaoCriado: 'exata',        // como o servidor arredonda a hora de envio: exata, hora ou dia
  atualizarRelatosSeg: 60,        // releitura periódica dos relatos no modo api
  estatico: { dados: '../dados/data.json', apoio: '../dados/rede-de-apoio.json', mapaBase: '../dados/osm/basemap.json' },
  ia: { provedor: 'heuristica', usaModelo: false }
};
export function aplicarConfigServidor(cfg) {
  if (!cfg || typeof cfg !== 'object') return;
  const jd = cfg.relatos && cfg.relatos.janela_dias;
  if (typeof jd === 'number' && jd > 0) CONFIG.janelaDias = jd;
  const rl = cfg.relatos || {};
  if (typeof rl.tipos_max === 'number' && rl.tipos_max > 0) CONFIG.tiposMax = rl.tipos_max;
  if (typeof rl.texto_max === 'number' && rl.texto_max >= 0) CONFIG.textoMax = rl.texto_max;
  if (['exata', 'hora', 'dia'].includes(rl.precisao_criado)) CONFIG.precisaoCriado = rl.precisao_criado;
  if (cfg.ia && typeof cfg.ia === 'object') CONFIG.ia = { provedor: String(cfg.ia.provedor || CONFIG.ia.provedor), usaModelo: cfg.ia.usa_modelo === true };
}
/* "30 dias" nos textos acompanha a janela configurada no servidor */
export const janelaTxt = () => CONFIG.janelaDias === 1 ? '1 dia' : CONFIG.janelaDias + ' dias';
/* quanto a hora de envio pode estar arredondada para baixo no servidor */
export const margemCriadoMs = () => ({ hora: 36e5, dia: 864e5 })[CONFIG.precisaoCriado] || 0;
