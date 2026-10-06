# 📖 Manual do Usuário — Bombe Code

Bem-vindo ao **Bombe Code**, o ambiente autônomo de engenharia de software com **Governança Determinística pelo Turing Runtime**, suporte híbrido a **TDD Formal** e **Vibe Coding**, e orquestração de **24 Agentes Especialistas**.

---

## 🎯 Sumário
1. [Visão Geral & Filosofia](#-visão-geral--filosofia)
2. [Os Dois Grandes Modos: TDD vs VIBE](#-os-dois-grandes-modos-tdd-vs-vibe)
   - [Modo TDD (`tdd-code` — Engenharia Formal & Governada)](#-modo-tdd-tdd-code--engenharia-formal--governada)
   - [Modo VIBE (`vibe-code` — Vibe Coding Livre & Ágil)](#-modo-vibe-vibe-code--vibe-coding-livre--ágil)
3. [Chave Mestra: Atalho Shift + Tab](#-chave-mestra-atalho-shift--tab)
4. [Ontologia das Ondas & Comportamento Contextual da Tecla Tab](#-ontologia-das-ondas--comportamento-contextual-da-tecla-tab)
   - [Onda 0: Greenfield Lean Inception Macro (`DISCOVERY` ➔ `INCEPTION`)](#onda-0-greenfield-lean-inception-macro)
   - [Ondas de Entrega 1..N e Brownfield (`PLAN` ➔ `REFINEMENT` ➔ `EXECUTE` ➔ `VALIDATE`)](#ondas-de-entrega-1n-e-brownfield)
   - [Tabela de Permissões e Travas Determinísticas (`StageGuard`)](#tabela-de-permissões-e-travas-determinísticas)
5. [Orquestração de ONDAS & Comandos /wave](#-orquestração-de-ondas--comandos-wave)
   - [Iniciar uma Nova ONDA (`/wave start`)](#iniciar-uma-nova-onda-wave-start)
   - [Alerta de Ondas Incompletas & Proteção `--force`](#alerta-de-ondas-incompletas--proteção---force)
   - [Execução Passo a Passo vs Modo Automático](#execução-passo-a-passo-vs-modo-automático)
6. [Elenco Oficial de 24 Agentes Especialistas](#-elenco-oficial-de-23-agentes-especialistas)
7. [Atalhos de Teclado na TUI](#-atalhos-de-teclado-na-tui)
8. [Caixa de Entrada Multilinha & Colagem Segura (Paste Support)](#-caixa-de-entrada-multilinha--colagem-segura-paste-support)
9. [Streaming em Tempo Real & Raciocínio ao Vivo](#-streaming-em-tempo-real--raciocínio-ao-vivo)
10. [Catálogo de Comandos de Barra (/)](#-catálogo-de-comandos-de-barra-)

---

## 🌟 Visão Geral & Filosofia

O Bombe Code opera como uma esteira de engenharia completa e local-first dentro do diretório do seu projeto. Ele une o melhor de dois mundos:
* **Rigor Arquitetural (TDD):** Garantia de qualidade, testes escritos antes do código pelo QA (`@aniche`), revisão técnica independente por Tech Lead (`@unclebob`), homologação por `@edith` e fiscalização determinística por quality gates em código Python imperativo.
* **Agilidade Criativa (VIBE):** Liberdade total para prototipagem rápida, experimentação e alterações diretas sem cerimônias formais.

Toda a persistência física das especificações é mantida em arquivos Markdown versionáveis no Git (`docs/briefings/`, `docs/architecture/`, `docs/backlog/`, `docs/reports/`) e o estado operacional fica salvo no banco SQLite local (`.bombe-code/state.db` ou `state.db`).

---

## 🧭 Os Dois Grandes Modos: TDD vs VIBE

O Bombe Code organiza sua experiência em dois modos autônomos de engenharia:

```
                  ┌────────────────────────────────────────┐
                  │          Chave Mestra: Shift + Tab     │
                  └───────────────────┬────────────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
    🛡️ MODO TDD (`tdd-code`)                      🔥 MODO VIBE (`vibe-code`)
 ┌───────────────────────────────┐              ┌───────────────────────────────┐
 │ • Governança formal da ONDA   │              │ • Modo livre e irrestrito     │
 │ • Travas rígidas por etapa    │              │ • Sem etapas ou travas        │
 │ • Tab cicla etapas contextuais│              │ • Tab NÃO cicla etapas        │
 │ • Ciclo TDD: RED ➔ GREEN ➔    │              │ • Badge em VERMELHO VIVO      │
 │   REFACTOR ➔ REVIEW GATE      │              │ • Foco em agilidade imediata  │
 └───────────────────────────────┘              └───────────────────────────────┘
```

---

### 🛡️ Modo TDD (`tdd-code` — Engenharia Formal & Governada)

* **O que é:** O modo de entrega profissional da ONDA. Toda alteração de código passa pela governança arquitetural, onde requisitos são clarificados antes de desenhar a solução e testes automatizados são concebidos antes da implementação.
* **Controle:** O desenvolvedor e a LLM estão **presos às diretrizes da etapa ativa**. Se a LLM tentar escrever código de produção na etapa de concepção ou planejamento, as ferramentas de escrita em `src/` são bloqueadas deterministicamente com mensagens de veto instrutivas (`StageGuard`).
* **Navegação Contextual:** A tecla **`Tab`** avança ciclicamente pelas etapas autorizadas para o tipo de onda ativa.

---

### 🔥 Modo VIBE (`vibe-code` — Vibe Coding Livre & Ágil)

* **O que é:** O modo de liberdade criativa total. Aqui o desenvolvedor pode fazer vibe coding à vontade, solicitando qualquer funcionalidade, refatoração, arquivo avulso, protótipo ou script direto sem cerimônias formais.
* **Sem Sub-etapas:** Não há divisões ou travas por etapa. A LLM executa prontamente o que você pedir.
* **Comportamento do `Tab`:** No modo VIBE, pressionar **`Tab` NÃO cicla etapas** (ele é reservado exclusivamente para autocompletar `/comandos` ou `@arquivos`).
* **Sinalização em VERMELHO VIVO:** A barra de status exibe o indicador em vermelho vivo:  
  `Modo: [VIBE]` (destaque visual marcante).
* **Permanência:** Uma vez no modo VIBE, você só sai de lá pressionando `Shift + Tab` novamente (ou digitando `/mode tdd`).

---

## ⚡ Chave Mestra: Atalho Shift + Tab

A qualquer momento durante o desenvolvimento na TUI:

* **Pressione `Shift + Tab`:** Comuta instantaneamente entre o **Modo TDD** e o **Modo VIBE**.
* **Retorno Inteligente:** Ao retornar para o Modo TDD, o sistema restaura com segurança exatamente a etapa onde você parou.
* Funciona mesmo com o foco ativo no campo de digitação de texto.

---

## 🌊 Ontologia das Ondas & Comportamento Contextual da Tecla Tab

O ciclo de vida no Bombe Code diferencia deterministicamente o início de novos projetos das ondas de desenvolvimento contínuo:

### Onda 0: Greenfield Lean Inception Macro
* **Identificadores:** `ONDA-000`, `ONDA-0`, `WAVE-000`.
* **Natureza:** Estritamente **UPSTREAM**. Não implementa código em `src/`.
* **Etapas:** `DISCOVERY` ➔ `INCEPTION` ➔ `COMPLETED`.
* **Ação do `Tab` na Onda 0:** Alterna ciclicamente entre:
  `DISCOVERY` ➔ `INCEPTION` ➔ `DISCOVERY`...
* **Trava:** O avanço para `EXECUTE` ou `VALIDATE` é **terminantemente PROIBIDO** na Onda 0 e gera erro determinístico (`InvalidTransitionError`).

### Ondas de Entrega 1..N e Brownfield
* **Identificadores:** `ONDA-001`, `ONDA-002`, `WAVE-001` em diante, ou evolução de bases legadas.
* **Natureza:** Fatias verticais executáveis com entrega de software pronto para produção.
* **Etapas:** `PLAN` ➔ `REFINEMENT` ➔ `EXECUTE` ➔ `VALIDATE` ➔ `COMPLETED`.
* **Ação do `Tab` nas Ondas de Entrega:** Alterna ciclicamente entre:
  `PLAN` ➔ `REFINEMENT` ➔ `EXECUTE` ➔ `VALIDATE` ➔ `PLAN`...

---

### Tabela de Permissões e Travas Determinísticas (`StageGuard`)

| Etapa | Foco & Responsabilidades | Permissões de Ferramentas | Travas Determinísticas |
|---|---|---|---|
| **DISCOVERY** / **DISCUSS** | Viabilidade, mercado e PRD com `@meira` e `@grace`. | Leitura liberada. Escrita em `docs/briefings/`. | ⛔ **Bloqueada** escrita em `src/`, `lib/`, `tests/`. |
| **INCEPTION** | Lean Inception Macro, Canvas MVP e Sequenciador com `@caroli`, `@alan`, `@norman`, `@ieru`, `@codd`, `@claudia`, `@barreto`. | Leitura liberada. Escrita em `docs/architecture/` e `docs/briefings/`. | ⛔ **Bloqueada** escrita de código de produção em `src/`. |
| **PLAN** | Planejamento técnico da fatia da onda: ADRs e contratos com `@ieru`, `@alan`, `@codd`/`@claudia`. | Leitura liberada. Escrita em `docs/architecture/`. | ⛔ **Bloqueada** escrita de código de produção em `src/`. |
| **REFINEMENT** | Refinamento PBB: decomposição em `ai-stories` atômicas e DoR (INVEST) com `@caroli`. | Leitura liberada. Escrita em `docs/backlog/stories/`. | ⛔ **Bloqueada** escrita de código de produção em `src/`. |
| **EXECUTE** | Ciclo TDD: `@aniche` (RED) ➔ Devs (GREEN) ➔ `@unclebob` (REFACTOR & REVIEW). | Escrita e leitura **100% liberadas** em `src/`, `tests/` e `docs/`. | Segue o ciclo TDD: sem teste falhante, dev não commita. |
| **VALIDATE** | Homologação final do entregável contra o PRD com `@edith` e auditoria FinOps/ética com `@nina`. | Escrita de relatórios em `docs/reports/` e execução de testes. | ⛔ **Bloqueada** criação de novos módulos em `src/` (anti-scope creep). |

> **Dica:** A alternância de etapas via `Tab` persiste automaticamente o estado no banco SQLite local (`state.db`) e sincroniza com a sessão ativa.

---

## 🌊 Orquestração de ONDAS & Comandos /wave

Além da navegação passo a passo via `Tab`, você pode comandar a esteira via comandos de barra (`/wave`):

### Iniciar uma Nova ONDA (`/wave start`)

```bash
/wave start [ONDA-ID] [auto|semi_auto] [--force]
```

**Exemplos:**
* `/wave start ONDA-000` — Inicia a Onda 0 (Greenfield Lean Inception Macro).
* `/wave start ONDA-001 auto` — Inicia a Onda de Entrega 1 com autonomia total.
* `/wave start ONDA-001 semi` — Inicia a Onda 1 no modo semi-automático (pausa entre stories para confirmação).

---

### Alerta de Ondas Incompletas & Proteção `--force`

Se você tentar iniciar uma nova ONDA enquanto a onda atual **ainda possuir pendências ativas** (estágio diferente de `COMPLETED`), o Bombe Code emitirá um alerta amigável de segurança:

> `⚠️ A ONDA-001 ainda está em andamento (etapa: EXECUTE) e possui pendências ativas. Finalize-a com '/wave end' ou use '--force' ('/wave start ONDA-002 --force') para sobrescrever e iniciar uma nova onda.`

Isso protege você de perder o contexto de uma entrega em andamento por acidente.

---

### Execução Passo a Passo vs Modo Automático

Você tem dois jeitos elegantes de trabalhar:
1. **Passo a Passo Manual (via `Tab`):** Você navega em cada etapa no seu próprio ritmo, interage com a LLM sobre cada detalhe e pressiona `Tab` quando estiver satisfeito para avançar.
2. **Esteira Orquestrada (via `/wave start auto` ou CLI):** O orquestrador aciona os especialistas em sequência, valida os quality gates (PRD Gate, Journey Gate, Architecture Gate, Database Gate, Story DoR Gate, Review Gate e Seal Gate) e entrega a ONDA de ponta a ponta.

---

## 👥 Elenco Oficial de 24 Agentes Especialistas

O Bombe Code conta com 24 agentes especialistas de elite (12 brasileiros e 11 internacionais) que podem ser chamados com `@nome`:

### Upstream (Concepção, Inception, Arquitetura & Refinamento)
* **`@meira`** (Silvio Meira — Brasil): Senior Research & Viability Analyst. Análise de viabilidade técnica, mercado e inovação.
* **`@grace`** (Grace Hopper — EUA): Lead Product Manager. Visão de produto, priorização RICE e elaboração do PRD em `docs/briefings/PRD.md`.
* **`@alan`** (Alan Cooper — EUA): User Journey Architect. Mapeamento de entry points, navegação e inventário de telas em `docs/architecture/journey.md`.
* **`@norman`** (Don Norman — EUA): UI/UX Designer & Design Systems. Heurísticas de Nielsen, wireframes e design tokens em `docs/architecture/ui-ux.md`.
* **`@ieru`** (Roberto Ierusalimschy — Brasil): Principal Systems Architect. Arquitetura limpa, monolitos modulares, microsserviços e ADRs em `docs/architecture/arch.md`.
* **`@codd`** (Edgar F. Codd — UK): Relational Database Architect. Modelagem relacional, normalização, migrações e índices SQL em `docs/architecture/db.md`.
* **`@claudia`** (Claudia Bauzer Medeiros — Brasil): NoSQL & Vector Store Architect. Bancos NoSQL, grafos e índices para IA vetorial em `docs/architecture/db-nosql.md`.
* **`@barreto`** (Paulo Barreto — Brasil): Principal Security Architect. Modelagem de ameaças STRIDE e criptografia em `docs/security/threat-model.md`.
* **`@caroli`** (Paulo Caroli — Brasil): Agile Master & Flow Architect. Lean Inception Macro, Canvas MVP, Sequenciador e Decomposição PBB de `ai-stories` em `docs/backlog/`.
* **`@nelson`** (Nelson Mattos — Brasil): Prompt Engineer & AI Context Specialist. Engenharia de contexto, system prompts e alinhamento de IA.

### Downstream (Construção TDD & Qualidade de Código)
* **`@valim`** (José Valim — Brasil): Senior Elixir Backend Developer. Concorrência funcional, OTP, alta escala e BEAM.
* **`@barbara`** (Barbara Liskov — EUA): Senior Python & Go Backend Developer. APIs FastAPI, Pydantic v2, concorrência Go e microsserviços.
* **`@scott`** (Scott Guthrie — EUA): Senior .NET Backend Developer. ASP.NET Core 8+, C# 12, Minimal APIs e Entity Framework Core.
* **`@ryan`** (Ryan Dahl — EUA): Senior Node.js & TS Backend Developer. Runtime Node/TS, TypeScript Strict, APIs REST e Express/Fastify.
* **`@james`** (James Gosling — Canadá): Senior Java Backend Developer. Java 21, Spring Boot 3+, Virtual Threads e Clean Architecture.
* **`@ada`** (Ada Lovelace — UK): Senior Frontend Developer. React 19, Tailwind CSS, Flutter, design responsivo e acessibilidade.
* **`@diego`** (Diego Aranha — Brasil): AppSec Pentest & Offensive Security Auditor. Auditoria ofensiva, testes SAST/DAST e mitigação OWASP Top 10.
* **`@aniche`** (Maurício Aniche — Brasil): Test Architect & QA Automation. Estratégia de testes, escrita de testes falhantes (`RED`) e automação completa.
* **`@unclebob`** (Robert C. Martin — EUA): Tech Lead & Architectural Guardian. Clean Code, princípios SOLID, refatoração e Code Review de aprovação.
* **`@demi`** (Demi Getschko — Brasil): SRE & Infrastructure Engineer. Redes, containers Docker, pipelines CI/CD e observabilidade local.

### Downstream (Validação, Homologação & Maestro)
* **`@edith`** (Edith Ranzini — Brasil): Contract & Deliverable Validator. Auditoria final do entregável contra o PRD e emissão do Selo de Entrega em `docs/reports/`.
* **`@nina`** (Nina Silva — Brasil): Gov, FinOps & AI Ethics Auditor. Auditoria de consumo de tokens, governança de custos e conformidade ética e LGPD.
* **`@turing`** (Alan Turing — UK): Runtime Maestro & Orquestrador. Orquestração da ONDA, máquina de estados finita e guarda de quality gates.

---

## ⌨️ Atalhos de Teclado na TUI

| Tecla de Atalho | Ação Executada |
|---|---|
| **`Enter`** | **Envia a mensagem ou prompt digitado** |
| **`Shift + Enter`** | **Insere uma quebra de linha (modo multilinha)** |
| **`Shift + Tab`** | **Comuta entre Modo TDD e Modo VIBE (Chave Mestra)** |
| **`Tab`** | **Alterna ciclicamente as etapas do Modo TDD** (contextual por tipo de onda) |
| **`Tab` (em `/` ou `@`)** | Autocompleta comandos de barra ou arquivos do projeto |
| **`Ctrl + P`** | Abre a Paleta de Comandos unificada |
| **`Ctrl + B`** | Alterna a exibição do Painel Lateral (Sidebar) com métricas de contexto |
| **`Ctrl + C`** / **`Esc`** | Interrompe o turno ativo da LLM |
| **`Ctrl + Q`** | Fecha a TUI com segurança imediata (sem travamentos) |
| **`Up` / `Down`** | Navega no histórico de prompts enviados |

---

## 📝 Caixa de Entrada Multilinha & Colagem Segura (Paste Support)

O campo de prompt do Bombe Code é uma área de texto multilinha com auto-grow dinâmico (3 a 8 linhas):
* **Colagem Completa de Textos:** Cole especificações extensas, snippets de código ou instruções vindas do ChatGPT, Claude ou da web sem perder quebras de linha e sem corte na primeira linha.
* **Envio Imediato:** Pressione `Enter` para despachar o prompt.
* **Quebras de Linha Manuais:** Use `Shift + Enter` para quebrar linhas e formatar seu texto antes do envio.

---

## ⚡ Streaming em Tempo Real & Raciocínio ao Vivo

A experiência de resposta na TUI opera com paridade visual e reatividade imediata:
* **Token-a-Token Imediato:** Os tokens fluem progressivamente via Server-Sent Events (SSE). As palavras surgem à medida que são geradas pela LLM.
* **Pensamento ao Vivo (`reasoning-delta`):** Em modelos com raciocínio analítico integrado (como o Z.ai **GLM-5.3-Flash**, DeepSeek R1 ou Claude 3.7 Sonnet), o raciocínio é exibido em tempo real em um painel discreto (`⚡ Pensamento / Raciocínio`), permitindo acompanhar a linha de raciocínio da IA antes da resposta final ser montada.
* **Arquitetura Anti-Freezing:** A renderização utiliza throttling inteligente a ~35ms, garantindo fluidez contínua sem consumir 100% de CPU. A TUI nunca trava e você pode rolar a tela ou sair com `Ctrl + Q` a qualquer instante.
* **Feedback Visual Animado:** Durante a conexão com a nuvem, uma ampulheta animada (`⏳` ➔ `⌛`) e pontinhos de status sinalizam atividade enquanto a resposta é preparada.

---

## 🛠️ Catálogo de Comandos de Barra (/)

Digite `/` no campo de prompt para ter sugestões instantâneas:

* `/connect` — Abre o assistente para conectar provedores de IA (Z.ai GLM-5.3-Flash, OpenAI, Anthropic, Ollama, etc.) e registrar chaves.
* `/wave status` — Visualiza o status da ONDA ativa, resumo de stories e gates do Turing.
* `/wave start [id] [auto|semi]` — Inicializa uma nova ONDA formal (ex: `/wave start ONDA-000` ou `/wave start ONDA-001`).
* `/wave discuss [tema]` — Executa a etapa DISCUSS com `@meira` e `@grace`.
* `/wave plan` — Executa a etapa PLAN com os arquitetos de upstream.
* `/wave cycle [story_id]` — Executa o ciclo atômico de uma story específica com QA (`@aniche`), Dev e Tech Lead (`@unclebob`).
* `/wave end` — Finaliza formalmente a ONDA atual.
* `/agent [nome]` — Alterna o agente de atendimento (ex: `/agent @aniche`, `/agent @unclebob`).
* `/models [nome]` — Lista ou troca o modelo de LLM ativo (ex: Z.ai, OpenAI, Claude).
* `/compact` — Compacta o histórico da sessão para economizar contexto.
* `/undo` — Reverte o último turno e alterações de arquivo via git.
* `/rca <incidente>` — Executa Análise de Causa Raiz determinística com `@unclebob`.
* `/simplify <alvo>` — Conduz auditoria de simplificação de código com `@ieru` e `@unclebob`.
* `/verbosity [verbose|quiet]` — Alterna a verbosidade do runtime: `verbose` (padrão) streama cada letra, raciocínio e tool call dos agentes ao vivo; `quiet` exibe apenas anúncios de onda, etapas e vetos.
* `/exit` — Sai da aplicação.

### 🤖 Autonomia Total: o que acontece quando algo é vetado

Em modo `AUTO`, nenhum veto interrompe o processo. Quando um validador reprova a ONDA, o Turing determinístico:
1. **Classifica** a causa do veto (formato do parecer, gap de produto, falha de testes ou bloqueio declarado);
2. **Rastreia o autor** do artefato causador (PRD→`@grace`, story→`@caroli`, schema→`@codd`, arquitetura→`@ieru`, testes→`@aniche`);
3. **Devolve o bloqueio** para esse autor corrigir o artefato upstream;
4. **Re-queima as stories afetadas** no ciclo TDD (RED→GREEN→REFACTOR);
5. **Re-auditá** com o validador original — e repete até aprovar (2 rodadas autônomas).

Somente após esgotar o ciclo autônomo você é convocado — com uma **Dúvida de Negócio** estruturada (bloqueios listados + responsável técnico sugerido). Ao validar cada onda, o runtime arquiva e encadeia a próxima automaticamente; na onda final, o produto está pronto para a sua navegação de aceite.

**Dica:** para acompanhar tudo que os agentes pensam e fazem, fique no modo `verbose` (padrão). Para uma execução executiva enxuta, use `bombe-code tui --quiet`.

---

*Bombe Code — Engenharia Determinística, Qualidade Industrial e Vibe Coding sem Atrito.*
