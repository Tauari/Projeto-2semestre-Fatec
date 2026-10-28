"""Rotas da API. O ``main.py`` inclui todas com o prefixo ``/api/v1``."""
from backend.routes import analise, apoio, dados_oficiais, dados_percepcao, dashboard, ia, mapa, moderacao, relatos, sistema, usuarios

ROTAS = (sistema.router, mapa.router, relatos.router, dados_oficiais.router, dados_percepcao.router, dashboard.router,
         ia.router, moderacao.router, apoio.router, usuarios.router, analise.router)

__all__ = ['ROTAS']
