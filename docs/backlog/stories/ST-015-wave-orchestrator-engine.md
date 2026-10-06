---
status: "DONE"
id: "ST-015"
type: "feature"
agent: "@valim"
tdd: true
test_of: "src/bombe_code/turing/orchestrator.py"
test_type: "unit"
adr_ref: "docs/architecture/bombe-code-wave2-arch.md"
depends_on: ["ST-001", "ST-002", "ST-003", "ST-014"]
ux_approved: true
snippet_ref: "WaveOrchestrator"
estimation: "2h"
---

# ST-015: Motor WaveOrchestrator Central

## Scope

**O que faz:**
Implementa a classe `WaveOrchestrator` em `src/bombe_code/turing/orchestrator.py`, atuando como ponto único de coordenação entre a máquina de estados (`TuringStateMachine`), a persistência local (`ProjectDatabase`), o catálogo de especialistas (`AgentRegistry`), o executor de IA (`AgentRunner`) e os gates determinísticos (`TemplateGate`, `SealGate`).

**O que NÃO faz:**
- ❌ Não implementa a UI gráfica ou widgets do Textual.
- ❌ Não substitui os gates determinísticos existentes.

**Limites:**
- [x] Apenas camada de orquestração do Turing (`bombe_code.turing`).
- [x] Opera com SQLite síncrono local em `.bombe-code/state.db`.

## Interface (Input / Output)

```python
class WaveOrchestrator:
    def __init__(
        self,
        project_dir: str = ".",
        db: ProjectDatabase | None = None,
        state_machine: TuringStateMachine | None = None,
        registry: AgentRegistry | None = None,
        llm_factory: PydanticAiFactory | None = None,
    ) -> None: ...

    def start_wave(self, wave_id: str) -> dict[str, Any]: ...
    def get_status(self) -> dict[str, Any]: ...
    def transition_to(self, target_stage: TuringStage) -> bool: ...
```

## Critérios de Aceite

1. `start_wave("ONDA-004")` deve inicializar o estado no SQLite com estágio `DISCUSS`.
2. `get_status()` deve retornar dados estruturados: `wave_id`, `stage`, `autonomy_mode`, `engineering_mode`, `tasks_summary`.
3. `transition_to(stage)` deve validar transições válidas na `TuringStateMachine` e persistir a alteração.
