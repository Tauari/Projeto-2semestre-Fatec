"""Corpus dos testes diferenciais (Python x src/app.js no Node).

``CASOS_MANUAIS``: frases escritas à mão, em português, cobrindo cada regra do legado.
``gerar_corpus``: milhares de frases determinísticas, combinando fragmentos e ruído.
"""
from __future__ import annotations

import random
import unicodedata

from backend.tests.paridade.oraculo import dados_brutos

ESPACOS_UNICODE = ['\N{NO-BREAK SPACE}', '\N{EN SPACE}', '\N{EM SPACE}', '\N{THIN SPACE}', '\N{HAIR SPACE}', '\N{NARROW NO-BREAK SPACE}', '\N{MEDIUM MATHEMATICAL SPACE}', '\N{IDEOGRAPHIC SPACE}', '\N{ZERO WIDTH NO-BREAK SPACE}',
                   '\N{OGHAM SPACE MARK}', '\N{LINE SEPARATOR}', '\N{PARAGRAPH SEPARATOR}', '\t', '\n', '\r\n', '\x0b', '\x0c', '\x85', '\N{MONGOLIAN VOWEL SEPARATOR}', '\N{ZERO WIDTH SPACE}',
                   '\x1c', '\x1f', '\N{EN QUAD}', '\N{EM QUAD}', '\N{FIGURE SPACE}', '\N{PUNCTUATION SPACE}']
EMOJIS = ['😡', '🚗', '👩🏽', '🏳\N{VARIATION SELECTOR-16}\N{ZERO WIDTH JOINER}🌈', '𝐀', '🇧🇷', '🙏', '😱', '💔', '🆘', '𠀀', '\U0010ffff']

TELEFONES = ['+55 (19) 99876-5432', '+55 19 99876-5432', '+5519998765432', '55 19 99876 5432', '(19) 99876-5432',
             '(19)99876-5432', '19 99876-5432', '1999876-5432', '19998765432', '99876-5432', '9876-5432', '3534-1234',
             '(19) 3534-1234', '19 3534.1234', '998765432', '99876 5432', '+55(19)3524-0000', '0800 770 1234', '190',
             '180', '(019) 99876-5432', '+55\N{NO-BREAK SPACE}19\N{NO-BREAK SPACE}99876-5432', '19\N{THIN SPACE}99876\N{THIN SPACE}5432', '+1 (415) 555-0100',
             '11 91234 5678', '(11)91234.5678', '5519 9 9876-5432', '99876-54321', '099876-5432', '9 9876-5432']
DOCUMENTOS = ['123.456.789-09', '12345678909', '123.456.789-0', '000.000.000-00', 'CPF 987.654.321-00.']
EMAILS = ['maria.silva@gmail.com', 'fulano+teste@empresa.com.br', 'a_b-c@x-y.z', 'contato@aurora', 'joão@exemplo.com',
          'EMAIL@DOMINIO.COM.BR.', 'x@y.co', 'ana@@b.com', 'user@sub.dominio-x.org', '@gmail.com', 'nome.sobrenome@hotmail.com']
PLACAS = ['ABC-1234', 'ABC1234', 'abc1d23', 'BRA2E19', 'BRA-2E19', 'placa FJK 3344', 'XYZ12345', 'placa FJK-3D44',
          'Placa: EIY-7J20', 'ab1234', 'ABCD1234', 'Ábc1234']
PERFIS = ['@fulano_123', '@maria.silva', 'insta @ab', 'me segue no @joao.pedro.', 'email@handle', ' @xyz', '@a.b',
          'perfil@abc', '(@abcd)', '\N{NO-BREAK SPACE}@nbsp_user', '\N{IDEOGRAPHIC SPACE}@ideografico']
