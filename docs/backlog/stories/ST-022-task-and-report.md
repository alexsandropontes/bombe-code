---
status: "DONE"
id: "ST-022"
type: "feature"
agent: "@turing"
tdd: true
test_of: "src/bombe_code/turing/orchestrator.py"
test_type: "unit"
adr_ref: "docs/architecture/bombe-code-foundation-master.md"
depends_on: ["ST-015"]
ux_approved: true
snippet_ref: "run_task, generate_status_report"
estimation: "2h"
---

# ST-022: Tasks Pontuais (/task) e Relatório Consolidado (/report status)

## Scope

**O que faz:**
Implementa os comandos de operação pontual e visibilidade:
- `/task <descrição>`: Permite despachar uma solicitação avulsa a um agente especialista sem violar nem avançar a máquina de estados da ONDA ativa, persistindo no Kanban de `agent_tasks`.
- `/report status`: Gera relatório executivo consolidado com status da ONDA, métricas de fluxo, contagem de tasks e resumo do estado de engenharia.

**O que NÃO faz:**
- ❌ Não altera o estado da ONDA ativa ao rodar uma task avulsa.

## Interface (Input / Output)

```python
class WaveOrchestrator:
    def run_task(self, description: str, agent_handle: str | None = None) -> dict[str, Any]: ...
    def generate_status_report(self) -> dict[str, Any]: ...
```

## Critérios de Aceite

1. `run_task` registra uma tarefa com status `completed` no SQLite e executa sem alterar o `stage` da ONDA.
2. `generate_status_report` consolida métricas do banco local e status dos gates.
