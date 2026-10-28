"""GET /dashboard/resumo: contagens descritivas dos relatos da janela, e cada evidência na sua seção."""
from __future__ import annotations

import json
from pathlib import Path

from backend.database.repositorios import DIA_MS, instante_atual_ms
from backend.services.analise_padroes import contar_relatos

API = '/api/v1'
RAIZ = Path(__file__).resolve().parents[2]


def test_resumo_sem_relatos(cliente):
    r = cliente.get(API + '/dashboard/resumo')
    assert r.status_code == 200
    resumo = r.json()
    assert resumo['relatos_comunidade'] == {
        'tipo_evidencia': 'relato_comunidade', 'janela_dias': 30, 'total': 0, 'por_tipo': {}, 'por_periodo': {}, 'por_celula': {},
        'aviso': 'Relatos enviados por usuárias, sem verificação individual. Mostram concentração de relatos, não risco.'}
    assert resumo['classificacoes_automaticas'] == {'tipo_evidencia': 'classificacao_automatica', 'total': 0, 'por_provedor': {}}
    assert resumo['analise_ia'] == {'tipo_evidencia': 'analise_ia', 'implementado': True}
    d = json.loads((RAIZ / 'dados' / 'data.json').read_bytes().decode('utf-8'))
    assert resumo['dados_oficiais'] == [{'chave': 'bo-ssp-2025-2026', 'titulo': 'Boletins de ocorrência (SSP-SP, base R.D.O. via FALASP)',
                                         'periodo': d['bo']['periodo'], 'tipo_evidencia': 'dado_oficial',
                                         'total': {k: d['bo']['total'][k] for k in ('vd', 'fe', 'te', 'n')}}]
    assert resumo['percepcao'] == [{'chave': 'pesquisa-percepcao-2026', 'titulo': 'Pesquisa “Segurança e percepção das mulheres em Rio Claro”',
                                    'tipo_evidencia': 'percepcao', 'respostas': d['pesq']['n'], 'de': d['pesq']['de'], 'ate': d['pesq']['ate']}]


def test_resumo_conta_como_contar_relatos(cliente, publicar, inserir_relato):
    publicar(tipos=['assedio', 'roubo'], cell='0_0', periodo='20-22')
    publicar(tipos=['assedio'], cell='0_0', periodo=None)
    publicar(tipos=['perseguicao', 'assedio'], cell='-1_2', periodo='madrugada', texto='um cara me seguiu')
    publicar(tipos=['ambiente'], cell='3_3', periodo='20-22')
    inserir_relato(instante_atual_ms() - 45 * DIA_MS, tipos=['violencia'], cell='9_9', periodo='manha')  # fora da janela
    relatos = cliente.get(API + '/relatos').json()['relatos']
    resumo = cliente.get(API + '/dashboard/resumo').json()['relatos_comunidade']
    esperado = contar_relatos(relatos)
    assert {k: resumo[k] for k in ('total', 'por_tipo', 'por_periodo', 'por_celula')} == esperado
    assert resumo['total'] == 4
    assert resumo['por_tipo'] == {'assedio': 3, 'roubo': 1, 'perseguicao': 1, 'ambiente': 1}
    assert resumo['por_periodo'] == {'20-22': 2, 'madrugada': 1}
    assert resumo['por_celula'] == {'0_0': 2, '-1_2': 1, '3_3': 1}
    assert 'violencia' not in resumo['por_tipo'] and '9_9' not in resumo['por_celula']


def test_resumo_segue_a_janela_da_configuracao(criar_cliente, inserir_relato):
    c = criar_cliente(relatos_janela_dias=60)
    inserir_relato(instante_atual_ms() - 45 * DIA_MS, tipos=['violencia'], cell='9_9')
    resumo = c.get(API + '/dashboard/resumo').json()['relatos_comunidade']
    assert resumo['janela_dias'] == 60
    assert resumo['total'] == 1
    assert resumo['por_tipo'] == {'violencia': 1}


def test_classificacoes_por_provedor(cliente, publicar):
    publicar(texto='um cara me seguiu')
    publicar(texto='ficou me encarando')
    publicar(texto='')
    resumo = cliente.get(API + '/dashboard/resumo').json()
    assert resumo['classificacoes_automaticas'] == {'tipo_evidencia': 'classificacao_automatica', 'total': 2,
                                                    'por_provedor': {'heuristica': 2}}
    assert resumo['relatos_comunidade']['total'] == 3
