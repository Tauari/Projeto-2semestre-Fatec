from __future__ import annotations

import pytest

API = '/api/v1'
CAB = {'X-Aurora-Equipe': '1'}
SENHA = 'senha-ficticia-para-os-testes'


@pytest.fixture
def admin(cliente):
    """Cliente já logado como administrador da equipe (cookie de sessão); o Observatório usa esse login."""
    from backend.database import sessao as banco
    from backend.services.equipe import criar_primeiro_admin
    with banco.SessionLocal() as s:
        criar_primeiro_admin(s, 'responsavel', SENHA)
    r = cliente.post(API + '/usuarios/entrar', json={'login': 'responsavel', 'senha': SENHA}, headers=CAB)
    assert r.status_code == 200, r.text
    return cliente


def test_rotas_bloqueadas_sem_login(cliente):
    """Sem login da equipe, toda rota do Observatório responde 401."""
    # Relatórios do Observatório
    r_rel = cliente.get(f'{API}/observatorio/relatorios')
    assert r_rel.status_code == 401

    # Retornos da Secretaria
    r_ret = cliente.get(f'{API}/observatorio/retornos')
    assert r_ret.status_code == 401

    # Registros de Despacho
    r_dsp = cliente.post(
        f'{API}/observatorio/retornos/ret-01/despachos',
        headers=CAB,
        json={
            'orgao': 'Secretaria da Mulher',
            'status_novo': 'em_acompanhamento',
            'parecer_tecnico': 'Atendimento presencial realizado.',
            'encaminhamentos': ['CAM']
        }
    )
    assert r_dsp.status_code == 401

    # Desbloqueio LGPD
    r_sig = cliente.post(
        f'{API}/observatorio/retornos/ret-01/desbloquear-sigilo',
        json={'justificativa': 'Necessidade de intimação urgente.'}
    )
    assert r_sig.status_code == 401

    # Exportação de Dados
    r_csv = cliente.get(f'{API}/observatorio/exportar/csv')
    assert r_csv.status_code == 401

    r_pdf = cliente.get(f'{API}/observatorio/exportar/pdf')
    assert r_pdf.status_code == 401


def test_senha_fixa_do_codigo_antigo_nao_entra(cliente):
    """As credenciais que existiam escritas no código não funcionam mais."""
    assert cliente.post(f'{API}/usuarios/login', json={'login': 'admin', 'senha': 'admin'}).status_code in (404, 405)
    r = cliente.get(f'{API}/observatorio/relatorios', headers={'X-Admin-Token': 'aurora_admin_token_master_2026'})
    assert r.status_code == 401


def test_equipe_sem_papel_de_administrador_recebe_403(admin):
    assert admin.post(API + '/usuarios/equipe', headers=CAB,
                      json={'login': 'revisora', 'senha': SENHA, 'papel': 'moderacao'}).status_code == 201
    admin.post(API + '/usuarios/sair', headers=CAB)
    assert admin.post(API + '/usuarios/entrar', headers=CAB, json={'login': 'revisora', 'senha': SENHA}).status_code == 200
    assert admin.get(f'{API}/observatorio/relatorios').status_code == 403


def test_relatorio_observatorio_com_admin(admin):
    cliente = admin
    """Acesso aos relatórios estruturados pelo Observatório com token de admin."""
    headers = {}
    r = cliente.get(f'{API}/observatorio/relatorios', headers=headers)
    assert r.status_code == 200
    corpo = r.json()

    # Validação dos KPIs
    assert 'kpis' in corpo
    kpis = corpo['kpis']
    assert kpis['total_ocorrencias'] > 0
    assert 'violencia_domestica_pct' in kpis
    assert 'via_publica_pct' in kpis
    assert 'bairro_mais_critico' in kpis

    # Validação das ocorrências filtradas
    assert len(corpo['ocorrencias']) > 0
    primeira = corpo['ocorrencias'][0]
    assert 'protocolo' in primeira
    assert 'tipo_label' in primeira
    assert 'bairro' in primeira

    # Teste de filtro textual
    r_filtro = cliente.get(f'{API}/observatorio/relatorios?busca=Cervezão', headers=headers)
    assert r_filtro.status_code == 200
    for item in r_filtro.json()['ocorrencias']:
        assert 'cervezão' in item['bairro'].lower() or 'cervezão' in item['descricao_anonima'].lower()


def test_retornos_secretaria_lgpd_e_desbloqueio(admin):
    cliente = admin
    """Acesso restrito a retornos com mascaramento de dados sensíveis e auditoria LGPD."""
    headers = CAB

    # 1. Consulta inicial com proteção LGPD (nome e telefone mascarados)
    r = cliente.get(f'{API}/observatorio/retornos', headers=headers)
    assert r.status_code == 200
    casos = r.json()
    assert len(casos) > 0
    caso = next(c for c in casos if c['id'] == 'ret-01')
    assert caso['vitima_nome_completo'] is None
    assert caso['vitima_telefone_protegido'] is None
    assert caso['vitima_iniciais'] == 'M. S. O.'

    # 2. Desbloqueio auditado com justificativa legal
    r_desbloqueio = cliente.post(
        f'{API}/observatorio/retornos/ret-01/desbloquear-sigilo',
        json={'justificativa': 'Solicitação formal de acolhimento protocolada no CAM.'},
        headers=headers
    )
    assert r_desbloqueio.status_code == 200
    caso_desbloqueado = r_desbloqueio.json()
    assert caso_desbloqueado['vitima_nome_completo'] == 'Mariana Souza Oliveira'
    assert caso_desbloqueado['vitima_telefone_protegido'] == '(19) 9987*-****'

    # Verifica registro na trilha de auditoria
    assert len(caso_desbloqueado['historico_acessos']) > 0
    ultimo_acesso = caso_desbloqueado['historico_acessos'][0]
    assert 'CAM' in ultimo_acesso['justificativa']


def test_registro_novo_despacho(admin):
    cliente = admin
    """Inserção de parecer técnico e atualização de status de caso."""
    headers = CAB
    novo_despacho = {
        'orgao': 'Secretaria Municipal da Mulher',
        'status_novo': 'acolhida_cam',
        'parecer_tecnico': 'Vítima acolhida com sucesso no Centro de Referência.',
        'encaminhamentos': ['Atendimento psicológico', 'Auxílio abrigo']
    }
    r = cliente.post(
        f'{API}/observatorio/retornos/ret-01/despachos',
        json=novo_despacho,
        headers=headers
    )
    assert r.status_code == 200
    caso_atualizado = r.json()
    assert caso_atualizado['status_retorno'] == 'acolhida_cam'
    assert caso_atualizado['despachos'][0]['parecer_tecnico'] == novo_despacho['parecer_tecnico']


def test_exportacao_csv_e_pdf(admin):
    cliente = admin
    """Exportação de relatórios em CSV e PDF por administrador."""
    headers = CAB

    # CSV
    r_csv = cliente.get(f'{API}/observatorio/exportar/csv', headers=headers)
    assert r_csv.status_code == 200
    assert 'text/csv' in r_csv.headers['content-type']
    assert r_csv.content.startswith(b'\xef\xbb\xbf')
    assert 'Protocolo;Data;Tipo de Ocorrencia' in r_csv.text

    # PDF
    r_pdf = cliente.get(f'{API}/observatorio/exportar/pdf', headers=headers)
    assert r_pdf.status_code == 200
    assert 'application/pdf' in r_pdf.headers['content-type']
    assert r_pdf.content.startswith(b'%PDF-')