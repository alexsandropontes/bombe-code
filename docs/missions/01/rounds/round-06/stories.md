---
version: "1.0.0"
round:
  number: 6
  goal: "FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON"
  status: "done"
  started_at: "2026-10-31T16:55:00"
  completed_at: "2026-10-31T17:01:00"
  capacity: 4
  used: 3
  remaining: 1

stories:
  story_006:
    id: "STORY-006"
    title: "FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON"
    order: 1
    status: "done"
    assigned_to: "@barbara"
    points: 3
    priority: 1
    dependencies: ["STORY-005"]
    blocks: ["STORY-007"]
    started_at: "2026-10-31T16:55:00"
    completed_at: "2026-10-31T17:01:00"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
    commit_sha: "2ae3bf5"
---

# Estado das Stories — ROUND-6 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD | Commit |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-006` | FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON | Nível 2 | 3 | ✅ done | @barbara | ✅ Approved | ✅ Approved | `2ae3bf5` |

## 2. Detalhamento & Rastreabilidade — STORY-006

- **Documento Canônico:** `docs/missions/01/stories/STORY-006.md`
- **Épico Pai:** `EP-02` (`docs/missions/01/epics/epic-02.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Backend Python & Async Systems)
- **Critérios de Aceite:**
  - **AC-01 (Extração de Blocos Markdown):** Respostas contendo blocos ````json {"tool": "read_file", "arguments": {"path": "..."}} ```` são extraídas como chamadas de tool estruturadas.
  - **AC-02 (Extração em Texto Puro):** Payloads JSON sem delimitadores de bloco markdown, mas contendo os pares válidos de chamada (`"tool"` / `"name"` e `"arguments"`), são recuperados com sucesso.
  - **AC-03 (Tolerância a Erros de Sintaxe):** Blocos com JSON inválido ou corrompido são ignorados sem propagar exceção de crash para a esteira.
  - **AC-04 (Preservação de Integridade de Argumentos):** Argumentos com estruturas complexas (objetos aninhados, arrays, caracteres de escape) são desserializados com integridade absoluta.

## 3. Gestão de Dependências
- **Bloqueado por:** `STORY-005` (Round 5 concluído e validado no commit `6da8fee`).
- **Desbloqueia:** `STORY-007` (Round 7 — Motor de Execução Kanban e Tríade CLI).
