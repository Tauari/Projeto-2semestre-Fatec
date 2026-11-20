"""Contas individuais, papéis, sessões e proteção das ações da equipe."""
import pytest
from sqlalchemy import select

API = '/api/v1'
CAB = {'X-Aurora-Equipe': '1'}
SENHA = 'senha-ficticia-para-os-testes'


@pytest.fixture
def admin(cliente):
    from backend.database import sessao as banco
    from backend.services.equipe import criar_primeiro_admin
    with banco.SessionLocal() as s:
        criar_primeiro_admin(s, 'responsavel', SENHA)
    r = cliente.post(API + '/usuarios/entrar', json={'login': 'responsavel', 'senha': SENHA}, headers=CAB)
    assert r.status_code == 200, r.text
    return cliente


def criar(c, login='revisora', papel='moderacao'):
    return c.post(API + '/usuarios/equipe', headers=CAB, json={'login': login, 'senha': SENHA, 'papel': papel})


def test_bootstrap_unico_e_hash(admin):
    from backend.database import sessao as banco
    from backend.database.tabelas import CredencialEquipe
    from backend.services.equipe import criar_primeiro_admin
    with banco.SessionLocal() as s:
        with pytest.raises(ValueError, match='administrador'):
            criar_primeiro_admin(s, 'outro', SENHA)
        conta = s.scalar(select(CredencialEquipe))
        assert SENHA not in conta.senha_hash
    assert admin.get(API + '/usuarios/eu').json()['papeis'] == ['administrador', 'moderacao']


def test_admin_cria_moderador_sem_permissao_para_cadastrar(admin):
    r = criar(admin)
    assert r.status_code == 201
    assert 'senha' not in r.text
    assert criar(admin, login='REVISORA').status_code == 409
    assert admin.post(API + '/usuarios/sair', headers=CAB).status_code == 204
    assert admin.post(API + '/usuarios/entrar', headers=CAB,
                      json={'login': 'revisora', 'senha': SENHA}).status_code == 200
    assert admin.get(API + '/moderacao').status_code == 200
    assert admin.get(API + '/usuarios/equipe').status_code == 403
    assert criar(admin, login='intruso', papel='administrador').status_code == 403


def test_csrf_e_logout_revogam_sessao(admin):
    cookie = admin.cookies.get('aurora_equipe')
    assert admin.post(API + '/usuarios/equipe', json={'login': 'outro', 'senha': SENHA}).status_code == 403
    assert admin.post(API + '/usuarios/sair', headers=CAB).status_code == 204
    assert admin.get(API + '/moderacao', headers={'Cookie': 'aurora_equipe=' + cookie}).status_code == 401


def test_desativar_revoga_acesso_e_protege_propria_conta(admin):
    from fastapi.testclient import TestClient
    r = criar(admin).json()
    with TestClient(admin.app) as revisor:
        revisor.post(API + '/usuarios/entrar', headers=CAB, json={'login': 'revisora', 'senha': SENHA})
        assert revisor.get(API + '/moderacao').status_code == 200
        assert admin.post(API + '/usuarios/equipe/' + r['id'] + '/ativo', headers=CAB, json={'ativo': False}).status_code == 200
        assert revisor.get(API + '/moderacao').status_code == 401
        assert revisor.post(API + '/usuarios/entrar', headers=CAB,
                             json={'login': 'revisora', 'senha': SENHA}).status_code == 401
    eu = admin.get(API + '/usuarios/eu').json()['usuario']
    assert admin.post(API + '/usuarios/equipe/' + eu['id'] + '/ativo', headers=CAB, json={'ativo': False}).status_code == 409


def test_cookie_seguro_e_expiracao(admin, configurar):
    from backend.database import sessao as banco
    from backend.database.tabelas import SessaoEquipe
    configurar(sessao_cookie_seguro=True)
    r = admin.post(API + '/usuarios/entrar', headers=CAB, json={'login': 'responsavel', 'senha': SENHA})
    cookie = r.headers['set-cookie'].lower()
    token = r.cookies.get('aurora_equipe')
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'secure' in cookie
    with banco.SessionLocal() as s:
        for sessao in s.scalars(select(SessaoEquipe)):
            sessao.expira_em = 0
        s.commit()
    assert admin.get(API + '/moderacao', headers={'Cookie': 'aurora_equipe=' + token}).status_code == 401


def test_limita_tentativas_e_erro_generico(cliente):
    for _ in range(10):
        r = cliente.post(API + '/usuarios/entrar', headers=CAB, json={'login': 'desconhecida', 'senha': 'incorreta'})
        assert r.status_code == 401
        assert r.json()['detail'] == 'Usuário ou senha inválidos.'
    assert cliente.post(API + '/usuarios/entrar', headers=CAB,
                        json={'login': 'desconhecida', 'senha': 'incorreta'}).status_code == 429


def test_auditoria_registra_quem_moderou(admin):
    from backend.database import sessao as banco
    from backend.database.tabelas import AcaoModeracao
    r = admin.post(API + '/relatos', json={'tipos': ['assedio'], 'cell': '0_0'}).json()['relato']
    eu = admin.get(API + '/usuarios/eu').json()['usuario']
    assert admin.post(API + '/moderacao/' + r['id'], headers=CAB, json={'campo': 'oculto', 'valor': True}).status_code == 200
    with banco.SessionLocal() as s:
        assert s.scalar(select(AcaoModeracao)).usuario_id == eu['id']
