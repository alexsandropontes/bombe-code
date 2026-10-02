# PROMPT MESTRE DE FUNDAÇÃO — BOMBE CODE (ONDA 2)

## Contexto & Propósito

Este documento é a especificação fundamental e o **Prompt Mestre de Delegação Arquitetural** do **Bombe Code**. Ele reúne a visão, o modelo mental, os contratos de governança, o desenho de software e as decisões de engenharia que norteiam o projeto.

O Bombe Code **não é** um chatbot convencional, nem um simples wrapper de LLM que atua como operador de perguntas e respostas. O Bombe Code é um **harness de engenharia de software com orquestração determinística, governança e execução orientada a objetivos**, utilizando Modelos de Linguagem (LLMs) como *workers cognitivos especializados*.

---

## 1. Genealogia Técnica e Posicionamento

O Bombe Code nasce de uma linhagem clara e estruturada:

```
                  [ OpenCode Original (Go) ]
                              │
                              ▼
    [ Fase 1: Port para Python (TUI Textual + Server FastAPI + SSE) ]
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
    [ Code-Forge-2 ]                     [ Bombe Code ]
  (Multi-tenant, Nuvem,                (Open Source, Local-First,
   Enterprise Server)                   Lightweight, Máquina Soberana)
```

* **Fase 1 (Concluída com Sucesso):** Port completo do OpenCode original para Python moderno (3.13+), com TUI Textual, servidor FastAPI in-process, adaptadores agnósticos de provedores, barramento SSE de streaming token a token em tempo real e 100% de testes automatizados passando.
* **Fase 2 (Esta Onda — Fundação do Turing Runtime):** Incorporação soberana e determinística do framework de governança (Bombe Core) embutido diretamente no código do runtime, e não como arquivos soltos em disco que LLMs esquecem de ler. Uma versão open source enxuta, mono-usuário e mono-projeto, com inteligência herdada dos padrões de orquestração do `code-forge-2`.

---

## 2. O Problema Resolvido: O Fim do "Chat com Parada Artificial"

Harnesses tradicionais sofrem de um vício crônico: a LLM opera em turnos isolados. Ela gera parte do trabalho, perde o fôlego, interrompe o fluxo e espera que o humano atue como babá digitando comandos artificiais como *"continue"*, *"prossiga"*, *"leia o arquivo X"*.

No **Bombe Code**:
* **O Humano:** Define o objetivo inicial, valida decisões estratégicas de negócio e atua apenas quando explicitamente convocado em bloqueios reais.
* **A LLM:** É a força de trabalho cognitiva especializada que executa sob demanda.
* **O Turing Runtime:** É o maestro determinístico em Python que controla o fluxo, a máquina de estados, os eventos de ciclo de vida e a transição entre fases até a entrega completa da meta.

---

## 3. O Conceito Central: A ONDA

A unidade suprema de trabalho no Bombe Code é a **ONDA**. Uma ONDA representa uma entrega de valor completa e rastreável (ex.: `ONDA-002: Implementação do Turing Runtime Engine e Pydantic AI Factory`).

Uma ONDA é estruturada em dois grandes blocos e quatro etapas fundamentais:

