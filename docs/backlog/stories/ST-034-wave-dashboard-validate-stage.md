# STORY ST-034: Visualização de Bloqueios e DEV_DONE no Dashboard da ONDA

> **Épico:** EP-007  
> **Status:** DONE
> **Responsáveis:** @turing, @alan, @norman  
> **Prioridade:** MÉDIA  

---

## 1. Descrição & Valor
Como operador do Bombe Code e gestor de fluxo,  
Quero que o `/wave status` e o comando CLI exibam cards em `DEV_DONE` e destaquem cards bloqueados com `🛑 [BLOCKED]`,  
Para que a parada da linha de montagem seja visível imediatamente no local exato do problema.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Card bloqueado é destacado no Kanban
* **Dado** que um card em `IN_PROGRESS` teve a flag `is_blocked = True` acionada
* **Quando** o usuário executar `bombe-code wave status` ou `/wave status`
* **Então** o card deve ser exibido com o indicador `🛑 [BLOCKED: <motivo>]` preservando o status da coluna onde ocorreu o problema.
