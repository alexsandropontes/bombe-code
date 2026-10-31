---
round: 3
story_id: STORY-011
epic_id: EP-02
status: validated
started_at: "2026-10-31T18:48:00"
completed_at: "2026-10-31T19:00:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
dod_validated: true
---

# Objetivo do ROUND-3 — STORY-011: Engine de Rounds Autônomos (Full & All)

## 1. Round Goal
Implementar o motor de execução de rounds autônomos do Bombe Code (`bombe round full [N]` para execução semi-automática de 1 story ponta a ponta e `bombe round all` para pipeline contínuo desatendido por todos os rounds da missão ativa sem perguntas vazias de cortesia), com tratamento de sinais de interrupção, parada determinística apenas sob erro real e 100% dos testes unitários passando.

## 2. Escopo do Round
- **Story Alocada:** `STORY-011` (Engine de Rounds Autônomos: Full & All).
- **Entregável Técnico:** Expansão dos comandos Typer `full` e `all` em `src/bombe_code/cli/commands/round.py`, métodos `execute_round_full` e `execute_round_all` em `src/bombe_code/orchestration/engine.py`, asserção de ausência de falhas `_assert_no_test_failures` e suíte de testes em `tests/unit/test_round_autonomous_engine.py`.
- **Fronteira Negativa:** Não implementar interceptores da Wave Bridge (escopo do Round 4) nem equalização de comandos avulsos/standalone (escopo do Round 5).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Subcomandos Typer `full` e `all` registrados em `round_app` (`src/bombe_code/cli/commands/round.py`) e acoplados ao `RoundExecutionEngine`.
- [x] Método `execute_round_full` implementado respeitando SRF (< 25 linhas) executando Upstream -> Burn -> Review -> Validate para o round N e consolidando relatório (AC-01).
- [x] Método `execute_round_all` implementado respeitando SRF (< 30 linhas) iterando sequencialmente por todos os rounds pendentes da missão ativa (AC-02).
- [x] Execução autônoma sem confirmações vazias: zero chamadas a `typer.confirm`, `input()` ou bloqueios em stdin durante `round all` (AC-03).
- [x] Interrupção imediata por falha real: se qualquer teste unitário ou gate de review falhar, aborta a execução contínua com exit code 1 (AC-04).
- [x] Exibição de sumário conclusivo ao término do último round em `round all`, instruindo encerramento via `bombe mission end` (AC-05).
- [x] Suíte de testes `tests/unit/test_round_autonomous_engine.py` cobrindo cenários de sucesso contínuo, interrupção por falha de teste e flags de timeout com 100% de aprovação.
- [x] Zero ocorrências de `NotImplementedError`, `pass` ou stubs em código de produção.
- [x] Conformidade de linter com Ruff e tipagem estrita com Mypy.
- [x] Funções respeitando Single Responsibility Principle (SRF) com menos de 30 linhas cada.
- [x] Pureza de artefatos garantida (zero assinaturas decorativas ou rodapés institucionais em código de produção ou documentação persistida).
- [x] Code review de compliance aprovado pelo Reviewer (@hoare) e validação arquitetural pelo Tech Lead (@unclebob).
- [x] Validação final de DoD do round executada pelo Agile Master (@david).
