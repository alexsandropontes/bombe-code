---
id: STORY-007
title: "Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI"
epic_id: EP-03
round: ROUND-7
agent: "@barbara"
estimation: 4h
status: done
type: feature
layer: backend
depends_on:
  - STORY-006
tags:
  - kanban
  - cli
  - execution-engine
  - round-start
  - round-full
  - round-all
---

# STORY-007 — Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI

## 1. Scope

**O que faz:**
Implementa o `RoundExecutionEngine` e os comandos CLI da tríade operacional (`round-start`, `round-full`, `round-all`) no Typer, garantindo deterministicamente a invariante **1 Round = 1 Story**, a sincronização atômica do Kanban no `mission.md` e o bloqueio de transição caso o round anterior contenha pendências de Definition of Done (DoD).

**O que NÃO faz:**
- ❌ Não executa o scaffolding da Inception Macro (Round 0 permanece sob responsabilidade do Upstream Macro).
- ❌ Não altera o fluxo interno de queima de slices TDD (RED -> GREEN -> REFACTOR).
- ❌ Não permite avanço de round se existirem caixas `- [ ]` no DoD do round anterior.

**Limites:**
- [x] Apenas camada de backend (`src/bombe_code/orchestration/` e `src/bombe_code/cli/commands/`) e testes em `tests/unit/`.
- [x] Zero modificações em pastas de runtime do Bombe Core (`.agents/`, `CLAUDE.md`, `.bombeconfig`).

---

## 2. Interface (Input / Output)

### Contrato Python (`RoundExecutionEngine`)
```python
class RoundExecutionEngine:
    def __init__(self, project_dir: Path | str = ".") -> None: ...
    def validate_round_scope(self, stories: list[str] | str) -> str: ...
    def assert_no_dod_pendencies(self, round_num: int) -> None: ...
    def sync_mission_kanban(self, round_num: int, status: str, story_status: str | None = None) -> None: ...
    def start_round(self, round_num: int) -> dict[str, Any]: ...
    def full_round(self, round_num: int) -> dict[str, Any]: ...
    def all_rounds(self) -> list[dict[str, Any]]: ...
```

### Contrato CLI Typer
```bash
bombe-code round-start [ROUND_NUM] [--project-dir .]
bombe-code round-full [ROUND_NUM] [--project-dir .]
bombe-code round-all [--project-dir .]
```

### Regras de Validação & Exceções:
- **Invariante 1 Round = 1 Story:** Se `len(stories) != 1` ou se houver múltiplos identificadores separados por vírgula/espaço -> Levanta `InvalidRoundScopeError("Invariante violada: 1 Round deve conter exatamente 1 Story.")`.
- **DoD Pendente:** Se o arquivo `goal.md` do round anterior contiver uma ou mais linhas com `- [ ]` -> Levanta `PendingDoDError("Round anterior N possui pendências de Definition of Done não concluídas.")`.

---

## 3. Slices Verticais de Implementação

### SLICE-01: `RoundExecutionEngine` e Invariantes Kanban
- **Tipo:** Backend (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Arquivo de Teste:** `tests/unit/test_round_execution_engine.py`
- **Arquivo de Produção:** `src/bombe_code/orchestration/engine.py`
- **Critérios de Aceite Cobertos:** AC-01, AC-05, AC-02 (núcleo), AC-03 (núcleo), AC-04 (núcleo)
- **Escopo Técnico:**
  - Classes de exceção `InvalidRoundScopeError` e `PendingDoDError`.
  - Validação estrita 1 Round = 1 Story via `validate_round_scope`.
  - Porteiro bloqueante `assert_no_dod_pendencies`.
  - Mecanismo de persistência e atualização atômica de `mission.md`.
  - Métodos `start_round`, `full_round` e `all_rounds`.

### SLICE-02: Tríade CLI Typer (`round-start`, `round-full`, `round-all`)
- **Tipo:** Backend / CLI (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Arquivo de Teste:** `tests/unit/test_round_execution_engine.py`
- **Arquivo de Produção:** `src/bombe_code/cli/commands/round.py` e `src/bombe_code/cli/main.py`
- **Critérios de Aceite Cobertos:** AC-02, AC-03, AC-04
- **Escopo Técnico:**
  - Registro do Typer app `round_app` e comandos `round-start`, `round-full`, `round-all`.
  - Tratamento de exceções e formatação de saída amigável via console Typer.
  - Suíte de testes com `CliRunner` validando invocação CLI e códigos de saída.

---

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Invariante 1:1):** Rejeita registrar mais de uma história no mesmo round levantando `InvalidRoundScopeError`.
- **AC-02 (Comando round-start):** Atualiza status para `in_progress` e interrompe a execução deterministicamente na fronteira do DoR.
- **AC-03 (Comando round-full):** Executa Upstream + Downstream + Validate da story do round e finaliza sem avançar para o próximo round.
- **AC-04 (Comando round-all):** Itera sequencialmente pelos rounds pendentes da missão, parando apenas diante de falha ou conclusão da missão.
- **AC-05 (Bloqueio por Pendência de DoD):** Nenhuma execução de round inicia se o round anterior contiver itens `- [ ]` pendentes.

---

## 5. Definition of Done (DoD)
- [x] Implementação de `RoundExecutionEngine` em `src/bombe_code/orchestration/engine.py` sob tipagem estrita (`mypy --strict`).
- [x] Implementação dos comandos Typer em `src/bombe_code/cli/commands/round.py` e registro no CLI principal `src/bombe_code/cli/main.py`.
- [x] Suíte de testes completa passando em `tests/unit/test_round_execution_engine.py` com 100% de sucesso.
- [x] Zero corpos vazios (`pass`, `...`), zero stubs em produção e zero violações de Clean Code.
- [x] Code review do Tech Lead (@unclebob) aprovado.

## 6. Code Review & Approval
| Data | Reviewer | Eixos Avaliados | Status | Notas |
| :--- | :--- | :--- | :--- | :--- |
| 2026-10-31 | @hoare | Story Compliance & Traceability | APPROVED | 100% dos ACs atendidos e verificados |
| 2026-10-31 | @unclebob | Correctness, Readability, Architecture, Security, Performance | APPROVED | Zero violações de SOLID; invariante 1:1 e Tríade CLI validadas |

## 7. Dependências
- **Bloqueado por:** `STORY-006` (Round 6 concluído).
- **Desbloqueia:** `STORY-008` (Round 8).

---

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (Scope, Interface, SRF Check, Anti-padrões, Invariante 1:1, Porteiro DoD, Slices Verticais TDD)
**Notas Técnicas:** Slicing aprovado em 2 slices atômicos verticais. A desenvolvedora backend (@barbara) está formalmente autorizada a iniciar a queima do SLICE-01 no ciclo TDD (RED -> GREEN -> REFACTOR).
