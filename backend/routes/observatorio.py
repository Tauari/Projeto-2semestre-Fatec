"""Rotas do Observatório de Segurança e Secretaria Municipal da Mulher.
Todas as rotas exigem obrigatoriamente autenticação de administrador (HTTP 403 Forbidden para não-admins).

Atende às User Stories:
- 01: Geração de relatórios analíticos para o Observatório
- 05: Acesso profissional restrito aos relatórios de retorno e medidas protetivas
- 06: Exportação de relatórios em CSV e PDF
"""
from __future__ import annotations

from typing import Any, Literal
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from backend.models.observatorio import (
    DespachoEntrada,
    JustificativaSigilo,
    RelatorioRetornoSaida,
    RespostaObservatorio,
)
from backend.routes.usuarios import extrair_token, validar_token_admin
from backend.services.relatorio import (
    adicionar_despacho,
    exportar_csv_observatorio,
    obter_relatorio_observatorio,
    obter_retornos_secretaria,
    registrar_termo_sigilo,
)

router = APIRouter(prefix="/observatorio", tags=["observatório"])

# Conjunto em memória para rastrear casos com sigilo desbloqueado na sessão
_CASOS_DESBLOQUEADOS_SIGILO: set[str] = set()


def exigir_admin(
    authorization: str | None = Header(None, alias="Authorization"),
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
) -> dict[str, Any]:
    """Dependência de segurança por rota:
    Garante que SOMENTE administradores autenticados possam acessar qualquer dado do Observatório.
    Rejeita requisições anônimas ou de usuários comuns com HTTP 403 Forbidden.
    """
    token = extrair_token(authorization, x_admin_token)
    if not validar_token_admin(token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito. Somente administradores autorizados do Observatório e Secretaria da Mulher podem acessar estes dados.",
        )
    return {
        "usuario": "admin_observatorio",
        "nome": "Coordenadoria Observatório / Secretaria da Mulher",
        "cargo": "Técnica Especializada / Gestora de Dados",
        "email": "observatorio.seguranca@mulher.rioclaro.sp.gov.br",
        "papeis": ["admin", "observatorio", "secretaria_mulher"],
    }


@router.get(
    "/relatorios",
    response_model=RespostaObservatorio,
    summary="Relatório consolidado para o Observatório (US 01)",
)
def relatorios_observatorio(
    fonte: str = Query("todas", description="Fonte de dados: todas, boletim_oficial, relato_comunidade, pesquisa_percepcao"),
    tipo: str = Query("todos", description="Tipo de ocorrência ou violência"),
    bairro: str = Query("todos", description="Bairro de referência em Rio Claro"),
    periodo: str = Query("todos", description="Faixa horária"),
    ano: str = Query("todos", description="Ano de ocorrência"),
    busca: str | None = Query(None, description="Termo de busca textual ou protocolo"),
    admin: dict[str, Any] = Depends(exigir_admin),
):
    """Retorna dados agregados, tabelas com filtros e indicadores do Observatório.
    Protegido por rota: acessível apenas por administradores.
    """
    return obter_relatorio_observatorio(
        fonte=fonte,
        tipo=tipo,
        bairro=bairro,
        periodo=periodo,
        ano=ano,
        busca=busca,
    )


@router.get(
    "/retornos",
    response_model=list[RelatorioRetornoSaida],
    summary="Relatórios de Retorno da Secretaria da Mulher (US 05)",
)
def listar_retornos(
    admin: dict[str, Any] = Depends(exigir_admin),
):
    """Consulta relatórios de retorno da rede de acolhimento.
    Por padrão, os dados pessoais das vítimas são mascarados conforme a LGPD e Lei 11.340.
    Protegido por rota: acessível apenas por administradores.
    """
    return obter_retornos_secretaria(desbloqueados_ids=_CASOS_DESBLOQUEADOS_SIGILO)


