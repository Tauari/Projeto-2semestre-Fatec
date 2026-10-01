import { $, h, toast } from '../shared/dom.js';
import { areaName } from '../shared/bairros.js';
import { Store } from '../shared/store.js';
import { allReports } from '../relatos/relatos.js';
import { reportItem } from '../relatos/item-relato.js';

/* no modo api a moderação fica escondida: ela ainda é local e daria a impressão de moderar relatos compartilhados */
export const canModerate = () => Store.canEdit || Store.mode === 'local' || (Store.papeis || []).includes('moderacao');

export function renderMod() {
  const el = $('#view-moderacao'); el.replaceChildren();
  el.append(h('div', { class: 'page-head' }, h('p', { class: 'eyebrow' }, 'Moderação'), h('h1', null, 'Revisar relatos'),
    h('p', null, 'Relatos com 3 ou mais sinalizações de informação falsa saem do mapa até alguém da equipe revisar. “Verificar” mantém o relato visível e mostra um selo.')));
  if (!canModerate()) { el.append(h('p', { class: 'muted' }, 'Só a equipe responsável vê esta página.')); return; }
  const all = allReports().sort((a, b) => ((Store.votes[b.id] || {}).f || 0) - ((Store.votes[a.id] || {}).f || 0) || b.criado - a.criado);
  if (!all.length) { el.append(h('div', { class: 'card empty' }, h('h3', null, 'Nenhum relato ainda'), h('p', null, 'Os relatos enviados pelo chat aparecem aqui.'))); return; }
  const list = h('div', { class: 'modlist' });
  for (const r of all) {
    const v = Store.votes[r.id] || { c: 0, p: 0, f: 0 }, oc = !!Store.mod.oculto[r.id], ver = !!Store.mod.verificado[r.id];
    const status = ver ? 'Verificado' : oc ? 'Oculto pela equipe' : v.f >= 3 ? 'Fora do mapa: ' + v.f + ' sinalizações' : 'Visível';
    const left = h('div', { style: 'display:grid;gap:6px' }, h('b', { text: areaName(r.cell) }),
      h('span', { class: 'muted', style: 'font-size:13px' }, status + ' · ' + v.c + ' ainda acontece · ' + v.p + ' parou · ' + v.f + ' falso'),
      reportItem(r, { votes: false, tag: 'div' }));
    const act = (label, fn) => h('button', { class: 'btn sm', type: 'button', onclick: async () => { try { await fn(); toast('Moderação salva.'); } catch (e) { toast('Não foi possível salvar. Só quem pode editar o protótipo modera.'); } } }, label);
    list.append(h('div', { class: 'card modrow' }, left, h('div', { class: 'acts' },
      oc ? act('Mostrar', () => Store.setMod(r.id, 'oculto', false)) : act('Ocultar', () => Store.setMod(r.id, 'oculto', true)),
      ver ? act('Tirar verificação', () => Store.setMod(r.id, 'verificado', false)) : act('Verificar', () => Store.setMod(r.id, 'verificado', true)))));
  }
  el.append(list);
}
