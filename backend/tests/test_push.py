"""Alerta padronizado por tipo e notificação no celular (Expo Push): cadastro do aparelho, quem é avisado, o que vai na
notificação, limite de frequência e falhas do Expo."""
from __future__ import annotations

import re
from pathlib import Path

import httpx
import pytest

from backend.database.repositorios import CHAVE_GEOGRAFIA, RepositorioDados, RepositorioPush
from backend.models.vocabulario import TIPOS_POR_ID
from backend.services.alertas import PRIORIDADE, ROTULOS, SEM_ALERTA, tipo_do_alerta, titulo_alerta
from backend.services.padroes import Grade

API = '/api/v1'
TOKEN = 'ExponentPushToken[abcdefghij1234567890]'
OUTRO = 'ExponentPushToken[zyxwvutsrq0987654321]'
FINA = 'f10_4'
TEXTO_COM_ROUPA = 'Fui assediada por um homem de camiseta preta e calça roxa'


# ------------------------------------------------------------------ alerta padronizado
def test_assedio_vira_potencial_assediador():
    assert titulo_alerta(['assedio']) == 'Potencial assediador na área'


def test_todo_tipo_tem_titulo_e_prioridade():
    assert set(ROTULOS) == set(TIPOS_POR_ID) == set(PRIORIDADE)


def test_o_tipo_mais_grave_da_o_titulo():
    assert tipo_do_alerta(['veiculo', 'assedio']) == 'assedio'
    assert tipo_do_alerta(['assedio', 'violencia']) == 'violencia'


def test_rua_escura_nao_gera_alerta():
    assert SEM_ALERTA == {'ambiente'}
    assert titulo_alerta(['ambiente']) is None
    assert titulo_alerta(['ambiente', 'roubo']) == ROTULOS['roubo']


def test_titulos_do_frontend_sao_os_mesmos():
    js = (Path(__file__).resolve().parents[2] / 'frontend' / 'relatos' / 'alerta.js').read_text(encoding='utf-8')
    for tipo, titulo in ROTULOS.items():
        assert re.search(rf"\b{tipo}\s*:\s*'{re.escape(titulo)}'", js), tipo


# ------------------------------------------------------------------ cadastro do aparelho
def _registrar(cliente, token=TOKEN, areas=(FINA,)):
    return cliente.post(API + '/push/dispositivos', json={'token': token, 'areas': list(areas)})


def test_cadastra_e_troca_as_areas(cliente, sessao):
    assert _registrar(cliente, areas=['f1_1', '2_2']).status_code == 204
    assert RepositorioPush(sessao).com_areas()[0].areas == ['f1_1', '2_2']
    assert _registrar(cliente, areas=['f3_3']).status_code == 204
    sessao.expire_all()
    (d,) = RepositorioPush(sessao).com_areas()
    assert d.token == TOKEN and d.areas == ['f3_3']


def test_sem_areas_o_aparelho_nao_recebe_nada(cliente, sessao):
    assert _registrar(cliente, areas=[]).status_code == 204
    assert RepositorioPush(sessao).contar() == 1 and RepositorioPush(sessao).com_areas() == []


def test_areas_sem_repeticao_e_no_maximo_40(cliente, sessao):
    muitas = [f'f{i}_1' for i in range(60)] + ['f0_1']
    assert _registrar(cliente, areas=muitas).status_code == 204
    assert len(RepositorioPush(sessao).com_areas()[0].areas) == 40


@pytest.mark.parametrize('token', ['', 'abc', 'ExponentPushToken[]', 'ExponentPushToken[curto]', 'Bearer ExponentPushToken[abcdefghij1234]', 'ExponentPushToken[abc def ghi jkl]'])
def test_token_invalido_422(cliente, token):
    assert _registrar(cliente, token=token).status_code == 422


@pytest.mark.parametrize('area', ['', 'abc', 'f1_', '1_2_3', '99999_1'])
def test_area_invalida_422(cliente, area):
    assert _registrar(cliente, areas=[area]).status_code == 422


def test_remover_aparelho(cliente, sessao):
    _registrar(cliente)
    assert cliente.delete(API + '/push/dispositivos', headers={'X-Push-Token': TOKEN}).status_code == 204
    assert RepositorioPush(sessao).contar() == 0
    assert cliente.delete(API + '/push/dispositivos', headers={'X-Push-Token': TOKEN}).status_code == 404
    assert cliente.delete(API + '/push/dispositivos').status_code == 404


# ------------------------------------------------------------------ envio
def _expo(monkeypatch, tickets=None, falha=None):
    """Troca httpx.post pelo Expo de mentira e guarda o que foi enviado."""
    enviados = []

    def post(url, **kw):
        if falha is not None:
            raise falha
        enviados.append({'url': url, **kw})
        corpo = tickets if tickets is not None else [{'status': 'ok', 'id': 'x'} for _ in kw['json']]
        return httpx.Response(200, json={'data': corpo}, request=httpx.Request('POST', url))
    monkeypatch.setattr(httpx, 'post', post)
    return enviados


