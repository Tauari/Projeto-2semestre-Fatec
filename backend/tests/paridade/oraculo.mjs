/* Oráculo de paridade: roda as funções ORIGINAIS de src/app.js no Node, para comparar com o porte em Python.
   O código não é redigitado: cada declaração é recortada do arquivo original pelo nome (casando chaves,
   parênteses, strings e regex) e avaliada num contexto vm com os BAIRROS montados como na linha 107.
   Entrada (stdin): JSON com uma lista de pedidos {fn, args, bairros?}. Saída (stdout): lista de {ok} ou {erro}. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';

const AQUI = path.dirname(fileURLToPath(import.meta.url));
const RAIZ = path.resolve(AQUI, '..', '..', '..');
const FONTE = readFileSync(path.join(RAIZ, 'src', 'app.js'), 'utf8');
const DADOS = JSON.parse(readFileSync(path.join(RAIZ, 'dados', 'data.json'), 'utf8'));

/* ------------------------------------------------------------------ recorte do código original */
const ANTES_DE_REGEX = new Set(['return', 'typeof', 'instanceof', 'in', 'of', 'new', 'delete', 'void', 'throw', 'case', 'do', 'else', 'yield', 'await']);

function fimString(src, i) {
  const q = src[i];
  let j = i + 1;
  while (j < src.length && src[j] !== q) {
    if (src[j] === '\\') j += 2;
    else if (src[j] === '\n') throw new Error('string sem fim na posição ' + i);
    else j++;
  }
  return j + 1;
}

function fimRegex(src, i) {
  let j = i + 1, classe = false;
  for (;;) {
    const c = src[j];
    if (c === undefined || c === '\n') throw new Error('regex sem fim na posição ' + i);
    if (c === '\\') { j += 2; continue; }
    if (classe) { if (c === ']') classe = false; }
    else if (c === '[') classe = true;
    else if (c === '/') break;
    j++;
  }
  const corpo = src.slice(i + 1, j);
  j++;
  let k = j;
  while (k < src.length && /[a-z]/.test(src[k])) k++;
  return { fim: k, source: corpo, flags: src.slice(j, k) };
}

function fimTemplate(src, i, regexes) {
  let j = i + 1;
  while (j < src.length && src[j] !== '`') {
    if (src[j] === '\\') j += 2;
    else if (src[j] === '$' && src[j + 1] === '{') j = varrer(src, j + 2, 'template', regexes);
    else j++;
  }
  return j + 1;
}

/* modo 'instrucao': vai até o ';' de nível 0; 'bloco': até fechar a primeira chave de nível 0;
   'template': até o '}' que fecha um ${...} */
function varrer(src, ini, modo, regexes) {
  let prof = 0, i = ini, regexOk = true;
  while (i < src.length) {
    const c = src[i], d = src[i + 1];
    if (c === '/' && d === '/') { const f = src.indexOf('\n', i); i = f < 0 ? src.length : f; continue; }
    if (c === '/' && d === '*') { const f = src.indexOf('*/', i + 2); if (f < 0) throw new Error('comentário sem fim'); i = f + 2; continue; }
    if (/\s/.test(c)) { i++; continue; }
    if (c === '"' || c === "'") { i = fimString(src, i); regexOk = false; continue; }
    if (c === '`') { i = fimTemplate(src, i, regexes); regexOk = false; continue; }
    if (c === '/') {
      if (regexOk) { const r = fimRegex(src, i); if (regexes) regexes.push({ source: r.source, flags: r.flags }); i = r.fim; regexOk = false; }
      else { i++; regexOk = true; }
      continue;
    }
    if (/[A-Za-z0-9_$]/.test(c)) {
      let j = i; while (j < src.length && /[A-Za-z0-9_$]/.test(src[j])) j++;
      regexOk = ANTES_DE_REGEX.has(src.slice(i, j));
      i = j; continue;
    }
    if (c === '(' || c === '[' || c === '{') { prof++; regexOk = true; i++; continue; }
    if (c === ')' || c === ']' || c === '}') {
      if (modo === 'template' && c === '}' && prof === 0) return i + 1;
      prof--;
      if (prof < 0) throw new Error('fechamento sem abertura na posição ' + i);
      i++;
      if (modo === 'bloco' && c === '}' && prof === 0) return i;
      regexOk = c === '}';
      continue;
    }
    if (modo === 'instrucao' && c === ';' && prof === 0) return i + 1;
    regexOk = true; i++;
  }
  throw new Error('fim do arquivo antes do fim da declaração');
}

