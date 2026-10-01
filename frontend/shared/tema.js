/* tema claro ou escuro */
export const mq = matchMedia('(prefers-color-scheme: dark)');
export function isDark() { const t = document.documentElement.getAttribute('data-theme'); return t ? t === 'dark' : mq.matches; }