@router.post(
    "/retornos/{retorno_id}/despachos",
    response_model=RelatorioRetornoSaida,
    summary="Registrar despacho institucional e atualizar status (US 05)",
)
def registrar_despacho(
    retorno_id: str,
    dados: DespachoEntrada,
    admin: dict[str, Any] = Depends(exigir_admin),
):
    """Insere parecer técnico da Secretaria da Mulher ou rede parceira (CAM, DDM, CREAS).
    Protegido por rota: acessível apenas por administradores.
    """
    resultado = adicionar_despacho(
        retorno_id=retorno_id,
        despacho_data=dados.model_dump(),
        profissional=admin,
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Relatório de retorno não encontrado.")
    return resultado


@router.post(
    "/retornos/{retorno_id}/desbloquear-sigilo",
    response_model=RelatorioRetornoSaida,
    summary="Desbloquear dados completos da vítima com justificativa LGPD (US 05)",
)
def desbloquear_sigilo_vitima(
    retorno_id: str,
    justificativa: JustificativaSigilo,
    admin: dict[str, Any] = Depends(exigir_admin),
):
    """Desbloqueia os dados sensíveis da vítima exclusivamente para a profissional responsável.
    Exige justificativa administrativa e grava o acesso na trilha de auditoria irreversível.
    Protegido por rota: acessível apenas por administradores.
    """
    resultado = registrar_termo_sigilo(
        retorno_id=retorno_id,
        justificativa=justificativa.justificativa,
        profissional=admin,
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Relatório de retorno não encontrado.")

    _CASOS_DESBLOQUEADOS_SIGILO.add(retorno_id)
    return resultado


@router.get(
    "/exportar/{formato}",
    summary="Exportar relatórios em CSV ou PDF (US 06)",
)
def exportar_relatorio(
    formato: Literal["csv", "pdf"],
    fonte: str = Query("todas"),
    tipo: str = Query("todos"),
    bairro: str = Query("todos"),
    periodo: str = Query("todos"),
    ano: str = Query("todos"),
    busca: str | None = Query(None),
    admin: dict[str, Any] = Depends(exigir_admin),
):
    """Exportação dos relatórios e análises para uso em reuniões institucionais e arquivos oficiais.
    Protegido por rota: acessível apenas por administradores.
    """
    relatorio = obter_relatorio_observatorio(
        fonte=fonte,
        tipo=tipo,
        bairro=bairro,
        periodo=periodo,
        ano=ano,
        busca=busca,
    )
    itens = relatorio.get("ocorrencias", [])

    if formato == "csv":
        conteudo_csv = exportar_csv_observatorio(itens)
        return Response(
            content=conteudo_csv.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": "attachment; filename=aurora_relatorio_observatorio.csv",
            },
        )

    # Formato PDF simples estruturado para reuniões institucionais
    kpis = relatorio.get("kpis", {})
    linhas_texto = [
        "%PDF-1.4",
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
        "3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >> endobj",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
    ]

    titulo = "RELATORIO CONSOLIDADO - OBSERVATORIO DE SEGURANCA E SECRETARIA DA MULHER (RIO CLARO)"
    subtitulo = f"Total Ocorrencias: {kpis.get('total_ocorrencias', 0)} | Violencia Domestica: {kpis.get('violencia_domestica_pct', 0)}% | Via Publica: {kpis.get('via_publica_pct', 0)}%"
    meta = f"Gerado por: {admin.get('nome')} ({admin.get('cargo')}) - Acesso Administrativo Autorizado"

    stream_content = f"BT /F1 14 Tf 40 750 Td ({titulo}) Tj ET\n"
    stream_content += f"BT /F1 10 Tf 40 730 Td ({subtitulo}) Tj ET\n"
    stream_content += f"BT /F1 9 Tf 40 715 Td ({meta}) Tj ET\n"

    y = 680
    for idx, item in enumerate(itens[:25]):
        linha = f"[{item.get('protocolo')}] {item.get('data')} - {item.get('tipo_label')} - Bairro: {item.get('bairro')} ({item.get('fonte_label')})"
        linha_ascii = linha.encode("ascii", "replace").decode("ascii")
        stream_content += f"BT /F1 8 Tf 40 {y} Td ({linha_ascii}) Tj ET\n"
        y -= 20
        if y < 60:
            break

    stream_bytes = stream_content.encode("latin-1", "replace")
    linhas_texto.append(f"5 0 obj << /Length {len(stream_bytes)} >> stream\n{stream_content}endstream\nendobj")
    linhas_texto.append("xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000115 00000 n \n0000000220 00000 n \n0000000295 00000 n \n")
    linhas_texto.append("trailer << /Size 6 /Root 1 0 R >>\nstartxref\n450\n%%EOF")

    conteudo_pdf = "\n".join(linhas_texto).encode("latin-1", "replace")
    return Response(
        content=conteudo_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=aurora_relatorio_observatorio.pdf",
        },
    )
