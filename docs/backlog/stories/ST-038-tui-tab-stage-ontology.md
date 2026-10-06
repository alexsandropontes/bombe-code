# ST-038: Ontologia da Navegação TAB na TUI e Estágios Canônicos (Onda Zero vs Ondas de Entrega)

> **Story:** ST-038  
> **Épico:** EP-008 (Onda Zero Lean Inception e Ontologia de Ondas)  
> **Status:** DONE
> **Responsáveis:** @turing (Orquestrador), @norman (UI/UX Architect), @unclebob (Tech Lead)  
> **Modo:** tdd-code  

---

## 1. Contexto & Problema
Com a segregação entre Onda Zero (Greenfield / Lean Inception Macro) e Ondas de Entrega Subsequentes (Ondas 1..N e Brownfield), a tecla `TAB` no modo `TDD` da TUI não pode mais ciclar de forma cega pelas 4 etapas tradicionais.
Na Onda Zero, o usuário ou agente está definindo a visão estratégica, viabilidade, personas, jornadas, Canvas MVP e o sequenciador de ondas. Ir acidentalmente para `EXECUTE` ou `VALIDATE` na Onda Zero quebraria o isolamento estrito de UPSTREAM.

Além disso, as nomenclaturas de etapas foram refinadas para refletir a semântica real:
1. **Onda Zero (ou projeto novo recém-criado):**
   - **`DISCOVERY`:** Descoberta de problema, viabilidade de negócio/mercado (@meira, @demarco), pesquisa e briefing.
   - **`INCEPTION`:** Lean Inception oficial (@caroli, @grace, @alan), personas, jornadas, Canvas MVP e Sequenciador de Ondas.
   - O `TAB` cicla estritamente entre `DISCOVERY` ➔ `INCEPTION`.

2. **Ondas Subsequentes (Onda 1..N e Brownfield):**
   - **`PLAN`:** Planejamento da fatia, seleção de épicos, ADRs técnicos e contratos.
   - **`REFINEMENT`:** Refinamento PBB (@caroli, @david) fatiando stories em tarefas atômicas especializadas.
   - **`EXECUTE`:** Construção TDD fullstack task-by-task.
   - **`VALIDATE`:** Homologação e qualidade E2E.
   - O `TAB` cicla exclusivamente entre `PLAN` ➔ `REFINEMENT` ➔ `EXECUTE` ➔ `VALIDATE`.

3. **Modo VIBE:**
   - O `TAB` permanece inalterado (modo livre, sem travas de etapa).

---

## 2. Critérios de Aceitação (INVEST)
* [x] **AC-1:** Projeto novo / recém-criado sem estado prévio inicializa autônomamente em `DISCOVERY`.
* [x] **AC-2:** Pressionar `TAB` na Onda Zero cicla estritamente entre `DISCOVERY` e `INCEPTION`.
* [x] **AC-3:** Pressionar `TAB` em Ondas de Entrega cicla sequencialmente entre `PLAN` ➔ `REFINEMENT` ➔ `EXECUTE` ➔ `VALIDATE`.
* [x] **AC-4:** `stage_guard.py` trata `DISCOVERY` com bloqueio total de código de produção e testes (igual a DISCUSS), e `INCEPTION` e `REFINEMENT` com bloqueio de código de produção (permitindo docs).
* [x] **AC-5:** `state_machine.py` reconhece `DISCOVERY` e `INCEPTION` em `WaveState` e bloqueia transições ilegais para `EXECUTE` ou `VALIDATE` na Onda Zero.
* [x] **AC-6:** Modo VIBE não sofre interferência: o `TAB` não cicla etapas quando `mode == "VIBE"`.
* [x] **AC-7:** 100% dos testes unitários passando.
