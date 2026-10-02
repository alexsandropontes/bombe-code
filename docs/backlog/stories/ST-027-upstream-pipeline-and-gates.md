# STORY ST-027: Upstream Flow Pipeline & Gates Determinísticos do Turing

> **Épico:** [EP-006: Orquestração do Turing, Gates Determinísticos & Kanban Dinâmico](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/epics/EP-006-turing-flow-orchestration-and-gates.md)  
> **Status:** READY  
> **Prioridade:** ALTA  
> **Responsáveis:** @turing (Soberano da ONDA), @grace (Product Strategy), @ieru (Software Architecture)  
> **Modo:** tdd-code  

---

## 1. Descrição
Como orquestrador do ciclo de vida da ONDA (`WaveOrchestrator`),  
Desejo executar os agentes de Upstream (`@meira`, `@grace`, `@alan`, `@ieru`, `@caroli`, `@unclebob`) e validar seus entregáveis através de gates determinísticos (`PRDQualityGate`, `JourneyGate`, `ArchitectureGate`, `StoryDoRGate`),  
Para que a ONDA só transite para a etapa de implementação (`EXECUTE`) se todos os requisitos de qualidade contratual estiverem comprovadamente atendidos.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Validação determinística do PRD (PRDQualityGate)
* **Dado** um documento ou saída de PRD
* **Quando** o `PRDQualityGate.evaluate(content)` for executado
* **Então** deve aprovar se contiver as seções: "Visão Geral", "Problema", "Personas", "Critérios RICE" e "MVP Operacional"
* **E** deve rejeitar apontando exatamente quais seções estão ausentes caso alguma falte.

### Cenário 2: Validação da Jornada do Usuário (JourneyGate)
* **Dado** o artefato de jornada gerado por `@alan`
* **Quando** o `JourneyGate.evaluate(content)` for executado
* **Então** deve verificar a presença de "Entry Points", "Fluxo de Navegação" e "Telas/Componentes".

### Cenário 3: Validação da Arquitetura e Decisões Técnicas (ArchitectureGate)
* **Dado** o artefato arquitetural gerado por `@ieru`
* **Quando** o `ArchitectureGate.evaluate(content)` for executado
* **Então** deve verificar decisões de stack, camadas ou ports/adapters.

### Cenário 4: Validação de DoR de Stories (StoryDoRGate)
* **Dado** uma lista de stories geradas por `@caroli` ou `@david`
* **Quando** o `StoryDoRGate.evaluate(stories)` for executado
* **Então** deve validar se cada story possui critérios INVEST, cenários BDD ("Dado", "Quando", "Então") e critérios de aceite objetivos.

### Cenário 5: Transição bloqueada do Turing se algum gate falhar
* **Dado** que a ONDA está em `PLAN`
* **Quando** eu tentar transicionar para `EXECUTE` com um gate de Upstream reprovado
* **Então** o Turing deve barrar a transição e retornar a lista determinística de não-conformidades.
