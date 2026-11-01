/* notificações no celular: dentro do app instalado (Expo), o app nativo guarda o token do aparelho em window.AuroraApp.
   Aqui o token e as áreas que a pessoa acompanha vão para o servidor, que avisa quando um relato novo cai numa delas. */
import { apiPost } from './api.js';
import { Store } from './store.js';
import { tokenPush } from './ambiente.js';

const AREAS_MAX = 40;
let enviado = '';

async function sincronizar() {
  const token = tokenPush();
  if (!token || Store.mode !== 'api' || !Store.ready) return;
  const areas = Store.perfil.areas.slice(0, AREAS_MAX);
  const assinatura = token + '|' + areas.join(',');
  if (assinatura === enviado) return;
  try { await apiPost('/push/dispositivos', { token, areas }); enviado = assinatura; } catch (e) { /* tenta de novo na próxima mudança */ }
}

export function iniciarPush() {
  Store.on(sincronizar);
  window.addEventListener('aurora-push-token', sincronizar); // o app nativo avisa quando o token chega
  sincronizar();
}
