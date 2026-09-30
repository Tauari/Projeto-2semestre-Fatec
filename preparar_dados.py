# -*- coding: utf-8 -*-
"""Prepara os dados do MVP Aurora a partir das duas fontes enviadas:
- ocorrencias-rio-claro-completo.md  (recorte de Rio Claro da base de B.O. SSP/FALASP)
- Seguranca e percepcao das mulheres em Rio Claro 2.csv (51 respostas do formulário)
Gera data.json com agregados por célula hexagonal (~1 km) e estatísticas da pesquisa.
"""
import csv, json, math, re, unicodedata, collections, datetime, pathlib

BASE = pathlib.Path(__file__).resolve().parent
MD = BASE / "dados" / "ocorrencias-rio-claro-completo.md"
CSV = BASE / "dados" / "pesquisa-seguranca-mulheres-rio-claro.csv"
OUT = BASE / "dados" / "data.json"

# ---------- grade hexagonal (mesmas constantes do JavaScript) ----------
LAT0, LNG0, R = -22.41, -47.56, 500.0
MLAT = 110574.0
MLNG = 111320.0 * math.cos(math.radians(LAT0))
S3 = math.sqrt(3)

def to_xy(lat, lng):
    return ((lng - LNG0) * MLNG, (lat - LAT0) * MLAT)

def to_ll(x, y):
    return (LAT0 + y / MLAT, LNG0 + x / MLNG)

def cube_round(q, r):
    s = -q - r
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return int(rq), int(rr)

def cell_of(lat, lng):
    x, y = to_xy(lat, lng)
    q = (S3 / 3 * x - y / 3) / R
    r = (2 / 3 * y) / R
    return cube_round(q, r)

def cell_center(q, r):
    x = R * S3 * (q + r / 2)
    y = R * 1.5 * r
    return to_ll(x, y)

def cid(q, r):
    return f"{q}_{r}"

# ---------- nomes de bairros ----------
ACC = {
    "CENTENARIO": "Centenário", "CHACARA": "Chácara", "SAO": "São", "JOSE": "José",
    "PARAISO": "Paraíso", "ESTADIO": "Estádio", "CONSOLACAO": "Consolação", "SAUDE": "Saúde",
    "OLIMPICO": "Olímpico", "UNIVERSITARIO": "Universitário", "INDUSTRIAS": "Indústrias",
    "HIPODROMO": "Hipódromo", "INDEPENDENCIA": "Independência", "OPERARIA": "Operária",
    "INDAIA": "Indaiá", "ARAUCARIA": "Araucária", "BRASILIA": "Brasília", "NACOES": "Nações",
    "AMERICA": "América", "CERVEZAO": "Cervezão", "FLORIDA": "Flórida", "AGUAS": "Águas",
    "ITAPUA": "Itapuã", "ESPERANCA": "Esperança", "FLORENCA": "Florença",
    "ASSISTENCIA": "Assistência", "IPE": "Ipê", "DONANGELA": "Donângela", "MAE": "Mãe",
    "ALEMA": "Alemã", "EXPANSAO": "Expansão", "SEBASTIAO": "Sebastião", "BENJAMIM": "Benjamim",
    "GRACIOLI": "Gracioli", "IRIS": "Íris",
}
LOWER = {"DA", "DAS", "DE", "DO", "DOS", "E"}
KEEP_UP = {"BNH", "I", "II", "III"}

