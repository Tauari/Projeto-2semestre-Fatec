# -*- coding: utf-8 -*-
"""Monta as duas versões do Aurora a partir de src/:
dist/aurora-link.html  -> conteúdo publicado como Artifact (sem <html>/<head>/<body>)
dist/aurora.html       -> arquivo completo para hospedar (GitHub Pages, Netlify etc.)"""
import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent  # raiz do repositório (o script fica em scripts/)
SRC = ROOT / "src"
DIST = ROOT / "dist"; DIST.mkdir(exist_ok=True)

css_leaflet = (ROOT / "vendor/leaflet.css").read_text(encoding="utf-8")
css_leaflet = re.sub(r"/\*.*?\*/", "", css_leaflet, flags=re.S)
css_leaflet = re.sub(r"url\((?:images/)[^)]*\)", "none", css_leaflet)
css_leaflet = re.sub(r"\s*\n\s*", "\n", css_leaflet).strip()
css_app = (SRC / "app.css").read_text(encoding="utf-8")
markup = (SRC / "app.html").read_text(encoding="utf-8")
js = (SRC / "app.js").read_text(encoding="utf-8")
data = json.loads((ROOT / "dados" / "data.json").read_text(encoding="utf-8"))
data_js = "window.AURORA_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"
osm = json.loads((ROOT / "dados" / "osm" / "basemap.json").read_text(encoding="utf-8"))
osm_js = "window.AURORA_OSM=" + json.dumps(osm, ensure_ascii=False, separators=(",", ":")) + ";"
apoio = json.loads((ROOT / "dados" / "rede-de-apoio.json").read_text(encoding="utf-8"))
apoio_js = "window.AURORA_APOIO=" + json.dumps(apoio, ensure_ascii=False, separators=(",", ":")) + ";"

TITLE = "Aurora Rio Claro"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=Bricolage+Grotesque:opsz,wght@12..96,500..800&display=swap">')
LEAFLET = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js"></script>\n'
           '<script>if(!window.L){document.write(\'<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"><\\/script>\')}</script>')

body = (markup + "\n" + LEAFLET + "\n<script>" + data_js + "</script>\n<script>" + osm_js + "</script>\n<script>" + apoio_js + "</script>\n<script>\n" + js + "\n</script>\n")
style = "<style>\n" + css_leaflet + "\n" + css_app + "\n</style>"

artifact = "<title>" + TITLE + "</title>\n" + FONTS + "\n" + style + "\n" + body
# newline="\n": a saída fica idêntica em qualquer sistema (no Windows, write_text trocaria por \r\n)
(DIST / "aurora-link.html").write_text(artifact, encoding="utf-8", newline="\n")

standalone = ('<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              '<meta name="description" content="Mapa colaborativo de segurança para mulheres em Rio Claro (SP): relatos anônimos, percepção da pesquisa, registros oficiais e onde pedir ajuda.">\n'
              '<meta name="theme-color" content="#2A2037">\n'
              '<title>' + TITLE + '</title>\n' + FONTS + "\n" + style + "\n</head>\n<body>\n" + body + "</body>\n</html>\n")
(DIST / "aurora.html").write_text(standalone, encoding="utf-8", newline="\n")
print("artifact", len(artifact.encode()), "bytes; standalone", len(standalone.encode()), "bytes")
