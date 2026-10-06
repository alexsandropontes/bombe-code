# Arquitetura — Bombe Code

> Reimplementação Python do opencode (MIT). Padrão: monolito modular em camadas com fronteiras explícitas — cada subpacote espelha um pacote do original (ver `docs/research/opencode-dissection.md`).
> **Atualização as-is (pós-DDD, commits `4e3cbef`/`d84b00e`):** o núcleo de sessão/providers/tools/server permanece parity com o original; o orquestrador ganhou camadas DDD (`domain/`, `application/`, `infrastructure/`) e o motor Turing (`turing/`).

## 1. Estrutura de módulos (as-is, 188 módulos)

```
src/bombe_code/                  # backend (path configurado em .bombeconfig)
├── __init__.py / __main__.py    # boot + __version__
├── config/                      # F1 — parity: opencode/src/config + core/v1/config
│   ├── paths.py                 # XDG (platformdirs) + descoberta de bombe.json(c)
│   ├── loader.py                # merge profundo, concat de arrays
│   └── project_config.py        # ProjectConfigManager (.bombeconfig YAML, ST-019)
├── storage/                     # F1 — parity: opencode/src/storage/storage.ts
│   ├── kv.py                    # JSON por arquivo + lock
│   ├── session_store.py         # info/message/part
│   └── project_db.py            # SQLite .bombe-code/state.db (Turing/Kanban — Onda 2)
├── providers/                   # F2 — parity: provider/provider.ts, auth, models-dev
│   ├── registry.py              # list/get/parseModel/closest/defaultModel
│   ├── models_dev.py            # catálogo + cache TTL
│   ├── auth.py                  # auth.json (0600)
│   ├── resolver.py              # resolução hierárquica + failover de provedores
│   └── adapters/                # parity: llm/src/providers (anthropic, openai, z.ai, …)
├── llm/                         # Onda 2 — PydanticAiFactory e rotas de provedor
│   ├── pydantic_factory.py      # fábrica tipada de agentes (pydantic-ai)
│   ├── provider_rotator.py      # rotação/failover com cooldown
│   └── quota_detector.py        # detecção de quota/timeout por provedor
├── session/                     # F3/F4 — parity: session/*.ts
│   ├── models.py / crud.py / system.py
│   ├── loop.py / processor.py / to_provider.py / lifecycle.py
├── domain/                      # DDD — entidades e regras puras (sem I/O)
│   ├── wave/                    # models (WaveState/Wave), sequencer, workspace, repository
│   ├── intent/                  # vocabulário de intenções
│   └── session/                 # regras de sessão
├── application/                 # DDD — casos de uso
│   ├── wave/service.py          # orquestração de alto nível da ONDA
│   └── intent/                  # aplicação de intenções
├── infrastructure/storage/      # DDD — adaptadores de persistência
├── turing/                      # ⭐ Turing Runtime Engine (Onda 2, EP-006..010)
│   ├── state_machine.py         # FSM da ONDA (WaveType, sub-stages)
│   ├── orchestrator.py          # run_discuss/run_plan/run_cycle/run_validate/…
│   ├── classifier.py            # NLU determinística local (0 tokens)
│   ├── waiter.py                # espera 3-tiers / auto-cascade
│   ├── gates.py                 # TemplateGate, SealGate, ConsumerHandoffGate
│   ├── upstream_gates.py        # PRD, Journey, Architecture, DB, StoryDoR (INVEST)
│   ├── upstream_profiler.py     # perfil Lean Inception adaptativo
│   ├── review_gate.py           # duplo review @aniche + @unclebob + anti-fraude
│   ├── handoff_gate.py          # gate de entrada do consumidor
│   ├── kanban.py                # KanbanManager (SQLite + markdown, Andon flag)
│   ├── pbb.py                   # decomposição PBB em tarefas atômicas
│   └── prompt_assembler.py      # LEGO de prompts por DeliveryTarget
├── agents/                      # EP-003 — 23 definições (definitions/*.md) + registry/runner
├── skills/                      # EP-003 — discovery, manifest, registry on-demand
├── commands/                    # slash commands (loader, templates)
├── tools/                       # F5 — parity: opencode/src/tool/*
│   ├── base.py / registry.py
│   └── builtin/                 # read, write, edit, shell, grep, glob, snippet_*, …
├── permissions/                 # F6 — parity: permission/index.ts
│   ├── rules.py / shell_scan.py
│   └── stage_guard.py           # trava de escrita em src/ nas etapas Upstream
├── server/                      # F7 — parity: server/server.ts + routes
│   ├── app.py / bus.py / questions.py / deps.py
│   └── routes/                  # session, meta, wave (SSE real)
├── cli/                         # F9 — Typer: run, tui(default), serve, wave, project, snippet, mode, …
├── tui/                         # F8/F15 — Textual: app, client, commands, widgets/, themes
├── registry/                    # EP-009 — catálogo declarativo v2
│   ├── starters/                # 38 manifests YAML + 27 blueprints físicos
│   └── snippets/                # 55 snippets testados (python/node/go/java/dotnet/react)
├── starters/                    # EP-005 — engine de scaffolding, matcher, decision
├── snippets/                    # EP-005 — registry v1 (legado, baseline)
├── worktree/                    # git worktrees por onda/stories
├── sdk/                         # F10 (bônus) — cliente do OpenAPI
├── web/                         # F11 (bônus) — Reflex (extra opcional `web`)
├── desktop/                     # F16 (bônus) — pywebview (extra opcional `desktop`)
├── plugins/ / lsp/ / snapshot/ / mcp/ / acp/ / images/ / formatters/   # bônus parity
└── models/                      # state (modelos de estado do runtime)
tests/                           # 90 arquivos — 414 testes verdes
├── unit/                        # 72 arquivos (mocks/fakes permitidos)
└── integration/                 # 18 arquivos (storage/HTTP REAIS, sem mocks)
```

