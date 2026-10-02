# Design System MVP — Bombe Code

> Tokens e componentes para TUI (Textual) e web-ui (Reflex), parity visual com opencode (themes JSON, mesma linguagem de componentes).

## 1. Identidade visual

- **Paleta base (dark default):** fundo `#1e1e2e`, superfície `#181825`, texto `#cdd6f4`, primária `#89b4fa`, sucesso `#a6e3a1`, erro `#f38ba8`, aviso `#f9e2af`, muted `#6c7086` (equivalente Catppuccin Mocha — paridade com themes do original).
- **Themes:** JSON idêntico em estrutura aos do original (`tui/theme/assets/*.json`): dracula, catppuccin (mocha/macchiato), github dark/light, tokyonight. Troca em runtime, sem restart.
- **Tipografia:** TUI — fonte do terminal (monospace padrão); web — system font stack monospace para blocos de código, `Inter/system-ui` para chrome.
- **Espaçamento:** grid de 4px (web) / células (TUI): 4/8/12/16/24.

## 2. Componentes base (inventário paridade)

**TUI (Textual):**
- `PromptInput` — textarea expansível, autocomplete `@`/`/`, history (↑/↓), frecency, stash (ctrl+s)
- `PartsView` — render de TextPart, ReasoningPart (colapsável), ToolPart (estado colorido: pending=muted, running=animated, completed=success, error=error), PatchPart (diff)
- `Dialog` base + variantes: alert, confirm, prompt, select, help
- `PermissionDialog` — ações Allow once / Always / Reject
- `QuestionDialog` — resposta livre à pergunta do agente
- `CommandPalette` — fuzzy search com frecency
- `SessionList`, `ModelSwitcher`, `ThemeSwitcher`, `McpDialog`, `ProviderDialog`, `SkillDialog`
- `Toasts` (info/success/error), `Footer` (keymap), `Sidebar` (sessões)

**Web (Reflex) — espelho da lista acima:** `chat_view`, `session_list`, `prompt_input`, `permission_modal`, `question_modal`, `model_picker`, `terminal_embed`, `toast`.

## 3. Padrões de interação

- **Loading:** spinner de stream (texto incremental NÃO fica em bracelete — só o cursor inicial).
- **Error:** toast + estado retry; SSE cai → banner "reconectando (backoff)".
- **Empty:** "Nova sessão — descreva o que você quer construir" + dica de atalhos.
- **Permission:** modal não-bloqueante do fluxo; `always` mostra aviso "afeta regras salvas".
- **Interrupt:** `Esc`/ctrl+c sempre interrompe turno ativo e mostra "interrompido".

## 4. Design tokens

- Arquivo único `tokens.py` (TUI) exportando dicionário espelhado em `web/assets/theme.py` — mesma origem lógica, dois renderers.
- Sem CSS arbitrário na web: variáveis CSS (`--bc-bg`, `--bc-fg`, `--bc-accent`…) geradas do mesmo dicionário.

## 5. Acessibilidade (WCAG 2.1 AA no web; no TUI contraste alto)

- Contraste mínimo 4.5:1 para texto corrente; nunca só cor para estado (sempre ícone/texto junto: ✓/✗/…).
- Focus ring visível em todos os controles web; na TUI, seleção reversa.
- Atalhos documentados em `?` (help dialog); labels explícitos em inputs web (aria-label).
- Respeito a `prefers-reduced-motion` (web) e animações mínimas na TUI.
