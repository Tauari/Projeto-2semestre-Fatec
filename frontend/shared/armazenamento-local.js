/* armazenamento no aparelho (localStorage), com o mesmo prefixo do legado */
export const LS = {
  get(k, d) { try { const v = localStorage.getItem('aurora.v1.' + k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
  set(k, v) { try { localStorage.setItem('aurora.v1.' + k, JSON.stringify(v)); } catch (e) { /* armazenamento indisponível */ } }
};
