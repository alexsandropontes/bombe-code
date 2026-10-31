---
round: 2
story_id: STORY-010
epic_id: EP-02
status: validated
started_at: "2026-10-31T18:30:00"
completed_at: "2026-10-31T18:45:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-2 — STORY-010: Engine de Rounds Manuais com DoR Gate

## 1. Round Goal
Implementar o motor de execução de rounds manuais do Bombe Code com parada determinística na Definition of Ready (`bombe round start`), queima TDD de slices verticais (`bombe round burn`), code review de conformidade (`bombe round review`), validação formal de DoD (`bombe round validate`) e visualização de status em kanban (`bombe round status`), assegurando gate bloqueante de entrada e saída com WIP = 1 e 100% dos testes unitários passando.

## 2. Escopo do Round
- **Story Alocada:** `STORY-010` (Engine de Rounds Manuais com DoR Gate).
- **Entregável Técnico:** Submódulo Typer `src/bombe_code/cli/commands/round.py`, expansão de `RoundExecutionEngine` em `src/bombe_code/orchestration/engine.py` (métodos `start_round`, `burn_round`, `review_round`, `validate_round`), contratos `RoundState`, `SliceState` e `RoundStatus` em `src/bombe_code/domain/contracts/round.py` e suíte de testes em `tests/unit/test_round_manual_engine.py`.
- **Fronteira Negativa:** Não implementar pipeline contínuo hands-free sem paradas (`bombe round full` / `bombe round all` — escopo do Round 3) nem interceptores da Wave Bridge (escopo do Round 4).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Sub-app Typer `round_app` criado em `src/bombe_code/cli/commands/round.py` e acoplado à CLI raiz em `src/bombe_code/cli/main.py`.
- [x] Modelos de contrato Pydantic V2 `RoundState`, `SliceState` e `RoundStatus` definidos em `src/bombe_code/domain/contracts/round.py`.
- [x] Invocação de `bombe round start [N]` valida o DoD do round anterior, gera os scaffolds físicos (`goal.md`, `stories.md`, `capacity.md`), fatia a história em slices verticais e PARA deterministicamente com status `dor_ready` (AC-01).
- [x] Invocação de `bombe round burn [N]` atua como gate bloqueante: aborta caso o round não esteja em `dor_ready` e executa a queima TDD dos slices cadastrados (AC-02 e AC-03).
- [x] Invocação de `bombe round review [N]` executa auditoria formal de compliance técnica e qualidade de código (@hoare) (AC-04).
- [x] Invocação de `bombe round validate [N]` valida todos os critérios de aceite e checkboxes de DoD, atualizando o status para `validated` (AC-04).
- [x] Subcomando `bombe round status` exibe quadro kanban formatado via Rich com status dos rounds, slices e quality gates (AC-05).
- [x] Suíte de testes `tests/unit/test_round_manual_engine.py` cobrindo gates de entrada (DoR), bloqueio de queima prematura, ciclo TDD e validação com 100% de sucesso.
- [x] Zero ocorrências de `NotImplementedError`, `pass` ou stubs em código de produção.
- [x] Conformidade de linter com Ruff e tipagem estrita com Mypy.
- [x] Funções respeitando Single Responsibility Principle (SRF) com menos de 30 linhas cada.
- [x] Pureza de artefatos garantida (zero assinaturas decorativas ou rodapés institucionais em código de produção ou documentação persistida).
- [x] Code review de compliance aprovado pelo Reviewer (@hoare) e validação arquitetural pelo Tech Lead (@unclebob).
- [x] Validação final de DoD do round executada pelo Agile Master (@david).
