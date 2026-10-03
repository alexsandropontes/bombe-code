# STORY ST-036: Decomposição PBB — Modelo de Dados de AtomicTask

> **Épico:** EP-008  
> **Status:** READY  
> **Responsáveis:** @caroli, @unclebob, @turing  
> **Prioridade:** ALTA  

---

## 1. Descrição & Valor
Como Agile Master e Tech Lead,  
Quero que as ai-stories do PBB sejam decompostas em tarefas atômicas (`AtomicTask`) com caráter técnico único (DB, Contrato, Backend TDD, Frontend UI, E2E),  
Para que as LLMs atuem em fatias ultra-focadas sem sobrecarga de contexto, garantindo que cada classe/módulo resolva um único problema de forma limpa.

---

## 2. Critérios INVEST
* **I (Independente):** Não depende de execução de LLM em si, mas da modelagem de dados da tarefa.
* **N (Negociável):** Enums de tipos de tarefa atômica.
* **V (Valiosa):** Previne alucinação e geração de código espaguete pela IA.
* **E (Estimável):** Modelo de dados e parser em módulo dedicado.
* **S (Small):** Classes Pydantic / dataclasses imutáveis e serializáveis.
* **T (Testável):** Validável com testes unitários TDD.

---

## 3. Critérios de Aceite (BDD)

### Cenário 1: Tipos canônicos de tarefas atômicas
* **Dado** a enum `AtomicTaskType`
* **Quando** os tipos forem inspecionados
* **Então** devem existir: `DATABASE`, `CONTRACT`, `BACKEND_TDD`, `FRONTEND_UI` e `E2E_INTEGRATION`.

### Cenário 2: Uma Story vincula uma sequência ordenada de Tasks
* **Dado** uma story `ST-001`
* **Quando** for decomposta em tarefas atômicas
* **Então** deve retornar uma lista ordenada de `AtomicTask` com IDs sequenciais (ex: `ST-001-T1`, `ST-001-T2`), descrição de responsabilidade única e agente responsável correspondente.

### Cenário 3: Serialização e validação de pré-condições da task
* **Dado** uma `AtomicTask` do tipo `BACKEND_TDD`
* **Quando** suas pré-condições forem avaliadas
* **Então** ela deve requerer que a task de `CONTRACT` e `DATABASE` precedentes estejam concluídas.
