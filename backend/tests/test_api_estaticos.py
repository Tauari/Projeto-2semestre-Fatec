"""Arquivos estáticos: o frontend em /, o Leaflet em /vendor, nada de dados/ fora das rotas da API, e /api
nunca cai no frontend."""
from __future__ import annotations

from pathlib import Path

import pytest

API = '/api/v1'
RAIZ = Path(__file__).resolve().parents[2]
INDEX = RAIZ / 'frontend' / 'index.html'
CONTEUDOS_PROTEGIDOS = [(RAIZ / 'dados' / n).read_bytes() for n in ('data.json', 'rede-de-apoio.json', 'osm/basemap.json')]


@pytest.mark.parametrize('caminho', [
    '/dados/data.json', '/dados/rede-de-apoio.json', '/dados/osm/basemap.json', '/dados/', '/dados/LEIA-ME-DADOS.md',
    '/../dados/data.json', '/..%2Fdados%2Fdata.json', '/%2e%2e/dados/data.json', '/..%5Cdados%5Cdata.json',
    '/vendor/../dados/data.json', '/vendor/..%2F..%2Fdados%2Fdata.json', '/vendor/..%5C..%5Cdados%5Cdata.json',
    '/frontend/../dados/data.json', '/src/app.js', '/backend/config.py', '/.venv/pyvenv.cfg',
])
def test_dados_e_codigo_nao_sao_servidos(cliente, caminho):
    r = cliente.get(caminho)
    assert r.status_code == 404
    assert r.content not in CONTEUDOS_PROTEGIDOS
    assert b'"bo"' not in r.content and b'"pontos"' not in r.content


@pytest.mark.parametrize('metodo,caminho', [('GET', '/api/v1/naoexiste'), ('GET', '/api/naoexiste'), ('GET', '/api'),
                                            ('GET', '/api/'), ('GET', '/api/v1'), ('GET', '/api/v1/index.html'),
                                            ('POST', '/api/v1/naoexiste'), ('DELETE', '/api/v1/relatos')])
def test_api_desconhecida_e_404_em_json(cliente, metodo, caminho):
    r = cliente.request(metodo, caminho)
    assert r.status_code in (404, 405)
    assert r.headers['content-type'].startswith('application/json')
    assert r.json()['detail'] in ('Recurso não encontrado.', 'Método não permitido.')
    assert b'<html' not in r.content.lower()


def test_api_nunca_cai_no_frontend(criar_cliente, tmp_path):
    # um frontend com 404.html e até uma pasta api/: nada disso pode responder por /api
    pasta = tmp_path / 'frontend'
    (pasta / 'api' / 'v1').mkdir(parents=True)
    (pasta / 'index.html').write_text('<html>index</html>', encoding='utf-8')
    (pasta / '404.html').write_text('<html>404 do frontend</html>', encoding='utf-8')
    (pasta / 'api' / 'v1' / 'naoexiste').write_text('<html>arquivo</html>', encoding='utf-8')
    (pasta / 'api' / 'index.html').write_text('<html>api</html>', encoding='utf-8')
    c = criar_cliente(pasta_frontend=str(pasta))
    for caminho in ('/api/v1/naoexiste', '/api/v1/outra', '/api', '/api/'):
        r = c.get(caminho)
        assert r.status_code == 404, caminho
        assert r.json() == {'detail': 'Recurso não encontrado.'}
    assert c.put(API + '/saude').status_code == 405
    assert c.get(API + '/saude').json()['status'] == 'ok'
    # fora de /api, o frontend responde normalmente, com o 404.html dele
    assert c.get('/').text == '<html>index</html>'
    r = c.get('/pagina-que-nao-existe')
    assert r.status_code == 404
    assert r.text == '<html>404 do frontend</html>'


def test_rota_desconhecida_da_api_nao_devolve_o_index(cliente):
    r = cliente.get('/api/v1/naoexiste')
    assert r.status_code == 404
    assert r.json() == {'detail': 'Recurso não encontrado.'}


def test_metodo_errado_na_api_e_405(cliente):
    r = cliente.put(API + '/saude')
    assert r.status_code == 405
    assert r.json() == {'detail': 'Método não permitido.'}


def test_frontend_na_raiz(cliente):
    if not INDEX.is_file():
        pytest.skip('frontend/index.html ainda não existe')
    r = cliente.get('/')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/html')
    assert r.content == INDEX.read_bytes()


def test_modulos_do_frontend(cliente):
    main = RAIZ / 'frontend' / 'main.js'
    if not main.is_file():
        pytest.skip('frontend/main.js ainda não existe')
    r = cliente.get('/main.js')
    assert r.status_code == 200
    assert 'javascript' in r.headers['content-type']
    assert r.content == main.read_bytes()


def test_vendor_leaflet(cliente):
    r = cliente.get('/vendor/leaflet.css')
    assert r.status_code == 200
    assert r.headers['content-type'].startswith('text/css')
    assert r.content == (RAIZ / 'vendor' / 'leaflet.css').read_bytes()


def test_sem_servir_frontend(criar_cliente):
    c = criar_cliente(servir_frontend=False)
    assert c.get('/').status_code == 404
    assert c.get('/vendor/leaflet.css').status_code == 404
    assert c.get(API + '/saude').status_code == 200


def test_pasta_do_frontend_ausente(criar_cliente, tmp_path):
    c = criar_cliente(pasta_frontend=str(tmp_path / 'nao-existe'))
    assert c.get('/').status_code == 404
    assert c.get('/vendor/leaflet.css').status_code == 200
    assert c.get(API + '/saude').status_code == 200


def test_cors_desligado_por_padrao(cliente):
    r = cliente.get(API + '/saude', headers={'Origin': 'http://exemplo.test'})
    assert 'access-control-allow-origin' not in r.headers


def test_cors_configurado(criar_cliente):
    c = criar_cliente(cors_origens=['http://localhost:8080'])
    r = c.options(API + '/relatos', headers={'Origin': 'http://localhost:8080', 'Access-Control-Request-Method': 'DELETE',
                                             'Access-Control-Request-Headers': 'X-Chave-Exclusao'})
    assert r.status_code == 200
    assert r.headers['access-control-allow-origin'] == 'http://localhost:8080'
    r = c.get(API + '/saude', headers={'Origin': 'http://outro.test'})
    assert 'access-control-allow-origin' not in r.headers
