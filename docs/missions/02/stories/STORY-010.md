---
id: STORY-010
title: "Engine de Rounds Manuais com DoR Gate"
epic_id: EP-02
round: ROUND-2
agent: "@barbara"
estimation: 4h
status: done
type: feature
layer: backend
complexity: 3
depends_on: ["STORY-009"]
tags:
  - round-engine
  - dor-gate
  - tdd-slices
  - manual-rounds
---

# STORY-010 — Engine de Rounds Manuais com DoR Gate

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado
**Critérios INVEST:** Atendidos
**Prioridade:** Essencial / Bloqueante para Round 2

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (scope, interface, validações, SRF, anti-padrões, contratos de teste)
**Notas Técnicas:** Motor de execução de rounds manuais com parada determinística na DoR (`bombe round start`), queima TDD por slice (`round burn`), code review formal (`round review`) e validação de DoD (`round validate`).

---

## 1. Contexto de Negócio
No modo de condução manual, o engenheiro de software necessita de total controle e visibilidade sobre a etapa de Upstream técnico (detalhamento de contratos e fatiamento da story em slices) antes de liberar a implementação. O comando `bombe round start` deve obrigatoriamente parar na Definition of Ready (DoR), permitindo auditoria humana antes que o desenvolvedor execute a queima TDD atômica via `bombe round burn`.

---

## 2. Escopo

**O que faz:**
Implementa o submódulo Typer `src/bombe_code/cli/commands/round.py` e expande o `RoundExecutionEngine` em `src/bombe_code/orchestration/engine.py` para suportar os comandos manuais da Tríade: `bombe round start [N]`, `bombe round burn [N]`, `bombe round review [N]`, `bombe round validate [N]` e `bombe round status`. Inclui o gate bloqueante de DoR que impede queima sem Upstream validado.

**O que NÃO faz:**
- ❌ Não executa pipeline contínuo hands-free sem paradas (escopo da `STORY-011`).
- ❌ Não intercepta comandos legados de ondas (escopo da `STORY-012`).

**Limites:**
- [x] Camada de execução de rounds manuais.
- [x] Zero mocks em código de produção.
- [x] Testes unitários e de integração em `tests/unit/test_round_manual_engine.py`.

---

## 3. User Story & Intenção do Usuário
**Como** Desenvolvedor ou Tech Lead,  
**Quero** conduzir a esteira de desenvolvimento de um round passo a passo com parada determinística na DoR,  
**Para que** eu possa auditar o fatiamento da história antes de autorizar a queima de código e testes.

---

## 4. Acceptance Criteria (ACs Testáveis)
- [x] **AC-01 (Parada Determinística na DoR):** `bombe round start [N]` valida o DoD do round N-1, cria o scaffold do round (`goal.md`, `stories.md`), fatia a story em slices verticais e PARA deterministicamente com exit code 0 e status `dor_ready`.
- [x] **AC-02 (Gate Bloqueante de Queima):** `bombe round burn [N]` verifica se o round atingiu `dor_ready`; caso contrário, aborta com erro orientando a execução de `round start`.
- [x] **AC-03 (Queima TDD por Slice):** `bombe round burn [N]` executa o ciclo TDD (Slice Backend Red/Green/Refactor + Slice Frontend Construction) atualizando o estado dos slices.
- [x] **AC-04 (Review & Validate Gates):** `bombe round review [N]` audita compliance técnica (@hoare) e `bombe round validate [N]` valida critérios de aceite e DoD (@david), transicionando o round para `validated`.
- [x] **AC-05 (Inspeção Visual):** `bombe round status` exibe kanban detalhado com status de slices e quality gates.

---

## 5. Definition of Done (DoD)
- [x] Sub-app `round_app` criado em `src/bombe_code/cli/commands/round.py` com subcomandos manuais.
- [x] Contratos `RoundState`, `SliceState` e `RoundStatus` em `src/bombe_code/domain/contracts/round.py`.
- [x] Suíte `tests/unit/test_round_manual_engine.py` cobrindo os gates de entrada e saída.
- [x] Código aprovado no Ruff e Mypy sem warnings.

---

## 6. Notas Técnicas & Contratos

### 6.1 Contrato da CLI (Subcomandos Manuais)
```text
bombe round start [ROUND_NUMBER] [--project-dir PATH]
bombe round burn [ROUND_NUMBER] [--project-dir PATH]
bombe round review [ROUND_NUMBER] [--project-dir PATH]
bombe round validate [ROUND_NUMBER] [--project-dir PATH]
bombe round status [--project-dir PATH]
```

### 6.2 Estrutura de Código & SRF Check
| Função / Método | Assinatura | Responsabilidade | Limite |
|---|---|---|---|
| `RoundExecutionEngine.start_round` | `(round_num: int, project_dir: Path) -> RoundState` | Upstream, valida DoR e para | < 30 linhas |
| `RoundExecutionEngine.burn_round` | `(round_num: int, project_dir: Path) -> RoundState` | Queima TDD atômica dos slices | < 30 linhas |
| `RoundExecutionEngine.review_round` | `(round_num: int, project_dir: Path) -> RoundState` | Auditoria formal de conformidade | < 25 linhas |
| `RoundExecutionEngine.validate_round` | `(round_num: int, project_dir: Path) -> RoundState` | Valida DoD e marca como done | < 25 linhas |

**SRF Check:**
- [x] Nenhuma função possui "e" no nome.
- [x] Cada função cumpre apenas uma etapa da esteira.
- [x] Nenhuma função excede 30 linhas.

### 6.3 O que NÃO Fazer (Anti-padrões)
- ⛔ NÃO prosseguir para a queima automaticamente dentro do comando `bombe round start`.
- ⛔ NÃO permitir que `round burn` execute se houver pendência de DoD no round anterior.
- ⛔ NÃO usar mocks em testes de integração de filesystem.

---

## 7. Dependências
- **Blocked by:** `STORY-009` (Round 1 da MISSION-02 aprovado).
- **Required by:** `STORY-011` (Rounds Autônomos).
