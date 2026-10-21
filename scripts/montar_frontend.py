"""Gera dist/aurora-novo.html: o frontend/ novo em um único arquivo (abre com dois cliques, sem servidor).
Módulos viram data: URLs ligadas por um import map; os JSON de dados/ vão embutidos e o fetch os devolve."""
import base64, json, pathlib, posixpath, re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FRONT = RAIZ / "frontend"
ler = lambda p: p.read_text(encoding="utf-8")

mods = {}
for p in sorted(FRONT.rglob("*.js")):
    rel = p.relative_to(FRONT).as_posix()
    mods[rel] = ler(p)

def resolve(de, alvo):
    return posixpath.normpath(posixpath.join(posixpath.dirname(de), alvo))

spec = lambda rel: "aurora/" + rel
imp = re.compile(r"""((?:from|import)\s*)(['"])(\.{1,2}/[^'"]+)\2""")
mapa = {}
for rel, src in mods.items():
    src = imp.sub(lambda m: m.group(1) + "'" + spec(resolve(rel, m.group(3))) + "'", src)
    mapa[spec(rel)] = "data:text/javascript;base64," + base64.b64encode(src.encode()).decode()

dados = {
    "data.json": ler(RAIZ / "dados/data.json"),
    "rede-de-apoio.json": ler(RAIZ / "dados/rede-de-apoio.json"),
    "basemap.json": ler(RAIZ / "dados/osm/basemap.json"),
    "grafo.json": ler(RAIZ / "dados/rotas/grafo.json"),
}
prelude = ("const __D=" + json.dumps({k: json.loads(v) for k, v in dados.items()}, ensure_ascii=False, separators=(",", ":")) + ";"
           "const __f=window.fetch;window.fetch=(u,o)=>{const k=String(u).split('/').pop();"
           "return k in __D?Promise.resolve(new Response(JSON.stringify(__D[k]),{headers:{'content-type':'application/json'}})):Promise.reject(new TypeError('offline'))};")

html = ler(FRONT / "index.html")
html = html.replace('<link rel="stylesheet" href="../vendor/leaflet.css">', "<style>" + ler(RAIZ / "vendor/leaflet.css") + "</style>")
html = html.replace('<link rel="stylesheet" href="shared/app.css">', "<style>" + ler(FRONT / "shared/app.css") + "</style>")
fontes = ler(RAIZ / "vendor/fontes/fontes.css")
for arq in (RAIZ / "vendor/fontes").glob("*.woff2"):
    fontes = fontes.replace(arq.name, "data:font/woff2;base64," + base64.b64encode(arq.read_bytes()).decode())
html = html.replace('<link rel="stylesheet" href="../vendor/fontes/fontes.css">', "<style>" + fontes + "</style>")
html = html.replace('<script src="../vendor/leaflet.js"></script>', "<script>" + ler(RAIZ / "vendor/leaflet.js").replace("</script", "<\\/script") + "</script>")
tag = '<script type="module" src="main.js"></script>'
assert tag in html
html = html.replace(tag, "<script>" + prelude + "</script>\n<script type=\"importmap\">" + json.dumps({"imports": mapa}) + "</script>\n<script type=\"module\">import 'aurora/main.js'</script>")
saida = RAIZ / "dist" / "aurora-novo.html"
saida.write_text(html, encoding="utf-8", newline="\n")
print(saida, len(html) // 1024, "KiB")
