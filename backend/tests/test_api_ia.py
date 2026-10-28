"""POST /ia/extrair: o resultado é o do provedor heurístico, e nada é guardado nem registrado em log."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from backend.services.classificacao import bairros_de_lista
from backend.services.ia import ContextoIA, ProvedorHeuristico

API = '/api/v1'
RAIZ = Path(__file__).resolve().parents[2]
TEXTOS = [
    'Ontem à noite, umas 22h, um cara me seguiu perto da Unesp e ficou me encarando',
    'Hoje de manhã no Centro um motorista de uber ficou buzinando e mexeu comigo',
    'socorro, estou sendo seguida agora na Vila Alemã',
    'Semana passada roubaram meu celular na rodoviária. O nome dele é João, telefone (19) 3533-9009',
    'rua escura e deserta, sem luz, perto do lago azul, às 23:30',
    'algo aconteceu',
]


def _bairros():
    d = json.loads((RAIZ / 'dados' / 'data.json').read_bytes().decode('utf-8'))
    return bairros_de_lista(d['bairros'])


@pytest.mark.parametrize('texto', TEXTOS)
def test_extrair_igual_ao_provedor_heuristico(cliente, texto):
    r = cliente.post(API + '/ia/extrair', json={'texto': texto})
    assert r.status_code == 200
    corpo = r.json()
    assert list(corpo) == ['provedor', 'usa_modelo', 'tipo_evidencia', 'resultado']
    assert (corpo['provedor'], corpo['usa_modelo'], corpo['tipo_evidencia']) == ('heuristica', False, 'classificacao_automatica')
    e = ProvedorHeuristico().extrair(texto, ContextoIA(bairros=_bairros()))
    assert corpo['resultado'] == {
        'urgente': e.urgente, 'tipos': e.tipos,
        'bairro': {'nome': e.bairro.nome, 'lat': e.bairro.lat, 'lng': e.bairro.lng} if e.bairro else None,
        'quando': e.quando, 'periodo': e.periodo, 'descricao': e.descricao, 'removidos': e.removidos, 'resposta': e.resposta}


def test_extrair_exemplo(cliente):
    r = cliente.post(API + '/ia/extrair', json={'texto': TEXTOS[0]}).json()['resultado']
    assert r['tipos'] == ['perseguicao', 'intimidacao']
    assert (r['quando'], r['periodo'], r['urgente']) == ('ontem', '22-00', False)
    assert r['bairro']['nome'] == 'Bela Vista'
    urgente = cliente.post(API + '/ia/extrair', json={'texto': TEXTOS[2]}).json()['resultado']
    assert urgente['urgente'] is True
    limpo = cliente.post(API + '/ia/extrair', json={'texto': TEXTOS[3]}).json()['resultado']
    assert '3533-9009' not in limpo['descricao']
    assert 'telefone' in limpo['removidos']


def test_extrair_nao_guarda_nem_registra_nada(cliente, sessao, contar_linhas, caplog):
    caplog.set_level(logging.DEBUG, logger='aurora')
    antes = contar_linhas(sessao)
    for texto in TEXTOS:
        assert cliente.post(API + '/ia/extrair', json={'texto': texto}).status_code == 200
    sessao.expire_all()
    assert contar_linhas(sessao) == antes
    assert antes['relatos'] == 0 and antes['classificacoes'] == 0
    for texto in TEXTOS:
        assert texto not in caplog.text


def test_extrair_heuristica_le_o_texto_inteiro(cliente):
    # como heuristic() no legado: nada é cortado antes das regras
    r = cliente.post(API + '/ia/extrair', json={'texto': 'a' * 1500 + ' me seguiram'}).json()['resultado']
    assert r['tipos'] == ['perseguicao']
    r = cliente.post(API + '/ia/extrair', json={'texto': 'a' * 1480 + ' me seguiram'}).json()['resultado']
    assert r['tipos'] == ['perseguicao']


@pytest.mark.parametrize('corpo', [{'texto': ''}, {'texto': 'x' * 4001}, {'texto': 5}, {'texto': None}, {}, {'text': 'oi'}])
def test_extrair_validacao_422(cliente, corpo):
    r = cliente.post(API + '/ia/extrair', json=corpo)
    assert r.status_code == 422
    assert r.json()['detail'] == 'Dados da requisição inválidos.'
    assert r.json()['erros'][0]['campo'] == 'texto'
    assert 'xxxx' not in r.text


def test_extrair_limites(cliente):
    assert cliente.post(API + '/ia/extrair', json={'texto': 'x'}).status_code == 200
    assert cliente.post(API + '/ia/extrair', json={'texto': 'x' * 4000}).status_code == 200


def test_extrair_meio_emoji_no_corte(cliente):
    r = cliente.post(API + '/ia/extrair', json={'texto': 'x' * 299 + '😀 fim'})
    assert r.status_code == 200
    assert r.json()['resultado']['descricao'] == 'x' * 299 + '�'


# ------------------------------------------------------------------ POST /ia/rota

def test_rota_sem_modelo_responde_501(cliente):
    r = cliente.post(API + '/ia/rota', json={'texto': 'rota da rua 7 até a rua 3'})
    assert r.status_code == 501


def test_rota_com_ollama(criar_cliente, monkeypatch):
    import httpx
    resposta = {'origem': 'Rua 7', 'destino': 'Avenida 29', 'modo': 'bike'}
    monkeypatch.setattr(httpx, 'post', lambda *a, **k: httpx.Response(
        200, json={'response': json.dumps(resposta)}, request=httpx.Request('POST', 'http://x')))
    c = criar_cliente(ia_provedor='ollama')
    r = c.post(API + '/ia/rota', json={'texto': 'rota da rua 7 até a avenida 29 de bicicleta'})
    assert r.status_code == 200 and r.json() == {'provedor': 'ollama', **resposta}


def test_rota_com_ollama_desligado_devolve_vazio(criar_cliente, monkeypatch):
    import httpx

    def quebra(*a, **k):
        raise httpx.ConnectError('desligado')
    monkeypatch.setattr(httpx, 'post', quebra)
    r = criar_cliente(ia_provedor='ollama').post(API + '/ia/rota', json={'texto': 'rota da rua 7 até a rua 3'})
    assert r.json() == {'provedor': 'ollama', 'origem': None, 'destino': None, 'modo': None}


# ------------------------------------------------------------------ POST /ia/local

def test_local_sem_modelo_responde_501(cliente):
    assert cliente.post(API + '/ia/local', json={'texto': 'rua 5 com avenida 14'}).status_code == 501


def test_local_com_ollama_separa_lugar_e_dado_pessoal(criar_cliente, monkeypatch):
    import httpx
    enviado = {}

    def responde(url, json=None, **k):
        enviado['prompt'] = json['prompt']
        saida = {'ruas': ['Rua 5', 'Avenida 14', 5], 'pontos': ['Fatec'], 'referencia': 'Rua 5 com Avenida 14, na frente da Fatec, endereço 1532',
                 'sensiveis': ['nome'], 'descricao': 'Um homem gritou coisas, ligue 19 99876-5432'}
        return httpx.Response(200, json={'response': __import__('json').dumps(saida)}, request=httpx.Request('POST', 'http://x'))
    monkeypatch.setattr(httpx, 'post', responde)
    c = criar_cliente(ia_provedor='ollama')
    r = c.post(API + '/ia/local', json={'texto': 'sofri assédio na rua 5 com avenida 14 na frente da fatec, me liga 19 99876-5432'})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo['ruas'] == ['Rua 5', 'Avenida 14'] and corpo['pontos'] == ['Fatec']
    assert '1532' not in corpo['referencia']  # o número da casa não sai nem na referência
    assert corpo['sensiveis'] == ['telefone', 'nome']
    assert corpo['descricao'] == 'Um homem gritou coisas, ligue [telefone]'
    assert '99876' not in enviado['prompt']  # o modelo nunca vê o telefone


def test_local_com_ollama_desligado_devolve_vazio(criar_cliente, monkeypatch):
    import httpx

    def quebra(*a, **k):
        raise httpx.ConnectError('desligado')
    monkeypatch.setattr(httpx, 'post', quebra)
    r = criar_cliente(ia_provedor='ollama').post(API + '/ia/local', json={'texto': 'rua 5 com avenida 14'})
    assert r.json() == {'provedor': 'ollama', 'ruas': [], 'pontos': [], 'referencia': None, 'sensiveis': [], 'descricao': ''}