ENDERECOS = ['casa 12', 'Casa 12', 'CASA 12', 'apto 301', 'Apto. 301', 'APTO 301', 'apartamento 45', 'APARTAMENTO 45',
             'ap. 12', 'ap 12', 'nº 45', 'n° 45', 'no 45', 'Nº45', 'N° 45', 'nº. 45', 'n.º 45', 'número 1234', 'numero 123456',
             'NÚMERO 7', 'Número 7', 'nro 5', 'casa12', 'casa 123456', 'na casa 3 da rua', 'número\N{NO-BREAK SPACE}99', 'nümero 5',
             'caſa 12', 'apto\N{HAIR SPACE}44', 'Nº 1', 'nº 2']
NOMES = ['chamado João', 'chamada Maria Clara', 'se chama Pedro Henrique', 'nome dele é Carlos', 'o nome é Ana',
         'nome e José', 'nome dela Bruna', 'conhecido como Zé Pequeno', 'conhecida como Índia', 'apelido de Baixinho',
         'apelidado Tico', 'chamado ÉRICO', 'chamado joão', 'chamado  Ana', 'chamado\N{NO-BREAK SPACE}Ana', 'Chamado Ana',
         'chamado Ölaf', 'chamado Ÿves', 'chamado ×x', 'um cara chamado Joaquim Barbosa Silva', 'apelida de Tuca',
         'se chama\tRita', 'conhecido como DJ', 'apelido Lobo', 'chamado Jose\N{COMBINING ACUTE ACCENT}', 'chamado Ana\N{EM SPACE}Paula',
         'chamada Ñusta', 'se chama Þór', 'chamado O', 'chamado Ab', 'chamado 1Ana', 'nome é Ângela Íris']

BAIRROS_FRASES = ['perto da Unesp', 'UNESP', 'na unesp.', 'unespiano', 'Lago Azul', 'lago  azul', 'rodoviária',
                  'RODOVIÁRIA velha', 'estação', 'na estacao de trem', 'Jardim Público', 'jardim publico', 'centro',
                  'no Centro,', 'centrinho', 'zona central', 'Zona Central', 'centro-oeste', 'no Bela Vista', 'Vila Bela Vista',
                  'Jardim Bela Vista', 'bela vista', 'Cidade Nova', 'cidade nova', 'CHÁCARA LUSA', 'chacara lusa', 'Chácara Lusa',
                  'Jardim Claret', 'Cidade Claret', 'claret', 'JARDIM CLARET', 'Santana', 'Alto do Santana', 'alto do santana',
                  'vila operaria', 'VILA OPERÁRIA', 'são miguel', 'Vila São Miguel', 'SAO MIGUEL', 'BNH', 'no bnh', 'Ajapi',
                  'ajapi.', 'Wenzel', 'Novo Wenzel', 'Jardim Wenzel', 'Novo Jardim Wenzel', 'Terra Nova', 'terra-nova',
                  'Parque Mãe Preta', 'mae preta', 'Arco Íris', 'Conjunto Habitacional Arco Íris', 'Recreio das Águas Claras',
                  'aguas claras', 'Batovi', 'Jardim Progresso II', 'jardim progresso', 'progresso ii', 'São José',
                  'Vila São José', 'sao jose', 'Assistência', 'Bairro da Saúde', 'saude', 'Jardim do Horto', 'horto',
                  'Vila do Horto', 'Santa Cruz', 'santa cruzeiro', 'jardim', 'vila', 'parque', 'Rio Claro', 'jardim rio claro',
                  'Jardim Donângela', 'donangela', 'Jardim Itapuã', 'itapua', 'Consolação', 'consolacao', 'Cervezão',
                  'cervezao', 'Jardim Vilage', 'vilage', 'Vila Alemã', 'alema', 'Jardim Portugal', 'portugal']

QUANDO_FRASES = ['ontem', 'hoje', 'agora há pouco', 'agorinha', 'agora pouco', 'anteontem', 'segunda', 'terça-feira',
                 'quarta', 'quinta', 'sexta à noite', 'sábado', 'domingo', 'semana passada', 'mês passado', 'há 3 semanas',
                 'ha 10 semanas', 'faz tempo', 'ano passado', 'nesta semana', 'essa semana', 'esta semana', 'meses atrás',
                 'ONTEM', 'Hoje', 'hojemente', 'ontemzinho', 'segundaria', 'há semanas', 'mes passado']
