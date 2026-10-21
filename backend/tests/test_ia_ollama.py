"""Provedor Ollama: resposta do modelo validada e limpa; sem Ollama, volta para a heurística."""
import json

import httpx
import pytest

from backend.config import obter_configuracoes
from backend.services.classificacao import bairros_de_lista
from backend.services.ia import ContextoIA, obter_provedor

CTX = ContextoIA(bairros=bairros_de_lista([['Bela Vista', -22.4059, -47.552, 6]]))
TEXTO = 'Ontem umas 21h um cara de moto me seguiu perto do Bela Vista, a placa era ABC1D23'


@pytest.fixture
def ollama(monkeypatch):
    monkeypatch.setenv('AURORA_IA_PROVEDOR', 'ollama')
    obter_configuracoes.cache_clear()
    yield obter_provedor()
    obter_configuracoes.cache_clear()


def _resposta(obj):
    return lambda *a, **k: httpx.Response(200, json={'response': json.dumps(obj)}, request=httpx.Request('POST', 'http://x'))


def test_resposta_do_modelo_e_validada_e_limpa(ollama, monkeypatch):
    monkeypatch.setattr(httpx, 'post', _resposta({'tipos': ['perseguicao', 'inventado'], 'bairro': 'Bela Vista', 'quando': 'semana',
                                                   'periodo': 'madrugada', 'descricao': 'Um homem me seguiu, placa ABC1D23.'}))
    r = ollama.extrair(TEXTO, CTX)
    assert r.por_modelo and r.tipos == ['perseguicao'] and r.bairro.nome == 'Bela Vista'
    assert 'ABC1D23' not in r.descricao
    assert (r.quando, r.periodo) == ('ontem', '20-22')  # dia e horário vêm das regras, não do modelo


@pytest.mark.parametrize('falha', [httpx.ConnectError('desligado'), ValueError('lixo')])
def test_sem_ollama_volta_para_a_heuristica(ollama, monkeypatch, falha):
    def quebra(*a, **k):
        raise falha
    monkeypatch.setattr(httpx, 'post', quebra)
    r = ollama.extrair(TEXTO, CTX)
    assert not r.por_modelo and 'perseguicao' in r.tipos
