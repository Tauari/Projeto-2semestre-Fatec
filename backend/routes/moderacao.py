"""Moderação compartilhada: decisões persistidas e protegidas no servidor."""
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session

from backend.config import Configuracoes, obter_configuracoes
from backend.database.repositorios import DIA_MS, RepositorioModeracao, RepositorioRelatos, instante_atual_ms
from backend.database.tabelas import Usuario
from backend.services.equipe import conta_publica
from backend.database.sessao import obter_sessao
from backend.models.moderacao import AcaoModeracaoEntrada, EstadoModeracao, PainelModeracao, VerificacoesPublicas
from backend.routes.relatos import relato_publico
from backend.services.autorizacao import exigir_moderacao, exigir_admin
from backend.services.painel_equipe import resumo_equipe
from backend.services.relatorio import gerar_pdf
from backend.services.retencao import limite_retencao_ms

router = APIRouter(tags=['moderação'])


@router.get('/moderacao/estado', response_model=VerificacoesPublicas)
def estado_publico(response: Response, sessao: Session = Depends(obter_sessao),
                   cfg: Configuracoes = Depends(obter_configuracoes)):
    response.headers['Cache-Control'] = 'no-store'
    agora = instante_atual_ms()
    desde = max(agora - cfg.relatos_janela_dias * DIA_MS, limite_retencao_ms(cfg, agora) or 0)
    ids = [r.id for r in RepositorioRelatos(sessao).listar_desde(desde)]
    # Nunca revela IDs ou texto de relatos ocultos.
    return {'verificado': RepositorioModeracao(sessao).estado(ids)['verificado']}


@router.get('/moderacao', response_model=PainelModeracao, dependencies=[Depends(exigir_moderacao)])
def painel(response: Response, usuario: Usuario = Depends(exigir_moderacao), sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    response.headers['Cache-Control'] = 'no-store'
    relatos = RepositorioRelatos(sessao).listar_desde(limite_retencao_ms(cfg, instante_atual_ms()) or 0, incluir_ocultos=True)
    return {'usuario': conta_publica(sessao, usuario), 'relatos': [relato_publico(r) for r in relatos],
            'mod': RepositorioModeracao(sessao).estado([r.id for r in relatos])}


@router.post('/moderacao/{relato_id}', response_model=EstadoModeracao, dependencies=[Depends(exigir_moderacao)])
def moderar(relato_id: str, entrada: AcaoModeracaoEntrada, response: Response, usuario: Usuario = Depends(exigir_moderacao),
            sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    response.headers['Cache-Control'] = 'no-store'
    relato = RepositorioRelatos(sessao).obter(relato_id)
    limite = limite_retencao_ms(cfg, instante_atual_ms())
    if relato is None or (limite is not None and relato.criado < limite):
        raise HTTPException(404, 'Relato não encontrado.')
    repo = RepositorioModeracao(sessao)
    repo.registrar(relato_id, entrada.campo, entrada.valor, usuario.id)
    sessao.commit()
    return repo.estado([relato_id])


@router.get('/moderacao/resumo', dependencies=[Depends(exigir_moderacao)])
def resumo(response: Response, dias: int = Query(30, ge=1, le=365), sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    response.headers['Cache-Control'] = 'no-store'
    return resumo_equipe(sessao, cfg, dias)


@router.get('/moderacao/relatorio.pdf', dependencies=[Depends(exigir_admin)])
def relatorio(dias: int = Query(30, ge=1, le=365), encaminhamento: bool = False, sessao: Session = Depends(obter_sessao), cfg: Configuracoes = Depends(obter_configuracoes)):
    pdf = gerar_pdf(resumo_equipe(sessao, cfg, dias), encaminhamento)
    nome = 'aurora-minuta-encaminhamento.pdf' if encaminhamento else 'aurora-relatorio.pdf'
    return Response(pdf, media_type='application/pdf', headers={'Cache-Control':'no-store', 'Content-Disposition':f'attachment; filename="{nome}"'})
