"""Aviso no Telegram (para a patrulha) quando entra um relato novo, de qualquer tipo.

Roda depois da resposta da API (``BackgroundTasks``), com sessão própria, como o push. A mensagem é texto puro (sem
``parse_mode``, então nada do que a usuária escreveu vira formatação) e leva: o tipo, a área (bairro), quando foi, o
ponto aproximado no mapa (centro da célula de ~150 m: o app não guarda o endereço exato) e o texto do relato já limpo
pela anonimização. Qualquer falha é registrada e engolida: o relato já está salvo. O token do bot nunca vai em log.
"""
from __future__ import annotations

import logging

import httpx

from backend.config import Configuracoes, obter_configuracoes
from backend.database import sessao as banco
from backend.database.repositorios import CHAVE_GEOGRAFIA, RepositorioDados
from backend.database.tabelas import Relato
from backend.models.vocabulario import PERIODOS_POR_ID, QUANDO, TIPOS_POR_ID
from backend.services.alertas import PRIORIDADE, ROTULOS
from backend.services.padroes import Grade, Nomes

log = logging.getLogger('aurora.telegram')
LIMITE_TELEGRAM = 4096  # tamanho máximo de uma mensagem


def ids_dos_chats(cfg: Configuracoes) -> list[str]:
    return [c.strip() for c in cfg.telegram_chat_ids.split(',') if c.strip()]


def montar_mensagem(relato: Relato, area: str, ponto: tuple[float, float] | None) -> str:
    titulo = next((ROTULOS[t] for t in PRIORIDADE if t in relato.tipos), ROTULOS['outra'])
    tipos = ', '.join(TIPOS_POR_ID[t].label for t in relato.tipos if t in TIPOS_POR_ID)
    quando = QUANDO.get(relato.quando or '', None)
    periodo = PERIODOS_POR_ID[relato.periodo].long if relato.periodo in PERIODOS_POR_ID else None
    linhas = [f'🚨 Novo relato no mapa Aurora\n{titulo}', f'Área: {area}']
    if tipos:
        linhas.append(f'Ocorrência: {tipos}')
    if quando or periodo:
        linhas.append('Quando: ' + ' · '.join(x for x in (quando, periodo) if x))
    if relato.texto:
        linhas.append(f'Descrição: {relato.texto}')
    if ponto is not None:
        linhas.append(f'https://www.google.com/maps?q={ponto[0]:.5f},{ponto[1]:.5f}')
    return '\n'.join(linhas)[:LIMITE_TELEGRAM]


def notificar_telegram(relato_id: str) -> int:
    """Manda o relato para os chats configurados. Devolve quantas mensagens o Telegram aceitou."""
    cfg = obter_configuracoes()
    if cfg.telegram_bot_token is None or not ids_dos_chats(cfg):
        return 0
    try:
        return _enviar(relato_id, cfg)
    except Exception as e:
        log.warning('aviso no Telegram falhou (%s); o relato foi salvo do mesmo jeito.', type(e).__name__)
        return 0


def _enviar(relato_id: str, cfg: Configuracoes) -> int:
    with banco.SessionLocal() as sessao:
        relato = sessao.get(Relato, relato_id)
        if relato is None:
            return 0
        dados = RepositorioDados(sessao)
        geo = dados.referencia(CHAVE_GEOGRAFIA)
        grade = Grade(geo.dados['hex']) if geo is not None and isinstance(geo.dados.get('hex'), dict) else None
        area = Nomes(grade, dados.bairros(), {})(relato.cell) if grade is not None else 'área não identificada'
        ponto = grade.centro(relato.cell) if grade is not None else None
        texto = montar_mensagem(relato, area, ponto)
    url = f"{cfg.telegram_url}/bot{cfg.telegram_bot_token.get_secret_value()}/sendMessage"
    aceitos = 0
    for chat in ids_dos_chats(cfg):
        try:
            r = httpx.post(url, json={'chat_id': chat, 'text': texto, 'disable_web_page_preview': True},
                           timeout=cfg.telegram_timeout_s)
            r.raise_for_status()
            aceitos += 1
        except httpx.HTTPStatusError as e:  # a URL leva o token: loga só o código, nunca a exceção inteira
            log.warning('Telegram recusou o envio para um chat (HTTP %s).', e.response.status_code)
        except httpx.HTTPError as e:
            log.warning('Telegram fora do ar para um chat (%s).', type(e).__name__)
    return aceitos
