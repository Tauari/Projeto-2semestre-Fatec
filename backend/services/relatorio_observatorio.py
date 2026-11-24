from __future__ import annotations

import io
import csv
import json
import time
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[2]

# Dados estruturados de relatórios de retorno para acompanhamento da rede
_RETORNOS_DB = [
    {
        "id": "ret-01",
        "protocolo_sigiloso": "RET-2026-RC-042",
        "data_registro": "2026-10-26 14:32",
        "vitima_iniciais": "M. S. O.",
        "vitima_idade_aprox": "28 anos",
        "vitima_nome_completo": "Mariana Souza Oliveira",
        "vitima_telefone_protegido": "(19) 9987*-****",
        "bairro_referencia": "Jardim Cervezão",
        "tipo_violencia": "Violência Doméstica / Ameaça Reiterada",
        "canal_entrada": "Aurora Chat Colaborativo",
        "grau_urgencia": "prioridade_urgente",
        "status_retorno": "medida_protetiva_deferida",
        "status_retorno_label": "Medida Protetiva Deferida",
        "orgao_responsavel": "Secretaria da Mulher & DDM Rio Claro",
        "ultimo_despacho_data": "2026-10-30 16:45",
        "relato_resumo": "Vítima buscou orientação pelo app após ameaças do ex-companheiro. Encaminhada ao CAM e à DDM para medida protetiva.",
        "despachos": [
            {
                "id": "dsp-01",
                "data": "2026-10-30 16:45",
                "orgao": "Vara da Família / DDM Rio Claro",
                "responsavel_nome": "Dra. Helena Martins",
                "responsavel_cargo": "Coordenadora de Proteção",
                "status_anterior": "acolhida_cam",
                "status_novo": "medida_protetiva_deferida",
                "parecer_tecnico": "Decisão judicial proferida deferindo afastamento do agressor por 300 metros e proibição de qualquer contato. Patrulha Maria da Penha cadastrou o endereço para rondas periódicas.",
                "encaminhamentos": ["Monitoramento por Patrulha Maria da Penha", "Acompanhamento psicológico continuado no CAM"]
            },
            {
                "id": "dsp-02",
                "data": "2026-10-27 10:15",
                "orgao": "CAM - Centro de Atendimento à Mulher",
                "responsavel_nome": "Valéria Santos, MSW",
                "responsavel_cargo": "Assistente Social de Referência",
                "status_anterior": "aguardando_contato_seguro",
                "status_novo": "acolhida_cam",
                "parecer_tecnico": "Realizada escuta qualificada presencial no prédio da Secretaria da Mulher. Avaliação de risco apontou score elevado.",
                "encaminhamentos": ["Encaminhamento formal à DDM para pedido de MPU", "Cadastramento no programa de auxílio emergencial"]
            }
        ],
        "historico_acessos": [
            {
                "data": "2026-10-27 09:30",
                "profissional_nome": "Valéria Santos, MSW",
                "profissional_email": "valeria.santos@mulher.rioclaro.sp.gov.br",
                "justificativa": "Agendamento de acolhimento presencial inicial e conferência de segurança do número de telefone.",
                "dados_acessados": "Nome civil completo e telefone direto da usuária (LGPD Art. 7º, II)"
            }
        ]
    },
    {
        "id": "ret-02",
        "protocolo_sigiloso": "RET-2026-RC-043",
        "data_registro": "2026-10-28 19:10",
        "vitima_iniciais": "A. C. L.",
        "vitima_idade_aprox": "34 anos",
        "vitima_nome_completo": "Aline Cristina Lima",
        "vitima_telefone_protegido": "(19) 9876*-****",
        "bairro_referencia": "Centro",
        "tipo_violencia": "Perseguição Reiterada (Stalking)",
        "canal_entrada": "Plantão Noturno",
        "grau_urgencia": "alta",
        "status_retorno": "patrulha_acionada",
        "status_retorno_label": "Patrulha Acionada",
        "orgao_responsavel": "Guarda Civil Municipal & Secretaria da Mulher",
        "ultimo_despacho_data": "2026-10-29 08:30",
        "relato_resumo": "Vítima relata perseguição por indivíduo não identificado na saída do trabalho comercial no Centro.",
        "despachos": [
            {
                "id": "dsp-03",
                "data": "2026-10-29 08:30",
                "orgao": "GCM / Patrulha Mulher Segura",
                "responsavel_nome": "Inspetor Carlos Eduardo",
                "responsavel_cargo": "Comandante Operacional",
                "status_anterior": "aguardando_contato_seguro",
                "status_novo": "patrulha_acionada",
                "parecer_tecnico": "Ponto de visibilidade preventiva inserido na escala do horário das 18h às 21h na Rua 3 com Av. 2.",
                "encaminhamentos": ["Ronda no itinerário comercial", "Acolhimento agendado no CAM"]
            }
        ],
        "historico_acessos": []
    }
]

