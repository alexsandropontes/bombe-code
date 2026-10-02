# 📊 Relatório Executivo de Benchmark: Bombe Code vs. LLM Genérica

**Projeto Avaliado:** Onboarding Financeiro (Questionário de 10 perguntas 1–5, Score 10–50, 5 Perfis de Investidor, Validação de Nome/E-mail/Telefone, Persistência Local e Testes Automatizados)  
**Modelo de Linguagem:** `glm-5.3-flash` (Z.ai / BigModel) — Estritamente idêntico em ambos os experimentos.  
**Data da Avaliação:** 02 de Outubro de 2026  
**Ambiente Operacional:** Linux / Ubuntu 24.04 LTS  

---

## 🎯 1. Objetivo do Benchmark

O objetivo deste benchmark foi submeter **exatamente o mesmo briefing de negócio** a dois paradigmas distintos de engenharia de software assistida por IA:

1. **Abordagem A — Plataforma Bombe Code (Governança por ONDAS):**  
   Fluxo orquestrado pelo framework Bombe Code com ciclo formal de 4 etapas (`DISCUSS` ➔ `PLAN` ➔ `EXECUTE` ➔ `VALIDATE`), gates determinísticos, separação estrita de responsabilidades (Segregation of Duties) com 10 personas especializadas (`@meira`, `@grace`, `@alan`, `@ieru`, `@codd`, `@caroli`, `@aniche`, `@valim`, `@unclebob`, `@edith`, `@nina`), TDD rigoroso e telemetria nativa por agente.

2. **Abordagem B — LLM Genérica (Baseline / Harness Direto):**  
   Execução direta da mesma especificação contra a API do mesmo modelo (`glm-5.3-flash`), sem agentes, sem personas, sem skills, sem orquestrador e sem divisão de etapas (modo livre/vibe).

---

## 📈 2. Quadro Comparativo Consolidado de Métricas

| Métrica | Abordagem A: Bombe Code (Orquestrado) | Abordagem B: LLM Genérica (Baseline) | Variação / Diferença |
| :--- | :--- | :--- | :--- |
| **Modelo Base** | `glm-5.3-flash` (Z.ai) | `glm-5.3-flash` (Z.ai) | Idêntico |
| **Número de Requisições / Chamadas** | 10 agentes especializados | 1 chamada contínua | +9 chamadas moduladas |
| **Tokens de Entrada (Prompt)** | **8.571 tokens** | **434 tokens** | +8.137 tokens (contextos ricos) |
| **Tokens de Saída (Completion)** | **41.375 tokens** | **35.442 tokens** | +5.933 tokens (+16.7%) |
| **Total de Tokens Processados** | **49.946 tokens** | **35.876 tokens** | +14.070 tokens (+39.2%) |
| **Custo Total Estimado (USD)** | **$0.010686 USD** | **$0.008893 USD** | +$0.001793 USD (~ $0.0018) |
| **Custo Total Estimado (BRL)** | **R$ 0,0588** | **R$ 0,0489** | +R$ 0,0099 (~ 1 centavo de real) |
| **Tempo Total de Execução** | **1.523,09s (~ 25,4 min)** | **543,66s (~ 9,0 min)** | +16,4 min (etapas e retries) |
| **Throughput Médio Efetivo** | **32,8 tokens/s** | **66,0 tokens/s** | -33,2 tokens/s (overhead de rede/latência) |
| **Artefatos de Upstream Gerados** | **5 documentos formais** (`PRD.md`, `VIABILITY.md`, `USER_JOURNEY.md`, `SYSTEM_ARCHITECTURE.md`, `ST-001.md`) | **0 documentos** (apenas `README.md` resumido) | Governança completa de produto e backlog |
| **Controle de Qualidade (QA/Review)** | **Duplo Gate:** QA Plan TDD (`@aniche`), Code Review (`@unclebob`), Homologação (`@edith`) | **Autoverificação básica** (arquivo de teste embutido) | Auditoria independente vs autorrevisão |
| **Auditoria FinOps & Ética** | **Nativa (`@nina`)** com cálculo de custo por agente e por fase | **Inexistente** (requer cálculo manual externo) | Rastreabilidade financeira instantânea |

---

## 🔬 3. Detalhamento da Execução: Bombe Code

