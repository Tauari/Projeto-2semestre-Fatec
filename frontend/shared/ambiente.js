/* onde o app está rodando */
export const HAS_CLAUDE = !!(window.claude && typeof window.claude.use === 'function');
export const STANDALONE = !HAS_CLAUDE;
