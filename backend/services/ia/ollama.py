"""Provedor com modelo local, via Ollama (https://ollama.com). O texto não sai da máquina.

Usa o prompt e a validação do legado (``prompts.py``). Se o Ollama estiver desligado, demorar demais ou responder
algo que não é o JSON esperado, volta para o provedor heurístico: o chat nunca fica sem resposta.
"""
from __future__ import annotations

import json
import logging
import re

import httpx

from backend.config import obter_configuracoes
from backend.services.enderecos import anonimizar_completo
from backend.services.ia.base import ContextoIA, ProvedorIA, ResultadoExtracao
from backend.services.ia.heuristico import ProvedorHeuristico
from backend.services.ia.prompts import montar_prompt_extracao, validar_saida_extracao

log = logging.getLogger(__name__)
_SENSIVEL = re.compile(r'nome|apelido|telefone|placa|n[úu]mero|endere|perfil|rede|f[íi]sic|e-?mail|cpf|documento', re.I)


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

    def extrair_local(self, texto: str) -> dict:
        # o modelo só vê o texto já sem nomes, telefones, placas e números de casa
        seguro = anonimizar_completo(texto)
        prompt = ('Você é a Aurora, assistente de um mapa de segurança para mulheres em Rio Claro (SP). Leia o relato e separe ONDE foi e o que é dado pessoal. '
                  'Use só o que está escrito; não invente.\n'
                  '- ruas: ruas e avenidas do lugar ONDE ACONTECEU (não a rua onde ela mora), como escritas (ex.: "Rua 5", "Avenida 14"), sem número de casa; no máximo 4.\n'
                  '- pontos: lugares conhecidos usados como referência (ex.: "Fatec", "rodoviária", "shopping", "Santa Casa"); no máximo 3.\n'
                  '- referencia: o trecho do relato que diz onde foi (ex.: "Rua 5 com Avenida 14, na frente da Fatec"), ou null.\n'
                  '- sensiveis: o que no relato é dado pessoal ou revela um lugar exato: nome, apelido, telefone, placa, número de casa, endereço exato, '
                  'perfil de rede social, característica física muito específica. Escreva só o tipo (ex.: "nome", "placa"), nunca o dado. [] se nada.\n'
                  '- descricao: o relato reescrito em primeira pessoa, 1 ou 2 frases, até 200 caracteres, SEM ruas, avenidas, pontos de referência, nomes, telefones, placas ou números de casa. Mantenha o que ajuda a entender a situação e a reconhecer quem agrediu pelas roupas e acessórios (ex.: "boina verde", "capuz cinza", "camiseta azul", "moto preta"). TIRE a descrição física da pessoa (altura, peso, cor da pele, cabelo, barba, tatuagem, cicatriz, idade). "" se não houver situação.\n'
                  'Exemplo: Mensagem: "Fui seguida ontem na rua 7 esquina com a av 29, perto do Shopping, o cara alto e careca de boina verde se chamava Zé"\n'
                  'Resposta: {"ruas":["Rua 7","Avenida 29"],"pontos":["Shopping"],"referencia":"Rua 7 esquina com a Avenida 29, perto do Shopping","sensiveis":["nome"],"descricao":"Fui seguida por um homem de boina verde."}\n\n'
                  'Responda só com JSON: {"ruas":[],"pontos":[],"referencia":null,"sensiveis":[],"descricao":""}\n\nMensagem: "' + seguro.texto[:1000].replace('"', "'") + '"')
        try:
            r = httpx.post(self._url + '/api/generate', timeout=self._timeout, json={
                'model': self.modelo, 'prompt': prompt, 'format': 'json', 'stream': False, 'keep_alive': '30m', 'options': {'temperature': 0}})
            r.raise_for_status()
            o = json.loads(r.json()['response'])
        except (httpx.HTTPError, ValueError, KeyError) as e:
            log.warning('ollama indisponível ou resposta inválida (%s): sem local', type(e).__name__)
            o = {}
        o = o if isinstance(o, dict) else {}

        def lista(chave, maximo, tamanho):
            v = o.get(chave)
            return [x.strip()[:tamanho] for x in v if isinstance(x, str) and x.strip() and x.strip().lower() not in ('null', 'none')][:maximo] if isinstance(v, list) else []
        ref = o.get('referencia')
        return {'ruas': lista('ruas', 4, 60), 'pontos': lista('pontos', 3, 60),
                'referencia': anonimizar_completo(ref.strip()[:160]).texto if isinstance(ref, str) and ref.strip() else None,
                'sensiveis': list(dict.fromkeys(seguro.removidos + [s for s in lista('sensiveis', 6, 30) if _SENSIVEL.search(s)]))[:6],  # o modelo às vezes chama roupa de dado sensível
                'descricao': anonimizar_completo(desc.strip()[:220]).texto if isinstance(desc := o.get('descricao'), str) else ''}

    def extrair(self, texto: str, contexto: ContextoIA) -> ResultadoExtracao:
        # o modelo só vê o texto já sem nomes, telefones e placas: um modelo pequeno deixaria passar dado pessoal
        seguro = anonimizar_completo(texto)
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
        limpo = anonimizar_completo(res.descricao)
        res.descricao = limpo.texto
        res.removidos = list(dict.fromkeys(seguro.removidos + limpo.removidos))[:6]
        # dia e horário são regras fixas (ex.: "21h" = 20-22): a heurística acerta mais que um modelo de 3B; o modelo só completa
        res.quando, res.periodo = heur.quando or res.quando, heur.periodo or res.periodo
        res.tipos = res.tipos or heur.tipos  # modelo pequeno às vezes devolve lista vazia
        res.por_modelo = True
        return res
