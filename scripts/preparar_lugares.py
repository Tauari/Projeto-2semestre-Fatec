"""Acrescenta `lugares` ao dados/osm/basemap.json: locais conhecidos de Rio Claro (rodoviária, Fatec, hospitais, parques...)
que a busca de trajeto reconhece pelo nome. Lê dados/osm/bruto/lugares.json (consulta em dados/osm/consulta-overpass-lugares.txt).
Formato: lugares = [[nome, lat, lng, tipo], ...] com lat/lng em 5 casas. Rode de novo para atualizar com o OpenStreetMap."""
import json, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SRC = RAIZ / "dados" / "osm" / "bruto" / "lugares.json"
BASE = RAIZ / "dados" / "osm" / "basemap.json"
TIPOS = ["amenity", "railway", "public_transport", "shop", "leisure", "tourism", "historic", "office", "building"]

lugares, vistos = [], set()
for e in json.loads(SRC.read_text(encoding="utf-8"))["elements"]:
    tags = e.get("tags", {})
    c = e if "lat" in e else e.get("center")
    nome = tags.get("name", "").strip()
    if not c or not nome or nome.lower() in vistos:
        continue
    vistos.add(nome.lower())
    tipo = next((tags[k] for k in TIPOS if k in tags), "lugar")
    lugares.append([nome, round(c["lat"], 5), round(c["lon"], 5), tipo])
lugares.sort(key=lambda l: l[0].lower())

base = json.loads(BASE.read_text(encoding="utf-8"))
base["lugares"] = lugares
BASE.write_text(json.dumps(base, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
print(len(lugares), "lugares em", BASE)
