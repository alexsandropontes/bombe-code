# EP-002: Turing Runtime Engine, Pydantic AI Factory & Dynamic TUI

## Status: APROVADO (DoR Atendido)
## Onda: ONDA-002
## Responsável: Turing & Equipe

---

### Descrição do Épico
Implementar o motor de orquestração autônomo **Turing Runtime Engine**, a fábrica unificada de agentes via **Pydantic AI**, a persistência limpa de estado local em `.bombe-code/state.db` com o **Kanban de Tasks de Agentes**, e o suporte a navegação por tecla `Tab` entre as 4 estações da ONDA na TUI.

---

### Stories do Épico

#### ST-001: Turing Intent Classifier (Cérebro Determinístico NLU)
* **Objetivo:** Classificar intenções e comandos de engenharia rotineiros em Python puro com latência < 1ms e custo zero de tokens.
* **Critérios de Aceite:**
  1. Suporta intenções: `wave_status`, `start_discuss`, `start_plan`, `start_cycle`, `review_cycle`, `validate_wave`, `toggle_mode`.
  2. Retorna `needs_llm=True` quando a entrada for ambígua ou desconhecida.
  3. Suporta extração de slots de parâmetros (ex: número da story ou modo).
  4. Cobertura 100% por testes unitários via pytest.

#### ST-002: Turing State Machine da ONDA
* **Objetivo:** Gerenciar as transições entre estações (`DISCUSS`, `PLAN`, `EXECUTE`, `VALIDATE`, `COMPLETED`) e modos de autonomia (`AUTO`, `SEMI_AUTO`, `MANUAL`).
* **Critérios de Aceite:**
  1. Valida pré-condições para avanço de estação.
  2. Suporta modos de engenharia `tdd-code` e `vibe-code`.
  3. Dispara callbacks/eventos tipados a cada transição de estado.
  4. Testes cobrindo avanço, rollback e impedimentos de transição.

#### ST-003: Turing Gates Engine (Cara-Crachá, Selos e Handoff)
* **Objetivo:** Implementar os portões de validação determinística de artefatos e assinaturas de qualidade.
* **Critérios de Aceite:**
  1. `TemplateGate`: Checa existência física do arquivo e tópicos/seções obrigatórias.
  2. `SealGate`: Valida a presença do selo do Tech Lead na Story ou do Validator na Onda.
  3. `ConsumerHandoffGate`: Permite ao agente consumidor rejeitar insumos rasos e gerar rework prompt automático.
  4. Testes automatizados unitários cobrindo aprovação e rejeição com relatório de não-conformidade.

#### ST-004: Storage Local do Projeto (.bombe-code/state.db)
* **Objetivo:** Isolar o banco de dados do projeto e o Kanban operacional das tasks dos agentes em `.bombe-code/state.db` sem poluir a raiz.
* **Critérios de Aceite:**
  1. Cria o diretório `.bombe-code/` se não existir e inicializa o SQLite `state.db`.
  2. Tabela de checkpoints da ONDA e tabela de tasks operacionais de agentes.
  3. Métodos CRUD para tasks de agentes (`create_task`, `update_task_status`, `list_tasks_by_story`).
  4. Testes com banco SQLite em memória e em arquivo local.

#### ST-005: Pydantic AI Factory
* **Objetivo:** Fornecer camada padrão para instanciação e execução de agentes LLM com validação Pydantic estrita.
* **Critérios de Aceite:**
  1. Adiciona `pydantic-ai` ao projeto.
  2. Fábrica `PydanticAiFactory` que retorna agentes tipados.
  3. Suporte a OpenAI, Anthropic, Gemini, Ollama e compatível local (llama-server).
  4. Validação de saída em schemas Pydantic tipados com tratamento de erros.

#### ST-006: TUI Dinâmica (Ciclo do Tab nas 4 Estações)
* **Objetivo:** Habilitar tecla `Tab` para navegar e refletir visualmente as 4 estações da ONDA na interface de terminal.
* **Critérios de Aceite:**
  1. Tecla `Tab` alterna ciclicamente: `DISCUSS` → `PLAN` → `EXECUTE` → `VALIDATE`.
  2. Status bar e Header atualizam com badge colorido indicando a estação ativa.
  3. Sincronização com o estado da ONDA do Turing Runtime.
  4. Testes de TUI simulando disparo de tecla `Tab`.
