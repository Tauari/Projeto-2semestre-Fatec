"""Envio de relatos sem cadastro: permite envio anônimo, valida campos e protege dados sensíveis."""
from __future__ import annotations

import pytest
from backend.database.repositorios import RepositorioRelatos
from backend.models.vocabulario import TIPOS_POR_ID, QUANDO, PERIODOS_POR_ID

API = '/api/v1'


class relatosSemCadastros:
    __test__ = True

    def test_envio_sem_autenticacao_ou_token(self, cliente):
        # usuário anônimo sem login consegue enviar relato
        eu = cliente.get(f'{API}/usuarios/eu')
        assert eu.status_code == 200
        assert eu.json() == {'autenticado': False, 'papeis': []}

        payload = {
            'tipos': ['assedio'],
            'cell': '10_20',
            'quando': 'hoje',
            'periodo': 'noite',
            'texto': 'Relato enviado sem login.',
            'origem': 'chat'
        }
        res = cliente.post(f'{API}/relatos', json=payload)
        assert res.status_code == 201
        dados = res.json()
        assert 'relato' in dados
        assert dados['relato']['cell'] == '10_20'
        # devolve chave para a pessoa poder apagar o próprio relato
        assert 'chave_exclusao' in dados
        assert len(dados['chave_exclusao']) >= 24

    def test_campos_do_relato(self, cliente):
        # confere se todos os campos necessários são retornados no relato
        payload = {
            'tipos': ['ambiente', 'assedio'],
            'cell': '-5_12',
            'quando': 'semana',
            'periodo': 'madrugada',
            'texto': 'Rua escura perto da praça.',
            'origem': 'chat'
        }
        res = cliente.post(f'{API}/relatos', json=payload)
        assert res.status_code == 201
        relato = res.json()['relato']

        campos = {'id', 'tipos', 'cell', 'quando', 'periodo', 'texto', 'criado', 'origem'}
        assert set(relato.keys()) == campos
        assert relato['tipos'] == ['ambiente', 'assedio']
        assert relato['cell'] == '-5_12'
        assert relato['quando'] == 'semana'
        assert relato['periodo'] == 'madrugada'
        assert relato['texto'] == 'Rua escura perto da praça.'
        assert isinstance(relato['criado'], int)

    def test_validacao_tipos_obrigatorio(self, cliente):
        # não deixa criar sem pelo menos um tipo válido
        res1 = cliente.post(f'{API}/relatos', json={'cell': '0_0'})
        assert res1.status_code == 422
        assert any(e['campo'] == 'tipos' for e in res1.json()['erros'])

        res2 = cliente.post(f'{API}/relatos', json={'tipos': [], 'cell': '0_0'})
        assert res2.status_code == 422
        assert any(e['campo'] == 'tipos' for e in res2.json()['erros'])

        res3 = cliente.post(f'{API}/relatos', json={'tipos': ['tipo_invalido'], 'cell': '0_0'})
        assert res3.status_code == 422
        assert any(e['campo'] == 'tipos' for e in res3.json()['erros'])

    def test_validacao_cell_obrigatorio_e_formato(self, cliente):
        # cell é obrigatória e precisa seguir o formato da grade
        res1 = cliente.post(f'{API}/relatos', json={'tipos': ['assedio']})
        assert res1.status_code == 422
        assert any(e['campo'] == 'cell' for e in res1.json()['erros'])

        for cell in ['invalido', '10', '10.5_20', '', None, 123]:
            res = cliente.post(f'{API}/relatos', json={'tipos': ['assedio'], 'cell': cell})
            assert res.status_code == 422
            assert any(e['campo'] == 'cell' for e in res.json()['erros'])

    def test_validacao_limite_tamanho_texto(self, cliente):
        # texto longo demais é recusado
        res = cliente.post(f'{API}/relatos', json={'tipos': ['assedio'], 'cell': '1_1', 'texto': 'A' * 2001})
        assert res.status_code == 422
        assert any(e['campo'] == 'texto' for e in res.json()['erros'])

    def test_confirmacao_de_envio(self, cliente):
        # sucesso devolve 201 com o relato e a chave de exclusão
        res = cliente.post(f'{API}/relatos', json={'tipos': ['perseguicao'], 'cell': '2_3'})
        assert res.status_code == 201
        corpo = res.json()
        assert 'relato' in corpo
        assert 'chave_exclusao' in corpo
        assert corpo['relato']['id'] is not None

    def test_mensagem_de_erro_estruturada(self, cliente):
        # erro 422 retorna lista detalhada com os campos que falharam
        res = cliente.post(f'{API}/relatos', json={'tipos': [], 'cell': 'invalida'})
        assert res.status_code == 422
        corpo = res.json()
        assert corpo['detail'] == 'Dados do relato inválidos.'
        campos = {e['campo'] for e in corpo['erros']}
        assert 'tipos' in campos
        assert 'cell' in campos

    def test_nao_solicita_nem_persiste_dados_pessoais(self, cliente, sessao):
        # campos extras com dados pessoais são ignorados e não vão pro banco
        payload = {
            'tipos': ['assedio'],
            'cell': '5_5',
            'nome_usuaria': 'Maria dos Santos',
            'email': 'maria@exemplo.com',
            'telefone': '(19) 99999-8888',
            'cpf': '111.222.333-44',
            'texto': 'Situação ocorrida sem identificação.'
        }
        res = cliente.post(f'{API}/relatos', json=payload)
        assert res.status_code == 201
        relato = res.json()['relato']

        assert 'nome_usuaria' not in relato
        assert 'email' not in relato
        assert 'telefone' not in relato
        assert 'cpf' not in relato

        guardado = RepositorioRelatos(sessao).obter(relato['id'])
        assert not hasattr(guardado, 'nome_usuaria')
        assert not hasattr(guardado, 'email')
        assert not hasattr(guardado, 'telefone')
        assert not hasattr(guardado, 'cpf')

    def test_sanitizacao_e_anonimizacao_de_dados_sensiveis(self, cliente, sessao):
        # se escapar dados pessoais no texto, o servidor limpa antes de salvar
        texto = (
            'O agressor se chama José Pereira e estava perto da Rua 3 número 456. '
            'Ele me ligou do número (19) 98765-4321 e mandou email para contato@teste.org. '
            'Meu documento informado foi 123.456.789-10.'
        )
        res = cliente.post(f'{API}/relatos', json={'tipos': ['assedio'], 'cell': '4_4', 'texto': texto})
        assert res.status_code == 201
        dados = res.json()
        texto_limpo = dados['relato']['texto']
        removidos = dados['anonimizacao']['removidos']

        assert 'José Pereira' not in texto_limpo
        assert '98765-4321' not in texto_limpo
        assert 'contato@teste.org' not in texto_limpo
        assert '123.456.789-10' not in texto_limpo
        assert '456' not in texto_limpo

        assert any(item in removidos for item in ['nome', 'telefone', 'e-mail', 'documento', 'número de endereço'])

        guardado = RepositorioRelatos(sessao).obter(dados['relato']['id'])
        assert 'José Pereira' not in guardado.texto
        assert '98765-4321' not in guardado.texto
        assert 'contato@teste.org' not in guardado.texto

    def test_localizacao_agregada_sem_coordenadas_exatas(self, cliente):
        # localização fica só na célula da grade, sem coordenada GPS exata
        res = cliente.post(f'{API}/relatos', json={'tipos': ['ambiente'], 'cell': '12_34'})
        assert res.status_code == 201
        relato = res.json()['relato']
        assert 'lat' not in relato
        assert 'lng' not in relato
        assert 'latitude' not in relato
        assert 'longitude' not in relato
        assert 'endereco' not in relato
        assert relato['cell'] == '12_34'
