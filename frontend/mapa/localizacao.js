import { toast } from '../shared/dom.js';
import { plural } from '../shared/formato.js';
import { D } from '../shared/dados.js';
import { cellOf } from '../shared/grade.js';
import { areaName } from '../shared/bairros.js';
import { S } from '../shared/estado.js';
import { Store } from '../shared/store.js';
import { map } from './mapa.js';
import { fmtDist, nearestApoio } from '../apoio/rede.js';
import { recentReports } from '../relatos/relatos.js';
import { renderAlertas } from '../relatos/alertas.js';

/* ------------------------------------------------------------------ onde você está no mapa */
export let meMarker = null;
export function showMe(ll) {
  if (!meMarker) meMarker = L.marker(ll, { icon: L.divIcon({ className: '', html: '<span class="youare"></span>', iconSize: [0, 0] }), interactive: false, keyboard: false }).addTo(map);
  else meMarker.setLatLng(ll);
}

/* ------------------------------------------------------------------ modo atenção (GPS, só na versão arquivo) */
export const Watch = {
  id: null, on: false, cell: null, last: {},
  start() {
    if (!('geolocation' in navigator)) return;
    this.on = true; this.cell = null;
    this.id = navigator.geolocation.watchPosition(p => this.onPos(p), () => { toast('Não consegui acessar sua localização. Verifique a permissão do navegador.'); this.stop(); renderAlertas(false); },
      { enableHighAccuracy: true, maximumAge: 15000, timeout: 30000 });
    try { if ('Notification' in window && Notification.permission === 'default') Notification.requestPermission(); } catch (e) { /* opcional */ }
    toast('Modo atenção ligado.');
  },
  stop() { if (this.id != null) navigator.geolocation.clearWatch(this.id); this.id = null; this.on = false; this.cell = null; if (meMarker) { meMarker.remove(); meMarker = null; } },
  onPos(p) {
    const ll = [p.coords.latitude, p.coords.longitude]; showMe(ll);
    const id = cellOf(...ll); if (id === this.cell) return;
    this.cell = id; if (S.view === 'alertas') renderAlertas(false);
    const n = recentReports().filter(r => r.cell === id).length, pc = D.pesq.cells[id], fol = Store.perfil.areas.includes(id);
    if (!n && !(pc && pc.n >= 2) && !fol) return;
    if (this.last[id] && Date.now() - this.last[id] < 30 * 60e3) return;
    this.last[id] = Date.now();
    const body = [n ? plural(n, 'relato recente', 'relatos recentes') : '', pc && pc.n >= 2 ? 'citada por ' + pc.n + ' mulheres na pesquisa' : '', fol && !n ? 'área que você acompanha' : ''].filter(Boolean).join(' · ');
    const near = S.apoio ? nearestApoio(ll, 1)[0] : null;
    toast('Atenção: ' + areaName(id) + ' · ' + body + (near ? ' · ajuda mais perto: ' + (near.p.curto || near.p.nome) + ', ' + fmtDist(near.d) : ''), 8000);
    try { navigator.vibrate && navigator.vibrate([220, 120, 220]); } catch (e) { /* opcional */ }
    try { if ('Notification' in window && Notification.permission === 'granted' && document.hidden) new Notification('Aurora: ' + areaName(id), { body }); } catch (e) { /* opcional */ }
  }
};
