"""Aviso no Telegram para a patrulha: o que vai na mensagem, quando não envia e falhas do Telegram."""
from __future__ import annotations

import httpx
import pytest

TOKEN = '123456:ABC-segredo'
CONFIG = {'telegram_bot_token': TOKEN, 'telegram_chat_ids': '-1001, 42'}


def _telegram(monkeypatch, falha=None, status=200):
    enviados = []

    def post(url, **kw):
        if falha is not None:
            raise falha
        enviados.append({'url': url, **kw})
        return httpx.Response(status, json={'ok': status == 200}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    return enviados


def test_cada_relato_vai_para_todos_os_chats(criar_cliente, publicar, monkeypatch):
    enviados = _telegram(monkeypatch)
    criar_cliente(**CONFIG)
    publicar(tipos=['assedio'], cell='f10_4', quando='hoje', periodo='20-22', texto='Seguiu a pé ate o ponto')
    assert [e['json']['chat_id'] for e in enviados] == ['-1001', '42']
    assert all(e['url'] == f'https://api.telegram.org/bot{TOKEN}/sendMessage' for e in enviados)
    texto = enviados[0]['json']['text']
    assert 'Potencial assediador na área' in texto and 'Área:' in texto
    assert 'Descrição: Seguiu a pé ate o ponto' in texto
    assert 'google.com/maps?q=' in texto and 'hoje' in texto
    assert 'parse_mode' not in enviados[0]['json']


def test_telefone_no_texto_nao_chega_ao_telegram(criar_cliente, publicar, monkeypatch):
    enviados = _telegram(monkeypatch)
    criar_cliente(**CONFIG)
    publicar(texto='Me ligou no (19) 99876-5432 depois')
    assert '99876' not in enviados[0]['json']['text']


def test_rua_escura_tambem_avisa(criar_cliente, publicar, monkeypatch):
    enviados = _telegram(monkeypatch)
    criar_cliente(**CONFIG)
    publicar(tipos=['ambiente'], cell='f10_4')
    assert len(enviados) == 2


@pytest.mark.parametrize('config', [{}, {'telegram_bot_token': TOKEN}, {'telegram_chat_ids': '42'}])
def test_sem_token_ou_sem_chat_nao_envia(criar_cliente, publicar, monkeypatch, config):
    enviados = _telegram(monkeypatch)
    criar_cliente(**config)
    publicar()
    assert enviados == []


@pytest.mark.parametrize('falha, status', [(httpx.ConnectError('fora'), 200), (None, 500)])
def test_telegram_fora_do_ar_nao_derruba_o_relato(criar_cliente, publicar, monkeypatch, caplog, falha, status):
    _telegram(monkeypatch, falha=falha, status=status)
    criar_cliente(**CONFIG)
    assert publicar()['relato']['id']
    assert TOKEN not in caplog.text
