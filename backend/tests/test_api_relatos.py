"""POST/GET/DELETE /relatos: validação como no cleanReport do legado, anonimização no servidor, janela,
classificação separada, chave de exclusão e precisão da hora de envio."""
from __future__ import annotations

import hashlib
import logging

import pytest

from backend.database.repositorios import DIA_MS, RepositorioClassificacoes, RepositorioRelatos, instante_atual_ms
from backend.services.anonimizacao import anonimizar_texto
from backend.services.ia import ProvedorHeuristico

API = '/api/v1'
CAMPOS_PUBLICOS = ['id', 'tipos', 'cell', 'quando', 'periodo', 'texto', 'criado', 'origem']
TEXTO_COM_DADOS = ('Ontem à noite um cara me seguiu, ele se chama Pedro Silva. Me liga no (19) 99876-5432 '
                   'ou manda para fulana.teste@exemplo.com, meu CPF é 123.456.789-09')


def _corpo(**campos):
    corpo = {'tipos': ['assedio'], 'cell': '0_0', 'quando': 'hoje', 'periodo': '20-22', 'texto': '', 'origem': 'chat'}
    corpo.update(campos)
    return corpo


def test_publicar_caminho_feliz(cliente):
    antes = instante_atual_ms()
    r = cliente.post(API + '/relatos', json=_corpo(tipos=['perseguicao', 'intimidacao'], cell='-3_12', quando='ontem',
                                                   periodo='madrugada', texto='Um carro ficou me seguindo devagar.', origem='chat-ia'))
    assert r.status_code == 201
    corpo = r.json()
    assert list(corpo) == ['relato', 'chave_exclusao', 'anonimizacao']
    rel = corpo['relato']
    assert list(rel) == CAMPOS_PUBLICOS
    assert len(rel['id']) == 32 and int(rel['id'], 16) >= 0
    assert rel['tipos'] == ['perseguicao', 'intimidacao']
    assert (rel['cell'], rel['quando'], rel['periodo'], rel['origem']) == ('-3_12', 'ontem', 'madrugada', 'chat-ia')
    assert rel['texto'] == 'Um carro ficou me seguindo devagar.'
    assert antes <= rel['criado'] <= instante_atual_ms()
    assert isinstance(corpo['chave_exclusao'], str) and len(corpo['chave_exclusao']) >= 32
    assert corpo['anonimizacao'] == {'removidos': []}
    lista = cliente.get(API + '/relatos').json()
    assert lista['tipo_evidencia'] == 'relato_comunidade'
    assert lista['janela_dias'] == 30
    assert lista['relatos'] == [rel]
    assert cliente.get(API + '/relatos/' + rel['id']).json() == {'relato': rel}


def test_anonimizacao_no_servidor(cliente, sessao):
    r = cliente.post(API + '/relatos', json=_corpo(texto=TEXTO_COM_DADOS))
    assert r.status_code == 201
    corpo = r.json()
    esperado = anonimizar_texto(TEXTO_COM_DADOS)
    assert corpo['relato']['texto'] == esperado.texto[:300]
    assert corpo['anonimizacao']['removidos'] == esperado.removidos
    assert set(esperado.removidos) >= {'telefone', 'e-mail', 'documento', 'nome'}
    for dado in ('99876-5432', 'fulana.teste@exemplo.com', '123.456.789-09', 'Pedro', 'Silva'):
        assert dado not in r.text
    # o banco só tem o texto limpo
    guardado = RepositorioRelatos(sessao).obter(corpo['relato']['id'])
    assert guardado.texto == esperado.texto
    assert 'Pedro' not in guardado.texto and '99876' not in guardado.texto


def test_numero_do_imovel_nao_fica_no_relato(cliente, sessao):
    r = cliente.post(API + '/relatos', json=_corpo(texto='homem armado roubando na rua 2 cj endereço 1532, perto da Rua das Flores 45'))
    assert r.status_code == 201
    corpo = r.json()
    assert '1532' not in r.text and '45' not in corpo['relato']['texto']
    assert 'rua 2 cj' in corpo['relato']['texto']  # o número da rua fica; só o do imóvel sai
    assert 'número de endereço' in corpo['anonimizacao']['removidos']
    assert '1532' not in RepositorioRelatos(sessao).obter(corpo['relato']['id']).texto


