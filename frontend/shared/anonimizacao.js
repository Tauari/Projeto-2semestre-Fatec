/* texto: tira dados pessoais */
export function scrub(s) {
  let t = String(s || '');
  const removed = new Set();
  const rep = (re, label, token) => { t = t.replace(re, () => { removed.add(label); return token; }); };
  rep(/[\w.+-]+@[\w-]+\.[\w.-]+/g, 'e-mail', '[e-mail]');
  rep(/\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g, 'documento', '[documento]');
  rep(/(\+?55\s?)?\(?\b\d{2}\)?\s?9?\d{4}[-\s.]?\d{4}\b/g, 'telefone', '[telefone]');
  rep(/\b9?\d{4}-\d{4}\b/g, 'telefone', '[telefone]');
  rep(/\b[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}\b/g, 'placa', '[placa]');
  rep(/(^|\s)@[A-Za-z0-9_.]{3,}/g, 'perfil de rede social', ' [perfil]');
  rep(/\b(n[ºo°]\.?|n[uú]mero|casa|apto|apartamento|ap\.)\s?\d{1,5}\b/gi, 'número de endereço', '[número]');
  t = t.replace(/((?:chamad[oa]|se chama|nome (?:é|e|dele|dela)|conhecid[oa] como|apelid[oa](?: de)?)\s+)([A-ZÀ-Ý][\wÀ-ÿ]+(?:\s[A-ZÀ-Ý][\wÀ-ÿ]+)?)/g,
    (m, p1) => { removed.add('nome'); return p1 + '[nome]'; });
  return { text: t.replace(/\s{2,}/g, ' ').trim(), removed: [...removed] };
}
