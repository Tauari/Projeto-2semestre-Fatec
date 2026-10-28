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
  // número do imóvel depois de "endereço" ou do nome da rua; o número da rua ("rua 2", "avenida 29") fica. Mesmos padrões de backend/services/enderecos.py
  const RUA = String.raw`(?:rua|r\.|avenida|av\.|travessa|alameda|estrada|rodovia|pra[çc]a)`, PAL = '[A-Za-zÀ-ÿ]+';
  rep(/(?:^|\s)(?:endere[çc]o|end\.|resid[eê]ncia|moradia)\s?:?\s?\d{1,5}(?![\d\w])/gi, 'número de endereço', ' [número]');
  for (const re of [new RegExp(String.raw`(^|\s)(${RUA}\s+(?:${PAL}\s+){0,3}${PAL})\s*,?\s+\d{2,5}(?![\d\w])`, 'gi'), new RegExp(String.raw`(^|\s)(${RUA}\s+\d{1,3})\s*,?\s+\d{2,5}(?![\d\w])`, 'gi')])
    t = t.replace(re, (m, p0, p1) => { removed.add('número de endereço'); return p0 + p1 + ' [número]'; });
  // descrição física de quem agrediu (altura, cor da pele, cabelo, tatuagem, idade): sai. Roupa, acessório e veículo ficam. Mesmos padrões de backend/services/fisico.py
  const PES = String.raw`(?:homem|homens|cara|caras|rapaz|rapazes|sujeito|menino|garoto|mulher|pessoa|motorista|motoqueiro|suspeito|desconhecido|senhor)`;
  const TRA = String.raw`(?:alto|alta|baixo|baixa|baixinho|magro|magra|magrelo|gordo|gorda|gordinho|forte|musculoso|careca|calvo|barbudo|loiro|loira|moreno|morena|ruivo|ruiva|negro|negra|branco|branca|pardo|parda|jovem|velho|idoso|novinho)`;
  const PAR = String.raw`(?:cabelos?|barba|bigode|tatuagem|tatuagens|cicatriz|cicatrizes|olhos|pele)`;
  const DET = String.raw`(?:muito\s+)?(?:longos?|curtos?|compridos?|crespos?|cacheados?|lisos?|pretos?|castanhos?|claros?|escuros?|loiros?|ruivos?|grisalhos?|azuis|verdes|branca|negra|clara|escura|grande|cheia|rala|(?:no|na|nos|nas|do|da)\s+[a-zç]+)`;
  const antesFisico = t;
  t = t.replace(new RegExp(String.raw`\b(${PES})((?:\s*(?:,|e)?\s*(?:muito\s+|bem\s+)?${TRA}\b)+)`, 'gi'), (m, p) => p)
    .replace(new RegExp(String.raw`,?\s*(?:(?:de|com)\s+)?${PAR}(?:\s+${DET}){0,3}\b`, 'gi'), '')
    .replace(/,?\s*(?:de\s+)?(?:uns\s+|umas\s+|aproximadamente\s+|cerca\s+de\s+)?\d{1,2}\s+anos(?:\s+de\s+idade)?\b/gi, '');
  if (t !== antesFisico) {
    removed.add('descrição física');
    t = t.replace(new RegExp(String.raw`\b(${PES})\s*,?\s*e\s+(de|com)\b`, 'gi'), (m, p, q) => p + ' ' + q)
      .replace(new RegExp(String.raw`\b(${PES})\s*,?\s*e\s+(?!(?:de|com)\b)`, 'gi'), (m, p) => p + ' com ')
      .replace(/\s+([,.;!?])/g, '$1').replace(/,\s*([,.;])/g, '$1');
  }
  t = t.replace(/((?:chamad[oa]|se chama|nome (?:é|e|dele|dela)|conhecid[oa] como|apelid[oa](?: de)?)\s+)([A-ZÀ-Ý][\wÀ-ÿ]+(?:\s[A-ZÀ-Ý][\wÀ-ÿ]+)?)/g,
    (m, p1) => { removed.add('nome'); return p1 + '[nome]'; });
  return { text: t.replace(/\s{2,}/g, ' ').trim(), removed: [...removed] };
}
