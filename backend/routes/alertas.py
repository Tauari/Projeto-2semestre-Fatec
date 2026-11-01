"""Alertas recentes, para o app de celular avisar quando a pessoa chega perto de um.

A pessoa NÃO manda a localização dela: o app baixa esta lista e compara a posição com a de cada alerta no próprio aparelho
(a localização fica só lá). Cada alerta traz o título padrão do tipo, o nome da área e o centro da célula de ~150 m; o texto
da usuária nunca vai aqui.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import (
    CHAVE_GEOGRAFIA,
    RepositorioDados,
    RepositorioRelatos,
    instante_atual_ms,
)
from backend.database.sessao import obter_sessao
from backend.models.alertas import ListaAlertas
from backend.models.comum import Erro
from backend.models.vocabulario import TipoEvidencia
from backend.services.alertas import tipo_do_alerta, titulo_alerta
from backend.services.padroes import Grade, Nomes
from backend.services.retencao import limite_retencao_ms

router = APIRouter(tags=['alertas'])

HORA_MS = 3_600_000
MAX_ALERTAS = 100


@router.get('/alertas', response_model=ListaAlertas, responses={404: {'model': Erro}})
def listar(janela_horas: int = Query(6, ge=1, le=72), sessao: Session = Depends(obter_sessao),
           cfg: Configuracoes = Depends(obter_configuracoes)):
    dados = RepositorioDados(sessao)
    geo = dados.referencia(CHAVE_GEOGRAFIA)
    if geo is None or not isinstance(geo.dados.get('hex'), dict):
        raise HTTPException(404, 'A geografia do mapa não está carregada.')
    grade = Grade(geo.dados['hex'])
    nome = Nomes(grade, dados.bairros(), {})
    agora = instante_atual_ms()
    desde = max(agora - janela_horas * HORA_MS, limite_retencao_ms(cfg, agora) or 0)
    alertas = []
    for r in RepositorioRelatos(sessao).listar_desde(desde):  # do mais novo para o mais antigo
        titulo = titulo_alerta(r.tipos)
        if titulo is None:
            continue
        lat, lng = grade.centro(r.cell)
        alertas.append({'id': r.id, 'tipo': tipo_do_alerta(r.tipos), 'titulo': titulo, 'cell': r.cell, 'lat': lat, 'lng': lng,
                        'area': nome(r.cell), 'criado': r.criado})
        if len(alertas) == MAX_ALERTAS:
            break
    return {'tipo_evidencia': TipoEvidencia.RELATO_COMUNIDADE.value, 'janela_horas': janela_horas, 'alertas': alertas}
