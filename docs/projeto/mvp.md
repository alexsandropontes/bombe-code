---
title: "Definição do MVP e Critérios Enterprise-Grade — Bombe Code"
date: "2026-10-31"
author: "@grace"
status: approved
version: "1.0.0"
tags:
  - mvp
  - roadmap
  - enterprise-grade
  - quality-gates
---

# Definição do MVP e Critérios Enterprise-Grade — Bombe Code

## 1. Princípio do MVP no Bombe Core

No Bombe Core, **MVP significa Minimum Viable Product Production-Ready**. Não é uma Prova de Conceito (POC), não é um protótipo descartável e não tolera código incompleto ou atalhos técnicos ("stubs de faz de conta").

Como o Bombe Code opera sob a classificação `scope_type: legacy-parity` e nível de maturidade `delivery_target: enterprise-grade`, **nenhuma funcionalidade crítica é ignorada**, e todo o código produzido deve suportar execução real, sob concorrência e condições de falha severa.

---

## 2. Quality Gates Enterprise-Grade (Constitution IX-A)

A modernização do Bombe Code só será declarada **DONE** se satisfazer integralmente os seis gates mandatários:

| Gate | Requisito Técnico | Critério de Aceite Objetivo |
| :--- | :--- | :--- |
| **G1** | Backend TDD Estrito | Slices de backend desenvolvidos sob ciclo RED/GREEN/REFACTOR rigoroso, sem código de produção escrito antes de teste falhante. |
| **G2** | Interface Operacional Real | CLI e TUI integrados diretamente aos serviços reais do core, consumindo o orquestrador sem camadas de simulação vazias. |
| **G3** | Zero Código Morto ou Stubs | Proibição absoluta de `NotImplementedError`, `pass`, comentários `// TODO` ou mocks em pastas de produção (`src/bombe_code/`). |
| **G4** | Testes de Integração com Infra Real | Provedores locais e clientes HTTP testados contra endpoints reais ou mocks de transporte de rede determinísticos, sem desativação de interceptors. |
| **G5** | Inicialização Limpa e Sem Erros | O executável sobe via CLI, processa parâmetros e executa fluxos completos sem exceções não tratadas ou vazamento de descritores de arquivo. |
| **G6** | Teste E2E de Contingência | Validação de ponta a ponta com simulação de interrupção (ex: conta Cloud estourada com erro 429) e recuperação transparente via modelo local. |

---

## 3. Escopo da Entrega Atual (MISSION-01 — Core Modernization)

O escopo da MISSION-01 contempla a modernização nuclear do sistema para destravar a esteira:

### Itens Incluídos (In-Scope — MVP)
1. **Equalização do Core e Governança:**
   - Atualização do arquivo `.bombeconfig` para `mode: slice-code` com migração registrada.
   - Refatoração dos dossiês de agentes para o padrão comportamental PDW 4.0, garantindo posturas cognitivas afiadas e papéis especializados.
2. **Orquestrador Híbrido de LLMs & Gateway de Resiliência:**
   - Abstração agnóstica de provedores: suporte nativo a Ollama/vLLM/OpenAI-compatible local e APIs comerciais (OpenAI, Anthropic, Z.AI).
   - Motor de scoring de complexidade da tarefa (1 a 10) para despacho dinâmico.
   - Interceptor reativo de exaustão de cota: detecção automática de HTTP 429 / erros de crédito e failover transparente em menos de 2 segundos para o pool local.
3. **Pipeline Kanban Granular (1 Round = 1 Story):**
   - Reformulação do motor de rounds: cada round encapsula exatamente 1 Story do backlog.
   - Preservação da queima atômica em Slices (Backend TDD + Frontend Construction).
   - Ponto de controle de revisão atômica com @unclebob ao término de cada round.
4. **Validação E2E com Provedor Real Estourado:**
   - Teste prático do cenário relatado na demanda (Z.AI com cota esgotada) acionando fallback local com continuidade da missão sem quebra de pipeline.

---

## 4. Escopo Postergar (Out-of-Scope — Releases Futuras)

As seguintes funcionalidades foram avaliadas estrategicamente e segregadas para versões subsequentes, evitando inflar o escopo do núcleo do harness:

| Funcionalidade | Release Alvo | Justificativa Estratégica (RICE / ROI) |
| :--- | :--- | :--- |
| **Painel Web de Telemetria e FinOps** | v1.1.0 | A CLI/TUI já provê métricas locais suficientes para o operador técnico. Um dashboard web adicionaria dependências de infra sem ganho no core de automação imediato. |
| **Fine-Tuning Automatizado de Modelos Locais** | v1.2.0 | Ajustar pesos de modelos locais a partir do histórico de commits é um acelerador valioso, mas exige massa de dados de rounds executados previamente. |
| **Cluster Mesh Multi-Nó de Inferência Local** | v2.0.0 | Orquestrar instâncias de Ollama distribuídas em múltiplos computadores da LAN corporativa tem alto esforço de rede e só se justifica após validação do nó único local. |
| **Suporte Nativo a Ambientes Windows sem WSL** | v1.1.0 | O foco da engenharia autônoma é ambientes POSIX/Linux. O suporte via WSL2 já cobre 100% dos usuários Windows sem complexidade adicional de caminhos de arquivo. |
