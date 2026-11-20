# Aurora — painel atualizado, vídeo e prints

Demonstração de 18/11/2026 com dados fictícios e banco isolado. O celular é uma simulação de navegador móvel (390 × 844), não uma gravação de aparelho físico. Os vídeos não têm narração.

## Baixar

- [Vídeo completo atualizado — mulheres e administradores, PC e celular](plataforma-atualizada.mp4?raw=true)
- [Vídeo curto — novo painel, PC e celular](painel-atualizado.mp4?raw=true)
- [Print do PC](painel-pc.png)
- [Print do celular](painel-celular.png)
- [Relatório PDF de exemplo](relatorio-exemplo.pdf)
- [Minuta PDF de exemplo](minuta-exemplo.pdf)
- [ZIP com todos os arquivos](aurora-painel-video-prints.zip?raw=true)

O vídeo completo dura aproximadamente 1min59s. A sequência é:

| Início | Fluxo |
| --- | --- |
| 00:00 | Área pública para mulheres no PC: mapa e registro guiado |
| 00:43 | Área pública para mulheres no celular simulado |
| 01:27 | Administrador no PC: indicadores, filtros, gráficos e PDFs |
| 01:43 | Administrador no celular simulado: painel e documentos |

Os dois trechos da área pública são da demonstração anterior, cuja funcionalidade foi preservada. Os trechos administrativos foram gravados novamente com o painel atualizado, sem o chatbot. Os prints são capturas de página inteira; a barra móvel fixa aparece na posição do viewport.

## O que mudou

- Visão geral como primeira tela da equipe, com cards de relatos recebidos, a revisar, verificados e ocultos.
- Gráficos de tipos de situação, regiões aproximadas e envios por dia; filtro de 7, 30, 90 e 365 dias.
- Chatbot e botão de registrar relato ocultos na Moderação; disponíveis na área pública.
- Download de relatório consolidado em PDF para administradores.
- Preparação de uma minuta agregada para revisão humana, com destinatário sugerido Patrulha Maria da Penha.

**A minuta não é enviada automaticamente, não aciona viatura e não constitui despacho oficial.** Não há integração oficial com a Patrulha configurada. Os PDFs excluem textos dos relatos e dados pessoais. Os exemplos deste pacote usam somente dados fictícios.

## Executar e conferir

Siga o [guia completo da Moderação](../../docs/moderacao/README.md), incluindo instalação das dependências atualizadas (ReportLab), criação do primeiro responsável e execução do FastAPI. O GitHub armazena o código e os arquivos; este envio não hospeda o backend.

Verificações finais: 14 testes de API/configuração e 6 cenários de navegador passaram. A suíte geral ainda apresenta a incompatibilidade Unicode preexistente entre Python e Node, descrita no guia.
