"""Percepção (tipo de evidência percepcao): onde as mulheres da pesquisa disseram se sentir inseguras."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.repositorios import RepositorioDados, dados_completos
from backend.database.sessao import obter_sessao
from backend.database.tabelas import ConjuntoPercepcao
from backend.models.comum import ConjuntoDetalhe, Erro, ListaConjuntos
from backend.models.vocabulario import TipoEvidencia

router = APIRouter(tags=['percepção'])


def resumo_percepcao(c: ConjuntoPercepcao) -> dict:
    return {'chave': c.chave, 'tipo_evidencia': TipoEvidencia.PERCEPCAO.value, 'titulo': c.titulo, 'periodo': c.periodo,
            'fonte': c.fonte, 'gerado_em': c.gerado_em}


@router.get('/percepcao', response_model=ListaConjuntos)
def listar(sessao: Session = Depends(obter_sessao)):
    return {'conjuntos': [resumo_percepcao(c) for c in RepositorioDados(sessao).percepcoes()]}


@router.get('/percepcao/{chave}', response_model=ConjuntoDetalhe, responses={404: {'model': Erro}})
def obter(chave: str, sessao: Session = Depends(obter_sessao)):
    c = RepositorioDados(sessao).percepcao(chave)
    if c is None:
        raise HTTPException(404, 'Conjunto de percepção não encontrado.')
    return {**resumo_percepcao(c), 'avisos': c.avisos, 'dados': dados_completos(c)}
