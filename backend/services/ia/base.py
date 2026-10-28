"""Interface dos provedores de IA e os resultados que eles devolvem.

Na fase 1 só existe o provedor heurístico (palavras-chave, sem modelo). Análise de padrões e
relatórios ficam marcados como capacidades futuras: levantam ``CapacidadeNaoImplementada``.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.services.classificacao import Bairro

# ordem em que as capacidades aparecem em info()
CAPACIDADES_ATUAIS = ('extrair', 'classificar')
CAPACIDADES_FUTURAS = ('analise_padroes', 'analise_agregada', 'relatorios')


@dataclass
class ContextoIA:
    bairros: list[Bairro]


@dataclass
class ResultadoExtracao:
    urgente: bool
    tipos: list[str]
    bairro: Bairro | None
    quando: str | None
    periodo: str | None
    descricao: str
    removidos: list[str]
    resposta: str
    por_modelo: bool = False  # True só quando um modelo respondeu (e não a heurística de reserva)


@dataclass
class ResultadoClassificacao:
    tipos: list[str]
    urgente: bool
    quando: str | None
    periodo: str | None
    confianca: float | None = None


class CapacidadeNaoImplementada(NotImplementedError):
    pass


class ProvedorIA(ABC):
    nome: str
    usa_modelo: bool
    modelo: str | None = None
    capacidades: frozenset[str] = frozenset()

    @abstractmethod
    def extrair(self, texto: str, contexto: ContextoIA) -> ResultadoExtracao:
        ...

    def classificar(self, texto: str, contexto: ContextoIA) -> ResultadoClassificacao:
        r = self.extrair(texto, contexto)
        return ResultadoClassificacao(tipos=list(r.tipos), urgente=r.urgente, quando=r.quando, periodo=r.periodo)

    def extrair_rota(self, texto: str) -> dict:
        """{'origem': str | None, 'destino': str | None, 'modo': 'pe' | 'bike' | 'carro' | None}."""
        raise CapacidadeNaoImplementada('Este provedor não entende pedidos de rota.')

    def extrair_local(self, texto: str) -> dict:
        """{'ruas': [...], 'pontos': [...], 'referencia': str | None, 'sensiveis': [...]}: onde foi e o que é dado pessoal."""
        raise CapacidadeNaoImplementada('Este provedor não localiza endereços no texto.')

    def analisar_padroes(self, *args, **kwargs):
        # depende do Observatório: não finge que existe
        raise CapacidadeNaoImplementada('A análise de padrões por IA ainda não foi implementada.')

    def gerar_relatorio(self, *args, **kwargs):
        raise CapacidadeNaoImplementada('Relatórios por IA ainda não foram implementados.')

    def info(self) -> dict:
        ordem = CAPACIDADES_ATUAIS + CAPACIDADES_FUTURAS
        capacidades = [c for c in ordem if c in self.capacidades] + sorted(c for c in self.capacidades if c not in ordem)
        return {
            'nome': self.nome,
            'usa_modelo': self.usa_modelo,
            'modelo': self.modelo,
            'capacidades': capacidades,
            'nao_implementado': [c for c in CAPACIDADES_FUTURAS if c not in self.capacidades],
        }
