# Aurora · MVP 03 — Rio Claro

Mapa colaborativo de segurança para mulheres em Rio Claro (SP), com chat para registrar situações sem identificação e os pontos da rede de apoio: onde registrar ocorrência, pedir medida protetiva, conversar com alguém ou ser atendida na saúde.

## Onde está cada coisa

O projeto está migrando de um arquivo HTML único para um app com servidor (FastAPI) e frontend em módulos. **As duas versões convivem:** a original continua publicada e é a referência de comportamento até cada parte ser migrada e verificada.

| Caminho      | Para quê                                                                                                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/`   | **Novo.** Servidor FastAPI: API em `/api/v1`, banco de dados, anonimização, classificação, provedores de IA e testes.                                                                       |
| `frontend/`  | **Novo.** O mesmo app dividido em módulos por área (`mapa/`, `relatos/`, `chatbot/`, `apoio/`, `dashboard/`, `moderacao/`, `observatorio/`, `shared/`). Sem framework e sem etapa de build. |
| `scripts/`   | `preparar_dados.py` e `preparar_mapa.py` (geram os dados) e `montar.py` (gera a versão original em arquivo único).                                                                          |
| `dados/`     | Dados agregados, rede de apoio e `osm/` (mapa de ruas do OpenStreetMap). Os dados brutos ficam fora (veja `dados/LEIA-ME-DADOS.md`).                                                        |
| `index.html` | **Versão original**, que o GitHub Pages publica. É uma cópia de `dist/aurora.html`.                                                                                                         |
| `src/`       | Código-fonte da versão original: `app.html`, `app.css`, `app.js`. Não editar durante a migração: é a referência.                                                                            |
| `vendor/`    | Leaflet (biblioteca do mapa) e sua licença.                                                                                                                                                 |
| `mobile/`    | App Android (Expo) que abre o Aurora e liga as notificações no celular. Veja `mobile/README.md`.                                                                                            |

## Como rodar a nova versão

Precisa de Python 3.11 ou mais novo. Na primeira vez, crie o ambiente e instale as dependências:

```
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt

```

(No Linux/macOS, troque `.venv/Scripts/python` por `.venv/bin/python`.)

Para subir o servidor, que já serve o app em `http://localhost:8000`:

```
.venv/Scripts/python -m uvicorn backend.main:app --port 8000 --no-access-log

```

- Na primeira execução, o servidor cria o banco `backend/database/aurora.db` (SQLite, fora do git) e carrega nele os arquivos de `dados/`. Depois de editar um arquivo de `dados/`, reinicie o servidor: na inicialização ele compara cada arquivo com o que já carregou e recarrega só o que mudou.

- `--no-access-log` evita que o servidor escreva o IP de quem acessa.

- A documentação da API fica em `http://localhost:8000/api/v1/docs`.

Testes (incluindo a comparação automática com o código original em JavaScript, que precisa do Node.js). Se o `test_texto.py` falhar, veja as
versões de Unicode: ele compara a normalização do Python com a do Node, e dá diferença quando as duas estão muito distantes (por exemplo,
Python 3.12, Unicode 15, com Node 22, Unicode 17). Confira com `python -c "import unicodedata; print(unicodedata.unidata_version)"` e
`node -e "console.log(process.versions.unicode)"`:

```
.venv/Scripts/python -m pytest

```

A nova versão também roda **sem servidor**, como site estático. Nesse caso ela lê `dados/` direto e guarda tudo no aparelho, como a versão original hospedada:

```
python -m http.server 8080 --bind 127.0.0.1

```

**Use sempre `--bind 127.0.0.1`.** Sem ele, o servidor estático responde para qualquer aparelho da mesma rede e entrega a pasta inteira do projeto, inclusive `backend/database/aurora.db` (os relatos) e os dados brutos de `dados/`, se estiverem na pasta. Esse modo é só para testar no próprio computador.

Depois abra `http://localhost:8080/frontend/`. A versão original continua em `http://localhost:8080/`.

### O que já passa pelo servidor (fase 1)

