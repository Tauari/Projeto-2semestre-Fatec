"""Vocabulário do relato (porte de src/app.js:59-83). Dados de domínio, sem Pydantic.

As regex ``kw`` são cópias literais das do legado e rodam sobre o texto já normalizado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from backend.services.texto import regex_js


@dataclass(frozen=True)
class TipoSituacao:
    id: str
    label: str
    long: str | None
    kw: re.Pattern | None


@dataclass(frozen=True)
class Periodo:
    id: str
    label: str
    long: str
    inicio: int
    fim: int


TIPOS: tuple[TipoSituacao, ...] = (
    TipoSituacao('assedio', 'Assédio verbal', None, regex_js(r'assedi|cantada|mexeu comigo|falou (coisa|besteira|gracinha)|gracinha|obscen|buzin')),
    TipoSituacao('perseguicao', 'Perseguição', 'Perseguição / me seguiram', regex_js(r'segui(u|ram|ndo|da)|persegu|atras de mim|me acompanh')),
    TipoSituacao('abordagem', 'Abordagem indesejada', None, regex_js(r'abord|chegou em mim|puxou conversa|tentou (falar|conversar|pegar)|insist')),
    TipoSituacao('intimidacao', 'Intimidação', 'Encarar ou intimidar', regex_js(r'encar|olhando|observ|intimid|me medindo')),
    TipoSituacao('exposicao', 'Exposição sexual', None, regex_js(r'exposi|mostrou (as partes|o penis|o orgao)|se masturb|nudez|pelado')),
    TipoSituacao('roubo', 'Roubo ou furto', None, regex_js(r'roub|furt|assalt|levaram|puxaram (meu|minha)')),
    TipoSituacao('violencia', 'Violência física', None, regex_js(r'agred|bateu|empurr|soco|tapa|violencia fisica|me pegou|agarr')),
    TipoSituacao('veiculo', 'Situação com veículo', None, regex_js(r'\bcarro\b|\bmoto\b|veiculo|\buber\b|\b99\b|motorista|\bvan\b|caminhao')),
    TipoSituacao('ambiente', 'Rua escura ou deserta', None, regex_js(r'escur|desert|sem luz|iluminac|apagad|vazi[ao]')),
    TipoSituacao('outra', 'Outra situação', None, None),
)
TIPOS_POR_ID: dict[str, TipoSituacao] = {t.id: t for t in TIPOS}

PERIODOS: tuple[Periodo, ...] = (
    Periodo('manha', 'Manhã', 'Manhã (6h–12h)', 6, 12),
    Periodo('tarde', 'Tarde', 'Tarde (12h–18h)', 12, 18),
    Periodo('18-20', '18–20h', '18h–20h', 18, 20),
    Periodo('20-22', '20–22h', '20h–22h', 20, 22),
    Periodo('22-00', '22–00h', '22h–00h', 22, 24),
    Periodo('madrugada', 'Madrugada', 'Madrugada (0h–6h)', 0, 6),
)
PERIODOS_POR_ID: dict[str, Periodo] = {p.id: p for p in PERIODOS}

QUANDO: dict[str, str] = {'hoje': 'hoje', 'ontem': 'ontem', 'semana': 'nesta semana', 'antes': 'há mais de uma semana'}

ORIGENS_RELATO = ('chat', 'chat-ia')


def periodo_da_hora(h: int) -> str:
    """Porte de ``periodOfHour``."""
    for p in PERIODOS:
        if h >= p.inicio and h < p.fim:
            return p.id
    return PERIODOS[5].id


class TipoEvidencia(str, Enum):
    RELATO_COMUNIDADE = 'relato_comunidade'
    DADO_OFICIAL = 'dado_oficial'
    PERCEPCAO = 'percepcao'
    CLASSIFICACAO_AUTOMATICA = 'classificacao_automatica'
    ANALISE_IA = 'analise_ia'


def vocabulario_publico() -> dict:
    """O bloco ``vocabulario`` de ``GET /config``, na ordem do legado."""
    return {
        'tipos': [{'id': t.id, 'label': t.label, 'long': t.long} for t in TIPOS],
        'periodos': [{'id': p.id, 'label': p.label, 'long': p.long, 'from': p.inicio, 'to': p.fim} for p in PERIODOS],
        'quando': dict(QUANDO),
    }
