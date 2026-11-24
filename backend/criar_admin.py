"""Cria só o primeiro administrador, sem alterar contas existentes.

    python -m backend.criar_admin

Lê a senha sem eco nem argumento de linha de comando; grava somente seu hash.
"""
from getpass import getpass

from pydantic import ValidationError

from backend.database import sessao as banco
from backend.services.equipe import criar_primeiro_admin


def main():
    login = input('Usuário do primeiro administrador: ').strip()
    senha = getpass('Senha (mínimo de 12 caracteres): ')
    if senha != getpass('Confirme a senha: '):
        raise SystemExit('As senhas não coincidem. Nada foi alterado.')
    motor = banco.configurar_banco()
    banco.criar_tabelas(motor)
    try:
        with banco.SessionLocal() as sessao:
            criar_primeiro_admin(sessao, login, senha)
    except ValidationError:
        raise SystemExit('Use usuário com 3–64 letras, números, ponto, hífen ou sublinhado e senha com 12–128 caracteres.')
    except ValueError as exc:
        raise SystemExit(str(exc))
    finally:
        motor.dispose()
    print('Administrador criado. Entre em /moderacao para cadastrar a equipe.')


if __name__ == '__main__':
    main()
