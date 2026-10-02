---
id: "ST-016"
type: "feature"
agent: "@valim"
tdd: true
test_of: "src/bombe_code/turing/orchestrator.py"
test_type: "unit"
adr_ref: "docs/architecture/bombe-code-wave2-arch.md"
depends_on: ["ST-015"]
ux_approved: true
snippet_ref: "run_discuss, run_plan"
estimation: "2h"
---

# ST-016: Comandos de Upstream (/wave discuss & /wave plan)

## Scope

**O que faz:**
Implementa os métodos de execução do Upstream no `WaveOrchestrator`:
- `run_discuss(topic: str)`: despacha `@meira` para gerar `docs/briefings/viability.md` e `@grace` para gerar `docs/briefings/PRD.md`.
- `run_plan()`: despacha a cadeia de planejamento técnico (`@alan`, `@norman`, `@ieru`, `@codd`, `@barreto`, `@caroli`) para produzir a jornada, arquitetura, dados, threat model e stories verticais.
- Valida os artefatos com `TemplateGate` antes de autorizar a transição para a próxima etapa.

**O que NÃO faz:**
- ❌ Não executa código de produção da aplicação nem testes (etapa downstream).

## Interface (Input / Output)

```python
class WaveOrchestrator:
    def run_discuss(self, topic: str, context: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def run_plan(self, context: dict[str, Any] | None = None) -> dict[str, Any]: ...
```

## Critérios de Aceite

1. `run_discuss` falha se a ONDA não estiver em estágio `DISCUSS`.
2. `run_discuss` executa `@meira` e `@grace` registrando as tarefas no SQLite local.
3. `run_plan` valida que `docs/briefings/PRD.md` existe antes de despachar os arquitetos.
