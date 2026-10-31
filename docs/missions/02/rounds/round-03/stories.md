---
version: "1.0.0"
round:
  number: 3
  goal: "Engine de Rounds Autônomos (bombe round full [N] & bombe round all)"
  status: "validated"
  started_at: "2026-10-31T18:48:00"
  completed_at: "2026-10-31T19:00:00"
  capacity: 4.0
  used: 4.0
  remaining: 0.0

stories:
  story_011:
    id: "STORY-011"
    title: "Engine de Rounds Autônomos (Full & All)"
    order: 1
    status: "done"
    assigned_to: "@barbara"
    points: 3
    priority: 1
    dependencies: ["STORY-010"]
    blocks: ["STORY-012", "STORY-014"]
    started_at: "2026-10-31T18:48:00"
    completed_at: "2026-10-31T19:00:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
---

# Estado das Stories — ROUND-3 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-011` | Engine de Rounds Autônomos (Full & All) | Nível 3 (Sênior) | 3 | ✅ done | @barbara | ✅ Approved | ✅ Approved |

## 2. Detalhamento & Rastreabilidade — STORY-011

- **Documento Canônico:** `docs/missions/02/stories/STORY-011.md`
- **Épico Pai:** `EP-02` (`docs/missions/02/epics/epic-02.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python & CLI)
- **Critérios de Aceite:**
  - **AC-01:** `bombe round full [N]` executa sequencialmente Upstream -> Burn -> Review -> Validate para o round N e para ao final com relatório consolidado.
  - **AC-02:** `bombe round all` localiza todos os rounds pendentes da missão ativa e os executa ordenadamente do primeiro ao último.
  - **AC-03:** Durante a execução de `round all`, o sistema não solicita entrada no stdin e não emite prompts de confirmação de cortesia.
  - **AC-04:** Se qualquer round falhar no teste TDD ou no review de arquitetura, o comando `round all` aborta imediatamente com exit code 1, preservando o estado do repositório para diagnóstico.
  - **AC-05:** Ao concluir o último round em `round all`, exibe sumário de sucesso orientando o encerramento via `bombe mission end`.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-2 (`STORY-010` — Engine de Rounds Manuais concluído e validado).
- **Desbloqueia:** `STORY-012` (Round 4 — Wave Bridge) e `STORY-014` (Round 6 — Suíte E2E).
