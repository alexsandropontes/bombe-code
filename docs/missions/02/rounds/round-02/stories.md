---
version: "1.0.0"
round:
  number: 2
  goal: "Engine de Rounds Manuais com DoR Gate (bombe round start/burn/review/validate/status)"
  status: "validated"
  started_at: "2026-10-31T18:30:00"
  completed_at: "2026-10-31T18:45:00"
  capacity: 4.0
  used: 3.0
  remaining: 1.0

stories:
  story_010:
    id: "STORY-010"
    title: "Engine de Rounds Manuais com DoR Gate"
    order: 1
    status: "done"
    assigned_to: "@barbara"
    points: 3
    priority: 1
    dependencies: ["STORY-009"]
    blocks: ["STORY-011", "STORY-012"]
    started_at: "2026-10-31T18:30:00"
    completed_at: "2026-10-31T18:45:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
---

# Estado das Stories — ROUND-2 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-010` | Engine de Rounds Manuais com DoR Gate | Nível 3 (Sênior) | 3 | ✅ done | @barbara | ✅ Approved | ✅ Approved |

## 2. Detalhamento & Rastreabilidade — STORY-010

- **Documento Canônico:** `docs/missions/02/stories/STORY-010.md`
- **Épico Pai:** `EP-02` (`docs/missions/02/epics/epic-02.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python & CLI)
- **Critérios de Aceite:**
  - **AC-01:** `bombe round start [N]` valida DoD anterior, prepara scaffold, fatia story e para deterministicamente na DoR (`dor_ready`).
  - **AC-02:** `bombe round burn [N]` bloqueia execução caso round não tenha atingido `dor_ready`.
  - **AC-03:** `bombe round burn [N]` queima atomicamente os slices da história via ciclo TDD.
  - **AC-04:** `bombe round review [N]` e `bombe round validate [N]` operam como quality gates formais.
  - **AC-05:** `bombe round status` renderiza inspeção visual completa do estado do round.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-1 (`STORY-009` — Lifecycle de Missões concluído e validado).
- **Desbloqueia:** `STORY-011` (Round 3 — Rounds Autônomos) e `STORY-012` (Round 4 — Wave Bridge).
