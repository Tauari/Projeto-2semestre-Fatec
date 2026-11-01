"""Alerta padronizado de um relato, como o aviso do Waze ("Acidente na rodovia"): um título fixo por tipo de situação.

O título não repete o texto da usuária; ele diz só o que a área tem de novo. O frontend tem os mesmos títulos em
``frontend/relatos/alerta.js`` (um teste confere que os dois batem).
"""
from __future__ import annotations

ROTULOS: dict[str, str] = {
    'assedio': 'Potencial assediador na área',
    'perseguicao': 'Possível perseguidor na área',
    'abordagem': 'Abordagem indesejada na área',
    'intimidacao': 'Intimidação relatada na área',
    'exposicao': 'Exposição sexual relatada na área',
    'roubo': 'Roubo ou furto na área',
    'violencia': 'Violência física relatada na área',
    'veiculo': 'Situação com veículo na área',
    'ambiente': 'Rua escura ou deserta na área',
    'outra': 'Situação relatada na área',
}

# se o relato tem mais de um tipo, o título vem do mais grave primeiro
PRIORIDADE: tuple[str, ...] = ('violencia', 'exposicao', 'perseguicao', 'assedio', 'abordagem', 'intimidacao', 'roubo',
                               'veiculo', 'ambiente', 'outra')

# "rua escura ou deserta" é uma condição do lugar, não algo acontecendo agora: não vira alerta ao vivo nem notificação
SEM_ALERTA: frozenset[str] = frozenset({'ambiente'})


def tipo_do_alerta(tipos: list[str]) -> str | None:
    """O tipo que dá o título do alerta, ou ``None`` se o relato só tem tipos que não geram alerta."""
    for t in PRIORIDADE:
        if t in tipos and t not in SEM_ALERTA:
            return t
    return None


def titulo_alerta(tipos: list[str]) -> str | None:
    t = tipo_do_alerta(tipos)
    return ROTULOS[t] if t else None
