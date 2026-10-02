# Dissecação do opencode original — insumo para a reimplementação Bombe Code

> Fonte: snapshot em `docs/opencode/` (opencode v1.18.34, MIT, Bun/TypeScript).
> Referência técnica exclusiva para a reimplementação Python. Caminhos citados são do original.

## 1. Visão geral da arquitetura

Monorepo Bun workspaces + turbo. 34 pacotes em `packages/`.

### Camadas
```
schema (tipos/Effect Schema)
  → protocol (definição Effect HttpApi)
    → core / llm / server (domínio, providers, utilitários HTTP)
      → opencode (binário: CLI + server + orquestração)
        → tui / app (UIs) · sdk/js (cliente) · plugin · desktop (Electron)
```
Regra do original: `client` nunca depende de core/server (`AGENTS.md`).

### Pacotes principais → responsabilidade

| Pacote | Responsabilidade |
|---|---|
| `packages/opencode` | CLI (yargs), server HTTP, orquestração, tools/LSP/MCP/permission |
| `packages/core` | Domínio: session v2/runner, config, provider, DB/drizzle, pty, git, eventos |
| `packages/protocol` | Definição Effect `HttpApi` (groups: session, fs, pty, event…) |
| `packages/schema` | Tipos/schemas compartilhados (Effect Schema) |
| `packages/llm` | Providers/protocolos LLM (openai, anthropic, gemini, bedrock…) |
| `packages/server` | Rotas, CORS, auth basic, OpenAPI em `/openapi.json` |
| `packages/tui` | UI terminal (Solid + @opentui) |
| `packages/app` | Web UI (Solid + Vite), embutida no binário |
| `packages/sdk/js` | SDK público, gerado de `openapi.json` via @hey-api/openapi-ts |
| `packages/client` | Client HTTP codegen (`src/generated`) |
| `packages/plugin` | API de plugins (hooks: config, event, models, auth, provider, tool, dispose) |
| `packages/desktop` | Shell Electron |
| `packages/web` | Site/docs (Astro) |
| `packages/cli` | Novo binário `lildax` (Effect CLI): api, serve, service, migrate |

### Stack do original
- Bun 1.3, TypeScript 5.8, **Effect 4 beta** (padrão dominante), drizzle-orm + SQLite, zod, Vercel AI SDK (`ai` + `@ai-sdk/*`, ~20 providers), MCP SDK, ws, yargs, ulid, fuzzysort.
- UI: **SolidJS + @opentui** (TUI), Solid+Vite (web), Tailwind, shiki.
- Build: `Bun.build` custom (`packages/opencode/script/build.ts`), targets linux/mac/win; testes `bun test`; lint oxlint + prettier.

## 2. Pontos de entrada (superfícies do produto)

1. **CLI/binário:** `packages/opencode/bin/opencode` → `src/index.ts` (yargs).
   Comandos legados: `run`, `tui`, `attach`, `acp`, `mcp`, `serve`, `web`, `generate`, `models`, `providers`, `agent`, `session`, `export/import`, `stats`, `github`, `pr`, `plugin`, `db`, `upgrade`, `uninstall`, `console`, `debug`.
   Comando default = TUI (`src/cli/cmd/tui.ts`).
2. **TUI:** `tui.ts` spawna worker (`src/cli/tui/worker.ts`) que roda **server in-process** + RPC de eventos; UI importa `run` de `packages/tui/src/app`.
3. **Server HTTP:** `src/server/server.ts` — Effect HttpApi sobre `node:http`; rotas em `src/server/routes/`; SSE + OpenAPI. (Hono só em `packages/function` e `packages/enterprise`.)
4. **Web:** `opencode web` sobe server e embute `packages/app` (Solid+Vite).
5. **Desktop:** Electron (`packages/desktop`), renderer = `packages/app`.
6. **SDK:** gerado do OpenAPI (`script/build.ts` → `openapi.json` → hey-api).

## 3. Storage e paths XDG

