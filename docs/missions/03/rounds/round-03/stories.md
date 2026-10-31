---
version: "1.0.0"
round:
  number: 3
  goal: "Suporte e Parametrização de MTP (Multi-Token Prediction)"
  status: "in_progress"
  started_at: "2026-10-31T21:38:00"
  capacity: 3.0
  used: 0.0
  remaining: 3.0

stories:
  story_017:
    id: "STORY-017"
    title: "Suporte e Parametrização de MTP (Multi-Token Prediction)"
    order: 1
    status: "in_progress"
    assigned_to: "@barbara"
    points: 3
    priority: 1
    dependencies: ["STORY-016"]
    blocks: ["STORY-018"]
    started_at: "2026-10-31T21:38:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "pending"
      architecture: "pending"
    committed: false
---

# Estado das Stories — ROUND-3 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-017` | Suporte e Parametrização de MTP (Multi-Token Prediction) | Nível 2 (Pleno) | 3 | 🔄 in_progress | @barbara | ✅ Approved | ⏳ in_progress |

## 2. Detalhamento & Rastreabilidade — STORY-017

- **Documento Canônico:** `docs/missions/03/stories/STORY-017.md`
- **Épico Pai:** `EP-08` (`docs/missions/03/epics/epic-08.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python)
- **Critérios de Aceite:**
  - **AC-1:** Se o modelo for Gemma 4 E4B com MTP ativo, a linha de comando deve conter:
    `--model-draft <path>/mtp-gemma-4-E4B-it-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 3 -fa off`.
  - **AC-2:** Se o modelo for Gemma 4 26B com MTP ativo, a linha de comando deve conter:
    `--model-draft <path>/mtp-gemma-4-26B-A4B-it-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 3 -fa on --n-cpu-moe 999`.
  - **AC-3:** Se o modelo for Qwen 3.8-9B com MTP ativo, a linha de comando deve conter:
    `--spec-type draft-mtp --spec-draft-n-max 2 -fa on` (sem flag `--model-draft`).
  - **AC-4:** O sistema deve verificar a existência física do arquivo `.gguf` de draft antes de tentar iniciar o servidor, levantando `DraftModelNotFoundError` se ausente.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-2 (STORY-016 concluída e validada).
- **Desbloqueia:** `STORY-018` (Round 4 — HybridRouter & Benchmark E2E).