| Funcionalidade | Onde fica agora |
| --- | --- |
| Mapa, camadas, filtros, painel de área, trajeto, GPS, saída rápida | Frontend (igual à original) |
| Relatos: publicar, listar, apagar | **Servidor** (`/api/v1/relatos`). O texto é anonimizado de novo no servidor; quem publica recebe uma chave para apagar, guardada só no aparelho. |
| Dados oficiais (B.O.), pesquisa de percepção, geografia, rede de apoio | **Servidor**, cada tipo de evidência na sua rota e na sua tabela |
| Classificação automática | **Servidor**. Fica numa tabela separada do relato e não muda os tipos escolhidos pela usuária. |
| Extração do texto livre (IA) | Interface de provedor no servidor (`/api/v1/ia`). O provedor padrão são as mesmas regras de palavras-chave da versão original. Sem modelo de IA configurado, o texto do chat não sai do aparelho. |
| Moderação | **Servidor**, com contas individuais da equipe; ocultar, mostrar e verificar persistem no banco. |
| Votos e áreas acompanhadas | Ainda no aparelho. Sinalizações locais não entram na fila da equipe. |

Configurações pendentes de decisão com o Observatório ficam em variáveis `AURORA_*` (veja `backend/config.py`). O padrão de cada uma reproduz o comportamento atual: por exemplo, `AURORA_RELATOS_RETENCAO_DIAS` (padrão: não apagar) e `AURORA_RELATOS_PRECISAO_CRIADO` (padrão: hora exata).

## Painel de Moderação e equipe

A equipe dispõe de visão geral com cards e gráficos, filtros de período e revisão de relatos. Administradores também exportam relatórios PDF e minutas agregadas de encaminhamento para revisão e envio manual. O chatbot aparece somente na área pública.

**[Guia completo: instalação, primeiro administrador e uso passo a passo](docs/moderacao/README.md)**

O desenvolvedor cria **uma única conta inicial de administrador** no servidor. Essa pessoa entra no painel e cadastra o restante da equipe, sem depender de alterações no código.

```bash
.venv/bin/python -m backend.criar_admin
.venv/bin/python -m uvicorn backend.main:app --port 8000 --no-access-log
```

No Windows, use `.venv/Scripts/python`. O comando solicita usuário e senha sem exibir a senha no terminal, cria as tabelas que faltam e grava apenas um hash scrypt. Se já existir administrador, ele recusa criar outro e preserva as contas existentes. Execute apontando `AURORA_BANCO_URL` para o mesmo banco usado pelo servidor.

Abra `http://localhost:8000/moderacao` diretamente no navegador. Entre com a conta inicial, abra **Equipe** e cadastre cada pessoa com usuário, senha de pelo menos 12 caracteres e permissão:

| Permissão | O que pode fazer |
| --- | --- |
| Administrador | Revisar relatos, cadastrar moderadores e outros administradores, desativar/reativar moderadores. |
| Moderador | Ocultar, mostrar, verificar e retirar a verificação de relatos. Não pode listar nem cadastrar contas. |

Use senhas individuais e entregue a senha de cada pessoa por um canal privado. Contas administrativas não podem ser desativadas pelo painel, evitando perder o responsável. A chave compartilhada `AURORA_MODERACAO_CHAVE` foi substituída pelas contas individuais e não concede mais acesso.

As sessões usam cookie HttpOnly e SameSite=Strict, duram oito horas (`AURORA_SESSAO_HORAS`, entre 1 e 24) e sobrevivem a recargas. **Sair da moderação** revoga a sessão no servidor; desativar uma conta revoga todos os acessos dela. Em produção, use HTTPS e `AURORA_SESSAO_COOKIE_SEGURO=true`. O painel é servido na mesma origem da API. Há limite de tentativas de login por conta e por processo; aplicações com vários processos precisam de limitação compartilhada na infraestrutura.

O histórico de moderação registra usuário, ação e horário. As tabelas novas de credenciais e sessões são adicionadas na inicialização, preservando os relatos e a tabela de usuários existente. As ações antigas sem usuário continuam válidas.