`packages/core/src/global.ts` (xdg-basedir):
- data: `~/.local/share/opencode`, config: `~/.config/opencode`, state: `~/.local/state/opencode`, cache: `~/.cache/opencode`, log: `$data/log`, tmp: `/tmp/opencode`, bin: `$cache/bin`.
- SQLite: `$data/opencode.db` (drizzle; `core/src/database/database.ts`).
- Storage JSON (v1 legado, ainda presente): `$data/storage/session/{info,message,part}/…` — KV arquivo-a-arquivo com locks e migrations (`opencode/src/storage/storage.ts`).
- Auth: `$data/auth.json` (chmod 600).
- Catálogo de modelos: cache `$cache/models.json`, fonte `https://models.opencode.ai` TTL 5 min (`core/src/models-dev.ts`).

**Decisão Bombe Code:** storage JSON em XDG (formato do storage v1) — escolha explícita do usuário; sem SQLite no MVP.

## 4. Config

- Descoberta (`src/config/paths.ts`): sobe de cwd até worktree procurando `opencode.json|opencode.jsonc` e `.opencode/`; `~/.opencode`, `OPENCODE_CONFIG_DIR`, flag `DISABLE_PROJECT_CONFIG`.
- Campos (`core/src/v1/config/config.ts`): `$schema, shell, logLevel, server, command, skills, references, watcher, snapshot, plugin, share, autoupdate, disabled_providers, enabled_providers, model, small_model, default_agent, subagent_depth, username, mode, agent, provider, mcp, formatter, lsp, instructions, layout, permission, tools, attachment, compaction, experimental, enterprise, policies, remote_config`.
- Merge profundo com concat de arrays; jsonc-parser para edição.
- Themes: JSONs embutidos em `packages/tui/src/theme/assets/*.json`.
- `models.json` via cache em `$cache/models.json`.

## 5. Agent loop (domínio central)

- **Loop externo:** `src/session/prompt.ts` (`runLoop`): while(true) → histórico → tasks (subtask/compaction) → cria msg assistente → resolve tools (`session/tools.ts`) → system prompt (`session/system.ts` + `prompt/*.txt`) → `handle.process()` → resultado `compact|stop|continue`; quebra quando finish ∉ {tool-calls, unknown}; `maxSteps` do agent.
- **Streaming/turno:** `src/session/processor.ts` — eventos `reasoning-*`, `text-*`, `tool-input-*`, `tool-call`, `tool-result`, `step-*`, `finish`; persiste Parts incrementalmente (`updatePartDelta`); doom-loop detector (3 chamadas idênticas → permissão); snapshot/patch por step; retry (`session/retry.ts`); cleanup em abort.
- **Chamada LLM:** `src/session/llm.ts` — Vercel AI `streamText`, repair de tool call → tool `invalid`; adaptador `session/llm/ai-sdk.ts` normaliza `fullStream` → `LLMEvent`.
- **V2 (direção):** `core/src/session/runner/llm.ts` — 1 `llm.stream()` por turno, tool calls persistidos duráveis antes do side-effect.

### Modelo de dados de sessão
- `Info` (id, slug, projectID, parentID, directory, title, agent, model, tokens, cost, summary, revert, permission[]) — `src/session/session.ts`.
- Parts (`schema/src/v1/session.ts`): `TextPart, ReasoningPart, ToolPart (state: pending|running|completed|error), StepStartPart, StepFinishPart, FilePart, PatchPart, SnapshotPart, CompactionPart, SubtaskPart`. IDs prefixados `msg_`, `prt_`.
- Mapeamento mensagens→provedor: `session/message-v2.ts`.

## 6. Tools

- **Contrato:** `src/tool/tool.ts` — `Def {id, description, parameters, jsonSchema, execute(args, ctx)}`; `ctx = {sessionID, messageID, agent, abort, messages, metadata(), ask()}`; validação + truncamento (`tool/truncate.ts`).
- **Registry:** `src/tool/registry.ts` — builtins: `invalid, question, shell, read, glob, grep, edit, write, task, webfetch, todowrite, websearch, skill, apply_patch` (+ flags `lsp`, `plan`, `execute/code-mode`); custom de `{tool,tools}/*.{js,ts}`; filtra por modelo (GPT-* → `apply_patch`) e permissão.
- **Implementações chave:** `read.ts`, `edit.ts`, `write.ts`, `shell/` (scan AST → permissões por comando), `grep.ts` (ripgrep), `glob.ts`, `apply_patch.ts`, `task.ts` (subagentes), `webfetch.ts`.

