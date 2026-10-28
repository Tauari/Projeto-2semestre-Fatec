"""Geografia, dados oficiais, percepção, rede de apoio e mapa de ruas: o servidor devolve os arquivos de
``dados/`` sem mudar nada (valores e ordem das chaves), e a carga no banco é idempotente."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from backend.database.repositorios import RepositorioDados
from backend.services.processamento_dados import carregar_dados_iniciais

API = '/api/v1'
RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / 'dados'
TABELAS_DE_DADOS = ('conjuntos_referencia', 'pontos_apoio', 'conjuntos_oficiais', 'oficiais_celulas',
                    'conjuntos_percepcao', 'percepcao_celulas')


def _ler(nome: str):
    return json.loads((DADOS / nome).read_bytes().decode('utf-8'))


def _texto(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)  # sort_keys=False: a ordem das chaves conta


def _montar_D(cliente) -> tuple[dict, dict, dict, dict]:
    """Como o ``carregarDados()`` do frontend monta o ``D`` no modo api."""
    cp = cliente.get(API + '/config').json()['conjuntos_padrao']
    geo = cliente.get(API + '/mapa/geografia').json()
    oficial = cliente.get(API + '/dados-oficiais/' + cp['dado_oficial']).json()
    percepcao = cliente.get(API + '/percepcao/' + cp['percepcao']).json()
    return {**geo['dados'], 'bo': oficial['dados'], 'pesq': percepcao['dados']}, geo, oficial, percepcao


def test_data_json_remontado_exatamente(cliente):
    original = _ler('data.json')
    D, geo, _, _ = _montar_D(cliente)
    assert D == original
    assert list(geo['dados']) == [k for k in original if k not in ('bo', 'pesq')]
    # na ordem do arquivo, o texto JSON é idêntico: mesma ordem de chaves em todos os níveis
    assert _texto({k: D[k] for k in original}) == _texto(original)


def test_celulas_na_ordem_original(cliente):
    original = _ler('data.json')
    D, _, _, _ = _montar_D(cliente)
    assert list(D['bo']['cells']) == list(original['bo']['cells'])
    assert list(D['pesq']['cells']) == list(original['pesq']['cells'])
    assert _texto(D['bo']['cells']) == _texto(original['bo']['cells'])
    assert _texto(D['pesq']['cells']) == _texto(original['pesq']['cells'])
    assert _texto(D['bo']) == _texto(original['bo'])
    assert _texto(D['pesq']) == _texto(original['pesq'])


def test_geografia_envelope(cliente):
    geo = cliente.get(API + '/mapa/geografia').json()
    assert list(geo) == ['tipo', 'gerado_em', 'fonte', 'notas', 'dados']
    assert geo['tipo'] == 'geografia'
    assert geo['gerado_em'] == _ler('data.json')['gerado']
    assert geo['fonte'] == 'dados/data.json'
    assert geo['notas'] and all(isinstance(n, str) and n for n in geo['notas'])


def test_apoio_igual_ao_arquivo(cliente):
    original = _ler('rede-de-apoio.json')
    r = cliente.get(API + '/apoio')
    assert r.status_code == 200
    apoio = r.json()
    assert list(apoio) == ['tipo', 'atualizado', 'nota', 'dados']
    assert apoio['tipo'] == 'rede_apoio'
    assert apoio['atualizado'] == original['atualizado']
    assert apoio['nota'] == original['nota']
    assert apoio['dados'] == original
    assert _texto(apoio['dados']) == _texto(original)
    assert [p['id'] for p in apoio['dados']['pontos']] == [p['id'] for p in original['pontos']]


def test_mapa_base_igual_ao_arquivo(cliente):
    r = cliente.get(API + '/mapa/base')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('application/json')
    assert r.headers['cache-control'] == 'no-cache'
    assert r.content == (DADOS / 'osm' / 'basemap.json').read_bytes()
    assert r.json() == _ler('osm/basemap.json')


def test_grafo_de_rotas_igual_ao_arquivo(cliente):
    r = cliente.get(API + '/mapa/rotas')
    assert r.status_code == 200
    assert r.content == (DADOS / 'rotas' / 'grafo.json').read_bytes()


def test_listas_de_conjuntos(cliente):
    oficiais = cliente.get(API + '/dados-oficiais').json()
    percepcao = cliente.get(API + '/percepcao').json()
    campos = ['chave', 'tipo_evidencia', 'titulo', 'periodo', 'fonte', 'gerado_em']
    assert [list(c) for c in oficiais['conjuntos']] == [campos]
    assert [list(c) for c in percepcao['conjuntos']] == [campos]
    bo, pesq = oficiais['conjuntos'][0], percepcao['conjuntos'][0]
    assert bo == {'chave': 'bo-ssp-2025-2026', 'tipo_evidencia': 'dado_oficial',
                  'titulo': 'Boletins de ocorrência (SSP-SP, base R.D.O. via FALASP)', 'periodo': _ler('data.json')['bo']['periodo'],
                  'fonte': 'Base R.D.O. da SSP-SP obtida via FALASP', 'gerado_em': '2026-09-24'}
    assert pesq['chave'] == 'pesquisa-percepcao-2026'
    assert pesq['tipo_evidencia'] == 'percepcao'
    assert pesq['titulo'] == 'Pesquisa “Segurança e percepção das mulheres em Rio Claro”'
    assert pesq['periodo'] == '10 set 2026 a 18 set 2026'
    assert pesq['gerado_em'] == '2026-09-24'


def test_detalhe_dos_conjuntos(cliente):
    for caminho, tipo in (('/dados-oficiais/bo-ssp-2025-2026', 'dado_oficial'), ('/percepcao/pesquisa-percepcao-2026', 'percepcao')):
        c = cliente.get(API + caminho).json()
        assert list(c) == ['chave', 'tipo_evidencia', 'titulo', 'periodo', 'fonte', 'gerado_em', 'avisos', 'dados']
        assert c['tipo_evidencia'] == tipo
        assert c['avisos'] and all(isinstance(a, str) and a for a in c['avisos'])
    bo = cliente.get(API + '/dados-oficiais/bo-ssp-2025-2026').json()
    assert '683 é a soma de três contadores e não garante 683 episódios ou pessoas distintas.' in bo['avisos']


@pytest.mark.parametrize('caminho', ['/dados-oficiais/naoexiste', '/percepcao/naoexiste',
                                     # um tipo de evidência não é servido como outro
                                     '/dados-oficiais/pesquisa-percepcao-2026', '/percepcao/bo-ssp-2025-2026',
                                     '/dados-oficiais/geografia-rio-claro', '/percepcao/rede-apoio-rio-claro'])
def test_conjunto_inexistente_404(cliente, caminho):
    r = cliente.get(API + caminho)
    assert r.status_code == 404
    assert isinstance(r.json()['detail'], str)


def test_evidencias_separadas(cliente, publicar):
    publicar(tipos=['assedio'], cell='0_0')
    publicar(tipos=['roubo'], cell='1_0')
    assert {c['tipo_evidencia'] for c in cliente.get(API + '/dados-oficiais').json()['conjuntos']} == {'dado_oficial'}
    assert cliente.get(API + '/dados-oficiais/bo-ssp-2025-2026').json()['tipo_evidencia'] == 'dado_oficial'
    assert {c['tipo_evidencia'] for c in cliente.get(API + '/percepcao').json()['conjuntos']} == {'percepcao'}
    assert cliente.get(API + '/percepcao/pesquisa-percepcao-2026').json()['tipo_evidencia'] == 'percepcao'
    assert cliente.get(API + '/relatos').json()['tipo_evidencia'] == 'relato_comunidade'
    resumo = cliente.get(API + '/dashboard/resumo').json()
    assert list(resumo) == ['relatos_comunidade', 'dados_oficiais', 'percepcao', 'classificacoes_automaticas', 'analise_ia']
    assert resumo['relatos_comunidade']['tipo_evidencia'] == 'relato_comunidade'
    assert [c['tipo_evidencia'] for c in resumo['dados_oficiais']] == ['dado_oficial']
    assert [c['tipo_evidencia'] for c in resumo['percepcao']] == ['percepcao']
    assert resumo['classificacoes_automaticas']['tipo_evidencia'] == 'classificacao_automatica'
    assert resumo['analise_ia'] == {'tipo_evidencia': 'analise_ia', 'implementado': False}
    # relatos nunca somados com B.O. nem com a pesquisa
    bo = _ler('data.json')['bo']
    assert resumo['relatos_comunidade']['total'] == 2
    assert resumo['relatos_comunidade']['por_celula'] == {'1_0': 1, '0_0': 1}
    assert resumo['dados_oficiais'][0]['total'] == bo['total']
    assert resumo['percepcao'][0]['respostas'] == _ler('data.json')['pesq']['n']


def _contagens(contar_linhas, s) -> dict[str, int]:
    return {k: v for k, v in contar_linhas(s).items() if k in TABELAS_DE_DADOS}


def test_carga_idempotente(cliente, sessao, contar_linhas):
    antes = _contagens(contar_linhas, sessao)
    original = _ler('data.json')
    assert antes == {'conjuntos_referencia': 2, 'pontos_apoio': len(_ler('rede-de-apoio.json')['pontos']),
                     'conjuntos_oficiais': 1, 'oficiais_celulas': len(original['bo']['cells']),
                     'conjuntos_percepcao': 1, 'percepcao_celulas': len(original['pesq']['cells'])}
    for _ in range(2):
        r = carregar_dados_iniciais(sessao, DADOS)
        assert r == {'data.json': 'inalterado', 'rede-de-apoio.json': 'inalterado', 'osm/basemap.json': 'presente'}
        assert _contagens(contar_linhas, sessao) == antes


def test_carga_refaz_quando_o_arquivo_muda(cliente, sessao, contar_linhas, tmp_path):
    pasta = tmp_path / 'dados'
    shutil.copytree(DADOS, pasta)
    antes = _contagens(contar_linhas, sessao)
    d = _ler('data.json')
    d['gerado'] = '2026-10-01'
    (pasta / 'data.json').write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
    r = carregar_dados_iniciais(sessao, pasta)
    assert r['data.json'] == 'carregado'
    assert r['rede-de-apoio.json'] == 'inalterado'
    assert _contagens(contar_linhas, sessao) == antes
    assert carregar_dados_iniciais(sessao, pasta)['data.json'] == 'inalterado'
    assert _contagens(contar_linhas, sessao) == antes
    geo = cliente.get(API + '/mapa/geografia').json()
    assert geo['gerado_em'] == '2026-10-01'
    assert geo['dados']['gerado'] == '2026-10-01'


def test_carga_em_banco_novo_duas_vezes(tmp_path, contar_linhas):
    from sqlalchemy.orm import Session

    from backend.database.sessao import criar_motor, criar_tabelas

    motor = criar_motor('sqlite:///' + (tmp_path / 'novo.db').as_posix())
    try:
        criar_tabelas(motor)
        with Session(motor) as s:
            primeira = carregar_dados_iniciais(s, DADOS)
            depois_da_primeira = _contagens(contar_linhas, s)
            segunda = carregar_dados_iniciais(s, DADOS)
            assert primeira == {'data.json': 'carregado', 'rede-de-apoio.json': 'carregado', 'osm/basemap.json': 'presente'}
            assert segunda == {'data.json': 'inalterado', 'rede-de-apoio.json': 'inalterado', 'osm/basemap.json': 'presente'}
            assert _contagens(contar_linhas, s) == depois_da_primeira
            assert len(RepositorioDados(s).bairros()) == len(_ler('data.json')['bairros'])
    finally:
        motor.dispose()


def test_sem_carga_automatica(criar_cliente):
    c = criar_cliente(carga_automatica=False)
    assert c.get(API + '/mapa/geografia').status_code == 404
    assert c.get(API + '/apoio').status_code == 404
    assert c.get(API + '/dados-oficiais').json() == {'conjuntos': []}
    assert c.get(API + '/percepcao').json() == {'conjuntos': []}
    assert c.get(API + '/mapa/base').status_code == 200  # o mapa de ruas vem do arquivo, não do banco
    # sem geografia, a extração segue sem bairros
    r = c.post(API + '/ia/extrair', json={'texto': 'me seguiram perto da unesp ontem'})
    assert r.status_code == 200
    assert r.json()['resultado']['bairro'] is None


def test_pasta_de_dados_vazia(criar_cliente, tmp_path):
    vazia = tmp_path / 'vazia'
    vazia.mkdir()
    c = criar_cliente(pasta_dados=str(vazia))
    for caminho in ('/mapa/geografia', '/apoio', '/mapa/base', '/dados-oficiais/bo-ssp-2025-2026'):
        r = c.get(API + caminho)
        assert r.status_code == 404
        assert isinstance(r.json()['detail'], str)
    assert c.get(API + '/saude').status_code == 200
