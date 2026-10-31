---
title: "Escopo Geral do Produto — Bombe Code"
date: "2026-10-31"
author: "@grace"
status: approved
approved_by: "@grace"
approved_at: "2026-10-31T17:55:00"
version: "1.1.0"
tags:
  - escopo
  - inception
  - bombe-code
  - strategy
  - cli-parity
  - core-v4
---

# Escopo Geral do Produto — Bombe Code

## 1. Visão de Produto Sniper

> **Para** desenvolvedores de software, engenheiros de IA e equipes ágeis que buscam autonomia operacional e disciplina de engenharia,  
> **o Bombe Code** é um harness autônomo CLI/TUI nativo em Python que orquestra agentes de inteligência artificial sob o rigor metodológico e arquitetural do Bombe Core v4,  
> **que** automatiza a entrega de software ponta a ponta através de fatiamento atômico (Slice Code) na cadência **1 Round = 1 Story**, com comandos CLI canônicos equalizados e roteamento híbrido inteligente entre modelos locais e cloud,  
> **diferentemente de** assistentes genéricos de chat ou extensões proprietárias acopladas a nuvens corporativas que geram dependência, custos astronômicos e código não testado,  
> **nós** oferecemos independência de infraestrutura, redução de 80%+ nos custos de tokens, esteira contínua desatendida e garantia de paridade funcional estrita com o Bombe Core.

---

## 2. O que o Bombe Code É vs. O que NÃO É

| O que o Bombe Code É | O que o Bombe Code NÃO É |
| :--- | :--- |
| **Harness CLI/TUI Nativo em Python:** Runtime completo e desacoplado que governa o ciclo de vida, ferramentas e execução de agentes de IA locais e remotos via terminal. | **Não é uma extensão de IDE:** Não é plugin para VS Code, JetBrains ou Cursor; opera como software de engenharia autônomo headless. |
| **Orquestrador de Missões, Rounds e Slices:** Implementação estrita da esteira Slice Code v3/v4 (Round 0 Upstream Macro + Rounds de Execução com Slices Backend TDD + Frontend Construction). | **Não é uma esteira baseada no conceito legado de "Ondas":** O conceito de ondas foi formalmente descontinuado por ser monolítico e ineficiente. |
| **CLI Canônica Equalizada ao Bombe Core v4:** Suporte integral a 19 entry points canônicos (`bombe mission`, `bombe round`, `bombe project`, `bombe mode`, etc.) com paridade 1:1 de funções. | **Não é uma ferramenta de comandos desconexos:** Cada comando reflete diretamente um protocolo constitucional do Core. |
| **Bridge Transparente de Retrocompatibilidade:** Interceptor pedagógico para comandos legados (`bombe wave ...`), redirecionando-os para a sintaxe moderna sem quebrar scripts existentes. | **Não é um software de breaking changes abruptas:** Não aborta comandos legados de forma ríspida sem guiar o desenvolvedor para o novo padrão. |
| **Roteador Híbrido e Resiliente de LLMs:** Engine inteligente capaz de despachar requisições por score de complexidade e chavear instantaneamente para LLMs locais sob HTTP 429. | **Não é um simples wrapper de API única:** Opera com múltiplos backends (vLLM, Ollama, OpenAI, Anthropic, Z.AI) mantendo alta disponibilidade. |
| **Esteira Kanban Granular (1 Round = 1 Story):** Cadência de desenvolvimento em fluxo contínuo que assegura escopo unitário, revisões atômicas por @unclebob e lead time reduzido. | **Não é esteira Waterfall:** Não acumula dezenas de histórias em rounds massivos que sobrecarregam a janela de contexto de auditoria. |

---

## 3. Transição Arquitetural: Obsolescência Formal de "Ondas" em Favor de "Missões, Rounds e Slices"

