"""Acrescenta `cruzamentos` ao dados/osm/basemap.json: onde cada par de ruas com nome se encontra ("Rua 5 com Avenida 14").
Lê o mesmo extrato das ruas do roteador (dados/osm/bruto/ruas-roteamento.json, consulta em consulta-overpass-rotas.txt).
Formato: cruzamentos = {"nomes": [...], "pontos": [[i, j, lat, lng], ...]} (i e j são posições em "nomes"; lat/lng com 5 casas).
Uma mesma rua pode ter o mesmo nome em bairros diferentes: então um par pode ter mais de um ponto."""
import itertools, json, pathlib
from collections import defaultdict

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SRC = RAIZ / "dados" / "osm" / "bruto" / "ruas-roteamento.json"
BASE = RAIZ / "dados" / "osm" / "basemap.json"

nos = defaultdict(set)  # ponto (arredondado) -> nomes das vias que passam por ele
for e in json.loads(SRC.read_text(encoding="utf-8"))["elements"]:
    nome = e.get("tags", {}).get("name", "").strip()
    if not nome or e.get("tags", {}).get("highway") in ("footway", "path", "steps", "cycleway", "pedestrian"):
        continue
    for g in e["geometry"]:
        nos[(round(g["lat"], 5), round(g["lon"], 5))].add(nome)

nomes, idx, pontos, vistos = [], {}, [], set()
for (lat, lng), vias in sorted(nos.items()):
    for a, b in itertools.combinations(sorted(vias), 2):
        chave = (a, b, round(lat, 4), round(lng, 4))  # ~11 m: pistas duplas viram um ponto só
        if chave in vistos:
            continue
        vistos.add(chave)
        for n in (a, b):
            if n not in idx:
                idx[n] = len(nomes)
                nomes.append(n)
        pontos.append([idx[a], idx[b], lat, lng])

base = json.loads(BASE.read_text(encoding="utf-8"))
base["cruzamentos"] = {"nomes": nomes, "pontos": pontos}
BASE.write_text(json.dumps(base, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
print(len(nomes), "ruas,", len(pontos), "cruzamentos em", BASE)
