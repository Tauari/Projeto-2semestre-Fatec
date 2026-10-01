"""services/analise_padroes.contar_relatos: só contagem descritiva."""
from types import SimpleNamespace

from backend.services import analise_padroes
from backend.services.analise_padroes import contar_relatos


def test_vazio():
    assert contar_relatos([]) == {'total': 0, 'por_tipo': {}, 'por_periodo': {}, 'por_celula': {}}


def test_dicts_e_objetos():
    relatos = [
        {'tipos': ['assedio', 'perseguicao'], 'periodo': '20-22', 'cell': '3_-2'},
        {'tipos': ['assedio', 'assedio'], 'periodo': None, 'cell': '3_-2'},  # tipo repetido conta uma vez
        SimpleNamespace(tipos=['roubo'], periodo='manha', cell='0_0'),
        SimpleNamespace(tipos=['assedio'], periodo='20-22', celula='1_1'),  # ORM com "celula"
        {'tipos': [], 'cell': '0_0'},  # sem período
    ]
    r = contar_relatos(relatos)
    assert r == {
        'total': 5,
        'por_tipo': {'assedio': 3, 'perseguicao': 1, 'roubo': 1},
        'por_periodo': {'20-22': 2, 'manha': 1},
        'por_celula': {'3_-2': 2, '0_0': 2, '1_1': 1},
    }
    assert list(r) == ['total', 'por_tipo', 'por_periodo', 'por_celula']


def test_aceita_gerador_e_campos_ausentes():
    r = contar_relatos(x for x in [{'tipos': None}, SimpleNamespace()])
    assert r == {'total': 2, 'por_tipo': {}, 'por_periodo': {}, 'por_celula': {}}


def test_docstring_diz_que_e_so_descritivo():
    doc = analise_padroes.__doc__.lower()
    assert 'só contagem descritiva' in doc
    assert 'tendências' in doc and 'agrupamentos' in doc and 'risco' in doc
