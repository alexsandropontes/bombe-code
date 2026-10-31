---
version: "1.0.0"
round:
  number: 1
  goal: "Migração de Configuração e Runtime Slice-Code com rastreabilidade histórica"
  status: "active"
  started_at: "2026-10-31T15:49:00"
  completed_at: null
  capacity: 2
  used: 0
  remaining: 2

stories:
  story_001:
    id: "STORY-001"
    title: "Migração de Configuração e Runtime Slice-Code"
    order: 1
    status: "in_progress"
    assigned_to: "@fowler"
    points: 2
    priority: 1
    dependencies: []
    blocks: ["STORY-002"]
    started_at: "2026-10-31T15:49:00"
    completed_at: null
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: null
      architecture: null
    committed: false
---

# Estado das Stories — ROUND-1 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-001` | Migração de Configuração e Runtime Slice-Code | Nível 1 | 2 | ⏳ in_progress | @fowler | ✅ Approved | ⏳ Pending |

## 2. Detalhamento & Rastreabilidade — STORY-001

- **Documento Canônico:** `docs/missions/01/stories/STORY-001.md`
- **Épico Pai:** `EP-01` (`docs/missions/01/epics/epic-01.md`)
- **Layer:** `backend`
- **Especialista Designado:** @fowler (Engenharia de Testes e Refactoring Python)
- **Critérios de Aceite:**
  - **AC-01:** Carregamento de `.bombeconfig` com `mode: slice-code` passa sem erros no Pydantic.
  - **AC-02:** Rastreabilidade formal com chaves `mode: "slice-code"` e `mode_origin: "tdd-code"`.
  - **AC-03:** Rejeição de modos legados extintos levantando `InvalidModeError`.
  - **AC-04:** Suíte de testes `tests/unit/test_config.py` com 100% de sucesso.

## 3. Gestão de Dependências
- **Bloqueado por:** Nenhuma (Round 0 macro validado).
- **Desbloqueia:** `STORY-002` (Round 2 — Atualização dos Dossiês dos Agentes).
