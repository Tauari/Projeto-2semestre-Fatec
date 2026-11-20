"""Resumo administrativo e PDF respeitam sessão, período e retenção."""
from backend.tests.test_api_equipe import admin, criar, CAB, SENHA
from backend.database.repositorios import DIA_MS, instante_atual_ms

BASE = '/api/v1/moderacao'

def relato(c, tipos=None):
    return c.post('/api/v1/relatos', json={'tipos': tipos or ['assedio'], 'cell':'0_0', 'texto':'Texto privado do teste.'}).json()['relato']['id']

def test_resumo_e_pdf_exigem_sessao(cliente):
    assert cliente.get(BASE+'/resumo').status_code == 401
    assert cliente.get(BASE+'/relatorio.pdf').status_code == 401

def test_contagens_exclusivas_e_multiplos_tipos(admin):
    a,b,c = relato(admin),relato(admin,['assedio','perseguicao']),relato(admin)
    admin.post(BASE+'/'+b, headers=CAB,json={'campo':'verificado','valor':True})
    admin.post(BASE+'/'+c, headers=CAB,json={'campo':'verificado','valor':True})
    admin.post(BASE+'/'+c, headers=CAB,json={'campo':'oculto','valor':True})
    r=admin.get(BASE+'/resumo').json()
    assert r['indicadores']=={'total':3,'pendentes':1,'verificados':1,'ocultos':1}
    assert r['por_tipo']=={'assedio':3,'perseguicao':1}
    assert sum(r['por_dia'].values())==3
    assert 'Texto privado' not in str(r)

def test_periodo_e_retencao(admin, configurar):
    from backend.database import sessao as banco
    from backend.database.tabelas import Relato
    id=relato(admin)
    with banco.SessionLocal() as s:
        s.get(Relato,id).criado=instante_atual_ms()-40*DIA_MS;s.commit()
    assert admin.get(BASE+'/resumo?dias=30').json()['indicadores']['total']==0
    assert admin.get(BASE+'/resumo?dias=90').json()['indicadores']['total']==1
    configurar(relatos_retencao_dias=20)
    assert admin.get(BASE+'/resumo?dias=90').json()['indicadores']['total']==0
    assert admin.get(BASE+'/resumo?dias=0').status_code==422

def test_pdf_e_permissoes(admin):
    relato(admin)
    r=admin.get(BASE+'/relatorio.pdf?dias=30')
    assert r.status_code==200
    assert r.content.startswith(b'%PDF-') and b'%%EOF' in r.content
    assert r.headers['content-type']=='application/pdf'
    assert r.headers['cache-control']=='no-store'
    minuta=admin.get(BASE+'/relatorio.pdf?encaminhamento=true')
    assert minuta.status_code==200 and minuta.content.startswith(b'%PDF-')
    assert 'minuta-encaminhamento' in minuta.headers['content-disposition']
    criar(admin)
    admin.post('/api/v1/usuarios/sair',headers=CAB)
    admin.post('/api/v1/usuarios/entrar',headers=CAB,json={'login':'revisora','senha':SENHA})
    assert admin.get(BASE+'/resumo').status_code==200
    assert admin.get(BASE+'/relatorio.pdf').status_code==403
