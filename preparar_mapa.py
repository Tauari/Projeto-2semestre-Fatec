# -*- coding: utf-8 -*-
"""Prepara o mapa de ruas embutido no app a partir do extrato do OpenStreetMap
(osm/rio-claro-osm.json: ruas, ferrovia, rios, lagos, áreas verdes e campi, geometria em polyline).
Gera osm/basemap.json com as camadas, candidatos a rótulo de rua e rótulos de lugares."""
import json, math, pathlib

BASE = pathlib.Path(__file__).resolve().parent
SRC = BASE / "osm" / "rio-claro-osm.json"
OUT = BASE / "osm" / "basemap.json"
d = json.loads(SRC.read_text(encoding="utf-8"))
names = d["names"]

MLAT = 110574.0
MLNG = 111320.0 * math.cos(math.radians(-22.41))

def dec(s):
    pts = []; i = 0; lat = 0; lng = 0
    while i < len(s):
        vals = []
        for _ in range(2):
            shift = 0; res = 0
            while True:
                b = ord(s[i]) - 63; i += 1
                res |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            vals.append(~(res >> 1) if res & 1 else res >> 1)
        lat += vals[0]; lng += vals[1]
        pts.append((lat / 1e5, lng / 1e5))
    return pts

def xy(p): return (p[1] * MLNG, p[0] * MLAT)
def seglen(a, b):
    ax, ay = xy(a); bx, by = xy(b); return math.hypot(bx - ax, by - ay)
def length(p): return sum(seglen(p[i - 1], p[i]) for i in range(1, len(p)))

def midpoint_angle(p):
    L = length(p); half = L / 2; acc = 0
    for i in range(1, len(p)):
        s = seglen(p[i - 1], p[i])
        if acc + s >= half and s > 0:
            t = (half - acc) / s
            lat = p[i - 1][0] + (p[i][0] - p[i - 1][0]) * t
            lng = p[i - 1][1] + (p[i][1] - p[i - 1][1]) * t
            ax, ay = xy(p[i - 1]); bx, by = xy(p[i])
            ang = -math.degrees(math.atan2(by - ay, bx - ax))  # CSS: y para baixo
            if ang > 90: ang -= 180
            if ang < -90: ang += 180
            return lat, lng, round(ang)
        acc += s
    return p[0][0], p[0][1], 0

def short(name):
    rep = {"Avenida": "Av.", "Rodovia": "Rod.", "Estrada": "Estr.", "Rua": "R.", "Praça": "Pç."}
    return name

def enc_num(v):
    v = ~(v << 1) if v < 0 else (v << 1)
    out = ""
    while v >= 0x20:
        out += chr((0x20 | (v & 0x1f)) + 63); v >>= 5
    return out + chr(v + 63)

def enc(pts):
    out = ""; pl = 0; pg = 0
    for la, lo in pts:
        a = round(la * 1e5); b = round(lo * 1e5)
        out += enc_num(a - pl) + enc_num(b - pg); pl = a; pg = b
    return out

def signed_area(ring):
    a = 0.0
    for i in range(len(ring)):
        x1, y1 = xy(ring[i - 1]); x2, y2 = xy(ring[i]); a += x1 * y2 - x2 * y1
    return a / 2

# ---------- camadas (strings em polyline, sem nomes) ----------
# polígonos com a mesma orientação: assim o preenchimento "nonzero" não abre buracos onde áreas se sobrepõem
layers = {}
for k in ["green", "park", "campus", "water", "river", "stream", "rail", "minor", "ter", "sec", "major"]:
    arr = [it[0] if isinstance(it, list) else it for it in d[k]]
    if k in ("green", "park", "campus", "water"):
        fixed = []
        for s_ in arr:
            ring = dec(s_)
            if len(ring) < 4: continue
            if signed_area(ring) < 0: ring = ring[::-1]
            fixed.append(enc(ring))
        arr = fixed
    layers[k] = arr

# ---------- candidatos a rótulo de rua ----------
TIER = {"major": 1, "sec": 2, "ter": 3, "minor": 4}
MINLEN = {"major": 220, "sec": 200, "ter": 180, "minor": 300}
skip = ("Trevo", "Rotatória", "Viaduto")
labels = []
for k, tier in TIER.items():
    for it in d[k]:
        if not (isinstance(it, list) and len(it) > 1): continue
        nm = names[it[1]]
        if nm.startswith(skip): continue
        p = dec(it[0])
        L = length(p)
        if L < MINLEN[k]: continue
        lat, lng, ang = midpoint_angle(p)
        labels.append([it[1], round(lat, 5), round(lng, 5), ang, tier, round(L)])
