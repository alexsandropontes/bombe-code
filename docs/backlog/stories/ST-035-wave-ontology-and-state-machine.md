# STORY ST-035: Ontologia de Ondas — WaveType e Máquina de Estados Diferenciada

> **Épico:** EP-008  
> **Status:** DONE
> **Responsáveis:** @turing, @caroli  
> **Prioridade:** ALTA  

---

## 1. Descrição & Valor
Como orquestrador do sistema Bombe Code,  
Quero diferenciar uma `WAVE_ZERO` (Lean Inception Macro, apenas Upstream) de uma `DELIVERY_WAVE` (Ondas 1..N e Brownfield: PLAN ➔ REFINEMENT ➔ EXECUTE ➔ VALIDATE),  
Para que projetos Greenfield comecem com planejamento estratégico sem código e ondas subsequentes operem no ciclo completo com PBB fino e execução atômica.

---

## 2. Critérios INVEST
* **I (Independente):** Define a estrutura base de tipos e estados da ONDA.
* **N (Negociável):** Estados mapeados no `TuringStateMachine`.
* **V (Valiosa):** Evita desperdício de código na concepção inicial e organiza as ondas de entrega.
* **E (Estimável):** Escopo delimitado no `state_machine.py`.
* **S (Small):** Ajuste preciso nos enums e nas validações de transição.
* **T (Testável):** Validável com testes unitários em pytest.

---

## 3. Critérios de Aceite (BDD)

### Cenário 1: ONDA ZERO permite apenas etapas de Upstream
* **Dado** uma onda inicializada como `WAVE_ZERO` (ou com ID `ONDA-000` / `WAVE-000`)
* **Quando** o estado transitar após `DISCUSS`
* **Então** a única transição válida é para `PLAN`
* **E** a transição de `PLAN` para `EXECUTE` deve ser estritamente bloqueada com `InvalidTransitionError`.

### Cenário 2: ONDA DE ENTREGA suporta o ciclo canônico
* **Dado** uma onda de entrega (`DELIVERY_WAVE` / Onda 1..N ou Brownfield)
* **Quando** as transições forem solicitadas
* **Então** a máquina deve suportar a cadeia `PLAN ➔ REFINEMENT ➔ EXECUTE ➔ VALIDATE ➔ COMPLETED`.

### Cenário 3: Detecção automática do tipo de onda por ID ou configuração
* **Dado** a inicialização da onda
* **Quando** `wave_id` for `ONDA-000` ou parâmetro `wave_type` for informado
* **Então** a máquina de estados deve configurar automaticamente o `WaveType` correspondente.
