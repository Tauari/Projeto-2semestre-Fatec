"""Senhas com scrypt e operações de contas, sem guardar senha ou token em texto puro."""
import hashlib
import hmac
import secrets
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.repositorios import instante_atual_ms
from backend.database.tabelas import CredencialEquipe, Usuario
from backend.models.equipe import NovaConta


def hash_senha(senha: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    valor = hashlib.scrypt(senha.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=1, maxmem=64 * 1024 * 1024).hex()
    return 'scrypt$' + salt + '$' + valor


# Mesmo custo de verificação para um usuário inexistente.
HASH_INEXISTENTE = hash_senha(secrets.token_urlsafe(32))


def senha_correta(senha: str, armazenada: str) -> bool:
    _, salt, _ = armazenada.split('$')
    return hmac.compare_digest(hash_senha(senha, salt), armazenada)


def conta_publica(sessao: Session, usuario: Usuario) -> dict:
    credencial = sessao.get(CredencialEquipe, usuario.id)
    return {'id': usuario.id, 'login': credencial.login, 'papel': usuario.papel, 'ativo': usuario.ativo}


def criar_conta(sessao: Session, entrada: NovaConta) -> Usuario:
    usuario = Usuario(id=uuid4().hex, papel=entrada.papel, identificador_externo=None,
                      criado_em=instante_atual_ms(), ativo=True)
    try:
        sessao.add(usuario)
        sessao.flush()
        sessao.add(CredencialEquipe(usuario_id=usuario.id, login=entrada.login,
                                    senha_hash=hash_senha(entrada.senha.get_secret_value())))
        sessao.commit()
    except IntegrityError:
        sessao.rollback()
        raise ValueError('Este usuário já existe.') from None
    return usuario


def criar_primeiro_admin(sessao: Session, login: str, senha: str) -> Usuario:
    """Bootstrap local: recusa repetir a criação; não muda nenhuma conta existente."""
    if sessao.scalar(select(Usuario.id).where(Usuario.papel == 'administrador').limit(1)):
        raise ValueError('Já existe um administrador. Cadastre outras pessoas pelo painel.')
    return criar_conta(sessao, NovaConta(login=login, senha=senha, papel='administrador'))
