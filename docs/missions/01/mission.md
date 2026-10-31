---
id: MISSION-01
title: "Modernização do Bombe Code — Equalização Core v4, Orquestração Híbrida de LLMs & Pipeline 1 Round = 1 Story"
status: open
maturity_level: enterprise-grade
scope_type: legacy-parity
created_at: "2026-10-31T12:28:00"
rounds:
  ROUND-0:
    status: validated
    type: upstream_macro
    completed_at: "2026-10-31T12:43:00"
  ROUND-1:
    status: validated
    story_id: STORY-001
    epic_id: EP-01
    title: "Migração de Configuração e Runtime Slice-Code"
    completed_at: "2026-10-31T15:58:00"
    commit: "a4e50cb"
  ROUND-2:
    status: validated
    story_id: STORY-002
    epic_id: EP-01
    title: "Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes"
    completed_at: "2026-10-31T16:17:00"
    commit: "f4af816"
  ROUND-3:
    status: validated
    story_id: STORY-003
    epic_id: EP-02
    title: "Contrato LLMProviderProtocol e Adapter Local vLLM (Porta 18096, Fila Indiana)"
    completed_at: "2026-10-31T16:31:00"
    commit: "c504b83"
  ROUND-4:
    status: validated
    story_id: STORY-004
    epic_id: EP-02
    title: "Classificador de Complexidade de Slice e Roteador Híbrido Dinâmico"
    completed_at: "2026-10-31T16:41:00"
    commit: "b573f7a"
  ROUND-5:
    status: validated
    story_id: STORY-005
    epic_id: EP-02
    title: "QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local"
    completed_at: "2026-10-31T16:51:00"
    commit: "6da8fee"
  ROUND-6:
    status: pending
    story_id: STORY-006
    epic_id: EP-02
    title: "FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON"
  ROUND-7:
    status: pending
    story_id: STORY-007
    epic_id: EP-03
    title: "Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI"
  ROUND-8:
    status: pending
    story_id: STORY-008
    epic_id: EP-04
    title: "Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local"
---

# MISSION-01 — Modernização do Bombe Code

## 1. DEMAND (Verbatim)

