---
status: "DONE"
id: "ST-020"
type: "feature"
agent: "@turing"
tdd: true
test_of: "src/bombe_code/turing/orchestrator.py"
test_type: "unit"
adr_ref: "docs/architecture/bombe-code-foundation-master.md"
depends_on: ["ST-019"]
ux_approved: true
snippet_ref: "set_mode, /mode"
estimation: "1h"
---

# ST-020: Gerenciador de Modos de Operação (/mode)

## Scope

**O que faz:**
Implementa a alternância dinâmica dos modos de autonomia (`auto`, `semi-auto`, `manual`) e de engenharia (`tdd-code`, `vibe-code`) através do comando `/mode`:
- Inspeciona o modo atual caso nenhum argumento seja passado.
- Permite alterar autonomia (`/mode auto`, `/mode manual`) ou engenharia (`/mode tdd`, `/mode vibe`).
- Sincroniza a alteração tanto no `.bombeconfig` quanto na `TuringStateMachine` e no SQLite local (`state.db`).

**O que NÃO faz:**
- ❌ Não corrompe o histórico de tasks existentes no SQLite.

## Interface (Input / Output)

```python
class WaveOrchestrator:
    def set_mode(self, mode_str: str) -> dict[str, Any]: ...
```

## Critérios de Aceite

1. `/mode` sem argumentos exibe os modos atuais e opções disponíveis.
2. `/mode manual` altera a autonomia para `MANUAL` no SQLite e no `.bombeconfig`.
3. `/mode tdd` atualiza o modo de engenharia para `tdd-code`.
