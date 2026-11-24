"""Sessões individuais em cookie HttpOnly, com autorização conferida a cada requisição."""
import hashlib

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database.repositorios import instante_atual_ms
from backend.database.sessao import obter_sessao
from backend.database.tabelas import SessaoEquipe, Usuario

COOKIE_EQUIPE = 'aurora_equipe'


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def exigir_origem(request: Request) -> None:
    # Cabeçalho não simples: sites externos não podem enviá-lo sem preflight CORS autorizado.
    if request.headers.get('X-Aurora-Equipe') != '1':
        raise HTTPException(403, 'Requisição da equipe não autorizada.')


def usuario_da_sessao(request: Request, sessao: Session = Depends(obter_sessao)) -> Usuario | None:
    token = request.cookies.get(COOKIE_EQUIPE)
    acesso = sessao.get(SessaoEquipe, hash_token(token)) if token else None
    if acesso is None or acesso.expira_em <= instante_atual_ms():
        return None
    usuario = sessao.get(Usuario, acesso.usuario_id)
    return usuario if usuario and usuario.ativo else None


def exigir_moderacao(request: Request, usuario: Usuario | None = Depends(usuario_da_sessao)) -> Usuario:
    if usuario is None:
        raise HTTPException(401, 'Entre com sua conta da equipe para continuar.')
    if usuario.papel not in ('administrador', 'moderacao'):
        raise HTTPException(403, 'Esta conta não tem acesso à moderação.')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        exigir_origem(request)
    return usuario


def exigir_admin(usuario: Usuario = Depends(exigir_moderacao)) -> Usuario:
    if usuario.papel != 'administrador':
        raise HTTPException(403, 'Somente administradores podem gerenciar a equipe.')
    return usuario