def test_tipos_sem_repetir_filtrados_e_no_maximo_4(cliente):
    r = cliente.post(API + '/relatos', json=_corpo(tipos=['assedio', 'assedio', 'xyz', 'roubo', 5, None, 'perseguicao', 'roubo',
                                                          'violencia', 'ambiente', 'veiculo']))
    assert r.status_code == 201
    assert r.json()['relato']['tipos'] == ['assedio', 'roubo', 'perseguicao', 'violencia']


def test_tipos_max_da_configuracao(criar_cliente):
    c = criar_cliente(relatos_tipos_max=2)
    r = c.post(API + '/relatos', json=_corpo(tipos=['assedio', 'roubo', 'perseguicao']))
    assert r.json()['relato']['tipos'] == ['assedio', 'roubo']


def test_celula_fina_de_200_m_e_aceita(cliente):
    assert cliente.post(API + '/relatos', json=_corpo(cell='f-123_1234')).status_code == 201


@pytest.mark.parametrize('cell', ['abc', '', '12345_1', '1_12345', 'ff1_1', 'f', '1f_1', '0-0', '0_0\n', '\n0_0', ' 0_0', '0_0 ', '١_٢', '0_0_0',
                                  5, None, ['0_0']])
def test_celula_invalida_422(cliente, cell):
    r = cliente.post(API + '/relatos', json=_corpo(cell=cell))
    assert r.status_code == 422
    corpo = r.json()
    assert corpo['detail'] == 'Dados do relato inválidos.'
    assert [e['campo'] for e in corpo['erros']] == ['cell']
    assert all(set(e) == {'campo', 'mensagem', 'tipo'} for e in corpo['erros'])


def test_celula_ausente_422(cliente):
    corpo = _corpo()
    del corpo['cell']
    r = cliente.post(API + '/relatos', json=corpo)
    assert r.status_code == 422
    assert r.json()['erros'] == [{'campo': 'cell', 'mensagem': 'Campo obrigatório.', 'tipo': 'missing'}]


@pytest.mark.parametrize('cell', ['0_0', '-10_19', '999_-999', '-1_-1'])
def test_celula_valida(cliente, cell):
    assert cliente.post(API + '/relatos', json=_corpo(cell=cell)).status_code == 201


@pytest.mark.parametrize('tipos', [[], ['xyz'], [1, 2], [None], ['Assedio'], 'assedio', None, {'assedio': True}])
def test_sem_tipo_valido_422(cliente, tipos):
    r = cliente.post(API + '/relatos', json=_corpo(tipos=tipos))
    assert r.status_code == 422
    corpo = r.json()
    assert corpo['detail'] == 'Dados do relato inválidos.'
    assert [e['campo'] for e in corpo['erros']] == ['tipos']


def test_corpo_invalido_422(cliente):
    r = cliente.post(API + '/relatos', content=b'{"tipos": [', headers={'Content-Type': 'application/json'})
    assert r.status_code == 422
    assert r.json()['detail'] == 'Dados do relato inválidos.'
    r = cliente.post(API + '/relatos', json=['assedio'])
    assert r.status_code == 422


def test_erro_de_validacao_nao_ecoa_o_texto(cliente):
    texto = 'segredo-' + 'x' * 2000
    r = cliente.post(API + '/relatos', json=_corpo(texto=texto))
    assert r.status_code == 422
    assert r.json()['erros'][0]['campo'] == 'texto'
    assert 'segredo' not in r.text


@pytest.mark.parametrize('quando,periodo', [('amanha', '25-26'), (123, 7), ('HOJE', 'Manha'), (['hoje'], ['manha']),
                                            ('toString', 'constructor'), (None, None)])