Guard rail: NENHUM arquivo fora de `src/bombe_code/`, `tests/`, `docs/`.

## 2. Padrões

- **Modular monolith** com composition root (`main.py`): dependências construídas uma vez e injetadas.
- **DI:** FastAPI `Depends` no server; injeção explícita (parâmetros/`ctx`) no core — sem singletons globais além do event bus.
- **Ports & Adapters nos providers LLM:** interface `LLMProvider.stream(request) -> AsyncIterator[LLMEvent]`; adapters normalizam qualquer provedor para o `LLMEvent` unificado (parity com `session/llm/ai-sdk.ts`).
- **Event bus tipado** (pub/sub in-process) como fonte única dos eventos SSE — TUI/web/SDK consomem o mesmo fluxo.
- **Idiomas do domínio:** Effect (original) → Pydantic models + dataclasses + `asyncio`; Schema Effect → Pydantic (OpenAPI automático).
- **Async first:** todo I/O (LLM, storage, SSE, permissões) é `async`; tools de subprocesso em thread pool.

## 3. Contratos de API (paridade com `/api/*`)

| Método/Rota | Payload principal | Resp |
|---|---|---|
| GET `/api/health` | — | status |
| GET `/api/event` | SSE (`Last-Event-ID`) | stream de `Event` |
| POST `/api/session` | `{title?, agent?, model?}` | `Session` |
| GET `/api/session` | — | `Session[]` |
| GET `/api/session/:id/message` | — | `Message[]` + parts |
| POST `/api/session/:id/prompt` | `{parts[], model?, agent?}` | eventos via SSE; `wait` opcional |
| POST `/api/session/:id/interrupt` | — | ack |
| POST `/api/session/:id/compact` \| `/revert/...` | — | ack |
| GET/POST `/api/session/:id/{model,agent,permission,question,context,history}` | — | parity |
| GET `/api/model` \| `/api/provider[/:id]` | — | catálogo |
| GET `/api/agent` \| `/api/command` \| `/api/skill` | — | listagens |
| GET `/api/fs/{list,read/*,find}` | paths | conteúdo (com permissão) |
| POST `/api/permission/request` \| `/saved` | regra/resposta | ack/lista |
| POST `/api/question/request` | pergunta | resposta UI |

- **Eventos SSE:** `message.part.updated`, `message.updated`, `permission.updated`, `question.asked`, `server.connected`, etc. (tipados em Pydantic, ordenados com `id` monotônico).
- **OpenAPI:** gerado pelo FastAPI em `/openapi.json` → fonte do SDK (F10).

## 4. Estratégia de dependências (UV)

- `uv` + `pyproject.toml` (workspace único). Runtime: `fastapi`, `uvicorn`, `typer`, `pydantic`, `platformdirs`, `httpx`, `textual`, `rich`, `jsonpath`/`jsonc` para config, `tree-sitter`/`bashlex` (scan shell), `pygls` (LSP), `sse-starlette` ou FastAPI nativo.
- Reflex entra como **dependência obrigatória** (web UI é feature interna); pywebview como extra opcional: `--extra desktop`.
- Testes: `pytest`, `pytest-asyncio`, `respx` (HTTP), `coverage`.

## 5. Camadas e responsabilidades (as-is pós-DDD)

```
cli / tui / web / sdk      →  interface (consomem server ou core in-process)
server                     →  contratos HTTP/SSE + auth + permissão ponte
application (wave/intent)  →  casos de uso da ONDA (orquestração de alto nível)
turing                     →  motor determinístico: FSM, gates, kanban, PBB, prompts
domain (wave/intent/session) → entidades e regras puras (zero I/O)
session (loop/processor)   →  orquestração do turno (harness)
tools / permissions        →  ação no mundo (isoladas, testáveis sem LLM)
llm / providers            →  fronteira externa LLM (adapters + failover)
storage / config           →  fronteira disco (XDG JSON + SQLite .bombe-code/)
```

Regras de dependência: `interface → server → application → {turing, session} → {tools, providers}`; `domain` não importa de ninguém; `storage/config` só é dependido pelo core e pela infraestrutura; nada importa de `tui/web/cli` (evita ciclo).

## 6. Decisões-chave (ADR curtos)

1. **Storage JSON XDG, não SQLite** — escolha explícita; formato parity com storage v1 do original; swap posterior encapsulado atrás de `session_store`.
2. **Effect → asyncio/Pydantic** — sem framework Effect-like; contratos tipados via Pydantic.
3. **Server in-process na TUI** — parity com worker do original; mesmo event bus.
4. **Um `LLMEvent` unificado** por provider — adapters traduzem streams.
5. **Harness é a spine** — F1..F9 na ordem fixa; bônus só após harness green.
6. **Refactor DDD (pós-v0.1.19)** — domínio da ONDA extraído para `domain/` (regras puras) + `application/` (casos de uso) + `infrastructure/` (persistência), mantendo o harness parity intacto.
7. **SQLite só para estado do Turing** — `state.db` em `.bombe-code/` guarda onda ativa, kanban e checkpoints; sessões continuam em JSON XDG.
8. **Registry declarativo v2 (YAML)** — 38 starters e 55 snippets em `registry/` substituem os builtins em código como fonte oficial; `starters/`/`snippets/` v1 permanecem como baseline/legado.
9. **NLU determinística primeiro** — `turing/classifier.py` resolve intenções rotineiras com 0 tokens; LLM classificadora só entra sob ambiguidade (`needs_llm=True`).
