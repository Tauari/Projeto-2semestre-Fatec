"""Acesso e gestão da equipe. Quem envia relatos continua anônimo."""
import secrets
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import instante_atual_ms
from backend.database.sessao import obter_sessao
from backend.database.tabelas import CredencialEquipe, SessaoEquipe, Usuario
from backend.models.comum import Identidade
from backend.models.equipe import AcessoEquipe, AtividadeConta, ContaPublica, NovaConta
from backend.services.autorizacao import COOKIE_EQUIPE, exigir_admin, exigir_origem, hash_token, usuario_da_sessao
from backend.services.equipe import HASH_INEXISTENTE, conta_publica, criar_conta, senha_correta

router = APIRouter(tags=['usuários'])
_lock_login = threading.Lock()


def _limitar_login(request: Request, login: str):
    """10 tentativas por login/5 min e 60 totais/min por processo, sem armazenar IP."""
    agora = time.monotonic()
    with _lock_login:
        estado = getattr(request.app.state, 'tentativas_login', {})
        estado = {k: (inicio, n) for k, (inicio, n) in estado.items() if agora - inicio < (60 if k == '*' else 300)}
        chave = hash_token(login)
        for k, limite in (('*', 60), (chave, 10)):
            if estado.get(k, (agora, 0))[1] >= limite:
                raise HTTPException(429, 'Muitas tentativas. Aguarde alguns minutos e tente novamente.', headers={'Retry-After': '300'})
        for k in ('*', chave):
            inicio, n = estado.get(k, (agora, 0))
            estado[k] = inicio, n + 1
        request.app.state.tentativas_login = estado


@router.get('/usuarios/eu', response_model=Identidade, response_model_exclude_none=True)
def eu(response: Response, usuario: Usuario | None = Depends(usuario_da_sessao), sessao: Session = Depends(obter_sessao)):
    response.headers['Cache-Control'] = 'no-store'
    if usuario is None:
        return {'autenticado': False, 'papeis': []}
    return {'autenticado': True, 'papeis': ['administrador', 'moderacao'] if usuario.papel == 'administrador' else ['moderacao'],
            'usuario': conta_publica(sessao, usuario)}


@router.post('/usuarios/entrar', response_model=ContaPublica, dependencies=[Depends(exigir_origem)])
def entrar(entrada: AcessoEquipe, request: Request, response: Response, sessao: Session = Depends(obter_sessao),
           cfg: Configuracoes = Depends(obter_configuracoes)):
    _limitar_login(request, entrada.login)
    credencial = sessao.scalar(select(CredencialEquipe).where(CredencialEquipe.login == entrada.login))
    correta = senha_correta(entrada.senha.get_secret_value(), credencial.senha_hash if credencial else HASH_INEXISTENTE)
    usuario = sessao.get(Usuario, credencial.usuario_id) if credencial else None
    if not correta or usuario is None or not usuario.ativo:
        raise HTTPException(401, 'Usuário ou senha inválidos.')
    agora = instante_atual_ms()
    sessao.execute(delete(SessaoEquipe).where(SessaoEquipe.expira_em <= agora))
    anterior = request.cookies.get(COOKIE_EQUIPE)
    if anterior:
        sessao.execute(delete(SessaoEquipe).where(SessaoEquipe.token_hash == hash_token(anterior)))
    token = secrets.token_urlsafe(32)
    duracao = cfg.sessao_horas * 3600
    sessao.add(SessaoEquipe(token_hash=hash_token(token), usuario_id=usuario.id, expira_em=agora + duracao * 1000))
    sessao.commit()
    response.set_cookie(COOKIE_EQUIPE, token, max_age=duracao, httponly=True, secure=cfg.sessao_cookie_seguro,
                        samesite='strict', path='/api/v1')
    response.headers['Cache-Control'] = 'no-store'
    return conta_publica(sessao, usuario)


@router.post('/usuarios/sair', status_code=204, dependencies=[Depends(exigir_origem)])
def sair(request: Request, sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    token = request.cookies.get(COOKIE_EQUIPE)
    if token:
        sessao.execute(delete(SessaoEquipe).where(SessaoEquipe.token_hash == hash_token(token)))
        sessao.commit()
    response = Response(status_code=204, headers={'Cache-Control': 'no-store'})
    response.delete_cookie(COOKIE_EQUIPE, path='/api/v1', httponly=True, secure=cfg.sessao_cookie_seguro, samesite='strict')
    return response


@router.get('/usuarios/equipe', response_model=list[ContaPublica], dependencies=[Depends(exigir_admin)])
def listar(response: Response, sessao: Session = Depends(obter_sessao)):
    response.headers['Cache-Control'] = 'no-store'
    usuarios = sessao.scalars(select(Usuario).join(CredencialEquipe).order_by(CredencialEquipe.login))
    return [conta_publica(sessao, u) for u in usuarios]


@router.post('/usuarios/equipe', status_code=201, response_model=ContaPublica, dependencies=[Depends(exigir_admin)])
def cadastrar(entrada: NovaConta, response: Response, sessao: Session = Depends(obter_sessao)):
    response.headers['Cache-Control'] = 'no-store'
    try:
        usuario = criar_conta(sessao, entrada)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    return conta_publica(sessao, usuario)


@router.post('/usuarios/equipe/{usuario_id}/ativo', response_model=ContaPublica)
def atividade(usuario_id: str, entrada: AtividadeConta, response: Response,
              admin: Usuario = Depends(exigir_admin), sessao: Session = Depends(obter_sessao)):
    response.headers['Cache-Control'] = 'no-store'
    usuario = sessao.get(Usuario, usuario_id)
    if usuario is None or sessao.get(CredencialEquipe, usuario_id) is None:
        raise HTTPException(404, 'Conta não encontrada.')
    if usuario.id == admin.id:
        raise HTTPException(409, 'Você não pode desativar sua própria conta.')
    # Administradores só podem ser desativados pelo operador do servidor: evita a corrida do último admin.
    if usuario.papel == 'administrador' and not entrada.ativo:
        raise HTTPException(409, 'Contas administradoras não podem ser desativadas pelo painel.')
    usuario.ativo = entrada.ativo
    if not usuario.ativo:
        sessao.execute(delete(SessaoEquipe).where(SessaoEquipe.usuario_id == usuario.id))
    sessao.commit()
    return conta_publica(sessao, usuario)
