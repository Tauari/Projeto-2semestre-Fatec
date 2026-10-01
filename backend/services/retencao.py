"""Política de retenção dos relatos (roda na inicialização do servidor e a cada relato novo).

decisão pendente com o Observatório: por quanto tempo guardar os relatos. Com ``relatos_retencao_dias=None``
(padrão, o comportamento atual) nenhum relato é apagado por idade. Com um número de dias, os relatos mais
antigos que isso são apagados junto com as classificações ligadas a eles.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import DIA_MS, RepositorioRelatos, instante_atual_ms


def limite_retencao_ms(cfg: Configuracoes, agora_ms: int) -> int | None:
    """Instante antes do qual um relato está fora do prazo (``None``: sem prazo). As leituras também respeitam."""
    dias = cfg.relatos_retencao_dias
    return None if dias is None else agora_ms - dias * DIA_MS


def aplicar_retencao(sessao: Session, agora_ms: int | None = None) -> int:
    """Apaga os relatos fora do prazo de retenção e devolve quantos apagou (0 se não houver prazo)."""
    dias = obter_configuracoes().relatos_retencao_dias
    if dias is None:
        return 0
    agora = instante_atual_ms() if agora_ms is None else agora_ms
    try:
        apagados = RepositorioRelatos(sessao).apagar_anteriores(agora - dias * DIA_MS)
        sessao.commit()
    except Exception:
        sessao.rollback()
        raise
    return apagados
