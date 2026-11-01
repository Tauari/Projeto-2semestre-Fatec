"""GET /alertas: alertas recentes com título padrão, área e posição, sem o texto da usuária."""
from __future__ import annotations

import pytest

from backend.database.repositorios import instante_atual_ms

API = '/api/v1'
FINA = 'f10_4'
HORA = 3_600_000
CAMPOS = ['id', 'tipo', 'titulo', 'cell', 'lat', 'lng', 'area', 'criado']


def test_sem_relatos_lista_vazia(cliente):
    r = cliente.get(API + '/alertas')
    assert r.status_code == 200
    assert r.json() == {'tipo_evidencia': 'relato_comunidade', 'janela_horas': 6, 'alertas': []}


def test_alerta_traz_titulo_area_e_posicao(cliente, publicar):
    publicar(tipos=['assedio'], cell=FINA, texto='Fui assediada por um homem de camiseta preta e calça roxa')
    (a,) = cliente.get(API + '/alertas').json()['alertas']
    assert list(a) == CAMPOS
    assert a['titulo'] == 'Potencial assediador na área' and a['tipo'] == 'assedio' and a['cell'] == FINA
    assert -23.0 < a['lat'] < -22.0 and -48.0 < a['lng'] < -47.0  # Rio Claro
    assert a['area'].startswith(('Perto de', 'Zona rural'))


def test_o_texto_da_usuaria_nunca_vai(cliente, publicar):
    publicar(tipos=['assedio'], cell=FINA, texto='Fui assediada por um homem de camiseta preta e calça roxa')
    corpo = cliente.get(API + '/alertas').text
    assert 'camiseta' not in corpo and 'roxa' not in corpo and 'texto' not in corpo


def test_rua_escura_nao_e_alerta(cliente, publicar):
    publicar(tipos=['ambiente'], cell=FINA)
    publicar(tipos=['ambiente', 'roubo'], cell=FINA)
    assert [a['tipo'] for a in cliente.get(API + '/alertas').json()['alertas']] == ['roubo']


def test_so_a_janela_pedida_e_do_mais_novo_para_o_mais_antigo(cliente, inserir_relato):
    agora = instante_atual_ms()
    inserir_relato(agora - 10 * HORA, tipos=['roubo'], cell=FINA)
    novo = inserir_relato(agora - 1 * HORA, tipos=['assedio'], cell=FINA)
    medio = inserir_relato(agora - 3 * HORA, tipos=['violencia'], cell=FINA)
    ids = [a['id'] for a in cliente.get(API + '/alertas').json()['alertas']]
    assert ids == [novo.id, medio.id]
    assert len(cliente.get(API + '/alertas', params={'janela_horas': 24}).json()['alertas']) == 3


@pytest.mark.parametrize('horas', [0, -1, 73, 'abc'])
def test_janela_invalida_422(cliente, horas):
    assert cliente.get(API + '/alertas', params={'janela_horas': horas}).status_code == 422
