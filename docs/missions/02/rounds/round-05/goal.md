---
round: 5
story_id: STORY-013
epic_id: EP-04
status: validated
started_at: "2026-10-31T19:25:00"
completed_at: "2026-10-31T19:40:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
dod_validated: true
---

# Objetivo do ROUND-5 — STORY-013: Equalização de Comandos Standalone e Governança

## 1. Round Goal
Implementar os comandos standalone e de governança de projeto (`project configure`, `project ship [env]`, `mode`, `task`, `rca`, `review`, `simplify`, `status-report`) decompostos nos submódulos Typer `src/bombe_code/cli/commands/project.py` e `src/bombe_code/cli/commands/standalone.py`, com o motor `ShipEngine` em `src/bombe_code/orchestration/ship_engine.py` protegido deterministicamente por testes pre-flight antes de qualquer promoção Git, mantendo 100% de conformidade com a Constituição Bombe Core (Categorias B e C) e suíte de testes unitários passando com 100% de sucesso.

## 2. Escopo do Round
- **Story Alocada:** `STORY-013` (Equalização de Comandos Standalone e Governança).
- **Entregável Técnico:** Submódulos Typer `src/bombe_code/cli/commands/project.py` e `src/bombe_code/cli/commands/standalone.py` registrados em `src/bombe_code/cli/main.py`, motor de promoção `ShipEngine` em `src/bombe_code/orchestration/ship_engine.py`, motor de governança `StandaloneEngine` em `src/bombe_code/orchestration/standalone_engine.py` e suíte de testes unitários em `tests/unit/test_standalone_commands.py`.
- **Fronteira Negativa:** Não implementar testes de integração E2E da CLI (escopo do Round 6 / STORY-014) nem reintroduzir fluxos legados de ondas já interceptados pelo Wave Bridge no Round 4.

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Sub-apps Typer `project_app` e `standalone_app` registrados no entrypoint `src/bombe_code/cli/main.py`.
- [x] Comando `bombe project configure` implementado com validação Pydantic de paths, stack e guardrails no `.bombeconfig` (AC-01).
- [x] Comando `bombe project ship [dev|hml|prd]` implementado com execução prévia mandatória de suíte de testes pelo `ShipEngine` abortando com exit code 1 em caso de falha (AC-02).
- [x] Comando `bombe mode [slice-code|vibe-code]` implementado com comutação auditada gravando `mode_origin` e `mode_migrated_at` no `.bombeconfig` (AC-03).
- [x] Comando `bombe task '<desc>'` implementado com suporte a despacho via Protocolo Garçom para subagentes especializados (AC-04).
- [x] Comandos avulsos de qualidade (`bombe rca`, `bombe review`, `bombe simplify` e `bombe status-report`) implementados operando em modo standalone sem exigir missão ativa (AC-05).
- [x] Motor `ShipEngine` em `src/bombe_code/orchestration/ship_engine.py` com pre-flight test runner e merge seguro entre branches.
- [x] Suíte `tests/unit/test_standalone_commands.py` cobrindo todos os comandos e cenários de erro/sucesso do pre-flight com 100% de aprovação.
- [x] Zero ocorrências de `NotImplementedError`, `pass` ou stubs em código de produção.
- [x] Conformidade de linter com Ruff e tipagem estrita com Mypy.
- [x] Funções respeitando Single Responsibility Principle (SRF) com menos de 30 linhas cada.
- [x] Pureza de artefatos garantida (zero assinaturas decorativas ou rodapés institucionais em código de produção ou documentação persistida).
- [x] Code review de compliance aprovado pelo Reviewer (@hoare) e validação arquitetural pelo Tech Lead (@unclebob).
- [x] Validação final de DoD do round executada pelo Agile Master (@david).
