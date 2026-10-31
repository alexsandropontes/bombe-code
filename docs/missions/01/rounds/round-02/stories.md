---
version: "1.0.0"
round:
  number: 2
  goal: "Atualização dos Dossiês dos Agentes para PDW 4.0 com preservação absoluta dos nomes e validador determinístico"
  status: "completed"
  started_at: "2026-10-31T16:00:00"
  completed_at: "2026-10-31T16:17:00"
  capacity: 3
  used: 3
  remaining: 0

stories:
  story_002:
    id: "STORY-002"
    title: "Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes"
    order: 1
    status: "done"
    assigned_to: "@andrej"
    points: 3
    priority: 1
    dependencies: ["STORY-001"]
    blocks: ["STORY-003"]
    started_at: "2026-10-31T16:00:00"
    completed_at: "2026-10-31T16:17:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
---

# Estado das Stories — ROUND-2 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-002` | Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes | Nível 1 | 3 | ✅ done | @andrej | ✅ Approved | ✅ Approved |

## 2. Detalhamento & Rastreabilidade — STORY-002

- **Documento Canônico:** `docs/missions/01/stories/STORY-002.md`
- **Épico Pai:** `EP-01` (`docs/missions/01/epics/epic-01.md`)
- **Layer:** `backend`
- **Especialista Designado:** @andrej (Prompt Architect & PDW 4.0) em conjunto com @fowler (Test Engineering)
- **Commit:** `f4af816`
- **Critérios de Aceite:**
  - **AC-01 (Conformidade PDW 4.0):** 100% dos dossiês em `src/bombe_code/agents/definitions/*.md` devem conter as 6 seções obrigatórias e o frontmatter estruturado.
  - **AC-02 (Preservação de Nomes):** Nenhum arquivo de agente histórico deve ser renomeado ou excluído; os handles permanecem idênticos aos originais.
  - **AC-03 (Validador Automatizado):** O script de verificação `AgentDossierValidator` deve auditar todos os arquivos `.md` e aprovar sem divergências de campos obrigatórios.
  - **AC-04 (Restrições de Soberania):** Todos os agentes de teste e arquitetura devem conter explicitamente o veto de implementação de código de produção fora de sua stack.

## 3. Gestão de Dependências
- **Bloqueado por:** `STORY-001` (Round 1 concluído e validado no commit `a4e50cb`).
- **Desbloqueia:** `STORY-003` (Round 3 — Contrato LLMProviderProtocol e Adapter Local vLLM).
