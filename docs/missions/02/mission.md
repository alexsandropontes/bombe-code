---
id: MISSION-02
title: "Equalização de Comandos CLI e Transição Wave -> Slice/Round (Core v4 Parity)"
status: open
maturity_level: enterprise-grade
scope_type: legacy-parity
created_at: "2026-10-31T17:48:00"
rounds:
  ROUND-0:
    status: validated
    type: upstream_macro
    started_at: "2026-10-31T17:48:00"
    completed_at: "2026-10-31T18:07:00"
  ROUND-1:
    status: validated
    story_id: STORY-009
    epic_id: EP-01
    title: "Porteiro Atômico e Lifecycle de Missões"
    started_at: "2026-10-31T18:10:00"
    completed_at: "2026-10-31T18:25:00"
  ROUND-2:
    status: validated
    story_id: STORY-010
    epic_id: EP-02
    title: "Engine de Rounds Manuais com DoR Gate"
    started_at: "2026-10-31T18:30:00"
    completed_at: "2026-10-31T18:45:00"
  ROUND-3:
    status: pending
    story_id: STORY-011
    epic_id: EP-02
    title: "Engine de Rounds Autônomos (Full & All)"
  ROUND-4:
    status: pending
    story_id: STORY-012
    epic_id: EP-03
    title: "Wave Bridge e Interceptor de Depreciação"
  ROUND-5:
    status: pending
    story_id: STORY-013
    epic_id: EP-04
    title: "Equalização de Comandos Standalone e Governança"
  ROUND-6:
    status: pending
    story_id: STORY-014
    epic_id: EP-05
    title: "Suíte E2E da CLI e Homologação de Gates G1-G6"
---

# MISSION-02 — Equalização de Comandos CLI e Transição Wave -> Slice/Round (Core v4 Parity)

## 1. DEMAND (Verbatim)

*bc project mission. Cara nova missão... o bombe code ainda está usando provavelmente o fluxo antigo de comandos etc... vamos equalizar os comandos antigods com os novos do bombe core.. claro nomenclaturas mantem, mas a função tem que ser equivalente... o bobme code tinha o conceito de wave que morreu, agora temos o conceito de slice e rounds... precisamos ajustar essas coisas dos comandos do bombe code entendeu? Inclusive o conceito de missions do novo bombe core... enfim.. revisão completa dos comandos

---

## 2. Índice dos Documentos de Projeto & Missão

- **Inception Geral (`docs/projeto/`):**
  - [Escopo do Produto](file:///home/lexpontes/projetos/struct/bombe-code/docs/projeto/escopo.md) — Atualizado com paridade de comandos CLI v4 e aposentadoria do conceito de onda.
  - [Jornadas do Usuário](file:///home/lexpontes/projetos/struct/bombe-code/docs/projeto/jornada.md) — Mapeamento dos fluxos CLI canônicos (missão, rounds, queima de slices, fallback wave).
  - [Definição de MVP](file:///home/lexpontes/projetos/struct/bombe-code/docs/projeto/mvp.md) — Quality gates de CLI e transição sem quebra de compatibilidade.
  - [Sequenciador Geral](file:///home/lexpontes/projetos/struct/bombe-code/docs/projeto/sequenciador.md) — Planejamento kanban 1 Round = 1 Story da MISSION-02.
- **Missão 02 (`docs/missions/02/`):**
  - [PRD da Missão](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/prd/prd.md) — Requisitos funcionais, comandos CLI equalizados e bridge de retrocompatibilidade.
  - [Arquitetura Técnica](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/architecture/architecture.md) — Design do Command Dispatcher, mapeamento Wave -> Round/Slice e ADRs.
  - **Épicos:**
    - [EP-01 — Gestão de Ciclo de Vida de Missões](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/epics/epic-01.md)
    - [EP-02 — Tríade de Execução de Rounds e Slices](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/epics/epic-02.md)
    - [EP-03 — Ponte de Retrocompatibilidade Wave Bridge](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/epics/epic-03.md)
    - [EP-04 — Governança de Projeto & Comandos Standalone](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/epics/epic-04.md)
    - [EP-05 — Validação Integrada E2E e Quality Gates](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/epics/epic-05.md)
  - **Stories Base:**
    - [STORY-009 (Round 1)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/stories/STORY-009.md) · [STORY-010 (Round 2)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/stories/STORY-010.md) · [STORY-011 (Round 3)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/stories/STORY-011.md) · [STORY-012 (Round 4)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/stories/STORY-012.md) · [STORY-013 (Round 5)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/stories/STORY-013.md) · [STORY-014 (Round 6)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/02/stories/STORY-014.md)

---

## 3. Quadro Kanban da Missão

| Round | Story | Épico | Título | Complexidade | Status |
| :---: | :---: | :---: | :--- | :---: | :---: |
| **R-0** | — | — | Upstream Macro (Inception, PRD, Arquitetura, Sequenciador, Stories BASE) | — | **VALIDATED** ✅ |
| **R-1** | `STORY-009` | `EP-01` | Porteiro Atômico e Lifecycle de Missões | Pleno (3h) | **VALIDATED** ✅ |
| **R-2** | `STORY-010` | `EP-02` | Engine de Rounds Manuais com DoR Gate | Sênior (4h) | **VALIDATED** ✅ |
| **R-3** | `STORY-011` | `EP-02` | Engine de Rounds Autônomos (Full & All) | Sênior (4h) | 📋 READY |
| **R-4** | `STORY-012` | `EP-03` | Wave Bridge e Interceptor de Depreciação | Pleno (3h) | 📋 READY |
| **R-5** | `STORY-013` | `EP-04` | Equalização de Comandos Standalone e Governança | Pleno (3h) | 📋 READY |
| **R-6** | `STORY-014` | `EP-05` | Suíte E2E da CLI e Homologação de Gates G1-G6 | Pleno (3h) | 📋 READY |
