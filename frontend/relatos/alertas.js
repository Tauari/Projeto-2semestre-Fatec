import { janelaTxt, margemCriadoMs } from '../config.js';
import { $, h, icon, toast } from '../shared/dom.js';
import { DAY, plural } from '../shared/formato.js';
import { STANDALONE } from '../shared/ambiente.js';
import { D } from '../shared/dados.js';
import { dentro, grossa } from '../shared/grade.js';
import { areaName } from '../shared/bairros.js';
import { Store } from '../shared/store.js';
import { updateCounts } from '../mapa/mapa.js';
import { focusCell } from '../mapa/lista-areas.js';
import { Watch } from '../mapa/localizacao.js';
import { allReports, recentReports } from './relatos.js';
import { reportItem } from './item-relato.js';

export function toggleFollow(id, force) {
  const a = new Set(Store.perfil.areas), on = force != null ? force : !a.has(id);
  if (on) a.add(id); else a.delete(id);
  Store.perfil.areas = [...a]; Store.savePerfil(); Store.emit();
  toast(on ? 'Você está acompanhando ' + areaName(id) + '. As novidades aparecem em Meus alertas.' : 'Você parou de acompanhar esta área.');
}

/* novo desde a última visita. Com a hora de envio arredondada no servidor (ou com o relógio do aparelho diferente),
   um relato pode ter criado <= visto sem ter sido visto: por isso a visita guarda também os ids vistos */
