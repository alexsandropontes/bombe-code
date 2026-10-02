# 📖 Manual do Usuário — Bombe Code

Bem-vindo ao **Bombe Code**, o ambiente agentic de engenharia de software com **Governança Determinística pelo Turing Runtime** e suporte híbrido a **TDD Formal** e **Vibe Coding**.

---

## 🎯 Sumário
1. [Visão Geral & Filosofia](#-visão-geral--filosofia)
2. [Os Dois Grandes Modos: TDD vs VIBE](#-os-dois-grandes-modos-tdd-vs-vibe)
   - [Modo TDD (Engenharia Formal & Governada)](#-modo-tdd-engenharia-formal--governada)
   - [Modo VIBE (Vibe Coding Livre & Ágil)](#-modo-vibe-vibe-coding-livre--ágil)
3. [Chave Mestra: Atalho Shift + Tab](#-chave-mestra-atalho-shift--tab)
4. [As 4 Etapas Formais da ONDA & Navegação via Tab](#-as-4-etapas-formais-da-onda--navegação-via-tab)
5. [Orquestração de ONDAS & Comandos /wave](#-orquestração-de-ondas--comandos-wave)
   - [Iniciar uma Nova ONDA (`/wave start`)](#iniciar-uma-nova-onda-wave-start)
   - [Alerta de Ondas Incompletas & Proteção `--force`](#alerta-de-ondas-incompletas--proteção---force)
   - [Execução Passo a Passo vs Modo Automático](#execução-passo-a-passo-vs-modo-automático)
6. [Elenco de Agentes Especialistas](#-elenco-de-agentes-especialistas)
7. [Atalhos de Teclado na TUI](#-atalhos-de-teclado-na-tui)
8. [Catálogo de Comandos de Barra (/)](#-catálogo-de-comandos-de-barra-)

---

## 🌟 Visão Geral & Filosofia

O Bombe Code opera como uma esteira de engenharia completa dentro do diretório do seu projeto. Ele une o melhor de dois mundos:
* **Rigor Arquitetural (TDD):** Garantia de qualidade, testes escritos antes do código pelo QA, revisão por Tech Lead e auditoria determinística por gates.
* **Agilidade Criativa (VIBE):** Liberdade total para prototipagem rápida, experimentação e alterações diretas sem cerimônias.

Toda a persistência física das especificações é mantida em pastas versionáveis (`docs/briefings/`, `docs/journeys/`, `docs/architecture/`, `docs/stories/`, `docs/reports/`) e o estado operacional fica no banco SQLite local (`.bombe-code/state.db`).

---

## 🧭 Os Dois Grandes Modos: TDD vs VIBE

O Bombe Code organiza sua experiência em dois modos soberanos:

```
                  ┌────────────────────────────────────────┐
                  │          Chave Mestra: Shift + Tab     │
                  └───────────────────┬────────────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
    🛡️ MODO TDD (Formal)                          🔥 MODO VIBE (Livre)
 ┌───────────────────────────────┐              ┌───────────────────────────────┐
 │ • 4 Etapas: Discuss, Plan,    │              │ • Modo livre e irrestrito     │
 │   Execute, Validate           │              │ • Sem etapas ou travas        │
 │ • Tab cicla entre as 4 etapas │              │ • Tab NÃO cicla etapas        │
 │ • Travas rígidas por etapa    │              │ • Badge em VERMELHO VIVO      │
 │ • Foco em qualidade e gates   │              │ • Agilidade e ordens diretas  │
 └───────────────────────────────┘              └───────────────────────────────┘
```

---

### 🛡️ Modo TDD (Engenharia Formal & Governada)

* **O que é:** O modo de entrega profissional da ONDA. Toda alteração de código passa pela governança arquitetural, onde requisitos são clarificados antes de desenhar a solução e testes são concebidos antes da implementação.
* **Controle:** O desenvolvedor e a LLM estão **presos às diretrizes da etapa ativa**. Se a LLM tentar escrever código na etapa `DISCUSS` ou `PLAN`, as ferramentas são rejeitadas deterministicamente com mensagens de veto instrutivas.
* **Navegação:** A tecla **`Tab`** avança ciclicamente pelas 4 etapas:
  `DISCUSS` ➔ `PLAN` ➔ `EXECUTE` ➔ `VALIDATE` ➔ `DISCUSS`...

---

### 🔥 Modo VIBE (Vibe Coding Livre & Ágil)

* **O que é:** O modo normal de liberdade criativa total. Aqui o desenvolvedor pode fazer vibe coding à vontade, pedindo qualquer funcionalidade, refatoração, arquivo avulso ou script direto sem cerimônias formais.
* **Sem Sub-etapas:** Não há divisões ou travas por etapa. A LLM executa prontamente o que você pedir.
* **Comportamento do `Tab`:** No modo VIBE, pressionar **`Tab` NÃO cicla etapas** (ele é reservado exclusivamente para autocompletar `/comandos` ou `@arquivos`).
* **Sinalização em VERMELHO VIVO:** A barra de status exibe o indicador em vermelho vivo:  
  `Modo: [VIBE]` (destaque visual marcante e sem sustos).
* **Permanência:** Uma vez no modo VIBE, você só sai de lá pressionando `Shift + Tab` novamente.

---

## ⚡ Chave Mestra: Atalho Shift + Tab

A qualquer momento durante o desenvolvimento na TUI:

* **Pressione `Shift + Tab`:** Comuta instantaneamente entre o **Modo TDD** e o **Modo VIBE**.
* **Retorno Inteligente:** Ao retornar para o Modo TDD, o sistema restaura exatamente a etapa onde você parou (ou inicia em `DISCUSS` por padrão).
* Funciona mesmo com o foco ativo no campo de digitação de texto.

---

## 🧱 As 4 Etapas Formais da ONDA & Navegação via Tab

Quando estiver no **Modo TDD**, utilize a tecla **`Tab`** para avançar entre as 4 etapas governadas:

| Etapa | Foco & Responsabilidades | Permissões de Ferramentas | Travas Determinísticas |
|---|---|---|---|
| **1. DISCUSS** | Concepção, viabilidade e alinhamento de escopo com `@demarco` e `@grace`. | Leitura liberada. Escrita permitida em `docs/briefings/` e documentação inicial. | ⛔ **Bloqueada** criação ou alteração de código em `src/`, `lib/`, `tests/`. |
| **2. PLAN** | Arquitetura com `@hamilton`, jornadas com `@alan` e breakdown de stories com `@david`. | Leitura liberada. Escrita em `docs/journeys/`, `docs/architecture/`, `docs/stories/`. | ⛔ **Bloqueada** criação ou edição de código de produção em `src/`. |
| **3. EXECUTE** | QA `@aniche` gera plano de testes; Devs implementam; Tech Lead `@unclebob` faz code review. | Escrita e leitura **100% liberadas** em `src/`, `tests/` e `docs/stories/`. | Segue o fluxo TDD: Teste ➔ Dev ➔ Code Review ➔ QA Run. |
| **4. VALIDATE** | Testes de integração, E2E, validação de DoD e relatório final com `@turing`. | Escrita de relatórios em `docs/reports/` e execução de suíte de testes. | ⛔ **Bloqueada** criação de novos módulos arbitrários em `src/` (evita scope creep). |

> **Dica:** O avanço de etapa via `Tab` persiste automaticamente o estado no banco SQLite local (`.bombe-code/state.db`) e sincroniza com a sessão ativa.

---

## 🌊 Orquestração de ONDAS & Comandos /wave

Além da navegação passo a passo via `Tab`, você pode comandar a esteira via comandos de barra (`/wave`):

### Iniciar uma Nova ONDA (`/wave start`)

```bash
/wave start [ONDA-ID] [auto|semi_auto] [--force]
```

**Exemplos:**
* `/wave start` — Inicia uma nova onda padrão no modo `AUTO`.
* `/wave start ONDA-002 auto` — Inicia a `ONDA-002` com autonomia total.
* `/wave start semi` — Inicia no modo semi-automático (pausa entre stories para confirmação).

---

### Alerta de Ondas Incompletas & Proteção `--force`

Se você tentar iniciar uma nova ONDA enquanto a onda atual **ainda possuir pendências ativas** (estágio diferente de `COMPLETED`), o Bombe Code emitirá um alerta amigável:

> `⚠️ A ONDA-001 ainda está em andamento (etapa: EXECUTE) e possui pendências ativas. Finalize-a com '/wave end' ou use '--force' ('/wave start ONDA-002 --force') para sobrescrever e iniciar uma nova onda.`

Isso protege você de perder o contexto de uma entrega em andamento por acidente.

---

### Execução Passo a Passo vs Modo Automático

Você tem dois jeitos elegantes de trabalhar:
1. **Passo a Passo Manual (via `Tab`):** Você navega em cada etapa no seu próprio ritmo, interage com a LLM sobre cada detalhe e dá `Tab` quando estiver satisfeito para avançar.
2. **Esteira Orquestrada (via `/wave start auto` ou `bombe wave run`):** O orquestrador aciona os especialistas em sequência, valida os quality gates (PRD Gate, Journey Gate, Architecture Gate, Story DoR Gate, Review Gate e Seal Gate) e entrega a ONDA de ponta a ponta.

---

## 👥 Elenco de Agentes Especialistas

O Bombe Code conta com agentes de inteligência hiper-focados que podem ser chamados com `@nome`:

### Upstream (Concepção & Planejamento)
* `@demarco` — Pesquisa de mercado, viabilidade e briefing de produto.
* `@grace` — Product Manager, visão de produto, métricas e PRD.
* `@alan` — Arquiteto de jornadas do usuário e navegação.
* `@norman` — UI/UX Designer, heurísticas e design system.
* `@hamilton` — Arquiteto de software, decisões estruturais e ADRs.
* `@david` — Agile Master, DoD/DoR e decomposição de ai-stories em `docs/stories/`.

### Core & Qualidade
* `@aniche` — QA Lead: escreve suíte de testes antes do dev (test-first) e executa validação final.
* `@unclebob` — Tech Lead: autoridade máxima em Clean Code, SOLID e Code Review rigoroso.
* `@turing` — Árbitro determinístico de gates, kanban e orquestração da ONDA.

### Devs Especialistas
* `@ada` — Frontend Developer (React, Next.js, Tailwind, Flutter).
* `@barbara` — Backend Developer (Python, FastAPI, Go).
* `@james` — Java Backend Developer (Spring Boot 3, Java 21).
* `@scott` — .NET Backend Developer (C# 12, ASP.NET Core).
* `@ryan` — Node.js & TypeScript Backend Developer.

### Operações & Infra
* `@radia` — SRE & Release Engineer: Docker, CI/CD, deploy e resiliência.

---

## ⌨️ Atalhos de Teclado na TUI

| Tecla de Atalho | Ação Executada |
|---|---|
| **`Shift + Tab`** | **Comuta entre Modo TDD e Modo VIBE** |
| **`Tab`** | **Alterna ciclicamente as etapas do Modo TDD** (`DISCUSS` ➔ `PLAN` ➔ `EXECUTE` ➔ `VALIDATE`) |
| **`Tab` (em `/` ou `@`)** | Autocompleta comandos de barra ou arquivos do projeto |
| **`Ctrl + P`** | Abre a Paleta de Comandos unificada |
| **`Ctrl + B`** | Alterna a exibição do Painel Lateral (Sidebar) com métricas de contexto |
| **`Ctrl + C`** / **`Esc`** | Interrompe o turno ativo da LLM |
| **`Ctrl + Q`** | Fecha a TUI com segurança |
| **`Up` / `Down`** | Navega no histórico de prompts enviados |

---

## 🛠️ Catálogo de Comandos de Barra (/)

Digite `/` no campo de prompt para ter sugestões instantâneas:

* `/wave status` — Visualiza o status da ONDA ativa, resumo de stories e gates do Turing.
* `/wave start [id] [auto|semi]` — Inicializa uma nova ONDA formal.
* `/wave discuss [tema]` — Executa a etapa DISCUSS com `@demarco` e `@grace`.
* `/wave plan` — Executa a etapa PLAN com os arquitetos de upstream.
* `/wave cycle [story_id]` — Executa o ciclo atômico de uma story específica com QA, Dev e Tech Lead.
* `/wave end` — Finaliza formalmente a ONDA atual.
* `/agent [nome]` — Alterna o agente de atendimento (ex: `/agent @aniche`, `/agent @unclebob`).
* `/models [nome]` — Lista ou troca o modelo de LLM ativo (ex: Z.ai, OpenAI, Claude, MiMo).
* `/compact` — Compacta o histórico da sessão para economizar contexto.
* `/undo` — Reverte o último turno e alterações de arquivo via git.
* `/rca <incidente>` — Executa Análise de Causa Raiz determinística com `@unclebob`.
* `/simplify <alvo>` — Conduz auditoria de simplificação de código com `@ieru` e `@unclebob`.
* `/exit` — Sai da aplicação.

---

*Bombe Code — Engenharia Determinística, Qualidade Industrial e Vibe Coding sem Atrito.*
