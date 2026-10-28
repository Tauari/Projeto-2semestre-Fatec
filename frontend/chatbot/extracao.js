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
  const rel = tempoRelativo(text); if (rel) { quando = rel.quando; periodo = rel.periodo; }
  const sc = scrub(text);
  const urgente = /(estou|to|estamos) (sendo seguid|em perigo|com medo agora)|socorro|me ajud(a|em) agora|agora mesmo/.test(t);
  return { urgente, tipos, bairro: findBairroInText(text), quando, periodo, descricao: sc.text.slice(0, 300), removidos: sc.removed, resposta: '', fromAI: false };
}

/* "há 30 minutos", "faz 2 horas", "há meia hora": quem calcula é o relógio, não o modelo (que erra a conta) */
const NUM = { um: 1, uma: 1, dois: 2, duas: 2, meia: 0.5 };
export function tempoRelativo(text, agora = new Date()) {
  const m = norm(text).match(/\b(?:ha|faz|fazem)\s+(?:uns\s+|umas\s+|cerca de\s+)?(\d{1,3}|um|uma|dois|duas|meia)\s*(min(?:uto)?s?|h(?:ora)?s?)\b/);
  if (!m) return null;
  const n = Object.hasOwn(NUM, m[1]) ? NUM[m[1]] : +m[1], min = m[2][0] === 'm' ? n : n * 60;
  if (!(min >= 0 && min <= 24 * 60)) return null;
  const quando = new Date(agora.getTime() - min * 60000);
  return { quando: quando.getDate() === agora.getDate() ? 'hoje' : 'ontem', periodo: periodOfHour(quando.getHours()) };
}

/* o modelo pequeno às vezes inventa o horário: só vale se o texto der alguma pista, e "de noite" sem hora não é madrugada nem tarde */
export function periodoCoerente(text, periodo) {
  if (!periodo) return null;
  const n = norm(text);
  const hora = /\b\d{1,2}\s?(?:h\b|hs\b|horas|:\d{2})|meia[- ]?noite|madrugada|\bmanha\b|\btarde\b|\bnoite\b|\bha\s+\S+\s+(?:min|hora)/.test(n);
  if (!hora) return null;
  if (/\bnoite\b/.test(n) && !/\b\d{1,2}\s?(?:h\b|hs\b|horas|:\d{2})|madrugada|manha|tarde/.test(n) && !['18-20', '20-22', '22-00'].includes(periodo)) return null;
  return periodo;
}

/* provedor de IA em uso (vem de /config quando há servidor) */
export function infoProvedorIA() { return CONFIG.ia; }

/* onde foi e o que é dado pessoal, pelo servidor (/ia/local). Só com modelo; em qualquer erro volta null e o chat usa as regras locais */
export async function localNoServidor(text) {
  try {
    const r = await apiPost('/ia/local', { texto: text });
    const lista = v => (Array.isArray(v) ? v.filter(x => typeof x === 'string' && x.trim()).map(x => x.trim()) : []);
    return { ruas: lista(r.ruas), pontos: lista(r.pontos), referencia: typeof r.referencia === 'string' ? r.referencia : null,
      sensiveis: lista(r.sensiveis), descricao: typeof r.descricao === 'string' ? r.descricao.trim() : '' };
  } catch (e) {
    return null;
  }
}

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