def test_quando_e_periodo_desconhecidos_viram_null(cliente, quando, periodo):
    r = cliente.post(API + '/relatos', json=_corpo(quando=quando, periodo=periodo))
    assert r.status_code == 201
    assert (r.json()['relato']['quando'], r.json()['relato']['periodo']) == (None, None)


def test_quando_e_periodo_ausentes(cliente):
    r = cliente.post(API + '/relatos', json={'tipos': ['assedio'], 'cell': '0_0'})
    assert r.status_code == 201
    rel = r.json()['relato']
    assert (rel['quando'], rel['periodo'], rel['texto'], rel['origem']) == (None, None, '', 'chat')


@pytest.mark.parametrize('origem,esperada', [('chat-ia', 'chat-ia'), ('chat', 'chat'), ('xyz', 'chat'), ('CHAT-IA', 'chat'),
                                             (123, 'chat'), (None, 'chat')])
def test_origem_normalizada(cliente, origem, esperada):
    r = cliente.post(API + '/relatos', json=_corpo(origem=origem))
    assert r.json()['relato']['origem'] == esperada


def test_criado_id_e_v_do_cliente_ignorados(cliente):
    antes = instante_atual_ms()
    r = cliente.post(API + '/relatos', json=_corpo(criado=0, v=99, id='meu-id', chave_hash='x', removidos=['nome']))
    assert r.status_code == 201
    rel = r.json()['relato']
    assert rel['id'] != 'meu-id'
    assert antes <= rel['criado'] <= instante_atual_ms()
    assert list(rel) == CAMPOS_PUBLICOS


@pytest.mark.parametrize('texto,esperado', [
    ('a' * 1000, 'a' * 300),
    ('😀' * 200, '😀' * 150),  # o corte conta unidades UTF-16, como o slice do JS
    ('x' * 299 + '😀', 'x' * 299 + '�'),  # meio emoji: o navegador mostraria U+FFFD
    ('x' * 298 + '😀', 'x' * 298 + '😀'),
])
def test_texto_cortado_em_300(cliente, texto, esperado):
    r = cliente.post(API + '/relatos', json=_corpo(texto=texto))
    assert r.status_code == 201
    assert r.json()['relato']['texto'] == esperado
    assert cliente.get(API + '/relatos/' + r.json()['relato']['id']).json()['relato']['texto'] == esperado


def test_texto_que_chega_com_substituto_solto(cliente):
    # o frontend manda o texto já cortado pelo slice do JS, que pode terminar em meio emoji
    corpo = b'{"tipos":["assedio"],"cell":"0_0","texto":"oi \\ud83d"}'
    r = cliente.post(API + '/relatos', content=corpo, headers={'Content-Type': 'application/json'})
    assert r.status_code == 201
    assert r.json()['relato']['texto'] == 'oi �'


@pytest.mark.parametrize('texto', [123, None, ['texto'], {'a': 1}, True])
def test_texto_que_nao_e_string_fica_vazio(cliente, texto):
    r = cliente.post(API + '/relatos', json=_corpo(texto=texto))
    assert r.status_code == 201
    assert r.json()['relato']['texto'] == ''


def test_texto_max_da_configuracao(criar_cliente):
    c = criar_cliente(relatos_texto_max=10)
    r = c.post(API + '/relatos', json=_corpo(texto='0123456789abcdef'))
    assert r.json()['relato']['texto'] == '0123456789'


def test_resposta_nunca_expoe_chave_nem_classificacoes(cliente):
    r = cliente.post(API + '/relatos', json=_corpo(texto='um cara me seguiu e ficou me encarando'))
    corpo = r.json()
    chave = corpo['chave_exclusao']
    hash_chave = hashlib.sha256(chave.encode()).hexdigest()
    id_ = corpo['relato']['id']
    for resp in (r, cliente.get(API + '/relatos'), cliente.get(API + '/relatos/' + id_)):
        assert hash_chave not in resp.text
        assert 'chave_hash' not in resp.text
        assert 'classifica' not in resp.text
        assert 'provedor' not in resp.text
    assert chave not in cliente.get(API + '/relatos').text
    assert chave not in cliente.get(API + '/relatos/' + id_).text
    assert list(cliente.get(API + '/relatos/' + id_).json()['relato']) == CAMPOS_PUBLICOS
    assert all(list(x) == CAMPOS_PUBLICOS for x in cliente.get(API + '/relatos').json()['relatos'])


