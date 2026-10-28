"""Servidor da Aurora: a API em ``/api/v1``, o Leaflet em ``/vendor`` e o frontend em ``/``.

``dados/`` não é servida como pasta: os dados só saem pelas rotas da API. Rode sem log de acesso, para
não gravar IPs no console::

    python -m uvicorn backend.main:app --no-access-log
"""
from __future__ import annotations

import logging
import mimetypes
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match, Mount

from backend import __version__
from backend.config import obter_configuracoes
from backend.database import sessao as banco
from backend.models.comum import traduzir_erros
from backend.routes import ROTAS
from backend.services.ia import obter_provedor
from backend.services.processamento_dados import carregar_dados_iniciais
from backend.services.retencao import aplicar_retencao

PREFIXO_API = '/api/v1'
log = logging.getLogger('aurora')

# no Windows, o registro às vezes diz text/plain para .js, e o navegador recusa carregar módulos ES assim
for _tipo, _extensao in (('text/javascript', '.js'), ('text/javascript', '.mjs'), ('text/css', '.css')):
    mimetypes.add_type(_tipo, _extensao)

# mensagens padrão (em inglês) do Starlette e do FastAPI, em português
_DETALHES_PADRAO = {404: 'Recurso não encontrado.', 405: 'Método não permitido.'}
_TRADUCOES = {'There was an error parsing the body': 'Não foi possível ler o corpo da requisição.'}


class _CorpoGrandeDemais(StarletteHTTPException):
    def __init__(self):
        super().__init__(413, 'O corpo da requisição é grande demais.')


class LimiteDeCorpo:
    """Recusa com 413 o corpo maior que ``limite_corpo_bytes``, antes de ele ir inteiro para a memória.

    Olha o Content-Length e também conta os bytes de corpos sem ele (chunked). O erro é um HTTPException,
    que o FastAPI repassa mesmo quando acontece no meio da leitura do corpo.
    """

    def __init__(self, app, limite: int):
        self.app, self.limite = app, limite

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        for nome, valor in scope.get('headers') or []:
            if nome == b'content-length' and valor.isdigit() and int(valor) > self.limite:
                return await self._recusar(scope, receive, send)
        lidos = 0

        async def receber():
            nonlocal lidos
            mensagem = await receive()
            if mensagem['type'] == 'http.request':
                lidos += len(mensagem.get('body', b''))
                if lidos > self.limite:
                    raise _CorpoGrandeDemais()
            return mensagem

        await self.app(scope, receber, send)

    async def _recusar(self, scope, receive, send):
        resposta = JSONResponse(status_code=413, content={'detail': 'O corpo da requisição é grande demais.'})
        await resposta(scope, receive, send)


def _eh_da_api(caminho: str) -> bool:
    return caminho == '/api' or caminho.startswith('/api/')


class _EstaticosSemCache(StaticFiles):
    """O frontend muda toda hora: o navegador confere a cada abertura se há versão nova (e não baixa de novo se nada mudou)."""

    async def get_response(self, path, scope):
        r = await super().get_response(path, scope)
        r.headers['Cache-Control'] = 'no-cache'
        return r


class _MontagemFrontend(Mount):
    """Frontend em ``/``. Nunca responde por ``/api``: lá, um caminho desconhecido é um 404 em JSON da API."""

    def matches(self, scope):
        if scope['type'] in ('http', 'websocket'):
            caminho, raiz = scope['path'], scope.get('root_path', '')
            if raiz and caminho.startswith(raiz):
                caminho = caminho[len(raiz):]
            if _eh_da_api(caminho):
                return Match.NONE, {}
        return super().matches(scope)


async def _tratar_http(request: Request, exc: StarletteHTTPException):
    detalhe = exc.detail
    try:
        padrao = HTTPStatus(exc.status_code).phrase
    except ValueError:
        padrao = None
    if detalhe == padrao and exc.status_code in _DETALHES_PADRAO:
        detalhe = _DETALHES_PADRAO[exc.status_code]
    elif isinstance(detalhe, str) and detalhe in _TRADUCOES:
        detalhe = _TRADUCOES[detalhe]
    if detalhe is not exc.detail:
        exc = StarletteHTTPException(exc.status_code, detalhe, headers=exc.headers)
    return await http_exception_handler(request, exc)


async def _tratar_validacao(request: Request, exc: RequestValidationError):
    if request.method == 'POST' and request.url.path.rstrip('/').endswith(PREFIXO_API + '/relatos'):
        detalhe = 'Dados do relato inválidos.'
    else:
        detalhe = 'Dados da requisição inválidos.'
    return JSONResponse(status_code=422, content={'detail': detalhe, 'erros': traduzir_erros(exc.errors())})


async def _tratar_erro_interno(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={'detail': 'Erro interno do servidor.'})


@asynccontextmanager
async def _ciclo_de_vida(app: FastAPI):
    cfg = obter_configuracoes()
    obter_provedor(cfg.ia_provedor)  # provedor desconhecido: falha já na inicialização, com mensagem clara
    motor = banco.configurar_banco(cfg.banco_url)
    banco.criar_tabelas(motor)
    with banco.SessionLocal() as sessao:
        if cfg.carga_automatica:
            carregar_dados_iniciais(sessao, cfg.pasta_dados)
        apagados = aplicar_retencao(sessao)
    if apagados:
        log.info('retenção: %d relato(s) apagado(s) por idade.', apagados)
    try:
        yield
    finally:
        motor.dispose()


def create_app() -> FastAPI:
    cfg = obter_configuracoes()
    banco.configurar_banco(cfg.banco_url)
    app = FastAPI(title='Aurora Rio Claro', version=__version__, lifespan=_ciclo_de_vida,
                  docs_url=PREFIXO_API + '/docs', redoc_url=None, openapi_url=PREFIXO_API + '/openapi.json')
    app.add_exception_handler(StarletteHTTPException, _tratar_http)
    app.add_exception_handler(RequestValidationError, _tratar_validacao)
    app.add_exception_handler(Exception, _tratar_erro_interno)
    app.add_middleware(LimiteDeCorpo, limite=cfg.limite_corpo_bytes)
    if cfg.cors_origens:
        app.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origens, allow_methods=['GET', 'POST', 'DELETE'],
                           allow_headers=['Content-Type', 'X-Chave-Exclusao'])
    for rota in ROTAS:
        app.include_router(rota, prefix=PREFIXO_API)
    if cfg.servir_frontend:
        vendor, frontend = Path(cfg.pasta_vendor), Path(cfg.pasta_frontend)
        if vendor.is_dir():
            app.mount('/vendor', StaticFiles(directory=vendor), name='vendor')
        if frontend.is_dir():
            # por último: "/" casa com tudo o que as rotas acima não pegaram
            app.router.routes.append(_MontagemFrontend('/', app=_EstaticosSemCache(directory=frontend, html=True), name='frontend'))
    return app


app = create_app()


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('backend.main:app', host='127.0.0.1', port=8000, access_log=False)
