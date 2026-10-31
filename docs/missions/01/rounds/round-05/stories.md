---
version: "1.0.0"
round:
  number: 5
  goal: "QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local"
  status: "done"
  started_at: "2026-10-31T16:45:00"
  completed_at: "2026-10-31T16:51:00"
  capacity: 4
  used: 4
  remaining: 0

stories:
  story_005:
    id: "STORY-005"
    title: "QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local"
    order: 1
    status: "done"
    assigned_to: "@barbara"
    points: 4
    priority: 1
    dependencies: ["STORY-004"]
    blocks: ["STORY-006"]
    started_at: "2026-10-31T16:45:00"
    completed_at: "2026-10-31T16:51:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
    commit_sha: "6da8fee"
---

# Estado das Stories — ROUND-5 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD | Commit |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-005` | QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local | Nível 3 | 4 | ✅ done | @barbara | ✅ Approved | ✅ Approved | `6da8fee` |

## 2. Detalhamento & Rastreabilidade — STORY-005

- **Documento Canônico:** `docs/missions/01/stories/STORY-005.md`
- **Épico Pai:** `EP-02` (`docs/missions/01/epics/epic-02.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Backend Python & Async Systems)
- **Critérios de Aceite:**
  - **AC-01 (Detecção de Erro 429):** Ao receber HTTP 429 de qualquer provedor cloud, o `QuotaManager` marca o provedor como `exhausted` e calcula a janela de bloqueio em `locked_until`.
  - **AC-02 (Persistência Atômica de Estado):** O estado de contingência é persistido em `quota_state.json` com integridade estrutural.
  - **AC-03 (Chaveamento em Menos de 2s):** O tempo total entre a rejeição da cloud e o disparo da inferência local de contingência é inferior a 2000ms.
  - **AC-04 (Silenciamento de Exceção ao Usuário):** A falha de cota não aborta o comando CLI nem exibe stack trace ao operador.

## 3. Gestão de Dependências
- **Bloqueado por:** `STORY-004` (Round 4 concluído e validado no commit `b573f7a`).
- **Desbloqueia:** `STORY-006` (Round 6 — FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON).