- **Ocultar/Mostrar**: retira/devolve o relato às consultas públicas, incluindo os relatos do resumo do dashboard. Ocultar prevalece sobre o selo de verificação.
- **Verificar/Tirar verificação**: adiciona/remove o selo público da equipe.
- **Atualizar relatos**: lê novamente o banco. O painel inclui relatos antigos dentro da retenção; o mapa mantém sua janela de dias.
- Votos continuam locais, sem virar denúncias compartilhadas. A versão estática mantém a moderação local de demonstração. Quem envia relatos continua sem precisar de conta.

API da equipe: `POST /api/v1/usuarios/entrar`, `POST /api/v1/usuarios/sair`, `GET /api/v1/usuarios/eu`, `GET/POST /api/v1/usuarios/equipe` e `POST /api/v1/usuarios/equipe/{id}/ativo`. Requisições que alteram acesso ou moderação exigem o cabeçalho `X-Aurora-Equipe: 1`, além da sessão quando aplicável. O servidor verifica o papel em cada operação.

Testes de API: `.venv/bin/python -m pytest backend/tests/test_api_equipe.py backend/tests/test_api_moderacao.py`. Testes de navegador (Playwright e Chromium): `.venv/bin/python -m pytest tests/e2e/test_moderacao.py`. Os testes usam contas fictícias, servidor e banco temporários.

## Link publicado × arquivo hospedado

O mesmo código roda nos dois lugares e muda de comportamento sozinho. O mapa de ruas (ruas, avenidas, ferrovia, rios, lagos, parques e campi de Rio Claro, do OpenStreetMap) e a rede de apoio ficam guardados dentro do próprio app. Por isso aparecem também no link do claude.ai, que bloqueia servidores de mapa externos.

## Onde pedir ajuda no mapa

Ícones redondos mostram 14 pontos, com endereço, horário, telefone, fonte e botão “Como chegar”:

- **Registrar ocorrência e medida protetiva**: Delegacia de Defesa da Mulher (Av. 23, 1300, com a Delegacia Seccional no mesmo prédio) e Guarda Civil Municipal com a Patrulha Maria da Penha (Rua 12, 26).

- **Conversar e ter acompanhamento**: Secretaria Municipal da Mulher (Rua 7, 830), CREAS (Rua 6, 640) e cinco CRAS. O CRAS Panorama fica só na lista porque não deu para confirmar a posição.

- **Orientação jurídica e Justiça**: Defensoria Pública (Rua 1, 659) e Anexo de Violência Doméstica do TJSP (Rua 7, 830, no prédio da Secretaria da Mulher).

- **Saúde 24 horas**: pronto-socorro ginecológico e obstétrico (Av. 15 com Rua 2, referência depois de violência sexual), UPA 29 e PA Jardim Chervezon.

Toque numa área do mapa e o painel mostra a ajuda mais perto para registrar ocorrência, para conversar e para a saúde. A caixa “Onde pedir ajuda” na legenda liga e desliga a camada. A página Apoio traz a mesma lista, com “Ver no mapa” em cada serviço.

Como cada ponto foi posicionado:

- **Exata**: o prédio está mapeado no OpenStreetMap com o mesmo endereço.

- **Pelo endereço**: calculado a partir do endereço oficial, usando as esquinas citadas e números de prédios já mapeados na mesma rua para achar a quadra e o lado da rua. Margem de uns 30 metros.

- **Aproximada** (CRAS Mãe Preta e CRAS Jardim Brasília): margem de até 100 metros. O ícone tem borda tracejada.

Casas-abrigo nunca aparecem, para proteger quem está nelas. O encaminhamento para acolhimento seguro é feito pela rede, por exemplo pelo CREAS.

Atenção a uma mudança recente: o CREAS saiu da Rua 1, 1809 em junho de 2024 e hoje atende na Rua 6, 640. O endereço antigo agora é do Conselho Tutelar, e algumas listas oficiais ainda mostram o endereço velho.

## Alertas ao vivo e notificações

