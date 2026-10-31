---
round: 1
story_id: STORY-009
epic_id: EP-01
status: validated
started_at: "2026-10-31T18:10:00"
completed_at: "2026-10-31T18:25:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-1 — STORY-009: Porteiro Atômico e Lifecycle de Missões

## 1. Round Goal
Implementar o ciclo de vida soberano de missões do Bombe Code (`bombe mission new`, `bombe mission status` e `bombe mission end`) integrado ao porteiro atômico `assert_no_open_mission()` baseado em filesystem, garantindo WIP = 1 e integridade referencial dos artefatos em `docs/missions/` com 100% dos testes unitários passando.

## 2. Escopo do Round
- **Story Alocada:** `STORY-009` (Porteiro Atômico e Lifecycle de Missões).
- **Entregável Técnico:** Subcomando Typer `src/bombe_code/cli/commands/mission.py`, motor de ciclo de vida `src/bombe_code/orchestration/mission_engine.py`, modelos de contrato Pydantic V2 em `src/bombe_code/domain/contracts/mission.py` e suíte de testes em `tests/unit/test_mission_lifecycle.py`.
- **Fronteira Negativa:** Não implementar engine de rounds manuais (Round 2), rounds autônomos (Round 3) ou interceptores da Wave Bridge (Round 4).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Módulos `src/bombe_code/cli/commands/mission.py` e `src/bombe_code/orchestration/mission_engine.py` criados e integrados à CLI raiz em `src/bombe_code/cli/main.py`.
- [x] Modelos Pydantic V2 `MissionState` e `MissionStatus` definidos em `src/bombe_code/domain/contracts/mission.py`.
- [x] Invocação de `bombe mission new` aborta com exit code 1 e mensagem explícita caso exista missão em status `open`, `active` ou `in_progress` (AC-01).
- [x] Scaffolding físico completo gerado em caminho feliz com próximo ID sequencial (`docs/missions/NN/` e subdiretórios `prd/`, `architecture/`, `epics/`, `stories/`, `rounds/`) (AC-02).
- [x] Subcomando `bombe mission status` imprime tabela Rich formatada com status e lista de rounds da missão ativa (AC-03).
- [x] Subcomando `bombe mission end` valida DoD de rounds antes do fechamento e atualiza status para `completed` com timestamp (AC-04).
- [x] Suíte de testes `tests/unit/test_mission_lifecycle.py` passando com 100% de sucesso usando `tmp_path`.
- [x] Zero ocorrências de `NotImplementedError`, `pass` ou stubs em código de produção.
- [x] Conformidade de linter com Ruff e tipagem estrita com Mypy.
- [x] Pureza de artefatos garantida (zero assinaturas decorativas ou rodapés institucionais em código de produção ou documentação persistida).
- [x] Code review de compliance aprovado pelo Reviewer (@hoare) e validação arquitetural pelo Tech Lead (@unclebob).
- [x] Validação final de DoD do round executada pelo Agile Master (@david).
