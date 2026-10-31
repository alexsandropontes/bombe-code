---
version: "1.0.0"
round:
  number: 2
  goal: "Implementação dos Perfis de Hardware e Tetos de Contexto"
  status: "in_progress"
  started_at: "2026-10-31T21:20:00"
  capacity: 2.5
  used: 2.5
  remaining: 0.0

stories:
  story_016:
    id: "STORY-016"
    title: "Implementação dos Perfis de Hardware e Tetos de Contexto"
    order: 1
    status: "in_progress"
    assigned_to: "@barbara"
    points: 2
    priority: 1
    dependencies: ["STORY-015"]
    blocks: ["STORY-017"]
    started_at: "2026-10-31T21:20:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "pending"
      architecture: "pending"
    committed: false
---

# Estado das Stories — ROUND-2 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-016` | Implementação dos Perfis de Hardware e Tetos de Contexto | Nível 2 (Pleno) | 2 | 🟡 in_progress | @barbara | ✅ Approved | 🟡 in_progress |

## 2. Detalhamento & Rastreabilidade — STORY-016

- **Documento Canônico:** `docs/missions/03/stories/STORY-016.md`
- **Épico Pai:** `EP-07` (`docs/missions/03/epics/epic-07.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python)
- **Critérios de Aceite:**
  - **AC-1:** Para Gemma 4 E4B e LFM3, o comando gerado deve incluir `-c 131072` (128K).
  - **AC-2:** Para Gemma 4 26B-A4B e Qwen 3.8-9B, o comando gerado deve incluir `-c 65536` (64K).
  - **AC-3:** Para todos os perfis, as flags de quantização do cache KV `-ctk q8_0 -ctv q8_0` devem ser injetadas.
  - **AC-4:** Para Gemma 4 26B-A4B, a flag `--n-cpu-moe 999` e `-fa on` devem ser incluídas.
  - **AC-5:** Para Gemma 4 E4B, a flag `-fa off` deve ser configurada obrigatoriamente.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-1 (STORY-015 concluída e validada).
- **Desbloqueia:** `STORY-017` (Round 3 — Suporte e Integração a MTP).
