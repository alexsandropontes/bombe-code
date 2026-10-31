---
round: 1
story_id: STORY-001
epic_id: EP-01
status: done
started_at: "2026-10-31T15:49:00"
completed_at: "2026-10-31T15:58:00"
maturity_level: enterprise-grade
layer: backend
agent: "@fowler"
---

# Objetivo do ROUND-1 — STORY-001: Migração de Configuração e Runtime Slice-Code

## 1. Round Goal
Migrar o arquivo de configuração raiz `.bombeconfig` e o subsistema de configuração em `src/bombe_code/config/` do modelo obsoleto `tdd-code` para a esteira unificada `slice-code`, estabelecendo rastreabilidade histórica via `mode_origin: tdd-code` e blindagem determinística via Pydantic V2 com 100% dos testes unitários passando.

## 2. Escopo do Round
- **Story Alocada:** `STORY-001` (Migração de Configuração e Runtime Slice-Code).
- **Entregável Técnico:** Novo schema de configuração Pydantic V2, `.bombeconfig` atualizado, suite de testes unitários em `tests/unit/test_config.py` e validação estrita de runtime.
- **Fronteira Negativa:** Não tocar em dossiês de agentes (Round 2) nem em orquestração de LLMs (Round 3).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] O arquivo `.bombeconfig` na raiz do projeto está atualizado com `mode: "slice-code"`, `mode_origin: "tdd-code"` e `mode_migrated_at`.
- [x] O schema de configuração em `src/bombe_code/config/` valida determinísticamente as novas chaves via Pydantic V2.
- [x] Modos legados extintos (`tdd-code`, `spec-code`) disparam `InvalidModeError` se informados como modo ativo sem migração.
- [x] Suíte de testes unitários implementada em `tests/unit/test_config.py` cobrindo AC-01 a AC-04 com 100% de aprovação.
- [x] Código em conformidade com tipagem estrita (`mypy --strict`) e linter ruff sem advertências.
- [x] Ausência de dead code, stubs ou menções operacionais a `tdd-code` como runtime ativo.
- [x] Zero assinaturas de personas ou rodapés institucionais persistidos nos arquivos de código ou configuração.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob).
- [x] Validação final do round executada pelo Agile Master (@david).
