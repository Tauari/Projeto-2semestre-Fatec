"""Retenção dos relatos: por padrão nada é apagado; com prazo, os antigos saem junto com as classificações."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.database.repositorios import DIA_MS, RepositorioClassificacoes, RepositorioRelatos, instante_atual_ms
from backend.database.sessao import SessionLocal
from backend.main import create_app
from backend.services.retencao import aplicar_retencao

API = '/api/v1'


def _classificar(sessao, relato):
    RepositorioClassificacoes(sessao).criar(relato_id=relato.id, provedor='heuristica', modelo=None, tipos=['roubo'],
                                            urgente=False, quando=None, periodo=None, confianca=None, criado=relato.criado)
    sessao.commit()


def test_sem_prazo_nada_e_apagado(cliente, sessao, inserir_relato):
    agora = instante_atual_ms()
    antigo = inserir_relato(agora - 4000 * DIA_MS)
    _classificar(sessao, antigo)
    assert aplicar_retencao(sessao) == 0
    assert aplicar_retencao(sessao, agora_ms=agora + 10_000 * DIA_MS) == 0
    assert RepositorioRelatos(sessao).obter(antigo.id) is not None
    assert RepositorioClassificacoes(sessao).contar() == 1
    assert cliente.get(API + '/relatos/' + antigo.id).status_code == 200


def test_com_prazo_apaga_os_antigos_e_as_classificacoes(configurar, cliente, sessao, inserir_relato):
    agora = instante_atual_ms()
    antigo = inserir_relato(agora - 31 * DIA_MS)
    no_limite = inserir_relato(agora - 30 * DIA_MS)
    recente = inserir_relato(agora - 1 * DIA_MS)
    for r in (antigo, no_limite, recente):
        _classificar(sessao, r)
    configurar(relatos_retencao_dias=30)
    assert aplicar_retencao(sessao, agora_ms=agora) == 1
    sessao.expire_all()
    repo = RepositorioRelatos(sessao)
    assert repo.obter(antigo.id) is None
    assert repo.obter(no_limite.id) is not None
    assert repo.obter(recente.id) is not None
    classificacoes = RepositorioClassificacoes(sessao)
    assert classificacoes.do_relato(antigo.id) == []
    assert len(classificacoes.do_relato(no_limite.id)) == 1
    assert classificacoes.contar() == 2
    assert cliente.get(API + '/relatos/' + antigo.id).status_code == 404
    # rodar de novo não apaga mais nada
    assert aplicar_retencao(sessao, agora_ms=agora) == 0


def test_retencao_roda_na_inicializacao(configurar):
    configurar()
    agora = instante_atual_ms()
    with TestClient(create_app()) as c:
        with SessionLocal() as s:
            antigo = RepositorioRelatos(s).criar(id='a' * 32, tipos=['roubo'], cell='0_0', quando=None, periodo=None, texto='',
                                                 origem='chat', criado=agora - 100 * DIA_MS, chave_hash='0' * 64)
            s.commit()
            _classificar(s, antigo)
        assert c.get(API + '/relatos/' + 'a' * 32).status_code == 200
    # sem prazo, reiniciar não apaga nada
    with TestClient(create_app()) as c:
        assert c.get(API + '/relatos/' + 'a' * 32).status_code == 200
    configurar(relatos_retencao_dias=90)
    with TestClient(create_app()) as c:
        assert c.get(API + '/relatos/' + 'a' * 32).status_code == 404
        with SessionLocal() as s:
            assert RepositorioClassificacoes(s).contar() == 0
