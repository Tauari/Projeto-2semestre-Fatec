# US04 — Envio de relatos sem cadastro

## 1. Descrição da User Story

| Atributo | Detalhe |
| :--- | :--- |
| **Identificador** | **US04** |
| **Título** | Envio de relatos sem cadastro |
| **Módulo** | Relatos da Comunidade / Privacidade |
| **Prioridade** | Alta (Essencial para a segurança e acessibilidade) |
| **Responsável** | Equipe Aurora (Projeto Fatec) |

### Persona e História de Usuária
> **Como** usuária do mapa,  
> **quero** enviar um relato de vulnerabilidade sem criar uma conta ou realizar login,  
> **para** comunicar uma situação de maneira acessível e preservar minha privacidade.

---

## 2. Critérios de Aceitação e Cenários BDD (Gherkin)

### Critério 1: Permitir envio sem cadastro ou login
A usuária não precisa fornecer credenciais, e-mail, senha, número de telefone ou autenticar-se para registrar um relato no mapa.

```gherkin
Cenário: Envio de relato com sucesso por usuária anônima
  Dado que a usuária acessa a funcionalidade de registrar relato no mapa
  E não possui cadastro nem realizou login na aplicação
  Quando ela preencher os dados da situação ocorrida e confirmar o envio
  Então o sistema deve registrar o relato com status HTTP 201 Created
  E gerar uma chave de exclusão exclusiva armazenada localmente no aparelho
  E disponibilizar o relato de forma anônima para a comunidade
```

---

### Critério 2: Exibir os campos necessários para o relato
A interface (chat conversacional ou formulário) e a API devem contemplar os campos essenciais para descrever a situação de vulnerabilidade sem excessos.

| Campo | Tipo | Obrigatório | Descrição |
| :--- | :--- | :--- | :--- |
| `tipos` | `list[str]` | Sim | Tipos de situação selecionados (ex.: assédio, ambiente, perseguição). Máximo de 4. |
| `cell` | `str` | Sim | Identificador da célula geográfica aproximada (ex.: `10_20` ou `f-5_12`). |
| `quando` | `str` | Não | Momento temporal aproximado (`hoje`, `ontem`, `semana`, `antes`). |
| `periodo` | `str` | Não | Faixa de horário (`manha`, `tarde`, `18-20`, `20-22`, `22-00`, `madrugada`). |
| `texto` | `str` | Não | Descrição em texto livre sobre o ocorrido (até 2000 caracteres). |
| `origem` | `str` | Não | Origem do envio (`chat` ou `chat-ia`, padrão `chat`). |

```gherkin
Cenário: Apresentação estruturada dos dados no relato publicado
  Dado que a usuária enviou os campos necessários
  Quando a resposta do servidor for gerada
  Então o objeto do relato público deve conter exatamente os atributos:
    | id | tipos | cell | quando | periodo | texto | criado | origem |
```

---

### Critério 3: Validar os campos obrigatórios
O sistema deve validar os dados enviados e impedir a criação de relatos inconsistentes.

```gherkin
Cenário: Tentativa de envio sem selecionar o tipo de situação
  Dado que a usuária tenta enviar um relato sem selecionar nenhum tipo válido
  Quando a requisição for processada
  Então o sistema deve rejeitar o envio com status HTTP 422 Unprocessable Entity
  E retornar a mensagem de erro específica para o campo "tipos"

Cenário: Tentativa de envio sem informar ou com célula geográfica inválida
  Dado que a usuária tenta enviar um relato com "cell" nula, vazia ou fora do padrão de grade
  Quando a requisição for processada
  Então o sistema deve rejeitar o envio com status HTTP 422 Unprocessable Entity
  E retornar a mensagem de erro específica para o campo "cell"

Cenário: Tentativa de envio com texto excedendo o limite permitido
  Dado que a usuária tenta enviar um texto livre superior a 2000 caracteres
  Quando a requisição for processada
  Então o sistema deve recusar o envio com status HTTP 422 Unprocessable Entity
```

---

### Critério 4: Apresentar confirmação de envio ou mensagem de erro
A usuária deve receber retorno claro e imediato quanto ao status da sua comunicação.

```gherkin
Cenário: Confirmação visual e programática após publicação com sucesso
  Dado que os dados do relato são válidos
  Quando a requisição de publicação for concluída
  Então a usuária recebe a confirmação imediata ("Relato publicado. Obrigada por avisar outras mulheres.")
  E opções contextuais (ver no mapa, acompanhar área, rede de apoio)
  E a chave de exclusão para remoção futura caso deseje

Cenário: Exibição de mensagem de erro amigável em caso de falha
  Dado que ocorra um erro de validação ou indisponibilidade do servidor
  Quando o envio for tentado
  Então o sistema deve exibir orientações claras sobre o motivo da falha
  E manter os dados do rascunho preservados para nova tentativa
```

---

### Critério 5: Evitar solicitar dados pessoais desnecessários
A aplicação adota o princípio de **minimização de dados** (LGPD, Art. 6º, III).

```gherkin
Cenário: Descarte automático de campos de identificação pessoal
  Dado que por qualquer motivo sejam enviados campos como "nome", "email", "cpf" ou "telefone"
  Quando o backend receber o payload
  Então esses campos devem ser ignorados pelo schema de entrada (extra="ignore")
  E não devem ser gravados no banco de dados nem expostos publicamente
```

---

