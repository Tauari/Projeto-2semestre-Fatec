"""Geografia do mapa (hexágonos, contorno, bairros) e o mapa de ruas do OpenStreetMap."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import CHAVE_GEOGRAFIA, RepositorioDados, dados_completos
from backend.database.sessao import obter_sessao
from backend.models.comum import Erro, Geografia

router = APIRouter(tags=['mapa'])


@router.get('/mapa/geografia', response_model=Geografia, responses={404: {'model': Erro}})
def geografia(sessao: Session = Depends(obter_sessao)):
    geo = RepositorioDados(sessao).referencia(CHAVE_GEOGRAFIA)
    if geo is None:
        raise HTTPException(404, 'Os dados do mapa ainda não foram carregados.')
    return {'tipo': 'geografia', 'gerado_em': geo.gerado_em, 'fonte': geo.fonte, 'notas': geo.notas, 'dados': dados_completos(geo)}


@router.get('/mapa/rotas', response_class=FileResponse,
            responses={200: {'content': {'application/json': {}}}, 404: {'model': Erro}})
def mapa_rotas(cfg: Configuracoes = Depends(obter_configuracoes)):
    caminho = Path(cfg.pasta_dados) / 'rotas' / 'grafo.json'
    if not caminho.is_file():
        raise HTTPException(404, 'O grafo de ruas para rotas não está disponível.')
    return FileResponse(caminho, media_type='application/json', headers={'Cache-Control': 'public, max-age=86400'})


@router.get('/mapa/base', response_class=FileResponse,
            responses={200: {'content': {'application/json': {}}}, 404: {'model': Erro}})
def mapa_base(cfg: Configuracoes = Depends(obter_configuracoes)):
    # o arquivo vai como está: não passa pelo banco nem é reescrito
    caminho = Path(cfg.pasta_dados) / 'osm' / 'basemap.json'
    if not caminho.is_file():
        raise HTTPException(404, 'O mapa de ruas não está disponível.')
    return FileResponse(caminho, media_type='application/json', headers={'Cache-Control': 'public, max-age=86400'})