```
┌────────────────────────────────────── ONDA ──────────────────────────────────────┐
│                                                                                  │
│  [ UPSTREAM: Entendimento e Engenharia Antes de Qualquer Código ]                │
│  ├── 1. DISCUSS  ──▶ Entrevista, intenção de negócio, viabilidade, riscos, PRD   │
│  └── 2. PLAN     ──▶ Arquitetura, ADRs, modelo de dados, UX, Épicos e Stories     │
│                                                                                  │
│  [ DOWNSTREAM: Construção Rigorosa e Verificação de Contrato ]                   │
│  ├── 3. EXECUTE  ──▶ Ciclos (CYCLES) de Stories verticais com TDD e Tech Review  │
│  └── 4. VALIDATE ──▶ Auditoria de Contrato: Pedido no Upstream vs. Entregue      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Modos de Autonomia da ONDA
1. **AUTO (Autonomia Máxima):** O humano define a intenção inicial; o Turing conduz `DISCUSS` → `PLAN` → `EXECUTE` → `VALIDATE` de forma contínua, parando apenas se houver uma dúvida de negócio ou risco crítico.
2. **SEMI-AUTO (Aprovação por Fase):** Executa todo o Upstream de forma contínua, pausa para o humano aprovar a entrada em construção, executa o Downstream e pausa na entrega final.
3. **MANUAL (Pausa por Etapa/Cycle):** O usuário controla cada transição ou inspeciona cada Cycle individualmente.

### Modos de Engenharia: Foco Duplo (TDD-Code & Vibe-Code)
O Bombe Code foca exclusivamente em dois modos de desenvolvimento, simplificando o ecossistema:
* **`tdd-code` (Padrão de Engenharia e Missão Crítica):** Rigor pleno — Backend com TDD estrito (**RED → GREEN → REFACTOR**), Frontend com Construction Integrada e Review obrigatório do Tech Lead antes do fechamento de cada Cycle.
* **`vibe-code` (Agilidade & Prototipagem Fluida):** Foco em velocidade de iteração, exploração rápida e menor cerimônia, ideal para descobertas rápidas de produto.
* **Aposentadoria do `spec-code` como Modo de Processo:** A especificação de negócio (Briefings, PRDs, Arquitetura, Épicos) é unificada e comum a ambos os modos (`docs/briefings/` e `docs/backlog/`). A especificação deixa de ser um "modo burocrático apartado" e passa a ser o ativo documental vivo de engenharia do projeto.

---

## 4. Os "Múltiplos Cérebros" do Turing e o Princípio de Economia de Tokens

Turing **não** é uma LLM gigante e gastadora rodando em loop infinito. O runtime adota uma hierarquia de inteligência em camadas:

1. **Cérebro 1: Turing Determinístico (NLU / Regex Local — Custo 0):**
   - Reconhece intenções rotineiras de engenharia (*"status da onda"*, *"iniciar ciclo"*, *"próxima story"*, *"abrir review"*) instantaneamente em Python puro, sem gastar 1 único token.
2. **Cérebro 2: Turing Heurístico (Mini-LM / LLM Classificadora sob Demanda):**
   - Invocado exclusivamente quando uma entrada humana ou evento for semanticamente ambíguo.
3. **Turing Escalation Engine:**
   - Interpreta o resultado das tarefas e decide deterministamente se faz *retry orientado*, se registra erro ou se escala para o humano.

---

## 5. A Governança de Gates e Separação de Papéis

### A. O Papel do Turing Gate ("Cara-Crachá")
Turing é o fiscal de trânsito determinístico:
* **No Upstream:** Verifica no disco se o artefato esperado foi criado no caminho exato, com o nome exato e dentro do template estrutural obrigatório (ex.: seções obrigatórias de um `PRD.md`).
* **No Downstream (Fim do Cycle):** Verifica se a Story contém o **Selo de Aprovação do Tech Lead** gravado.
* **No Validate (Fim da Onda):** Verifica se o relatório de auditoria possui o **Selo de Homologação do Contract Validator**.

### B. O Princípio da Responsabilidade do Consumidor (Qualidade Semântica)
Turing não analisa a semântica fina de um texto. **Quem avalia qualidade é o Agente Consumidor**:
* O Arquiteto só aceita o `PRD.md` se o documento tiver clareza e solidez técnica para sustentar a arquitetura; se for raso, o próprio Arquiteto rejeita e exige retrabalho.
* O Desenvolvedor só inicia a Story se o Definition of Ready (DoR) e os Critérios de Aceite forem inequívocos; se faltar detalhe, ele rejeita a entrada.

### C. O Tech Lead no Código (Downstream)
Turing **não** microgerencia as linhas de código durante o TDD do desenvolvedor. Código exige julgamento contextual:
* O Desenvolvedor cria os testes, implementa o código e refatora.
* O **Tech Lead** faz o Code Review técnico aprofundado: verifica Clean Code, integridade do TDD, ausência de mocks falsos e legibilidade.
* Se aprovado, o Tech Lead assina o **Selo de Aprovação** na Story. Turing lê o selo e libera o próximo Cycle.

---

## 6. TDD Pragmático & MVP Operacional

A disciplina técnica de entrega elimina dogmas acadêmicos e blinda contra fraude de IA:

1. **Regra Fundamental no Backend:** `SEM TESTE RED = SEM CÓDIGO DE PRODUÇÃO`.
   - Nenhuma lógica de negócio, serviço ou endpoint nasce sem teste prévio que falhou legitimamente.
2. **Frontend como Construction Integrada:**
   - Em features fullstack, o slice vertical é obrigatório: a story só está concluída com o componente visual funcional e integrado à API real. Não se exige TDD dogmático em divs/CSS, mas a entrega do front é mandatória.
3. **Flexibilidade para Código Não-Comportamental:**
   - Configurações puramente declarativas, arquivos de infraestrutura e schemas estáticos não exigem testes artificiais inúteis.
4. **Conceito de MVP Operacional:**
   - Substitui o antigo termo "MVP Production Ready" para evitar paralisia por análise.
   - *MVP Operacional:* Versão mínima funcional pronta para ser utilizada por usuários externos reais. Proibido substituir funcionalidades centrais por mocks ou telas falsas. Não é POC.
5. **Aplicação Precisa Subir (Healthcheck Real):**
   - Ao final do Cycle/Onda, o sistema roda o teste de fumaça da aplicação iniciando e respondendo com sucesso.

---

## 7. Segregação Física de Pastas e Persistência Limpa

Fim definitivo da poluição da raiz do projeto. O Bombe Code atua em três esferas rigorosas:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. ESFERA GLOBAL DA MÁQUINA (~/.bombe-code/)                            │
│    • Chaves de API, credenciais e configurações de provedores de LLM   │
│    • Modelos padrão e favoritos do usuário                             │
│    • Preferências visuais da TUI e registro de plugins globais         │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ 2. ESFERA LOCAL DO PROJETO (.bombe-code/ — NO .gitignore)              │
│    • state.db (SQLite local do projeto)                                │
│    • Máquina de estados da ONDA atual                                  │
│    • KANBAN TÉCNICO INTERNO DOS AGENTES (tasks operacionais efêmeras)  │
│    • Logs de telemetria, traces e checkpoints de continuidade          │
│    • ZERO poluição no diretório raiz do projeto!                       │
└────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────┐
│ 3. ESFERA DO PRODUTO (docs/ e src/ — VERSIONÁVEIS NO GIT)               │
│    • docs/briefings/ (PRDs, visão, viabilidade)                        │
│    • docs/architecture/ (ADRs, modelos de dados, diagramas)            │
│    • docs/backlog/ (ÉPICOS e STORIES — O KANBAN DE PRODUTO)            │
│    • src/ e tests/ (Código de produção e suites de testes reais)       │
└────────────────────────────────────────────────────────────────────────┘
```

