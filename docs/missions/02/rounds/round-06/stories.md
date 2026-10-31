---
version: "1.0.0"
round:
  number: 6
  goal: "Suíte E2E da CLI e Homologação de Gates G1-G6 (19 Entry Points, Tríade de Rounds, Wave Bridge, Standalone, Zero Mocks e Gates G1-G6)"
  status: "validated"
  started_at: "2026-10-31T19:45:00"
  completed_at: "2026-10-31T20:05:00Z"
  capacity: 3.0
  used: 3.0
  remaining: 0.0

stories:
  story_014:
    id: "STORY-014"
    title: "Suíte E2E da CLI e Homologação de Gates G1-G6"
    order: 1
    status: "validated"
    assigned_to: "@barbara"
    points: 2
    priority: 1
    dependencies: ["STORY-013"]
    blocks: []
    started_at: "2026-10-31T19:45:00"
    completed_at: "2026-10-31T20:05:00Z"
    dor:
      process: "approved"
      dev: "approved"
    review:
      code_review: "approved"
      architecture: "approved"
    committed: true
---

# Estado das Stories — ROUND-6 (Cadência 1 Round = 1 Story)

## 1. Quadro de Execução do Round

| Ordem | Story ID | Título | Complexidade | Pts | Status | Responsável | DoR | DoD |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `STORY-014` | Suíte E2E da CLI e Homologação de Gates G1-G6 | Nível 2 (Pleno) | 2 | ✅ validated | @barbara | ✅ Approved | ✅ Validated |

## 2. Detalhamento & Rastreabilidade — STORY-014

- **Documento Canônico:** `docs/missions/02/stories/STORY-014.md`
- **Épico Pai:** `EP-05` (`docs/missions/02/epics/epic-05.md`)
- **Layer:** `backend`
- **Especialista Designado:** @barbara (Backend & Test Engineering)
- **Critérios de Aceite:**
  - **AC-01 (Cobertura Integral dos 19 Entry Points):** Todos os 19 entry points (EP-01 a EP-19) possuem casos de teste automatizados em `tests/e2e/test_cli_parity.py`.
  - **AC-02 (Fluxo de Missão e Rounds E2E):** O ciclo `mission new` -> `round start` -> `round burn` -> `round review` -> `round validate` -> `round full` -> `round all` -> `mission end` executa com sucesso em diretório temporário.
  - **AC-03 (Validação da Wave Bridge):** Os 7 subcomandos legados `bombe wave ...` são validados comprovando que emitem o banner pedagógico e despacham com paridade.
  - **AC-04 (Auditoria Zero Mocks / Zero Stubs):** Teste de auditoria varre recursivamente `src/bombe_code/` e falha se encontrar `NotImplementedError`, corpos vazios `pass` não decorados ou tags de stubs.
  - **AC-05 (Homologação Gates G1 a G6):** Suíte comprova que os gates G1 a G6 estabelecidos na governança estão 100% satisfeitos.

## 3. Gestão de Dependências
- **Bloqueado por:** ROUND-5 (`STORY-013` — Equalização de Comandos Standalone e Governança concluído e validado).
- **Desbloqueia:** Encerramento formal da MISSION-02 (`bombe mission end`).
