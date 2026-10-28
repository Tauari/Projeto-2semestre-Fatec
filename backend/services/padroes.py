"""Padrões nos dados (US-02): onde, quando e que tipo de ocorrência mais aparece, com a evidência de cada achado.

Como funciona: a *detecção* é por regras que qualquer pessoa consegue conferir (contagens, parcelas e limites mínimos de
amostra). A IA entra depois, só para escrever em linguagem simples um resumo desses números (``ProvedorIA.analisar_padroes``).
Três fontes, nunca somadas entre si: relatos da comunidade, histórico de B.O. e pesquisa de percepção. Cada uma é analisada
pelas dimensões que de fato tem (região, período, tipo); o que falta ou é pouco para concluir vai em ``insuficiente``.

Regras de linguagem: os padrões descrevem o que *já foi registrado*. Nada aqui prevê ou afirma que uma ocorrência vai acontecer,
e relatos mostram concentração de relatos, não risco.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from backend.models.vocabulario import PERIODOS_POR_ID, TIPOS_POR_ID

# ---- limites mínimos: abaixo disso a fonte é dita "insuficiente" em vez de inventar padrão
MIN_RELATOS = 10          # relatos na janela para analisar qualquer coisa
MIN_RELATOS_PERIODO = 8   # relatos que informam o horário
MIN_RESPOSTAS = 20        # respostas da pesquisa
MIN_BO = 30               # registros de B.O. com posição
PRED_PCT, PRED_RAZAO, PRED_N = 40, 1.5, 5   # "predominante": >= 40%, 1,5x o segundo colocado e >= 5 casos
CRUZ_PCT, CRUZ_N, CRUZ_AREA_N = 60, 3, 4     # "naquela área, esse tipo/período": >= 60%, >= 3 casos, área com >= 4

HEX_RELATOS_M = 150  # mesmo valor de CONFIG.hexRelatosM no frontend
S3, MLAT = math.sqrt(3), 110574
NOTURNOS = ('18-20', '20-22', '22-00', 'madrugada')
AVISOS = [
    'Os padrões descrevem o que já foi registrado. Não indicam nem preveem que uma ocorrência vai acontecer.',
    'Relatos não são verificados um a um e mostram concentração de relatos, não risco. Relatos, B.O. e pesquisa são fontes '
    'diferentes e nunca são somados.',
]


def _conf(n: int) -> str:
    return 'alta' if n >= 30 else 'media' if n >= 10 else 'baixa'


def _pct(a: int, b: int) -> int:
    return round(100 * a / b) if b else 0


def _lista(nomes: list[str]) -> str:
    return nomes[0] if len(nomes) == 1 else ', '.join(nomes[:-1]) + ' e ' + nomes[-1]


# ------------------------------------------------------------------ grade hexagonal (porte de frontend/shared/grade.js)
class Grade:
    def __init__(self, hexa: dict[str, float]):
        self.lat0, self.lng0, self.R = hexa['lat0'], hexa['lng0'], hexa['R']
        self.mlng = 111320 * math.cos(math.radians(self.lat0))

    def _xy(self, cid: str) -> tuple[float, float]:
        fina = cid[0] == 'f'
        R = HEX_RELATOS_M if fina else self.R
        q, r = (int(v) for v in cid.lstrip('f').split('_'))
        return R * S3 * (q + r / 2), R * 1.5 * r

    def centro(self, cid: str) -> tuple[float, float]:
        x, y = self._xy(cid)
        return self.lat0 + y / MLAT, self.lng0 + x / self.mlng

    def celula(self, lat: float, lng: float) -> str:
        """Célula de ~1 km que contém o ponto."""
        x, y = (lng - self.lng0) * self.mlng, (lat - self.lat0) * MLAT
        q, r = (S3 / 3 * x - y / 3) / self.R, (2 / 3 * y) / self.R
        s = -q - r
        rq, rr, rs = (math.floor(v + 0.5) for v in (q, r, s))
        dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
        if dq > dr and dq > ds:
            rq = -rr - rs
        elif dr > ds:
            rr = -rq - rs
        return f'{rq or 0}_{rr or 0}'

    def grossa(self, cid: str) -> str:
        return cid if cid[0] != 'f' else self.celula(*self.centro(cid))


class Nomes:
    """Nome de cada área, como o mapa mostra (``areaName`` do frontend)."""

    def __init__(self, grade: Grade, bairros: list[Any], bo_celulas: dict[str, list[str]]):
        self.grade, self.bairros, self.bo = grade, bairros, bo_celulas
        self._cache: dict[str, str] = {}

    def __call__(self, cid: str) -> str:
        g = self.grade.grossa(cid)
        if g not in self._cache:
            if self.bo.get(g):
                self._cache[g] = self.bo[g][0] + ' e arredores'
            else:
                lat, lng = self.grade.centro(g)
                melhor, dist = None, 1e9
                for b in self.bairros:
                    d = math.hypot((b.lng - lng) * self.grade.mlng, (b.lat - lat) * MLAT)
                    if d < dist:
                        melhor, dist = b, d
                self._cache[g] = f'Perto de {melhor.nome}' if melhor is not None and dist < 1800 else 'Zona rural de Rio Claro'
        return self._cache[g]


# ------------------------------------------------------------------ utilidades de padrão
def _predominante(cont: Counter, base: int, minimo_n: int = PRED_N, minimo_pct: int = PRED_PCT):
    """(chave, n, %) do mais frequente se ele realmente se destaca; senão None."""
    if not cont or not base:
        return None
    (k, n), *resto = cont.most_common(2)
    if n < minimo_n or _pct(n, base) < minimo_pct or (resto and n < PRED_RAZAO * resto[0][1]):
        return None
    return k, n, _pct(n, base)


def _padrao(pid, fonte, dims, titulo, descricao, n, de, areas=None, extra=None):
    return {'id': pid, 'fonte': fonte, 'dimensoes': dims, 'titulo': titulo, 'descricao': descricao,
            'evidencia': {'n': n, 'de': de, 'pct': _pct(n, de)}, 'confianca': _conf(de), 'areas': areas or [], **(extra or {})}


def _rot_tipo(t: str) -> str:
    return TIPOS_POR_ID[t].label if t in TIPOS_POR_ID else t


def _rot_per(p: str) -> str:
    return PERIODOS_POR_ID[p].long if p in PERIODOS_POR_ID else p


def _concentracao(pid, fonte, cont: Counter, base: int, nome, unidade: str, titulo: str, de: str = 'dos', minimo_pct: int = PRED_PCT):
    """As 3 áreas mais citadas concentram boa parte do total?"""
    if len(cont) < 4:
        return None
    topo = cont.most_common(3)
    soma = sum(n for _, n in topo)
    if _pct(soma, base) < minimo_pct:
        return None
    nomes = []
    for c, _ in topo:
        n = nome(c)
        if n not in nomes:
            nomes.append(n)
    desc = f'{_lista(nomes)} reúnem {soma} {de} {base} {unidade} ({_pct(soma, base)}%), em {len(cont)} áreas com registros.'
    return _padrao(pid, fonte, ['regiao'], titulo, desc, soma, base, [c for c, _ in topo])


# ------------------------------------------------------------------ relatos da comunidade
def _relatos(relatos, grade: Grade, nome, janela_dias: int):
    padroes, insuf = [], []
    total = len(relatos)
    fonte = {'id': 'relatos', 'titulo': f'Relatos da comunidade (últimos {janela_dias} dias)', 'total': total, 'situacao': 'ok'}
    if total < MIN_RELATOS:
        fonte['situacao'] = 'insuficiente'
        motivo = f'Só há {total} relato{"" if total == 1 else "s"} nos últimos {janela_dias} dias; são necessários pelo menos {MIN_RELATOS} para procurar padrões.'
        insuf += [{'fonte': 'relatos', 'dimensao': d, 'motivo': motivo} for d in ('regiao', 'periodo', 'tipo')]
        return fonte, padroes, insuf
    por_area, por_tipo, por_per = Counter(), Counter(), Counter()
    area_tipo, area_per, tipo_per = {}, {}, {}
    for r in relatos:
        a = grade.grossa(r.cell)
        por_area[a] += 1
        for t in dict.fromkeys(r.tipos or []):
            por_tipo[t] += 1
            area_tipo.setdefault(a, Counter())[t] += 1
            if r.periodo:
                tipo_per.setdefault(t, Counter())[r.periodo] += 1
        if r.periodo:
            por_per[r.periodo] += 1
            area_per.setdefault(a, Counter())[r.periodo] += 1
    com_horario = sum(por_per.values())

    p = _concentracao('relatos-regiao', 'relatos', por_area, total, nome, 'relatos', 'Relatos concentrados em poucas áreas')
    if p:
        padroes.append(p)
    p = _predominante(por_tipo, total)
    if p:
        padroes.append(_padrao('relatos-tipo', 'relatos', ['tipo'], f'{_rot_tipo(p[0])} é o tipo mais relatado',
                               f'{p[1]} dos {total} relatos ({p[2]}%) são do tipo "{_rot_tipo(p[0])}".', p[1], total))
    if com_horario < MIN_RELATOS_PERIODO:
        insuf.append({'fonte': 'relatos', 'dimensao': 'periodo',
                      'motivo': f'Só {com_horario} relato{"" if com_horario == 1 else "s"} informa{"" if com_horario == 1 else "m"} o horário; são necessários pelo menos {MIN_RELATOS_PERIODO}.'})
    else:
        p = _predominante(por_per, com_horario)
        if p:
            padroes.append(_padrao('relatos-periodo', 'relatos', ['periodo'], f'Mais relatos em {_rot_per(p[0])}',
                                   f'{p[1]} dos {com_horario} relatos que informam o horário ({p[2]}%) são de {_rot_per(p[0])}.', p[1], com_horario))
        # tipo x período: um tipo concentrado num horário que se destaca do geral
        achados = []
        for t, c in tipo_per.items():
            n_t = sum(c.values())
            per, n, pc = (_predominante(c, n_t, 5, 50) or (None, 0, 0))
            if per and pc >= _pct(por_per[per], com_horario) + 15:
                achados.append((n, t, per, pc, n_t))
        for n, t, per, pc, n_t in sorted(achados, reverse=True)[:3]:
            padroes.append(_padrao(f'relatos-tipo-periodo-{t}', 'relatos', ['tipo', 'periodo'], f'{_rot_tipo(t)} aparece mais em {_rot_per(per)}',
                                   f'{n} dos {n_t} relatos de "{_rot_tipo(t)}" com horário ({pc}%) são de {_rot_per(per)}.', n, n_t))
    # região x tipo e região x período (áreas com relatos suficientes)
    for pid, dim, tabela, rot in (('relatos-area-tipo', 'tipo', area_tipo, _rot_tipo), ('relatos-area-periodo', 'periodo', area_per, _rot_per)):
        achados = []
        if dim == 'periodo' and com_horario < MIN_RELATOS_PERIODO:
            continue  # sem relatos suficientes com horário, não há padrão de período por área
        for a, c in tabela.items():
            base = por_area[a] if dim == 'tipo' else sum(c.values())
            if base < CRUZ_AREA_N:
                continue
            k, n, pc = (_predominante(c, base, CRUZ_N, CRUZ_PCT) or (None, 0, 0))
            if k:
                achados.append((n, a, k, pc, base))
        for n, a, k, pc, base in sorted(achados, reverse=True)[:3]:
            padroes.append(_padrao(f'{pid}-{a}', 'relatos', ['regiao', dim], f'{nome(a)}: {rot(k)}',
                                   f'Em {nome(a)}, {n} dos {base} relatos{" com horário" if dim == "periodo" else ""} ({pc}%) são de {rot(k)}.', n, base, [a]))
    return fonte, padroes, insuf


# ------------------------------------------------------------------ histórico de B.O.
def _historico(conj, grade: Grade, nome):
    padroes, insuf = [], []
    cells = {c.celula: c for c in conj.celulas}
    total = sum((c.n or 0) for c in cells.values())
    fonte = {'id': 'historico:' + conj.chave, 'titulo': f'Histórico de B.O. ({conj.periodo or conj.titulo})', 'total': total, 'situacao': 'ok'}
    if total < MIN_BO:
        fonte['situacao'] = 'insuficiente'
        insuf += [{'fonte': fonte['id'], 'dimensao': d, 'motivo': f'Só {total} registros com posição; são necessários pelo menos {MIN_BO}.'} for d in ('regiao', 'tipo')]
    else:
        por_area = Counter({k: (c.n or 0) for k, c in cells.items() if c.n})
        p = _concentracao('historico-regiao', fonte['id'], por_area, total, nome, 'registros de B.O.', 'B.O. concentrados em poucas áreas')
        if p:
            padroes.append(p)
        cat = Counter({k: sum((c.dados.get(k) or 0) for c in cells.values()) for k in ('vd', 'fe', 'te')})
        rot = {'vd': 'violência doméstica', 'fe': 'feminicídio', 'te': 'tentativa de feminicídio'}
        p = _predominante(cat, sum(cat.values()), PRED_N, PRED_PCT)
        if p:
            outros = [f'{cat[k]} de {rot[k]}' for k in ('fe', 'te') if cat[k]]
            padroes.append(_padrao('historico-tipo', fonte['id'], ['tipo'], f'Predomínio de {rot[p[0]]} nos registros',
                                   f'{p[1]} dos {sum(cat.values())} registros com posição ({p[2]}%) são de {rot[p[0]]}.'
                                   + (f' Também constam {_lista(outros)}.' if outros else ''), p[1], sum(cat.values())))
        graves = sorted(((((c.dados.get('fe') or 0) + (c.dados.get('te') or 0)), k) for k, c in cells.items() if (c.dados.get('fe') or 0) + (c.dados.get('te') or 0)), reverse=True)
        if graves:
            n = sum(g for g, _ in graves)
            padroes.append(_padrao('historico-area-grave', fonte['id'], ['regiao', 'tipo'], 'Onde constam feminicídio e tentativa',
                                   f'{n} registro{"" if n == 1 else "s"} de feminicídio ou tentativa em {len(graves)} área{"" if len(graves) == 1 else "s"} '
                                   f'(entre elas {_lista([nome(k) for _, k in graves[:3]])}). Poucos casos: leia com cautela.', n, sum(cat.values()), [k for _, k in graves[:3]]))
    insuf.append({'fonte': fonte['id'], 'dimensao': 'periodo',
                  'motivo': f'Os registros de B.O. carregados trazem só o período geral ({conj.periodo or "sem data"}), sem dia nem horário por local: não dá para ver padrão de horário.'})
    return fonte, padroes, insuf, por_area if total >= MIN_BO else Counter()


# ------------------------------------------------------------------ pesquisa de percepção
def _percepcao(conj, nome):
    padroes, insuf = [], []
    cells = {c.celula: c for c in conj.celulas}
    resp = conj.respostas or 0
    fonte = {'id': 'percepcao:' + conj.chave, 'titulo': conj.titulo, 'total': resp, 'situacao': 'ok'}
    if resp < MIN_RESPOSTAS:
        fonte['situacao'] = 'insuficiente'
        insuf += [{'fonte': fonte['id'], 'dimensao': d, 'motivo': f'Só {resp} respostas; são necessárias pelo menos {MIN_RESPOSTAS}.'} for d in ('regiao', 'periodo', 'tipo')]
        return fonte, padroes, insuf, Counter()
    mencoes = Counter({k: (c.n or 0) for k, c in cells.items() if c.n})
    base = sum(mencoes.values())
    p = _concentracao('percepcao-regiao', fonte['id'], mencoes, base, nome, 'menções de áreas', 'Áreas mais citadas na pesquisa', 'das')
    if p:
        p['descricao'] += f' (A pesquisa teve {resp} respostas; cada mulher pôde citar mais de uma área.)'
        padroes.append(p)
    horas = Counter()
    por_area_h: dict[str, Counter] = {}
    for k, c in cells.items():
        for h, v in (c.dados.get('h') or {}).items():
            if h in NOTURNOS or h == 'dia':
                horas[h] += v
                por_area_h.setdefault(k, Counter())[h] += v
    marcas = sum(horas.values())
    if marcas >= MIN_RESPOSTAS:
        noite = sum(horas[h] for h in NOTURNOS)
        if _pct(noite, marcas) >= 60:
            padroes.append(_padrao('percepcao-periodo', fonte['id'], ['periodo'], 'A insegurança é mais citada à noite e de madrugada',
                                   f'{noite} das {marcas} marcações de horário ({_pct(noite, marcas)}%) são entre 18h e 6h.', noite, marcas))
        achados = []
        for k, c in por_area_h.items():
            b = sum(c.values())
            n_noite = sum(c[h] for h in NOTURNOS)
            if b >= 5 and _pct(n_noite, b) >= 80:
                achados.append((b, k, n_noite))
        for b, k, n_noite in sorted(achados, reverse=True)[:2]:
            padroes.append(_padrao(f'percepcao-area-periodo-{k}', fonte['id'], ['regiao', 'periodo'], f'{nome(k)}: citada sobretudo à noite',
                                   f'Em {nome(k)}, {n_noite} das {b} marcações de horário ({_pct(n_noite, b)}%) são entre 18h e 6h.', n_noite, b, [k]))
    else:
        insuf.append({'fonte': fonte['id'], 'dimensao': 'periodo', 'motivo': f'Só {marcas} marcações de horário; são necessárias pelo menos {MIN_RESPOSTAS}.'})
    sit = (conj.dados.get('stats') or {}).get('situacao') or {}
    itens = Counter({i[0]: i[1] for i in (sit.get('i') or []) if isinstance(i, list) and len(i) == 2})
    p = _predominante(itens, resp, PRED_N, PRED_PCT)
    if p:
        padroes.append(_padrao('percepcao-tipo', fonte['id'], ['tipo'], f'Situação mais vivida: {p[0].lower()}',
                               f'{p[1]} das {resp} respondentes ({p[2]}%) marcaram "{p[0]}".', p[1], resp))
    return fonte, padroes, insuf, mencoes


# ------------------------------------------------------------------ juntando tudo
def analisar(relatos, oficiais, percepcoes, geo_hex: dict, bairros: list, janela_dias: int) -> dict:
    """Resultado completo: fontes, padrões, o que não deu para analisar e os avisos fixos."""
    grade = Grade(geo_hex)
    bo = {}
    for conj in oficiais:
        for c in conj.celulas:
            if c.dados.get('b'):
                bo[c.celula] = [b[0] for b in c.dados['b'] if isinstance(b, list) and b]
    nome = Nomes(grade, bairros, bo)
    fontes, padroes, insuf, topos = [], [], [], {}

    f, p, i = _relatos(relatos, grade, nome, janela_dias)
    fontes.append(f); padroes += p; insuf += i
    if f['situacao'] == 'ok':
        topos['relatos'] = Counter(grade.grossa(r.cell) for r in relatos)
    for conj in oficiais:
        f, p, i, top = _historico(conj, grade, nome)
        fontes.append(f); padroes += p; insuf += i
        if top:
            topos['historico'] = top
    for conj in percepcoes:
        f, p, i, top = _percepcao(conj, nome)
        fontes.append(f); padroes += p; insuf += i
        if top:
            topos['percepcao'] = top

    # coincidência entre fontes: a mesma área entre as 5 mais citadas em duas ou mais fontes
    if len(topos) >= 2:
        cinco = {k: {a for a, _ in c.most_common(5)} for k, c in topos.items()}
        contagem = Counter(a for s in cinco.values() for a in s)
        comuns = [a for a, n in contagem.most_common() if n >= 2][:4]
        if comuns:
            rot = {'relatos': 'relatos', 'historico': 'B.O.', 'percepcao': 'pesquisa'}
            for a in comuns:
                onde = [rot[k] for k, s in cinco.items() if a in s]
                padroes.append(_padrao(f'cruzada-{a}', 'cruzada', ['regiao'], f'{nome(a)} aparece em mais de uma fonte',
                                       f'{nome(a)} está entre as 5 áreas mais citadas em: {_lista(onde).rstrip(".")}. As fontes medem coisas diferentes: '
                                       'isso é uma coincidência de onde os dados se concentram, não uma prova de risco.', len(onde), len(topos), [a]))
    return {'janela_dias': janela_dias, 'fontes': fontes, 'padroes': padroes, 'insuficiente': insuf, 'avisos': AVISOS}


# ------------------------------------------------------------------ texto do resumo
def narrativa_padrao(res: dict) -> str:
    """Resumo escrito por regras (usado sem IA e quando o modelo falha na checagem)."""
    padroes = sorted(res['padroes'], key=lambda p: ({'alta': 0, 'media': 1, 'baixa': 2}[p['confianca']], -p['evidencia']['n']))
    partes = []
    if padroes:
        partes.append('Nos dados disponíveis, os principais padrões são: ' + ' '.join(p['descricao'] for p in padroes[:3]))
    else:
        partes.append('Os dados disponíveis ainda não mostram nenhum padrão que se destaque.')
    if res['insuficiente']:
        n = len(res['insuficiente'])
        partes.append(f'Em {n} {"caso" if n == 1 else "casos"} não há dados suficientes para concluir (veja a lista abaixo).')
    partes.append('Isso descreve o que já foi registrado, não prevê o que vai acontecer.')
    return ' '.join(partes)


# palavras que prometem futuro ou certeza: o resumo da IA é recusado se tiver alguma
PROIBIDAS = re.compile(r'\b(vai|vão|irá|irão|ir[aá] (?:acontecer|ocorrer)|acontecer[aá]|ocorrer[aá]|haver[aá]|certamente|com certeza|sempre (?:vai|ser[aá])|inevit[aá]vel|prev[eê]|previs[aã]o|garant)', re.I)


def numeros(texto: str) -> set[str]:
    return set(re.findall(r'\d+(?:[.,]\d+)?', texto))


# vocabulário que só existe em uma fonte: o modelo pequeno confunde ("relatos de violência doméstica") e a frase é recusada
SO_BO = re.compile(r'viol[êe]ncia dom[ée]stica|feminic[ií]dio', re.I)
SO_RELATOS = re.compile('|'.join(re.escape(t.label.lower()) for t in TIPOS_POR_ID.values() if t.id != 'outra'), re.I)
CITA_BO = re.compile(r'b\.?o\.?\b|boletim|registros? de', re.I)
CITA_RELATO = re.compile(r'relat', re.I)


def _mistura_fontes(texto: str) -> bool:
    for frase in re.split(r'(?<=[.!?])\s+|\n+', texto):
        if SO_BO.search(frase) and CITA_RELATO.search(frase) and not CITA_BO.search(frase):
            return True
        if SO_RELATOS.search(frase) and CITA_BO.search(frase) and not CITA_RELATO.search(frase):
            return True
    return False


def resumo_valido(texto: str, res: dict) -> bool:
    """O resumo escrito por modelo só vale se não promete futuro, só usa números que estão nos achados e não troca uma fonte por outra."""
    if not texto or len(texto) > 900 or PROIBIDAS.search(texto) or _mistura_fontes(texto) or re.search(r'boletins? oficia', texto, re.I):
        return False
    permitidos = set()
    for p in res['padroes']:
        permitidos |= numeros(p['descricao']) | {str(p['evidencia']['n']), str(p['evidencia']['de']), str(p['evidencia']['pct'])}
    for i in res['insuficiente']:
        permitidos |= numeros(i['motivo'])
    for f in res['fontes']:
        permitidos |= {str(f['total'])} | numeros(f['titulo'])  # o título traz o período (ex.: jan/2025 a abr/2026)
    permitidos |= {str(len(res['insuficiente'])), str(res['janela_dias'])}
    return numeros(texto) <= permitidos
