---
id: "ST-021"
type: "feature"
agent: "@unclebob"
tdd: true
test_of: "src/bombe_code/turing/orchestrator.py"
test_type: "unit"
adr_ref: "docs/architecture/bombe-code-foundation-master.md"
depends_on: ["ST-015"]
ux_approved: true
snippet_ref: "run_rca, run_simplify"
estimation: "2h"
---

# ST-021: Módulo Forense RCA (/rca) e Simplificação YAGNI (/simplify)

## Scope

**O que faz:**
Implementa os comandos de diagnóstico e qualidade antientropia:
- `/rca <incidente>`: Despacha `@unclebob` (Tech Lead) e `@diego` (AppSec) para investigar a causa raiz de uma falha ou bug, gerando um relatório em `docs/rca/RCA-XXX.md` com análise dos 5 Porquês, diagrama Ishikawa e plano de correção.
- `/simplify <alvo>`: Despacha `@ieru` e `@unclebob` para inspecionar um arquivo ou módulo, identificar violações de YAGNI, complexidade ciclomática excessiva e sugerir/aplicar a simplificação mais elegante.

**O que NÃO faz:**
- ❌ Não executa sem registrar a task no SQLite do projeto.

## Interface (Input / Output)

```python
class WaveOrchestrator:
    def run_rca(self, incident: str) -> dict[str, Any]: ...
    def run_simplify(self, target: str) -> dict[str, Any]: ...
```

## Critérios de Aceite

1. `run_rca("Erro 500 no login")` gera relatório estruturado de RCA e registra tarefa.
2. `run_simplify("src/auth/service.py")` retorna plano cirúrgico de redução de complexidade.
