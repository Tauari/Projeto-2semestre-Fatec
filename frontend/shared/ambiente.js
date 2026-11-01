/* onde o app está rodando */
export const HAS_CLAUDE = !!(window.claude && typeof window.claude.use === 'function');
export const STANDALONE = !HAS_CLAUDE;
/* dentro do app de celular (Expo), o app nativo cria window.AuroraApp com o token das notificações */
export const noApp = () => !!(window.AuroraApp && window.AuroraApp.plataforma);
export const tokenPush = () => (window.AuroraApp && typeof window.AuroraApp.pushToken === 'string' ? window.AuroraApp.pushToken : null);
