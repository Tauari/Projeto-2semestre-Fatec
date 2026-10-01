"""Funções de texto com a mesma semântica do JavaScript do legado (src/app.js).

O porte das regras de texto precisa dar o mesmo resultado que o navegador: o JS conta o tamanho das
strings em unidades UTF-16 e as regex do legado não usam a flag ``u`` (``\\w``, ``\\d`` e ``\\b`` só
ASCII; ``\\s`` com os espaços Unicode). ``regex_js`` compila uma regex escrita para o JS com essa
semântica, para que as regras possam ser copiadas literalmente do ``src/app.js``.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# \s do JS: \t \n \v \f \r, espaços Unicode (Zs), U+2028, U+2029 e U+FEFF.
# O \s do Python é outro conjunto (tem \x1c-\x1f e \x85, não tem U+FEFF).
_CLASSE_S_JS = (r'\t\n\x0b\x0c\r \xa0\U00001680\U00002000-\U0000200a\U00002028\U00002029'
                r'\U0000202f\U0000205f\U00003000\U0000feff')
S_JS = '[' + _CLASSE_S_JS + ']'
ESPACOS_JS = ('\t\n\x0b\x0c\r \xa0\U00001680' + ''.join(map(chr, range(0x2000, 0x200b)))
              + '\U00002028\U00002029\U0000202f\U0000205f\U00003000\U0000feff')
# o . do JS (sem a flag s) não casa com nenhum fim de linha
_PONTO_JS = r'[^\n\r\U00002028\U00002029]'


def comprimento_js(s: str) -> int:
    """``s.length`` do JS (unidades UTF-16)."""
    return len(s.encode('utf-16-le', 'surrogatepass')) // 2


def fatiar_js(s: str, n: int) -> str:
    """``s.slice(0, n)`` do JS. Se o corte cair no meio de um par substituto, sobra o substituto solto."""
    if 0 <= n and 2 * len(s) <= n:
        return s
    b = s.encode('utf-16-le', 'surrogatepass')
    total = len(b) // 2
    if n < 0:
        n = max(total + n, 0)
    if n >= total:
        return s
    return b[:2 * n].decode('utf-16-le', 'surrogatepass')


def aparar_js(s: str) -> str:
    """``s.trim()`` do JS."""
    return s.strip(ESPACOS_JS)


_CANONICOS_BMP: dict[str, list[str]] | None = None


def _canonico_i(c: str) -> str:
    # Canonicalize da flag i sem u (ECMA-262): toUpperCase de uma unidade só, sem trocar não ASCII por ASCII
    u = c.upper()
    if len(u) != 1 or ord(u) > 0xFFFF or (ord(c) >= 128 and ord(u) < 128):
        return c
    return u


@lru_cache(maxsize=None)
def _equivalentes_i(c: str) -> str:
    global _CANONICOS_BMP
    if _CANONICOS_BMP is None:
        mapa: dict[str, list[str]] = {}
        for x in range(0x10000):
            mapa.setdefault(_canonico_i(chr(x)), []).append(chr(x))
        _CANONICOS_BMP = mapa
    return ''.join(_CANONICOS_BMP.get(_canonico_i(c), [c]))


def regex_js(fonte: str, flags: str = '') -> re.Pattern:
    """Compila uma regex do JS (sem a flag u) com a mesma semântica no Python.

    Traduz ``\\s``, ``\\S``, ``$`` e ``.`` para os conjuntos do JS e usa ``re.ASCII`` (``\\w``, ``\\d``
    e ``\\b`` ASCII, como no JS). Com a flag ``i``, as letras ASCII ficam com o ``re.IGNORECASE`` do
    modo ASCII e cada letra não ASCII vira a lista das letras que o JS considera iguais (ex.: ú/Ú).
    """
    for f in flags:
        if f not in 'gi':
            raise ValueError(f'flag de regex JS não suportada: {f!r}')
    ic = 'i' in flags
    saida: list[str] = []
    classe = False
    k = 0
    while k < len(fonte):
        c = fonte[k]
        if c == '\\':
            if k + 1 >= len(fonte):
                raise ValueError('regex termina com \\')
            d = fonte[k + 1]
            if d == 's':
                if classe and fonte[k + 2:k + 3] == '-' and fonte[k + 3:k + 4] != ']':
                    raise ValueError('\\s seguido de intervalo dentro de classe')
                saida.append(_CLASSE_S_JS if classe else S_JS)
            elif d == 'S':
                if classe:
                    raise ValueError('\\S dentro de classe não é suportado')
                saida.append('[^' + _CLASSE_S_JS + ']')
            else:
                saida.append(c + d)
            k += 2
            continue
        if classe:
            if c == ']':
                classe = False
                saida.append(c)
            elif ic and ord(c) >= 128:
                if fonte[k - 1] == '-' or fonte[k + 1:k + 2] == '-':
                    raise ValueError('intervalo com letra não ASCII e flag i não é suportado')
                saida.append(_equivalentes_i(c))
            else:
                saida.append(c)
        elif c == '[':
            classe = True
            saida.append(c)
        elif c == '$':
            saida.append(r'\Z')
        elif c == '.':
            saida.append(_PONTO_JS)
        elif ic and ord(c) >= 128:
            eq = _equivalentes_i(c)
            saida.append(eq if len(eq) == 1 else '[' + eq + ']')
        else:
            saida.append(c)
        k += 1
    return re.compile(''.join(saida), re.ASCII | (re.IGNORECASE if ic else 0))


_RE_MARCAS = regex_js('[\U00000300-\U0000036f]', 'g')


def normalizar(s) -> str:
    """Porte de ``norm`` (app.js:37): tira os acentos e passa para minúsculas."""
    return _RE_MARCAS.sub('', unicodedata.normalize('NFD', str(s or ''))).lower()
