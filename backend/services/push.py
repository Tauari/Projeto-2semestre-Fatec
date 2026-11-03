"""Notificação no celular (Expo Push) quando um relato novo cai numa área que alguém acompanha.

Roda depois da resposta da API (``BackgroundTasks``), com sessão própria. O título é o alerta padronizado do tipo
(``alertas.titulo_alerta``) e o corpo é só o nome da área; a descrição que a usuária escreveu (roupa, por exemplo)
nunca vai na notificação. Cada aparelho recebe no máximo uma notificação a cada ``push_intervalo_min`` minutos, e
quem enviou o relato não é avisado do próprio relato. Qualquer falha é registrada e engolida: o relato já está salvo.
"""
from __future__ import annotations

import logging

import httpx

from backend.config import Configuracoes, obter_configuracoes
from backend.database import sessao as banco
from backend.database.repositorios import CHAVE_GEOGRAFIA, RepositorioDados, RepositorioPush, instante_atual_ms
from backend.database.tabelas import Relato
from backend.services.alertas import titulo_alerta
from backend.services.padroes import Grade, Nomes

log = logging.getLogger('aurora.push')
LOTE = 100  # o Expo aceita até 100 mensagens por requisição
MINUTO_MS = 60_000


def na_area(grade: Grade | None, cell: str, area: str) -> bool:
    """O relato (célula ``cell``) está na área acompanhada ``area``, seja ela de ~150 m ou de ~1 km."""
    if area[:1] == 'f':
        return cell == area
    return grade is not None and grade.grossa(cell) == area


def notificar_relato(relato_id: str, ignorar_token: str | None = None) -> int:
    """Avisa os aparelhos que acompanham a área do relato. Devolve quantas notificações o Expo aceitou."""
    cfg = obter_configuracoes()
    if not cfg.push_ativo:
        return 0
    try:
        return _notificar(relato_id, ignorar_token, cfg)
    except Exception as e:
        log.warning('notificação falhou (%s); o relato foi salvo do mesmo jeito.', type(e).__name__)
        return 0


def _notificar(relato_id: str, ignorar_token: str | None, cfg: Configuracoes) -> int:
    with banco.SessionLocal() as sessao:
        relato = sessao.get(Relato, relato_id)
        titulo = titulo_alerta(relato.tipos) if relato is not None else None
        if titulo is None:
            return 0
        push, dados = RepositorioPush(sessao), RepositorioDados(sessao)
        geo = dados.referencia(CHAVE_GEOGRAFIA)
        grade = Grade(geo.dados['hex']) if geo is not None and isinstance(geo.dados.get('hex'), dict) else None
        agora = instante_atual_ms()
        intervalo = cfg.push_intervalo_min * MINUTO_MS
        alvos = [d for d in push.com_areas()
                 if d.token != ignorar_token and agora - d.ultimo_envio >= intervalo
                 and any(na_area(grade, relato.cell, a) for a in d.areas)]
        if not alvos:
            return 0
        corpo = Nomes(grade, dados.bairros(), {})(relato.cell) if grade is not None else 'Numa área que você acompanha'
        mensagens = [{'to': d.token, 'title': titulo, 'body': corpo, 'sound': 'default', 'priority': 'high',
                      'channelId': 'alertas', 'data': {'cell': relato.cell, 'relato': relato.id}} for d in alvos]
        aceitos: list[str] = []
        invalidos: list[str] = []
        for i in range(0, len(mensagens), LOTE):
            lote = mensagens[i:i + LOTE]
            r = httpx.post(cfg.push_url, json=lote, timeout=cfg.push_timeout_s,
                           headers={'Accept': 'application/json', 'Content-Type': 'application/json'})
            r.raise_for_status()
            tickets = r.json().get('data', [])
            if isinstance(tickets, dict):
                tickets = [tickets]
            for msg, ticket in zip(lote, tickets):
                if ticket.get('status') == 'ok':
                    aceitos.append(msg['to'])
                elif (ticket.get('details') or {}).get('error') == 'DeviceNotRegistered':
                    invalidos.append(msg['to'])  # app desinstalado: não adianta tentar de novo
        push.marcar_envio(aceitos, agora)
        push.remover_varios(invalidos)
        sessao.commit()
        return len(aceitos)
