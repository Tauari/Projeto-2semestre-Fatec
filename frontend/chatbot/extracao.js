import { CONFIG } from '../config.js';
import { norm } from '../shared/formato.js';
import { TIPOS, TIPO, PER, QUANDO, periodOfHour } from '../shared/vocabulario.js';
import { scrub } from '../shared/anonimizacao.js';
import { apiPost } from '../shared/api.js';
import { BYNAME, findBairroInText, matchBairro } from '../shared/bairros.js';

/* extração de campos sem IA (palavras-chave) */
export function heuristic(text) {
  const t = norm(text);
  const tipos = TIPOS.filter(x => x.kw && x.kw.test(t)).map(x => x.id).slice(0, 3);
  let quando = null;
  if (/\bhoje\b|agora ha pouco|agorinha|agora pouco/.test(t)) quando = 'hoje';
  else if (/\bontem\b/.test(t)) quando = 'ontem';
  else if (/semana passada|mes passado|\bmeses\b|faz tempo|ano passado|ha \d+ semanas/.test(t)) quando = 'antes';
  else if (/(essa|esta|nesta) semana|anteontem|segunda|terca|quarta|quinta|sexta|sabado|domingo/.test(t)) quando = 'semana';
  let periodo = null;
  const hm = t.match(/\b(\d{1,2})\s?(?:h\b|hs\b|horas|:\d{2}|da (noite|manha|tarde))/);
  if (hm) { let hr = +hm[1]; if ((hm[2] === 'noite' || hm[2] === 'tarde' || /\bnoite\b/.test(t)) && hr < 12 && hr >= 1) hr += 12; if (hr === 24) hr = 0; if (hr >= 0 && hr < 24) periodo = periodOfHour(hr); }
  if (!periodo) { if (/madrugada/.test(t)) periodo = 'madrugada'; else if (/meia[- ]?noite/.test(t)) periodo = '22-00'; else if (/de manha|pela manha|\bmanha\b/.test(t)) periodo = 'manha'; else if (/a tarde|de tarde|\btarde\b/.test(t)) periodo = 'tarde'; }
  const sc = scrub(text);
  const urgente = /(estou|to|estamos) (sendo seguid|em perigo|com medo agora)|socorro|me ajud(a|em) agora|agora mesmo/.test(t);
  return { urgente, tipos, bairro: findBairroInText(text), quando, periodo, descricao: sc.text.slice(0, 300), removidos: sc.removed, resposta: '', fromAI: false };
}

/* provedor de IA em uso (vem de /config quando há servidor) */
export function infoProvedorIA() { return CONFIG.ia; }

/* extração pelo servidor (/ia/extrair; o texto não é guardado lá). Em qualquer erro volta null e o chat segue com a heurística local */
export async function extrairNoServidor(text) {
  try {
    const o = await apiPost('/ia/extrair', { texto: text });
    const r = o && o.resultado;
    if (!r || typeof r !== 'object') return null;
    const nome = r.bairro && typeof r.bairro.nome === 'string' ? r.bairro.nome : null;
    return {
      urgente: r.urgente === true,
      tipos: Array.isArray(r.tipos) ? r.tipos.map(String).filter(t => Object.hasOwn(TIPO, t)).slice(0, 3) : [],
      bairro: nome ? (Object.hasOwn(BYNAME, nome) && BYNAME[nome]) || matchBairro(nome) || null : null,
      quando: Object.hasOwn(QUANDO, r.quando) ? r.quando : null,
      periodo: Object.hasOwn(PER, r.periodo) ? r.periodo : null,
      descricao: typeof r.descricao === 'string' ? r.descricao : '',
      removidos: Array.isArray(r.removidos) ? r.removidos.map(String) : [],
      resposta: typeof r.resposta === 'string' ? r.resposta : '',
      fromAI: o.usa_modelo === true
    };
  } catch (e) {
    return null;
  }
}
