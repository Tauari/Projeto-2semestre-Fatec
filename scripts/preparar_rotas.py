"""Gera dados/rotas/grafo.json, o grafo de ruas do roteador do app (a pé, carro e bicicleta), a partir do extrato
do OpenStreetMap em dados/osm/bruto/ruas-roteamento.json (consulta em dados/osm/consulta-overpass-rotas.txt).
Formato: nos = [lat, lng, giga, ...] (lat/lng em 1e-5 grau; giga = modos em que o nó está no maior trecho conexo)
         arestas = [u, v, metros, vai, volta, kmh_carro, ...] (vai: modos permitidos de u para v; volta: de v para u)
Modos (bits): 1 a pé, 2 bicicleta, 4 carro."""
import json, math, pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SRC = RAIZ / "dados" / "osm" / "bruto" / "ruas-roteamento.json"
OUT = RAIZ / "dados" / "rotas" / "grafo.json"
PE, BIKE, CARRO = 1, 2, 4
MLAT, MLNG = 110574.0, 111320.0 * math.cos(math.radians(-22.41))

VEICULO = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link",
           "tertiary", "tertiary_link", "unclassified", "residential", "living_street", "service", "track"}
SEM_PE_BIKE = {"motorway", "motorway_link", "trunk", "trunk_link"}
VEL = {"motorway": 80, "motorway_link": 40, "trunk": 70, "trunk_link": 40, "primary": 60, "primary_link": 40, "secondary": 50,
       "secondary_link": 40, "tertiary": 40, "tertiary_link": 30, "unclassified": 40, "residential": 30, "living_street": 10,
       "service": 15, "track": 15}


def modos(tags):
    hw, acesso = tags["highway"], tags.get("access")
    fechado = acesso in ("private", "no", "customers")
    m = 0
    if hw not in SEM_PE_BIKE and tags.get("foot") != "no" and (not fechado or tags.get("foot") in ("yes", "designated")):
        m |= PE
    bike_ok = hw in VEICULO - SEM_PE_BIKE or hw == "cycleway" or tags.get("bicycle") in ("yes", "designated")
    if bike_ok and hw != "steps" and tags.get("bicycle") != "no" and (not fechado or tags.get("bicycle") in ("yes", "designated")):
        m |= BIKE
    if hw in VEICULO and tags.get("motor_vehicle") != "no" and tags.get("vehicle") != "no" and not fechado:
        m |= CARRO
    return m


def kmh(tags):
    try:
        v = int(str(tags.get("maxspeed", "")).split()[0])
        if 5 <= v <= 120:
            return v
    except (ValueError, IndexError):
        pass
    return VEL.get(tags["highway"], 30)


def mao_unica(tags):
    """+1 só no sentido do desenho, -1 só no contrário, 0 nos dois."""
    ow, hw = tags.get("oneway"), tags["highway"]
    if ow == "-1":
        return -1
    if ow in ("yes", "true", "1") or tags.get("junction") in ("roundabout", "circular") or (ow is None and hw.startswith("motorway")):
        return 1
    return 0


def metros(a, b):
    return math.hypot((b[1] - a[1]) * MLNG, (b[0] - a[0]) * MLAT)


vias = [e for e in json.loads(SRC.read_text(encoding="utf-8"))["elements"] if e["type"] == "way" and "nodes" in e]
idx, nos, arestas = {}, [], []
for w in vias:
    t = w["tags"]; m = modos(t)
    if not m:
        continue
    sentido = mao_unica(t)
    # a mão única vale para carro e bicicleta (a pé ignora); oneway:bicycle=no libera a bicicleta nos dois sentidos
    livre = m & PE | (m & BIKE if t.get("oneway:bicycle") == "no" else 0)
    vai, volta = (m, m) if sentido == 0 else (m, livre) if sentido == 1 else (livre, m)
    ids = []
    for nid, g in zip(w["nodes"], w["geometry"]):
        if nid not in idx:
            idx[nid] = len(nos) // 3; nos += [round(g["lat"] * 1e5), round(g["lon"] * 1e5), 0]
        ids.append(idx[nid])
    v = kmh(t) if m & CARRO else 0
    for u, x in zip(ids, ids[1:]):
        d = metros((nos[3 * u] / 1e5, nos[3 * u + 1] / 1e5), (nos[3 * x] / 1e5, nos[3 * x + 1] / 1e5))
        if u != x and d > 0:
            arestas += [u, x, round(d, 1), vai, volta, v]

# nó "gigante" de cada modo: o maior conjunto conexo (ignora o sentido), para o app nunca ancorar um ponto numa ilha de ruas
pai = {b: list(range(len(nos) // 3)) for b in (PE, BIKE, CARRO)}
def raiz(p, i):
    while p[i] != i:
        p[i] = p[p[i]]; i = p[i]
    return i
for i in range(0, len(arestas), 6):
    u, x, _, vai, volta, _ = arestas[i:i + 6]
    for b in (PE, BIKE, CARRO):
        if (vai | volta) & b:
            pai[b][raiz(pai[b], u)] = raiz(pai[b], x)
for b in (PE, BIKE, CARRO):
    usados = {raiz(pai[b], u) for i in range(0, len(arestas), 6) for u in arestas[i:i + 2] if (arestas[i + 3] | arestas[i + 4]) & b}
    cont = {}
    for i in range(0, len(arestas), 6):
        if (arestas[i + 3] | arestas[i + 4]) & b:
            r = raiz(pai[b], arestas[i]); cont[r] = cont.get(r, 0) + 1
    maior = max(cont, key=cont.get)
    for n in range(len(nos) // 3):
        if raiz(pai[b], n) == maior:
            nos[3 * n + 2] |= b

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"nos": nos, "arestas": arestas, "fonte": "OpenStreetMap (ODbL)"}, separators=(",", ":")), encoding="utf-8")
print(OUT, len(nos) // 3, "nós", len(arestas) // 6, "arestas", OUT.stat().st_size // 1024, "KiB")