HORA_FRASES = ['22h', '22 h', '22hs', '22 horas', '10 da noite', '10 da manhã', '3 da tarde', 'às 7:30', 'as 19:45',
               'meia-noite', 'meia noite', 'meianoite', 'de madrugada', 'de manhã', 'pela manhã', 'à tarde', 'de tarde',
               'à noite', '0h', '24h', '12h', '23:59', '25h', '99h', 'umas 8 da noite', '8h da noite', '1h da manhã',
               '12 da noite', '11 da noite', '6h', '5h59', '18h30', '20h', '21 h', '7\N{NO-BREAK SPACE}horas', '9h\N{NARROW NO-BREAK SPACE}da noite',
               '123h', 'h 22', '1:00', '00:30', '11:15 da noite', 'tardezinha', 'manhãzinha', 'noite', 'às 13h',
               '19 h e pouco', '2 horas atrás', 'uns 4hs', '10:5', '10: 50', '٣h', '３h']
SITUACOES = ['um cara mexeu comigo', 'me seguiu até em casa', 'dois homens me seguiram', 'fiquei com medo', 'me assediou',
             'buzinou pra mim', 'me encarou o tempo todo', 'tentou me agarrar', 'roubaram meu celular', 'assalto',
             'um carro parou do meu lado', 'motorista do uber', 'motorista do 99', 'um cara de moto', 'rua escura',
             'sem luz nenhuma', 'rua deserta', 'falou besteira', 'falou gracinha', 'se masturbando no ponto', 'um homem pelado',
             'mostrou o pênis', 'me empurrou', 'levou um soco', 'me deu um tapa', 'agrediu', 'violência física',
             'puxou conversa e insistiu', 'chegou em mim', 'tentou falar comigo', 'tentou pegar meu braço', 'me medindo',
             'ficou olhando', 'observando de longe', 'me intimidou', 'furtaram a bolsa', 'puxaram minha bolsa', 'levaram tudo',
             'van branca', 'caminhão parado', 'veículo suspeito', 'iluminação ruim', 'poste apagado', 'praça vazia',
             'rua vazio', 'cantada', 'obscenidade', 'exposição', 'perseguição', 'atrás de mim', 'me acompanhou',
             'abordagem', 'carroça', 'motoqueiro', 'uberlândia', 'o 99 atrasou', 'mexeu comigo e me seguiu e roubou e bateu']
URGENCIAS = ['estou sendo seguida', 'to em perigo', 'estamos com medo agora', 'socorro', 'SOCORRO!!!', 'me ajuda agora',
             'me ajudem agora', 'agora mesmo', 'estou em perigo', 'tô sendo seguida', 'to sendo seguido', 'socorrooo',
             'me ajude agora']
ABERTURAS = ['Oi,', 'Olá', 'Então,', 'Queria contar que', 'Aconteceu', 'Gente,', 'Aurora, preciso registrar:', '',
             'Bom dia.', 'boa noite', 'Ei', 'Relato:']
CONECTORES = [' ', ', ', '. ', ' e ', ' - ', '; ', '! ', '... ', '\n', '  ', ' (', ') ', ': ']