const escRegExp = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const RECORTES = new Map();
function recortar(decl) {
  if (RECORTES.has(decl)) return RECORTES.get(decl);
  const re = new RegExp('(^|[\\s;{}])(' + escRegExp(decl).replace(/ /g, '\\s+') + ')(?![\\w$])', 'g');
  const achados = [...FONTE.matchAll(re)];
  if (achados.length !== 1) throw new Error(`"${decl}" aparece ${achados.length} vezes em src/app.js (esperado: 1)`);
  const ini = achados[0].index + achados[0][1].length;
  const modo = /^(async\s+)?function\b/.test(decl) ? 'bloco' : 'instrucao';
  const regexes = [];
  const fim = varrer(FONTE, ini, modo, regexes);
  const r = { fonte: FONTE.slice(ini, fim), regexes, linha: FONTE.slice(0, ini).split('\n').length };
  RECORTES.set(decl, r);
  return r;
}

/* ordem igual à do arquivo original */
const DECLARACOES = [
  'const norm', 'const escRe',
  'const TIPOS', 'const TIPO', 'const PERIODOS', 'const PER', 'const QUANDO', 'const periodOfHour',
  'const BAIRROS', 'const BYNAME', 'const LANDMARKS', 'function findBairroInText', 'function matchBairro',
  'function scrub', 'function heuristic', 'async function aiExtract'
];

/* ------------------------------------------------------------------ execução no contexto isolado */
const DESPACHO = `
function __semBairro(r) { return r && Object.assign({}, r, { bairro: r.bairro ? r.bairro.nome : null }); }
function __chatFalso(json) { return { sample: { json }, setAI() {} }; }
globalThis.__executar = async function (entradaJson, indicesJson) {
  // o JSON original é lido aqui dentro, sem reserializar (Infinity, -0 etc. chegam como o JSON.parse daria)
  const todos = JSON.parse(entradaJson), saida = [];
  for (const i of JSON.parse(indicesJson)) {
    const p = todos[i];
    const a = p.args || [];
    try {
      let v;
      switch (p.fn) {
        case 'norm': v = norm(a[0]); break;
        case 'normFaixa': v = []; for (let cp = a[0]; cp < a[1]; cp++) v.push(norm(String.fromCodePoint(cp))); break;
        case 'escRe': v = escRe(a[0]); break;
        case 'scrub': v = scrub(a[0]); break;
        case 'scrub2': v = scrub(scrub(a[0]).text); break;
        case 'heuristic': v = __semBairro(heuristic(a[0])); break;
        case 'findBairroInText': { const b = findBairroInText(a[0]); v = b ? b.nome : null; break; }
        case 'matchBairro': { const b = matchBairro(a[0]); v = b ? b.nome : null; break; }
        case 'periodOfHour': v = periodOfHour(a[0]); break;
        case 'aiPrompt': { let capturado = null; await aiExtract(a[0], __chatFalso(async prompt => { capturado = prompt; return null; })); v = capturado; break; }
        case 'aiSaida': v = __semBairro(await aiExtract('', __chatFalso(async () => a[0]))); break;
        case 'vocabulario': v = {
          tipos: TIPOS.map(t => ({ id: t.id, label: t.label, long: t.long === undefined ? null : t.long, kw: t.kw ? { source: t.kw.source, flags: t.kw.flags } : null })),
          periodos: PERIODOS, quando: QUANDO, tipoIds: Object.keys(TIPO), perIds: Object.keys(PER)
        }; break;
        case 'bairros': v = BAIRROS; break;
        case 'landmarks': v = LANDMARKS.map(([re, nome]) => [re.source, re.flags, nome]); break;
        default: throw new Error('função desconhecida: ' + p.fn);
      }
      saida.push({ ok: v === undefined ? null : v });
    } catch (e) { saida.push({ erro: String(e && e.stack || e) }); }
  }
  return JSON.stringify(saida);
};`;

