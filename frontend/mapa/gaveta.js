/* celular: o que fica abaixo do mapa e o painel da área/trajeto viram uma gaveta que se arrasta para cima (como no Google Maps).
   Nada cobre o mapa até a pessoa puxar a gaveta; ao tocar numa área, os dados dela aparecem dentro da gaveta. */
import { $, h } from '../shared/dom.js';

let subir = () => {};
/* chamado a cada vez que a pessoa escolhe uma área, trajeto ou ponto de apoio: a gaveta sobe com os dados novos, mesmo que ela a tenha abaixado */
export const subirGaveta = () => subir();

export function montarGaveta() {
  if (!matchMedia('(max-width:720px)').matches) return; // no computador tudo continua em volta do mapa, como antes
  const MIN = 56, max = () => innerHeight - 140, meio = () => Math.round(max() * 0.55); // 140 = barra do topo + barra de baixo
  const painel = $('#panel'), titulo = h('b', { text: 'Sobre o mapa' });
  const alca = h('button', { type: 'button', class: 'gaveta-alca', 'aria-label': 'Arraste para cima para ver mais' }, h('span', { class: 'grip' }), titulo);
  const corpo = h('div', { class: 'gaveta-corpo' }, painel, $('#legend'), $('#mapNote'), $('#sheetInfo'), $('.areas'));
  const g = h('div', { class: 'gaveta', id: 'gaveta' }, alca, corpo);
  $('#view-mapa').append(g);

  const alt = v => { g.style.height = Math.max(MIN, Math.min(max(), v)) + 'px'; };
  const snap = v => { g.classList.add('anim'); alt(v); setTimeout(() => g.classList.remove('anim'), 260); };
  let y0 = null, h0 = 0, moveu = false;
  alca.addEventListener('pointerdown', e => { y0 = e.clientY; h0 = g.offsetHeight; moveu = false; try { alca.setPointerCapture(e.pointerId); } catch (err) { /* sem captura: o arraste ainda funciona dentro da alça */ } });
  alca.addEventListener('pointermove', e => { if (y0 == null) return; const dy = y0 - e.clientY; if (Math.abs(dy) > 4) moveu = true; if (moveu) alt(h0 + dy); });
  const soltar = () => {
    if (y0 == null) return; y0 = null;
    const a = g.offsetHeight;
    snap(moveu ? [MIN, meio(), max()].reduce((p, c) => (Math.abs(c - a) < Math.abs(p - a) ? c : p)) : (a > MIN + 10 ? MIN : meio())); // toque simples: abre ou fecha
  };
  subir = () => snap(meio());
  alca.addEventListener('pointerup', soltar); alca.addEventListener('pointercancel', soltar);

  /* abrir um painel (área, trajeto, apoio) mostra os dados na gaveta; fechar volta ao "Sobre o mapa" fechado */
  let aberto = false;
  new MutationObserver(() => {
    const ab = !painel.hidden;
    g.classList.toggle('com-painel', ab);
    titulo.textContent = !ab ? 'Sobre o mapa' : painel.dataset.kind === 'route' ? 'Trajeto' : 'Detalhes';
    if (ab !== aberto) { aberto = ab; corpo.scrollTop = 0; snap(ab ? meio() : MIN); }
  }).observe(painel, { attributes: true, attributeFilter: ['hidden', 'data-kind'] });
}
