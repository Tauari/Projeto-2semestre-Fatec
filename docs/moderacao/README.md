# Moderação e gestão da equipe — passo a passo

Este guia descreve a versão com FastAPI e contas individuais. O ZIP de demonstração está em `entregas/moderacao/aurora-video-e-prints.zip`, na raiz do repositório, com dados fictícios.

## 1. Obter o código

```bash
git clone --branch branch-arthur https://github.com/oalfinho/Projeto-Aurora.git
cd Projeto-Aurora
```

Se você já tem esse fork, salve suas alterações antes de mudar de branch e execute `git switch branch-arthur` e `git pull --ff-only origin branch-arthur`.

## 2. Preparar o ambiente

Requisitos: Python 3.11 ou superior. Na raiz do projeto:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

Windows (PowerShell):

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
```

Nos comandos seguintes, Windows deve substituir `.venv/bin/python` por `.\.venv\Scripts\python.exe`.

## 3. Criar o primeiro responsável

```bash
.venv/bin/python -m backend.criar_admin
```

O desenvolvedor informa um usuário (3–64 caracteres: letras, números, ponto, hífen ou sublinhado), uma senha de 12–128 caracteres e a confirmação. A senha não aparece durante a digitação. Não existe senha administrativa padrão.

Esse comando cria apenas o primeiro administrador. Se já existir um, ele recusa a operação sem substituir contas. Entregue o acesso ao responsável por canal privado. Não coloque senhas no GitHub.

Por padrão o banco é SQLite em `backend/database/aurora.db`. Se usar `AURORA_BANCO_URL`, configure o mesmo valor ao criar o administrador e ao executar o servidor. Faça backup de um banco existente antes de atualizar. A inicialização adiciona as tabelas novas; não apague o banco para aplicar a atualização.

## 4. Iniciar e entrar

```bash
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Abra **http://localhost:8000/moderacao**. O endereço encaminha para `/#moderacao`. A equipe acessa o painel diretamente por esse endereço. Entre com o usuário e a senha criados. Use sempre o mesmo endereço do servidor durante a sessão.

O FastAPI serve o frontend e a API juntos. **GitHub Pages e `python -m http.server` não executam esse backend**: o modo estático é uma demonstração local, sem a gestão compartilhada da equipe. Enviar código ao GitHub não publica automaticamente o servidor.

## 5. Visão geral, relatórios e equipe

Ao entrar, a equipe vê a **Visão geral**, sem o chatbot. O assistente de registro continua na área pública.

- Escolha os últimos 7, 30, 90 ou 365 dias, pela **data de envio em UTC**, respeitando a retenção do banco.
- Os cards mostram total recebido, visíveis sem verificação, visíveis verificados e ocultos. Essas três categorias de estado somam o total.
- Os gráficos mostram tipos, até oito regiões aproximadas e os últimos 14 dias com envios no período. Um relato pode ter mais de um tipo. Concentração de relatos não é uma classificação de risco.
- **Atualizar indicadores** relê os dados. A aba **Relatos** mantém as ações de revisão.
- Administradores podem **Baixar relatório PDF**, gerado pelo servidor com os mesmos filtros. Moderadores podem consultar o painel, mas não exportar.
- **Preparar encaminhamento → Baixar minuta para revisão** gera um PDF com destinatário sugerido Patrulha Maria da Penha, contagens agregadas e campos de revisão, providência, data e assinatura. **Não envia mensagem, não aciona viatura e não é um despacho oficial.** O responsável revisa e envia pelo canal institucional autorizado. Não há integração oficial configurada.
- Os PDFs não incluem descrições, nomes de usuárias, IDs dos relatos ou localização exata. Relatos, boletins oficiais e pesquisa não são somados como se fossem a mesma evidência.

Ao atualizar uma instalação existente, execute novamente `python -m pip install -r backend/requirements.txt` dentro do ambiente virtual: a geração de PDF usa ReportLab.

### Cadastrar a equipe

Entre como administrador e abra **Equipe**. Preencha usuário, senha individual e permissão; clique em **Cadastrar pessoa**.

| Papel | Permissões |
| --- | --- |
| Administrador | Consultar indicadores, exportar PDFs, revisar relatos, cadastrar moderadores e administradores e desativar/reativar moderadores. |
| Moderador | Consultar indicadores e revisar relatos. Não exporta PDFs nem acessa a gestão da equipe. |

A pessoa cadastrada entra no mesmo endereço com sua própria conta. Desativar um moderador revoga imediatamente todas as sessões dele; reativar permite um novo login. O painel não desativa administradores, protegendo o acesso do responsável. Troca/recuperação de senha ainda não tem fluxo no painel.

## 6. Revisar relatos