def test_banco_guarda_so_o_hash_da_chave(cliente, sessao):
    corpo = cliente.post(API + '/relatos', json=_corpo()).json()
    guardado = RepositorioRelatos(sessao).obter(corpo['relato']['id'])
    assert guardado.chave_hash == hashlib.sha256(corpo['chave_exclusao'].encode()).hexdigest()
    assert corpo['chave_exclusao'] not in {str(v) for v in vars(guardado).values()}


def test_classificacao_gravada_separada(cliente, sessao):
    r = cliente.post(API + '/relatos', json=_corpo(tipos=['outra'], texto='Ontem, umas 22h, um cara me seguiu e ficou me encarando'))
    rel = r.json()['relato']
    assert rel['tipos'] == ['outra']  # os tipos do relato continuam os da usuária
    classificacoes = RepositorioClassificacoes(sessao).do_relato(rel['id'])
    assert len(classificacoes) == 1
    c = classificacoes[0]
    assert c.provedor == 'heuristica' and c.modelo is None
    assert c.tipos == ['perseguicao', 'intimidacao']
    assert (c.quando, c.periodo, c.urgente, c.confianca) == ('ontem', '22-00', False, None)
    assert c.criado == rel['criado']


def test_sem_texto_sem_classificacao(cliente, sessao):
    for texto in ('', '   '):
        rel = cliente.post(API + '/relatos', json=_corpo(texto=texto)).json()['relato']
        assert RepositorioClassificacoes(sessao).do_relato(rel['id']) == []
    assert RepositorioClassificacoes(sessao).contar() == 0


def test_classificacao_desligada(criar_cliente, sessao):
    c = criar_cliente(ia_classificar_ao_criar=False)
    c.post(API + '/relatos', json=_corpo(texto='um cara me seguiu'))
    assert RepositorioClassificacoes(sessao).contar() == 0


def test_relato_salvo_mesmo_se_o_classificador_falhar(cliente, sessao, monkeypatch, caplog):
    def falha(self, texto, contexto):
        raise RuntimeError('falha de propósito: ' + texto)
    monkeypatch.setattr(ProvedorHeuristico, 'classificar', falha)
    caplog.set_level(logging.DEBUG, logger='aurora')
    texto = 'um cara me seguiu na rua 7'
    r = cliente.post(API + '/relatos', json=_corpo(texto=texto))
    assert r.status_code == 201
    id_ = r.json()['relato']['id']
    assert cliente.get(API + '/relatos/' + id_).status_code == 200
    assert RepositorioClassificacoes(sessao).contar() == 0
    assert 'classificação automática falhou (RuntimeError)' in caplog.text
    assert texto not in caplog.text


def test_janela_de_relatos(cliente, inserir_relato):
    agora = instante_atual_ms()
    antigo = inserir_relato(agora - 40 * DIA_MS)
    limite = inserir_relato(agora - 29 * DIA_MS)
    novo = cliente.post(API + '/relatos', json=_corpo()).json()['relato']
    ids = [r['id'] for r in cliente.get(API + '/relatos').json()['relatos']]
    assert ids == [novo['id'], limite.id]  # do mais novo para o mais antigo
    assert antigo.id not in ids
    # fora da janela, continua acessível pelo id ("Meus relatos" antigos)
    r = cliente.get(API + '/relatos/' + antigo.id)
    assert r.status_code == 200
    assert r.json()['relato']['criado'] == agora - 40 * DIA_MS
    lista = cliente.get(API + '/relatos', params={'janela_dias': 60}).json()
    assert lista['janela_dias'] == 60
    assert [r['id'] for r in lista['relatos']] == [novo['id'], limite.id, antigo.id]
    assert [r['id'] for r in cliente.get(API + '/relatos', params={'janela_dias': 1}).json()['relatos']] == [novo['id']]