const CONTEXTOS = new Map();
function contexto(bairros) {
  const chave = JSON.stringify(bairros);
  if (CONTEXTOS.has(chave)) return CONTEXTOS.get(chave);
  const codigo = ["'use strict';", 'const D = ' + JSON.stringify({ bairros }) + ';', 'function toast() {}']
    .concat(DECLARACOES.map(d => recortar(d).fonte), DESPACHO).join('\n');
  const ctx = vm.createContext({});
  vm.runInContext(codigo, ctx, { filename: 'app.js-recortado.js' });
  CONTEXTOS.set(chave, ctx);
  return ctx;
}

/* funções do próprio JS (não do app.js), usadas para conferir fatiar_js, aparar_js e regex_js */
function nativo(fn, a) {
  switch (fn) {
    case 'slice': return String(a[0]).slice(0, a[1]);
    case 'trim': return String(a[0]).trim();
    case 'length': return String(a[0]).length;
    case 'espacos': {
      const s = [], trim = [];
      for (let c = 0; c < 0x10000; c++) { const ch = String.fromCharCode(c); if (/\s/.test(ch)) s.push(c); if (ch.trim() === '') trim.push(c); }
      return { s, trim };
    }
    case 'regexConjunto': {
      const re = new RegExp(a[0], a[1] || ''), out = [];
      for (let c = 0; c < 0x10000; c++) if (re.test(String.fromCharCode(c))) out.push(c);
      return out;
    }
    case 'regexTeste': return a[2].map(s => new RegExp(a[0], a[1] || '').test(s));
    case 'recorte': { const r = recortar(a[0]); return { fonte: r.fonte, regexes: r.regexes, linha: r.linha }; }
    case 'regexes': return recortar(a[0]).regexes;
    default: return undefined;
  }
}
const NATIVAS = new Set(['slice', 'trim', 'length', 'espacos', 'regexConjunto', 'regexTeste', 'recorte', 'regexes']);

async function main() {
  const partes = [];
  for await (const b of process.stdin) partes.push(b);
  const entrada = Buffer.concat(partes).toString('utf8');
  const pedidos = JSON.parse(entrada);
  const resultados = new Array(pedidos.length);
  // agrupa por lista de bairros para rodar cada grupo de uma vez no seu contexto
  const grupos = new Map();
  pedidos.forEach((p, i) => {
    if (NATIVAS.has(p.fn)) {
      try { const v = nativo(p.fn, p.args || []); resultados[i] = { ok: v === undefined ? null : v }; }
      catch (e) { resultados[i] = { erro: String(e && e.stack || e) }; }
      return;
    }
    const bairros = p.bairros || DADOS.bairros;
    const chave = JSON.stringify(bairros);
    if (!grupos.has(chave)) grupos.set(chave, { bairros, itens: [] });
    grupos.get(chave).itens.push(i);
  });
  for (const { bairros, itens } of grupos.values()) {
    const ctx = contexto(bairros);
    const json = await ctx.__executar(entrada, JSON.stringify(itens));
    JSON.parse(json).forEach((r, k) => { resultados[itens[k]] = r; });
  }
  process.stdout.write(JSON.stringify(resultados));
}

main().catch(e => { process.stderr.write(String(e && e.stack || e) + '\n'); process.exitCode = 1; });
