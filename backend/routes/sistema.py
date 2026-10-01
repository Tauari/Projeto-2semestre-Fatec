"""Saúde do servidor e a configuração pública que o frontend lê ao abrir."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from backend import __version__
from backend.config import Configuracoes, obter_configuracoes
from backend.models.comum import ConfiguracaoPublica, Saude
from backend.models.vocabulario import TipoEvidencia, vocabulario_publico
from backend.services.ia import obter_provedor
from backend.services.processamento_dados import CHAVE_DADO_OFICIAL, CHAVE_PERCEPCAO

router = APIRouter(tags=['sistema'])

MODULOS = {'relatos': True, 'apoio': True, 'dados_oficiais': True, 'percepcao': True, 'dashboard': True, 'ia': True,
           'moderacao': False, 'usuarios': False, 'relatorios': False}


@router.get('/saude', response_model=Saude)
def saude():
    return {'status': 'ok', 'versao': __version__}


@router.get('/config', response_model=ConfiguracaoPublica)
def configuracao(cfg: Configuracoes = Depends(obter_configuracoes)):
    provedor = obter_provedor(cfg.ia_provedor)
    return {
        'versao_api': '1',
        'vocabulario': vocabulario_publico(),
        'relatos': {'janela_dias': cfg.relatos_janela_dias, 'tipos_max': cfg.relatos_tipos_max, 'texto_max': cfg.relatos_texto_max,
                    'precisao_criado': cfg.relatos_precisao_criado},
        'ia': {'provedor': provedor.nome, 'usa_modelo': provedor.usa_modelo},
        'conjuntos_padrao': {TipoEvidencia.DADO_OFICIAL.value: CHAVE_DADO_OFICIAL, TipoEvidencia.PERCEPCAO.value: CHAVE_PERCEPCAO},
        'modulos': dict(MODULOS),
    }