## 7. Permissions

- Modelo (`schema/src/v1/permission.ts`): `Rule {permission, pattern, action: allow|deny|ask}` wildcard; default `ask`; `reply: once|always|reject`.
- Serviço (`src/permission/index.ts`): `evaluate()` última regra vence (agent + session + approved); `ask()` publica evento e aguarda Deferred; `reply("always")` grava em `approved`; `disabled()` esconde tools deny.
- Call sites: read → `read.ts`; edit/write/apply_patch → `edit`; shell → scan AST por padrão de comando + `external_directory` fora do worktree; também glob/grep/task/skill/webfetch.

## 8. Providers/Models

- Catálogo: `core/src/models-dev.ts` (models.dev API + cache).
- Service: `src/provider/provider.ts` — `list/getProvider/getModel/getLanguage/closest/defaultModel`, `parseModel("provider/model")`, transformações por modelo (`provider/transform.ts`).
- Auth: `src/auth/index.ts` (`auth.json`), `provider/auth.ts` (oauth|api), Copilot OAuth em `core/src/github-copilot/`.
- Providers via Vercel AI SDK: anthropic, openai, google, azure, bedrock, copilot, openrouter, xai, openai-compatible (`llm/src/providers/`).

## 9. Server HTTP — rotas

`GET /api/health`, `GET /api/event` (SSE), `/api/session` (`/:id/{message,prompt,history,wait,interrupt,compact,event,revert/*,permission/*,question/*,model,agent,context}`), `/api/model`, `/api/provider[/:id]`, `/api/agent`, `/api/command`, `/api/skill`, `/api/fs/{list,read/*,find}`, `/api/pty[...]`, `/api/permission/request|saved`, `/api/question/request`, `/api/location`, `/api/credential`, `/api/integration`, `/api/reference`. OpenAPI em `/openapi.json`. Auth basic (user `opencode`).

## 10. TUI

- `packages/tui` — **@opentui/core + @opentui/solid (SolidJS)**, não ink/react. Entrada `src/index.tsx` → `run()` em `src/app.tsx`.
- Chat: `src/routes/session/{index,footer,sidebar,permission,question,dialog-timeline,dialog-subagent}.tsx`.
- Input: `src/component/prompt/{index,autocomplete,history,frecency,stash}.tsx`.
- Paleta/dialogs: `command-palette.tsx`, `dialog-{session-list,model,theme-list,mcp,provider,skill,...}.tsx`, `ui/dialog{,-alert,-confirm,-prompt,-select,-help}.tsx`, `toast.tsx`.
- Consome server via SDK: `src/context/sdk.tsx` (`createOpencodeClient`, SSE `sdk.global.event`, batching 16 ms, retry/backoff).
- Themes: `src/theme/assets/*.json` (dracula, catppuccin, github…).

## 11. Plugins

- API (`packages/plugin/src/index.ts`): `plugin = (input, options?) => Promise<Hooks>`; `PluginInput {client, project, $}`; hooks: `config, event, models, auth, provider, tool, dispose`.
- Declaração no config: `plugin: Array<string | [string, options]>`.
- Loader (`opencode/src/plugin/loader.ts`): resolve npm/dir/entry → instala → checa compat → import dinâmico com retry.
- TUI: slots em `packages/tui/src/plugin/slots.tsx`.

## 12. LSP / edição / diff

- `src/lsp/` — `lsp.ts` (clients, `touchFile`, `diagnostics()`), `client.ts/server.ts/launch.ts/diagnostic.ts` (pull diagnostics).
- Integração: `edit.ts` toca arquivo e injeta diagnósticos LSP no output; `tool/lsp.ts` (symbols/diagnostics para o LLM, flag).
- Diff/rollback: `src/snapshot/` (git-based) → `PatchPart` por step; `session/revert.ts`; formatters (`format/formatter.ts`: gofmt, prettier, ruff, biome).

## 13. Extensões de escopo a decidir (não são o tool em si)

- `packages/desktop` (Electron), `packages/web` (site Astro), `packages/enterprise`, `packages/slack`, `packages/console/*` (SaaS), `packages/function` (edge), `packages/cli` (binário legado `lildax`).