def test_janela_da_configuracao(criar_cliente, inserir_relato):
    c = criar_cliente(relatos_janela_dias=7)
    inserir_relato(instante_atual_ms() - 10 * DIA_MS)
    lista = c.get(API + '/relatos').json()
    assert lista['janela_dias'] == 7
    assert lista['relatos'] == []


@pytest.mark.parametrize('janela', ['0', '3651', '-1', 'abc', '1.5'])
def test_janela_invalida_422(cliente, janela):
    r = cliente.get(API + '/relatos', params={'janela_dias': janela})
    assert r.status_code == 422
    assert isinstance(r.json()['detail'], str)
    assert r.json()['erros'][0]['campo'] == 'janela_dias'


def test_relato_inexistente_404(cliente):
    r = cliente.get(API + '/relatos/naoexiste')
    assert r.status_code == 404
    assert r.json() == {'detail': 'Relato não encontrado.'}


def test_apagar_com_a_chave_certa(cliente, sessao):
    corpo = cliente.post(API + '/relatos', json=_corpo(texto='um cara me seguiu')).json()
    id_ = corpo['relato']['id']
    assert RepositorioClassificacoes(sessao).contar() == 1
    r = cliente.delete(API + '/relatos/' + id_, headers={'X-Chave-Exclusao': corpo['chave_exclusao']})
    assert r.status_code == 204
    assert r.content == b''
    assert cliente.get(API + '/relatos/' + id_).status_code == 404
    assert cliente.get(API + '/relatos').json()['relatos'] == []
    assert RepositorioClassificacoes(sessao).contar() == 0
    # de novo: já não existe
    assert cliente.delete(API + '/relatos/' + id_, headers={'X-Chave-Exclusao': corpo['chave_exclusao']}).status_code == 404


@pytest.mark.parametrize('cabecalhos', [{}, {'X-Chave-Exclusao': ''}, {'X-Chave-Exclusao': 'errada'}, {'X-Outra-Coisa': 'x'}])
def test_apagar_com_chave_errada_ou_ausente_403(cliente, cabecalhos):
    corpo = cliente.post(API + '/relatos', json=_corpo()).json()
    id_ = corpo['relato']['id']
    r = cliente.delete(API + '/relatos/' + id_, headers=cabecalhos)
    assert r.status_code == 403
    assert isinstance(r.json()['detail'], str)
    assert cliente.get(API + '/relatos/' + id_).status_code == 200


def test_apagar_com_a_chave_de_outro_relato_403(cliente):
    a = cliente.post(API + '/relatos', json=_corpo()).json()
    b = cliente.post(API + '/relatos', json=_corpo()).json()
    r = cliente.delete(API + '/relatos/' + a['relato']['id'], headers={'X-Chave-Exclusao': b['chave_exclusao']})
    assert r.status_code == 403


def test_apagar_inexistente_404(cliente):
    r = cliente.delete(API + '/relatos/naoexiste', headers={'X-Chave-Exclusao': 'qualquer'})
    assert r.status_code == 404
    assert r.json() == {'detail': 'Relato não encontrado.'}


@pytest.mark.parametrize('precisao,passo', [('exata', 1), ('hora', 3_600_000), ('dia', DIA_MS)])
def test_precisao_do_criado(criar_cliente, sessao, precisao, passo):
    c = criar_cliente(relatos_precisao_criado=precisao)
    antes = instante_atual_ms()
    corpo = c.post(API + '/relatos', json=_corpo(texto='um cara me seguiu')).json()
    depois = instante_atual_ms()
    criado = corpo['relato']['criado']
    assert criado % passo == 0
    assert antes - antes % passo <= criado <= depois
    # a classificação guarda a mesma hora arredondada
    assert RepositorioClassificacoes(sessao).do_relato(corpo['relato']['id'])[0].criado == criado
