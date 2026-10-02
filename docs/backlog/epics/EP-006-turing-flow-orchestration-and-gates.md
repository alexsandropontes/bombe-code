# ÉPICO EP-006: Orquestração do Turing, Gates Determinísticos & Kanban Dinâmico

> **Status:** PLANNING -> READY FOR IMPLEMENTATION  
> **Onda:** ONDA-006  
> **Modo:** tdd-code (Sem teste RED = Sem código de produção)  
> **Liderança:** @turing (Soberano da ONDA), @grace (Product Strategy), @ieru (Software Architecture), @unclebob (Tech Lead), @aniche (Test Architect)  

---

## 1. Contexto & Proposta de Valor (Fase DISCUSS)

### 1.1 Análise de Viabilidade Técnica e Estratégica (@meira)
O Bombe Code já dispõe dos comandos de fluxo (`/wave`) e dos agentes especialistas cadastrados. No entanto, para garantir autonomia real de nível industrial, a transição entre etapas não pode depender de confiança cega na saída de LLMs.  
É mandatório estabelecer **Gates Determinísticos de Inspeção**:
1. **No Upstream (DISCUSS e PLAN):** O Turing fiscaliza se os artefatos concretos (PRD, Jornada, Arquitetura e ai-stories com DoR) possuem estrutura e completude exigidas antes de autorizar o avanço para a etapa de implementação.
2. **No Downstream (EXECUTE):** O Turing exige a dupla aprovação de `@aniche` (qualidade de testes e cobertura) e `@unclebob` (Clean Code e SOLID), além da execução verde da suíte automatizada, para permitir que qualquer card no Kanban seja movido para `DONE`.

### 1.2 Documento de Requisitos de Produto / PRD (@grace)
* **Objetivo:** Estabelecer uma linha de montagem com controle de qualidade em cada estação de trabalho, com sincronização em tempo real de cards no SQLite e no disco.
* **Critérios RICE:**
  - **Reach:** 100% dos fluxos de entrega e agentes do sistema.
  - **Impact:** Máximo (previne retrabalho, alucinações e histórias mal definidas no downstream).
  - **Confidence:** 100%.
  - **Effort:** Médio-Alto (implementação de gates, sincronizador de Kanban e visualizador de status).

---

## 2. Arquitetura Técnica & Decisões Estruturais (Fase PLAN - @ieru & @unclebob)

### 2.1 Gates Determinísticos de Upstream
* `PRDQualityGate`: Valida se o documento ou saída do PRD contém:
  - `Visão Geral`, `Problema`, `Personas`, `Critérios RICE`, `MVP Operacional`.
* `JourneyGate`: Valida se a jornada do usuário contém:
  - `Entry Points`, `Fluxo de Navegação`, `Mapeamento de Telas`.
* `ArchitectureGate`: Valida se a arquitetura contém:
  - `Decisões Arquiteturais`, `Stack Tecnológica`, `Padrões de Comunicação`.
* `StoryDoRGate`: Valida se as stories contêm:
  - Critérios INVEST, Cenários BDD (`Dado/Quando/Então`) e Definition of Ready.

### 2.2 Gate de Downstream (Review Gate)
* `TuringReviewGate`: Inspeciona os pareceres formais de:
  - `@aniche`: Suíte de testes automatizados presente, cobertura válida e ausência de testes flaky.
  - `@unclebob`: Conformidade com Clean Code, legibilidade e princípios SOLID.
  - Resultado da execução de testes do projeto (100% passing).

### 2.3 Sincronizador Dinâmico de Kanban (`KanbanManager`)
* Tabela no SQLite `state.db` mapeando stories da ONDA (`story_id`, `wave_id`, `title`, `agent`, `status`, `review_aniche`, `review_unclebob`).
* Estados permitidos: `BACKLOG` -> `READY` -> `IN_PROGRESS` -> `IN_REVIEW` -> `DONE`.
* Sincronização bidirecional com os arquivos físicos em `docs/backlog/stories/ST-xxx.md`.

### 2.4 `/wave status` Enriquecido
* Exibição visual detalhada:
  - Identificador da ONDA, autonomia e modo de engenharia.
  - Árvore de aprovação de Gates Upstream (✅/❌ com lista de pendências se houver).
  - Tabela formatada das stories no Kanban com status e parecer dos revisores.

---

## 3. Decomposição das Histórias de Usuário (ai-stories)

* [ST-027: Upstream Flow Pipeline & Gates Determinísticos do Turing](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/stories/ST-027-upstream-pipeline-and-gates.md)
* [ST-028: Downstream Review Gate & Validação dos Revisores (@aniche & @unclebob)](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/stories/ST-028-downstream-review-gate.md)
* [ST-029: Sincronização Dinâmica do Kanban (SQLite + Cards Físicos)](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/stories/ST-029-dynamic-kanban-sync.md)
* [ST-030: Dashboard `/wave status` Enriquecido na CLI e TUI](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/stories/ST-030-wave-status-dashboard.md)