CASOS_MANUAIS = [
    '',
    ' ',
    'oi',
    'Ontem às 22h um cara me seguiu perto da Unesp.',
    'me liga +55 (19) 99876-5432 ou maria@x.com, chamado João Silva casa 12',
    'Hoje de manhã, na rodoviária, um motorista do uber ficou me encarando.',
    'Um homem chamado Carlos me seguiu até a estação, meu número é (19) 3534-1234.',
    'estou sendo seguida agora na Avenida 1, socorro',
    'Semana passada, 10 da noite, um carro com placa ABC-1234 parou do meu lado no Jardim Claret',
    'Mercosul: BRA2E19 e antiga ABC1234 e minúscula abc1d23',
    'CPF 123.456.789-09 e telefone 99876-5432',
    'meu insta é @maria.silva e o dele @fulano_123',
    'Moro no apto 301, casa 12, nº 45, apartamento 45, ap. 12, número 1234',
    'o nome dele é Pedro e ele se chama Pedro Henrique Souza',
    'conhecido como Zé Pequeno, apelido de Baixinho, conhecida como Índia',
    'aconteceu no LAGO AZUL, perto da ESTAÇÃO',
    'CHÁCARA LUSA, JARDIM CENTENÁRIO, VILA OPERÁRIA',
    'foi à meia-noite na praça do Jardim Público',
    'às 7:30 da manhã, na Cidade Nova',
    'sábado de madrugada, rua escura e deserta',
    'anteontem à tarde uns caras mexeram comigo',
    'mês passado fui assaltada no centro',
    'há 3 semanas, 3 da tarde, na zona central',
    'agora há pouco, 12h, na Vila São Miguel',
    'faz tempo, uns 8 da noite, perto do Terra Nova',
    'hoje 0h no BNH',
    'hoje 24h no Batovi',
    'ontem 25h no Ajapi',
    'domingo 12 da noite',
    'segunda 11:59 da noite',
    'quinta 1h da manhã',
    'agorinha às 19:45 no Jardim Bela Vista e na Vila Bela Vista',
    'Unesp e Centro e Bela Vista',
    'centro e unesp',
    'perto da unespinha',
    'fui na estacao e depois no lago azul',
    'jardim publico',
    'rodoviaria nova',
    'no bairro Alto do Santana, perto do Santana',
    'Jardim Progresso II ou Jardim Progresso',
    'Novo Jardim Wenzel, Jardim Wenzel, Novo Wenzel, Wenzel',
    'Parque Mãe Preta\N{NO-BREAK SPACE}e\N{NO-BREAK SPACE}Vila Indaiá',
    'Recreio das Águas Claras',
    'Conjunto Habitacional Arco Íris',
    'Loteamento Sebastião dos Santos Lima',
    'Residencial Benjamim de Castro',
    'Jose\N{COMBINING ACUTE ACCENT} me seguiu no Jardim Centena\N{COMBINING ACUTE ACCENT}rio',
    'CHA\N{COMBINING ACUTE ACCENT}CARA LUSA',
    '\N{NO-BREAK SPACE}\N{NO-BREAK SPACE}chamado João\N{NO-BREAK SPACE}\N{NO-BREAK SPACE}',
    '\N{ZERO WIDTH NO-BREAK SPACE}chamado João\N{ZERO WIDTH NO-BREAK SPACE}',
    '  espaços   demais   aqui  ',
    '\N{EM SPACE}\N{EM SPACE}casa 12\N{EM SPACE}\N{EM SPACE}',
    'linha1\nlinha2\r\nlinha3\N{LINE SEPARATOR}linha4\N{PARAGRAPH SEPARATOR}fim',
    'tab\taqui\t\tali',
    '\x85chamado Ana\x85',
    '\N{MONGOLIAN VOWEL SEPARATOR}chamado Ana\N{MONGOLIAN VOWEL SEPARATOR}',
    '\N{ZERO WIDTH SPACE}@perfil_oculto\N{ZERO WIDTH SPACE}',
    '\x1c casa 12 \x1f',
    'SOCORRO!!! tô sendo seguida na rua deserta 😱',
    'me ajudem agora, estamos com medo agora',
    'agora mesmo um cara tentou me agarrar',
    '😡😡 me seguiu 🚗 moto 🏳\N{VARIATION SELECTOR-16}\N{ZERO WIDTH JOINER}🌈 🇧🇷',
    'Emoji no meio do número 9987😱6-5432',
    'ΣΑΣ ΟΔΟΣ ΜΑΣ',
    'İstanbul ẞ ǅ ﬁm',
    'Ａｖｅｎｉｄａ ３ (largura total)',
    '١٢٣ ٤٥٦ números árabes',
    'o 99 atrasou e o motorista do 99 me assediou',
    'uber e UBER e Uber',
    'uma van, um caminhão, um veículo',
    'carroça e motocicleta',
    'ele falou coisa e falou besteira e falou gracinha',
    'mostrou as partes, mostrou o orgão',
    'se masturbou, nudez, pelado',
    'puxaram meu celular, puxaram minha bolsa',
    'violencia fisica, me pegou pelo braço',
    'atras de mim o tempo todo, me acompanhou',
    'tentou conversar, tentou falar, tentou pegar',
    'me medindo de cima a baixo',
    'iluminação péssima, poste apagado, rua vazia, praça vazio',
    'e-mail: MARIA_SOUZA-2@EMPRESA.COM.BR',
    'mande para a.b@c.d.e.f',
    'test@test',
    'x@y.z@w.com',
    'fone: 19 99876 5432 / 19 3524-1234 / 3524 1234',
    '+55 19 3524-1234',
    '+5519 99876-5432',
    '55 (19) 99876-5432',
    'telefone 999999999999999',
    'meu número é 9876-54321',
    'sem telefone: 1234',
    'data 12/05/2024 e hora 22:30',
    'placa ABC 1234',
    'placa AB-1234',
    'placa ABCD-1234',
    'placa abc-1d23x',
    'nº 45 e Nº 46 e n° 47 e no 48 e NO 49',
    'fui no 12 e voltei',
    'casa 1, casa 12345, casa 123456',
    'NÚMERO 7 e Número 8 e número 9 e numero 10',
    'apto. 301 e ap.302 e ap. 303',
    'a casa 12h',
    'chamado João chamado Maria',
    'se chama maria (minúscula)',
    'nome é Ana, nome e Bia, nome dele Caio, nome dela Duda',
    'apelido de Tuca e apelida de Juca',
    'chamada Ana Maria Clara Souza',
    'chamado Óscar Ñandu',
    'chamado ÀÉÎÕÜ Ýzz',
    'o conhecido como RATO',
    'chamadoJoão',
    'chamado\N{EM SPACE}Pedro\N{EM SPACE}Álvares',
    'chamado Pedro\nÁlvares',
    '@abc no começo',
    'fim com @abc',
    'e-mail no fim: ana@b.co',
    'a' * 298 + '😡' + ' resto',
    'a' * 299 + '😡' + ' resto',
    'a' * 300 + '😡' + ' resto',
    'b' * 297 + ' 🏳\N{VARIATION SELECTOR-16}\N{ZERO WIDTH JOINER}🌈 fim',
    'casa 12 ' + 'c' * 292 + '👩🏽',
    'me liga 99876-5432 ' + 'd' * 285 + '🇧🇷🇧🇷',
    'x' * 1498 + '😡😡 cauda',
    'y' * 1499 + '😡 cauda',
    '"""aspas triplas""" no texto',
    '""""" cinco aspas',
    'Mensagem com "aspas" e \'apóstrofo\' e \\ barra',
    'Unesp' * 5,
    'lago azul lago azul',
    'meianoite',
    'meia noite e meia',
    'à noite, umas 9h',
    '9h da noite',
    '9 da tarde',
    '11 da manhã',
    'às 10: 30',
    'às 10 :30',
    '10hs da noite',
    '10 horas da noite',
    'as 7 e meia da manhã',
    'de manha cedo',
    'pela manha',
    'manha',
    'amanhã',
    'tarde demais',
    'a tarde',
    'hoje à tarde, ontem de manhã',
    'ontem, semana passada, hoje',
    'nesta semana na terça',
    'anteontem',
    'meses',
    'há 2 semanas',
    'ha  2 semanas',
    'segunda-feira passada',
    'sexta',
    'sextou',
    'sabado a noite',
    'Aconteceu no Jardim Novo? Ou no Jardim Nova?',
    'Vila Nova, Cidade Nova',
    'Santa Maria e Santa Cruz',
    'Parque Universitário perto da Unesp',
    'Distrito Industrial / Vila Industrial / Parque das Indústrias',
    'Bairro do Estádio',
    'Jardim do Trevo',
    'Jardim Maria Cristina e Vila Cristina',
    'Jardim Dona Regina Picelli',
    'Residencial dos Bosques',
    'Parque dos Eucaliptos',
    'Chácara Boa Vista e Boa Esperança',
    'Bairro Olímpico',
    'Residencial Florença',
    'Jardim América',
    'Residencial Gracioli',
    'Jardim Conduta',
    'rioclaro',
    'CENTRO',
    'Centro.',
    '(centro)',
    'centro2',
    '_centro_',
    'centro_',
    'epicentro',
    'bnh',
    'São Caetano do Sul',
    'Jardim São Paulo e Vila Paulista e Jardim Paulista',
]


