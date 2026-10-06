# 🏆 Relatório de Benchmark Comparativo: Bombe Code (TDD Governado) vs. LLM Genérica (Vibe Code)

**Data do Benchmark:** 03 de Outubro de 2026  
**Demanda Avaliada:** *App de Onboarding Interativo com Quiz Financeiro e Validação de Leads*  
**Objetivo de Entrega (Target):** MVP Operacional  
**Ambiente de Execução:** Ubuntu Linux / Python 3.13 / Node.js 24 LTS  

---

## Executive Summary

O objetivo deste benchmark é comparar empiricamente a **Plataforma Bombe Code** (executando em modo `tdd-code` com governança autônoma multi-agente, Turing Runtime, isolamento de papéis e travas de escopo) contra uma **LLM Genérica** (executando em modo livre / `vibe code`, simulando assistentes de codificação de mercado como Cursor, Copilot ou prompts livres).

Ambas as abordagens receberam a mesma demanda de negócio e geraram projetos funcionais em pastas separadas:
- **Bombe Code (ONDA Governança):** `/home/lexpontes/codeforgews/lexpontes/poc/onboarding-bombe-code`
- **LLM Genérica (Vibe Code):** `/home/lexpontes/codeforgews/lexpontes/poc/onboarding-generic-llm`

---

## 📊 Matriz Comparativa Consolidada

| Eixo de Avaliação | Bombe Code (Modo TDD Governado) | LLM Genérica (Modo Vibe Code) | Vencedor / Diferencial |
| :--- | :--- | :--- | :--- |
| **Arquitetura & Engenharia** | Monolito desacoplado, Hexagonal, Fastify, Shared Zod Schemas, 4 ADRs formais | Monolito Express + TypeScript em camadas simples, sem ADRs | **Bombe Code** (Padrão Enterprise) |
| **Persistência de Dados** | PostgreSQL Relacional, Migrações formais SQL (`0001_create_leads.sql`), ACID real | Arquivo JSON local (`data/leads.json`) com lock em memória | **Bombe Code** (Production-ready) |
| **Estratégia de Testes** | Pirâmide completa: Unitários + Integração de API + E2E com Playwright | Unitários e Integração HTTP rápida com `node:test` + Supertest | **Bombe Code** (Testes reais de UI/E2E) |
| **Controle de Escopo (YAGNI)** | Rígido: Focado 100% no teto do MVP (Quiz + Validação + Lead) | Scope Creep: Criou Painel CRM e Dashboard não solicitados | **Bombe Code** (Zero Scope Creep) |
| **Processo de Qualidade** | Quality Gates estritos: Viabilidade, PRD, Journey, Arch, DoR, Review, FinOps | Validação superficial baseada apenas em asserções do próprio código | **Bombe Code** (Default-Deny) |
| **Resiliência a Falhas** | Failover automático de provedores, tratamento CST (UTC+8) e Auto-Resolve | Falha no primeiro erro de runtime/cota sem fallback | **Bombe Code** (Alta Disponibilidade) |
| **Tempo Total de Execução** | ~29.5 minutos (pipeline profundo de 18 especialistas) | ~6.2 minutos (geração direta de bloco único) | **LLM Genérica** (Mais rápida) |
| **Consumo de Tokens** | 886,916 tokens | ~94,500 tokens | **LLM Genérica** (Menor footprint) |
| **Custo Estimado** | $0.046124 USD (~R$ 0,25) | ~$0.005 USD (~R$ 0,03) | **Ambos irrisórios** (< 5 centavos USD) |

---

## 🔬 Análise Detalhada por Abordagem

### 1. Plataforma Bombe Code (TDD / ONDA-001)

#### Destaques Positivos:
1. **Divisão de Responsabilidades Real (SoD - Segregation of Duties):**
   - O código não foi escrito e revisado pela mesma entidade. O QA (@aniche) projetou a suíte antes do Dev (@valim), e o Tech Lead (@unclebob) auditou Clean Code e SOLID antes do merge.
2. **Auto-Resolução Autônoma:**
   - Durante a execução, quando o QA apontou ambiguidade no plano de testes, o Turing Runtime acionou autonomamente a analista @caroli para refinar a especificação e desbloquear o card no Kanban sem travar a pipeline.
3. **Persistência e Contratos de Produção:**
   - Schemas Zod compartilhados entre client e server (`src/shared/lead-schema.ts`), garantindo fonte única de verdade.
   - Script de migração formal em SQL para PostgreSQL com garantias transacionais all-or-nothing.
   - Testes de ponta a ponta com Playwright validando navegação por teclado e acessibilidade WCAG.
4. **Governança de Custos e Fuso Horário:**
   - Telemetria transparente detalhada por agente, com detecção e tratamento de fusos horários da Z.ai (Pequim CST / UTC+8) e Provider Failover Router integrado.

#### Pontos de Atenção:
- Exige pipeline mais longo devido à orquestração multi-estágio e múltiplos gates de validação física no disco.

---

### 2. LLM Genérica (Vibe Code / Modo Livre)

#### Destaques Positivos:
1. **Velocidade de Kickoff:**
   - Ideal para prototipagem rápida e visualização imediata da interface.
2. **Interface Rica:**
   - Entregou um frontend visualmente atraente com CSS glassmorphism e medidor visual de score de crédito.
3. **Validação de Entrada Cuidadosa:**
   - Implementou algoritmo de validação matemática de CPF (módulo 11 da Receita Federal) e checagem de DDDs válidos no Brasil.

#### Fragilidades Técnicas (Riscos em Produção):
1. **Persistência Não Escalável (JSON File):**
   - A LLM genérica optou por salvar os leads em um arquivo `data/leads.json`. Em um ambiente corporativo ou com concorrência real, isso gera condições de corrida (race conditions) e corrupção de dados.
2. **Scope Creep Natural (Alucinação de Escopo):**
   - Sem as travas do `TuringPromptAssembler` e do `DELIVERY_TARGET: MVP`, a LLM genérica inventou um módulo de CRM completo com tabela administrativa e filtros que não foram pedidos, aumentando a superfície de ataque e o custo de manutenção desnecessariamente.
3. **Ausência de Testes End-to-End Reais:**
   - Os 40 testes gerados são unitários e de integração HTTP em memória (`supertest`). Não houve teste de interface real com leitor de tela ou navegador (Playwright/Puppeteer).

---

## 🎯 Conclusão e Veredito

| Cenário de Uso | Recomendação |
| :--- | :--- |
| **Ambientes Críticos / Produção / Enterprise** | **Bombe Code (TDD):** Indispensável para garantir código auditado, sem scope creep, com banco relacional real, testes E2E e zero risco de débito técnico acumulado. |
| **Hackathons / POCs Descartáveis de 1 Hora** | **LLM Genérica (Vibe Code):** Adequada para validações rápidas de conceito onde a persistência e a arquitetura formal não são requisitos imediatos. |

O custo de rodar a governança completa do Bombe Code para entregar um MVP robusto foi de **$0.046 USD (menos de 25 centavos de real)**, comprovando que o rigor de engenharia de software de ponta a ponta é viável, econômico e determinístico.
