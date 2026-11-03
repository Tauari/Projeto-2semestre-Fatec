/* Roupas e acessórios que aparecem no alerta ("Visto com: camiseta preta, calça roxa").
   Só sai o que casa com as listas abaixo (peça de roupa ou acessório, com cor ou material): nome, altura, cor da pele, cabelo,
   tatuagem, idade, placa e qualquer outro dado pessoal ou característica física nunca passam por aqui, mesmo que estejam no texto. */
import { norm } from '../shared/formato.js';

/* escritos sem acento: o texto é comparado sem acento e sem maiúsculas */
const ROUPAS = ['camiseta', 'camisa', 'camisao', 'blusa', 'blusao', 'regata', 'moletom', 'jaqueta', 'casaco', 'colete', 'agasalho', 'uniforme',
  'calca', 'bermuda', 'short', 'shorts', 'calcao', 'tenis', 'sapato', 'chinelo', 'bota', 'sandalia'];
const ACESSORIOS = ['bone', 'boina', 'chapeu', 'touca', 'gorro', 'capuz', 'oculos', 'mascara', 'capacete', 'mochila', 'bolsa', 'pochete', 'luvas',
  'cachecol', 'bandana', 'lenco', 'corrente', 'pulseira', 'relogio'];
const CORES = ['preto', 'preta', 'pretos', 'pretas', 'branco', 'branca', 'brancos', 'brancas', 'azul', 'azuis', 'verde', 'verdes', 'vermelho', 'vermelha',
  'amarelo', 'amarela', 'roxo', 'roxa', 'rosa', 'laranja', 'cinza', 'marrom', 'bege', 'vinho', 'lilas', 'dourado', 'dourada', 'prata', 'prateado',
  'prateada', 'jeans', 'listrado', 'listrada', 'xadrez', 'estampado', 'estampada', 'colorido', 'colorida', 'escuro', 'escura', 'escuros', 'escuras',
  'claro', 'clara', 'neon'];
const MAX = 5;

const alt = lista => lista.join('|');
const COM_COR = new RegExp('\\b(' + alt(ROUPAS.concat(ACESSORIOS)) + ')\\s+(?:(?:de|na|da)\\s+)?(?:cor\\s+)?(' + alt(CORES) + ')\\b', 'g');
const ITEM = alt(ACESSORIOS);
/* acessório sem cor, em lista ("de capacete e mochila"): só depois de "de", "com", "usando"... */
const LISTA = new RegExp('\\b(?:de|com|usando|vestindo|portando)\\s+((?:' + ITEM + ')(?:\\s*(?:,|\\be\\b)\\s*(?:' + ITEM + '))*)\\b', 'g');
const UM_ITEM = new RegExp('\\b(' + ITEM + ')\\b', 'g');
const NEGADO = /\b(sem|nao)\b/;

/** ['camiseta preta', 'calça roxa']: só roupas e acessórios citados no texto, na ordem em que aparecem. */
export function acessorios(texto) {
  const t = String(texto || '').normalize('NFC'), n = norm(t);
  const fonte = n.length === t.length ? t : n; // com o texto original saem os acentos ("calça", "boné")
  const achados = [], vistos = new Set(), comCor = new Set();
  const negado = i => NEGADO.test(n.slice(Math.max(0, i - 16), i));
  for (const m of n.matchAll(COM_COR)) {
    if (negado(m.index)) continue;
    comCor.add(m[1]);
    achados.push([m.index, fonte.slice(m.index, m.index + m[0].length).replace(/\s+/g, ' ')]);
  }
  for (const m of n.matchAll(LISTA)) {
    if (negado(m.index)) continue;
    const base = m.index + m[0].length - m[1].length;
    for (const it of m[1].matchAll(UM_ITEM)) {
      if (comCor.has(it[1])) continue;
      achados.push([base + it.index, fonte.slice(base + it.index, base + it.index + it[1].length)]);
    }
  }
  return achados.sort((a, b) => a[0] - b[0]).map(a => a[1]).filter(f => { const k = norm(f); if (vistos.has(k)) return false; vistos.add(k); return true; }).slice(0, MAX);
}
export const detalheAcessorios = texto => acessorios(texto).join(', ');
