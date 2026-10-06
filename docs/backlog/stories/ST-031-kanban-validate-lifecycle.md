# STORY ST-031: Ciclo de Vida do Kanban com DEV_DONE, VALIDATE e DONE

> **Épico:** EP-007  
> **Status:** DONE
> **Responsáveis:** @turing, @caroli, @edith  
> **Prioridade:** ALTA  

---

## 1. Descrição & Valor
Como desenvolvedor e arquiteto de software,  
Quero que o card transite por `DEV_DONE` e `VALIDATE` antes de atingir o `DONE` definitivo,  
Para que o board de Kanban reflita a situação real da entrega e mostre quando uma story está em validação por `@edith`.

---

## 2. Critérios INVEST
* **I (Independente):** Não depende de outros épicos.
* **N (Negociável):** Estados mapeados no Enum do Kanban.
* **V (Valiosa):** Transparência total no fluxo físico de entrega.
* **E (Estimável):** Escopo delimitado no KanbanManager e WaveOrchestrator.
* **S (Small):** Ajuste preciso na máquina de estados do card.
* **T (Testável):** Validável com testes unitários TDD.

---

## 3. Critérios de Aceite (BDD)

### Cenário 1: Conclusão técnica da story move para DEV_DONE
* **Dado** que a story `ST-001` foi executada em TDD e aprovada por `@aniche` e `@unclebob`
* **Quando** o ciclo atômico `run_cycle` for concluído
* **Então** o status do card deve ser `DEV_DONE` no banco SQLite e no arquivo físico.

### Cenário 2: Início da validação de produto move para VALIDATE
* **Dado** que as stories da ONDA estão com status `DEV_DONE`
* **Quando** `run_validate` for acionado
* **Então** os cards devem transitar para o status `VALIDATE`.

### Cenário 3: Homologação de produto promove para DONE definitivo
* **Dado** que os cards estão em `VALIDATE` e `@edith` homologou a entrega
* **Quando** a validação formal for concluída com sucesso
* **Então** todos os cards devem transitar para o status `DONE` definitivo.