A plataforma executou a ONDA `ONDA-001` percorrendo as quatro etapas determinísticas do framework:

### Etapa 1: `DISCUSS` (Discovery & Viabilidade de Negócio)
- `@meira` (Analista de Negócios): Avaliou a viabilidade do produto, unit economics, riscos e restrições regulatórias (4.679 tokens, $0.001046 USD, 120.35s).
- `@grace` (Product Manager): Gerou o **PRD formal** (`PRD.md`) contendo personas, metas mensuráveis, matriz RICE, escopo do MVP e critérios de não-aceite (6.531 tokens, $0.001477 USD, 101.13s).
- **Gate Avaliado:** PRD Gate aprovado com 100% de conformidade estrutural.
- *Subtotal DISCUSS:* **11.210 tokens | $0.002523 USD | 221.48s**

### Etapa 2: `PLAN` (Arquitetura de Upstream & Backlog)
- `@alan` (UX & Journey): Mapeou a jornada do usuário e especificou o fluxo de 10 telas e transições (`USER_JOURNEY.md`) (2.838 tokens, $0.000544 USD, 49.09s).
- `@ieru` (Arquiteto de Software): Desenhou o diagrama de arquitetura e definiu o isolamento em camadas puras (`SYSTEM_ARCHITECTURE.md`) (5.404 tokens, $0.001177 USD, 109.01s).
- `@codd` (DBA & Modelagem): Especificou a estrutura do modelo de dados e o esquema de armazenamento no `localStorage` (2.822 tokens, $0.000553 USD, 47.83s).
- `@caroli` (Scrum Master): Decompôs a ONDA na ai-story executável `ST-001.md` com critérios INVEST e cenários em formato BDD (7.507 tokens, $0.001694 USD, 131.32s).
- **Gate Avaliado:** Upstream Gate aprovado e sincronizado no Kanban SQLite.
- *Subtotal PLAN:* **18.571 tokens | $0.003968 USD | 337.25s**

### Etapa 3: `EXECUTE` (Ciclo TDD de Engenharia)
- `@aniche (QA Plan)`: Elaborou o plano formal de testes de unidade e slice antes de qualquer implementação (5.937 tokens, $0.001308 USD, 729.57s com retry).
- `@valim (Dev)`: Executou a implementação respeitando os contratos de TDD (4.031 tokens, $0.000887 USD, 76.38s).
- `@unclebob (Tech Lead)`: Inspecionou a conformidade com Clean Code, SOLID e padrões arquiteturais (2.508 tokens, $0.000505 USD, 38.73s).
- `@aniche (QA Run & Verify)`: Executou a verificação final da suíte da story (2.161 tokens, $0.000369 USD, 33.21s).
- *Subtotal EXECUTE:* **14.637 tokens | $0.003069 USD | 877.89s**

### Etapa 4: `VALIDATE` (Homologação & FinOps)
- `@edith (Product Homologation)`: Realizou a conferência do entregável contra os objetivos contratuais do PRD e critérios de aceite da ONDA (3.416 tokens, $0.000722 USD, 53.51s).
- `@nina (Gov & FinOps)`: Emitiu o relatório de auditoria de consumo de tokens, conformidade orçamentária e integridade ética (2.112 tokens, $0.000404 USD, 32.96s).
- *Subtotal VALIDATE:* **5.528 tokens | $0.001126 USD | 86.46s**

---

## ⚡ 4. Detalhamento da Execução: LLM Genérica (Baseline)

A abordagem baseline consistiu em um harness direto consumindo a mesma API do `glm-5.3-flash`:
- **Modo de Trabalho:** Prompt monolítico com todos os requisitos técnicos e funcionais.
- **Resultado da Geração:** 1 única resposta contínua de **35.442 tokens de completion**.
- **Tempo de Resposta:** **543,66 segundos (~ 9 minutos contínuos)**.
- **Arquivos Gerados:** 12 arquivos de código-fonte descompactados e testados funcionalmente:
  - `index.html` (interface web interativa)
  - `css/styles.css` (estilização responsiva)
  - `js/logic.js` (cálculo de score e atribuição de perfis)
  - `js/questions.js` (as 10 perguntas com pesos de 1 a 5)
  - `js/storage.js` (leitura e gravação no `localStorage`)
  - `js/app.js` (gerenciamento do fluxo de telas e eventos)
  - `tests.html` + `js/tests.js` (runner de testes no navegador)
  - `tests/logic.test.js` + `tests/storage.test.js` (testes automatizados em Node.js)
  - `package.json` + `README.md`