### Critério 6: Proteger as informações sensíveis do relato
Proteção ativa contra vazamento acidental de dados pessoais e de geolocalização precisa.

```gherkin
Cenário: Anonimização de dados pessoais inseridos no texto livre
  Dado que a usuária inclua inadvertidamente nomes ("ele se chama João"), telefones, e-mails, CPFs ou número de residência
  Quando o relato for enviado
  Então o serviço de anonimização deve substituir esses dados por marcadores genéricos ([nome], [telefone], [e-mail], [documento], [número])
  E persistir no banco de dados somente o texto sanitizado
  E informar à usuária quais tipos de dados foram removidos

Cenário: Proteção de geolocalização precisa (não exposição de endereço residencial)
  Dado que o relato é associado a um ponto geográfico
  Quando for persistido e renderizado no mapa
  Então a localização deve ser agrupada na célula de grade (cell de ~150-200m ou ~1km)
  E nunca expor coordenadas exatas (lat/lng) nem número predial
```

---

## 3. Implementação Técnica

### Backend (FastAPI / SQLAlchemy / Pydantic)
- **Rotas**: `backend/routes/relatos.py`
  - `POST /api/v1/relatos`: Recebe `RelatoEntrada`, aplica limpeza por `anonimizar_completo`, gera chave segura de 24 bytes via `secrets.token_urlsafe(24)`, salva o hash SHA-256 e persiste o relato no banco SQLite (`Relato`).
  - `GET /api/v1/usuarios/eu`: Endpoint de identidade em `backend/routes/usuarios.py` confirmando que não há exigência de cadastro (`autenticado: False`).
- **Modelos**: `backend/models/relatos.py`
  - `RelatoEntrada`: Pydantic model com validação de `tipos`, `cell` (regex `^f?-?\d{1,4}_-?\d{1,4}$`), `quando`, `periodo` e limite de 2000 caracteres no `texto`. Configuração `extra="ignore"` para descarte de dados pessoais extras.
  - `RelatoPublico`: Filtra a saída pública com apenas 8 campos estritamente anônimos.
- **Serviços**:
  - `backend/services/anonimizacao.py`: Higienização automática por expressões regulares para emails, telefones, documentos (CPF), placas, perfis e nomes associados a marcadores.
  - `backend/services/enderecos.py`: Anonimização e remoção de nomes de ruas específicas e números prediais.

### Frontend (JavaScript Vanilla modular)
- **Chatbot Conversacional**: `frontend/chatbot/chat.js`
  - Conduz o relato passo a passo sem exigir login.
  - Alerta explicitamente a usuária: *"Escreva abaixo. Evite nomes, telefones, placas e endereço exato: eu tiro o que escapar antes de publicar."*
  - Exibe revisão prévia com aviso: *"Publicado sem nome, contato ou local exato."*
- **Gerenciador de Estado e Chaves**: `frontend/shared/store.js`
  - Armazena a chave de exclusão `chave_exclusao` apenas no `localStorage` do aparelho da usuária (`LS.get('chaves')`), permitindo que ela apague seu próprio relato a qualquer momento sem precisar de login.

---

## 4. Testes Automatizados

A User Story é coberta por testes automatizados em `backend/tests/test_us04_envio_relatos_sem_cadastro.py`:

```bash
# Execução dos testes automatizados da US04
.venv/Scripts/python -m pytest backend/tests/test_us04_envio_relatos_sem_cadastro.py -v
```

### Resultados dos Casos de Teste (`relatosSemCadastros`)
| Caso de Teste | Critério Coberto | Status |
| :--- | :--- | :--- |
| `test_envio_sem_autenticacao_ou_token` | Critério 1 (Sem login/cadastro) | **Aprovado** (100%) |
| `test_campos_do_relato` | Critério 2 (Campos estruturados) | **Aprovado** (100%) |
| `test_validacao_tipos_obrigatorio` | Critério 3 (Validação de tipo obrigatório) | **Aprovado** (100%) |
| `test_validacao_cell_obrigatorio_e_formato` | Critério 3 (Validação de cell obrigatória) | **Aprovado** (100%) |
| `test_validacao_limite_tamanho_texto` | Critério 3 (Limite máx. de caracteres) | **Aprovado** (100%) |
| `test_confirmacao_de_envio` | Critério 4 (Status 201 + confirmação) | **Aprovado** (100%) |
| `test_mensagem_de_erro_estruturada` | Critério 4 (Status 422 + payload de erros) | **Aprovado** (100%) |
| `test_nao_solicita_nem_persiste_dados_pessoais` | Critério 5 (Minimização de dados LGPD) | **Aprovado** (100%) |
| `test_sanitizacao_e_anonimizacao_de_dados_sensiveis` | Critério 6 (Expurgo de dados sensíveis) | **Aprovado** (100%) |
| `test_localizacao_agregada_sem_coordenadas_exatas` | Critério 6 (Geolocalização por células) | **Aprovado** (100%) |

---

## 5. Definição de Pronto (Definition of Done - DoD)
- [x] Histórico e critérios de aceitação formalizados e aprovados.
- [x] Fluxo de envio de relato funcional sem exigência de conta ou autenticação.
- [x] Validação robusta de campos obrigatórios no backend e frontend.
- [x] Sanitização e anonimização automática de dados sensíveis ativa.
- [x] Chave de exclusão gerada com hash seguro e mantida no cliente.
- [x] Suíte de testes automatizados completa com 100% de sucesso.

