# Arquitetura — Bombe Code

> Reimplementação Python do opencode (MIT). Padrão: monolito modular em camadas com fronteiras explícitas — cada subpacote espelha um pacote do original (ver `docs/research/opencode-dissection.md`).

## 1. Estrutura de módulos

```
src/bombe_code/                  # backend (path configurado em .bombeconfig)
├── __init__.py
├── main.py                      # wiring: monta app FastAPI + CLI (composition root)
├── config/                      # F1 — parity: opencode/src/config + core/v1/config
│   ├── paths.py                 # XDG (platformdirs) + descoberta de bombe.json(c)
│   ├── loader.py                # merge profundo, concat de arrays
│   └── schema.py                # Pydantic: campos do config (parity com Info)
├── storage/                     # F1 — parity: opencode/src/storage/storage.ts
│   ├── kv.py                    # JSON por arquivo + lock
│   └── session_store.py         # info/message/part
├── providers/                   # F2 — parity: provider/provider.ts, auth, models-dev
│   ├── registry.py              # list/get/parseModel/closest/defaultModel
│   ├── models_dev.py            # catálogo + cache TTL 5min
│   ├── auth.py                  # auth.json (0600)
│   └── adapters/                # parity: llm/src/providers (anthropic, openai, …)
├── session/                     # F3/F4 — parity: session/*.ts
│   ├── models.py                # Session, Message, Part (Pydantic) — parity schema/v1
│   ├── crud.py                  # persistência via storage
│   ├── system.py                # system prompt
│   ├── loop.py                  # runLoop — parity session/prompt.ts
│   ├── processor.py             # stream → Parts — parity session/processor.ts
│   └── to_provider.py           # mensagens → formato do provider
├── tools/                       # F5 — parity: opencode/src/tool/*
│   ├── base.py                  # Def, ctx, truncate
│   ├── registry.py              # builtins + custom + plugins
│   └── builtin/                 # read, write, edit, shell, grep, glob, …
├── permissions/                 # F6 — parity: permission/index.ts
│   ├── rules.py                 # evaluate (última regra vence)
│   ├── ask.py                   # fila de aprovação (asyncio) ligada ao server
│   └── shell_scan.py            # AST scan → permissões bash/external_directory
├── server/                      # F7 — parity: server/server.ts + routes
│   ├── app.py                   # FastAPI, auth basic, CORS localhost
│   ├── routes/                  # session, event(SSE), model, agent, fs, permission, …
│   └── events.py                # barramento + SSE batching ~16ms + Last-Event-ID
├── cli/                         # F9 (path configurado: services) — parity yargs + packages/cli
│   └── main.py                  # Typer: run, tui(default), serve, web, models, …
├── tui/                         # F8/F15 (path configurado: frontend) — parity packages/tui
│   ├── app.py                   # Textual App
│   ├── screens/                 # chat, permission, question, dialogs, palette
│   ├── widgets/                 # parts, diff, prompt input
│   └── theme/assets/            # themes JSON (dracula, catppuccin, …)
├── web/                         # F11 (bônus) — parity packages/app (Reflex)
├── desktop/                     # F16 (bônus) — parity packages/desktop (pywebview)
├── sdk/                         # F10 (bônus) — cliente gerado do OpenAPI
├── plugins/                     # F13 (bônus) — parity packages/plugin
├── lsp/                         # F12 (bônus) — parity opencode/src/lsp
├── snapshot/                    # F12 (bônus) — parity snapshot/ (git)
├── mcp/                         # F14 (bônus)
└── acp/                         # F14 (bônus)
tests/
├── unit/                        # mocks/fakes permitidos
├── integration/                 # DB real → aqui: storage real em tmp, HTTP real
└── e2e/                         # HTTP real ponta-a-ponta (harness)
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
- Reflex e webview entram como extras opcionais: `uv sync --extra web`, `--extra desktop`.
- Testes: `pytest`, `pytest-asyncio`, `respx` (HTTP), `coverage`.

## 5. Camadas e responsabilidades

```
cli / tui / web / sdk      →  interface (consomem server ou core in-process)
server                     →  contratos HTTP/SSE + auth + permissão ponta
session (loop/processor)   →  orquestração do turno (harness)
tools / permissions        →  ação no mundo (isoladas, testáveis sem LLM)
providers                  →  fronteira externa LLM (adapters)
storage / config           →  fronteira disco (XDG)
```

Regras de dependência: `interface → server → session → {tools, providers}`; `storage/config` só é dependido pelo core; nada importa de `tui/web/cli` (evita ciclo).

## 6. Decisões-chave (ADR curtos)

1. **Storage JSON XDG, não SQLite** — escolha explícita; formato parity com storage v1 do original; swap posterior encapsulado atrás de `session_store`.
2. **Effect → asyncio/Pydantic** — sem framework Effect-like; contratos tipados via Pydantic.
3. **Server in-process na TUI** — parity com worker do original; mesmo event bus.
4. **Um `LLMEvent` unificado** por provider — adapters traduzem streams.
5. **Harness é a spine** — F1..F9 na ordem fixa; bônus só após harness green.