# no máximo 4 rótulos por nome e só os trechos mais longos
by = {}
for lb in labels: by.setdefault(lb[0], []).append(lb)
sl = []
for ni, lst in by.items():
    lst.sort(key=lambda x: -x[5])
    sl.extend(lst[:6 if lst[0][4] <= 2 else (4 if lst[0][4] == 3 else 3)])
sl.sort(key=lambda x: (x[4], -x[5]))
used = sorted({lb[0] for lb in sl})
remap = {old: i for i, old in enumerate(used)}
street_names = [names[i] for i in used]
sl = [[remap[lb[0]], lb[1], lb[2], lb[3], lb[4]] for lb in sl]

# ---------- rótulos de lugares (lagos, parques, campi, horto) ----------
def area_m2(ring):
    a = 0.0
    for i in range(len(ring)):
        x1, y1 = xy(ring[i - 1]); x2, y2 = xy(ring[i]); a += x1 * y2 - x2 * y1
    return abs(a) / 2

def inside(pt, ring):
    x, y = pt; c = False; j = len(ring) - 1
    for i in range(len(ring)):
        yi, xi = ring[i]; yj, xj = ring[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi): c = not c
        j = i
    return c

def label_point(ring):
    """ponto interno longe das bordas (busca em grade, estilo polylabel simplificado)"""
    lats = [p[0] for p in ring]; lngs = [p[1] for p in ring]
    best, bd = None, -1
    n = 24
    for i in range(1, n):
        for j in range(1, n):
            la = min(lats) + (max(lats) - min(lats)) * i / n
            lo = min(lngs) + (max(lngs) - min(lngs)) * j / n
            if not inside((lo, la), ring): continue
            dmin = min(seglen((la, lo), q) for q in ring[::max(1, len(ring) // 80)])
            if dmin > bd: bd, best = dmin, (la, lo)
    if best is None:
        best = (sum(lats) / len(lats), sum(lngs) / len(lngs))
    return best

RENAME = {
    "Floresta Estadual Edmundo Navarro de Andrade": "Horto Florestal (FEENA)",
    "Horto Florestal Edmundo Navarro de Andrade": "Horto Florestal (FEENA)",
    "Universidade Estadual Paulista": "Unesp",
    "UNESP - Instituto de Pesquisa em Bioenergia - IPBEN": "Unesp · IPBEN",
    "Lago Azul de Rio Claro": "Lago Azul",
    "Claretiano Faculdade e Colégio": "Claretiano",
    "ASSER - Campus Rio Claro": "ASSER",
}
pois = {}
for kind in ["green", "park", "campus", "water"]:
    for it in d[kind]:
        if not (isinstance(it, list) and len(it) > 1): continue
        nm = RENAME.get(names[it[1]], names[it[1]])
        ring = dec(it[0])
        if len(ring) < 4: continue
        a = area_m2(ring)
        if kind == "park" and a < 6000: continue
        if nm in pois and pois[nm][5] >= a: continue
        la, lo = label_point(ring)
        if a > 1e6: z = 12.5
        elif a > 1.5e5: z = 13.5
        elif a > 3e4: z = 14.5
        else: z = 15.5
        if nm in ("Unesp", "Lago Azul", "Jardim Público", "Fatec Rio Claro"): z = min(z, 13.5)
        pois[nm] = [nm, round(la, 5), round(lo, 5), kind, z, a]
poi = [v[:5] for v in sorted(pois.values(), key=lambda v: -v[5])]

out = {"layers": layers, "streetNames": street_names, "streetLabels": sl, "poi": poi,
       "source": "OpenStreetMap (ODbL), extraído em 24/09/2026"}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
cnt = {}
for lb in sl: cnt[lb[4]] = cnt.get(lb[4], 0) + 1
print("rótulos de rua por nível", cnt, "nomes", len(street_names))
print("lugares", len(poi), [p[0] + "@" + str(p[4]) for p in poi[:30]])
print("bytes", OUT.stat().st_size)
