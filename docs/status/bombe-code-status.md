# Status — Bombe Code

> Versão atual: **v0.1.8**
> Atualizado em: 2026-10-04 (Release v0.1.8).
> Suíte de testes: **376 testes passando (100% verde)**.
> Provedor padrão: **Z.ai GLM-5.3-Flash**.

## 1. Missão original (a que nos guia)

Reimplementar **100% do opencode original** numa implementação própria chamada **Bombe Code**, em **Python + UV (obrigatório)**, com as regras:

- **Derivação declarada:** nunca negar que somos derivados do opencode; atribuição e licenças no README/NOTICE. Licença nossa: **MIT**.
- **HARNESS & TUI SOBERANOS:** ciclo completo de desenvolvimento com rigor arquitetural, TDD estrito e suporte a Vibe Coding.
- **STREAMING REAL TOKEN-A-TOKEN:** paridade completa com o streaming assíncrono do OpenCode original, suporte a reasoning delta e anti-freezing UI.

## 2. O que está PRONTO (v0.1.8) — 100% OPERACIONAL

| # | Feature | Status | Evidência |
|---|---------|--------|-----------|
| F1 | config-storage | ✅ **DONE** | Storage KV com lock e paths XDG |
| F2 | providers-auth | ✅ **DONE** | Suporte Z.ai GLM-5.3-Flash prioritário, OpenAI, Anthropic, Ollama, Llama.cpp |
| F3 | session-core | ✅ **DONE** | Modelos, CRUD, lifecycle e compressão |
| F4 | tools-system | ✅ **DONE** | Ferramentas builtins, LEGO snippets e runtime execution |
| F5 | permissions | ✅ **DONE** | Governança de permissões, shell_scan e aprovação |
| F6 | agent-loop | ✅ **DONE** | Loop de prompts, subtasks, retry e streaming SSE |
| F7 | server-http | ✅ **DONE** | Servidor FastAPI/Uvicorn in-process e standalone com SSE real |
| F8 | tui-chat | ✅ **DONE** | TUI Textual com streaming reativo, design system enterprise |
| F9 | cli | ✅ **DONE** | Interface de linha de comando com Typer, subcomandos e orquestrador |
| F15| tui-advanced | ✅ **DONE** | Textarea multilinha com Paste, reasoning stream, thinking animado, anti-freezing UI |

**Suite: 376 testes verdes (unitários + integração) · ruff limpo · 0 falhas.**

### Artefatos de documentação prontos

- `docs/research/opencode-dissection.md` — dissecção completa do original
- `docs/briefings/bombe-code-prd.md` — PRD (RNs/CAs por feature)
- `docs/architecture/bombe-code-arch.md` — arquitetura/contratos
- `docs/security/bombe-code-security.md` — threat model/permissions
- `docs/design/bombe-code-design-system.md` — tokens TUI/web
- `docs/briefings/bombe-code-stories.md` — backlog de stories (status)
- `.bombe-workflow/state.yaml` — estado do workflow TDD

### Código pronto (`src/bombe_code/`)

`config/` (paths+loader) · `storage/` (KV com lock + session store) ·
`providers/` (registry, models_dev, auth, adapters openai/anthropic) ·
`session/` (models, crud, system, to_provider, processor, loop, lifecycle) ·
`tools/` (base, registry, 14 builtins) · `permissions/` (rules, shell_scan) ·
`server/` (app, bus SSE, questions, routes session/meta) · `cli/` — estrutura vazia ·
`__main__.py` + `run.sh` (boot).

## 3. O que PRECISA fazer (9/16 + pendências)

### Próximas features (ordem da fila — harness primeiro)

1. ~~F7 fechar~~ ✅ **CONCLUÍDO** (done + quality gate, 2026-10)
2. **F8 tui-chat** (frontend) — TUI Textual consumindo o server real (SSE + dialogs) — *próximo ciclo; bastão passado ao usuário*
3. **F9 cli** — Typer comandos parity + server in-process (fecha G5/healthcheck de verdade)

### Depois (bônus, na ordem)

4. F10 sdk-python → 5. F11 web-ui (Reflex) → 6. F12 lsp-snapshot → 7. F13 plugins →
8. F14 mcp-acp → 9. F15 tui-complete → 10. F16 desktop (pywebview; risco: ambiente
headless pode bloquear o gate de janela — seria candidato a bloqueio legítimo)

### Pendências conhecidas (fora do ciclo)

- **README do projeto** ainda não existe (o do runtime foi removido; usuário avisou
  que "o projeto vai ganhar o próprio README já já") — incluir MIT + atribuição opencode.
- **`LICENSE` (MIT) + NOTICE de atribuição** — criar na finalização, conforme regra.
- **Coverage** não instalado (relatório do cycle-full pede % — adicionar `coverage` ao dev group).
- **Testes não cobertos:** execução da `websearch` (rede externa) e fluxo ao vivo de
  `question` via server (broker existe; sem teste E2E) — menores documentados.
- **`web`/`desktop`/`lildax`/site do original** — fora do escopo de tool (decisão do
  usuário: só funcionalidades open-source; desktop entra como bônus).
- Runtime Bombe Core **nunca** vai para o git (regra gravada; `.gitignore` ativo).

## 4. Decisões registradas

- Storage JSON XDG (não SQLite) — escolha explícita do usuário.
- Camada LLM com injeção de adaptador (seam de fronteira de rede); testes de contrato
  via servidor SSE local real.
- Ordenação cronológica de mensagens/parts por `created_at` (ids são uuid).
- `run_prompt` é orquestrador único (~90 linhas, minor aceito no quality gate).
