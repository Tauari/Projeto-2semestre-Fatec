"""Classificação por palavras-chave: porte de ``heuristic``, ``findBairroInText`` e ``matchBairro``
(src/app.js:107-148 e 1259-1274), com as regex copiadas literalmente do legado.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from backend.models.vocabulario import TIPOS, periodo_da_hora
from backend.services.anonimizacao import anonimizar_texto
from backend.services.texto import aparar_js, comprimento_js, fatiar_js, normalizar, regex_js


@dataclass(frozen=True)
class Bairro:
    nome: str
    lat: float
    lng: float
    n: int
    key: str


def bairros_de_lista(lista) -> list[Bairro]:
    """Monta os bairros a partir de ``bairros`` do data.json (``[[nome, lat, lng, n], ...]``), como em app.js:107."""
    return [Bairro(nome=l[0], lat=l[1], lng=l[2], n=l[3], key=normalizar(l[0])) for l in lista]


def _por_nome(bairros) -> dict[str, Bairro]:
    return {b.nome: b for b in bairros}  # BYNAME: o último com o mesmo nome vence, como no Object.fromEntries


_RE_ESC = regex_js(r'[.*+?^${}()|[\]\\]', 'g')


def esc_re(s: str) -> str:
    """Porte de ``escRe``."""
    return _RE_ESC.sub(lambda m: '\\' + m.group(0), s)


@lru_cache(maxsize=4096)
def _re_bairro(key: str):
    return regex_js('(^|[^a-z0-9])' + esc_re(key) + '([^a-z0-9]|$)')


LANDMARKS = ((regex_js(r'\bunesp\b'), 'Bela Vista'), (regex_js(r'lago azul'), 'Vila Operária'), (regex_js(r'rodoviaria'), 'Jardim Claret'), (regex_js(r'estacao|jardim publico'), 'Centro'))
_RE_CENTRO = regex_js(r'\bcentro\b|zona central')


def encontrar_bairro_no_texto(texto, bairros) -> Bairro | None:
    t = ' ' + normalizar(texto) + ' '
    best = None
    for b in bairros:
        if comprimento_js(b.key) < 4:
            continue
        if _re_bairro(b.key).search(t) and (best is None or comprimento_js(b.key) > comprimento_js(best.key)):
            best = b
    if best is not None:
        return best
    for re_, nome in LANDMARKS:
        if re_.search(t):
            return _por_nome(bairros).get(nome)
    if _RE_CENTRO.search(t):
        return _por_nome(bairros).get('Centro')
    return None


def casar_bairro(nome, bairros) -> Bairro | None:
    k = aparar_js(normalizar(nome))
    if not k:
        return None
    for b in bairros:
        if b.key == k:
            return b
    for b in bairros:
        if k in b.key or b.key in k:
            return b
    return encontrar_bairro_no_texto(nome, bairros)


def _tipos(t: str) -> list[str]:
    return [x.id for x in TIPOS if x.kw and x.kw.search(t)][:3]


def classificar_tipos(texto) -> list[str]:
    """Os tipos cujas palavras-chave aparecem no texto, no máximo 3 (como em ``heuristic``)."""
    return _tipos(normalizar(texto))


@dataclass
class ExtracaoHeuristica:
    urgente: bool
    tipos: list[str]
    bairro: Bairro | None
    quando: str | None
    periodo: str | None
    descricao: str
    removidos: list[str]
    resposta: str = ''


_RE_HOJE = regex_js(r'\bhoje\b|agora ha pouco|agorinha|agora pouco')
_RE_ONTEM = regex_js(r'\bontem\b')
_RE_ANTES = regex_js(r'semana passada|mes passado|\bmeses\b|faz tempo|ano passado|ha \d+ semanas')
_RE_SEMANA = regex_js(r'(essa|esta|nesta) semana|anteontem|segunda|terca|quarta|quinta|sexta|sabado|domingo')
_RE_HORA = regex_js(r'\b(\d{1,2})\s?(?:h\b|hs\b|horas|:\d{2}|da (noite|manha|tarde))')
_RE_NOITE = regex_js(r'\bnoite\b')
_RE_MADRUGADA = regex_js(r'madrugada')
_RE_MEIA_NOITE = regex_js(r'meia[- ]?noite')
_RE_MANHA = regex_js(r'de manha|pela manha|\bmanha\b')
_RE_TARDE = regex_js(r'a tarde|de tarde|\btarde\b')
_RE_URGENTE = regex_js(r'(estou|to|estamos) (sendo seguid|em perigo|com medo agora)|socorro|me ajud(a|em) agora|agora mesmo')


def extrair_campos(texto, bairros) -> ExtracaoHeuristica:
    """Extração de campos sem IA (palavras-chave): porte fiel de ``heuristic``."""
    t = normalizar(texto)
    tipos = _tipos(t)
    quando = None
    if _RE_HOJE.search(t):
        quando = 'hoje'
    elif _RE_ONTEM.search(t):
        quando = 'ontem'
    elif _RE_ANTES.search(t):
        quando = 'antes'
    elif _RE_SEMANA.search(t):
        quando = 'semana'
    periodo = None
    hm = _RE_HORA.search(t)
    if hm:
        hr = int(hm.group(1))
        if (hm.group(2) == 'noite' or hm.group(2) == 'tarde' or _RE_NOITE.search(t)) and hr < 12 and hr >= 1:
            hr += 12
        if hr == 24:
            hr = 0
        if hr >= 0 and hr < 24:
            periodo = periodo_da_hora(hr)
    if not periodo:
        if _RE_MADRUGADA.search(t):
            periodo = 'madrugada'
        elif _RE_MEIA_NOITE.search(t):
            periodo = '22-00'
        elif _RE_MANHA.search(t):
            periodo = 'manha'
        elif _RE_TARDE.search(t):
            periodo = 'tarde'
    sc = anonimizar_texto(texto)
    urgente = bool(_RE_URGENTE.search(t))
    return ExtracaoHeuristica(urgente=urgente, tipos=tipos, bairro=encontrar_bairro_no_texto(texto, bairros), quando=quando,
                              periodo=periodo, descricao=fatiar_js(sc.texto, 300), removidos=sc.removidos, resposta='')
