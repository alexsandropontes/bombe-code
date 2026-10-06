# STORY ST-029: Sincronização Dinâmica do Kanban (SQLite + Cards Físicos)

> **Épico:** [EP-006: Orquestração do Turing, Gates Determinísticos & Kanban Dinâmico](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/epics/EP-006-turing-flow-orchestration-and-gates.md)  
> **Status:** DONE
> **Prioridade:** ALTA  
> **Responsáveis:** @david (Agile Master & Flow), @turing (Autônomo da ONDA)  
> **Modo:** tdd-code  

---

## 1. Descrição
Como desenvolvedor, Scrum Master ou agente autônomo,  
Desejo ter um gerenciador de Kanban dinâmico (`KanbanManager`) que sincronize os cards no banco local SQLite (`state.db`) e nos arquivos markdown físicos em `docs/backlog/stories/ST-xxx.md`,  
Para que o status de cada demanda reflita com precisão o estado real do projeto e nunca haja divergência entre o banco e os arquivos de documentação.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Registro e transição de demanda no SQLite
* **Dado** que uma nova story é planejada para a ONDA
* **Quando** `KanbanManager.add_card(...)` for executado
* **Então** deve persistir o card com status inicial `BACKLOG` ou `READY`.
* **Quando** o card for transicionado para `IN_PROGRESS`, `IN_REVIEW` ou `DONE`
* **Então** o registro no banco deve ser atualizado com timestamp e histórico.

### Cenário 2: Sincronização física com arquivo markdown
* **Dado** um card no SQLite com ID `ST-020`
* **Quando** seu status mudar para `DONE`
* **Então** o `KanbanManager.sync_file(story_id)` deve atualizar a linha `> **Status:** DONE` no arquivo correspondente em `docs/backlog/stories/`.

### Cenário 3: Varredura de stories existentes
* **Dado** um diretório de projeto com arquivos de stories em `docs/backlog/stories/`
* **Quando** `KanbanManager.scan_and_sync()` for invocado
* **Então** todas as stories devem ser carregadas e catalogadas no banco SQLite da ONDA.
