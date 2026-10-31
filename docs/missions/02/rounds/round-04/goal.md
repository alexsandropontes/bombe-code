---
round: 4
story_id: STORY-012
epic_id: EP-03
status: validated
started_at: "2026-10-31T19:05:00"
completed_at: "2026-10-31T19:20:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
dod_validated: true
---

# Objetivo do ROUND-4 — STORY-012: Wave Bridge e Interceptor de Depreciação

## 1. Round Goal
Implementar o interceptor de depreciação e ponte de retrocompatibilidade do Bombe Code (`wave_bridge.py`), interceptando deterministicamente os 7 comandos legados `bombe wave ...` (`start`, `run`, `cycle`, `validate`, `status`, `promote`, `end`), exibindo painel pedagógico formatado em Rich avisando sobre a transição definitiva de ondas para rounds e slices no Core v4, e despachando programaticamente para as primitivas canônicas modernas (`round`, `mission`, `project`), preservando códigos de saída POSIX e 100% dos testes unitários passando.

## 2. Escopo do Round
- **Story Alocada:** `STORY-012` (Wave Bridge e Interceptor de Depreciação).
- **Entregável Técnico:** Submódulo Typer `src/bombe_code/cli/commands/wave_bridge.py` acoplado ao entrypoint `src/bombe_code/cli/main.py`, modelos e enums de redirecionamento em `src/bombe_code/domain/contracts/wave_bridge.py`, renderizador de banner Rich de depreciação e suíte de testes unitários em `tests/unit/test_wave_bridge.py`.
- **Fronteira Negativa:** Não implementar ou reter motores proprietários legados de ondas (`WaveOrchestrator`) nem comandos avulsos/standalone (escopo do Round 5).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Sub-app Typer `wave_app` registrado no entrypoint `src/bombe_code/cli/main.py` interceptando a família de comandos `bombe wave`.
- [x] Modelos de contrato `WaveBridgeRedirect` e enum `LegacyWaveCommand` definidos em `src/bombe_code/domain/contracts/wave_bridge.py`.
- [x] Painel Rich educativo renderizado em console informando a substituição formal de "ondas" por "rounds e slices" no Core v4 (AC-01).
- [x] Redirecionamento 1:1 de `bombe wave start [ID]` para `bombe round start [N]` implementado com repasse de parâmetros (AC-02).
- [x] Redirecionamento 1:1 de `bombe wave run` para `bombe round all` implementado (AC-03).
- [x] Redirecionamento 1:1 de `bombe wave cycle [ID]` para `bombe round burn [N]` implementado (AC-04).
- [x] Redirecionamento dos comandos `validate`, `status`, `promote` e `end` para `round validate`, `round status`, `project ship` e `mission end` implementado (AC-05).
- [x] Preservação estrita dos códigos de retorno POSIX (exit code 0 em sucesso e propagação de códigos de erro) (AC-06).
- [x] Suíte `tests/unit/test_wave_bridge.py` testando o banner de depreciação e o redirecionamento dos 7 comandos legados com 100% de aprovação.
- [x] Zero ocorrências de `NotImplementedError`, `pass` ou stubs em código de produção.
- [x] Conformidade de linter com Ruff e tipagem estrita com Mypy.
- [x] Funções respeitando Single Responsibility Principle (SRF) com menos de 25 linhas cada.
- [x] Pureza de artefatos garantida (zero assinaturas decorativas ou rodapés institucionais em código de produção ou documentação persistida).
- [x] Code review de compliance aprovado pelo Reviewer (@hoare) e validação arquitetural pelo Tech Lead (@unclebob).
- [x] Validação final de DoD do round executada pelo Agile Master (@david).
