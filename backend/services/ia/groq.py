"""Provedor com modelo na nuvem, via API do Groq (https://console.groq.com). Ao contrário do Ollama, o texto SAI da máquina.

Reaproveita os prompts, a validação da saída e a limpeza de dados pessoais do provedor Ollama; só muda como o modelo é
chamado. O texto passa por ``anonimizar_completo`` antes de sair (telefone, placa, número de casa, e-mail, documento,
perfil e nome dito como "se chama X"; outros nomes podem passar). Sem a chave, o servidor nem sobe. Se o Groq falhar
(rede, limite de uso, resposta fora do JSON esperado), volta para a heurística: o chat nunca fica sem resposta.
"""
from __future__ import annotations

import httpx

from backend.config import obter_configuracoes
from backend.services.enderecos import anonimizar_completo
from backend.services.ia.ollama import ProvedorOllama


class ProvedorGroq(ProvedorOllama):
    nome = 'groq'

    def __init__(self) -> None:
        super().__init__()
        cfg = obter_configuracoes()
        if cfg.groq_api_key is None:
            raise ValueError('O provedor "groq" precisa da chave da API: defina AURORA_GROQ_API_KEY (no ambiente ou no arquivo .env).')
        self._chave = cfg.groq_api_key
        self.modelo = cfg.groq_modelo
        self._url = cfg.groq_url.rstrip('/')

    def _gerar(self, prompt: str, *, json_saida: bool, temperatura: float) -> str:
        corpo = {'model': self.modelo, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': temperatura, 'stream': False}
        if json_saida:
            corpo['response_format'] = {'type': 'json_object'}
        r = httpx.post(self._url + '/chat/completions', timeout=self._timeout, json=corpo,
                       headers={'Authorization': 'Bearer ' + self._chave.get_secret_value()})
        r.raise_for_status()
        try:
            return str(r.json()['choices'][0]['message']['content'])
        except (IndexError, TypeError) as e:
            raise ValueError('resposta do Groq fora do formato esperado') from e

    def extrair_rota(self, texto: str) -> dict:
        # no Ollama (local) a mensagem vai como está; aqui ela sai da máquina, então passa pela limpeza antes
        return super().extrair_rota(anonimizar_completo(texto or '').texto)
