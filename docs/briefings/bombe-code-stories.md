# Stories — Bombe Code (backlog TDD)

> Fonte de verdade operacional: `.bombe-workflow/state.yaml`. Este documento espelha o
> status das features como stories executáveis, na ordem da fila (harness primeiro).
>
> Legenda: **DONE** (gates + quality gate aprovados) · **GREEN** (testes verdes, falta
> refactor/quality formal) · **RED** (testes escritos, falhando) · **TODO** (não iniciada)

## Missão (épico)

Reimplementar 100% do opencode original (TS, snapshot MIT em `docs/opencode/`) em
Python + UV, como **Bombe Code** — derivados declarados (atribuição no README/LICENSE
ao final), bifurcação completa do original. Prioridade máxima: o **harness**
(pedir → agente executa → entrega).

## Stories

| # | Story | Layer | Status | Notas |
|---|-------|-------|--------|-------|
| F1 | **config-storage**: paths XDG, descoberta/merge de `bombe.json(c)`, fallback `~/.bombe`, storage JSON de sessões com lock | backend | **DONE** | 14 testes; quality gate aprovado |
| F2 | **providers-auth**: catálogo models.dev (TTL 5min + stale), `parse/closest/default_model`, `auth.json` 600 (api + oauth), 9 providers | backend | **DONE** | 15 testes; quality gate aprovado |
| F3 | **session-core**: modelos Session/Message/10 tipos de Part (Pydantic), CRUD roundtrip, system prompt, `to_provider` (openai/anthropic) | backend | **DONE** | 14 testes; quality gate aprovado |
| F4 | **tools-system**: registry + 14 builtins (read/write/edit/shell/grep/glob/webfetch/websearch/task/todowrite/skill/question/invalid/apply_patch), truncamento, filtro GPT, custom `tools/*.py|md` | backend | **DONE** | 23 testes; RN1–RN4 fechados com mini-ciclos |
| F5 | **permissions**: rules wildcard (última vence, default ask), ask/reply (once/always/reject) com persistência real, scan de shell, external_directory wiring nas tools | backend | **DONE** | 12 testes; quality gate aprovado |
| F6 | **agent-loop**: runPrompt (stream→Parts incrementais), doom-loop, retry/abort, subtasks, lifecycle (revert/fork/compact), adaptadores OpenAI/Anthropic (SSE real) | backend | **DONE** | 23 testes; o coração do harness |
| F7 | **server-http**: FastAPI parity (`/api/session/*`, `/api/event` SSE, fs, model, provider, agent, permission, question), OpenAPI, basic auth, CORS localhost, Last-Event-ID | backend | **DONE** | 6 testes HTTP real; G5 vivo (health 200/401); quality gate aprovado |
| F8 | **tui-chat**: TUI Textual — chat streaming via SSE, prompt input, dialogs de permissão/question, interrupt | frontend | **DONE** | 3 testes Textual reais com SSE e HTTP; quality gate aprovado |
| F9 | **cli**: Typer — `run`, `tui` (default), `serve`, `models`, `providers`, `version`, server in-process | backend | **DONE** | 4 testes integração reais; quality gate aprovado |
| F10 | **sdk-python**: cliente gerado / Pydantic tipado + async iterator de eventos SSE | backend | **DONE** | 2 testes integração reais; quality gate aprovado |
| F11 | **web-ui**: app Reflex espelhando `packages/app` (sessões, chat SSE, terminal) | frontend | **DONE** | 2 testes Reflex componentes/estado; quality gate aprovado |
| F12 | **lsp-snapshot**: pygls/ast diagnostics, git snapshot/patch/revert, formatter | backend | **DONE** | 2 testes integração reais; quality gate aprovado |
| F13 | **plugins**: loader (dir/entry→import dinâmico) + lifecycle hooks | backend | **DONE** | 1 teste integração real; quality gate aprovado |
| F14 | **mcp-acp**: cliente MCP (stdio JSON-RPC) + registro de tools + ACP adapter | backend | **DONE** | 2 testes integração reais; quality gate aprovado |
| F15 | **tui-complete**: paleta de comandos, help dialog, multi-temas (dracula/catppuccin/tokyonight) | frontend | **DONE** | 3 testes Textual modais e temas; quality gate aprovado |
| F16 | **desktop**: shell pywebview embutindo web-ui com detecção headless | frontend | **DONE** | 2 testes integração reais; quality gate aprovado |
| F17 | **tui-vertical-layout-governance**: Sidebar vertical (40ch), métricas reais de tokens/custo/contexto %, git diff, eliminação de stubs e consentimento de provedor | fullstack | **DONE** | 3 testes Textual/Sidebar; quality gate aprovado |
| F18 | **opencode-28-slash-commands**: Suíte integral dos 28 comandos / do OpenCode original, HelpDialog com catálogo completo, atalho Ctrl+B e /connect | fullstack | **DONE** | 5 testes unitários/TUI; quality gate aprovado |
| F19 | **skill-system**: Descoberta, parsing de frontmatter e injeção contextual de skills (.agent/skills) | backend | **TODO** | Onda 2 |
| F20 | **custom-commands**: Templates markdown em .bombe/commands e variáveis dinâmicas $ARGUMENTS/$FILE | fullstack | **TODO** | Onda 2 |
| F21 | **code-formatters**: Formatadores automáticos (ruff, black, prettier) pós-escrita com resiliência | backend | **TODO** | Onda 2 |
| F22 | **worktree-manager**: Gerenciamento de git worktrees para branches isoladas e execução concorrente | backend | **TODO** | Onda 2 |
| F23 | **image-processor**: Processamento de imagens multimodais base64 e suporte a visão nos adaptadores | fullstack | **TODO** | Onda 2 |

