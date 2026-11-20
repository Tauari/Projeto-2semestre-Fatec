import { $, h, toast } from '../shared/dom.js';
import { areaName } from '../shared/bairros.js';
import { Store } from '../shared/store.js';
import { allReports, cleanReport } from '../relatos/relatos.js';
import { renderVisaoGeral } from './visao-geral.js';
import { renderEquipe } from './equipe.js';
import { reportItem } from '../relatos/item-relato.js';

export const canModerate = () => Store.mode === 'api' ? !!Store.moderacao && (Store.papeis || []).includes('moderacao') : Store.canEdit || Store.mode === 'local';

let aba = 'resumo';

function formularioAcesso(el) {
  const login = h('input', { id: 'login-equipe', required: true, autocomplete: 'username', maxlength: 64, placeholder: 'Seu usuário' });
  const senha = h('input', { id: 'senha-equipe', type: 'password', required: true, autocomplete: 'current-password', maxlength: 128 });
  const erro = h('p', { role: 'alert', class: 'form-error' });
  const entrar = h('button', { class: 'btn primary', type: 'submit' }, 'Entrar');
  const form = h('form', { class: 'card acesso-equipe', onsubmit: async e => {
    e.preventDefault(); entrar.disabled = true; erro.textContent = '';
    try { aba = 'resumo'; await Store.entrarModeracao(login.value, senha.value); senha.value = ''; }
    catch (err) { erro.textContent = err.message || 'Não foi possível entrar. Tente novamente.'; }
    finally { entrar.disabled = false; }
  } }, h('h2', null, 'Acesso da equipe'), h('p', { class: 'muted' }, 'Entre com a conta criada pelo administrador responsável.'),
  h('label', { for: 'login-equipe' }, 'Usuário'), login, h('label', { for: 'senha-equipe' }, 'Senha'), senha, erro, entrar);
  el.append(form);
}

export function renderMod() {
  const el = $('#view-moderacao');
  // Releituras do mapa não apagam uma chave que a pessoa está digitando.
  if (Store.mode === 'api' && !canModerate() && el.querySelector('.acesso-equipe')) return;
  if (aba === 'resumo' && canModerate() && el.querySelector('.painel-geral')) return;
  if (aba === 'equipe' && canModerate() && el.querySelector('.equipe-layout')) return;
  el.replaceChildren();
  el.append(h('div', { class: 'page-head' }, h('p', { class: 'eyebrow' }, 'Moderação'), h('h1', null, canModerate() && aba === 'equipe' ? 'Pessoas que cuidam da comunidade' : aba === 'resumo' && canModerate() ? 'Visão geral da comunidade' : 'Revisar relatos'),
    h('p', null, Store.mode === 'api'
      ? aba === 'resumo' && canModerate() ? 'Acompanhe os relatos recebidos, consulte os indicadores e prepare os documentos da equipe.' : 'Revise os relatos da comunidade. Ocultar retira o relato do mapa para todas as pessoas. Verificar adiciona o selo da equipe. Os votos ainda ficam somente no aparelho de quem votou.'
      : 'Moderação local para testes: as decisões ficam apenas neste aparelho. Três sinalizações de informação falsa tiram um relato do mapa até a revisão.')));
  if (!Store.ready) { el.append(h('p', { class: 'muted' }, 'Carregando…')); return; }
  if (Store.mode === 'api' && !canModerate()) { formularioAcesso(el); return; }
  if (!canModerate()) { el.append(h('p', { class: 'muted' }, 'Só a equipe responsável vê esta página.')); return; }
  if (Store.mode === 'api') {
    const usuario = Store.moderacao.usuario;
    el.append(h('div', { class: 'equipe-toolbar' },
      h('p', { class: 'muted' }, h('b', null, usuario.login), ' · ', usuario.papel === 'administrador' ? 'Administrador' : 'Moderador'),
      h('div', { class: 'acts' },
        h('button', { class: 'btn sm', type: 'button', onclick: async () => {
          try { await Store.sairModeracao(); aba = 'resumo'; } catch (err) { toast(err.message); }
        } }, 'Sair da moderação'))));
    const tabs = h('div', { class: 'equipe-tabs', role: 'group', 'aria-label': 'Painel da equipe' });
    const tab = (nome, valor) => h('button', { class: 'btn' + (aba === valor ? ' primary' : ''), type: 'button',
      'aria-pressed': aba === valor ? 'true' : 'false', onclick: () => { aba = valor; el.replaceChildren(); renderMod(); } }, nome);
    tabs.append(tab('Visão geral', 'resumo'), tab('Relatos', 'relatos'));
    if (usuario.papel === 'administrador') tabs.append(tab('Equipe', 'equipe'));
    el.append(tabs);
    if (aba === 'resumo') { renderVisaoGeral(el, usuario.papel === 'administrador'); return; }
    if (aba === 'equipe' && usuario.papel === 'administrador') { renderEquipe(el, usuario); return; }
    el.append(h('button', { class: 'btn sm mod-refresh', type: 'button', onclick: async e => {
      e.currentTarget.disabled = true;
      try { await Store.atualizarModeracao(); } catch (err) { toast(err.message); }
      finally { renderMod(); }
    } }, 'Atualizar relatos'));
  }
  const mod = Store.mode === 'api' ? Store.moderacao.mod : Store.mod;
  const all = Store.mode === 'api' ? Store.moderacao.relatos.map(cleanReport).filter(Boolean) : allReports();
  all.sort((a, b) => Store.mode === 'api'
    ? Number(!!mod.oculto[b.id]) - Number(!!mod.oculto[a.id]) || b.criado - a.criado
    : ((Store.votes[b.id] || {}).f || 0) - ((Store.votes[a.id] || {}).f || 0) || b.criado - a.criado);
  if (!all.length) { el.append(h('div', { class: 'card empty' }, h('h3', null, 'Nenhum relato ainda'), h('p', null, 'Os relatos enviados pelo chat aparecem aqui.'))); return; }
  const list = h('div', { class: 'modlist' });
  for (const r of all) {
    const oc = !!mod.oculto[r.id], ver = !!mod.verificado[r.id];
    const v = Store.votes[r.id] || { c: 0, p: 0, f: 0 };
    const status = oc ? 'Oculto pela equipe' : ver ? 'Verificado' : Store.mode !== 'api' && v.f >= 3 ? 'Fora do mapa até revisão' : 'Visível';
    const detalhe = Store.mode === 'api' ? status : status + ' · ' + v.c + ' ainda acontece · ' + v.p + ' parou · ' + v.f + ' falso';
    const left = h('div', { style: 'display:grid;gap:6px' }, h('b', { text: areaName(r.cell) }),
      h('span', { class: 'muted', style: 'font-size:13px' }, detalhe),
      reportItem(r, { votes: false, tag: 'div', texto: true, moderacao: mod }));
    const acts = h('div', { class: 'acts' });
    const act = (label, key, value) => h('button', { class: 'btn sm', type: 'button', onclick: async () => {
      for (const b of acts.querySelectorAll('button')) b.disabled = true;
      try { await Store.setMod(r.id, key, value); toast('Moderação salva.'); }
      catch (err) { toast(err.message || 'Não foi possível salvar. Tente novamente.'); }
      finally { for (const b of acts.querySelectorAll('button')) b.disabled = false; }
    } }, label);
    acts.append(act(oc ? 'Mostrar' : 'Ocultar', 'oculto', !oc), act(ver ? 'Tirar verificação' : 'Verificar', 'verificado', !ver));
    list.append(h('div', { class: 'card modrow' }, left, acts));
  }
  el.append(list);
}