# Base de ocorrências analíticas integrando dados oficiais, comunidade e pesquisa
_OCORRENCIAS_BASE = [
    {
        "id": "bo-001",
        "protocolo": "SSP-2025-RC-10492",
        "data": "2025-11-14",
        "tipo": "violencia_domestica",
        "tipo_label": "Violência Doméstica (Lesão Corporal)",
        "bairro": "Jardim Cervezão",
        "periodo": "22-00",
        "periodo_label": "22h–00h",
        "fonte": "boletim_oficial",
        "fonte_label": "Boletim Oficial (SSP-SP)",
        "descricao_anonima": "Ocorrência registrada com medida protetiva expedida na DDM Rio Claro. Agressão física e ameaça.",
        "confirmacoes": 1,
        "status_validacao": "oficial",
        "grau_risco": "critico"
    },
    {
        "id": "rel-001",
        "protocolo": "AURORA-2026-0891",
        "data": "2026-10-24",
        "tipo": "perseguicao",
        "tipo_label": "Perseguição a pé (homem seguindo)",
        "bairro": "Centro",
        "periodo": "20-22",
        "periodo_label": "20h–22h",
        "fonte": "relato_comunidade",
        "fonte_label": "Relato da comunidade",
        "descricao_anonima": "Fui seguida da Rua 3 até a esquina da Av. 2. Acelerava o passo quando eu acelerava. Consegui entrar em uma farmácia aberta.",
        "confirmacoes": 8,
        "status_validacao": "verificado",
        "grau_risco": "alto"
    },
    {
        "id": "pesq-001",
        "protocolo": "PESQ-RC-016",
        "data": "2026-09-15",
        "tipo": "intimidacao",
        "tipo_label": "Pessoas encarando de forma intimidadora",
        "bairro": "Bela Vista / Unesp",
        "periodo": "22-00",
        "periodo_label": "22h–00h",
        "fonte": "pesquisa_percepcao",
        "fonte_label": "Pesquisa Segurança Mulheres RC",
        "descricao_anonima": "Região universitária citada por respondentes como ponto de apreensão no período noturno devido a pouca circulação.",
        "confirmacoes": 16,
        "status_validacao": "oficial",
        "grau_risco": "medio"
    }
]


