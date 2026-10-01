"""Schemas Pydantic comuns: envelopes dos conjuntos de dados, configuração pública, resumo, identidade e erros."""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel

_RE_SUBSTITUTO = re.compile('[\ud800-\udfff]')


def texto_bem_formado(s: str) -> str:
    """Troca os substitutos UTF-16 soltos por U+FFFD, que é o que o navegador mostra no lugar deles.

    O ``slice`` do JS (e o ``fatiar_js``) pode cortar um emoji ao meio, e um substituto solto não pode ser
    gravado no banco nem escrito em JSON UTF-8.
    """
    if not _RE_SUBSTITUTO.search(s):
        return s
    return s.encode('utf-16-le', 'surrogatepass').decode('utf-16-le', 'replace')


class Saude(BaseModel):
    status: str
    versao: str


class Identidade(BaseModel):
    autenticado: bool
    papeis: list[str]


class Erro(BaseModel):
    detail: str


class ItemErro(BaseModel):
    campo: str
    mensagem: str
    tipo: str


class ErroValidacao(BaseModel):
    detail: str
    erros: list[ItemErro]


class ConjuntoResumo(BaseModel):
    chave: str
    tipo_evidencia: str
    titulo: str
    periodo: str | None
    fonte: str
    gerado_em: str | None


class ListaConjuntos(BaseModel):
    conjuntos: list[ConjuntoResumo]


class ConjuntoDetalhe(ConjuntoResumo):
    avisos: list[str]
    dados: dict[str, Any]


class Geografia(BaseModel):
    tipo: str
    gerado_em: str | None
    fonte: str
    notas: list[str]
    dados: dict[str, Any]


class RedeApoio(BaseModel):
    tipo: str
    atualizado: str | None
    nota: str | None
    dados: dict[str, Any]


class ConfiguracaoRelatos(BaseModel):
    janela_dias: int
    tipos_max: int
    texto_max: int
    precisao_criado: str  # "exata", "hora" ou "dia": como o servidor arredonda a hora de envio


class ConfiguracaoIA(BaseModel):
    provedor: str
    usa_modelo: bool


class ConfiguracaoPublica(BaseModel):
    versao_api: str
    vocabulario: dict[str, Any]
    relatos: ConfiguracaoRelatos
    ia: ConfiguracaoIA
    conjuntos_padrao: dict[str, str]
    modulos: dict[str, bool]


class ResumoRelatos(BaseModel):
    tipo_evidencia: str
    janela_dias: int
    total: int
    por_tipo: dict[str, int]
    por_periodo: dict[str, int]
    por_celula: dict[str, int]
    aviso: str


class ResumoOficial(BaseModel):
    chave: str
    titulo: str
    periodo: str | None
    tipo_evidencia: str
    total: dict[str, Any]


class ResumoPercepcao(BaseModel):
    chave: str
    titulo: str
    tipo_evidencia: str
    respostas: int | None
    de: str | None
    ate: str | None


class ResumoClassificacoes(BaseModel):
    tipo_evidencia: str
    total: int
    por_provedor: dict[str, int]


class ResumoAnaliseIA(BaseModel):
    tipo_evidencia: str
    implementado: bool


class ResumoDashboard(BaseModel):
    relatos_comunidade: ResumoRelatos
    dados_oficiais: list[ResumoOficial]
    percepcao: list[ResumoPercepcao]
    classificacoes_automaticas: ResumoClassificacoes
    analise_ia: ResumoAnaliseIA


_MENSAGENS = {
    'missing': 'Campo obrigatório.',
    'string_type': 'Deve ser um texto.',
    'list_type': 'Deve ser uma lista.',
    'bool_type': 'Deve ser verdadeiro ou falso.',
    'bool_parsing': 'Deve ser verdadeiro ou falso.',
    'int_type': 'Deve ser um número inteiro.',
    'int_parsing': 'Deve ser um número inteiro.',
    'int_from_float': 'Deve ser um número inteiro.',
    'greater_than_equal': 'Deve ser no mínimo {ge}.',
    'less_than_equal': 'Deve ser no máximo {le}.',
    'string_too_short': 'Texto curto demais (mínimo de {min_length} caracteres).',
    'string_too_long': 'Texto longo demais (máximo de {max_length} caracteres).',
    'json_invalid': 'O corpo da requisição não é um JSON válido.',
    'model_attributes_type': 'O corpo da requisição deve ser um objeto JSON.',
    'model_type': 'O corpo da requisição deve ser um objeto JSON.',
    'dict_type': 'Deve ser um objeto JSON.',
    'literal_error': 'Valor não permitido.',
}
# erros levantados pelos nossos validadores, já com a mensagem em português
_PROPRIOS = {'tipos_invalidos', 'celula_invalida', 'texto_longo'}
_LOCAIS = {'body', 'query', 'path', 'header', 'cookie'}


def traduzir_erros(erros) -> list[dict]:
    """Os erros de validação do Pydantic em português, sem ecoar o valor enviado (que pode ser o texto do relato)."""
    saida = []
    for e in erros:
        loc = list(e.get('loc') or ())
        if loc and loc[0] in _LOCAIS:
            loc = loc[1:]
        tipo = e.get('type', '')
        campo = 'corpo' if tipo == 'json_invalid' or not loc else '.'.join(str(x) for x in loc)
        if tipo in _PROPRIOS:
            mensagem = e.get('msg', '')
        elif tipo == 'missing' and campo == 'corpo':
            mensagem = 'O corpo da requisição é obrigatório.'
        elif tipo == 'string_too_short' and (e.get('ctx') or {}).get('min_length') == 1:
            mensagem = 'O texto não pode ficar vazio.'
        else:
            try:
                mensagem = _MENSAGENS[tipo].format(**(e.get('ctx') or {}))
            except (KeyError, IndexError, ValueError):
                mensagem = 'Valor inválido.'
        saida.append({'campo': campo, 'mensagem': mensagem, 'tipo': tipo})
    return saida
