"""Dados oficiais (tipo de evidência dado_oficial): registros de B.O. da SSP-SP, por célula."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.repositorios import RepositorioDados, dados_completos
from backend.database.sessao import obter_sessao
from backend.database.tabelas import ConjuntoOficial
from backend.models.comum import ConjuntoDetalhe, Erro, ListaConjuntos
from backend.models.vocabulario import TipoEvidencia

router = APIRouter(tags=['dados oficiais'])


def resumo_oficial(c: ConjuntoOficial) -> dict:
    return {'chave': c.chave, 'tipo_evidencia': TipoEvidencia.DADO_OFICIAL.value, 'titulo': c.titulo, 'periodo': c.periodo,
            'fonte': c.fonte, 'gerado_em': c.gerado_em}


@router.get('/dados-oficiais', response_model=ListaConjuntos)
def listar(sessao: Session = Depends(obter_sessao)):
    return {'conjuntos': [resumo_oficial(c) for c in RepositorioDados(sessao).oficiais()]}


@router.get('/dados-oficiais/{chave}', response_model=ConjuntoDetalhe, responses={404: {'model': Erro}})
def obter(chave: str, sessao: Session = Depends(obter_sessao)):
    c = RepositorioDados(sessao).oficial(chave)
    if c is None:
        raise HTTPException(404, 'Conjunto de dados oficiais não encontrado.')
    return {**resumo_oficial(c), 'avisos': c.avisos, 'dados': dados_completos(c)}
