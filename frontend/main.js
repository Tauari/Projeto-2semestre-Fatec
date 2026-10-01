/* Aurora · mapa colaborativo de segurança para mulheres em Rio Claro (SP)
   Com o servidor da Aurora, os relatos ficam no servidor (modo api);
   sem ele, o app lê os arquivos de dados/ e guarda tudo no aparelho (modo local). */
import { janelaTxt } from './config.js';
import { $, $$, toast } from './shared/dom.js';
import { fmtN } from './shared/formato.js';
import { mq } from './shared/tema.js';
import { D, AP as AP_DADOS, carregarDados } from './shared/dados.js';
import { configurarGrade } from './shared/grade.js';
import { configurarBairros } from './shared/bairros.js';
import { S } from './shared/estado.js';
import { Store } from './shared/store.js';
import { showView } from './shared/navegacao.js';
import { openSobre, closeSobre } from './shared/sobre.js';
import { quickExit, instalarAtalhos } from './shared/saida-rapida.js';
import { initMap, renderMap, setLayer } from './mapa/mapa.js';
import { refreshPanel } from './mapa/painel-area.js';
import { renderAreaList } from './mapa/lista-areas.js';
import { renderChips, syncControls } from './mapa/controles.js';
import { configurarApoio } from './apoio/rede.js';
import { showApoioOnMap } from './apoio/camada-apoio.js';
import { renderApoioPage } from './apoio/pagina-apoio.js';
import { recentReports } from './relatos/relatos.js';
import { renderAlertas } from './relatos/alertas.js';
import { Chat, relatar, closeChat } from './chatbot/chat.js';
import { renderDados } from './dashboard/dados-pesquisa.js';
import { canModerate, renderMod } from './moderacao/moderacao.js';

/* ------------------------------------------------------------------ inicialização */
export function boot() {
  $('#stBO').textContent = fmtN(D.bo.total.n);
  $('#stPesq').textContent = D.pesq.n;
  for (const b of $$('#layerSeg button')) b.onclick = () => setLayer(b.dataset.layer);
  $('#typeSel').onchange = e => { if (S.layer === 'relatos') S.tipo = e.target.value; else S.cat = e.target.value; renderMap(); };
  $('#areaSearch').addEventListener('input', renderAreaList);
  $('#areaMore').onclick = () => { S.showAll = !S.showAll; renderAreaList(); };
  for (const b of $$('#sobreTabs button')) b.onclick = () => openSobre(b.dataset.tab);
  $('#sobre').addEventListener('click', e => { if (e.target.id === 'sobre') closeSobre(); });
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-view],[data-act],[data-copy]'); if (!b) return;
    if (b.dataset.view) { showView(b.dataset.view); closeChat(); }
    const a = b.dataset.act;
    if (a === 'relatar') relatar();
    else if (a === 'sobre') openSobre(b.dataset.tab);
    else if (a === 'fecharSobre') closeSobre();
    else if (a === 'fecharChat') closeChat();
    else if (a === 'recomecar') Chat.start();
    else if (a === 'sair') quickExit();
    else if (a === 'apoioMapa') showApoioOnMap();
    if (b.dataset.copy) {
      const txt = b.dataset.copy;
      try { navigator.clipboard.writeText(txt).then(() => toast('Copiado: ' + txt), () => toast('Número: ' + txt)); } catch (err) { toast('Número: ' + txt); }
    }
  });
  syncControls();
  initMap();
  renderApoioPage();
  Chat.init();
  renderMap();
  Store.on(() => {
    const modNav = $('[data-modnav]'); if (modNav) modNav.hidden = !canModerate();
    if (!S.userLayer && Store.ready && recentReports().length && S.layer !== 'relatos') { S.layer = 'relatos'; syncControls(); }
    renderMap(); refreshPanel();
    if (S.view === 'dados') renderDados();
    if (S.view === 'alertas') renderAlertas(false);
    if (S.view === 'moderacao') renderMod();
  });
  Store.init();
  const onTheme = () => renderMap();
  if (mq.addEventListener) mq.addEventListener('change', onTheme);
  new MutationObserver(onTheme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  setInterval(() => { renderChips(); if (S.period === 'agora') { renderMap(); refreshPanel(); } }, 5 * 60e3);
}
/* os atalhos de teclado (Esc duas vezes = sair rápido) valem desde o início, como no legado */
export async function iniciar() {
  instalarAtalhos();
  /* o botão "Sair rápido" também funciona enquanto os dados carregam (ou se não carregarem); o boot assume depois */
  const sairCedo = e => { if (e.target.closest('[data-act="sair"]')) quickExit(); };
  document.addEventListener('click', sairCedo);
  const nota = document.getElementById('mapNote');
  if (!window.L) { nota.lastChild.textContent = 'O mapa não carregou. Verifique a conexão e recarregue a página.'; return; }
  nota.lastChild.textContent = 'Carregando dados…';
  try { await carregarDados(); } catch (e) { console.error(e); nota.lastChild.textContent = 'Não consegui carregar os dados. Verifique a conexão e recarregue a página.'; return; }
  configurarGrade(D.hex); configurarBairros(); configurarApoio(AP_DADOS);
  const jan = document.querySelector('#stRel ~ small'); if (jan) jan.textContent = 'últimos ' + janelaTxt();
  document.removeEventListener('click', sairCedo);
  boot();
}
iniciar();
