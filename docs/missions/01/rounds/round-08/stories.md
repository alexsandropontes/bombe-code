---
version: "1.0.0"
round:
  number: 8
  goal: "Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local"
  status: "done"
  started_at: "2026-10-31T17:15:00"
  completed_at: "2026-10-31T17:35:00"
  capacity: 4
  used: 4
  remaining: 0

stories:
  story_008:
    id: "STORY-008"
    title: "Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local"
    order: 1
    status: "done"
    assigned_to: "@fowler"
    points: 4
    priority: 1
    dependencies: ["STORY-007"]
    blocks: []
    started_at: "2026-10-31T17:15:00"
    completed_at: "2026-10-31T17:35:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
    commit_hash: "5135e6f"
---

# Estado das Stories — ROUND-8 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD | Commit |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-008` | Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local | Nível 2 | 4 | ✅ done | @fowler | ✅ Process / ✅ Dev | ✅ 100% | `5135e6f` |

## 2. Detalhamento & Rastreabilidade — STORY-008

- **Documento Canônico:** `docs/missions/01/stories/STORY-008.md`
- **Épico Pai:** `EP-04` (`docs/missions/01/epics/epic-04.md`)
- **Layer:** `backend`
- **Especialista Designado:** @fowler (Test Engineering & Refactoring)
- **Critérios de Aceite:**
  - **AC-01 (Simulação/Captura 429):** A chamada rejeitada com HTTP 429 pelo provedor cloud deve ser interceptada sem crash da aplicação.
  - **AC-02 (Transição de Roteamento em Tempo Real):** O log de execução deve evidenciar a transição `Cloud (Z.ai) -> Local vLLM (18096)` em tempo < 2.0s.
  - **AC-03 (Execução Local Green):** O slice sob teste deve ser implementado, os testes associados executados e o resultado final validado como 100% verde (passed).
  - **AC-04 (Persistência de Estado):** O arquivo `quota_state.json` deve registrar o provedor cloud em estado `exhausted` e `locked_until` ativo.

## 3. Gestão de Dependências
- **Bloqueado por:** `STORY-007` (Round 7 concluído e validado no commit `40e5094`).
- **Desbloqueia:** Homologação final e encerramento da `MISSION-01`.
