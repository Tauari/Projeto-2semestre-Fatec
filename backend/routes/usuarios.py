# Identidade e autenticação de usuários da Aurora.
# Controla acesso por rota para garantir que SOMENTE administradores autorizados tenham acesso aos dados restritos do Observatório e Secretaria da Mulher.

from __future__ import annotations

import secrets
from typing import Any
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from backend.models.comum import Identidade

router = APIRouter(tags=['usuários'])

# Tokens administrativos válidos em memória (persistidos na sessão do servidor)
_TOKENS_ADMIN: set[str] = {
    "aurora_admin_token_master_2026",
    "aurora_token_observatorio_secretaria_mulher",
}

# Credenciais institucionais autorizadas (Administração / Observatório / Secretaria da Mulher)
_USUARIOS_ADMIN = {
    "admin": {
        "senha": "admin",
        "nome": "Administrador Geral",
        "cargo": "Administrador do Sistema",
        "orgao": "Prefeitura de Rio Claro / Observatório",
        "matricula": "ADM-001-RC",
        "papeis": ["admin", "observatorio", "secretaria_mulher"]
    },
    "admin_observatorio": {
        "senha": "aurora2026",
        "nome": "Dra. Helena Martins",
        "cargo": "Coordenadora do Observatório de Segurança",
        "orgao": "Observatório de Segurança de Rio Claro",
        "matricula": "OBS-2026-042",
        "papeis": ["admin", "observatorio"]
    },
    "secretaria_mulher": {
        "senha": "aurora2026",
        "nome": "Valéria Santos, MSW",
        "cargo": "Assistente Social Coordenadora",
        "orgao": "Secretaria Municipal da Mulher de Rio Claro",
        "matricula": "SEC-MULHER-109",
        "papeis": ["admin", "secretaria_mulher"]
    }
}


class CredenciaisLogin(BaseModel):
    login: str = Field(..., description="E-mail funcional ou usuário administrativo")
    senha: str = Field(..., description="Senha de acesso restrito")


class RespostaLogin(BaseModel):
    autenticado: bool
    token: str
    usuario: str
    nome: str
    cargo: str
    orgao: str
    matricula: str
    papeis: list[str]


class IdentidadeCompleta(BaseModel):
    autenticado: bool
    papeis: list[str]
    usuario: str | None = None
    nome: str | None = None
    cargo: str | None = None
    orgao: str | None = None


def extrair_token(authorization: str | None, x_admin_token: str | None) -> str | None:
    """Extrai token do cabeçalho Authorization (Bearer) ou X-Admin-Token."""
    if authorization:
        partes = authorization.strip().split()
        if len(partes) == 2 and partes[0].lower() == "bearer":
            return partes[1]
        return authorization.strip()
    if x_admin_token:
        return x_admin_token.strip()
    return None


def validar_token_admin(token: str | None) -> bool:
    """Verifica se o token informado pertence a um administrador ativo."""
    if not token:
        return False
    return token in _TOKENS_ADMIN


@router.post('/usuarios/login', response_model=RespostaLogin)
def login(dados: CredenciaisLogin):
    """Autenticação restrita para administradores do Observatório e Secretaria da Mulher."""
    login_limpo = dados.login.strip().lower()
    usuario_info = _USUARIOS_ADMIN.get(login_limpo)

    if not usuario_info or usuario_info["senha"] != dados.senha:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas. Acesso restrito a profissionais autorizados.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    novo_token = f"aurora_admin_{secrets.token_hex(16)}"
    _TOKENS_ADMIN.add(novo_token)

    return {
        "autenticado": True,
        "token": novo_token,
        "usuario": login_limpo,
        "nome": usuario_info["nome"],
        "cargo": usuario_info["cargo"],
        "orgao": usuario_info["orgao"],
        "matricula": usuario_info["matricula"],
        "papeis": usuario_info["papeis"]
    }


@router.post('/usuarios/logout')
def logout(
    authorization: str | None = Header(None, alias="Authorization"),
    x_admin_token: str | None = Header(None, alias="X-Admin-Token")
):
    """Encerra a sessão administrativa revogando o token."""
    token = extrair_token(authorization, x_admin_token)
    if token and token in _TOKENS_ADMIN and not token.startswith("aurora_admin_token_master"):
        _TOKENS_ADMIN.discard(token)
    return {"status": "sessao_encerrada"}


@router.get('/usuarios/eu', response_model=IdentidadeCompleta)
def eu(
    authorization: str | None = Header(None, alias="Authorization"),
    x_admin_token: str | None = Header(None, alias="X-Admin-Token")
):
    """Retorna o estado de autenticação de quem requisita.
    
    Somente usuários com token de administrador válido recebem autenticado=True e seus papéis.
    """
    token = extrair_token(authorization, x_admin_token)
    if validar_token_admin(token):
        return {
            "autenticado": True,
            "papeis": ["admin", "observatorio", "secretaria_mulher"],
            "usuario": "admin_observatorio",
            "nome": "Equipe Observatório & Secretaria da Mulher",
            "cargo": "Gestor(a) de Dados e Políticas Públicas",
            "orgao": "Observatório de Segurança / Secretaria da Mulher de Rio Claro"
        }
    return {
        "autenticado": False,
        "papeis": [],
        "usuario": None,
        "nome": None,
        "cargo": None,
        "orgao": None
    }