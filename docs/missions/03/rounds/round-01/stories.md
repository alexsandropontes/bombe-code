---
version: "1.0.0"
round:
  number: 1
  goal: "Implementação do LocalModelManager e VRAMGate"
  status: "in_progress"
  started_at: "2026-10-31T21:10:00"
  capacity: 3.0
  used: 0.0
  remaining: 3.0

stories:
  story_015:
    id: "STORY-015"
    title: "Implementação do LocalModelManager e VRAMGate"
    order: 1
    status: "in_progress"
    assigned_to: "@barbara"
    points: 3
    priority: 1
    dependencies: []
    blocks: ["STORY-016"]
    started_at: "2026-10-31T21:10:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "pending"
      architecture: "pending"
    committed: false
---

# Estado das Stories — ROUND-1 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-015` | Implementação do LocalModelManager e VRAMGate | Nível 2 (Pleno) | 3 | ⏳ in_progress | @barbara | ✅ Approved | ⏳ in_progress |

## 2. Detalhamento & Rastreabilidade — STORY-015

- **Documento Canônico:** `docs/missions/03/stories/STORY-015.md`
- **Épico Pai:** `EP-06` (`docs/missions/03/epics/epic-06.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python)
- **Critérios de Aceite:**
  - **AC-1:** O `LocalModelManager` deve manter no máximo uma instância ativa de `llama-server`.
  - **AC-2:** Antes de executar qualquer subprocesso, a classe `VRAMGate` deve invocar `nvidia-smi` e certificar que a VRAM ocupada está abaixo de 300MiB.
  - **AC-3:** O encerramento de um modelo ativo deve emitir `SIGTERM`, aguardar até 15 segundos e, se o processo persistir, emitir `SIGKILL`.
  - **AC-4:** O método `start_model(profile)` deve realizar polling no endpoint `http://{host}:{port}/health` e só retornar sucesso quando receber HTTP 200 dentro do timeout de 120s.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-0 (Inception Macro validado).
- **Desbloqueia:** `STORY-016` (Round 2 — Hardware Tuning & Tetos de Contexto).
