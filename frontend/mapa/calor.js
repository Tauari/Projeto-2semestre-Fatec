/* mapa de calor (como o do notebook de estatísticas): cada área vira uma mancha que esmaece com a distância,
   as manchas se somam e a soma vira cor. Desenhado em canvas, sem biblioteca: funciona offline. */

/* a mesma paleta do notebook nos dois temas: azul → verde → laranja → vermelho, já com a transparência */
const RAMPA = [[0, 'rgba(0,0,255,0)'], [0.2, 'rgba(0,0,255,.5)'], [0.5, 'rgba(0,230,0,.7)'], [0.8, 'rgba(255,165,0,.85)'], [1, 'rgba(255,0,0,.92)']];
export const rampaCss = () => 'linear-gradient(90deg,' + RAMPA.map(([p, c]) => c.replace(/,[.\d]+\)$/, ',1)') + ' ' + p * 100 + '%').join(',') + ')';

function paleta() {
  const c = document.createElement('canvas'); c.width = 1; c.height = 256;
  const g = c.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 256);
  for (const [p, cor] of RAMPA) gr.addColorStop(p, cor);
  g.fillStyle = gr; g.fillRect(0, 0, 1, 256);
  return g.getImageData(0, 0, 1, 256).data;
}

export function criarCalor(map, pane) {
  const cv = document.createElement('canvas'); cv.className = 'calor'; cv.style.pointerEvents = 'none';
  map.getPane(pane).appendChild(cv);
  let dados = { pts: [], raioM: 200, topo: 1, minPx: 36 }, cor = null;
  const pinta = () => {
    const s = map.getSize(), pad = Math.round(Math.max(s.x, s.y) * 0.25), w = s.x + pad * 2, h = s.y + pad * 2;
    L.DomUtil.setPosition(cv, map.containerPointToLayerPoint([-pad, -pad]));
    cv.width = w; cv.height = h; // redimensionar também limpa
    if (!dados.pts.length) return;
    const g = cv.getContext('2d'), z = map.getZoom();
    const r = Math.max(dados.minPx, dados.raioM / (40075016.686 * Math.cos(map.getCenter().lat * Math.PI / 180) / (256 * 2 ** z))); // com o mapa afastado a mancha não some
    for (const [ll, v] of dados.pts) {
      const p = map.latLngToContainerPoint(ll), x = p.x + pad, y = p.y + pad;
      if (x < -r || y < -r || x > w + r || y > h + r) continue;
      const a = 0.6 + 0.4 * Math.min(1, v / dados.topo), gr = g.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, 'rgba(0,0,0,' + a + ')'); gr.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2);
    }
    cor = cor || paleta();
    const img = g.getImageData(0, 0, w, h), d = img.data;
    for (let i = 0; i < d.length; i += 4) { const a = d[i + 3]; if (!a) continue; const k = a * 4; d[i] = cor[k]; d[i + 1] = cor[k + 1]; d[i + 2] = cor[k + 2]; d[i + 3] = cor[k + 3]; }
    g.putImageData(img, 0, 0);
  };
  map.on('zoomstart', () => { cv.style.visibility = 'hidden'; });
  map.on('zoomend moveend resize', () => { pinta(); cv.style.visibility = ''; });
  return {
    /* pts: [[[lat,lng], valor]]; raioM: alcance de cada mancha; topo: valor que já conta como "muito" */
    desenhar(pts, raioM, topo, minPx = 36) { dados = { pts, raioM, topo, minPx }; pinta(); },
    limpar() { dados = { pts: [], raioM: 200, topo: 1, minPx: 36 }; pinta(); }
  };
}
