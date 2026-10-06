# PRD Enxuto — Bombe Code

> Reimplementação em Python/UV do opencode (MIT). Storage: JSON em XDG (sem DB). Escopo: funcionalidades open-source.

## Prioridade (decisão do usuário)

**HARNESS PRIMEIRO** — o que importa é o ciclo vibe: pedir → agente executa → entrega o projeto.
- **Harness (núcleo, ordem fixa):** F1 config-storage → F2 providers-auth → F3 session-core → F5 tools → F6 permissions → F4 agent-loop → F7 server-http → F8 tui-chat → F9 cli.
- **Bônus (depois que o harness entrega):** F10 sdk, F11 web-ui, F12 lsp-snapshot, F13 plugins, F14 mcp-acp, F15 tui-complete, F16 desktop.
- Ciclos TDD nunca começam feature de bônus enquanto houver feature do harness pendente.

## Feature F1: config-storage
**Layer:** backend

### Regras de Negocio
- RN1: Paths seguem XDG via platformdirs: data `~/.local/share/bombe-code`, config `~/.config/bombe-code`, state, cache, log em `$data/log`.
- RN2: Descoberta de config sobe de cwd até a worktree procurando `bombe.json|bombe.jsonc` e `.bombe/`; fallback `~/.bombe`, env `BOMBE_CONFIG_DIR`.
- RN3: Merge profundo de configs com concat de arrays (paridade com `config.ts`).
- RN4: Storage JSON: KV arquivo-a-arquivo em `$data/storage/session/{info,message,part}/*.json` com lock por arquivo.

### Criterios de Aceitacao
- CA1: Dado cwd aninhado num projeto com `bombe.json`, quando a config e carregada, entao o merge e deterministico (mesma entrada → mesmo resultado).
- CA2: Dado storage vazio, quando uma sessao e criada, entao info/message/part existem como arquivos JSON legiveis.
- CA3: Dado dois processos escrevendo o mesmo arquivo, quando ha concorrencia, entao lock impede corrupcao (um espera ou falha explicita).

### Fluxos
- Happy path: boot → descobre config → carrega paths → storage pronto.
- Edge cases: sem config (defaults); config invalida (erro claro, sem crash); dir sem permissao.

### Dependencias
- Depende de: — (base de tudo)

## Feature F2: providers-auth
**Layer:** backend

### Regras de Negocio
- RN1: Catalogo de modelos baixa de models.dev API com cache em `$cache/models.json` (TTL 5 min), offline-first com cache stale.
- RN2: `parseModel("provider/model")` resolve provider e modelo; `closest()` e `defaultModel()` replicam a logica do original.
- RN3: Auth em `$data/auth.json` (chmod 600): API keys e tokens OAuth por provider.
- RN4: Providers suportados (paridade open-source): anthropic, openai, google, azure, bedrock, copilot, openrouter, xai, openai-compatible.

### Criterios de Aceitacao
- CA1: Dado cache valido (<5 min), quando `models()` e chamado, entao nenhuma requisicao de rede ocorre.
- CA2: Dado auth.json com key, quando uma chamada ao provider e feita, entao o arquivo mantem permissao 600.
- CA3: Dado `openai/gpt-4o`, quando parseado, entao provider=openai, model=gpt-4o.

### Fluxos
- Happy path: parse model → resolve provider → auth → chamada LLM.
- Edge cases: cache expirado offline; modelo inexistente; key ausente (erro orientado).

### Dependencias
- Depende de: F1

## Feature F3: session-core
**Layer:** backend

### Regras de Negocio
- RN1: Modelos Pydantic: Session (id `ses_`, slug, projectID, parentID, title, agent, model, tokens, cost, summary) e Parts (Text, Reasoning, Tool[state pending|running|completed|error], StepStart, StepFinish, File, Patch, Snapshot, Compaction, Subtask) com IDs `msg_`, `prt_`.
- RN2: CRUD integral no storage JSON (F1) com roundtrip from/to JSON estavel.
- RN3: System prompt montado por agent (base + instrucoes do projeto), paridade com `session/system.ts`.
- RN4: Mapeamento historico → mensagens de provedor (formato por provider).

### Criterios de Aceitacao
- CA1: Dada uma sessao com N mensagens, quando recarregada do disco, entao estado identico (roundtrip).
- CA2: Dado um ToolPart running, quando persistido e relido, entao state preservado.
- CA3: Dado input do usuario, quando turno e montado, entao mensagens do provedor sao validas segundo schema do provider.