Como os avisos do Waze, cada relato vira um **alerta com título padrão**, escolhido pelo tipo (o mais grave, se houver mais de um):
assédio verbal = "Potencial assediador na área", perseguição = "Possível perseguidor na área", roubo ou furto = "Roubo ou furto na área",
e assim por diante (`backend/services/alertas.py` e `frontend/relatos/alerta.js`, com um teste que confere que os dois batem).
"Rua escura ou deserta" é condição do lugar, não um acontecimento: não vira alerta.

- **No mapa:** cada relato aparece no painel da área (e em "Meus alertas") com o título padrão do tipo, por exemplo "Potencial assediador na área",
  e, embaixo, só as **roupas e os acessórios** que a usuária citou: "Visto com: camiseta preta, calça roxa, boné azul"
  (`frontend/relatos/acessorios.js`). Isso sai de listas fixas de peças e cores: nome, altura, cor da pele, cabelo, tatuagem,
  idade, placa e o resto do texto nunca aparecem, mesmo que estejam no relato (o servidor ainda tira a descrição física antes de gravar).
  O texto inteiro fica guardado e só a moderação o lê.

- **No chat:** se a mulher só diz "fui assediada", sem apontar que foi algo falado, a Aurora não chuta "Assédio verbal": pergunta o que aconteceu
  (assédio pode ser verbal, uma abordagem, exposição, violência física...).

- **No celular:** quem acompanha uma área ("Acompanhar" no mapa) recebe uma notificação quando alguém relata algo nela, pelo app de
  `mobile/` (Expo Push). A notificação traz só o título padrão e o nome da área, nunca a descrição. Limite de uma por aparelho a cada
  10 minutos. O servidor guarda só o token do aparelho e as áreas (tabela `dispositivos_push`).
- **Telegram da patrulha:** com `AURORA_TELEGRAM_BOT_TOKEN` e `AURORA_TELEGRAM_CHAT_IDS` preenchidos (`.env` ou segredos do Render), cada relato
  novo, de qualquer tipo, vira uma mensagem no(s) grupo(s) do Telegram: título, área, ocorrência, quando, link do mapa e a descrição já limpa pela
  anonimização (`backend/services/telegram.py`). O ponto é o centro da célula de ~150 m, não o endereço exato. Sem os dois, fica desligado.
  Para criar: fale com o @BotFather (`/newbot`), adicione o bot ao grupo da patrulha e pegue o id do grupo.
- **Modo atenção (app fechado):** quem liga em *Meus alertas* recebe uma notificação quando surge um alerta a até 500 m, mesmo com o app
  fechado. O app baixa `GET /api/v1/alertas` e compara com o GPS **no próprio celular**: a localização não vai para o servidor.
  Detalhes e ajustes de bateria (Xiaomi) em `mobile/README.md`.

- **Cuidado:** o alerta é de uma pessoa, sem verificação. Por isso o título diz "potencial" e o relato aparece como não verificado, e o
  alerta só vale por algumas horas (6 h no `GET /alertas`). Só as roupas e os acessórios citados aparecem no alerta; nada disso vai na notificação. Definir se e como
  o grupo verifica esses relatos é decisão pendente com o Observatório.

## Site no ar pelo GitHub Pages

1. No repositório, vá em **Settings → Pages**.

2. Em _Branch_, escolha `main` e a pasta `/ (root)`. Clique em **Save**.

3. Em um ou dois minutos o site fica em `https://SEU-USUARIO.github.io/NOME-DO-REPOSITORIO/`.

O aviso por GPS precisa de endereço `https://` (o GitHub Pages já dá) e da permissão de localização do navegador. Ele funciona enquanto a página está aberta.

## Servidor e banco na nuvem (sem depender de um computador ligado)

O servidor já aceita **Postgres**: não há o que reescrever, só trocar a variável `AURORA_BANCO_URL` (o SQLAlchemy cuida do resto).
Sem ela, continua o SQLite local de sempre. Duas peças precisam ficar no ar: o **Postgres** (onde ficam os relatos) e o **servidor**
(que serve o site e a API). Só o banco na nuvem não basta: sem o servidor, o app continuaria dependendo do seu computador.
O caminho escolhido é **Neon** (banco) + **Render** (servidor), ambos com plano grátis.

