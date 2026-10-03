# EP-008: Onda Zero (Lean Inception Macro) e Ontologia das Ondas Subsequentes (Plan, Refinement/PBB, Execute por Task Atômica, Validate)

> **Épico:** EP-008  
> **Status:** IN_PROGRESS  
> **Responsáveis:** @turing (Orquestrador), @caroli (Lean Inception & PBB Master), @grace (Produto), @unclebob (Tech Lead)  
> **Modo:** tdd-code  

---

## 1. Visão Geral & Problema
A esteira de agentes do Bombe Code necessita de uma ontologia rigorosa e clara para diferenciar o nascimento de um produto (Greenfield) da sua evolução contínua (Brownfield ou Ondas Subsequentes):

1. **ONDA ZERO (`ONDA-000` / Greenfield):**
   - É estritamente **UPSTREAM** (zero código de produção, zero downstream).
   - Executa a **Lean Inception Macro** adaptada ao Delivery Target (Mini para POC/Prototype, Completa para MVP Premium, Deep para Enterprise).
   - Etapas exclusivas: `DISCUSS` (Viabilidade e Visão) e `PLAN` (Lean Inception com Jornadas, ADRs macro, Canvas MVP e o **Sequenciador de Ondas**).
   - Entrega o planejamento estratégico macro distribuindo as funcionalidades nas Ondas 1, 2, 3...

2. **ONDAS DE ENTREGA SUBSEQUENTES (Onda 1..N e Brownfield / Evolução):**
   - Executam a entrega incremental nas 4 etapas ontológicas:
     - **`PLAN`:** Pega as funcionalidades daquela onda, define os Épicos detalhados e executa Elicitation cirúrgica com o usuário para fechar pontas soltas.
     - **`REFINEMENT` (PBB Real):** Conduzido pelo `@caroli`, fatia Épicos em Stories de Problema Único (SRP) e decompõe cada Story em **Tarefas Atômicas (`AtomicTask`)**: DB, Contratos, Backend TDD, Frontend UI e E2E.
     - **`EXECUTE`:** A LLM não consome a story inteira de uma vez; o Turing despacha **task por task** no ciclo Red-Green-Refactor.
     - **`VALIDATE`:** Homologação funcional com `@edith` e fechamento formal da entrega.

---

## 2. Diagrama de Transição de Ondas

```
[GREENFIELD] ──► ONDA-000 (Lean Inception Macro: DISCUSS ➔ PLAN)
                     │
                     ▼
             [Sequenciador de Ondas: Onda 1, Onda 2, Onda 3...]
                     │
                     ▼
[BROWNFIELD / EVOLUÇÃO] ──► ONDAS DE ENTREGA (PLAN ➔ REFINEMENT ➔ EXECUTE ➔ VALIDATE)
```

---

## 3. Stories do Épico
* **ST-035:** Ontologia de Ondas — `WaveType` (`WAVE_ZERO` vs `DELIVERY_WAVE`), estados permitidos por tipo de onda e transições no `TuringStateMachine`.
* **ST-036:** Decomposição PBB — Modelo de dados para `AtomicTask` (DB, Contract, Backend TDD, Frontend UI, E2E), vinculadas à Story de problema único.
* **ST-037:** Despachante de Execução por Task no `WaveOrchestrator` — Execução sequencial e atômica com isolamento de contexto no ciclo TDD.
