# STORY ST-028: Downstream Review Gate & Validação dos Revisores (@aniche & @unclebob)

> **Épico:** [EP-006: Orquestração do Turing, Gates Determinísticos & Kanban Dinâmico](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/epics/EP-006-turing-flow-orchestration-and-gates.md)  
> **Status:** DONE
> **Prioridade:** ALTA  
> **Responsáveis:** @turing (Autônomo da ONDA), @aniche (Test Architect), @unclebob (Tech Lead)  
> **Modo:** tdd-code  

---

## 1. Descrição
Como orquestrador do ciclo de execução (`WaveOrchestrator`),  
Desejo submeter cada entrega de story do downstream à dupla revisão independente de `@aniche` (testes e cobertura) e `@unclebob` (Clean Code e SOLID),  
Para que o `TuringReviewGate` valide deterministicamente se ambos os revisores aprovaram a entrega antes de autorizar a finalização do card.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Dupla aprovação e validação com sucesso
* **Dado** que um desenvolvedor especialista implementou uma story com testes
* **Quando** `@aniche` emitir parecer positivo para a suíte de testes
* **E** `@unclebob` emitir parecer positivo para Clean Code e SOLID
* **Então** o `TuringReviewGate` deve aprovar a entrega e carimbar o review.

### Cenário 2: Veto de testes por @aniche
* **Dado** que a suíte de testes possui falhas, cobertura insuficiente ou testes flaky
* **Quando** `@aniche` vetar a entrega
* **Então** o `TuringReviewGate` deve rejeitar a finalização da story com o apontamento de falhas de teste.

### Cenário 3: Veto de código por @unclebob
* **Dado** que o código contém violações de SOLID, acoplamento indevido ou funções obscuras
* **Quando** `@unclebob` vetar a entrega
* **Então** o `TuringReviewGate` deve rejeitar a finalização da story com o apontamento de refatoração necessária.

### Cenário 4: Integração com o `run_cycle`
* **Dado** a execução de um ciclo de story via `orchestrator.run_cycle(story_id)`
* **Quando** os revisores forem despachados
* **Então** o resultado do review deve ser persistido no registro da demanda.
