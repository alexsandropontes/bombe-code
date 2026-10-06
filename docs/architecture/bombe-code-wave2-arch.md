# Arquitetura Técnica — ONDA 2: Turing Runtime Engine & Pydantic AI

## 1. Visão Geral da Arquitetura

A Onda 2 introduz três pilares estruturais no pacote `bombe_code`:
1. **Camada de Orquestração Autônoma (`bombe_code.turing`):** Máquina de estados da ONDA, barramento de eventos, orquestrador, classificadores de intenção e gates.
2. **Camada de LLM Baseada em Pydantic AI (`bombe_code.llm` / `PydanticAiFactory`):** Centralização tipada de workers de IA.
3. **Camada de Persistência Local do Projeto (`bombe_code.storage.project_db`):** SQLite local assíncrono em `.bombe-code/state.db` gerenciando o Kanban de tasks internas dos agentes e checkpoints da ONDA.

---

## 2. Diagrama de Componentes

```
┌────────────────────────────────────────────────────────────────────────┐
│                              TUI / CLI                                 │
│          (Textual: Tab para alternar Discuss/Plan/Execute/Validate)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        TURING RUNTIME ENGINE                           │
│                                                                        │
│   ┌────────────────────────┐         ┌─────────────────────────────┐   │
│   │ TuringIntentClassifier │         │      TuringStateMachine     │   │
│   │ (Regex/Slots - 0 tok)  │         │ (Discuss/Plan/Exec/Validate)│   │
│   └───────────┬────────────┘         └──────────────┬──────────────┘   │
│               │                                     │                  │
│               ▼                                     ▼                  │
│   ┌────────────────────────┐         ┌─────────────────────────────┐   │
│   │    TuringGatesEngine   │         │       WaveOrchestrator      │   │
│   │(Cara-crachá + Selos TL)│         │ (Despacho de Agentes/Cycles)│   │
│   └────────────────────────┘         └──────────────┬──────────────┘   │
└─────────────────────────────────────────────────────┼──────────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       ▼                                                             ▼
┌──────────────────────────────────────────────┐              ┌──────────────────────────────────────────────┐
│             PydanticAiFactory                │              │           ProjectStorage (SQLite)            │
│   • Agentes tipados Pydantic AI              │              │   • .bombe-code/state.db                     │
│   • Retries automáticos                      │              │   • Kanban Operacional de Tasks dos Agentes  │
│   • Provedores (OpenAI, Anthropic, Ollama, pg)│             │   • Checkpoints de Estado da ONDA            │
└──────────────────────────────────────────────┘              └──────────────────────────────────────────────┘
```

---

## 3. Módulos e Pacotes a Implementar

### 3.1. `bombe_code.turing.classifier`
* `TuringIntentResult`: Dataclass tipada (`intention`, `confidence`, `slots`, `needs_llm`).
* `TuringIntentClassifier`: Classificador determinístico em Python puro com match de intenções de engenharia (`wave_status`, `start_discuss`, `start_plan`, `start_cycle`, `review_cycle`, `validate_wave`, `toggle_mode`).

### 3.2. `bombe_code.turing.state_machine`
* `WaveState` (Enum): `DISCUSS`, `PLAN`, `EXECUTE`, `VALIDATE`, `COMPLETED`.
* `AutonomyMode` (Enum): `AUTO`, `SEMI_AUTO`, `MANUAL`.
* `EngineeringMode` (Enum): `TDD_CODE`, `VIBE_CODE`.
* `TuringStateMachine`: Máquina de estados finita com transições controladas e persistência no banco local.

### 3.3. `bombe_code.turing.gates`
* `TemplateGate`: Verifica se artefatos esperados existem no caminho e atendem aos cabeçalhos obrigatórios do template.
* `SealGate`: Fiscaliza se a Story contém o `[SELO TECH LEAD: APROVADO]` ou se a Onda contém o `[SELO VALIDATOR: HOMOLOGADO]`.
* `ConsumerHandoffGate`: Permite ao agente consumidor rejeitar insumos rasos e gerar rework prompts automáticos.

### 3.4. `bombe_code.llm.pydantic_factory`
* Adicionar dependência `pydantic-ai` ao `pyproject.toml`.
* `PydanticAiFactory`: Fábrica central de instâncias de agentes Pydantic AI (`Agent`), configurando o modelo de inferência (remoto ou local OpenAI-compatível como llama.cpp).
* Funções auxiliares para execução de prompts estruturados tipados com fallback gracioso.

### 3.5. `bombe_code.storage.project_db`
* `ProjectDatabase`: Driver assíncrono para `.bombe-code/state.db` via `aiosqlite` (ou sqlite3 síncrono padrão para simplicidade e zero complexidade).
* Tabelas:
  - `wave_state`: Armazena a onda ativa, estação atual, modo de autonomia e modo de engenharia.
  - `agent_tasks`: Kanban operacional de tasks dos agentes (`id`, `story_id`, `agent_role`, `title`, `status`, `created_at`, `updated_at`).

### 3.6. `bombe_code.tui.app` (Integração do `Tab` nas 4 Estações)
* Capturar a tecla `tab` no `BombeTuiApp`.
* Alternar ciclicamente entre:
  `DISCUSS` ──▶ `PLAN` ──▶ `EXECUTE` ──▶ `VALIDATE`.
* Refletir a estação ativa na barra de status e no cabeçalho.
