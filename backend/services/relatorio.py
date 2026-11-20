"""PDFs da equipe gerados em memória. Sem transmissão ou acionamento externo."""
from io import BytesIO
from datetime import datetime, timezone
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from backend.models.vocabulario import TIPOS_POR_ID


def gerar_pdf(resumo, encaminhamento=False):
    buf = BytesIO()
    styles = getSampleStyleSheet()
    texto = lambda s: Paragraph(escape(str(s)), styles['BodyText'])
    titulo = 'Minuta de encaminhamento' if encaminhamento else 'Relatório consolidado da equipe'
    story = [Paragraph('AURORA', styles['Title']), Paragraph(titulo, styles['Heading1']),
             texto('Emitido em '+datetime.fromtimestamp(resumo['gerado_em']/1000,timezone.utc).strftime('%d/%m/%Y %H:%M UTC')),
             texto(f"Período: últimos {resumo['dias']} dias, limitado pela retenção do banco."), Spacer(1,.4*cm)]
    if encaminhamento:
        story += [texto('Destinatário sugerido: Patrulha Maria da Penha'),
                  texto('MINUTA PARA REVISÃO HUMANA. Este documento não foi enviado e não constitui acionamento, despacho oficial ou boletim de ocorrência.'),
                  texto('Finalidade: apresentar dados agregados para avaliação da equipe responsável. Sem nomes, contatos, texto dos relatos ou localização exata.'), Spacer(1,.4*cm)]
    story += [texto(resumo['aviso']),Spacer(1,.3*cm)]
    def tabela(cab, linhas):
        t=Table([[texto(x) for x in row] for row in [cab]+linhas],colWidths=[13*cm,3*cm],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eee6f8')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d2c7df')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
        story.extend([t,Spacer(1,.5*cm)])
    labels={'total':'Relatos recebidos','pendentes':'Visíveis sem verificação','verificados':'Visíveis verificados','ocultos':'Ocultos pela equipe'}
    tabela(['Situação','Quantidade'],[[labels[k],v] for k,v in resumo['indicadores'].items()])
    story.append(Paragraph('Tipos de situação',styles['Heading2']))
    tabela(['Tipo','Relatos'],[[TIPOS_POR_ID[k].label,v] for k,v in resumo['por_tipo'].items()] or [['Nenhum relato no período',0]])
    story.append(texto('Um relato pode conter mais de um tipo; a soma dos tipos pode superar o total. O relatório não inclui descrições individuais.'))
    story.append(Paragraph('Envios por dia (UTC)',styles['Heading2']))
    tabela(['Data de envio','Relatos'],list(resumo['por_dia'].items()) or [['Sem envios',0]])
    if encaminhamento:
        story += [Paragraph('Revisão e envio manual',styles['Heading2']),texto('Responsável pela revisão: ____________________________________'),texto('Providência proposta: _________________________________________'),texto('Data e assinatura: ___________________________________________'),texto('O responsável deve revisar os dados, a finalidade e o destinatário antes de qualquer envio pelo canal institucional autorizado.')]
    def pagina(canvas, doc):
        canvas.setFont('Helvetica',9);canvas.drawString(2*cm,1.2*cm,'Aurora | Dados agregados da comunidade');canvas.drawRightString(19*cm,1.2*cm,str(doc.page))
    SimpleDocTemplate(buf,topMargin=1.7*cm,bottomMargin=2*cm,title=titulo,author='Aurora').build(story,onFirstPage=pagina,onLaterPages=pagina)
    return buf.getvalue()