**1. Banco no Neon**

1. Crie a conta em [neon.com](https://neon.com) (dá para entrar com Google ou GitHub).
2. *Create project*: nome `aurora` e região **AWS US East 1 (N. Virginia)**, a mesma do Render.
3. Em *Connect*, copie a *connection string* (começa com `postgresql://`). Guarde só para colar no Render: nada de arquivo do git.

**2. Servidor no Render**

1. Crie a conta em [render.com](https://render.com) (pode ser com o GitHub).
2. *New → Blueprint* e informe o repositório `https://github.com/Tauari/Projeto-2semestre-Fatec` (é público). Escolha a branch que tem o
   `render.yaml` (hoje `branch-tauari`; depois que for para a `main`, use a `main`).
3. O Render lê o `render.yaml` e pergunta os dois segredos: `AURORA_BANCO_URL` (a string do Neon) e `AURORA_GROQ_API_KEY` (a chave do Groq).
   Cole e clique em *Apply*. Eles ficam guardados no Render, nunca no git. Para usar só as regras (sem IA), troque `AURORA_IA_PROVEDOR` para
   `heuristica` em *Environment*.
4. Espere o primeiro build (alguns minutos). Na primeira subida o servidor cria as tabelas e carrega os arquivos de `dados/` sozinho.
5. Quando o serviço ficar *Live*, abra `https://NOME.onrender.com/api/v1/saude`: deve responder `{"status":"ok", ...}`.
6. **Endereço fixo:** cole esse endereço no app Aurora (⚙) no lugar do link do túnel. O `cloudflared` deixa de ser necessário.

A cada `git push` na branch escolhida o Render publica de novo. Se algo não subir, veja a aba *Logs* do serviço: o erro mais comum é a
string do banco colada errada.

**3. pgAdmin (opcional)** serve para **olhar e administrar** o banco da nuvem pelo computador, não para hospedá-lo. Em *Register → Server*,
preencha Host, Porta (5432), Database, Username e Password da string do Neon e, na aba *SSL*, use **Require**. As tabelas ficam em
*Databases → banco → Schemas → public → Tables* (`relatos`, `dispositivos_push`, `classificacoes`...).

Cuidados: no plano grátis o servidor do Render **dorme** quando ninguém usa (o primeiro acesso demora até cerca de 1 minuto; abra o site uns
10 minutos antes da apresentação), a API passa a ser pública (ainda não há limite de envios por pessoa) e os relatos passam a ficar num
servidor de terceiros, o que entra na conversa de LGPD com o Observatório. Os relatos de teste do SQLite local não migram sozinhos; o banco
novo começa vazio. Os dados são os mesmos de `dados/`, que o servidor carrega a cada subida.

### Painel da Secretaria (equipe) na nuvem

A moderação e a visão geral da Secretaria ficam em `/moderacao` e exigem login. Não existe senha padrão: o primeiro responsável é criado
com `python -m backend.criar_admin`, que grava no banco apontado por `AURORA_BANCO_URL`. No Render grátis não há terminal, então rode esse comando
**no seu computador**, com a string do Neon em `AURORA_BANCO_URL` no `.env`, antes de entrar pela primeira vez no site do Render. O `render.yaml` já liga
`AURORA_SESSAO_COOKIE_SEGURO`, porque o login só funciona por HTTPS. O guia completo está em `docs/moderacao/README.md`.

## Como atualizar os dados

Precisa de Python 3 (sem bibliotecas extras).

1. Coloque os arquivos brutos em `dados/` (eles não vão para o GitHub; veja `dados/LEIA-ME-DADOS.md`).

2. Rode `python scripts/preparar_dados.py`, depois `python scripts/preparar_mapa.py` e por fim `python scripts/montar.py`.

3. A versão original sai em `dist/aurora.html`. Copie para `index.html` antes de enviar ao GitHub, para o site no ar ser atualizado.

Para mudar um endereço, telefone ou horário da rede de apoio, edite `dados/rede-de-apoio.json` num editor de texto e rode só `python scripts/montar.py` (depois copie `dist/aurora.html` para `index.html`). Cada serviço tem `nome`, `end` (endereço), `bairro`, `tel`, `horario`, `lat` e `lng` (posição), `precisao` (`exata`, `endereco` ou `aproximada`) e `fontes`. Um serviço sem `lat` e `lng` aparece só na página Apoio. Para achar a posição de um endereço novo, abra openstreetmap.org, clique com o botão direito no prédio e escolha “Mostrar endereço”: a latitude e a longitude aparecem no painel.

O mapa de ruas foi extraído do OpenStreetMap em 24/09/2026 e não precisa ser atualizado por enquanto. A consulta usada está em `dados/osm/consulta-overpass.txt`.

O `scripts/preparar_dados.py` imprime um relatório de conferência (totais, células, áreas citadas) para vocês checarem os números.

## Como os dados entram no mapa

- **Relatos**: enviados pelo chat. Ficam 30 dias no mapa, por célula de cerca de 1 km, nunca num ponto exato. Três sinalizações de “informação falsa” tiram um relato do mapa até a moderação revisar.

- **Percepção**: as 51 respostas da pesquisa. As regiões citadas em texto livre foram ligadas aos bairros da base de B.O. Unesp entrou como Bela Vista; Lago Azul entre Vila Operária, Jardim Primavera e Vila Aparecida; Rodoviária no Jardim Claret. Shopping, cemitério, Av. 40, Av. Brasil, avenida do Fórum e Vila Santo Antônio ficaram fora do mapa por falta de posição confiável.

- **Histórico B.O.**: 683 registros (673 de violência doméstica, 2 feminicídios, 8 tentativas), jan/2025 a abr/2026. O mapa mostra os 524 que têm bairro com coordenada própria. Ficam fora 84 da zona rural, 42 sem bairro, 28 de bairros com coordenada genérica e 5 sem nome de bairro.

- **Onde pedir ajuda**: serviços públicos, com endereço exato. É a única camada com pontos exatos, porque são endereços públicos e não expõem ninguém.

Violência doméstica acontece sobretudo dentro de casa. Por isso o app apresenta a camada de B.O. como “onde a rede de apoio é mais necessária”, e não como área para evitar na rua.

## O que falta para um lançamento público

1. **Banco compartilhado.** Em andamento na nova versão: o servidor FastAPI (`backend/`) já guarda os relatos num banco (SQLite por padrão; para Postgres, basta trocar `AURORA_BANCO_URL`). Ainda falta hospedar o servidor e migrar os votos para ele.
2. **Moderação de verdade**: definir com o Observatório quem modera e em quanto tempo.

3. **Confirmar a rede de apoio com cada serviço**: endereços, telefones e horários foram reunidos em 24/09/2026 em páginas oficiais, mas algumas listas estavam desatualizadas. Pontos a checar primeiro: o horário da DDM, onde funciona o plantão da Polícia Civil fora do horário da DDM (ficou fora do mapa por falta de endereço confirmado), se o CREAS 2 (Rua 8, 3131) ainda existe e a posição do CRAS Panorama. A Secretaria da Mulher deve mudar para a Av. Visconde do Rio Claro com a Av. 26 no início de 2027.

4. **LGPD**: termo de uso, política de privacidade e um canal para pedir remoção de relatos. Relatos podem conter dados sensíveis mesmo com a limpeza automática.

5. **Notificações com o app fechado**: exige transformar o site em PWA com service worker.

## Créditos

Mapa: Leaflet (licença BSD-2). Dados do mapa © colaboradores do OpenStreetMap, licença ODbL. Fontes: Atkinson Hyperlegible e Bricolage Grotesque (Google Fonts). Rede de apoio: Prefeitura de Rio Claro, Tribunal de Justiça de SP, Defensoria Pública de SP e Fundação Municipal de Saúde de Rio Claro.

Demonstração atualizada: [vídeo completo, prints e PDFs do novo painel](entregas/painel-atualizado/README.md).
