"""Tira a descrição física de quem agrediu (altura, cor da pele, cabelo, barba, tatuagem, idade) e mantém o que ajuda outras
mulheres a reconhecer a situação: roupas, acessórios ("boina verde", "capuz cinza"), moto ou carro e a cor deles.

Só age onde dá para ter certeza de que é a pessoa: "homem alto" perde o "alto", "falou alto" não muda e "carro branco" fica.
Os mesmos padrões estão em ``frontend/shared/anonimizacao.js``.
"""
from __future__ import annotations

import re

_PESSOA = r'(?:homem|homens|cara|caras|rapaz|rapazes|sujeito|menino|garoto|mulher|pessoa|motorista|motoqueiro|suspeito|desconhecido|senhor)'
_TRACO = (r'(?:alto|alta|baixo|baixa|baixinho|magro|magra|magrelo|gordo|gorda|gordinho|forte|musculoso|careca|calvo|barbudo|loiro|loira|'
          r'moreno|morena|ruivo|ruiva|negro|negra|branco|branca|pardo|parda|jovem|velho|idoso|novinho)')
_PARTE = r'(?:cabelos?|barba|bigode|tatuagem|tatuagens|cicatriz|cicatrizes|olhos|pele)'
_DETALHE = (r'(?:muito\s+)?(?:longos?|curtos?|compridos?|crespos?|cacheados?|lisos?|pretos?|castanhos?|claros?|escuros?|loiros?|ruivos?|grisalhos?|'
            r'azuis|verdes|branca|negra|clara|escura|grande|cheia|rala|(?:no|na|nos|nas|do|da)\s+[a-zç]+)')

# "homem alto e magro" -> "homem"
_RE_TRACO = re.compile(r'\b(' + _PESSOA + r')((?:\s*(?:,|e)?\s*(?:muito\s+|bem\s+)?' + _TRACO + r'\b)+)', re.I)
# "com tatuagem no braço", "de cabelo preto curto"
_RE_PARTE = re.compile(r',?\s*(?:(?:de|com)\s+)?' + _PARTE + r'(?:\s+' + _DETALHE + r'){0,3}\b', re.I)
# "de uns 30 anos"
_RE_IDADE = re.compile(r',?\s*(?:de\s+)?(?:uns\s+|umas\s+|aproximadamente\s+|cerca\s+de\s+)?\d{1,2}\s+anos(?:\s+de\s+idade)?\b', re.I)
# arruma o que sobra: "homem e de boina" -> "homem de boina"; "cara, e camiseta azul" -> "cara com camiseta azul"
_RE_E_DE = re.compile(r'\b(' + _PESSOA + r')\s*,?\s*e\s+(de|com)\b', re.I)
_RE_E = re.compile(r'\b(' + _PESSOA + r')\s*,?\s*e\s+(?!(?:de|com)\b)', re.I)


def tirar_fisico(texto: str) -> tuple[str, bool]:
    """(texto sem a descrição física, se tirou alguma coisa)."""
    t = _RE_TRACO.sub(lambda m: m.group(1), texto)
    t = _RE_PARTE.sub('', t)
    t = _RE_IDADE.sub('', t)
    if t == texto:
        return texto, False
    t = _RE_E_DE.sub(lambda m: m.group(1) + ' ' + m.group(2), t)
    t = _RE_E.sub(lambda m: m.group(1) + ' com ', t)
    t = re.sub(r'\s+([,.;!?])', r'\1', t)
    t = re.sub(r',\s*([,.;])', r'\1', t)
    return re.sub(r'\s{2,}', ' ', t).strip(), True
