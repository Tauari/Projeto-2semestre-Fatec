/* "Padrões nos dados" (US-02): o que os dados mostram por região, período e tipo de ocorrência, com a evidência de cada achado,
   o que não deu para analisar e o aviso de que isso descreve o passado e não prevê nada. Vem de GET /analise/padroes. */
import { $, esc } from '../shared/dom.js';
import { apiGet } from '../shared/api.js';
import { focusCell } from '../mapa/lista-areas.js';

const DIM = { regiao: 'Região', periodo: 'Período', tipo: 'Tipo' };
const CONF = { alta: 'Confiança alta', media: 'Confiança média', baixa: 'Confiança baixa: poucos casos' };
const GRUPOS = [['relatos', 'Relatos da comunidade'], ['historico', 'Histórico de B.O.'], ['percepcao', 'Pesquisa de percepção'], ['cruzada', 'Entre as fontes']];

const cartao = p => '<div class="card pad padrao conf-' + p.confianca + '"><div class="ph"><h3>' + esc(p.titulo) + '</h3><span class="dims">' +
  p.dimensoes.map(d => '<span class="dim">' + DIM[d] + '</span>').join('') + '</span></div>' +
  '<p>' + esc(p.descricao) + '</p>' +
  '<div class="evid"><span class="bar"><i style="width:' + Math.min(100, p.evidencia.pct) + '%"></i></span><span class="num">' + p.evidencia.n + ' de ' + p.evidencia.de + ' · ' + p.evidencia.pct + '%</span></div>' +
  '<div class="pf"><span class="conf">' + CONF[p.confianca] + '</span>' +
  (p.areas.length ? '<button type="button" class="btn sm" data-area="' + esc(p.areas[0]) + '">Ver no mapa</button>' : '') + '</div></div>';

export async function carregarPadroes(el) {
  const topo = '<h2>Padrões nos dados</h2><p class="lead">Onde, quando e que tipo de ocorrência mais aparece nos dados históricos, nos relatos e na pesquisa. Cada achado mostra de quantos casos ele vem.</p>';
  el.innerHTML = topo + '<p class="muted">Procurando padrões…</p>';
  let r;
  try { r = await apiGet('/analise/padroes'); } catch (e) { el.innerHTML = topo + '<div class="card empty"><p>A análise de padrões precisa do servidor da Aurora e não está disponível agora.</p></div>'; return; }
  const nome = id => (r.fontes.find(f => f.id === id) || { titulo: id }).titulo;
  const grupos = GRUPOS.map(([k, t]) => [t, r.padroes.filter(p => p.fonte.split(':')[0] === k)]).filter(([, l]) => l.length);
  el.innerHTML = topo +
    '<div class="card pad resumo"><span class="selo">' + (r.usa_modelo ? 'Resumo escrito pela IA local' : 'Resumo automático, sem IA') + '</span><p>' + esc(r.resumo) +
    '</p><small class="muted">Escrito só a partir dos achados abaixo; a detecção dos padrões é por contagem e limites mínimos de amostra.</small></div>' +
    '<div class="sec note-box"><svg class="i"><use href="#i-info"/></svg><span>' + r.avisos.map(esc).join(' ') + '</span></div>' +
    '<div class="fontes">' + r.fontes.map(f => '<span class="chipf ' + f.situacao + '">' + esc(f.titulo) + ' · ' + f.total + (f.situacao === 'ok' ? '' : ' · dados insuficientes') + '</span>').join('') + '</div>' +
    (grupos.length ? grupos.map(([t, l]) => '<h3 class="gp">' + esc(t) + '</h3><div class="grid2">' + l.map(cartao).join('') + '</div>').join('')
      : '<div class="card empty"><h3>Nenhum padrão se destaca</h3><p>Com os dados disponíveis, nenhuma região, período ou tipo passou dos limites mínimos para ser chamado de padrão.</p></div>') +
    (r.insuficiente.length ? '<h3 class="gp">Dados insuficientes</h3><div class="card pad"><ul class="insuf">' +
      r.insuficiente.map(i => '<li><b>' + esc(nome(i.fonte)) + ' · ' + DIM[i.dimensao].toLowerCase() + ':</b> ' + esc(i.motivo) + '</li>').join('') + '</ul></div>' : '');
  for (const b of el.querySelectorAll('[data-area]')) b.onclick = () => focusCell(b.dataset.area);
}
