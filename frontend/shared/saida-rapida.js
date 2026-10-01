/* sair rápido */
import { $ } from './dom.js';
import { STANDALONE } from './ambiente.js';
import { S } from './estado.js';
import { Chat, openChat, closeChat } from '../chatbot/chat.js';
import { closeSobre } from './sobre.js';
import { closePanel } from '../mapa/painel-area.js';
import { stopPick } from '../mapa/selecao.js';
import { clearRoute } from '../mapa/trajeto.js';

export function quickExit() {
  try { Chat.start(); closeSobre(); closeChat(); closePanel(); } catch (e) { /* segue */ }
  $('#cover').hidden = false; document.title = 'Lista de compras';
  if (STANDALONE) { try { window.location.replace('https://www.google.com/search?q=previs%C3%A3o+do+tempo'); } catch (e) { /* fica na capa */ } }
}
let lastEsc = 0;
/* Esc fecha o que estiver aberto; Esc duas vezes seguidas sai rápido */
export function instalarAtalhos() {
  document.addEventListener('keydown', e => {
    if (e.key !== 'Escape') return;
    const now = Date.now();
    if (now - lastEsc < 700) { quickExit(); lastEsc = 0; return; }
    lastEsc = now;
    if (!$('#sobre').hidden) closeSobre();
    else if (S.pick) { stopPick(); openChat(); }
    else if (S.routeMode) clearRoute();
    else if (!$('#panel').hidden) closePanel();
  });
}
