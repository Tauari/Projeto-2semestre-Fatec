"""Schemas Pydantic para o Observatório e Relatórios de Retorno da Secretaria da Mulher.
Atende às User Stories 01, 05 e 06 com acesso restrito a admins e conformidade LGPD.
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class CredenciaisLogin(BaseModel):
    login: str = Field(..., description="E-mail institucional ou matrícula")
    senha: str = Field(..., description="Senha funcional")


class RespostaLogin(BaseModel):
    autenticado: bool
    token: str
    usuario: str
    nome: str
    cargo: str
    orgao: str
    matricula: str
    papeis: list[str]


class DespachoEntrada(BaseModel):
    orgao: str = Field(..., description="Órgão emissor do parecer (ex.: Secretaria da Mulher, CREAS, DDM)")
    status_novo: str = Field(..., description="Novo status do caso")
    parecer_tecnico: str = Field(..., description="Descrição detalhada das providências adotadas")
    encaminhamentos: list[str] = Field(default_factory=list, description="Lista de encaminhamentos")


class DespachoSaida(BaseModel):
    id: str
    data: str
    orgao: str
    responsavel_nome: str
    responsavel_cargo: str
    status_anterior: str
    status_novo: str
    parecer_tecnico: str
    encaminhamentos: list[str]


class RegistroAuditoriaSaida(BaseModel):
    data: str
    profissional_nome: str
    profissional_email: str
    justificativa: str
    dados_acessados: str


class JustificativaSigilo(BaseModel):
    justificativa: str = Field(..., min_length=10, description="Justificativa funcional obrigatória para desbloqueio LGPD")


class RelatorioRetornoSaida(BaseModel):
    id: str
    protocolo_sigiloso: str
    data_registro: str
    vitima_iniciais: str
    vitima_idade_aprox: str
    vitima_nome_completo: str | None = None
    vitima_telefone_protegido: str | None = None
    bairro_referencia: str
    tipo_violencia: str
    canal_entrada: str
    grau_urgencia: str
    status_retorno: str
    status_retorno_label: str
    orgao_responsavel: str
    ultimo_despacho_data: str
    relato_resumo: str
    despachos: list[DespachoSaida]
    historico_acessos: list[RegistroAuditoriaSaida]


class OcorrenciaObservatorioSaida(BaseModel):
    id: str
    protocolo: str
    data: str
    tipo: str
    tipo_label: str
    bairro: str
    periodo: str
    periodo_label: str
    fonte: str
    fonte_label: str
    descricao_anonima: str
    confirmacoes: int
    status_validacao: str
    grau_risco: str


class KPIsObservatorio(BaseModel):
    total_ocorrencias: int
    total_oficiais: int
    total_comunitarios: int
    total_pesquisa: int
    violencia_domestica_pct: int
    via_publica_pct: int
    bairro_mais_critico: dict[str, Any]
    periodo_mais_critico: dict[str, Any]
    taxa_confirmacao_comunitaria: int


class RespostaObservatorio(BaseModel):
    kpis: KPIsObservatorio
    ocorrencias: list[OcorrenciaObservatorioSaida]
    distribuicao_tipos: list[dict[str, Any]]
    distribuicao_bairros: list[dict[str, Any]]
    distribuicao_horarios: list[dict[str, Any]]
