"""Proteções da revisão da fase 1: tamanho do corpo, apagar de vez no SQLite, retenção com o servidor ligado
e a precisão da hora de envio no /config (o frontend usa para os alertas)."""
from __future__ import annotations

from backend.database.repositorios import DIA_MS, RepositorioRelatos, instante_atual_ms
from backend.database.sessao import SessionLocal

API = '/api/v1'
RELATO = {'tipos': ['assedio'], 'cell': '0_0', 'quando': 'hoje', 'periodo': '20-22', 'origem': 'chat'}


# ------------------------------------------------------------------ tamanho do corpo

def test_corpo_grande_com_content_length_recebe_413(cliente):
    r = cliente.post(API + '/relatos', json={**RELATO, 'texto': 'oi', 'lixo': 'a' * 200_000})
    assert r.status_code == 413
    assert r.json() == {'detail': 'O corpo da requisição é grande demais.'}
    assert cliente.get(API + '/relatos').json()['relatos'] == []


def test_corpo_grande_sem_content_length_recebe_413(cliente):
    def pedacos():
        yield b'{"tipos":["assedio"],"cell":"0_0","lixo":"'
        for _ in range(100):
            yield b'a' * 2048
        yield b'"}'
    r = cliente.post(API + '/ia/extrair', content=pedacos(), headers={'content-type': 'application/json'})
    assert r.status_code == 413
    assert r.json()['detail'] == 'O corpo da requisição é grande demais.'


def test_limite_do_corpo_e_configuravel(criar_cliente):
    c = criar_cliente(limite_corpo_bytes=2048)
    assert c.post(API + '/relatos', json={**RELATO, 'texto': 'x' * 1500}).status_code == 201
    assert c.post(API + '/relatos', json={**RELATO, 'texto': 'x' * 1990, 'extra': 'y' * 200}).status_code == 413


def test_relato_de_tamanho_normal_passa(cliente):
    r = cliente.post(API + '/relatos', json={**RELATO, 'texto': 'ç' * 2000})
    assert r.status_code == 201


# ------------------------------------------------------------------ apagar de vez

def test_relato_apagado_nao_fica_no_arquivo_do_banco(configurar, tmp_path):
    from fastapi.testclient import TestClient
    from backend.main import create_app
    configurar()
    marca = 'MARCADOR-UNICO-QUE-NAO-PODE-SOBRAR'
    with TestClient(create_app()) as c:
        r = c.post(API + '/relatos', json={**RELATO, 'texto': marca}).json()
        assert c.delete(API + '/relatos/' + r['relato']['id'], headers={'X-Chave-Exclusao': r['chave_exclusao']}).status_code == 204
    dados = (tmp_path / 'aurora-teste.db').read_bytes()
    assert marca.encode() not in dados


# ------------------------------------------------------------------ retenção com o servidor ligado

def test_com_prazo_relato_vencido_nao_e_servido_nem_listado(criar_cliente):
    c = criar_cliente(relatos_retencao_dias=10, relatos_janela_dias=30)
    agora = instante_atual_ms()
    with SessionLocal() as s:
        repo = RepositorioRelatos(s)
        vencido = repo.criar(id='v' * 32, tipos=['roubo'], cell='0_0', quando=None, periodo=None, texto='', origem='chat',
                             criado=agora - 11 * DIA_MS, chave_hash='0' * 64)
        valido = repo.criar(id='w' * 32, tipos=['roubo'], cell='0_0', quando=None, periodo=None, texto='', origem='chat',
                            criado=agora - 5 * DIA_MS, chave_hash='0' * 64)
        s.commit()
        ids = (vencido.id, valido.id)
    lista = [r['id'] for r in c.get(API + '/relatos').json()['relatos']]
    assert ids[0] not in lista and ids[1] in lista
    assert c.get(API + '/relatos/' + ids[0]).status_code == 404
    assert c.get(API + '/relatos/' + ids[1]).status_code == 200


def test_com_prazo_publicar_apaga_os_vencidos(criar_cliente):
    c = criar_cliente(relatos_retencao_dias=10)
    agora = instante_atual_ms()
    with SessionLocal() as s:
        RepositorioRelatos(s).criar(id='v' * 32, tipos=['roubo'], cell='0_0', quando=None, periodo=None, texto='',
                                    origem='chat', criado=agora - 11 * DIA_MS, chave_hash='0' * 64)
        s.commit()
    assert c.post(API + '/relatos', json=RELATO).status_code == 201
    with SessionLocal() as s:
        assert RepositorioRelatos(s).obter('v' * 32) is None


def test_sem_prazo_relato_antigo_continua_servido(criar_cliente):
    c = criar_cliente()
    with SessionLocal() as s:
        RepositorioRelatos(s).criar(id='v' * 32, tipos=['roubo'], cell='0_0', quando=None, periodo=None, texto='',
                                    origem='chat', criado=instante_atual_ms() - 4000 * DIA_MS, chave_hash='0' * 64)
        s.commit()
    assert c.post(API + '/relatos', json=RELATO).status_code == 201
    assert c.get(API + '/relatos/' + 'v' * 32).status_code == 200


# ------------------------------------------------------------------ precisão no /config

def test_config_informa_a_precisao_da_hora_de_envio(criar_cliente):
    assert criar_cliente().get(API + '/config').json()['relatos']['precisao_criado'] == 'exata'
    assert criar_cliente(relatos_precisao_criado='hora').get(API + '/config').json()['relatos']['precisao_criado'] == 'hora'