def test_avisa_quem_acompanha_a_area_com_o_titulo_padrao(cliente, publicar, monkeypatch):
    enviados = _expo(monkeypatch)
    _registrar(cliente, areas=[FINA])
    publicar(tipos=['assedio'], cell=FINA, texto=TEXTO_COM_ROUPA)
    (envio,) = enviados
    assert envio['url'] == 'https://exp.host/--/api/v2/push/send'
    (msg,) = envio['json']
    assert msg['to'] == TOKEN and msg['title'] == 'Potencial assediador na área'
    assert msg['data']['cell'] == FINA and msg['channelId'] == 'alertas' and msg['priority'] == 'high'


def test_a_roupa_nao_vai_na_notificacao(cliente, publicar, monkeypatch):
    enviados = _expo(monkeypatch)
    _registrar(cliente)
    publicar(tipos=['assedio'], cell=FINA, texto=TEXTO_COM_ROUPA)
    msg = enviados[0]['json'][0]
    assert 'camiseta' not in str(msg) and 'roxa' not in str(msg) and 'homem' not in str(msg)


def test_area_de_1_km_pega_relato_de_150_m_dentro_dela(cliente, sessao, publicar, monkeypatch):
    enviados = _expo(monkeypatch)
    grade = Grade(RepositorioDados(sessao).referencia(CHAVE_GEOGRAFIA).dados['hex'])
    _registrar(cliente, areas=[grade.grossa(FINA)])
    publicar(tipos=['roubo'], cell=FINA)
    assert len(enviados) == 1 and enviados[0]['json'][0]['title'] == 'Roubo ou furto na área'
    assert enviados[0]['json'][0]['body'].startswith(('Perto de', 'Zona rural'))


def test_area_de_outro_lugar_nao_e_avisada(cliente, publicar, monkeypatch):
    enviados = _expo(monkeypatch)
    _registrar(cliente, areas=['f50_50', '40_40'])
    publicar(tipos=['assedio'], cell=FINA)
    assert enviados == []


def test_quem_enviou_o_relato_nao_e_avisado(cliente, monkeypatch):
    enviados = _expo(monkeypatch)
    _registrar(cliente, token=TOKEN)
    _registrar(cliente, token=OUTRO)
    r = cliente.post(API + '/relatos', json={'tipos': ['assedio'], 'cell': FINA}, headers={'X-Push-Token': TOKEN})
    assert r.status_code == 201
    assert [m['to'] for m in enviados[0]['json']] == [OUTRO]


def test_rua_escura_nao_notifica(cliente, publicar, monkeypatch):
    enviados = _expo(monkeypatch)
    _registrar(cliente)
    publicar(tipos=['ambiente'], cell=FINA)
    assert enviados == []


def test_limite_de_uma_notificacao_a_cada_intervalo(cliente, publicar, monkeypatch):
    enviados = _expo(monkeypatch)
    _registrar(cliente)
    publicar(tipos=['assedio'], cell=FINA)
    publicar(tipos=['roubo'], cell=FINA)
    assert len(enviados) == 1


def test_sem_intervalo_todo_relato_notifica(criar_cliente, monkeypatch):
    enviados = _expo(monkeypatch)
    c = criar_cliente(push_intervalo_min=0)
    _registrar(c)
    for _ in range(2):
        assert c.post(API + '/relatos', json={'tipos': ['assedio'], 'cell': FINA}).status_code == 201
    assert len(enviados) == 2


def test_push_desligado_na_configuracao(criar_cliente, monkeypatch):
    enviados = _expo(monkeypatch)
    c = criar_cliente(push_ativo=False)
    _registrar(c)
    assert c.post(API + '/relatos', json={'tipos': ['assedio'], 'cell': FINA}).status_code == 201
    assert enviados == []


def test_aparelho_que_nao_existe_mais_e_removido(cliente, sessao, publicar, monkeypatch):
    _expo(monkeypatch, tickets=[{'status': 'error', 'message': 'x', 'details': {'error': 'DeviceNotRegistered'}}])
    _registrar(cliente)
    publicar(tipos=['assedio'], cell=FINA)
    sessao.expire_all()
    assert RepositorioPush(sessao).contar() == 0


@pytest.mark.parametrize('falha', [httpx.ConnectError('sem internet'), httpx.ReadTimeout('demorou')])
def test_expo_fora_do_ar_nao_derruba_o_relato(cliente, publicar, monkeypatch, falha):
    _expo(monkeypatch, falha=falha)
    _registrar(cliente)
    rel = publicar(tipos=['assedio'], cell=FINA)['relato']
    assert cliente.get(API + '/relatos/' + rel['id']).status_code == 200


def test_falha_do_expo_nao_gasta_o_intervalo(cliente, sessao, publicar, monkeypatch):
    _expo(monkeypatch, falha=httpx.ConnectError('sem internet'))
    _registrar(cliente)
    publicar(tipos=['assedio'], cell=FINA)
    sessao.expire_all()
    assert RepositorioPush(sessao).com_areas()[0].ultimo_envio == 0