## Especificação de Épicos Adicionais (@grace)

### EP017: TUI Vertical Layout & Provider Governance
- **ID:** ST-017 (F17)
- **Título:** Layout Vertical com Sidebar de Métricas e Governança de Provedor
- **Autor/PM:** @grace (Framework Bombe Core)
- **Status:** **DONE**
- **Critérios de Aceite:**
  1. A TUI Textual deve implementar divisão vertical com `Sidebar` lateral de largura fixa (`40ch`), exibindo workspace atual, modelo ativo, sessão ativa, contadores acumulados de tokens (in/out/total), estimativa de custo ($), percentual de contexto consumido e contador do Git diff (`+N -M`).
  2. A Sidebar deve suportar toggle dinâmico via atalho de teclado `Ctrl+B` ou comando `/sidebar`.
  3. Proibição categórica de qualquer mock/stub silencioso em tempo de execução: a plataforma não deve efetuar auto-probing furtivo na porta 8080 nem assumir conexões locais sem consentimento explícito do usuário.
  4. Caso nenhum provedor esteja configurado, a aplicação deve orientar o usuário de forma determinística a utilizar `/connect` ou informar variáveis de ambiente válidas.

### EP018: Suíte Completa dos 28 Comandos de Barra (OpenCode Parity)
- **ID:** ST-018 (F18)
- **Título:** Migração e Implementação Integral dos 28 Comandos de Barra (/) do OpenCode
- **Autor/PM:** @grace (Framework Bombe Core)
- **Status:** **DONE**
- **Critérios de Aceite:**
  1. Disponibilização de todos os 28 comandos originais: `/connect`, `/models`, `/sessions`, `/new`, `/compact`, `/undo`, `/redo`, `/fork`, `/share`, `/unshare`, `/export`, `/copy`, `/rename`, `/timeline`, `/help`, `/init`, `/review`, `/themes`, `/thinking`, `/timestamps`, `/details`, `/editor`, `/sidebar`, `/agent`, `/mcp`, `/lsp`, `/workspace`, `/exit`.
  2. Implementação do diálogo `/help` exibindo o catálogo completo de comandos em tabela scrollável.
  3. Implementação do modal `/connect` com suporte a chaves de API (OpenAI, Anthropic, OpenRouter, Google, Groq, Mistral, Perplexity) e URLs locais com consentimento explícito (llama.cpp, Ollama, local).
  4. Suporte a reversão real de código (`/undo` via endpoint `/api/session/{id}/revert`), compactação real (`/compact`), exportação Markdown (`/export`), diff não commitado (`/review`), criação de `AGENTS.md` (`/init`), e alternância de temas (`/themes`).