def nomes_bairros() -> list[str]:
    return [b[0] for b in dados_brutos()['bairros']]


def _sem_acento(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))


def _variar(rnd: random.Random, s: str) -> str:
    op = rnd.randrange(12)
    if op == 0:
        return s.upper()
    if op == 1:
        return s.lower()
    if op == 2:
        return _sem_acento(s)
    if op == 3:
        return unicodedata.normalize('NFD', s)
    if op == 4:
        return s.title()
    if op == 5 and s:
        i = rnd.randrange(len(s) + 1)
        return s[:i] + rnd.choice(ESPACOS_UNICODE) + s[i:]
    if op == 6 and s:
        i = rnd.randrange(len(s) + 1)
        return s[:i] + rnd.choice(EMOJIS) + s[i:]
    if op == 7:
        return s.replace(' ', rnd.choice(ESPACOS_UNICODE))
    return s


ALFABETO_RUIDO = ('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' * 2 + ' ' * 20
                  + '@.-+()_/:;,!?"#ºª°' + 'áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇñÑ×÷ÿŸſıİK' + ''.join(ESPACOS_UNICODE) + ''.join(EMOJIS))


def _ruido(rnd: random.Random) -> str:
    return ''.join(rnd.choice(ALFABETO_RUIDO) for _ in range(rnd.randrange(1, 60)))