Na aba **Relatos**:

- **Ocultar** retira o relato das consultas públicas; ele continua na fila privada da equipe.
- **Mostrar** devolve o relato às consultas públicas, respeitando as janelas de tempo e retenção.
- **Verificar** adiciona o selo da equipe; **Tirar verificação** remove o selo. Um relato oculto continua oculto mesmo verificado.
- **Atualizar relatos** consulta novamente o banco.

O painel mostra o texto do relato para revisão. A apresentação pública com títulos de alertas e acessórios foi preservada. Ações são gravadas no banco com o usuário responsável e o horário. Os votos continuam locais e não formam uma fila de denúncias compartilhada.

Para testar manualmente, registre um relato fictício no app, revise-o no painel e confira o mapa em outra janela. Depois desative uma conta de moderador e confirme que ela perdeu acesso. Não use dados pessoais reais na demonstração.

## 7. Sessão, configuração e hospedagem

O login usa cookie HttpOnly e SameSite=Strict. A sessão dura 8 horas por padrão; `AURORA_SESSAO_HORAS` aceita 1 a 24. **Sair da moderação** revoga a sessão no servidor. Recarregar a página mantém uma sessão válida.

Em hospedagem pública, use HTTPS e `AURORA_SESSAO_COOKIE_SEGURO=true`, armazenamento persistente para o banco e frontend/API na mesma origem. Em HTTP local mantenha esse parâmetro falso, senão o navegador não envia o cookie. O limite de tentativas de login é por processo; instalações com vários processos precisam de limitação compartilhada na infraestrutura.

A variável antiga `AURORA_MODERACAO_CHAVE` não concede acesso. As senhas são armazenadas como hash scrypt. O cadastro público de relatos continua anônimo e não exige conta.

## 8. Problemas comuns

- **Já existe administrador:** use a conta existente; novos administradores são cadastrados por ela em Equipe.
- **Login não funciona:** confira usuário/senha, conta ativa, mesmo banco no comando e no servidor e cookie seguro compatível com HTTP/HTTPS.
- **Não aparece Equipe:** confira se entrou como administrador, e não como moderador.
- **Sem relatos:** publique um relato de teste no servidor correto; dados do modo estático ficam no navegador.
- **Limite de tentativas:** aguarde a janela de bloqueio (5 minutos) e tente novamente.
- **Site publicado continua antigo:** o GitHub Pages serve a versão estática; é necessário hospedar e executar o FastAPI para usar contas e moderação compartilhada.

## 9. Testes

API e regressões:

```bash
.venv/bin/python -m pytest backend/tests
```

Testes de navegador opcionais (instalação explícita de ferramentas de desenvolvimento):

```bash
.venv/bin/python -m pip install playwright
.venv/bin/python -m playwright install chromium
.venv/bin/python -m pytest tests/e2e/test_moderacao.py
```

Os testes E2E usam banco e servidor temporários, com contas fictícias, em desktop e celular. A comparação Unicode de `backend/tests/test_texto.py` pode falhar quando Python e Node usam tabelas Unicode diferentes; isso já ocorria antes da Moderação. Não indica sucesso total da suíte.

### Resultado da verificação desta entrega (17/11/2026)

Na cópia integrada do fork: **394 testes passaram e 1 falhou**, executando backend e os 4 cenários E2E de desktop/celular juntos. A única falha foi `test_normalizar_todos_os_caracteres_um_a_um`, a incompatibilidade Unicode preexistente descrita acima. A sintaxe dos módulos JavaScript alterados e `git diff --check` passaram. Não há etapa de build do frontend nem comandos de lint/type-check configurados para essa entrega. Hospedagem em produção não foi realizada nem validada.

### API do painel

`GET /api/v1/moderacao/resumo?dias=30` exige sessão da equipe. `GET /api/v1/moderacao/relatorio.pdf?dias=30` exige administrador; acrescente `&encaminhamento=true` para a minuta. O período aceita 1–365 dias; respostas privadas usam `Cache-Control: no-store`.

### Verificação do novo painel (18/11/2026)

Após a atualização dos cenários para a abertura na Visão geral, **6 testes E2E passaram**, cobrindo login, equipe, revogação, revisão, indicadores, PDFs, ausência de chatbot na Moderação e retorno à área pública, em PC e celular. Os **14 testes de API/configuração** (`test_api_painel_equipe.py` e `test_api_sistema.py`) também passaram, assim como a sintaxe JavaScript e `git diff --check`. A falha Unicode preexistente continua sendo uma limitação da suíte geral.

[Vídeo atualizado, prints e PDFs de exemplo](../../entregas/painel-atualizado/README.md). Todo o material usa dados fictícios; não houve implantação em produção.
