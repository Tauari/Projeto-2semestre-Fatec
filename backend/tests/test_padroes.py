"""US-02: padrões por região, período e tipo; evidência em cada achado; dados insuficientes ditos; nada de previsão."""
from types import SimpleNamespace as NS

import httpx
import pytest

from backend.config import obter_configuracoes
from backend.services import padroes as P
from backend.services.classificacao import bairros_de_lista
from backend.services.ia import obter_provedor
from backend.tests.conftest import API

HEX = {'lat0': -22.41, 'lng0': -47.56, 'R': 500.0}
BAIRROS = bairros_de_lista([['Centro', -22.4074, -47.5632, 10], ['Bela Vista', -22.4059, -47.552, 8]])


def relato(cell, tipos, periodo=None):
    return NS(cell=cell, tipos=tipos, periodo=periodo, quando='hoje')


def analisar(relatos, oficiais=(), percepcoes=()):
    return P.analisar(list(relatos), list(oficiais), list(percepcoes), HEX, BAIRROS, 30)


def test_poucos_relatos_dizem_que_ha_dados_insuficientes():
    r = analisar([relato('f0_0', ['assedio'], '20-22')] * 3)
    assert r['fontes'][0]['situacao'] == 'insuficiente' and r['padroes'] == []
    assert {i['dimensao'] for i in r['insuficiente']} == {'regiao', 'periodo', 'tipo'}
    assert 'Só há 3 relatos' in r['insuficiente'][0]['motivo']
    assert 'não há dados suficientes' in P.narrativa_padrao(r)


def test_detecta_tipo_periodo_e_regiao_com_a_evidencia():
    rel = ([relato('f0_0', ['assedio'], '20-22')] * 8 + [relato('f0_0', ['roubo'], '20-22')] * 2 +
           [relato('f6_6', ['ambiente'], 'tarde')] * 3 + [relato('f9_9', ['assedio'], '20-22')] * 2)
    r = analisar(rel)
    por_id = {p['id']: p for p in r['padroes']}
    tipo = por_id['relatos-tipo']
    assert tipo['evidencia'] == {'n': 10, 'de': 15, 'pct': 67} and 'Assédio verbal' in tipo['titulo']
    assert por_id['relatos-periodo']['evidencia'] == {'n': 12, 'de': 15, 'pct': 80} and por_id['relatos-periodo']['dimensoes'] == ['periodo']
    assert any(p['dimensoes'] == ['regiao', 'tipo'] and p['areas'] for p in r['padroes'])
    assert all(p['confianca'] in ('baixa', 'media', 'alta') and p['evidencia']['de'] > 0 for p in r['padroes'])


def test_so_horario_com_amostra_minima():
    rel = [relato('f0_0', ['assedio'], '20-22')] * 5 + [relato('f0_0', ['roubo'])] * 6  # 11 relatos, só 5 com horário
    r = analisar(rel)
    assert any(i['dimensao'] == 'periodo' and 'informa' in i['motivo'] for i in r['insuficiente'])
    assert not any('periodo' in p['dimensoes'] for p in r['padroes'])


def test_historico_sem_horario_e_dito_e_dados_com_posicao_geram_padroes():
    celulas = [NS(celula=f'{i}_0', n=n, dados={'vd': n, 'fe': 0, 'te': 0, 'b': [[f'Bairro {i}', n]]}) for i, n in enumerate([30, 20, 10, 5, 5])]
    bo = NS(chave='bo', titulo='B.O.', periodo='jan/2025 a abr/2026', celulas=celulas)
    r = analisar([], [bo])
    assert any(i['dimensao'] == 'periodo' and 'sem dia nem horário' in i['motivo'] for i in r['insuficiente'])
    assert any(p['id'] == 'historico-regiao' for p in r['padroes'])


def test_nenhum_texto_gerado_promete_futuro():
    r = analisar([relato('f0_0', ['assedio'], '20-22')] * 12)
    textos = [p['descricao'] + p['titulo'] for p in r['padroes']] + [i['motivo'] for i in r['insuficiente']]
    assert not any(P.PROIBIDAS.search(t) for t in textos)
    resumo = P.narrativa_padrao(r).replace('não prevê o que vai acontecer', '')  # a única menção ao futuro é a negação
    assert not P.PROIBIDAS.search(resumo) and 'não prevê' in P.narrativa_padrao(r)


def test_resumo_de_modelo_so_vale_sem_futuro_sem_numero_novo_e_sem_misturar_fontes():
    r = analisar([relato('f0_0', ['assedio'], '20-22')] * 12)
    n = r['padroes'][0]['evidencia']
    ok = f'Nos dados, {n["n"]} dos {n["de"]} relatos ({n["pct"]}%) são de assédio verbal.'
    assert P.resumo_valido(ok, r)
    assert not P.resumo_valido(ok + ' Isso vai acontecer de novo.', r)
    assert not P.resumo_valido(ok + ' Certamente continuará.', r)
    assert not P.resumo_valido('Nos dados, 77 relatos são de assédio verbal.', r)
    assert not P.resumo_valido('A maioria dos relatos é de violência doméstica.', r)
    assert not P.resumo_valido('', r)


def test_rota_com_dados_reais_do_projeto(cliente):
    r = cliente.get(API + '/analise/padroes')
    assert r.status_code == 200
    j = r.json()
    assert j['tipo_evidencia'] == 'analise_ia' and j['usa_modelo'] is False and j['provedor'] == 'heuristica'
    assert any(f['id'].startswith('historico') for f in j['fontes'])
    assert any(i['dimensao'] == 'periodo' for i in j['insuficiente'])  # B.O. sem horário
    assert any('regiao' in p['dimensoes'] for p in j['padroes'])
    assert any('não indicam nem preveem' in a.lower() for a in j['avisos'])
    assert 'não prevê' in j['resumo']


@pytest.fixture
def ollama(monkeypatch):
    monkeypatch.setenv('AURORA_IA_PROVEDOR', 'ollama')
    obter_configuracoes.cache_clear()
    import backend.services.ia.ollama as O
    O._RESUMOS.clear()
    yield obter_provedor()
    obter_configuracoes.cache_clear()


def _modelo(texto):
    return lambda *a, **k: httpx.Response(200, json={'response': texto}, request=httpx.Request('POST', 'http://x'))


def test_ollama_resumo_valido_e_aceito_e_invalido_cai_nas_regras(ollama, monkeypatch):
    r = analisar([relato('f0_0', ['assedio'], '20-22')] * 12)
    n = r['padroes'][0]['evidencia']
    bom = f'Nos dados, {n["n"]} dos {n["de"]} relatos ({n["pct"]}%) são de assédio verbal.'
    monkeypatch.setattr(httpx, 'post', _modelo(bom))
    assert ollama.analisar_padroes(r) == (bom, True)
    import backend.services.ia.ollama as O
    O._RESUMOS.clear()
    monkeypatch.setattr(httpx, 'post', _modelo(bom + ' Vai acontecer amanhã.'))
    texto, por_modelo = ollama.analisar_padroes(r)
    assert por_modelo is False and texto == P.narrativa_padrao(r)


def test_ollama_desligado_usa_regras(ollama, monkeypatch):
    def quebra(*a, **k):
        raise httpx.ConnectError('desligado')
    monkeypatch.setattr(httpx, 'post', quebra)
    r = analisar([relato('f0_0', ['assedio'], '20-22')] * 12)
    assert ollama.analisar_padroes(r) == (P.narrativa_padrao(r), False)
