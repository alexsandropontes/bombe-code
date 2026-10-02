# ÉPICO EP-003: ORQUESTRADOR DA ONDA & COMANDOS DE FLUXO (/wave)

> **Status:** Aberto / Em Execução  
> **Onda:** ONDA-004  
> **Dependência:** EP-001 (Turing Runtime Foundation), EP-002 (Elenco Completo de 23 Agentes)  
> **Princípio Central:** Unificação total sob o namespace `/wave` (sem bifurcação spec vs. tdd).

---

## 1. Visão do Épico

O Bombe Code opera como um harness determinístico orientado a ondas de desenvolvimento. Este épico implementa o **`WaveOrchestrator`** e a família de comandos `/wave`, conectando a máquina de estados finita do Turing ([`TuringStateMachine`](file:///home/lexpontes/projetos/struct/bombe-code/src/bombe_code/turing/state_machine.py)), a persistência SQLite local ([`ProjectDatabase`](file:///home/lexpontes/projetos/struct/bombe-code/src/bombe_code/storage/project_db.py)), os gates determinísticos ([`TuringGates`](file:///home/lexpontes/projetos/struct/bombe-code/src/bombe_code/turing/gates.py)) e os 23 especialistas do [`AgentRegistry`](file:///home/lexpontes/projetos/struct/bombe-code/src/bombe_code/agents/registry.py).

---

## 2. Mapa dos Comandos de Fluxo (/wave)

| Comando | Escopo / Etapa | Agente Líder | Comportamento Operacional |
| :--- | :--- | :--- | :--- |
| **`/wave start [ID]`** | Ciclo de Vida | `@turing` | Inicializa nova ONDA no SQLite, define etapa `DISCUSS`, limpa checkpoints e cria contexto. |
| **`/wave status`** | Observabilidade | `@turing` | Retorna radiografia determinística: ONDA ativa, etapa, stories pendentes e gates. |
| **`/wave discuss`** | UPSTREAM / `DISCUSS` | `@meira` & `@grace` | Executa validação de viabilidade (`viability.md`) e elaboração do PRD (`PRD.md`). |
| **`/wave plan`** | UPSTREAM / `PLAN` | `@alan`, `@norman`, `@ieru`, `@codd`, `@barreto`, `@caroli` | Executa jornada, UI/UX, arquitetura, dados, threat model e breakdown de stories com DoR. |
| **`/wave cycle [ST-XXX]`**| DOWNSTREAM / `EXECUTE` | Stack Dev + `@unclebob` | **Atômico (1 Story):** Executa o ciclo TDD (RED ➔ GREEN ➔ REFACTOR), review do Tech Lead e **para**. |
| **`/wave execute`** | DOWNSTREAM / `EXECUTE` | Stack Dev + `@unclebob` | **Lote Total (Cycle-Full):** Executa da Story 1 à última. No modo `MANUAL`/`SEMI_AUTO`, pausa e pede OK a cada story. |
| **`/wave validate`** | DOWNSTREAM / `VALIDATE`| `@edith` & `@nina` | Auditoria formal PRD vs. Entregável (Selo Final) e governança FinOps/Tokens. |
| **`/wave end`** | Ciclo de Vida | `@turing` | Conclui e arquiva a ONDA com status `COMPLETED`. |

---

## 3. Decomposição das Stories (ai-story)

1. **ST-015: Motor WaveOrchestrator Central**
   - Criação da classe `WaveOrchestrator` em `src/bombe_code/turing/orchestrator.py` orquestrando transições de estado, dispatch de agentes e chamada de gates.
2. **ST-016: Comandos de Upstream (`/wave start`, `/wave status`, `/wave discuss`, `/wave plan`)**
   - Execução determinística dos despachos de viabilidade, PRD, jornada e planejamento técnico.
3. **ST-017: Comandos de Downstream (`/wave cycle`, `/wave execute`, `/wave validate`, `/wave end`)**
   - Execução atômica por story (`/wave cycle`), execução em lote com pausa interativa (`/wave execute`), validação com selo (`/wave validate`) e encerramento.
4. **ST-018: Integração com TUI Textual & CLI Typer**
   - Handlers registrados em `src/bombe_code/tui/commands.py` e comandos `bombe-code wave ...` na CLI typer.