def obter_relatorio_observatorio(
    fonte: str | None = None,
    tipo: str | None = None,
    bairro: str | None = None,
    periodo: str | None = None,
    ano: str | None = None,
    busca: str | None = None,
) -> dict[str, Any]:
    """Filtra ocorrências e computa KPIs para integrantes do Observatório (US 01)."""
    itens = list(_OCORRENCIAS_BASE)

    if fonte and fonte != 'todas':
        itens = [i for i in itens if i['fonte'] == fonte]
    if tipo and tipo != 'todos':
        itens = [i for i in itens if i['tipo'] == tipo]
    if bairro and bairro != 'todos':
        itens = [i for i in itens if i['bairro'].lower() == bairro.lower()]
    if periodo and periodo != 'todos':
        itens = [i for i in itens if i['periodo'] == periodo]
    if ano and ano != 'todos':
        itens = [i for i in itens if i['data'].startswith(ano)]
    if busca and busca.strip():
        t = busca.lower().strip()
        itens = [
            i for i in itens
            if t in i['protocolo'].lower()
            or t in i['bairro'].lower()
            or t in i['tipo_label'].lower()
            or t in i['descricao_anonima'].lower()
        ]

    total = len(itens)
    oficiais = sum(1 for i in itens if i['fonte'] == 'boletim_oficial')
    comunitarios = sum(1 for i in itens if i['fonte'] == 'relato_comunidade')
    pesquisa = sum(1 for i in itens if i['fonte'] == 'pesquisa_percepcao')
    vd = sum(1 for i in itens if 'violencia_domestica' in i['tipo'] or 'feminicidio' in i['tipo'])

    bairro_counts: dict[str, int] = {}
    periodo_counts: dict[str, int] = {}
    tipo_counts: dict[str, dict[str, Any]] = {}

    for i in itens:
        b = i['bairro']
        bairro_counts[b] = bairro_counts.get(b, 0) + 1
        p = i['periodo']
        periodo_counts[p] = periodo_counts.get(p, 0) + 1
        tp = i['tipo']
        if tp not in tipo_counts:
            tipo_counts[tp] = {"tipo": tp, "label": i['tipo_label'], "total": 0}
        tipo_counts[tp]["total"] += 1

    top_bairro = max(bairro_counts.items(), key=lambda x: x[1], default=("Centro", 0))
    top_periodo = max(periodo_counts.items(), key=lambda x: x[1], default=("22-00", 0))

    kpis = {
        "total_ocorrencias": total,
        "total_oficiais": oficiais,
        "total_comunitarios": comunitarios,
        "total_pesquisa": pesquisa,
        "violencia_domestica_pct": round((vd / total) * 100) if total else 0,
        "via_publica_pct": max(0, 100 - (round((vd / total) * 100) if total else 0)),
        "bairro_mais_critico": {"nome": top_bairro[0], "total": top_bairro[1]},
        "periodo_mais_critico": {"id": top_periodo[0], "label": top_periodo[0], "total": top_periodo[1]},
        "taxa_confirmacao_comunitaria": 100 if comunitarios else 0
    }

    dist_tipos = [
        {"tipo": v["tipo"], "label": v["label"], "total": v["total"], "pct": round((v["total"] / total) * 100) if total else 0}
        for v in sorted(tipo_counts.values(), key=lambda x: x["total"], reverse=True)
    ]
    dist_bairros = [
        {"bairro": k, "total": v, "pct": round((v / total) * 100) if total else 0}
        for k, v in sorted(bairro_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    ordem_horarios = ["manha", "tarde", "18-20", "20-22", "22-00", "madrugada"]
    labels_horarios = {
        "manha": "Manhã (6h–12h)", "tarde": "Tarde (12h–18h)",
        "18-20": "18h–20h", "20-22": "20h–22h",
        "22-00": "22h–00h", "madrugada": "Madrugada (0h–6h)"
    }
    dist_horarios = [
        {"periodo": h, "label": labels_horarios.get(h, h), "total": periodo_counts.get(h, 0), "pct": round((periodo_counts.get(h, 0) / total) * 100) if total else 0}
        for h in ordem_horarios
    ]

    return {
        "kpis": kpis,
        "ocorrencias": itens,
        "distribuicao_tipos": dist_tipos,
        "distribuicao_bairros": dist_bairros,
        "distribuicao_horarios": dist_horarios
    }


def obter_retornos_secretaria(desbloqueados_ids: set[str] | None = None) -> list[dict[str, Any]]:
    """Retorna os relatórios de retorno da Secretaria da Mulher com privacidade LGPD (US 05)."""
    desbloqueados = desbloqueados_ids or set()
    saida = []
    for r in _RETORNOS_DB:
        copia = dict(r)
        if r["id"] not in desbloqueados:
            copia["vitima_nome_completo"] = None
            copia["vitima_telefone_protegido"] = None
        saida.append(copia)
    return saida


def adicionar_despacho(retorno_id: str, despacho_data: dict[str, Any], profissional: dict[str, Any]) -> dict[str, Any] | None:
    """Insere novo despacho institucional e atualiza status do caso (US 05)."""
    agora = time.strftime('%Y-%m-%d %H:%M')
    for r in _RETORNOS_DB:
        if r["id"] == retorno_id:
            novo_despacho = {
                "id": f"dsp-{int(time.time())}",
                "data": agora,
                "orgao": despacho_data["orgao"],
                "responsavel_nome": profissional.get("nome", "Técnica da Secretaria"),
                "responsavel_cargo": profissional.get("cargo", "Assistente Social"),
                "status_anterior": r["status_retorno"],
                "status_novo": despacho_data["status_novo"],
                "parecer_tecnico": despacho_data["parecer_tecnico"],
                "encaminhamentos": despacho_data.get("encaminhamentos", [])
            }
            r["status_retorno"] = despacho_data["status_novo"]
            r["ultimo_despacho_data"] = agora
            r["despachos"].insert(0, novo_despacho)
            return r
    return None


def registrar_termo_sigilo(retorno_id: str, justificativa: str, profissional: dict[str, Any]) -> dict[str, Any] | None:
    """Registra termo de sigilo na trilha de auditoria e libera dados completos sob LGPD (US 05)."""
    agora = time.strftime('%Y-%m-%d %H:%M')
    for r in _RETORNOS_DB:
        if r["id"] == retorno_id:
            auditoria = {
                "data": agora,
                "profissional_nome": profissional.get("nome", "Dra. Helena Martins"),
                "profissional_email": profissional.get("email", "helena.martins@mulher.rioclaro.sp.gov.br"),
                "justificativa": justificativa,
                "dados_acessados": "Prontuário completo e dados de contato seguro (LGPD Art. 7º e Lei 11.340)"
            }
            r["historico_acessos"].insert(0, auditoria)
            return r
    return None


def exportar_csv_observatorio(itens: list[dict[str, Any]], delimitador: str = ';') -> str:
    """Gera CSV compatível com Excel brasileiro com BOM UTF-8 (US 06)."""
    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM
    writer = csv.writer(output, delimiter=delimitador, quoting=csv.QUOTE_MINIMAL)
    writer.writerow([
        "Protocolo", "Data", "Tipo de Ocorrencia", "Bairro / Regiao",
        "Faixa Horaria", "Fonte de Dados", "Status Validacao",
        "Grau de Risco", "Confirmacoes", "Descricao Anonima"
    ])
    for i in itens:
        writer.writerow([
            i.get("protocolo", ""),
            i.get("data", ""),
            i.get("tipo_label", ""),
            i.get("bairro", ""),
            i.get("periodo_label", ""),
            i.get("fonte_label", ""),
            i.get("status_validacao", ""),
            i.get("grau_risco", ""),
            i.get("confirmacoes", 0),
            i.get("descricao_anonima", "")
        ])
    return output.getvalue()
