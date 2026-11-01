"""Provedor Groq: chamada à API, texto limpo antes de sair, chave protegida; sem Groq, volta para a heurística."""
import json

import httpx
import pytest

from backend.config import obter_configuracoes
from backend.services.classificacao import bairros_de_lista
from backend.services.ia import ContextoIA, obter_provedor, provedores_disponiveis

CTX = ContextoIA(bairros=bairros_de_lista([['Bela Vista', -22.4059, -47.552, 6]]))
TEXTO = 'Ontem umas 21h um cara de moto me seguiu perto do Bela Vista, a placa era ABC1D23'
CHAVE = 'gsk_chave-falsa-de-teste'


@pytest.fixture
def groq(monkeypatch):
    monkeypatch.setenv('AURORA_IA_PROVEDOR', 'groq')
    monkeypatch.setenv('AURORA_GROQ_API_KEY', CHAVE)
    obter_configuracoes.cache_clear()
    yield obter_provedor()
    obter_configuracoes.cache_clear()


def _chamadas(monkeypatch, resposta):
    """Troca httpx.post por uma função que guarda os argumentos e devolve a resposta no formato do Groq."""
    feitas = []

    def post(url, **kw):
        feitas.append({'url': url, **kw})
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(resposta)}}]}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    return feitas


def test_groq_esta_registrado():
    assert 'groq' in provedores_disponiveis()


def test_chama_o_groq_com_chave_modelo_e_saida_json(groq, monkeypatch):
    feitas = _chamadas(monkeypatch, {'tipos': ['perseguicao'], 'bairro': 'Bela Vista', 'descricao': 'Um homem de moto me seguiu.'})
    r = groq.extrair(TEXTO, CTX)
    assert r.por_modelo and r.tipos == ['perseguicao'] and r.bairro.nome == 'Bela Vista'
    (c,) = feitas
    assert c['url'] == 'https://api.groq.com/openai/v1/chat/completions'
    assert c['headers'] == {'Authorization': 'Bearer ' + CHAVE}
    assert c['json']['model'] == obter_configuracoes().groq_modelo
    assert c['json']['response_format'] == {'type': 'json_object'}
    assert c['json']['messages'][0]['role'] == 'user'


def test_o_texto_sai_sem_a_placa_e_a_resposta_volta_limpa(groq, monkeypatch):
    feitas = _chamadas(monkeypatch, {'tipos': ['perseguicao'], 'descricao': 'Um homem me seguiu, placa ABC1D23.'})
    r = groq.extrair(TEXTO, CTX)
    assert 'ABC1D23' not in feitas[0]['json']['messages'][0]['content']
    assert 'ABC1D23' not in r.descricao


def test_rota_sai_sem_telefone_nem_numero_de_casa(groq, monkeypatch):
    feitas = _chamadas(monkeypatch, {'origem': 'Rua 7', 'destino': 'rodoviária', 'modo': 'bike'})
    rota = groq.extrair_rota('saindo da Rua 7, 830, até a rodoviária de bike, meu telefone (19) 99999-1234')
    assert rota == {'origem': 'Rua 7', 'destino': 'rodoviária', 'modo': 'bike'}
    enviado = feitas[0]['json']['messages'][0]['content']
    assert '830' not in enviado and '99999' not in enviado


def test_resumo_de_padroes_nao_pede_saida_json(groq, monkeypatch):
    feitas = []

    def post(url, **kw):
        feitas.append(kw)
        return httpx.Response(200, json={'choices': [{'message': {'content': 'texto'}}]}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    assert groq._gerar('resuma', json_saida=False, temperatura=0.2) == 'texto'
    assert 'response_format' not in feitas[0]['json']


@pytest.mark.parametrize('falha', [
    httpx.ConnectError('sem internet'),
    httpx.HTTPStatusError('limite de uso', request=httpx.Request('POST', 'http://x'), response=httpx.Response(429)),
    ValueError('lixo'),
])
def test_sem_groq_volta_para_a_heuristica(groq, monkeypatch, falha):
    def quebra(*a, **k):
        raise falha
    monkeypatch.setattr(httpx, 'post', quebra)
    r = groq.extrair(TEXTO, CTX)
    assert not r.por_modelo and 'perseguicao' in r.tipos


@pytest.mark.parametrize('corpo', [{}, {'choices': []}, {'choices': [None]}])
def test_resposta_fora_do_formato_volta_para_a_heuristica(groq, monkeypatch, corpo):
    monkeypatch.setattr(httpx, 'post', lambda url, **kw: httpx.Response(200, json=corpo, request=httpx.Request('POST', url)))
    r = groq.extrair(TEXTO, CTX)
    assert not r.por_modelo and 'perseguicao' in r.tipos


def test_sem_chave_o_provedor_nao_sobe(monkeypatch):
    monkeypatch.setenv('AURORA_IA_PROVEDOR', 'groq')
    obter_configuracoes.cache_clear()
    with pytest.raises(ValueError, match='AURORA_GROQ_API_KEY'):
        obter_provedor()


def test_a_chave_nao_aparece_na_configuracao_nem_no_provedor(groq):
    cfg = obter_configuracoes()
    assert CHAVE not in repr(cfg) and CHAVE not in str(cfg)
    assert CHAVE not in json.dumps(groq.info())


def test_modelo_do_groq_vem_da_configuracao(monkeypatch):
    monkeypatch.setenv('AURORA_IA_PROVEDOR', 'groq')
    monkeypatch.setenv('AURORA_GROQ_API_KEY', CHAVE)
    monkeypatch.setenv('AURORA_GROQ_MODELO', 'modelo-de-teste')
    obter_configuracoes.cache_clear()
    p = obter_provedor()
    assert p.modelo == 'modelo-de-teste' and p.info()['modelo'] == 'modelo-de-teste'
