---
status: "DONE"
id: "ST-017"
type: "feature"
agent: "@valim"
tdd: true
test_of: "src/bombe_code/turing/orchestrator.py"
test_type: "unit"
adr_ref: "docs/architecture/bombe-code-wave2-arch.md"
depends_on: ["ST-015", "ST-016"]
ux_approved: true
snippet_ref: "run_cycle, run_execute, run_validate, end_wave"
estimation: "3h"
---

# ST-017: Comandos de Downstream (/wave cycle, /wave execute, /wave validate, /wave end)

## Scope

**O que faz:**
Implementa os fluxos executivos da ONDA no `WaveOrchestrator`:
- `run_cycle(story_id: str | None = None)`: **Atômico (1 Story)**. Identifica a próxima story pendente (ou a fornecida), executa o ciclo TDD (RED ➔ GREEN ➔ REFACTOR) com o especialista da stack, submete ao `@unclebob` para review e **para imediatamente**, aguardando o usuário.
- `run_execute(on_story_completed: Callable | None = None)`: **Lote Total (Cycle-Full)**. Executa da Story 1 até a última. No modo `MANUAL`/`SEMI_AUTO`, invoca `on_story_completed` para pausar e solicitar confirmação do usuário antes de prosseguir.
- `run_validate()`: Despacha `@edith` (auditoria PRD vs. Entregável e Selo Final) e `@nina` (FinOps e tokens).
- `end_wave()`: Verifica se o Selo Final do Validador existe e finaliza a ONDA como `COMPLETED`.

**O que NÃO faz:**
- ❌ Não pula o review do Tech Lead nem permite concluir story sem teste prévio.

## Interface (Input / Output)

```python
class WaveOrchestrator:
    def run_cycle(self, story_id: str | None = None) -> dict[str, Any]: ...
    def run_execute(
        self, confirm_callback: Callable[[str], bool] | None = None
    ) -> dict[str, Any]: ...
    def run_validate(self) -> dict[str, Any]: ...
    def end_wave(self) -> dict[str, Any]: ...
```

## Critérios de Aceite

1. `run_cycle` atua em exatamente uma story e retorna com status `completed` ou `failed`, sem avançar sozinho para a próxima.
2. `run_execute` em modo `MANUAL` pausa a cada story concluída se `confirm_callback` retornar `False` ou se for solicitado cancelamento.
3. `run_validate` só aprova se os testes passarem e `@edith` emitir o relatório de validação.
4. `end_wave` arquiva a ONDA no SQLite com status `COMPLETED`.
