---
version: "1.0.0"
round:
  number: 4
  goal: "Integração com HybridRouter e Execução E2E do Rate Limiter"
  status: "in_progress"
  started_at: "2026-10-31T21:52:00"
  capacity: 3.5
  used: 0.0
  remaining: 3.5

stories:
  story_018:
    id: "STORY-018"
    title: "Integração com HybridRouter e Execução E2E do Rate Limiter"
    order: 1
    status: "in_progress"
    assigned_to: "@barbara"
    points: 3
    priority: 1
    dependencies: ["STORY-017"]
    blocks: []
    started_at: "2026-10-31T21:52:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "pending"
      architecture: "pending"
    committed: false
---

# Estado das Stories — ROUND-4 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-018` | Integração com HybridRouter e Execução E2E do Rate Limiter | Nível 2 (Pleno) | 3 | 🟡 in_progress | @barbara | ✅ Approved | 🟡 in_progress |

## 2. Detalhamento & Rastreabilidade — STORY-018

- **Documento Canônico:** `docs/missions/03/stories/STORY-018.md`
- **Épico Pai:** `EP-09` (`docs/missions/03/epics/epic-09.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python)
- **Critérios de Aceite:**
  - **AC-1:** O `HybridRouter` deve requisitar ao `LocalModelManager` a inicialização do modelo correto caso o servidor local não esteja respondendo.
  - **AC-2:** A implementação do `TokenBucketRateLimiter` deve suportar taxa de recarga (`refill_rate`), capacidade máxima (`capacity`) e método `consume(tokens: int) -> bool` thread-safe.
  - **AC-3:** Suíte completa de testes unitários do Rate Limiter executada via `pytest` com 100% de aprovação.
  - **AC-4:** Evidência de geração de código via modelo local acelerado com MTP registrada no log de execução.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-3 (STORY-017 concluída e validada).
- **Desbloqueia:** Encerramento da MISSION-03.
