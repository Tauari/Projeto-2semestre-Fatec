"""Tira o número da casa que o ``scrub`` do legado deixava passar: "endereço 1532", "rua das Flores 123", "Rua 7, 45".

Fica fora de ``anonimizacao.py`` porque aquele arquivo é cópia literal do legado e é comparado com ele nos testes.
Os mesmos padrões estão em ``frontend/shared/anonimizacao.js``. O número da rua ("rua 2", "avenida 29") continua: só
o número do imóvel sai.
"""
from __future__ import annotations

import re

from backend.services.anonimizacao import ResultadoAnonimizacao, anonimizar_texto
from backend.services.fisico import tirar_fisico

_PALAVRA = r'[A-Za-zÀ-ÿ]+'
_RUA = r'(?:rua|r\.|avenida|av\.|travessa|alameda|estrada|rodovia|pra[çc]a)'
# endereço 1532 / residência: 45
_RE_ROTULO = re.compile(r'\b(?:endere[çc]o|end\.|resid[eê]ncia|moradia)\s?:?\s?\d{1,5}\b', re.I)
# rua das Flores 123 / Av. Brasil, 45
_RE_RUA_NOME = re.compile(r'\b(' + _RUA + r'\s+(?:' + _PALAVRA + r'\s+){0,3}' + _PALAVRA + r')\s*,?\s+\d{2,5}\b', re.I)
# rua 7, 45 / avenida 29 123
_RE_RUA_NUM = re.compile(r'\b(' + _RUA + r'\s+\d{1,3})\s*,?\s+\d{2,5}\b', re.I)


def anonimizar_completo(texto: str | None) -> ResultadoAnonimizacao:
    base = anonimizar_texto(texto)
    t, removidos = base.texto, list(base.removidos)

    def troca(m):
        if 'número de endereço' not in removidos:
            removidos.append('número de endereço')
        return m.group(1) + ' [número]' if m.groups() else '[número]'
    for re_ in (_RE_ROTULO, _RE_RUA_NOME, _RE_RUA_NUM):
        t = re_.sub(troca, t)
    t, tirou = tirar_fisico(t)
    if tirou:
        removidos.append('descrição física')
    return ResultadoAnonimizacao(texto=t, removidos=removidos)
