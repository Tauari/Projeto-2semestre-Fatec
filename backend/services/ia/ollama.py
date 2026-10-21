"""Provedor com modelo local, via Ollama (https://ollama.com). O texto não sai da máquina.

Usa o prompt e a validação do legado (``prompts.py``). Se o Ollama estiver desligado, demorar demais ou responder
algo que não é o JSON esperado, volta para o provedor heurístico: o chat nunca fica sem resposta.
"""
from __future__ import annotations

import json
import logging

import httpx

from backend.config import obter_configuracoes
from backend.services.anonimizacao import anonimizar_texto
from backend.services.ia.base import ContextoIA, ProvedorIA, ResultadoExtracao
from backend.services.ia.heuristico import ProvedorHeuristico
from backend.services.ia.prompts import montar_prompt_extracao, validar_saida_extracao

log = logging.getLogger(__name__)


class ProvedorOllama(ProvedorIA):
    nome = 'ollama'
    usa_modelo = True
    capacidades = frozenset({'extrair', 'classificar'})

    def __init__(self) -> None:
        cfg = obter_configuracoes()
        self.modelo = cfg.ia_modelo
        self._url = cfg.ia_ollama_url.rstrip('/')
        self._timeout = cfg.ia_timeout_s

    def extrair_rota(self, texto: str) -> dict:
        prompt = ('Você é a Aurora, assistente de um mapa de segurança em Rio Claro (SP). A pessoa quer uma rota. Extraia o ponto de partida, '
                  'o destino e como ela vai. origem e destino: nome da rua, avenida ou bairro, como foi escrito (sem inventar), ou null. '
                  'modo: "pe" (a pé), "bike" (bicicleta) ou "carro" (carro ou moto); null se não disser.\n'
                  'Responda só com JSON: {"origem":null,"destino":null,"modo":null}\n\nMensagem: ' + (texto or '')[:300].replace('"', "'"))
        try:
            r = httpx.post(self._url + '/api/generate', timeout=self._timeout, json={
                'model': self.modelo, 'prompt': prompt, 'format': 'json', 'stream': False, 'keep_alive': '30m', 'options': {'temperature': 0}})
            r.raise_for_status()
            o = json.loads(r.json()['response'])
        except (httpx.HTTPError, ValueError, KeyError) as e:
            log.warning('ollama indisponível ou resposta inválida (%s): sem rota', type(e).__name__)
            o = {}
        nome = lambda v: v.strip()[:80] if isinstance(v, str) and v.strip() else None  # noqa: E731
        o = o if isinstance(o, dict) else {}
        return {'origem': nome(o.get('origem')), 'destino': nome(o.get('destino')), 'modo': o.get('modo') if o.get('modo') in ('pe', 'bike', 'carro') else None}

    def extrair(self, texto: str, contexto: ContextoIA) -> ResultadoExtracao:
        # o modelo só vê o texto já sem nomes, telefones e placas: um modelo pequeno deixaria passar dado pessoal
        seguro = anonimizar_texto(texto)
        prompt = montar_prompt_extracao(seguro.texto, [b.nome for b in contexto.bairros])
        try:
            r = httpx.post(self._url + '/api/generate', timeout=self._timeout, json={
                'model': self.modelo, 'prompt': prompt, 'format': 'json', 'stream': False,
                'keep_alive': '30m',  # senão o Ollama descarrega o modelo após 5 min parado e o próximo uso demora
                'options': {'temperature': 0.1}})
            r.raise_for_status()
            res = validar_saida_extracao(json.loads(r.json()['response']), contexto.bairros)
        except (httpx.HTTPError, ValueError, KeyError) as e:
            log.warning('ollama indisponível ou resposta inválida (%s): usando a heurística', type(e).__name__)
            res = None
        heur = ProvedorHeuristico().extrair(texto, contexto)
        if res is None:
            return heur
        # o modelo pode deixar passar um dado pessoal: a descrição passa de novo pela limpeza antes de sair
        limpo = anonimizar_texto(res.descricao)
        res.descricao = limpo.texto
        res.removidos = list(dict.fromkeys(seguro.removidos + limpo.removidos))[:6]
        # dia e horário são regras fixas (ex.: "21h" = 20-22): a heurística acerta mais que um modelo de 3B; o modelo só completa
        res.quando, res.periodo = heur.quando or res.quando, heur.periodo or res.periodo
        res.tipos = res.tipos or heur.tipos  # modelo pequeno às vezes devolve lista vazia
        res.por_modelo = True
        return res
