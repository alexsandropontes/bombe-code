---
version: "1.0.0"
round:
  number: 4
  goal: "Wave Bridge e Interceptor de Depreciação (bombe wave -> bombe round/mission/project)"
  status: "validated"
  started_at: "2026-10-31T19:05:00"
  completed_at: "2026-10-31T19:20:00"
  capacity: 3.0
  used: 3.0
  remaining: 0.0

stories:
  story_012:
    id: "STORY-012"
    title: "Wave Bridge e Interceptor de Depreciação"
    order: 1
    status: "done"
    assigned_to: "@barbara"
    points: 2
    priority: 1
    dependencies: ["STORY-011"]
    blocks: ["STORY-013", "STORY-014"]
    started_at: "2026-10-31T19:05:00"
    completed_at: "2026-10-31T19:20:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
---

# Estado das Stories — ROUND-4 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-012` | Wave Bridge e Interceptor de Depreciação | Nível 2 (Pleno) | 2 | ✅ done | @barbara | ✅ Approved | ✅ Approved |

## 2. Detalhamento & Rastreabilidade — STORY-012

- **Documento Canônico:** `docs/missions/02/stories/STORY-012.md`
- **Épico Pai:** `EP-03` (`docs/missions/02/epics/epic-03.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python & CLI)
- **Critérios de Aceite:**
  - **AC-01 (Banner Educativo de Depreciação):** Toda invocação de `bombe wave <cmd>` renderiza um painel Rich informando que "ondas" foram substituídas por "rounds e slices" no Core v4.
  - **AC-02 (Redirecionamento 1:1 de `wave start`):** `bombe wave start [ID]` mapeia o ID para número de round e despacha para `bombe round start [N]`.
  - **AC-03 (Redirecionamento 1:1 de `wave run`):** `bombe wave run` despacha para `bombe round all`.
  - **AC-04 (Redirecionamento 1:1 de `wave cycle`):** `bombe wave cycle [ID]` despacha para `bombe round burn [N]`.
  - **AC-05 (Redirecionamento de `validate`, `status`, `promote`, `end`):** Mapeamento estrito para `round validate`, `round status`, `project ship` e `mission end`.
  - **AC-06 (Preservação de Exit Code):** O código de saída POSIX retornado pela bridge é idêntico ao comando canônico despachado.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-3 (`STORY-011` — Engine de Rounds Autônomos concluído e validado).
- **Desbloqueia:** `STORY-013` (Round 5 — Comandos Standalone) e `STORY-014` (Round 6 — Suíte E2E).
