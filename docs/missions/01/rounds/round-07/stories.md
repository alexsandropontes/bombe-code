---
version: "1.0.0"
round:
  number: 7
  goal: "Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI"
  status: "done"
  started_at: "2026-10-31T17:05:00"
  completed_at: "2026-10-31T17:13:00"
  capacity: 4
  used: 4
  remaining: 0

stories:
  story_007:
    id: "STORY-007"
    title: "Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI"
    order: 1
    status: "done"
    assigned_to: "@barbara"
    points: 4
    priority: 1
    dependencies: ["STORY-006"]
    blocks: ["STORY-008"]
    started_at: "2026-10-31T17:05:00"
    completed_at: "2026-10-31T17:13:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
    commit_sha: "40e5094"
---

# Estado das Stories — ROUND-7 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD | Commit |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-007` | Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI | Nível 3 | 4 | ✅ done | @barbara | ✅ Approved | ✅ Approved | `40e5094` |

## 2. Detalhamento & Rastreabilidade — STORY-007

- **Documento Canônico:** `docs/missions/01/stories/STORY-007.md`
- **Épico Pai:** `EP-03` (`docs/missions/01/epics/epic-03.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Backend Python & Async Systems)
- **Critérios de Aceite:**
  - **AC-01 (Invariante 1:1):** O motor de execução deve rejeitar qualquer tentativa de registrar mais de uma história no mesmo round com erro `InvalidRoundScopeError`.
  - **AC-02 (Comando round-start):** Deve criar os artefatos do round, atualizar o status da story para `in_progress` e interromper a execução deterministamente na fronteira do DoR.
  - **AC-03 (Comando round-full):** Deve executar a queima de todos os slices daquela story, acionar a subfase de validate do @unclebob e finalizar o round sem avançar para o próximo.
  - **AC-04 (Comando round-all):** Deve iterar sequencialmente por todos os rounds da missão ativa, parando apenas diante de falha de teste, erro técnico ou conclusão da missão.
  - **AC-05 (Bloqueio por Pendência de DoD):** Nenhuma execução de round novo pode iniciar se o round anterior contiver itens `- [ ]` não concluídos.

## 3. Gestão de Dependências
- **Bloqueado por:** `STORY-006` (Round 6 concluído e validado no commit `2ae3bf5`).
- **Desbloqueia:** `STORY-008` (Round 8 — Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local).
