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
