"""Moderação autenticada, persistência e visibilidade nas consultas públicas."""
import pytest

API = '/api/v1'
SENHA = 'senha-ficticia-para-os-testes'
AUTH = {'X-Aurora-Equipe': '1'}


@pytest.fixture
def moderador(criar_cliente):
    c = criar_cliente()
    from backend.database import sessao as banco
    from backend.services.equipe import criar_primeiro_admin
    with banco.SessionLocal() as s:
        criar_primeiro_admin(s, 'responsavel', SENHA)
    c.post(API + '/usuarios/entrar', headers=AUTH, json={'login': 'responsavel', 'senha': SENHA})
    return c


def publicar(c):
    return c.post(API + '/relatos', json={'tipos': ['assedio'], 'cell': '0_0', 'texto': 'Relato de teste.'}).json()['relato']


def agir(c, id, campo, valor):
    return c.post(API + '/moderacao/' + id, headers=AUTH, json={'campo': campo, 'valor': valor})


def test_sem_configuracao_nao_libera_moderacao(cliente):
    assert cliente.get(API + '/moderacao', headers=AUTH).status_code == 401


@pytest.mark.parametrize('headers', [{}, {'Authorization': 'Bearer errada'}, {'Authorization': 'Basic abc'}])
def test_exige_sessao_no_servidor(moderador, headers):
    r = publicar(moderador)
    moderador.cookies.clear()
    assert moderador.get(API + '/moderacao', headers=headers).status_code == 401
    assert moderador.post(API + '/moderacao/' + r['id'], headers=headers,
                          json={'campo': 'oculto', 'valor': True}).status_code == 401
    assert moderador.get(API + '/relatos/' + r['id']).status_code == 200


def test_ocultar_mostrar_e_verificar_persistem(moderador, criar_cliente):
    r = publicar(moderador)
    id = r['id']
    assert agir(moderador, id, 'verificado', True).status_code == 200
    assert moderador.get(API + '/moderacao/estado').json()['verificado'] == {id: True}
    assert agir(moderador, id, 'oculto', True).status_code == 200
    assert moderador.get(API + '/relatos').json()['relatos'] == []
    assert moderador.get(API + '/relatos/' + id).status_code == 404
    assert moderador.get(API + '/dashboard/resumo').json()['relatos_comunidade']['total'] == 0
    assert moderador.get(API + '/moderacao/estado').json()['verificado'] == {}
    # Uma nova aplicação/sessão lê a decisão do banco, não do navegador.
    outro = criar_cliente()
    outro.cookies.update(moderador.cookies)
    res = outro.get(API + '/moderacao', headers=AUTH)
    assert res.status_code == 200 and res.headers['cache-control'] == 'no-store'
    assert res.json()['relatos'] == [r]
    assert res.json()['mod'] == {'oculto': {id: True}, 'verificado': {id: True}}
    assert 'chave_hash' not in res.text and SENHA not in res.text
    assert agir(outro, id, 'oculto', False).status_code == 200
    assert outro.get(API + '/relatos').json()['relatos'] == [r]
    assert agir(outro, id, 'verificado', False).status_code == 200
    assert outro.get(API + '/moderacao/estado').json()['verificado'] == {}


@pytest.mark.parametrize('body', [{'campo': 'admin', 'valor': True}, {'campo': 'oculto', 'valor': 'false'},
                                  {'campo': 'oculto', 'valor': True, 'extra': 1}])
def test_valida_acao(moderador, body):
    r = publicar(moderador)
    assert moderador.post(API + '/moderacao/' + r['id'], headers=AUTH, json=body).status_code == 422


def test_relato_ausente_e_retencao(moderador, configurar):
    assert agir(moderador, 'inexistente', 'oculto', True).status_code == 404
    from backend.database import sessao as banco
    from backend.database.repositorios import RepositorioRelatos, DIA_MS, instante_atual_ms
    with banco.SessionLocal() as s:
        RepositorioRelatos(s).criar(id='antigo', tipos=['assedio'], cell='0_0', quando=None, periodo=None,
                                  texto='', origem='chat', criado=instante_atual_ms() - 40 * DIA_MS, chave_hash='teste')
        s.commit()
    configurar(relatos_retencao_dias=30)
    assert moderador.get(API + '/moderacao', headers=AUTH).json()['relatos'] == []
    assert agir(moderador, 'antigo', 'oculto', True).status_code == 404


def test_config_publica_nao_expoe_chave(moderador):
    r = moderador.get(API + '/config')
    assert r.json()['modulos']['moderacao'] is True
    assert SENHA not in r.text


def test_autora_pode_apagar_relato_oculto(moderador):
    publicado = moderador.post(API + '/relatos', json={'tipos': ['assedio'], 'cell': '0_0'}).json()
    id = publicado['relato']['id']
    assert agir(moderador, id, 'oculto', True).status_code == 200
    assert moderador.delete(API + '/relatos/' + id,
                           headers={'X-Chave-Exclusao': publicado['chave_exclusao']}).status_code == 204
    assert moderador.get(API + '/moderacao', headers=AUTH).json()['relatos'] == []


def test_rota_do_painel(cliente):
    r = cliente.get('/moderacao', follow_redirects=False)
    assert r.status_code == 307
    assert r.headers['location'] == '/#moderacao'
