# Aurora no celular (app Expo)

App Android que abre o Aurora dentro de um WebView e liga as **notificações na barra do celular**. A pessoa cola o link do
Aurora na primeira vez (o botão ⚙, no canto de baixo à esquerda, troca o link depois).

## Como funciona

1. O app pede permissão de notificação e pega o **token do Expo Push** do aparelho.
2. Antes de a página carregar, ele cria `window.AuroraApp = { plataforma, pushToken, areaInicial }`.
3. A página (`frontend/shared/push.js`) manda o token e as áreas que a pessoa acompanha para `POST /api/v1/push/dispositivos`.
4. Quando alguém relata algo numa dessas áreas, o servidor manda a notificação pelo Expo Push
   (`backend/services/push.py`): título padrão do tipo, por exemplo **"Potencial assediador na área"**, e o nome da área no corpo.
   Tocar na notificação abre a área no mapa.

O servidor guarda só o token e as áreas (sem nome, e-mail, IP nem ligação com os relatos). A descrição que a usuária escreveu
(roupa, por exemplo) **nunca vai na notificação**. Cada aparelho recebe no máximo uma notificação a cada 10 minutos
(`AURORA_PUSH_INTERVALO_MIN`), e quem enviou o relato não é avisado dele. `AURORA_PUSH_ATIVO=false` desliga tudo.

## Montar o APK (uma vez)

Você precisa de **Node 22 ou mais novo** (`node --version`) e de uma conta grátis em [expo.dev](https://expo.dev). O Expo SDK 58
e o `eas-cli` não rodam no Node 18 que vem em algumas distribuições Linux.

Neste computador o Node 22 está em `~/.local/node` e não entra sozinho no `PATH`. Em cada terminal novo, antes dos comandos:

```bash
export PATH=$HOME/.local/node/bin:$PATH
```

```bash
cd mobile
npm install
npx eas-cli login
npx eas-cli init
```

As dependências já foram instaladas e conferidas aqui (`npx expo-doctor`: 20 de 20 verificações; `npx expo export --platform android`:
o JavaScript compila; `npx expo prebuild`: o projeto Android é gerado com as notificações e o plugin do Firebase). O que ainda não foi
feito é o `eas build` e o teste num celular de verdade.

O `eas init` cria o projeto na sua conta e grava o `projectId` no `app.json` (sem ele o app não consegue pegar o token).
Se ele pedir para adicionar o `projectId` à mão, coloque em `app.json`, em `expo.extra.eas.projectId`.

### Notificações no Android precisam do Firebase (FCM)

O Android só recebe push por meio do Firebase Cloud Messaging. É grátis, mas é um passo seu, numa conta Google:

1. Em [console.firebase.google.com](https://console.firebase.google.com), crie um projeto e adicione um **app Android** com o
   pacote `br.fatec.aurora` (o mesmo de `app.json`). Baixe o **`google-services.json`** e coloque em `mobile/`.
   Ele fica fora do git (`mobile/.gitignore`).
2. Em *Configurações do projeto → Contas de serviço*, clique em **Gerar nova chave privada** e guarde o JSON.
3. Envie essa chave para o Expo: `npx eas-cli credentials`, escolha *Android*, o perfil *preview* e a opção de
   **FCM V1 service account key** para notificações push.
4. Envie o `google-services.json` ao EAS como variável de arquivo: `npx eas-cli env:create` e responda: nome
   `GOOGLE_SERVICES_JSON`, tipo `file`, visibilidade `secret`, ambiente `preview`, valor `./google-services.json`.
   O `app.config.js` lê essa variável no build.

### Gerar e instalar

```bash
npx eas-cli build --platform android --profile preview
```

O build roda na nuvem do Expo. No fim, ele mostra o link do **APK**: abra no celular e instale (o Android pede para permitir
a instalação de fontes desconhecidas). Abra o app, cole o link do Aurora e aceite a permissão de notificação.

## Modo atenção: avisa com o app fechado

Em *Meus alertas → Modo atenção*, o app confere os alertas perto de você **mesmo fechado** (versão 3 do app):

1. O Android mostra uma notificação fixa, **"Aurora · Modo atenção ligado"**: é o serviço que mantém o GPS funcionando.
2. A cada ~1 minuto o app pega a posição do aparelho e baixa a lista de alertas das últimas 6 horas (`GET /api/v1/alertas`).
3. Se algum alerta está a até **500 m** e ainda não foi avisado, aparece uma notificação: título padrão, área e a distância.
   Tocar nela abre a área no mapa. O relato que o próprio aparelho enviou nunca avisa quem enviou.

**A localização nunca vai para o servidor.** O servidor só entrega a lista de alertas, igual para todo mundo; a comparação com a sua
posição acontece no celular (`mobile/alertas-proximos.js`).

Ao ligar, o Android pede três coisas: a **localização**, depois **"Permitir o tempo todo"** (tela das configurações do Android,
necessária para funcionar com o app fechado) e as **notificações**. Se alguma for negada, a página diz qual liberar.
O Modo atenção gasta mais bateria que o app aberto; desligue em *Meus alertas* quando não precisar.

**Celulares Xiaomi (MIUI/HyperOS) e outros com economia agressiva de bateria** costumam matar serviços em segundo plano. Em
*Configurações → Apps → Aurora*: *Economia de bateria → Sem restrições*, *Inicialização automática* ligada, e (opcional) fixe o
app na tela de recentes. Sem isso o aviso com o app fechado pode não chegar.

Esta versão também libera a localização para o *"Mostrar onde estou"* do mapa (a página pede ao app, que pergunta ao Android).
O **APK antigo precisa ser gerado de novo** (`eas build`, igual acima) e instalado por cima; com o antigo a página avisa
"instale a versão nova".

## Usar

1. No mapa, toque numa área (a da sua casa, do trabalho, da faculdade) e escolha **Acompanhar**.
2. Quando alguém relatar algo nela, a notificação chega na barra, mesmo com o app fechado.

## Se não funcionar

O app mostra o motivo em "Notificações desligadas: …" na tela do link (ou na tela de erro).

| Mensagem | O que fazer |
| --- | --- |
| Falta o projectId do EAS | Rode `npx eas-cli init` em `mobile/` e gere o APK de novo. |
| A permissão de notificação foi negada | Ajustes do Android → Apps → Aurora → Notificações. |
| Notificações não funcionam em emulador | Use um celular de verdade. |
| Erro de FirebaseApp / FCM | O `google-services.json` ou a chave FCM V1 não chegaram ao build: refaça os passos 1 a 4. |

O link do Aurora (túnel temporário) muda quando o `cloudflared` reinicia: toque no ⚙ e cole o novo. As áreas acompanhadas
continuam valendo, porque ficam no servidor.

## Ainda não tem

- Ícone próprio da notificação (hoje usa o padrão do Android).
- Versão para iPhone (precisa de conta Apple Developer paga).
- Aviso instantâneo: o Modo atenção confere a cada ~1 minuto; um alerta novo pode levar até esse tempo para chegar.
