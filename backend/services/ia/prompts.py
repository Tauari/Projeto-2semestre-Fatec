"""Prompt de extração do legado (``aiExtract``, src/app.js:1277-1312) e validação da saída de um modelo.

Ficam prontos para a fase 2 (provedor com modelo); nenhuma rota os usa ainda.
"""
from __future__ import annotations

import math
from decimal import Decimal

from backend.models.vocabulario import PERIODOS_POR_ID, QUANDO, TIPOS_POR_ID
from backend.services.classificacao import casar_bairro
from backend.services.ia.base import ResultadoExtracao
from backend.services.texto import aparar_js, fatiar_js


def montar_prompt_extracao(texto: str, nomes_bairros: list[str]) -> str:
    """A mesma string que o legado monta em ``aiExtract`` (app.js:1279-1291)."""
    nomes = '; '.join(nomes_bairros)
    prompt = ('Você é a Aurora, assistente de um mapa colaborativo de segurança para mulheres em Rio Claro (SP). Uma mulher escreveu a mensagem abaixo para registrar uma situação. Extraia os campos e reescreva a descrição sem dados pessoais.\n\n' +
              'Regras:\n' +
              '- descricao: 1 ou 2 frases em primeira pessoa, até 220 caracteres, em português, só com o que está na mensagem. Tire nomes, apelidos, telefones, e-mails, CPF, placas de veículos, perfis de redes sociais, números de casa, endereços exatos e nomes de estabelecimentos que identifiquem alguém. Tire características físicas muito específicas de uma pessoa (tatuagens, roupas únicas). Mantenha descrições genéricas, como "um homem de moto". Não acuse ninguém pelo nome e não invente detalhes. Se a mensagem não descreve uma situação, use "".\n' +
              '- tipos: ids desta lista, no máximo 3: assedio (assédio verbal), perseguicao (perseguição, me seguiram), abordagem (abordagem indesejada, insistência), intimidacao (encarar, intimidar), exposicao (exposição sexual), roubo (roubo ou furto), violencia (violência física), veiculo (carro, moto, app de transporte ou motorista envolvido), ambiente (rua escura, deserta, sem iluminação), outra.\n' +
              '- bairro: se a mensagem citar um lugar de Rio Claro, o nome mais próximo desta lista; senão null. Referências: Unesp = "Bela Vista"; Lago Azul = "Vila Operária"; Rodoviária = "Jardim Claret"; Estação ou Jardim Público = "Centro". Lista: ' + nomes + '\n' +
              '- quando: "hoje", "ontem", "semana" (nesta semana) ou "antes" (há mais de uma semana); null se não disser.\n' +
              '- periodo: "manha" (6h-12h), "tarde" (12h-18h), "18-20", "20-22", "22-00" ou "madrugada" (0h-6h); null se não der para saber ("à noite" sem hora = null).\n' +
              '- urgente: true só se ela disser que está em perigo neste momento.\n' +
              '- removidos: lista curta do que você tirou do texto (ex.: "nome", "placa", "telefone"); [] se nada.\n' +
              '- resposta: uma frase curta, acolhedora e sem julgamento, falando com ela.\n\n' +
              'Responda só com JSON neste formato:\n{"urgente":false,"tipos":[],"bairro":null,"quando":null,"periodo":null,"descricao":"","removidos":[],"resposta":""}\n\n' +
              'Mensagem:\n"""' + fatiar_js(texto, 1500).replace('"""', '"') + '"""')
    return prompt


def _numero_js(x: float) -> str:
    # Number.prototype.toString (ECMA-262 Number::toString, base 10)
    if math.isnan(x):
        return 'NaN'
    if math.isinf(x):
        return 'Infinity' if x > 0 else '-Infinity'
    if x == 0:
        return '0'
    if x < 0:
        return '-' + _numero_js(-x)
    _, digitos, exp = Decimal(repr(x)).as_tuple()
    d = ''.join(map(str, digitos)).rstrip('0')
    k = len(d)
    n = exp + len(digitos)
    if k <= n <= 21:
        return d + '0' * (n - k)
    if 0 < n <= 21:
        return d[:n] + '.' + d[n:]
    if -6 < n <= 0:
        return '0.' + '0' * (-n) + d
    e = n - 1
    sinal = '+' if e >= 0 else '-'
    return (d if k == 1 else d[0] + '.' + d[1:]) + 'e' + sinal + str(abs(e))


def _string_js(x) -> str:
    """``String(x)`` do JS para valores vindos de JSON."""
    if isinstance(x, str):
        return x
    if x is None:
        return 'null'
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, (int, float)):
        try:
            return _numero_js(float(x))
        except OverflowError:  # inteiro grande demais: no JSON.parse vira Infinity
            return 'Infinity' if x > 0 else '-Infinity'
    if isinstance(x, (list, tuple)):
        return ','.join('' if v is None else _string_js(v) for v in x)
    return '[object Object]'


def validar_saida_extracao(obj, bairros) -> ResultadoExtracao | None:
    """Porte da normalização da saída do modelo em ``aiExtract`` (app.js:1294-1305).

    Só aceita ids próprios do vocabulário (no JS, ``TIPO[t]`` também aceitava nomes herdados do
    Object.prototype, como "constructor").
    """
    if isinstance(obj, (list, tuple)):
        o = {}  # no JS, um array passa no typeof 'object' e não tem nenhum desses campos
    elif isinstance(obj, dict):
        o = obj
    else:
        return None
    tipos = o.get('tipos')
    quando = o.get('quando')
    periodo = o.get('periodo')
    descricao = o.get('descricao')
    removidos = o.get('removidos')
    resposta = o.get('resposta')
    bairro = o.get('bairro')
    return ResultadoExtracao(
        urgente=o.get('urgente') is True,
        tipos=[t for t in map(_string_js, tipos) if t in TIPOS_POR_ID][:3] if isinstance(tipos, list) else [],
        bairro=casar_bairro(bairro, bairros) if isinstance(bairro, str) else None,
        quando=quando if isinstance(quando, str) and quando in QUANDO else None,
        periodo=periodo if isinstance(periodo, str) and periodo in PERIODOS_POR_ID else None,
        descricao=fatiar_js(aparar_js(descricao), 300) if isinstance(descricao, str) else '',
        removidos=[fatiar_js(_string_js(x), 30) for x in removidos][:6] if isinstance(removidos, list) else [],
        resposta=fatiar_js(aparar_js(resposta), 220) if isinstance(resposta, str) else '',
    )
