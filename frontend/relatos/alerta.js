/* alerta padronizado de um relato, como o aviso do Waze ("Acidente na rodovia"): um título fixo por tipo de situação.
   Os mesmos títulos estão em backend/services/alertas.py (um teste confere que os dois batem). */
import { CONFIG } from '../config.js';
import { recentReports } from './relatos.js';

export const ROTULOS = {
  assedio: 'Potencial assediador na área',
  perseguicao: 'Possível perseguidor na área',
  abordagem: 'Abordagem indesejada na área',
  intimidacao: 'Intimidação relatada na área',
  exposicao: 'Exposição sexual relatada na área',
  roubo: 'Roubo ou furto na área',
  violencia: 'Violência física relatada na área',
  veiculo: 'Situação com veículo na área',
  ambiente: 'Rua escura ou deserta na área',
  outra: 'Situação relatada na área'
};
/* se o relato tem mais de um tipo, o título vem do mais grave primeiro */
export const PRIORIDADE = ['violencia', 'exposicao', 'perseguicao', 'assedio', 'abordagem', 'intimidacao', 'roubo', 'veiculo', 'ambiente', 'outra'];
/* "rua escura ou deserta" é uma condição do lugar, não algo acontecendo agora: não vira alerta ao vivo */
export const SEM_ALERTA = new Set(['ambiente']);

export const tipoDoAlerta = tipos => PRIORIDADE.find(t => tipos.includes(t) && !SEM_ALERTA.has(t)) || null;
export const tituloAlerta = tipos => { const t = tipoDoAlerta(tipos); return t ? ROTULOS[t] : null; };

/* relatos que valem como alerta ao vivo: recentes (CONFIG.alertasAoVivoHoras) e de um tipo que gera alerta; o mais novo primeiro */
export function alertasAoVivo(reps = recentReports()) {
  const lim = Date.now() - CONFIG.alertasAoVivoHoras * 36e5;
  return reps.filter(r => r.criado >= lim && tipoDoAlerta(r.tipos)).sort((a, b) => b.criado - a.criado);
}
export function haQuanto(ts) {
  const min = Math.max(0, Math.floor((Date.now() - ts) / 6e4));
  return min < 1 ? 'agora' : min < 60 ? 'há ' + min + ' min' : 'há ' + Math.floor(min / 60) + ' h';
}
