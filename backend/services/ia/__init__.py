"""Provedores de IA. Na fase 1 só existe o heurístico (palavras-chave, sem modelo)."""
from backend.services.ia.base import (
    CapacidadeNaoImplementada,
    ContextoIA,
    ProvedorIA,
    ResultadoClassificacao,
    ResultadoExtracao,
)
from backend.services.ia.heuristico import ProvedorHeuristico
from backend.services.ia.registro import obter_provedor, provedores_disponiveis, registrar_provedor

__all__ = [
    'CapacidadeNaoImplementada', 'ContextoIA', 'ProvedorIA', 'ResultadoClassificacao', 'ResultadoExtracao',
    'ProvedorHeuristico', 'obter_provedor', 'provedores_disponiveis', 'registrar_provedor',
]
