"""Tira dados pessoais do texto: porte fiel de ``scrub`` (src/app.js:151-165).

As regex são cópias literais das do legado, compiladas com a semântica do JS (ver ``texto.regex_js``).
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.services.texto import aparar_js, regex_js


@dataclass
class ResultadoAnonimizacao:
    texto: str
    removidos: list[str]


_REGRAS = (
    (regex_js(r'[\w.+-]+@[\w-]+\.[\w.-]+', 'g'), 'e-mail', '[e-mail]'),
    (regex_js(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', 'g'), 'documento', '[documento]'),
    (regex_js(r'(\+?55\s?)?\(?\b\d{2}\)?\s?9?\d{4}[-\s.]?\d{4}\b', 'g'), 'telefone', '[telefone]'),
    (regex_js(r'\b9?\d{4}-\d{4}\b', 'g'), 'telefone', '[telefone]'),
    (regex_js(r'\b[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}\b', 'g'), 'placa', '[placa]'),
    (regex_js(r'(^|\s)@[A-Za-z0-9_.]{3,}', 'g'), 'perfil de rede social', ' [perfil]'),
    (regex_js(r'\b(n[ºo°]\.?|n[uú]mero|casa|apto|apartamento|ap\.)\s?\d{1,5}\b', 'gi'), 'número de endereço', '[número]'),
)
_RE_NOME = regex_js(r'((?:chamad[oa]|se chama|nome (?:é|e|dele|dela)|conhecid[oa] como|apelid[oa](?: de)?)\s+)([A-ZÀ-Ý][\wÀ-ÿ]+(?:\s[A-ZÀ-Ý][\wÀ-ÿ]+)?)', 'g')
_RE_ESPACOS = regex_js(r'\s{2,}', 'g')


def anonimizar_texto(texto: str | None) -> ResultadoAnonimizacao:
    t = str(texto or '')
    removed: dict[str, None] = {}  # como o Set do JS: sem repetição, na ordem em que apareceu

    def rep(re_, label, token):
        nonlocal t

        def troca(m):
            removed[label] = None
            return token
        t = re_.sub(troca, t)

    for re_, label, token in _REGRAS:
        rep(re_, label, token)

    def troca_nome(m):
        removed['nome'] = None
        return m.group(1) + '[nome]'
    t = _RE_NOME.sub(troca_nome, t)
    return ResultadoAnonimizacao(texto=aparar_js(_RE_ESPACOS.sub(' ', t)), removidos=list(removed))
