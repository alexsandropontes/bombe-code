---
version: "1.0.0"
round:
  number: 5
  goal: "Equalização de Comandos Standalone e Governança (project configure/ship, mode, task, rca, review, simplify, status-report)"
  status: "validated"
  started_at: "2026-10-31T19:25:00"
  completed_at: "2026-10-31T19:40:00"
  capacity: 3.0
  used: 3.0
  remaining: 0.0

stories:
  story_013:
    id: "STORY-013"
    title: "Equalização de Comandos Standalone e Governança"
    order: 1
    status: "validated"
    assigned_to: "@barbara"
    points: 2
    priority: 1
    dependencies: ["STORY-012"]
    blocks: ["STORY-014"]
    started_at: "2026-10-31T19:25:00"
    completed_at: "2026-10-31T19:40:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
---

# Estado das Stories — ROUND-5 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-013` | Equalização de Comandos Standalone e Governança | Nível 2 (Pleno) | 2 | ✅ validated | @barbara | ✅ Approved | ✅ Validated |

## 2. Detalhamento & Rastreabilidade — STORY-013

- **Documento Canônico:** `docs/missions/02/stories/STORY-013.md`
- **Épico Pai:** `EP-04` (`docs/missions/02/epics/epic-04.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Engenharia Backend Python & CLI)
- **Critérios de Aceite:**
  - **AC-01 (Setup de Projeto):** `bombe project configure` valida e atualiza o `.bombeconfig` sem corromper chaves existentes.
  - **AC-02 (Promoção Protegida Git Ship):** `bombe project ship [env]` executa a suíte de testes antes do merge; se os testes falharem, a promoção é abortada com exit code 1.
  - **AC-03 (Comutação Auditada de Modo):** `bombe mode [modo]` comuta entre `slice-code` e `vibe-code` gravando `mode_origin` e `mode_migrated_at`.
  - **AC-04 (Despacho de Tasks Avulsas):** `bombe task '<desc>'` despacha para o subagente correto via Protocolo Garçom.
  - **AC-05 (Comandos de Qualidade Operacionais):** `bombe rca`, `bombe review`, `bombe simplify` e `bombe status-report` executam de forma standalone sem exigir missão ativa.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-4 (`STORY-012` — Wave Bridge e Interceptor de Depreciação concluído e validado).
- **Desbloqueia:** `STORY-014` (Round 6 — Suíte E2E da CLI e Homologação de Gates G1-G6).