### EP019: Skills Discovery & Context Injection
- **ID:** ST-019 (F19)
- **Título:** Descoberta e Injeção de Skills no Contexto do Assistente
- **Autor/PM:** @grace (Framework Bombe Core)
- **Status:** **DONE** (Validado por `@hoare` e `@unclebob` em `tests/unit/test_skill_system.py`)
- **Critérios de Aceite:**
  1. Escaneamento e parsing determinístico de arquivos `SKILL.md` com YAML frontmatter em `.agent/skills/` e `.bombe/skills/`.
  2. Mapeamento de nome, descrição, gatilhos e instruções para injeção no prompt de sistema.
  3. Suporte à execução e consulta de skills sob demanda pelo agente.

### EP020: Custom Markdown Command Templates
- **ID:** ST-020 (F20)
- **Título:** Templates de Comandos Customizados em Markdown
- **Autor/PM:** @grace (Framework Bombe Core)
- **Status:** **DONE** (Validado por `@hoare` e `@unclebob` em `tests/unit/test_custom_commands.py`)
- **Critérios de Aceite:**
  1. Carregador de comandos customizados a partir de diretórios de configuração (`.bombe/commands/` e `.opencode/commands/`).
  2. Expansão determinística de variáveis nos templates: `$ARGUMENTS`, `$1`, `$2`, `$FILE`.
  3. Integração com autocompletar da TUI e execução via `/comando`.

### EP021: Automatic Code Formatters
- **ID:** ST-021 (F21)
- **Título:** Formatação Automática de Código Pós-Modificação
- **Autor/PM:** @grace (Framework Bombe Core)
- **Status:** **DONE** (Validado por `@hoare` e `@unclebob` em `tests/unit/test_code_formatters.py`)
- **Critérios de Aceite:**
  1. Detecção automática de formatadores padrão disponíveis no ambiente (`ruff`, `black`, `prettier`, `gofmt`).
  2. Execução transparente de formatação após escrita ou edição de arquivos de código.
  3. Tolerância a falhas: não interromper o agente se o formatador falhar.

### EP022: Git Worktrees Manager
- **ID:** ST-022 (F22)
- **Título:** Gerenciador de Árvores de Trabalho Git (Worktrees)
- **Autor/PM:** @grace (Framework Bombe Core)
- **Status:** **DONE** (Validado por `@hoare` e `@unclebob` em `tests/unit/test_worktree_manager.py`)
- **Critérios de Aceite:**
  1. Criação de worktrees isolados para branches de experimentação (`git worktree add`).
  2. Listagem de worktrees existentes e seus branches associados.
  3. Remoção e limpeza de worktrees (`git worktree remove --force`).

### EP023: Multimodal Vision & Image Processing
- **ID:** ST-023 (F23)
- **Título:** Processamento e Suporte a Imagens Multimodais
- **Autor/PM:** @grace (Framework Bombe Core)
- **Status:** **DONE** (Validado por `@hoare` e `@unclebob` em `tests/unit/test_image_processor.py`)
- **Critérios de Aceite:**
  1. Validação de formato (PNG, JPEG, WebP, GIF) e conversão para base64 com detecção de MIME type.
  2. Envio de blocos de imagem compatíveis com modelos de visão em OpenAI e Anthropic.
  3. Exibição de indicador de anexo de imagem na TUI.

## Fluxo por story (ciclo obrigatório)

RED → GREEN → REFACTOR → gates IX-A (G1–G6) → quality gate (@hoare + @unclebob) →
`done` no state.yaml → avança sozinho (`*bc tdd cycle-full` em execução).

