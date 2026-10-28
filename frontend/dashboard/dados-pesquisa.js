import { janelaTxt } from '../config.js';
import { $, esc } from '../shared/dom.js';
import { fmtN, pct, plural, fmtDate } from '../shared/formato.js';
import { TIPO, PERIODOS } from '../shared/vocabulario.js';
import { D } from '../shared/dados.js';
import { areaName } from '../shared/bairros.js';
import { recentReports } from '../relatos/relatos.js';
import { carregarPadroes } from './padroes.js';

export function barsCard(title, items, total, { cls = '', sub = '', max } = {}) {
  const m = max || Math.max(1, ...items.map(x => x[1]));
  return '<div class="card pad bars"><h3>' + esc(title) + '</h3>' + (sub ? '<p class="sub">' + esc(sub) + '</p>' : '') +
    items.map(([l, v]) => '<div class="bar ' + cls + '" title="' + v + ' de ' + total + '"><span class="l">' + esc(l) + ' <span class="muted num">· ' + v + '</span></span><span class="v num">' + pct(v, total) + '%</span><span class="t"><i style="width:' + (100 * v / m).toFixed(1) + '%"></i></span></div>').join('') + '</div>';
}
export function renderDados() {
  const P = D.pesq, N = P.n, K = P.k, st = P.stats, B = D.bo, g = B.grupos;
  const get = (key, label) => (st[key].i.find(x => x[0] === label) || [0, 0])[1];
  const f = k => pct(get('funcoes', k), N), t = k => pct(get('confianca', k), N);
  const topBO = Object.entries(B.cells).sort((a, b) => b[1].n - a[1].n).slice(0, 8).map(([id, c]) => [areaName(id), c.n]);
  const reps = recentReports();
  const byT = {}; const byP = {};
  for (const r of reps) { for (const x of r.tipos) byT[x] = (byT[x] || 0) + 1; if (r.periodo) byP[r.periodo] = (byP[r.periodo] || 0) + 1; }
  const el = $('#view-dados');
  el.innerHTML =
    '<div class="page-head"><p class="eyebrow">Dados e pesquisa</p><h1>O que Rio Claro já contou</h1>' +
    '<p>Duas fontes alimentam o mapa: a pesquisa “Segurança e percepção das mulheres em Rio Claro”, com ' + N + ' respostas entre ' + fmtDate(P.de) + ' e ' + fmtDate(P.ate) + ', e ' + fmtN(B.total.n) + ' registros de boletins de ocorrência da SSP-SP. Os relatos da comunidade entram ao vivo.</p></div>' +
    '<div class="sec" id="padroes"></div>' +
    '<div class="grid2">' +
    kfig(pct(K.evitam, N), 'evitam passar por certos lugares da cidade', K.evitam + ' de ' + N + ' respostas') +
    kfig(pct(K.viveram, N), 'já viveram uma situação que as fez se sentir inseguras ou ameaçadas', K.viveram + ' de ' + N) +
    kfig(pct(K.noite, N), 'se sentem menos seguras no início da noite, à noite ou de madrugada', K.noite + ' de ' + N) +
    kfig(pct(K.usariam, N), 'usariam um mapa colaborativo com relatos recentes', K.usariam + ' de ' + N + ' (com certeza ou provavelmente)') +
    '</div>' +
    '<div class="sec"><h2>Quando e por quê</h2><p class="lead">Respostas de múltipla escolha: cada barra mostra a parcela das ' + N + ' mulheres que marcou a opção.</p><div class="grid2">' +
    barsCard(st.periodo.t, st.periodo.i, N, { max: N }) + barsCard(st.motivo.t, st.motivo.i, N, { max: N }) + '</div></div>' +
    '<div class="sec"><h2>O que já viveram e onde</h2><div class="grid2">' +
    barsCard(st.situacao.t, st.situacao.i, N, { max: N, sub: 'Entre todas as respondentes.' }) +
    barsCard('Regiões citadas como inseguras', P.areas, P.comRegiao, { max: P.comRegiao, sub: P.comRegiao + ' mulheres responderam onde se sentem inseguras. Outros lugares citados: ' + P.outros.map(x => x[0]).join(', ') + '.' }) +
    barsCard(st.horario.t, st.horario.i, st.horario.n, { max: st.horario.n, sub: 'Entre as ' + st.horario.n + ' que responderam.' }) +
    barsCard(st.mudaria.t, st.mudaria.i, st.mudaria.n, { max: st.mudaria.n, sub: st.mudaria.n + ' respostas abertas, agrupadas por tema.' }) +
    '</div></div>' +
    '<div class="sec"><h2>Por que os grupos de WhatsApp não bastam</h2><p class="lead">' + pct(K.whats, N) + '% ficam sabendo de riscos por grupos de WhatsApp. Os problemas mais citados são justamente o que um mapa resolve.</p><div class="grid2">' +
    barsCard(st.whats.t, st.whats.i, N, { max: N }) + barsCard(st.sabe.t, st.sabe.i, N, { max: N }) + '</div></div>' +
    '<div class="sec"><h2>Do pedido ao MVP</h2><p class="lead">Cada função existe porque foi pedida na pesquisa.</p><div class="card tablewrap"><table class="maptable"><thead><tr><th>Pedido</th><th>Quem pediu</th><th>Como o MVP responde</th></tr></thead><tbody>' +
    trow('Mapa de alertas', f('Mapa de alertas'), 'Mapa com três camadas: relatos recentes, percepção da pesquisa e histórico de B.O.') +
    trow('Consultar antes de fazer um trajeto', f('Consultar informações antes de fazer um trajeto'), 'Checar trajeto: marca partida e destino e lista as áreas no caminho.') +
    trow('Visualizar alertas por horário', f('Visualizar alertas por horário'), 'Filtro de horário com as mesmas faixas da pesquisa, incluindo “Agora”.') +
    trow('Ver relatos próximos de um local', f('Ver relatos próximos de determinado local'), 'Toque numa área para ver relatos, percepção e registros dela.') +
    trow('Receber alertas de uma região', f('Receber alertas de uma região'), 'Acompanhar áreas em Meus alertas. Na versão instalada, aviso ao entrar na área.') +
    trow('Registrar um relato', f('Registrar um relato'), 'Chat da Aurora: botões ou texto livre, sem nome e sem endereço.') +
    trow('Encontrar serviços de apoio', f('Encontrar serviços de apoio'), 'Camada “Onde pedir ajuda” no mapa: Delegacia da Mulher, Guarda, CREAS, CRAS, Secretaria da Mulher, Defensoria e saúde 24h, com endereço, horário e telefone.') +
    '</tbody></table></div>' +
    '<div class="card tablewrap" style="margin-top:14px"><table class="maptable"><thead><tr><th>Para confiar, precisam de</th><th>Quem citou</th><th>Como o MVP responde</th></tr></thead><tbody>' +
    trow('Saber quantas relataram algo parecido', t('Saber quantas pessoas fizeram relatos semelhantes'), 'Contagem por área e confirmações “ainda acontece” em cada relato.') +
    trow('Instituição responsável', t('Saber que existe participação de uma instituição responsável'), 'Painel de moderação para a equipe e o Observatório.') +
    trow('Saber quando aconteceu', t('Saber quando o relato aconteceu'), 'Cada relato mostra quando foi enviado, quando aconteceu e a faixa de horário.') +
    trow('Moderação', t('Saber que existe moderação'), 'Três sinalizações de informação falsa tiram o relato do mapa até revisão.') +
    trow('Não identificar as pessoas', t('Saber que os relatos não identificam as pessoas'), 'Área de ~150 m, texto sem nomes, telefones e placas, relato gravado sem a conta de quem enviou.') +
    trow('Denunciar informação falsa', t('Poder denunciar informações falsas'), 'Botão “Informação falsa” em cada relato.') +
    trow('Não acusar pessoas individualmente', t('Saber que o sistema não acusa pessoas individualmente'), 'A Aurora reescreve o texto descrevendo a situação, sem identificar ninguém.') +
    '</tbody></table></div></div>' +
    '<div class="sec"><h2>Registros de boletins de ocorrência</h2><p class="lead">Base R.D.O. da SSP-SP obtida via FALASP, com ocorrências registradas de janeiro de 2025 a abril de 2026. São contagens por bairro, sem boletins individuais.</p><div class="grid2">' +
    '<div class="card pad"><dl class="dl">' +
    '<dt>Violência doméstica</dt><dd class="num">' + fmtN(B.total.vd) + '</dd><dt>Feminicídio</dt><dd class="num">' + B.total.fe + '</dd><dt>Tentativa de feminicídio</dt><dd class="num">' + B.total.te + '</dd>' +
    '<dt>Soma dos três</dt><dd class="num"><b>' + fmtN(B.total.n) + '</b></dd>' +
    '<dt>No mapa</dt><dd class="num">' + fmtN(g.mapeado.n) + ' em ' + g.mapeado.linhas + ' bairros com coordenada própria</dd>' +
    '<dt>Zona rural</dt><dd class="num">' + g.rural.n + ' (posição distribuída pela fonte, fora do mapa)</dd>' +
    '<dt>Sem bairro</dt><dd class="num">' + B.semGeo.n + ' + ' + g.naoinf.n + ' sem nome de bairro</dd>' +
    '<dt>Sem posição precisa</dt><dd class="num">' + g.placeholder.n + ' em ' + g.placeholder.linhas + ' bairros com coordenada genérica</dd>' +
    '</dl><p class="muted" style="font-size:13px;margin-top:12px">683 é a soma de três contadores e não garante 683 episódios ou pessoas distintas.</p></div>' +
    barsCard('Áreas com mais registros', topBO, g.mapeado.n, { cls: 'rose', sub: 'Parcela dos registros exibidos no mapa. Não é taxa por população.' }) +
    '</div></div>' +
    '<div class="sec"><h2>Relatos da comunidade</h2>' +
    (reps.length ? '<p class="lead">' + plural(reps.length, 'relato', 'relatos') + ' nos últimos ' + janelaTxt() + '.</p><div class="grid2">' +
      barsCard('Tipos de situação', Object.entries(byT).sort((a, b) => b[1] - a[1]).map(([k, v]) => [TIPO[k].label, v]), reps.length, { cls: 'amb' }) +
      barsCard('Horário', PERIODOS.filter(p => byP[p.id]).map(p => [p.long, byP[p.id]]), reps.length, { cls: 'amb' }) + '</div>'
      : '<div class="card empty"><h3>Ainda não há relatos</h3><p>Quando as primeiras mulheres registrarem situações pelo chat, os tipos e horários aparecem aqui.</p></div>') +
    '</div>' +
    '<div class="sec note-box"><svg class="i"><use href="#i-info"/></svg><span>Percepção não é ocorrência, e registro de B.O. não é risco atual. As três camadas ficam separadas de propósito para que cada uma seja lida pelo que é. Detalhes em <button class="linkbtn" data-act="sobre" data-tab="fontes" style="text-decoration:underline">Fontes e método</button>.</span></div>';
  carregarPadroes($('#padroes'));
}
export function kfig(v, label, small) { return '<div class="card kfig"><b class="num">' + v + '%</b><span>' + esc(label) + '</span><small>' + esc(small) + '</small></div>'; }
export function trow(a, p, b) { return '<tr><td>' + esc(a) + '</td><td class="p num">' + p + '%</td><td>' + esc(b) + '</td></tr>'; }
