# Segurança — Bombe Code

## 1. Nível

**Médio.** Ferramenta de desenvolvimento local que executa código sob demanda do usuário e fala com provedores LLM. Dados sensíveis: API keys (`auth.json`), conteúdo de arquivos do worktree, prompts (podem conter PII). Sem dados de terceiros, sem pagamento, sem multi-tenant.

## 2. Autenticação

- **Server HTTP:** basic auth (user `bombe`, password gerada e guardada em `$state/server-auth`, chmod 600) — parity com o original (user `opencode`). Bind em `127.0.0.1` apenas (nunca 0.0.0.0 por default).
- **API keys de providers:** `auth.json` em `$data/auth.json` com **chmod 600**; nunca em logs, erros ou eventos SSE.
- **Sem MFA/sessão web** no MVP (ferramenta local). Web-ui/desktop herdam o token basic do server local.

## 3. Autorização

- Modelo de permissions parity: `Rule {permission, pattern, action: allow|deny|ask}`, **default `ask`**, última regra vence; `reply: once|always|reject`; `always` persiste em saved rules.
- Superfícies: `read`, `edit`, `bash`, `external_directory`, `webfetch`, `websearch`, `task`, `skill`.
- Tools com deny `*` ficam ocultas do modelo (não expostas no registry).

## 4. Proteção de dados

- NUNCA logar: keys, tokens, headers de auth, conteúdo integral de `auth.json`.
- Logs em `$data/log` com redação automática de padrões `sk-*`, `Bearer *`, `ANTHROPIC_*` etc.
- Temporários de edição/snapshot em `$tmp` (permissão 700).
- Export de sessão não inclui `auth.json` nem config com segredos.

## 5. Threat model

| Ameaça | Mitigação |
|---|---|
| **Prompt injection → execução de shell maliciosa** | default `ask` em `bash`; scan AST por comando; aprovação humana na TUI/web |
| **Path traversal em read/write/edit/fs** | normalização + checagem de worktree; `external_directory` exige permissão; bloqueio de symlink escape |
| **Escrita fora do projeto** | mesma checagem de dir; blocklist implícita (`~/.ssh`, etc. via regra default ask/deny) |
| **Arquivo malicioso via webfetch** | limites de tamanho/timeout; não executa conteúdo baixado |
| **SSE/server local sequestrado** | bind localhost + basic auth; CORS apenas `http://127.0.0.1:*` |
| **Plugin hostil** | opt-in explícito no config; erros isolados; sem sandbox real (documentado como risco aceito, parity com original) |
| **Symlink/hardlink escape no storage** | storage só em paths XDG; validação de path resolvido |
| **Resource exhaustion via loop** | `maxSteps`, doom-loop detector (3 calls idênticas → ask), limites de output/truncate |
| **Command injection em formatter/shell tools** | sem `shell=True` com string do modelo; argv list; shell da tool com parser próprio |
| **Secrets em eventos SSE** | redação no barramento antes do broadcast |

## 6. Headers/CORS

- CORS: somente origens `127.0.0.1/localhost` na porta do server.
- Headers: `X-Content-Type-Options: nosniff`, `Cache-Control: no-store` no SSE; CSP restritiva na web-ui (Reflex).
- Sem HTTPS local (paridade; tool localhost).

## 7. Compliance de licença (obrigação do projeto)

- Licença do Bombe Code: **MIT** (arquivo LICENSE na raiz, ao final).
- Derivação do opencode (MIT): declarada no README + NOTICE de atribuição — **sem** comentários por função.
- Redistribution de themes/assets copiados do original: manter copyright notice MIT original.
