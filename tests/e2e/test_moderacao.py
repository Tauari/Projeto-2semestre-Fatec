"""Fluxo real do painel. Rodar com pytest + playwright e Chromium instalados.

    .venv/bin/python -m pytest tests/e2e/test_moderacao.py

Usa servidor e SQLite temporários, sem alterar os relatos do ambiente de desenvolvimento.
"""
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

import httpx
import pytest
from playwright.sync_api import expect, sync_playwright

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture
def servidor(tmp_path):
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        porta = s.getsockname()[1]
    chave = secrets.token_urlsafe(32)
    env = {k: v for k, v in os.environ.items() if not k.startswith('AURORA_')}
    env.update(AURORA_BANCO_URL='sqlite:///' + str(tmp_path / 'e2e.db'))
    from sqlalchemy.orm import Session
    from backend.database.sessao import criar_motor, criar_tabelas
    from backend.services.equipe import criar_primeiro_admin
    motor = criar_motor(env['AURORA_BANCO_URL'])
    criar_tabelas(motor)
    with Session(motor) as sessao:
        criar_primeiro_admin(sessao, 'responsavel', chave)
    motor.dispose()
    log = (tmp_path / 'server.log').open('w+')
    proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1',
                             '--port', str(porta), '--no-access-log'], cwd=RAIZ, env=env, stdout=log, stderr=log)
    url = f'http://127.0.0.1:{porta}'
    try:
        with httpx.Client(base_url=url, trust_env=False) as api:
            for _ in range(100):
                if proc.poll() is not None:
                    log.seek(0)
                    pytest.fail(log.read())
                try:
                    if api.get('/api/v1/saude').status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(.1)
            else:
                pytest.fail('Servidor não iniciou')
            yield url, chave, api
    finally:
        proc.terminate()
        proc.wait(timeout=10)
        log.close()


@pytest.mark.parametrize('viewport', [{'width': 1280, 'height': 900}, {'width': 390, 'height': 844}])
def test_painel_completo(servidor, viewport):
    url, chave, api = servidor
    relato = api.post('/api/v1/relatos', json={'tipos': ['assedio'], 'cell': '0_0', 'texto': 'Texto para revisão.'}).json()
    id = relato['relato']['id']
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        erros = []
        page.on('pageerror', lambda e: erros.append(str(e)))
        page.goto(url + '/moderacao')
        expect(page.get_by_role('heading', name='Revisar relatos')).to_be_visible()
        expect(page.get_by_label('Senha', exact=True)).to_be_visible()
        page.get_by_label('Usuário', exact=True).fill('responsavel')
        page.get_by_label('Senha', exact=True).fill('errada')
        page.get_by_role('button', name='Entrar', exact=True).click()
        expect(page.get_by_role('alert')).to_contain_text('inválidos')
        page.get_by_label('Usuário', exact=True).fill('responsavel')
        page.get_by_label('Senha', exact=True).fill(chave)
        page.get_by_role('button', name='Entrar', exact=True).click()
        page.get_by_role('button', name='Relatos', exact=True).click()
        expect(page.get_by_role('button', name='Ocultar', exact=True)).to_be_visible()
        # Erro de rede não deve salvar estado local nem anunciar sucesso.
        page.route('**/api/v1/moderacao/' + id, lambda route: route.abort())
        page.get_by_role('button', name='Ocultar', exact=True).click()
        expect(page.locator('#toast')).to_contain_text('Sem conexão')
        assert api.get('/api/v1/relatos').json()['relatos'][0]['id'] == id
        page.unroute('**/api/v1/moderacao/' + id)
        # Simula a autoria no aparelho para cobrir a volta de um relato ocultado.
        page.evaluate('''async ({id, chave}) => {
            const {Store} = await import('/shared/store.js');
            Store.perfil.meus = [id]; Store.savePerfil();
            localStorage.setItem('aurora.v1.chaves', JSON.stringify({[id]: chave}));
        }''', {'id': id, 'chave': relato['chave_exclusao']})
        page.get_by_role('button', name='Verificar', exact=True).click()
        expect(page.get_by_role('button', name='Tirar verificação')).to_be_visible()
        assert api.get('/api/v1/moderacao/estado').json()['verificado'] == {id: True}
        page.get_by_role('button', name='Ocultar', exact=True).click()
        expect(page.get_by_role('button', name='Mostrar', exact=True)).to_be_visible()
        assert api.get('/api/v1/relatos').json()['relatos'] == []
        assert api.get('/api/v1/relatos/' + id).status_code == 404
        # Aguarda a atualização da lista pública, separada dos dados privados do painel.
        page.wait_for_function('''async id => !(await import('/shared/store.js')).Store.reports.has(id)''', arg=id)
        page.get_by_role('button', name='Mostrar', exact=True).click()
        expect(page.get_by_role('button', name='Ocultar', exact=True)).to_be_visible()
        page.wait_for_function('''async id => (await import('/shared/store.js')).Store.reports.has(id)''', arg=id)
        assert api.get('/api/v1/relatos').json()['relatos'][0]['id'] == id
        page.get_by_role('button', name='Tirar verificação').click()
        expect(page.get_by_role('button', name='Verificar', exact=True)).to_be_visible()
        assert api.get('/api/v1/moderacao/estado').json()['verificado'] == {}
        assert chave not in page.evaluate('JSON.stringify({...localStorage, ...sessionStorage})')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.get_by_role('button', name='Sair da moderação').click()
        expect(page.get_by_label('Senha', exact=True)).to_be_visible()
        expect(page.get_by_text('Texto para revisão.', exact=True)).not_to_be_visible()
        # A página pública abre no mapa. A equipe entra pelo endereço direto.
        page.goto(url)
        expect(page.locator('#view-mapa')).to_be_visible()
        expect(page.locator('[data-view="moderacao"]')).to_have_count(0)
        expect(page.locator('#view-moderacao')).to_be_hidden()
        page.goto(url + '/moderacao')
        expect(page).to_have_url(url + '/#moderacao')
        page.get_by_label('Usuário', exact=True).fill('responsavel')
        page.get_by_label('Senha', exact=True).fill(chave)
        page.get_by_role('button', name='Entrar', exact=True).click()
        page.get_by_role('button', name='Relatos', exact=True).click()
        expect(page.get_by_role('button', name='Ocultar', exact=True)).to_be_visible()
        page.reload()
        page.get_by_role('button', name='Relatos', exact=True).click()
        expect(page.get_by_role('button', name='Ocultar', exact=True)).to_be_visible()
        assert not erros, erros
        context.close()
        browser.close()