### 3.1. Aposentadoria do Modelo de Ondas (Waves)
Nas iterações experimentais prévias do Bombe Code, adotava-se o conceito de **"Onda" (Wave)** como unidade de entrega agregada. A experiência de engenharia comprovou que o modelo de ondas acarretava:
1. **Acoplamento de Escopo:** Múltiplas histórias e tarefas eram processadas em um mesmo lote, dificultando o isolamento de regressões.
2. **Sobrecarga Cognitiva dos Agentes:** Revisores (@unclebob e @hoare) precisavam auditar grandes diffs acumulados, degradando a qualidade da análise de conformidade.
3. **Incompatibilidade com o Bombe Core v4:** O ecossistema canônico padronizou o ciclo operacional em Missões -> Rounds -> Fases -> Slices.

### 3.2. Adoção da Arquitetura Canônica Core v4
A partir da versão atual, o Bombe Code consolida:
- **Missão (`bombe mission`):** Unidade macro de entrega atrelada a uma demanda de negócio. Possui ciclo de vida formal (`open`, `active`, `completed`) e porteiro atômico que impede a concorrência desordenada.
- **Round (`bombe round`):** Unidade de planejamento e queima onde **1 Round = 1 Story**. Executa a esteira em três modalidades operacionais: Manual (`round start` com parada na DoR), Semi-Auto (`round full`) ou Pipeline Contínuo (`round all`).
- **Slice:** Fatiamento vertical atômico de uma story em **Slice Backend (TDD estrito: RED -> GREEN -> REFACTOR)** e **Slice Frontend (CONSTRUCTION)**.

### 3.3. A Wave Bridge de Retrocompatibilidade
Para assegurar continuidade operacional a usuários e pipelines legados, o runtime incorpora a **Wave Bridge**. Invocadores de `bombe wave <subcomando>` são interceptados, recebem um aviso pedagógico no console e são redirecionados de forma transparente para a primitiva canônica de rounds ou missões correspondente.

---

## 4. Catálogo de Entry Points CLI Equalizados

| ID | Comando Canônico Bombe Code | Equivalente Bombe Core v4 | Categoria | Finalidade no Ciclo de Vida |
| :--- | :--- | :--- | :--- | :--- |
| **EP-01** | `bombe mission new '<demanda>'` | `*bc project mission '<demanda>'` | Missão | Inicialização da missão com porteiro atômico e Upstream Macro (Round 0). |
| **EP-02** | `bombe mission status` | — | Missão | Exibição do estado, progresso de rounds e métricas da missão ativa. |
| **EP-03** | `bombe mission end` | `*bc project mission end` | Missão | Validação de DoD geral, encerramento formal e arquivamento da missão. |
| **EP-04** | `bombe round start [N]` | `*bc execute round-start [N]` | Round (Manual) | Planejamento upstream da story, fatiamento em slices e parada mandatória na DoR. |
| **EP-05** | `bombe round burn [N]` | `*bc execute round-burn [N]` | Round (Manual) | Queima atômica TDD dos slices da story (Red/Green/Refactor). |
| **EP-06** | `bombe round review [N]` | `*bc execute round-review [N]` | Round (Manual) | Auditoria técnica de conformidade arquitetural por @hoare e @unclebob. |
| **EP-07** | `bombe round validate [N]` | `*bc execute round-validate [N]` | Round (Manual) | Validação de negócio contra critérios de aceitação e DoD por @david. |
| **EP-08** | `bombe round full [N]` | `*bc execute round-full [N]` | Round (Semi-Auto) | Execução sequencial ponta a ponta da story do round com parada final para homologação. |
| **EP-09** | `bombe round all` | `*bc execute round-all` | Round (Contínuo) | Pipeline contínuo desatendido para todos os rounds pendentes da missão. |
| **EP-10** | `bombe round status` | `*bc execute round-status` | Round | Inspeção tabular do status do round, kanban de slices e quality gates. |
| **EP-11** | `bombe wave <cmd>` *(legado)* | Ponte / Alias | Bridge | Interceptação amigável com warning e despacho para a primitiva canônica. |
| **EP-12** | `bombe project configure` | `*bc project configure` | Projeto | Configuração do `.bombeconfig`, paths, stack tecnológica e guardrails. |
| **EP-13** | `bombe project ship [env]` | `*bc project ship [env]` | Projeto | Promoção controlada de branches Git (`dev`, `hml`, `prd`) com testes prévios. |
| **EP-14** | `bombe mode [modo]` | `*bc mode [modo]` | Operação | Alternância auditada entre os modos `slice-code` e `vibe-code`. |
| **EP-15** | `bombe task '<desc>'` | `*bc task '<desc>'` | Standalone | Execução de tarefa técnica pontual roteada pelo Protocolo Garçom. |
| **EP-16** | `bombe rca '<incidente>'` | `*bc rca '<incidente>'` | Standalone | Análise forense de causa raiz determinística (Ishikawa + 5 Porquês). |
| **EP-17** | `bombe review [alvo]` | `*bc review [alvo]` | Standalone | Code review avulso multi-eixo sem aprovação automática. |
| **EP-18** | `bombe simplify [alvo]` | `*bc simplify [alvo]` | Standalone | Refatoração para redução de complexidade ciclomática preservando testes. |
| **EP-19** | `bombe status-report` | `*bc status-report` | Standalone | Relatório executivo do projeto, governança e saúde do repositório. |