*bc project mission... cara o Bombe code começou sendo desenvolvido no modelo tdd code que morreu aqui no bombe core, então tem que atualizar o bombe config etc para o novo bombe core que tem um modelo novo, documentação e tdo que já existe mantém no legado.. daqui pra frente as novas documentações e projeto será feito no Slice code... agora o Bombe code, não confunda. é o projeto que vamos mexer agora... o Bombe Core é o runtime ATUAL e que usamos aqui no harness do opencode pra vc codar e ajustar os outros projetos... nomes de agentes, fluxos, são meio diferentes. o bombe core foi atualizado depois que dei uma pausa no bombe code. e a ideia é equalizar os modelos de trabalho, workflow, linguagem, agentes (no sentido de comportamento e a nova versão do pdw 4.0, mas não nos "nomes" atuais do bombe code..  o nome é a única coisa que o bombe code mantém, todo o resto vc pode mexer ahahaha... mas enfim... vamos para as tarefas: 1 - Equalizar bombe code para ter o comportamento da versão atual do Bombe core... 2 - Refatorar toda a parte de gestão das llm's de forma que eu tenha as LLM's locais selecionadas na POC, para os devidos papéis, mas dando uma análise inteligente de quando usa a LLM local, quando usa uma llm cloud e a inteligência de migrar pra local quando estoura a conta das clouds... e mais uma coisa que vai ser legal.. agora no começo a conta da z.ai que acho que já está configurada lá no bombe code já está estourada, ou seja, na hora do teste já vai ser um teste de roteamento pq a conta está estourada hahahaha... Mas ai vem o seguinte. alguém precisa orquestrar isso.. decidir quando usa local, quando usa cloud pela complexidade da tarefa. talvez cada tarefa ser criada com uma nota de complexidade e o escalonamento ocorre de acordo com a complexidade... enfim.. não sei... talvez seria uma opção... podemos pensar nesse conceito... e indo numa alteração de fluxo que é diferente do bombe core um pouco mas simplifica mais... no Bombe core temos as FASES Upstream e Downstream... e os Rounds... que o 0 só tem upstream pq é a inception e os demais tem upsrtream e downstream.. nada disso muda... só queria facilitar ainda mais o trabalho e simplificar... a diferença que proponho é.. pra ficar mais kanban mesmo... mantém o round.. mas o round é 1 story... vou dar um exemplo.... Temos 3 épicos... o Épico 1 tem 3 stories, o épíco 2 tem 2 stories e o épico 3 tem 5 stories... a tendência era o round 1 ser as stories do épico 1... round 2 ser stories do épico 2 e a mesma regra pro 3... procede? hj é assim ne? a unica diferença da minha proposta é: Épico 1 tem 2 stories. ok.. a entrega do épico 1 tem 2 rounds... Épico 2 tem 3 stories? ok... épico 2 tem 3 rounds... sacou a diferença proposta? só pra simplificar e reduzir.. pq dai ao final do round, o nosso Unclebob faz o code review da Story completa e não de um round grande com 2 ou 3 stories. só pra diminuir o trabalho dele e focar mais.. como usaremos llm local em grande parte do projeto, o gasto a mais com tokens é compensado pela duivisão entre cloud e local... sacou a minha ideia?. Bora planejar? o bombe code fica em ~/projetos/struct/bombe-code E claro, a regra de slice não muda... ela continua como é hj.. essa mexida nos rounds que proponho não muda as outras regras, só reduz o escopo do round.

---

## 2. Índice dos Documentos de Projeto & Missão

- **Inception Geral (`docs/projeto/`):**
  - [Escopo do Produto](file:///home/lexpontes/projetos/struct/bombe-code/docs/projeto/escopo.md) — É/Não é, Objetivos de Negócio e Restrições.
  - [Jornadas do Usuário](file:///home/lexpontes/projetos/struct/bombe-code/docs/projeto/jornada.md) — Fluxos de CLI, modos operacionais e observabilidade de cota.
  - [Definição de MVP](file:///home/lexpontes/projetos/struct/bombe-code/docs/projeto/mvp.md) — Quality gates G1-G6 e fronteiras do MVP.
  - [Sequenciador Geral](file:///home/lexpontes/projetos/struct/bombe-code/docs/projeto/sequenciador.md) — Mapeamento kanban 1 Round = 1 Story (R-1 a R-8).
- **Missão 01 (`docs/missions/01/`):**
  - [PRD da Missão](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/prd/prd.md) — Problemas, Objetivos, Critérios de Aceite e Métricas.
  - [Arquitetura Técnica](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/architecture/architecture.md) — Stack, Contratos, Circuit Breaker, Fila Indiana e 5 ADRs.
  - **Épicos:**
    - [EP-01 — Equalização Core v4 e PDW 4.0](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/epics/epic-01.md)
    - [EP-02 — Orquestrador Híbrido de LLMs & Fallback de Cota](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/epics/epic-02.md)
    - [EP-03 — Esteira Kanban 1 Round = 1 Story & Tríade CLI](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/epics/epic-03.md)
    - [EP-04 — Validação Real End-to-End & Resiliência](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/epics/epic-04.md)
  - **Stories Base:**
    - [STORY-001 (Round 1)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/stories/STORY-001.md) · [STORY-002 (Round 2)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/stories/STORY-002.md) · [STORY-003 (Round 3)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/stories/STORY-003.md) · [STORY-004 (Round 4)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/stories/STORY-004.md) · [STORY-005 (Round 5)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/stories/STORY-005.md) · [STORY-006 (Round 6)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/stories/STORY-006.md) · [STORY-007 (Round 7)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/stories/STORY-007.md) · [STORY-008 (Round 8)](file:///home/lexpontes/projetos/struct/bombe-code/docs/missions/01/stories/STORY-008.md)

---

## 3. Quadro Kanban da Missão

| Round | Story | Épico | Título | Complexidade | Status |
| :---: | :---: | :---: | :--- | :---: | :---: |
| **R-0** | — | — | Upstream Macro (Inception, PRD, Arquitetura, Sequenciador) | — | **VALIDATED** ✅ |
| **R-1** | `STORY-001` | `EP-01` | Migração de Configuração e Runtime Slice-Code | Nível 1 | **VALIDATED** ✅ |
| **R-2** | `STORY-002` | `EP-01` | Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes | Nível 1 | **VALIDATED** ✅ |
| **R-3** | `STORY-003` | `EP-02` | Contrato LLMProviderProtocol e Adapter Local vLLM (Porta 18096, Fila Indiana) | Nível 2 | **VALIDATED** ✅ |
| **R-4** | `STORY-004` | `EP-02` | Classificador de Complexidade de Slice e Roteador Híbrido Dinâmico | Nível 2 | **VALIDATED** ✅ |
| **R-5** | `STORY-005` | `EP-02` | QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local | Nível 3 | **VALIDATED** ✅ |
| **R-6** | `STORY-006` | `EP-02` | FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON | Nível 2 | **READY** ⏳ |
| **R-7** | `STORY-007` | `EP-03` | Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI | Nível 3 | **BACKLOG** 📋 |
| **R-8** | `STORY-008` | `EP-04` | Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local | Nível 2 | **BACKLOG** 📋 |