### Fluxos
- Happy path: create session → append parts → reload → historico integro.
- Edge cases: arquivo corrompido (erro + skip); IDs duplicados (rejeitar).

### Dependencias
- Depende de: F1

## Feature F4: agent-loop
**Layer:** backend

### Regras de Negocio
- RN1: `runLoop`: while(true) → historico → subtask/compaction → cria msg assistente → resolve tools → system prompt → stream → `compact|stop|continue`; quebra quando finish sem tool calls; respeita `maxSteps`.
- RN2: Stream processor persiste Parts incrementalmente a cada evento (`text-delta`, `tool-input`, `tool-call`, `tool-result`, `step-*`, `finish`).
- RN3: Doom-loop: 3 tool calls identicas consecutivas → exige permissao.
- RN4: Abort cancela stream e limpa parts pendentes; retry com backoff em erros transitorios.
- RN5: Compaction e fork/revert de sessao replicam a semantica do original.

### Criterios de Aceitacao
- CA1: Dado prompt simples, quando o modelo responde sem tools, entao 1 mensagem assistant com 1 TextPart e estado stop.
- CA2: Dado modelo pedindo tool, quando tool executa, entao ciclo continua ate finish sem tools ou maxSteps.
- CA3: Dado 3 tool calls identicas, quando detectado doom-loop, entao fluxo pausa para permissao.
- CA4: Dado abort no meio do stream, quando verificado, entao parts ficam em estado consistente (sem running órfão).

### Fluxos
- Happy path: prompt → stream → tools → resposta final.
- Edge cases: erro de rede (retry); maxSteps atingido; compaction de contexto.

### Dependencias
- Depende de: F2, F3, F5, F6

## Feature F5: tools-system
**Layer:** backend

### Regras de Negocio
- RN1: Contrato Tool: `{id, description, parameters (Pydantic/jsonschema), execute(args, ctx)}`; ctx = {sessionID, messageID, agent, abort, messages, metadata(), ask()}.
- RN2: Builtins (paridade): `invalid, question, shell, read, glob, grep, edit, write, task, webfetch, todowrite, websearch, skill, apply_patch`.
- RN3: Validacao de args com InvalidArgumentsError; truncamento de output por limite de tokens.
- RN4: Custom tools de `{tool,tools}/*.{py,md}` + tools de plugins; filtro por modelo (GPT-* → apply_patch) e permissao.

### Criterios de Aceitacao
- CA1: Dado arg invalido, quando execute e chamado, entao InvalidArgumentsError e a LLM recebe feedback via tool invalid.
- CA2: Dado output gigante, quando truncado, entao limite respeitado com marcador de corte.
- CA3: Dado grep num repo, quando chamado, entao retorna matches com caminho:linha (usa ripgrep ou fallback py).

### Fluxos
- Happy path: tool-call evento → validate → permission check → execute → result.
- Edge cases: shell comando perigoso (permissão); arquivo inexistente; dir fora do worktree.

### Dependencias
- Depende de: F3, F6

## Feature F6: permissions
**Layer:** backend

### Regras de Negocio
- RN1: Rules `{permission, pattern, action: allow|deny|ask}` com wildcard; default `ask`; ultima regra vence (agent + session + approved).
- RN2: `ask()` publica evento e aguarda resposta UI (`once|always|reject`); `always` persiste em saved rules.
- RN3: Scan AST de shell por comando base → permissao `bash`; `external_directory` para paths fora do worktree.
- RN4: Tools com deny `*` ficam ocultas do modelo.

### Criterios de Aceitacao
- CA1: Dada regra allow `read ~/docs/*`, quando read nesse path, entao executa sem prompt.
- CA2: Dada acao ask, quando UI responde always, entao proxima chamada idempotente e regada.
- CA3: Dado `rm -rf /`, quando shell proposto, entao exige aprovacao (default ask/deny).

### Fluxos
- Happy path: tool chama ctx.ask → evaluate → allow segue / ask espera UI.
- Edge cases: sem UI conectada (fila/timeout); path com `~` e `$HOME`.

### Dependencias
- Depende de: F1

## Feature F7: server-http
**Layer:** backend

### Regras de Negocio
- RN1: FastAPI com rotas em paridade: `/api/health`, `/api/event` (SSE), `/api/session` (`/:id/{message,prompt,history,wait,interrupt,compact,event,revert/*,permission/*,question/*,model,agent,context}`), `/api/model`, `/api/provider[/:id]`, `/api/agent`, `/api/command`, `/api/skill`, `/api/fs/*`, `/api/permission/*`, `/api/question/*`.
- RN2: OpenAPI servido em `/openapi.json` (fonte para SDK).
- RN3: SSE de eventos com batching (~16ms) e IDs de evento para resume.
- RN4: Auth basic (user `bombe`) + CORS restrito a localhost.

