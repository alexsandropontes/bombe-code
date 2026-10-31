---
version: "1.0.0"
round:
  number: 1
  goal: "Porteiro Atômico e Lifecycle de Missões (bombe mission new/status/end)"
  status: "validated"
  started_at: "2026-10-31T18:10:00"
  completed_at: "2026-10-31T18:25:00"
  capacity: 3.0
  used: 2.0
  remaining: 1.0

stories:
  story_009:
    id: "STORY-009"
    title: "Porteiro Atômico e Lifecycle de Missões"
    order: 1
    status: "done"
    assigned_to: "@barbara"
    points: 2
    priority: 1
    dependencies: []
    blocks: ["STORY-010", "STORY-011"]
    started_at: "2026-10-31T18:10:00"
    completed_at: "2026-10-31T18:22:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
---

# Estado das Stories — ROUND-1 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-009` | Porteiro Atômico e Lifecycle de Missões | Nível 2 (Pleno) | 2 | ✅ done | @barbara | ✅ Approved | ✅ Done |

## 2. Detalhamento & Rastreabilidade — STORY-009

- **Documento Canônico:** `docs/missions/02/stories/STORY-009.md`
- **Épico Pai:** `EP-01` (`docs/missions/02/epics/epic-01.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python & CLI)
- **Critérios de Aceite:**
  - **AC-01:** `bombe mission new` bloqueia concorrência de missões ativas (exit code 1).
  - **AC-02:** Scaffolding determinístico de diretórios e arquivo `mission.md` no disco.
  - **AC-03:** Visualização tabular do status de missão ativa via Rich.
  - **AC-04:** Validação de DoD no encerramento (`bombe mission end`).

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-0 (Upstream Macro concluído e validado).
- **Desbloqueia:** `STORY-010` (Round 2 — Rounds Manuais) e `STORY-011` (Round 3 — Rounds Autônomos).
