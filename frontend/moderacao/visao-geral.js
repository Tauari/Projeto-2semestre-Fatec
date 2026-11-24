import { h, toast } from '../shared/dom.js';
import { apiGet } from '../shared/api.js';
import { CONFIG } from '../config.js';
import { TIPO } from '../shared/vocabulario.js';
import { areaName } from '../shared/bairros.js';

let dias = '30';
const num = n => Number(n).toLocaleString('pt-BR');

async function baixarPdf(periodo, minuta, botao) {
  botao.disabled = true;
  try {
    const res = await fetch(CONFIG.apiBase + '/moderacao/relatorio.pdf?dias=' + periodo + '&encaminhamento=' + minuta);
    if (!res.ok) throw new Error([401, 403].includes(res.status) ? 'Entre com uma conta de administrador para exportar.' : 'Não foi possível gerar o PDF. Tente novamente.');
    const url = URL.createObjectURL(await res.blob());
    const a = h('a', { href: url, download: minuta ? 'aurora-minuta-encaminhamento.pdf' : 'aurora-relatorio.pdf' });
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (e) { toast(e.message || 'Falha ao baixar o PDF.'); }
  finally { botao.disabled = false; }
}

function grafico(titulo, entradas, nota) {
  const box = h('section', { class: 'card painel-grafico' }, h('h2', null, titulo), h('p', { class: 'muted' }, nota));
  if (!entradas.length) { box.append(h('p', { class: 'painel-vazio' }, 'Nenhum relato neste período.')); return box; }
  const max = Math.max(...entradas.map(e => e[1]), 1);
  const list = h('ul', { class: 'painel-barras' });
  for (const [label, valor] of entradas) list.append(h('li', null,
    h('div', { class: 'painel-barra-legenda' }, h('span', null, label), h('b', null, num(valor))),
    h('div', { class: 'painel-barra-trilho', 'aria-hidden': 'true' }, h('span', { style: 'width:' + Math.max(1, valor / max * 100) + '%' }))));
  box.append(list); return box;
}

export function renderVisaoGeral(el, admin) {
  const host = h('div', { class: 'painel-geral' }); el.append(host);
  let versao = 0;
  async function carregar() {
    const atual = ++versao;
    host.replaceChildren();
    const periodo = h('select', { id: 'periodo-painel', onchange: () => { dias = periodo.value; carregar(); } },
      ...['7','30','90','365'].map(n => h('option', { value:n }, 'Últimos '+n+' dias')));
    periodo.value = dias;
    const cab = h('div', { class: 'painel-filtros' }, h('label', { for:'periodo-painel' }, 'Período do painel'), periodo,
      h('button', { type:'button', class:'btn sm', onclick:carregar }, 'Atualizar indicadores'));
    host.append(cab);
    const conteudo = h('div', { 'aria-live':'polite' }, h('p', { class:'muted' }, 'Carregando indicadores…'));host.append(conteudo);
    try {
      const dados = await apiGet('/moderacao/resumo?dias='+dias);
      if (!host.isConnected || atual !== versao) return;
      conteudo.replaceChildren();
      const cards=h('div', {class:'painel-metricas'});
      for (const [id,titulo,nota] of [
        ['total','Relatos recebidos','Todos os estados'],['pendentes','A revisar','Visíveis sem verificação'],
        ['verificados','Verificados','Visíveis com selo da equipe'],['ocultos','Ocultos','Fora das consultas públicas']]) {
        cards.append(h('article',{class:'card painel-metrica','data-metrica':id},h('p',null,titulo),h('strong',null,num(dados.indicadores[id])),h('small',null,nota)));
      }
      conteudo.append(cards,h('p',{class:'painel-nota'},dados.aviso));
      const ordenar = obj => Object.entries(obj).sort((a,b)=>b[1]-a[1]);
      const regioes = {};
      for (const [cell, total] of Object.entries(dados.por_celula)) { const nome = areaName(cell); regioes[nome] = (regioes[nome] || 0) + total; }
      const areas=ordenar(regioes);
      conteudo.append(h('div',{class:'painel-graficos'},
        grafico('Tipos de situação',ordenar(dados.por_tipo).map(([k,v])=>[TIPO[k]?.label || k,v]),'Um relato pode ter mais de um tipo.'),
        grafico('Áreas com mais relatos',areas.slice(0,8),'Até 8 regiões aproximadas. Concentração de relatos não significa risco.'),
        grafico('Envios por dia',Object.entries(dados.por_dia).slice(-14).map(([k,v])=>[k.split('-').reverse().join('/'),v]),'Últimos 14 dias com envios dentro do período selecionado. Datas em UTC.')));
      if (admin) {
        const exportar=h('section',{class:'card painel-exportar'},h('h2',null,'Relatórios e encaminhamento'),
          h('p',null,'Exporte as contagens deste período para reuniões e acompanhamento da equipe. Os documentos não incluem o texto dos relatos nem dados pessoais.'));
        const acoes=h('div',{class:'acts'});
        acoes.append(h('button',{type:'button',class:'btn primary',onclick:e=>baixarPdf(dados.dias,false,e.currentTarget)},'Baixar relatório PDF'));
        const detalhe=h('div',{class:'painel-minuta',hidden:true},h('h3',null,'Minuta para a Patrulha Maria da Penha'),
          h('p',null,'Nenhum documento é enviado automaticamente.'),
          h('p',null,'Revise os dados agregados e complete a finalidade, o responsável e a assinatura antes de enviar pelo canal institucional autorizado. Este documento não é um acionamento de emergência.'),
          h('button',{type:'button',class:'btn',onclick:e=>baixarPdf(dados.dias,true,e.currentTarget)},'Baixar minuta para revisão'));
        acoes.append(h('button',{type:'button',class:'btn','aria-expanded':'false',onclick:e=>{detalhe.hidden=!detalhe.hidden;e.currentTarget.setAttribute('aria-expanded',String(!detalhe.hidden));}},'Preparar encaminhamento'));
        exportar.append(acoes,detalhe);conteudo.append(exportar);
      }
      conteudo.append(h('p',{class:'muted painel-atualizacao'},'Atualizado em '+new Date(dados.gerado_em).toLocaleString('pt-BR')+'. Período limitado pela retenção do banco.'));
    } catch (e) {
      if (host.isConnected && atual===versao) conteudo.replaceChildren(h('p',{role:'alert'},e.message || 'Não foi possível carregar o painel.'),h('button',{type:'button',class:'btn',onclick:carregar},'Tentar novamente'));
    }
  }
  carregar();
}