### O Kanban Duplo
* **Kanban de Produto:** Épicos e Stories em `docs/backlog/` (formato `ai-story`), com DoR e critérios de aceite, commitados no Git da equipe humana.
* **Kanban Operacional de Agentes:** Micro-tarefas técnicas gerenciadas no SQLite local em `.bombe-code/state.db`, exibidas em tempo real na TUI sem poluir o histórico de commits.

---

## 8. Equipe de Personas: 50% Brasileiros / 50% Mundiais

Para homenagear ativamente os pioneiros que construíram a computação mundial, a equipe de personas é composta do zero com 50% de destaques brasileiros e 50% internacionais:

* **Turing (Alan Turing):** O Orquestrador e Maestro do Runtime (não codifica, rege a máquina de estados).
* **Personas Brasileiras (50% da Equipe):**
  - Homenagem a luminares da tecnologia brasileira que impactaram o mundo em linguagens de programação, sistemas concorrentes, compiladores, arquitetura e governança ética (ex.: nomes de referência e pioneiros de sistemas distribuídos e open source nacional).
* **Personas Mundiais (50% da Equipe):**
  - Homenagem a referências globais da engenharia de software em Clean Code, banco de dados, UX e arquitetura.
*(Cada persona conterá disclaimer explícito de homenagem histórica e respeito às suas contribuições).*

---

## 9. Skills sob Demanda & Tools Especializadas

* **Carregamento Progressivo (On-Demand):** Agentes **não** carregam megabytes de skills dentro do system prompt. Eles têm consciência de que o ecossistema possui skills e utilizam tools nativas (`search_skills`, `load_skill`) para carregar instruções especializadas apenas quando a tarefa exigir.
* **Avaliação Técnica de Ferramentas de Documentação:**
  - Ponto de design a ser calibrado pelos arquitetos técnicos: disponibilizar tools de negócio dedicadas (`save_doc`, `read_doc`) com caminhos determinísticos gerenciados pelo Turing, avaliando o trade-off entre rigor de path e consumo de tokens.

---

## 10. Pydantic AI Factory como Padrão Obrigatório de Toda LLM

No Bombe Code, **nenhuma chamada a LLM é feita de forma crua ou desgovernada**.
* **Obrigatoriedade:** Toda interação com LLM deve passar obrigatoriamente pelo **Pydantic AI** (`pydantic-ai`).
* **`PydanticAiFactory`:** Camada central de injeção de dependências e agentes que garante:
  - Saídas tipadas e validadas por schemas Pydantic (`result_type=...`).
  - Retries automáticos e orientados quando o modelo cometer desvio de formato.
  - Abstração completa entre modelos locais (llama.cpp/Ollama) e provedores remotos (OpenAI, Anthropic, Gemini, Groq).

---

## 11. A TUI Dinâmica: Ciclo do `Tab` nas 4 Estações da ONDA

A tecla `Tab` na interface de terminal alterna nativamente entre as 4 Estações da ONDA:

```
[Tab] ──▶  (1) DISCUSS  ──▶  (2) PLAN  ──▶  (3) EXECUTE  ──▶  (4) VALIDATE ──▶ (reinicia ciclo)
```

* O status bar e o cabeçalho da TUI refletem visualmente a estação ativa.
* Em modo `AUTO`, o Turing Runtime atualiza o seletor automaticamente à medida que os gates são aprovados.
* Em modo `MANUAL`, o usuário navega livremente com o `Tab` para interagir com os especialistas de cada fase.

---

## 12. Próximos Passos Executivos

Com a visão e os contratos deste documento aprovados, o ciclo de desenvolvimento da **ONDA 2** seguirá rigorosamente os passos:

1. **`*bc tdd start`:** Inicialização formal da ONDA-002 no motor.
2. **`*bc tdd discuss`:** Consolidação dos requisitos técnicos e especificações do Turing Runtime, SQLite State DB e Pydantic AI Factory.
3. **Plano de Implementação:** Definição das Stories e dos primeiros testes do novo runtime.