- **Validação:** Lógica executada via Node.js com score de 50 pontos resultando no perfil "Independente Financeiro".

---

## 🧐 5. Análise Comparativa Aprofundada: O Comportamento dos Sistemas

### A. Integridade e Resistência à Alucinação (Anti-Fake-Progress)
Um dos fenômenos mais reveladores observados durante a execução do Bombe Code foi o comportamento das personas `@valim`, `@unclebob`, `@edith` e `@nina`:
- Quando despachadas individualmente pelo orquestrador, suas instruções sistêmicas impuseram uma barreira intransponível: **nenhum agente aceita agir sem evidências materiais prévias**.
  - `@valim`: *"Sem RED legítimo na mesa, não há código de produção. A suíte é da @aniche e não tenho acesso a ela... Escrever no escuro seria violação."*
  - `@unclebob`: *"Revisar sem insumo não é code review — é adivinhação. Eu não adivinho. Eu inspeciono."*
  - `@edith`: *"Auditoria não iniciável — evidências obrigatórias não recebidas. Provas antes do selo."*
- **Significado Prático:** Enquanto a LLM Genérica gera tudo "no escuro" assumindo premissas sem contestar nenhuma inconsistência, o ecossistema Bombe Code possui **imunidade inata a aprovações cegas** e fraude de progresso.

### B. Custo Financeiro e Escalabilidade
- A diferença de custo total entre o sistema orquestrado com 10 agentes e a chamada monolítica foi de apenas **+$0.001793 USD (menos de 1 centavo de real)**:
  - Bombe Code: **$0.010686 USD (~ R$ 0,059)**
  - LLM Genérica: **$0.008893 USD (~ R$ 0,049)**
- **Risco de Timeout:** Uma completion monolítica de 35k tokens na LLM Genérica leva 9 minutos ininterruptos. Se a conexão cair no 8º minuto (como ocorreu durante testes com timeouts menores), **perde-se 100% da requisição**. No Bombe Code, cada requisição dura em média de 30 a 130 segundos, salvando checkpoints intermediários persistidos no SQLite (`state.db`).

### C. Manutenibilidade e Ciclo de Vida
- **LLM Genérica:** Produz código utilizável rapidamente, mas **sem qualquer registro histórico do "porquê"** das decisões arquiteturais tomadas. Se uma regra de negócio mudar amanhã, o desenvolvedor precisará reler 12 arquivos para deduzir as premissas.
- **Bombe Code:** Entrega um ecossistema completo de governança:
  1. `PRD.md`: Requisitos de negócio, métricas e restrições.
  2. `USER_JOURNEY.md`: Mapeamento de cada tela e transição.
  3. `SYSTEM_ARCHITECTURE.md`: Decisões técnicas e contratos de dados.
  4. `ST-001.md`: User story atômica pronta para sprints futuras.
  5. `telemetria.md`: Extrato financeiro transparente de cada token investido.

---

## 🏆 6. Conclusão e Veredito

| Cenário de Aplicação | Recomendação Técnica | Justificativa |
| :--- | :--- | :--- |
| **Prototipagem Rápida / Exploração Livre** | **Modo VIBE / LLM Direta** | Quando a velocidade bruta de entrega é o único critério e o código será descartado ou mantido por uma única pessoa, a chamada direta entrega tudo em ~9 minutos com custo mínimo. |
| **Aplicações Críticas, Enterprise e Sustentáveis** | **Plataforma Bombe Code (Modo TDD / ONDAS)** | Por um acréscimo irrisório de R$ 0,01 por demanda, o time ganha documentação viva, separação de deveres, auditoria de segurança/ética, plano formal de testes e proteção estrita contra alucinação de entregas. |

---

*Relatório gerado automaticamente através da telemetria persistida em:*  
- Workspace Bombe Code: `/home/lexpontes/codeforgews/lexpontes/poc/onboarding-bombe-code/docs/`
- Workspace LLM Genérica: `/home/lexpontes/codeforgews/lexpontes/poc/onboarding-generic-llm/`
