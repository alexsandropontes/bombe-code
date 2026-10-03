# STORY ST-037: Despachante de Execução por Task no WaveOrchestrator

> **Épico:** EP-008  
> **Status:** READY  
> **Responsáveis:** @turing, @unclebob, @valim, @aniche  
> **Prioridade:** ALTA  

---

## 1. Descrição & Valor
Como orquestrador do ciclo de engenharia do Bombe Code,  
Quero executar o ciclo TDD despachando a LLM tarefa por tarefa em vez de consumir a story completa de uma vez,  
Para que cada agente atue estritamente no seu domínio (DBA, Backend, Frontend) com contexto isolado, gerando código robusto, testado e sem alucinações.

---

## 2. Critérios INVEST
* **I (Independente):** Integração com o `WaveOrchestrator`.
* **N (Negociável):** Estrutura de execução sequencial no método `run_story_tasks`.
* **V (Valiosa):** Redução drástica de falhas e retrabalho na esteira de código.
* **E (Estimável):** Métodos de execução atômica no orquestrador.
* **S (Small):** Loop orquestrado por task.
* **T (Testável):** Validável com testes unitários TDD e mocks controlados de runner.

---

## 3. Critérios de Aceite (BDD)

### Cenário 1: Execução sequencial respeita dependência entre tasks
* **Dado** uma story com 3 tasks: `DB`, `BACKEND_TDD` e `FRONTEND_UI`
* **Quando** o orquestrador executar a story por tasks
* **Então** a task `DB` deve ser concluída antes da invocação da task `BACKEND_TDD`.

### Cenário 2: Falha em uma task interrompe a sequência (Fail-Fast)
* **Dado** que a task `BACKEND_TDD` falhou nos testes
* **Quando** o despachante avaliar o resultado
* **Então** a execução deve pausar imediatamente com status `FAILED`, sem despachar a task de frontend.

### Cenário 3: Conclusão de todas as tasks promove a story para DEV_DONE
* **Dado** que todas as tarefas atômicas da story foram concluídas com sucesso
* **Quando** a última task finalizar
* **Então** a story é consolidada e promovida para `DEV_DONE` para homologação.