def strip_acc(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def pretty(name):
    name = name.strip()
    name = re.sub(r"^JD\.?\s+", "JARDIM ", name)
    words = name.split()
    out = []
    for i, w in enumerate(words):
        base = strip_acc(w).upper()
        paren = ""
        if w.startswith("("):
            paren = "("; w = w[1:]; base = strip_acc(w).upper()
        close = ""
        if w.endswith(")"):
            close = ")"; w = w[:-1]; base = strip_acc(w).upper()
        if base in KEEP_UP:
            t = base
        elif i > 0 and base in LOWER:
            t = base.lower()
        elif base in ACC:
            t = ACC[base]
        else:
            t = w.capitalize()
        out.append(paren + t + close)
    return " ".join(out)

# ---------- leitura do MD ----------
md = open(MD, encoding="utf-8").read()
blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
geom = json.loads(blocks[0])
data = json.loads(blocks[3])
rows = data["bairros"]
ng = data["cidades_ng"][0]
assert len(rows) == 225, len(rows)

PH = (-22.4108, -47.5596)  # coordenada genérica repetida para bairros sem posição própria

tot = collections.Counter()
groups = {k: collections.Counter() for k in ["rural", "placeholder", "naoinf", "mapeado"]}
lines = collections.Counter()
mapped = []
for r in rows:
    n = r["vd"] + r["fe"] + r["te"]
    tot["vd"] += r["vd"]; tot["fe"] += r["fe"]; tot["te"] += r["te"]
    if r["b"] == "AREA RURAL":
        g = "rural"
    elif (r["lat"], r["lng"]) == PH:
        g = "placeholder"
    elif r["b"].strip() == "-":
        g = "naoinf"
    else:
        g = "mapeado"
        mapped.append(r)
    for k in ("vd", "fe", "te"):
        groups[g][k] += r[k]
    groups[g]["n"] += n
    lines[g] += 1

tot_all = {"vd": tot["vd"] + ng["vd"], "fe": tot["fe"] + ng["fe"], "te": tot["te"] + ng["te"]}
tot_all["n"] = tot_all["vd"] + tot_all["fe"] + tot_all["te"]
assert tot_all["n"] == 683, tot_all

ALIAS = {"JARDIM CHERVESON": "Cervezão", "JARDIM CHERVEZON": "Cervezão", "CHERVESON": "Cervezão",
         "CERVEZÃO": "Cervezão", "SANTA ELISA": "Jardim Santa Eliza", "SANTA ELIZA": "Jardim Santa Eliza",
         "JARDIM RESIDENCIAL SANTA ELIZA": "Jardim Santa Eliza", "RECANTO PARAISO": "Recanto Paraíso",
         "ESTADIO": "Bairro do Estádio", "ESTÁDIO": "Bairro do Estádio", "BAIRRO DO ESTADIO": "Bairro do Estádio",
         "BAIRRO DA CONSOLACAO": "Consolação", "BAIRRO SANTA CRUZ": "Santa Cruz", "BAIRRO SANTANA": "Santana",
         "JD NOVO 2": "Jardim Novo", "JARDIM PROGRESSO 2": "Jardim Progresso",
         "JARDIM DAS NAÇÕES II": "Jardim das Nações", "JARDIM DAS NAÇÕES I": "Jardim das Nações",
         "JARDIM DAS NAÇÕES 1": "Jardim das Nações", "JARDIM DAS NAÇÕES 2": "Jardim das Nações",
         "JD NAÇOES I": "Jardim das Nações", "JD NAÇÕES I": "Jardim das Nações", "NAÇÕES 1": "Jardim das Nações",
         "JARDIM BRASÍLIA II": "Jardim Brasília", "JARDIM PAULISTA II": "Jardim Paulista",
         "JD. GUANABARA": "Jardim Guanabara", "JD. BOM SUCESSO": "Jardim Bom Sucesso",
         "JD MARIA CRISTINA": "Jardim Maria Cristina", "JARDIM REGINA PICELLI": "Jardim Dona Regina Picelli",
         "NOVA AJAPI (AJAPI)": "Ajapi", "JARDIM TERRAS DE AJAPI (AJAPI)": "Ajapi",
         "BOM RETIRO II": "Bom Retiro", "JARDIM SÃO CAETANO II": "São Caetano", "JARDIM SAO CAETANO": "São Caetano",
         "SÃO CAETANO": "São Caetano", "JARDIM IPANEMA (EXPANSAO)": "Jardim Ipanema",
         "RESIDENCIAL BOSQUES DE RIO CLARO": "Residencial dos Bosques"}

# ---------- agregação por célula ----------
cells = {}
for r in mapped:
    q, rr = cell_of(r["lat"], r["lng"])
    k = cid(q, rr)
    c = cells.setdefault(k, {"vd": 0, "fe": 0, "te": 0, "n": 0, "b": collections.Counter()})
    c["vd"] += r["vd"]; c["fe"] += r["fe"]; c["te"] += r["te"]
    n = r["vd"] + r["fe"] + r["te"]
    c["n"] += n
    c["b"][ALIAS.get(r["b"], pretty(r["b"]))] += n
bo_cells = {}
for k, c in cells.items():
    bo_cells[k] = {"vd": c["vd"], "fe": c["fe"], "te": c["te"], "n": c["n"],
                   "b": [[nm, v] for nm, v in c["b"].most_common()]}
assert sum(c["n"] for c in bo_cells.values()) == groups["mapeado"]["n"]

bag = collections.defaultdict(lambda: {"n": 0, "lat": 0.0, "lng": 0.0})
for r in mapped:
    nm = ALIAS.get(r["b"], pretty(r["b"]))
    n = max(1, r["vd"] + r["fe"] + r["te"])
    b = bag[nm]
    b["lat"] += r["lat"] * n; b["lng"] += r["lng"] * n; b["n"] += n
bairros_all = []
for nm, b in bag.items():
    bairros_all.append([nm, round(b["lat"] / b["n"], 4), round(b["lng"] / b["n"], 4), b["n"]])
bairros_all.sort(key=lambda x: -x[3])

# rótulos exibidos no mapa: nível 1 aparece desde o zoom inicial
LABELS1 = ["Centro", "Bela Vista", "Vila Alemã", "Cervezão", "Parque Universitário", "Jardim Centenário",
           "Chácara Lusa", "Vila Nova", "Jardim Novo", "Distrito Industrial", "Ajapi", "Assistência",
           "Jardim Santa Eliza", "Parque Mãe Preta", "Consolação", "Jardim Floridiana", "Batovi"]
LABELS2 = ["Vila Indaiá", "Bairro do Estádio", "Santa Cruz", "Cidade Nova", "Vila Operária", "Vila Cristina",
           "Jardim Independência", "Jardim Panorama", "Jardim Bela Vista", "Jardim Claret", "Jardim Mirassol",
           "Jardim Brasília", "Jardim das Nações", "Terra Nova", "Cidade Jardim", "Jardim Itapuã",
           "Parque Flórida", "Parque Palmeiras", "Bom Retiro", "Jardim Paulista", "Jardim Progresso",
           "Boa Esperança", "Jardim Hipódromo", "Vila São Miguel", "Jardim Residencial das Palmeiras",
           "Vila Paulista", "Jardim Primavera", "Vila Aparecida", "Parque das Indústrias", "Recanto Paraíso",
           "Jardim Cidade Azul", "Jardim Olinda", "Alto do Santana", "Santana", "Vila Martins", "Vila Verde"]
pos = {b[0]: b for b in bairros_all}
labels = []
for tier, lst in ((1, LABELS1), (2, LABELS2)):
    for nm in lst:
        if nm in pos:
            b = pos[nm]
            labels.append([nm, b[1], b[2], tier])
        else:
            print("rótulo sem posição:", nm)

# ---------- contorno municipal ----------
ring = geom["geometry"]["coordinates"][0]
boundary = [[round(p[1], 4), round(p[0], 4)] for p in ring]

def point_in_poly(lat, lng, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        yi, xi = poly[i]; yj, xj = poly[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside

# campo de células de fundo: células a até ~1,3 km de algum bairro mapeado e dentro do município
pts = [(r["lat"], r["lng"]) for r in mapped]
field = set(bo_cells.keys())
for (lat, lng) in pts:
    q0, r0 = cell_of(lat, lng)
    for dq in range(-2, 3):
        for dr in range(-2, 3):
            if abs(dq + dr) > 2:
                continue
            q, rr = q0 + dq, r0 + dr
            clat, clng = cell_center(q, rr)
            if point_in_poly(clat, clng, boundary):
                field.add(cid(q, rr))
field = sorted(field)

# ---------- pesquisa ----------
rowsq = list(csv.reader(open(CSV, encoding="utf-8")))
hdr = [h.strip() for h in rowsq[0]]
resp = rowsq[1:]
N = len(resp)
assert N == 51

def multi(col):
    c = collections.Counter()
    for r in resp:
        for p in r[col].split(";"):
            p = p.strip()
            if p:
                c[p] += 1
    return c

def pct(v):
    return round(100 * v / N)

stats = {}
def put(key, title, col, keep=None, merge=None, order=None):
    c = multi(col)
    if merge:
        m = collections.Counter()
        for k, v in c.items():
            m[merge.get(k, k)] += v
        c = m
    items = c.most_common()
    if keep:
        items = [(k, v) for k, v in items if v >= keep]
    if order:
        items = sorted(items, key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
    answered = sum(1 for r in resp if r[col].strip())
    stats[key] = {"t": title, "n": answered, "i": [[k, v] for k, v in items]}

put("idade", "Faixa etária", 1, order=["Menos de 18", "18–20", "21–24", "25–29", "30–39", "40–49"])
put("desloc", "Como se deslocam", 4, merge={"uber / a pé  e transporte publico": "Outros", "Todos": "Outros",
                                               "Ônibus executivo": "Transporte público"})
put("periodo", "Períodos em que se sentem menos seguras", 5,
    order=["Manhã", "Tarde", "Início da noite", "Noite", "Madrugada", "Não tenho diferença de percepção por horário"])
put("evita", "Evitam passar por certos locais?", 6, order=["Sim, frequentemente", "Sim, algumas vezes", "Raramente", "Não"])
put("motivo", "O que faz evitar um local", 7, keep=2)
put("viveu", "Já viveram situação de insegurança na cidade", 8)
put("situacao", "Tipos de situação vividos", 9, keep=2)
put("horario", "Horários em que a região citada gera mais insegurança", 12,
    merge={"O tempo todo": "Qualquer horário", "Não tem horário": "Qualquer horário", "qualquer horário": "Qualquer horário"},
    order=["Antes das 18h", "18h–20h", "20h–22h", "22h–00h", "Madrugada", "Qualquer horário"])
put("sabe", "Como ficam sabendo de riscos", 13, keep=2)
put("whats", "Principal problema dos avisos no WhatsApp", 16, keep=2)
put("usaria", "Usariam um mapa colaborativo", 17, order=["Com certeza", "Provavelmente sim", "Talvez"])
put("funcoes", "Funcionalidades mais úteis", 18)
put("confia_pad", "Confiariam em análise de padrões", 19, order=["Sim", "Talvez", "Não"])
put("confianca", "O que é preciso para confiar", 20, keep=2)
put("participar", "Participariam da plataforma", 22, order=["Sim", "Talvez", "Não"])
put("contribuir", "Como contribuiriam", 23, keep=2)

# temas das respostas abertas "o que mudaria"
THEMES = [("Iluminação pública", r"ilumina"), ("Policiamento e guardas", r"polic|guarda|vigil|fiscaliza"),
          ("Câmeras", r"c[âa]mera"), ("Transporte e ônibus", r"transporte|[ôo]nibus|linhas"),
          ("Pontos de ajuda", r"pontos de ajuda"), ("Educação e respeito", r"educa"),
          ("Defesa pessoal", r"defesa|kits")]
open_ans = [r[21].strip() for r in resp if r[21].strip()]
tc = collections.Counter()
for a in open_ans:
    al = a.lower()
    for nm, pat in THEMES:
        if re.search(pat, al):
            tc[nm] += 1
stats["mudaria"] = {"t": "O que mudariam (respostas abertas, por tema)", "n": len(open_ans),
                    "i": [[k, v] for k, v in tc.most_common()]}

# ---------- percepção por área (menções livres -> bairros da base) ----------
def bpos(nm):
    b = pos[nm]
    return (b[1], b[2])

LAGO_AZUL = tuple(round(sum(v) / 3, 4) for v in zip(bpos("Vila Operária"), bpos("Jardim Primavera"), bpos("Vila Aparecida")))
AREAS = {  # nome exibido -> coordenada de referência
    "Centro": bpos("Centro"), "Bela Vista / Unesp": bpos("Bela Vista"), "Vila Alemã": bpos("Vila Alemã"),
    "Vila Indaiá": bpos("Vila Indaiá"), "Vila Nova": bpos("Vila Nova"), "Cervezão": bpos("Cervezão"),
    "Consolação": bpos("Consolação"), "Parque Universitário": bpos("Parque Universitário"),
    "Bairro do Estádio": bpos("Bairro do Estádio"), "Terra Nova": bpos("Terra Nova"), "Jardim Novo": bpos("Jardim Novo"),
    "Jd. Residencial das Palmeiras": bpos("Jardim Residencial das Palmeiras"), "Jardim Bela Vista": bpos("Jardim Bela Vista"),
    "Lago Azul": LAGO_AZUL, "Rodoviária (Jardim Claret)": bpos("Jardim Claret"),
}

# ---------- agregação por célula ----------
cells = {}
for r in mapped:
    q, rr = cell_of(r["lat"], r["lng"])
    k = cid(q, rr)
    c = cells.setdefault(k, {"vd": 0, "fe": 0, "te": 0, "n": 0, "b": collections.Counter()})
    c["vd"] += r["vd"]; c["fe"] += r["fe"]; c["te"] += r["te"]
    n = r["vd"] + r["fe"] + r["te"]
    c["n"] += n
    c["b"][ALIAS.get(r["b"], pretty(r["b"]))] += n
bo_cells = {}
for k, c in cells.items():
    bo_cells[k] = {"vd": c["vd"], "fe": c["fe"], "te": c["te"], "n": c["n"],
                   "b": [[nm, v] for nm, v in c["b"].most_common()]}
assert sum(c["n"] for c in bo_cells.values()) == groups["mapeado"]["n"]

# ---------- lista de bairros (nomes + posição) para nomear células e para busca no chat ----------
RULES = [  # (regex, área)
    (r"\bjardim bela vista\b", "Jardim Bela Vista"),
    (r"(?<!jardim )\bbela vista\b|gr[êe]mio", "Bela Vista / Unesp"),
    (r"unesp", "Bela Vista / Unesp"),
    (r"\bcentr(o|al)\b|esta[çc][ãa]o", "Centro"),
    (r"vila alem|av\.? ?24", "Vila Alemã"),
    (r"indai", "Vila Indaiá"), (r"vila nova", "Vila Nova"), (r"cervez", "Cervezão"),
    (r"consola", "Consolação"), (r"parque universit", "Parque Universitário"),
    (r"est[áa]dio", "Bairro do Estádio"), (r"terra nova", "Terra Nova"), (r"jardim novo", "Jardim Novo"),
    (r"palmeiras", "Jd. Residencial das Palmeiras"), (r"lago azul", "Lago Azul"), (r"rodovi", "Rodoviária (Jardim Claret)"),
]
UNMAPPED = [(r"shopping", "Região do shopping"), (r"cemit", "Arredores do cemitério"), (r"f[óo]rum", "Avenida do Fórum"),
            (r"av\.? ?40|avenida 40", "Avenida 40 (madrugada)"), (r"avenida brasil", "Avenida Brasil"),
            (r"santo ant", "Vila Santo Antônio"), (r"bares", "Praças e ruas com bares"),
            (r"afastados", "Bairros mais afastados")]
HOUR = {"Antes das 18h": "dia", "18h–20h": "18-20", "20h–22h": "20-22", "22h–00h": "22-00", "Madrugada": "madrugada",
        "O tempo todo": "todo", "Não tem horário": "todo", "qualquer horário": "todo"}

perc = {}
area_count = collections.Counter()
unm = collections.Counter()
mapped_resp = 0
for r in resp:
    txt = r[11].strip().lower()
    if not txt:
        continue
    found = []
    for pat, area in RULES:
        if re.search(pat, txt) and area not in found:
            found.append(area)
    for pat, nm in UNMAPPED:
        if re.search(pat, txt):
            unm[nm] += 1
    if found:
        mapped_resp += 1
    hours = [HOUR[h.strip()] for h in r[12].split(";") if h.strip() in HOUR]
    seen_cells = set()
    for area in found:
        area_count[area] += 1
        q, rr = cell_of(*AREAS[area])
        k = cid(q, rr)
        c = perc.setdefault(k, {"n": 0, "a": collections.Counter(), "h": collections.Counter()})
        c["a"][area] += 1
        if k in seen_cells:
            continue
        seen_cells.add(k)
        c["n"] += 1
        for h in hours:
            c["h"][h] += 1
perc_out = {k: {"n": v["n"], "a": [[a, n] for a, n in v["a"].most_common()], "h": dict(v["h"])} for k, v in perc.items()}
for k in perc_out:
    if k not in field:
        field.append(k)
field = sorted(set(field))

times = [datetime.datetime.strptime(r[0].replace(" GMT-3", ""), "%Y/%m/%d %I:%M:%S %p") for r in resp]

out = {
    "gerado": "2026-09-24",
    "hex": {"lat0": LAT0, "lng0": LNG0, "R": R},
    "boundary": boundary,
    "field": field,
    "bo": {
        "periodo": "jan/2025 – abr/2026",
        "total": tot_all,
        "grupos": {g: dict(groups[g], linhas=lines[g]) for g in groups},
        "semGeo": {"vd": ng["vd"], "fe": ng["fe"], "te": ng["te"], "n": ng["vd"] + ng["fe"] + ng["te"], "nb": ng["nb"]},
        "cells": bo_cells,
    },
    "labels": labels,
    "bairros": bairros_all,
    "pesq": {
        "n": N,
        "de": min(times).strftime("%Y-%m-%d"), "ate": max(times).strftime("%Y-%m-%d"),
        "comRegiao": sum(1 for r in resp if r[11].strip()),
        "mapeadas": mapped_resp,
        "areas": [[a, n] for a, n in area_count.most_common()],
        "outros": [[a, n] for a, n in unm.most_common()],
        "cells": perc_out,
        "stats": stats,
        "k": {  # números-chave
            "evitam": sum(1 for r in resp if r[6].startswith("Sim")),
            "viveram": sum(1 for r in resp if r[8].strip() == "Sim"),
            "usariam": sum(1 for r in resp if r[17].strip() in ("Com certeza", "Provavelmente sim")),
            "confiariam": sum(1 for r in resp if r[19].strip() == "Sim"),
            "whats": sum(1 for r in resp if "Grupo de WhatsApp" in r[13]),
            "ape": sum(1 for r in resp if "A pé" in r[4]),
            "noite": sum(1 for r in resp if ("Noite" in r[5] or "Início da noite" in r[5] or "Madrugada" in r[5])),
        },
    },
}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---------- relatório de conferência ----------
print("total B.O.", tot_all)
for g in groups:
    print(g, dict(groups[g]), "linhas", lines[g])
print("sem geo", ng)
print("células com B.O.", len(bo_cells), "campo", len(field))
top = sorted(bo_cells.items(), key=lambda kv: -kv[1]["n"])[:10]
for k, c in top:
    print("  ", k, c["n"], c["b"][:3])
print("pesquisa", N, "de", out["pesq"]["de"], "até", out["pesq"]["ate"], "com região", out["pesq"]["comRegiao"], "mapeadas", mapped_resp)
print("áreas", out["pesq"]["areas"])
print("outros", out["pesq"]["outros"])
print("células percepção", len(perc_out))
for k, v in sorted(perc_out.items(), key=lambda kv: -kv[1]["n"]):
    print("  ", k, v)
print("k", out["pesq"]["k"])
print("mudaria", stats["mudaria"])
print("bairros", len(bairros_all), "rótulos", len(labels))
print("bytes", len(json.dumps(out, ensure_ascii=False, separators=(",", ":"))))