---

## 5. Objetivos de Negócio

1. **Paridade 1:1 com a Governança Bombe Core v4:**
   - Garantir que qualquer operador ou agente familiarizado com os comandos canônicos `*bc` tenha exatamente as mesmas garantias de fluxo, qualidade e gates ao interagir via terminal com a CLI `bombe`.
2. **Eliminação do Débito Conceitual de Ondas:**
   - Erradicar referências ativas a ondas no código de produção e esteira interna, consolidando a mentalidade ágil de entrega contínua por fatias verticais.
3. **Preservação do Investimento e Automações Existentes:**
   - Garantir 0% de quebra em rotinas baseadas na sintaxe legada através da Wave Bridge ativa.
4. **Resiliência e Economia de Infraestrutura:**
   - Manter a esteira operando mesmo sob esgotamento total de créditos em nuvem comercial, despachando a queima de slices para instâncias locais.

---

## 6. Personas Atendidas

### 6.1. Engenheiro de Software / Desenvolvedor Autônomo
- **Perfil:** Operador diário de terminal focado em entrega rápida, código limpo e testes verdes sem interrupções artificiais.
- **Valor:** Execução via `bombe round all` ou `bombe round full`, parando exclusivamente diante de quebras reais de teste ou bloqueios de especificação.

### 6.2. Tech Lead / Arquiteto de Software
- **Perfil:** Guardião da qualidade estrutural, integridade arquitetural e rastreabilidade documental.
- **Valor:** Garantia de persistência física em `docs/`, auditorias formais em cada round por @unclebob e zero código morto em produção.

### 6.3. Operador de Scripts & Pipelines Legados
- **Perfil:** Desenvolvedor ou ferramenta de CI/CD que invoca comandos clássicos do ecossistema.
- **Valor:** Funcionamento contínuo via Wave Bridge com indicação clara do caminho canônico de modernização.

---

## 7. Restrições Operacionais Inegociáveis

1. **CLI First:** Nenhuma dependência visual é requisito para execução de qualquer comando ou tomada de decisão.
2. **Filesystem como SSOT (Single Source of Truth):** Proibido persistir estado de missões apenas em memória. Arquivos em `docs/missions/NN/` regem a verdade operacional.
3. **Porteiro Atômico Bloqueante:** Apenas uma única missão pode estar ativa (`open`, `active`, `in_progress`) por vez no projeto.
4. **Integridade de Produção:** Zero mocks, zero stubs e zero `NotImplementedError` em pacotes sob `src/bombe_code/`.