### Criterios de Aceitacao
- CA1: Dado `POST /api/session/:id/prompt`, quando chamado, entao stream de eventos SSE chega em ordem.
- CA2: Dado `/openapi.json`, quando consumido, entao todas as rotas documentadas.
- CA3: Dado cliente SSE reconectando com Last-Event-ID, quando ha eventos novos, entao resume sem perda material.

### Fluxos
- Happy path: start server → client conecta SSE → prompt → eventos.
- Edge cases: server in-process da TUI; multi-client SSE; porta ocupada.

### Dependencias
- Depende de: F3, F4, F6

## Feature F8: tui-chat
**Layer:** frontend

### Regras de Negocio
- RN1: TUI Textual com chat (historico), prompt input com autocomplete/history, consumo via SSE do server real (sem mock).
- RN2: Render de Parts: texto, reasoning (colapsado), tool calls (estado pending/running/completed/error), diff de patch.
- RN3: Dialogs de permissao e question conectados aos endpoints de permission/question.
- RN4: Model/agent switcher e interrupt em turno ativo.

### Criterios de Aceitacao
- CA1: Dado server com sessao ativa, quando chega evento SSE text-delta, entao texto renderiza incrementalmente na TUI.
- CA2: Dado pedido de permissao, quando dialog abre, entao reply `once/always/reject` chega ao server.
- CA3: Dado Ctrl+C/interrupt, quando acionado, entao turno aborta e estado consistente.

### Fluxos
- Happy path: abrir TUI → selecionar modelo → prompt → resposta streaming.
- Edge cases: server caiu (retry/backoff); sessao longa (scroll).

### Dependencias
- Depende de: F7 (consome API real)

## Feature F9: cli
**Layer:** backend

### Regras de Negocio
- RN1: Typer com comandos em paridade: `run`, `tui` (default), `serve`, `web`, `models`, `providers`, `agent`, `session`, `export/import`, `mcp`, `acp`, `generate`, `plugin`, `debug`, `upgrade`, `version`.
- RN2: Server in-process para TUI/run (paridade com worker do original).
- RN3: Flags globais: `--model`, `--agent`, `--session`, `--continue`, `--port`.

### Criterios de Aceitacao
- CA1: Dado `bombe-code run "prompt" --model anthropic/claude`, quando executado, entao resposta sai no stdout e exit 0.
- CA2: Dado `bombe-code serve --port 4096`, quando sobe, entao `/api/health` responde.
- CA3: Dado `bombe-code` sem args, quando executado, entao TUI abre.

### Fluxos
- Happy path: CLI → server in-process → loop → stdout/TUI.
- Edge cases: porta ocupada; sem API key (erro orientado).

### Dependencias
- Depende de: F7, F4

## Feature F10: sdk-python
**Layer:** backend

### Regras de Negocio
- RN1: Cliente Python gerado do OpenAPI do proprio server (openapi-python-client ou equivalente), com typed models.
- RN2: Wrapper de eventos SSE alto nivel (async iterator de eventos tipados).
- RN3: Publicado como `bombe_code.sdk` (in-package).

### Criterios de Aceitacao
- CA1: Dado server local, quando SDK cria sessao e envia prompt, entao resposta tipada chega sem parsing manual.
- CA2: Dado openapi.json desatualizado, quando gerado, entao diff falha no CI (contrato travado).

### Fluxos
- Happy path: generate → client tipado → uso na TUI/web/plugins.
- Edge cases: schema drift; server offline.

### Dependencias
- Depende de: F7

## Feature F11: web-ui
**Layer:** frontend

### Regras de Negocio
- RN1: App Reflex espelhando `packages/app`: lista de sessoes, chat com streaming (SSE), terminal embutido, tabs.
- RN2: Consome a MESMA API do server (paridade de contratos com a TUI).
- RN3: Temas e atalhos espelham o original.

### Criterios de Aceitacao
- CA1: Dado server rodando, quando abre web-ui, entao sessoes existentes aparecem.
- CA2: Dado prompt na web, quando eventos SSE chegam, entao texto renderiza incrementalmente.
- CA3: Dado permission request, entao dialog web responde ao server.

### Fluxos
- Happy path: `bombe-code web` → browser → chat completo.
- Edge cases: multi-tab; reconexao SSE.

