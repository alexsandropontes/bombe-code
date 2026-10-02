# STORY ST-030: Dashboard `/wave status` Enriquecido na CLI e TUI

> **Épico:** [EP-006: Orquestração do Turing, Gates Determinísticos & Kanban Dinâmico](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/epics/EP-006-turing-flow-orchestration-and-gates.md)  
> **Status:** READY  
> **Prioridade:** ALTA  
> **Responsáveis:** @norman (UI/UX), @turing (Soberano da ONDA)  
> **Modo:** tdd-code  

---

## 1. Descrição
Como desenvolvedor de software ou operador do framework,  
Desejo executar `/wave status` na TUI ou `bombe-code wave status` no CLI e visualizar uma radiografia rica e organizada do projeto,  
Para que eu consiga inspecionar instantaneamente o estágio da ONDA, a checklist de aprovação de Gates Upstream e a tabela detalhada de cards no Kanban.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Visualização dos Gates de Upstream
* **Dado** que a ONDA passou por `DISCUSS` e `PLAN`
* **Quando** eu consultar `/wave status`
* **Então** deve exibir o status individual de cada gate:
  - `PRDQualityGate`: ✅ Aprovado ou ❌ Reprovado
  - `JourneyGate`: ✅ Aprovado ou ❌ Reprovado
  - `ArchitectureGate`: ✅ Aprovado ou ❌ Reprovado
  - `StoryDoRGate`: ✅ Aprovado ou ❌ Reprovado

### Cenário 2: Tabela de Cards da ONDA
* **Dado** cards registrados no Kanban da ONDA ativa
* **Quando** exibido o relatório
* **Então** deve apresentar tabela contendo colunas: `ID`, `Título`, `Responsável`, `Status` (`BACKLOG`, `IN_PROGRESS`, `IN_REVIEW`, `DONE`) e `Reviewers`.

### Cenário 3: Exibição no CLI Typer com Rich
* **Dado** a execução de `bombe-code wave status`
* **Quando** renderizado no terminal
* **Então** deve utilizar painéis e tabelas Rich formatadas com cores semânticas.
