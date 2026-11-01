import { h, icon, toast } from '../shared/dom.js';
import { ago, cap } from '../shared/formato.js';
import { TIPO, PER, QUANDO } from '../shared/vocabulario.js';
import { Store } from '../shared/store.js';
import { isHidden } from './relatos.js';
import { tituloAlerta } from './alerta.js';
import { detalheAcessorios } from './acessorios.js';

export function voteRow(r) {
  const v = Store.votes[r.id] || { c: 0, p: 0, f: 0 }, mine = Store.myVotes[r.id];
  const mk = (key, ic, label, count) => h('button', { type: 'button', class: 'vote' + (mine === key ? ' on' : ''), 'aria-pressed': mine === key ? 'true' : 'false',
    title: Store.canVote() ? '' : 'Entre com uma conta com acesso de participação para confirmar',
    onclick: async () => {
      if (!Store.canVote()) { toast('Para confirmar relatos, é preciso acesso de participação a este protótipo.'); return; }
      try { await Store.vote(r.id, key); if (Store.myVotes[r.id] === key) toast(Store.mode === 'api' ? 'Obrigada. Por enquanto, essa marcação fica só neste aparelho: a revisão pela equipe ainda não foi ligada.'
        : key === 'f' ? 'Obrigada. A equipe vai revisar este relato.' : 'Obrigada. Sua confirmação ajuda outras mulheres.'); }
      catch (e) { toast('Não consegui registrar agora. Tente de novo.'); }
    } }, icon(ic), label, count != null ? h('span', { class: 'num', text: '(' + count + ')' }) : null);
  return h('div', { class: 'votes' },
    mk('c', 'check', 'Ainda acontece', v.c),
    mk('p', 'clock', 'Não acontece mais', v.p),
    mk('f', 'flag', 'Informação falsa', Store.canEdit ? v.f : null));
}
/* O relato aparece com o título padrão do tipo ("Potencial assediador na área") e, embaixo, só as roupas e os acessórios que a
   usuária citou ("Visto com: camiseta preta, calça roxa"). O resto do texto só aparece com `texto: true` (a moderação precisa ler)
   ou quando o tipo não gera título. */
export function reportItem(r, { votes = true, preview = false, tag = 'li', texto = false } = {}) {
  const box = h(tag, { class: 'rep' });
  box.append(h('div', { class: 'tipos' }, r.tipos.map(t => h('span', { class: 'tipo', text: TIPO[t].label }))));
  const meta = [];
  if (!preview) meta.push('Relatado ' + ago(r.criado));
  if (r.quando) meta.push('aconteceu ' + QUANDO[r.quando]);
  if (r.periodo) meta.push(PER[r.periodo].long);
  if (meta.length) box.append(h('div', { class: 'meta', text: cap(meta.join(' · ')) }));
  const titulo = texto ? null : tituloAlerta(r.tipos);
  if (titulo) {
    box.append(h('p', { class: 'txt alerta', text: titulo }));
    const visto = detalheAcessorios(r.texto); // só roupas e acessórios: o resto do texto não aparece
    if (visto) box.append(h('p', { class: 'txt detalhe', text: 'Visto com: ' + visto }));
  } else if (r.texto) box.append(h('p', { class: 'txt', text: r.texto }));
  if (!preview) {
    const flags = h('div', { class: 'flags' });
    if (Store.mod.verificado[r.id]) flags.append(h('span', { class: 'badge-ok' }, icon('shield', 'i sm'), 'Verificado pela equipe'));
    else flags.append(h('span', { class: 'badge-soft', text: 'Relato de uma usuária · não verificado' }));
    if (isHidden(r)) flags.append(h('span', { class: 'badge-warn', text: 'Fora do mapa até revisão' }));
    if (Store.perfil.meus.includes(r.id)) flags.append(h('span', { class: 'badge-soft', text: 'Enviado por você' }));
    box.append(flags);
    if (votes) box.append(voteRow(r));
  }
  return box;
}
