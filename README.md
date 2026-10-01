# Aurora · MVP 02 — Rio Claro

Mapa colaborativo de segurança para mulheres em Rio Claro (SP), com chat para registrar situações sem identificação e os pontos da rede de apoio: onde registrar ocorrência, pedir medida protetiva, conversar com alguém ou ser atendida na saúde.

## Onde está cada coisa

O projeto está migrando de um arquivo HTML único para um app com servidor (FastAPI) e frontend em módulos. **As duas versões convivem:** a original continua publicada e é a referência de comportamento até cada parte ser migrada e verificada.

| Caminho | Para quê |
| --- | --- |
| `backend/` | **Novo.** Servidor FastAPI: API em `/api/v1`, banco de dados, anonimização, classificação, provedores de IA e testes. |
| `frontend/` | **Novo.** O mesmo app dividido em módulos por área (`mapa/`, `relatos/`, `chatbot/`, `apoio/`, `dashboard/`, `moderacao/`, `observatorio/`, `shared/`). Sem framework e sem etapa de build. |
| `scripts/` | `preparar_dados.py` e `preparar_mapa.py` (geram os dados) e `montar.py` (gera a versão original em arquivo único). |
| `dados/` | Dados agregados, rede de apoio e `osm/` (mapa de ruas do OpenStreetMap). Os dados brutos ficam fora (veja `dados/LEIA-ME-DADOS.md`). |
| `index.html` | **Versão original**, que o GitHub Pages publica. É uma cópia de `dist/aurora.html`. |
| `src/` | Código-fonte da versão original: `app.html`, `app.css`, `app.js`. Não editar durante a migração: é a referência. |
| `vendor/` | Leaflet (biblioteca do mapa) e sua licença. |

## Como rodar a nova versão

Precisa de Python 3.11 ou mais novo. Na primeira vez, crie o ambiente e instale as dependências:

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
```

(No Linux/macOS, troque `.venv/Scripts/python` por `.venv/bin/python`.)

Para subir o servidor, que já serve o app em `http://localhost:8000`:

```bash
.venv/Scripts/python -m uvicorn backend.main:app --port 8000 --no-access-log
```

- Na primeira execução, o servidor cria o banco `backend/database/aurora.db` (SQLite, fora do git) e carrega nele os arquivos de `dados/`. Depois de editar um arquivo de `dados/`, reinicie o servidor: na inicialização ele compara cada arquivo com o que já carregou e recarrega só o que mudou.
- `--no-access-log` evita que o servidor escreva o IP de quem acessa.
- A documentação da API fica em `http://localhost:8000/api/v1/docs`.

Testes (243, incluindo a comparação automática com o código original em JavaScript, que precisa do Node.js):

```bash
.venv/Scripts/python -m pytest
```

A nova versão também roda **sem servidor**, como site estático. Nesse caso ela lê `dados/` direto e guarda tudo no aparelho, como a versão original hospedada:

```bash
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
| Votos, moderação, áreas acompanhadas | Ainda no aparelho. A tela de moderação fica escondida quando há servidor, até a moderação ser migrada. |

Configurações pendentes de decisão com o Observatório ficam em variáveis `AURORA_*` (veja `backend/config.py`). O padrão de cada uma reproduz o comportamento atual: por exemplo, `AURORA_RELATOS_RETENCAO_DIAS` (padrão: não apagar) e `AURORA_RELATOS_PRECISAO_CRIADO` (padrão: hora exata).

## Link publicado × arquivo hospedado

O mesmo código roda nos dois lugares e muda de comportamento sozinho. O mapa de ruas (ruas, avenidas, ferrovia, rios, lagos, parques e campi de Rio Claro, do OpenStreetMap) e a rede de apoio ficam guardados dentro do próprio app. Por isso aparecem também no link do claude.ai, que bloqueia servidores de mapa externos.

| | Link no claude.ai | Arquivo hospedado |
| --- | --- | --- |
| Mapa de ruas | Sim | Sim, o mesmo mapa |
| Onde pedir ajuda (pontos da rede de apoio) | Sim | Sim |
| Relatos compartilhados entre pessoas | Sim, para quem tem acesso ao link | Não. Ficam só no aparelho |
| IA no chat (entende texto livre e tira dados pessoais) | Sim, usando a conta Claude de quem escreve | Não. Usa palavras-chave e regras automáticas |
| Aviso ao entrar numa área (GPS) | Não. O ambiente bloqueia localização | Sim, com a página aberta, e diz qual ajuda está mais perto |
| “Mostrar onde estou” com a ajuda mais perto | Não | Sim |
| Painel de moderação | Só para quem pode editar o link | Local, para testes |

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

## Site no ar pelo GitHub Pages

1. No repositório, vá em **Settings → Pages**.
2. Em *Branch*, escolha `main` e a pasta `/ (root)`. Clique em **Save**.
3. Em um ou dois minutos o site fica em `https://SEU-USUARIO.github.io/NOME-DO-REPOSITORIO/`.

O aviso por GPS precisa de endereço `https://` (o GitHub Pages já dá) e da permissão de localização do navegador. Ele funciona enquanto a página está aberta.

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

1. **Banco compartilhado.** Em andamento na nova versão: o servidor FastAPI (`backend/`) já guarda os relatos num banco (SQLite por padrão; para Postgres, basta trocar `AURORA_BANCO_URL`). Ainda falta hospedar o servidor e migrar votos e moderação para ele.
2. **Moderação de verdade**: definir com o Observatório quem modera e em quanto tempo.
3. **Confirmar a rede de apoio com cada serviço**: endereços, telefones e horários foram reunidos em 24/09/2026 em páginas oficiais, mas algumas listas estavam desatualizadas. Pontos a checar primeiro: o horário da DDM, onde funciona o plantão da Polícia Civil fora do horário da DDM (ficou fora do mapa por falta de endereço confirmado), se o CREAS 2 (Rua 8, 3131) ainda existe e a posição do CRAS Panorama. A Secretaria da Mulher deve mudar para a Av. Visconde do Rio Claro com a Av. 26 no início de 2027.
4. **LGPD**: termo de uso, política de privacidade e um canal para pedir remoção de relatos. Relatos podem conter dados sensíveis mesmo com a limpeza automática.
5. **Notificações com o app fechado**: exige transformar o site em PWA com service worker.

## Créditos

Mapa: Leaflet (licença BSD-2). Dados do mapa © colaboradores do OpenStreetMap, licença ODbL. Fontes: Atkinson Hyperlegible e Bricolage Grotesque (Google Fonts). Rede de apoio: Prefeitura de Rio Claro, Tribunal de Justiça de SP, Defensoria Pública de SP e Fundação Municipal de Saúde de Rio Claro.
