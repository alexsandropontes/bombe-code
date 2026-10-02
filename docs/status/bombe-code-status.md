# Status — Bombe Code

> Atualizado em: onda TDD `*bc tdd cycle-full` (em execução).
> Fonte de verdade do workflow: `.bombe-workflow/state.yaml`.
> Stories detalhadas: `docs/briefings/bombe-code-stories.md`.

## 1. Missão original (a que nos guia)

Reimplementar **100% do opencode original** (TypeScript — snapshot MIT completo em
`docs/opencode/`) numa implementação própria chamada **Bombe Code**, em **Python + UV
(obrigatório)**, com as regras:

- **Derivação declarada:** nunca negar que somos derivados do opencode; atribuição e
  licenças no README/NOTICE **ao final** (sem comentários por função). Licença nossa: **MIT**.
- **Bifurcação:** a partir da onda atual não seguimos mais o original — somos
  reimplementação completa.
- **HARNESS PRIMEIRO:** o que importa é o ciclo *pedir (vibe) → agente executa →
  entrega o projeto*. Tudo além do harness (web, desktop, plugins, LSP, MCP, SDK,
  tui-complete) é **bônus** e nunca bloqueia o harness.
- Escopo open-source do original; enterprise/SaaS/pago **fora**.
- Stack definida no discuss: Python 3.13 + UV, FastAPI + Typer, TUI **Textual**,
  web-ui **Reflex**, storage **JSON em XDG** (sem banco), paths em
  `src/bombe_code/` (backend), `src/bombe_code/tui/` (frontend), `src/bombe_code/cli/` (services).

## 2. O que está PRONTO (7/16 features) — BACKEND DO HARNESS 100%

| # | Feature | Status | Evidência |
|---|---------|--------|-----------|
| F1 | config-storage | ✅ **DONE** | 14 testes, quality gate aprovado |
| F2 | providers-auth | ✅ **DONE** | 15 testes, quality gate aprovado |
| F3 | session-core | ✅ **DONE** | 14 testes, quality gate aprovado |
| F4 | tools-system | ✅ **DONE** | 23 testes (14 builtins), quality gate aprovado |
| F5 | permissions | ✅ **DONE** | 12 testes, wiring nas tools, quality gate aprovado |
| F6 | agent-loop | ✅ **DONE** | 23 testes (CA1–CA4, doom-loop, retry, subtasks, lifecycle, adaptadores SSE reais) |
| F7 | server-http | ✅ **DONE** | 6 testes HTTP/SSE real; G5 vivo (health 200 com auth / 401 sem); quality gate aprovado |

**Suite: 99 testes verdes · ruff limpo · 0 `NotImplementedError` · 0
`dependency_overrides` · `run.sh` sobe.**

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