function ehNovo(r, visto, meus) {
  if (meus.has(r.id) || (Store.perfil.vistos || []).includes(r.id)) return false;
  return r.criado > visto - margemCriadoMs();
}
export function alertCount() {
  const areas = Store.perfil.areas; if (!areas.length) return 0;
  const visto = Store.perfil.visto || 0, meus = new Set(Store.perfil.meus);
  return recentReports().filter(r => areas.some(a => dentro(r.cell, a)) && ehNovo(r, visto, meus)).length;
}
export function renderAlertas(markSeen) {
  const el = $('#view-alertas'), areas = Store.perfil.areas, visto = Store.perfil.visto || 0, meus = new Set(Store.perfil.meus);
  const rec = recentReports();
  el.replaceChildren();
  el.append(h('div', { class: 'page-head' }, h('p', { class: 'eyebrow' }, 'Meus alertas'), h('h1', null, 'As áreas por onde você passa'),
    h('p', null, 'Acompanhe as áreas do seu caminho. Quando alguém relata algo nelas, aparece aqui na próxima vez que você abrir a Aurora.')));
  const s1 = h('div', { class: 'sec' }, h('h2', null, 'Áreas que você acompanha'));
  if (!areas.length) {
    s1.append(h('div', { class: 'card empty' }, h('h3', null, 'Você ainda não acompanha nenhuma área'),
      h('p', null, 'No mapa, toque numa área (a da sua casa, do trabalho ou da faculdade) e escolha “Acompanhar”.'),
      h('div', null, h('button', { class: 'btn primary sm', type: 'button', 'data-view': 'mapa' }, icon('map', 'i sm'), 'Abrir o mapa'))));
  } else {
    const list = h('div', { class: 'follow' });
    for (const id of areas) {
      const rs = rec.filter(r => dentro(r.cell, id)), n7 = rs.filter(r => r.criado > Date.now() - 7 * DAY).length, novos = rs.filter(r => ehNovo(r, visto, meus)).length;
      const pc = D.pesq.cells[grossa(id)];
      const info = [plural(rs.length, 'relato em ' + janelaTxt(), 'relatos em ' + janelaTxt()) + (n7 ? ' (' + n7 + ' nesta semana)' : ''), pc ? 'citada por ' + plural(pc.n, 'mulher', 'mulheres') + ' na pesquisa' : ''].filter(Boolean).join(' · ');
      list.append(h('div', { class: 'card fcard' },
        h('div', null, h('h3', { text: areaName(id) }), h('p', null, info), novos ? h('p', { class: 'new' }, plural(novos, 'novo desde sua última visita', 'novos desde sua última visita')) : null),
        h('div', { class: 'acts' },
          h('button', { class: 'btn sm', type: 'button', onclick: () => focusCell(id) }, 'Ver no mapa'),
          h('button', { class: 'btn sm ghost', type: 'button', onclick: () => { toggleFollow(id, false); renderAlertas(false); } }, 'Parar de acompanhar'))));
    }
    s1.append(list);
    const novos = rec.filter(r => areas.some(a => dentro(r.cell, a)) && ehNovo(r, visto, meus));
    if (novos.length) {
      const ul = h('ul', { class: 'reports', style: 'margin-top:14px' });
      for (const r of novos.slice(0, 10)) { const li = reportItem(r); li.prepend(h('b', { text: areaName(r.cell) })); ul.append(li); }
      s1.append(h('h3', { style: 'margin-top:20px;font-size:17px' }, 'Novidades nas suas áreas'), ul);
    }
  }
  el.append(s1);
  const s2 = h('div', { class: 'sec' }, h('h2', null, 'Aviso ao passar por uma área'));
  if (STANDALONE && 'geolocation' in navigator) {
    const sw = h('button', { class: 'switch', type: 'button', role: 'switch', 'aria-checked': Watch.on ? 'true' : 'false', 'aria-label': 'Modo atenção' });
    sw.onclick = () => { if (Watch.on) Watch.stop(); else Watch.start(); renderAlertas(false); };
    s2.append(h('div', { class: 'card pad', style: 'display:grid;gap:10px' },
      h('div', { class: 'toggle' }, sw, h('div', null, h('b', null, 'Modo atenção'), h('p', { class: 'muted', style: 'font-size:14px' }, 'Com a Aurora aberta, avisa com vibração quando você entra numa área com relatos recentes, citada na pesquisa ou que você acompanha. Sua localização fica só neste aparelho.'))),
      Watch.on ? h('p', { style: 'font-size:14px;color:var(--ok)' }, Watch.cell ? 'Ligado. Você está em ' + areaName(Watch.cell) + '.' : 'Ligado. Procurando sua localização…') : null));
  } else {
    s2.append(h('div', { class: 'note-box' }, icon('info'), h('span', null, 'Neste link de demonstração o navegador não libera sua localização. Na versão instalada (o arquivo que a equipe hospeda), a Aurora avisa com vibração quando você entra numa área com relatos recentes.')));
  }
  el.append(s2);
  const mine = allReports().filter(r => meus.has(r.id));
  const s3 = h('div', { class: 'sec' }, h('h2', null, 'Meus relatos'), h('p', { class: 'lead' }, 'Esta lista fica só neste aparelho.'));
  if (!mine.length) s3.append(h('p', { class: 'muted' }, 'Você ainda não enviou relatos.'));
  else {
    const ul = h('ul', { class: 'reports' });
    for (const r of mine) {
      const li = reportItem(r, { votes: false }); li.prepend(h('b', { text: areaName(r.cell) }));
      const del = h('button', { class: 'btn sm danger', type: 'button' }, icon('trash', 'i sm'), 'Apagar relato');
      del.onclick = async () => {
        if (!del.dataset.confirm) { del.dataset.confirm = '1'; del.lastChild.textContent = 'Confirmar: apagar de vez'; return; }
        try { await Store.deleteReport(r.id); toast('Relato apagado.'); renderAlertas(false); } catch (e) { toast('Não consegui apagar agora.'); }
      };
      li.append(h('div', null, del)); ul.append(li);
    }
    s3.append(ul);
  }
  el.append(s3);
  if (markSeen) {
    const agora = Date.now(), folga = margemCriadoMs() + 36e5; // + 1 h para relógio do aparelho atrasado
    Store.perfil.visto = agora;
    Store.perfil.vistos = rec.filter(r => r.criado > agora - folga).map(r => r.id);
    Store.savePerfil(); updateCounts();
  }
}
