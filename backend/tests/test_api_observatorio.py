from __future__ import annotations

import pytest

API = '/api/v1'


def test_rotas_bloqueadas_para_nao_admins(cliente):
    """Garante bloqueio por rota: anônimos e usuários sem privilégios recebem HTTP 403."""
    # Relatórios do Observatório
    r_rel = cliente.get(f'{API}/observatorio/relatorios')
    assert r_rel.status_code == 403
    assert 'Acesso restrito' in r_rel.json()['detail']

    # Retornos da Secretaria
    r_ret = cliente.get(f'{API}/observatorio/retornos')
    assert r_ret.status_code == 403
    assert 'Acesso restrito' in r_ret.json()['detail']

    # Registros de Despacho
    r_dsp = cliente.post(
        f'{API}/observatorio/retornos/ret-01/despachos',
        json={
            'orgao': 'Secretaria da Mulher',
            'status_novo': 'em_acompanhamento',
            'parecer_tecnico': 'Atendimento presencial realizado.',
            'encaminhamentos': ['CAM']
        }
    )
    assert r_dsp.status_code == 403

    # Desbloqueio LGPD
    r_sig = cliente.post(
        f'{API}/observatorio/retornos/ret-01/desbloquear-sigilo',
        json={'justificativa': 'Necessidade de intimação urgente.'}
    )
    assert r_sig.status_code == 403

    # Exportação de Dados
    r_csv = cliente.get(f'{API}/observatorio/exportar/csv')
    assert r_csv.status_code == 403

    r_pdf = cliente.get(f'{API}/observatorio/exportar/pdf')
    assert r_pdf.status_code == 403


def test_login_admin_concede_acesso(cliente):
    """Testa autenticação de credenciais administrativas."""
    # Falha com senha errada
    r_erro = cliente.post(
        f'{API}/usuarios/login',
        json={'login': 'admin_observatorio', 'senha': 'senha_errada'}
    )
    assert r_erro.status_code == 401

    # Sucesso com credencial institucional
    r_ok = cliente.post(
        f'{API}/usuarios/login',
        json={'login': 'admin_observatorio', 'senha': 'aurora2026'}
    )
    assert r_ok.status_code == 200
    dados = r_ok.json()
    assert dados['autenticado'] is True
    assert 'admin' in dados['papeis']
    assert 'token' in dados
    token = dados['token']

    # Validação do perfil autenticado
    r_eu = cliente.get(f'{API}/usuarios/eu', headers={'Authorization': f'Bearer {token}'})
    assert r_eu.status_code == 200
    assert r_eu.json()['autenticado'] is True
    assert 'admin' in r_eu.json()['papeis']


def test_relatorio_observatorio_com_admin(cliente):
    """Acesso aos relatórios estruturados pelo Observatório com token de admin."""
    headers = {'X-Admin-Token': 'aurora_admin_token_master_2026'}
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


def test_retornos_secretaria_lgpd_e_desbloqueio(cliente):
    """Acesso restrito a retornos com mascaramento de dados sensíveis e auditoria LGPD."""
    headers = {'Authorization': 'Bearer aurora_admin_token_master_2026'}

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


def test_registro_novo_despacho(cliente):
    """Inserção de parecer técnico e atualização de status de caso."""
    headers = {'Authorization': 'Bearer aurora_admin_token_master_2026'}
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


def test_exportacao_csv_e_pdf(cliente):
    """Exportação de relatórios em CSV e PDF por administrador."""
    headers = {'Authorization': 'Bearer aurora_admin_token_master_2026'}

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