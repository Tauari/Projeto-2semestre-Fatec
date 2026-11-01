/* onde o app está rodando */
export const HAS_CLAUDE = !!(window.claude && typeof window.claude.use === 'function');
export const STANDALONE = !HAS_CLAUDE;
/* dentro do app de celular (Expo), o app nativo cria window.AuroraApp com o token das notificações */
export const noApp = () => !!(window.AuroraApp && window.AuroraApp.plataforma);
export const tokenPush = () => (window.AuroraApp && typeof window.AuroraApp.pushToken === 'string' ? window.AuroraApp.pushToken : null);
/* versão do app de celular: 2 em diante sabe pedir ao Android a permissão de localização */
export const versaoApp = () => (window.AuroraApp && Number(window.AuroraApp.versao)) || 0;
/* No app, o Android precisa liberar a localização para o app antes de a página usá-la, então a página pede ao app nativo
   (mensagem 'pedir-localizacao') e espera a resposta. No navegador comum é ele mesmo quem pergunta. */
export function liberarLocalizacao() {
  if (!noApp()) return Promise.resolve(true);
  if (window.AuroraApp.localizacao === true) return Promise.resolve(true);
  if (versaoApp() < 2 || !window.ReactNativeWebView) return Promise.resolve(false); // app antigo: não sabe pedir
  return new Promise(resolve => {
    const fim = e => { window.removeEventListener('aurora-localizacao', fim); resolve(!!(e.detail && e.detail.ok)); };
    window.addEventListener('aurora-localizacao', fim);
    window.ReactNativeWebView.postMessage(JSON.stringify({ tipo: 'pedir-localizacao' }));
  });
}
export const erroLocalizacao = () => !noApp() ? 'Não consegui acessar sua localização. Verifique a permissão do navegador.'
  : versaoApp() < 2 ? 'Para usar a localização, instale a versão nova do app Aurora.'
  : 'Não consegui acessar sua localização. Libere a localização do app Aurora nas configurações do Android e ligue o GPS do celular.';