### Dependencias
- Depende de: F7, F10

## Feature F12: lsp-snapshot
**Layer:** backend

### Regras de Negocio
- RN1: Cliente LSP (pygls): launch de servers por linguagem, `touchFile`, pull diagnostics.
- RN2: Apos edit de arquivo, injeta diagnostics no output da tool (paridade com edit.ts).
- RN3: Snapshot git-based por step → PatchPart; `revert` restaura; formatter hook (prettier/ruff/gofmt conforme config).
- RN4: Tool `lsp` (symbols/diagnostics para LLM) sob flag.

### Criterios de Aceitacao
- CA1: Dado arquivo com erro LSP, quando edit aplicado, entao output da tool inclui diagnostic.
- CA2: Dado step com mudancas, quando snapshot criado, entao revert volta ao estado anterior.
- CA3: Dado formatter configurado, quando edit termina, entao arquivo formatado.

### Fluxos
- Happy path: edit → LSP diagnostics → snapshot → diff.
- Edge cases: LSP server ausente (degrada); repo sem git (snapshot off).

### Dependencias
- Depende de: F5

## Feature F13: plugins
**Layer:** backend

### Regras de Negocio
- RN1: API de plugin: `plugin(input, options) -> hooks {config, event, models, auth, provider, tool, dispose}`; input = {client, project, shell}.
- RN2: Loader resolve npm/dir/entry, instala, checa compatibilidade, import dinamico com retry.
- RN3: Declaracao no config: `plugin: [path | [path, options]]`.

### Criterios de Aceitacao
- CA1: Dado plugin local com hook `tool`, quando registry monta tools, entao tool custom aparece.
- CA2: Dado plugin quebrado, quando carregado, entao erro isolado nao derruba o boot.

### Fluxos
- Happy path: config aponta plugin → loader → hooks registrados.
- Edge cases: plugin incompativel; dependencia faltando.

### Dependencias
- Depende de: F1, F5

## Feature F14: mcp-acp
**Layer:** backend

### Regras de Negocio
- RN1: Cliente MCP (stdio + http): registra tools/resources de servers MCP como tools do agente.
- RN2: Comando `bombe-code mcp` (list/add/remove) e endpoint de gerencia.
- RN3: ACP (Agent Client Protocol): ponte para editores externos.

### Criterios de Aceitacao
- CA1: Dado server MCP configurado, quando boot, entao tools MCP disponíveis no registry.
- CA2: Dado `mcp list`, quando executado, entao servers e status.

### Fluxos
- Happy path: config mcp → conexao → tools expostas.
- Edge cases: server MCP morre (reconnect/fail-fast).

### Dependencias
- Depende de: F5, F9

## Feature F15: tui-complete
**Layer:** frontend

### Regras de Negocio
- RN1: Command palette (fuzzy), dialogs: session-list, model, theme, mcp, provider, skill.
- RN2: History com frecency, stash de prompts, autocomplete com `@`/`/`.
- RN3: Themes JSON (dracula, catppuccin, github…) e keymap configuravel.
- RN4: Dialogs de subagent (task) e timeline de eventos.

### Criterios de Aceitacao
- CA1: Dado palette aberto, quando digitado fuzzy, entao ranking por frecency.
- CA2: Dado theme trocado, quando renderiza, entao tokens aplicados sem restart.
- CA3: Dado prompt stashado, quando recuperado, entao volta ao input intacto.

### Fluxos
- Happy path: palette → comando → acao.
- Edge cases: centenas de sessões (virtualização); tecla custom.

### Dependencias
- Depende de: F8

## Feature F16: desktop
**Layer:** frontend

### Regras de Negocio
- RN1: Shell desktop (pywebview) embutindo a web-ui (F11), espelhando o papel do Electron.
- RN2: Menu, janela unica, abertura de URL externa via browser do SO.
- RN3: Auto-update desabilitado por padrao (sem infra propria).

### Criterios de Aceitacao
- CA1: Dado `bombe-code desktop`, quando abre, entao janela renderiza a web-ui autenticada no server local.
- CA2: Dado link externo, quando clicado, entao abre no browser do SO.

### Fluxos
- Happy path: desktop → webview → chat funcional.
- Edge cases: SO sem webview (erro orientado).

### Dependencias
- Depende de: F11

---

## Ordem de execucao sugerida (intercalacao frontend)
F1 → F2 → F3 → F5 → F6 → F4 → F7 → **F8** → F9 → F10 → **F11** → F12 → F13 → F14 → **F15** → **F16**
