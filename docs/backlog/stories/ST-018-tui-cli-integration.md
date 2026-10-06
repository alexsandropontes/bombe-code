---
status: "DONE"
id: "ST-018"
type: "feature"
agent: "@ada"
tdd: true
test_of: "src/bombe_code/tui/commands.py"
test_type: "integration"
adr_ref: "docs/architecture/bombe-code-wave2-arch.md"
depends_on: ["ST-015", "ST-016", "ST-017"]
ux_approved: true
snippet_ref: "handle_slash_command (/wave)"
estimation: "2h"
---

# ST-018: Integração com TUI Textual & CLI Typer

## Scope

**O que faz:**
Registra e integra os comandos `/wave` tanto na TUI Textual (`src/bombe_code/tui/commands.py`) quanto na CLI Typer (`src/bombe_code/cli/main.py`), permitindo a invocação unificada:
- `/wave start [ID]`
- `/wave status`
- `/wave discuss`
- `/wave plan`
- `/wave cycle [ST-XXX]`
- `/wave execute`
- `/wave validate`
- `/wave end`
Adiciona suporte a autocomplete e feedback visual formatado com tokens do tema visual.

**O que NÃO faz:**
- ❌ Não mantém comandos legados baseados em `/tdd` (substituição integral por `/wave`).

## Critérios de Aceite

1. Digitar `/wave status` na TUI ou executar `bombe-code wave status` na CLI deve invocar o `WaveOrchestrator` e exibir as informações formatadas.
2. Autocomplete da TUI deve sugerir a família de comandos `/wave`.
3. Erros de validação ou de gate devem ser renderizados com cores e orientações determinísticas de recuperação.
