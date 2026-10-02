# PRD — ONDA 2: Turing Runtime Engine, Pydantic AI Factory & Dynamic TUI

## 1. Visão Geral e Objetivo
A **ONDA 2** tem como meta transformar o Bombe Code de um harness convencional de execução isolada de prompts em uma **máquina de engenharia autônoma e determinística**. O objetivo central é introduzir o **Turing Runtime**, que substitui o humano na tarefa repetitiva de guiar turnos de LLM, mantendo controle de fluxo, validação de templates, fiscalização de selos e persistência limpa de estado.

---

## 2. Escopo Funcional da Onda 2

### 2.1. Turing Runtime Engine (Máquina de Estados da ONDA)
* **Estados da ONDA:**
  - `DISCUSS`: Entendimento, intenção e PRD.
  - `PLAN`: Arquitetura, ADRs, Épicos e Stories com DoR.
  - `EXECUTE`: Construção por Cycles (Stories verticais) com TDD e Tech Lead Review.
  - `VALIDATE`: Auditoria de contrato entre o especificado no Upstream e o entregue no Downstream.
* **Modos de Autonomia:**
  - `AUTO`: Avança continuamente entre estações e cycles, escalando apenas dúvidas críticas.
  - `SEMI-AUTO`: Executa o Upstream completo, pausa para autorização humana e executa o Downstream.
  - `MANUAL`: Pausa explícita por estação e cycle.
* **Modos de Engenharia:**
  - `tdd-code`: Rigor pleno (RED/GREEN no backend, Construction no front, review obrigatório).
  - `vibe-code`: Agilidade máxima e prototipagem fluida com cerimônia reduzida.

### 2.2. Os Cérebros do Turing (Custo Zero de Tokens)
* **Cérebro Determinístico Local (`TuringIntentClassifier`):**
  - Reconhecimento ultrarrápido em Python (regex e extração de slots) para comandos e intenções rotineiras de engenharia.
  - Custo de tokens: **Zero**. Latência: **< 1ms**.
* **Cérebro Heurístico (Mini-LM / LLM Classificadora sob Demanda):**
  - Acionado exclusivamente quando o classificador local marcar `needs_llm=True` devido a ambiguidade semântica.

### 2.3. Governança de Gates e Selos
* **Turing Gate Cara-Crachá:**
  - Validação física de presença de arquivos de saída esperados no caminho e nome exatos.
  - Verificação de templates estruturais obrigatórios.
  - Verificação de autenticidade dos **Selos** (Selo do Tech Lead no `EXECUTE` e Selo do Contract Validator no `VALIDATE`).
* **Gate de Entrada do Consumidor (`ConsumerHandoffGate`):**
  - O agente que recebe o documento valida sua completude e profundidade semântica antes de iniciar o trabalho; insumos rasos são rejeitados com feedback estruturado de retrabalho (*rework prompt*).

### 2.4. Pydantic AI Factory (`PydanticAiFactory`)
* **Regra Fundamental:** Toda interação com LLMs no Bombe Code passa obrigatoriamente pelo `pydantic-ai`.
* Modelagem estrita de payloads de entrada e saída (`result_type`).
* Suporte agnóstico a múltiplos provedores (OpenAI, Anthropic, Gemini, Ollama, llama.cpp local).
* Retries automáticos e tratamento tipado de desvios de schema.

### 2.5. Segregação Física de Pastas e Persistência Local
* **Global (`~/.bombe-code/`):** Chaves, provedores configurados, modelos favoritos e preferências do usuário na máquina.
* **Projeto Local (`<project-dir>/.bombe-code/` — no `.gitignore`):**
  - `state.db` (SQLite local assíncrono via `aiosqlite`).
  - Tabela de sessões, checkpoints da máquina de estados e **Kanban Operacional das Tasks dos Agentes**.
  - Logs de execução e telemetria. Raiz do projeto 100% limpa.
* **Produto (`docs/` e `src/` — Versionados no Git):**
  - `docs/briefings/` (PRDs e visão).
  - `docs/architecture/` (ADRs e diagramas).
  - `docs/backlog/` (Épicos e Stories).

### 2.6. TUI Dinâmica com Chaveamento via `Tab`
* A tecla `Tab` alterna visualmente entre as 4 estações: `DISCUSS` → `PLAN` → `EXECUTE` → `VALIDATE`.
* O status bar e o cabeçalho exibem em tempo real o modo ativo, a estação e o estado da ONDA.

---

## 3. Critérios de Sucesso e Aceite da Onda 2
1. O runtime transita deterministamente entre os 4 estados da ONDA.
2. Comandos de intenção rotineira são resolvidos com 0 tokens pelo classificador NLU local.
3. Toda chamada de agente utiliza a fábrica do Pydantic AI.
4. O SQLite local em `.bombe-code/state.db` armazena e recupera o estado e as tasks de agentes sem poluir a raiz.
5. A TUI Textual responde ao `Tab` alternando entre as 4 estações da ONDA.
6. 100% de testes automatizados unitários e de integração cobrindo a nova arquitetura sem mocks fraudulentos.