@pytest.mark.parametrize('viewport', [{'width': 1440, 'height': 1000}, {'width': 390, 'height': 844}])
def test_admin_cadastra_e_revoga_moderadora(servidor, viewport):
    url, senha, api = servidor
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport=viewport)
        page = context.new_page()
        erros = []
        page.on('pageerror', lambda e: erros.append(str(e)))
        page.goto(url + '/moderacao')
        page.get_by_label('Usuário', exact=True).fill('responsavel')
        page.get_by_label('Senha', exact=True).fill(senha)
        page.get_by_role('button', name='Entrar', exact=True).click()
        page.get_by_role('button', name='Equipe', exact=True).click()
        page.get_by_label('Usuário da nova pessoa').fill('ana.silva')
        page.get_by_label('Senha da nova pessoa').fill('Senha-ficticia-da-Ana')
        page.get_by_role('button', name='Cadastrar pessoa').click()
        expect(page.locator('.equipe-pessoa').filter(has_text='ana.silva')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.get_by_role('button', name='Sair da moderação').click()
        expect(page.locator('.equipe-layout')).to_have_count(0)
        page.get_by_label('Usuário', exact=True).fill('ana.silva')
        page.get_by_label('Senha', exact=True).fill('Senha-ficticia-da-Ana')
        page.get_by_role('button', name='Entrar', exact=True).click()
        page.get_by_role('button', name='Relatos', exact=True).click()
        expect(page.get_by_text('Nenhum relato ainda', exact=True)).to_be_visible()
        expect(page.get_by_role('button', name='Equipe', exact=True)).to_have_count(0)
        assert context.request.get(url + '/api/v1/usuarios/equipe').status == 403
        api.post('/api/v1/usuarios/entrar', headers={'X-Aurora-Equipe': '1'}, json={'login': 'responsavel', 'senha': senha})
        pessoa = next(u for u in api.get('/api/v1/usuarios/equipe').json() if u['login'] == 'ana.silva')
        assert api.post('/api/v1/usuarios/equipe/' + pessoa['id'] + '/ativo', headers={'X-Aurora-Equipe': '1'}, json={'ativo': False}).status_code == 200
        page.get_by_role('button', name='Atualizar relatos').click()
        expect(page.get_by_label('Usuário', exact=True)).to_be_visible()
        assert not erros, erros
        context.close()
        browser.close()


@pytest.mark.parametrize('viewport', [{'width': 1440, 'height': 1000}, {'width': 390, 'height': 844}])
def test_visao_geral_sem_chat_e_exportacao(servidor, viewport):
    url, senha, api = servidor
    api.post('/api/v1/relatos', json={'tipos':['assedio'], 'cell':'0_0', 'texto':'Relato fictício do painel.'})
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
        ctx=browser.new_context(viewport=viewport)
        page=ctx.new_page();page.goto(url+'/moderacao')
        expect(page.locator('#chat')).not_to_be_visible()
        page.get_by_label('Usuário',exact=True).fill('responsavel')
        page.get_by_label('Senha',exact=True).fill(senha)
        page.get_by_role('button',name='Entrar',exact=True).click()
        page.get_by_role('button',name='Visão geral',exact=True).click()
        expect(page.locator('[data-metrica="total"]')).to_contain_text('1')
        expect(page.get_by_role('heading',name='Tipos de situação')).to_be_visible()
        page.get_by_label('Período do painel').select_option('7')
        expect(page.locator('[data-metrica="total"]')).to_contain_text('1')
        with page.expect_download() as evento:
            page.get_by_role('button',name='Baixar relatório PDF',exact=True).click()
        assert Path(evento.value.path()).read_bytes().startswith(b'%PDF-')
        page.get_by_role('button',name='Preparar encaminhamento',exact=True).click()
        expect(page.get_by_text('Nenhum documento é enviado automaticamente.',exact=True)).to_be_visible()
        with page.expect_download() as evento:
            page.get_by_role('button',name='Baixar minuta para revisão',exact=True).click()
        assert Path(evento.value.path()).read_bytes().startswith(b'%PDF-')
        page.get_by_role('button',name='Relatos',exact=True).click()
        page.get_by_role('button',name='Ocultar',exact=True).click()
        expect(page.get_by_role('button',name='Mostrar',exact=True)).to_be_visible()
        page.get_by_role('button',name='Visão geral',exact=True).click()
        expect(page.locator('[data-metrica="ocultos"]')).to_contain_text('1')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.goto(url)
        if viewport['width'] > 999: expect(page.locator('#chat')).to_be_visible()
        else:
            page.locator('.tabbar [data-act="relatar"]').click()
            expect(page.locator('#chat')).to_be_visible()
        ctx.close();browser.close()