def gerar_corpus(qtd: int = 4000, semente: int = 20260930) -> list[str]:
    rnd = random.Random(semente)
    bairros = nomes_bairros()
    grupos = [SITUACOES, BAIRROS_FRASES, bairros, QUANDO_FRASES, HORA_FRASES, TELEFONES, DOCUMENTOS, EMAILS, PLACAS,
              PERFIS, ENDERECOS, NOMES, URGENCIAS, EMOJIS]
    saida = []
    for i in range(qtd):
        tipo = i % 10
        if tipo == 0:
            s = _ruido(rnd)
        elif tipo == 1:
            # fragmentos de dados pessoais colados em ruído
            s = _ruido(rnd) + rnd.choice(CONECTORES) + rnd.choice(TELEFONES + DOCUMENTOS + EMAILS + PLACAS + PERFIS + ENDERECOS + NOMES) + rnd.choice(CONECTORES) + _ruido(rnd)
        else:
            partes = [rnd.choice(ABERTURAS)]
            for g in rnd.sample(grupos, rnd.randrange(2, 7)):
                partes.append(_variar(rnd, rnd.choice(g)))
            if rnd.random() < 0.3:
                rnd.shuffle(partes)
            s = ''
            for p in partes:
                s += p + rnd.choice(CONECTORES)
            if rnd.random() < 0.15:
                s = _variar(rnd, s)
        if i % 97 == 0:
            s = (s + ' ') * (300 // max(len(s), 1) + 1) + rnd.choice(EMOJIS)  # passa do corte de 300
        saida.append(s)
    return saida


def textos_longos(semente: int = 7) -> list[str]:
    """Textos perto do corte de 1500 unidades (provedor e prompt)."""
    rnd = random.Random(semente)
    saida = []
    for alvo in (1495, 1498, 1499, 1500, 1501, 1502, 1600, 3000):
        base = ' '.join(rnd.choice(SITUACOES + BAIRROS_FRASES + HORA_FRASES + TELEFONES) for _ in range(400))
        s = base[:alvo - 1] + rnd.choice(EMOJIS) + ' fim chamado João casa 12 socorro'
        saida.append(s)
        saida.append('z' * (alvo - 1) + '😡' + '"""' * 3)
        saida.append('"' * alvo)
    return saida


def objetos_saida_ia(qtd: int = 1500, semente: int = 99) -> list:
    """Saídas de modelo (JSON) para ``validar_saida_extracao``, sem os casos de desvio documentados."""
    rnd = random.Random(semente)
    bairros = nomes_bairros()
    tipos_ids = ['assedio', 'perseguicao', 'abordagem', 'intimidacao', 'exposicao', 'roubo', 'violencia', 'veiculo',
                 'ambiente', 'outra']
    valores_soltos = [None, True, False, 0, 1, -1, 0.5, 1e21, 1e-7, 123.0, -0.0, 1e16, 12345678901234567890, 'x', '', [], {},
                      ['a', None, ['b', 1]], {'a': 1}, 3.14159, 2 ** 53 + 1, 1.5e300, 0.1 + 0.2, 100, 1e-6]

    def talvez(d, chave, valor):
        if rnd.random() < 0.85:
            d[chave] = valor

    saida: list = [None, True, 0, 'texto', 3.5, [], [1, 2], {}, {'urgente': True}]
    for _ in range(qtd):
        o: dict = {}
        talvez(o, 'urgente', rnd.choice([True, False, 'true', 1, None, 0]))
        talvez(o, 'tipos', rnd.choice([
            rnd.sample(tipos_ids, rnd.randrange(0, 6)),
            rnd.sample(tipos_ids, 3) + ['xyz', 5, None],
            [rnd.choice(tipos_ids), [rnd.choice(tipos_ids)], ['assedio', 'roubo'], True, 1.0],
            'assedio', None, 7, {'0': 'assedio'},
        ]))
        talvez(o, 'bairro', rnd.choice([rnd.choice(bairros), _variar(rnd, rnd.choice(bairros)), rnd.choice(BAIRROS_FRASES),
                                        '', '   ', '\N{NO-BREAK SPACE}', 'Lugar Nenhum', 'jard', 'a', None, 12, ['Centro'], _ruido(rnd)]))
        talvez(o, 'quando', rnd.choice(['hoje', 'ontem', 'semana', 'antes', 'HOJE', 'amanhã', '', None, 5, True]))
        talvez(o, 'periodo', rnd.choice(['manha', 'tarde', '18-20', '20-22', '22-00', 'madrugada', 'noite', '18', 18, None, '']))
        desc = rnd.choice(CASOS_MANUAIS + SITUACOES)
        talvez(o, 'descricao', rnd.choice([desc, '  ' + desc + '\N{IDEOGRAPHIC SPACE}\n', 'w' * rnd.randrange(290, 310) + rnd.choice(EMOJIS) * 3,
                                           None, 42, ['a'], '\N{ZERO WIDTH NO-BREAK SPACE}' + desc]))
        talvez(o, 'removidos', rnd.choice([
            ['nome', 'placa', 'telefone'], [], [rnd.choice(valores_soltos) for _ in range(rnd.randrange(0, 9))],
            ['x' * rnd.randrange(25, 40), 'y' * 28 + '😡' + 'z'], 'nome', None, {'a': 'b'},
        ]))
        talvez(o, 'resposta', rnd.choice(['Sinto muito que isso aconteceu.', ' ' * 3 + 'q' * rnd.randrange(210, 230) + '🙏🙏',
                                          '', None, 0, '\N{LINE SEPARATOR}oi\N{PARAGRAPH SEPARATOR}']))
        if rnd.random() < 0.1:
            o['extra'] = rnd.choice(valores_soltos)
        saida.append(o)
    return saida
