---
id: EP-02
title: "Orquestrador Híbrido de LLMs & Fallback de Cota"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-01"
tags:
  - hybrid-llm
  - router
  - quota-manager
  - fallback
  - vllm
---

# EP-02 — Orquestrador Híbrido de LLMs & Fallback de Cota

## 1. Problema de Negócio
O Bombe Code depende criticamente de chamadas a provedores cloud proprietários (ex: Z.AI, OpenAI, Anthropic). Na conjuntura atual, cotas de chaves cloud frequentemente sofrem esgotamento súbito ou rate limits (HTTP 429), paralisando o ciclo de desenvolvimento de software autônomo. Além disso, tarefas mecânicas e simples consomem tokens caros de APIs externas, inflacionando o custo operacional em 80%+ sem necessidade.

## 2. Valor de Negócio
- **Autonomia Operacional Ininterrupta:** Continuidade garantida da esteira de desenvolvimento, mesmo durante quedas de internet ou bloqueios de faturamento em nuvens terceiras.
- **Eficiência Financeira (FinOps):** Redução mínima de 80% nos custos de tokens cloud, direcionando tarefas mecânicas e testes para instâncias vLLM locais gratuitas.
- **Proteção de Hardware:** Gerenciamento local em fila indiana na porta `18096`, garantindo que apenas um modelo ocupe a VRAM por vez e evitando travamentos por OOM (Out Of Memory).

## 3. Escopo

### O que o Épico Cobre
- Criação do contrato formal `LLMProviderProtocol` e adapter local para vLLM (`http://127.0.0.1:18096/v1`).
- Implementação da política de **Fila Indiana** para modelos locais (LFM 1.7B, Gemma 4B, Qwen 9B, Gemma 26B).
- Construção do classificador determinístico de complexidade (`ComplexityClassifier`) com pontuação de 1 a 3.
- Desenvolvimento do `HybridRouter` para despacho inteligente baseado em complexidade e disponibilidade de cota.
- Implementação do `QuotaManager` com Circuit Breaker persistido (`quota_state.json`), detecção de HTTP 429 e fallback em < 2000ms.
- Criação do `FallbackToolParser` para resgatar chamadas de tools expressas em markdown/JSON puro por modelos locais compactos.

### O que o Épico NÃO Cobre
- Não realiza treinamento, fine-tuning ou quantização de modelos locais (usa binários pré-quantizados GGUF/AWQ).
- Não gerencia a esteira de execução de rounds do Kanban (escopo do EP-03).
- Não realiza testes end-to-end com simulação de missões completas (escopo do EP-04).

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-003` | Round 3 | Contrato LLMProviderProtocol e Adapter Local vLLM (:18096, Fila Indiana) | @barbara | 4h |
| `STORY-004` | Round 4 | Classificador de Complexidade de Slice e Roteador Híbrido Dinâmico | @barbara | 3h |
| `STORY-005` | Round 5 | QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local | @barbara | 4h |
| `STORY-006` | Round 6 | FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON | @barbara | 3h |

## 5. Dependências
- **Upstream:** Épico EP-01 concluído e validado (runtime e configurações equalizadas).
- **Downstream:** Base técnica mandatória para a Esteira Kanban (EP-03) e Testes E2E (EP-04).

## 6. Critérios de Sucesso
- Endpoint vLLM local responde streaming assíncrono respeitando o contrato `LLMProviderProtocol`.
- Roteador despacha tarefas Nota 1 e 2 prioritariamente para o cluster local.
- Resposta HTTP 429 de provedor cloud aciona chaveamento para modelo local em tempo < 2.0 segundos sem lançar exceções não tratadas.
- `FallbackToolParser` extrai com sucesso payloads de tool calls gerados em blocos markdown.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Estouro de VRAM na GPU local (CUDA OOM) | Crítica | Imposição rígida da Fila Indiana: swap sequencial com desalocação de modelo anterior antes de subir novo binário. |
| Modelos locais pequenos falharem em emitir tool calls no padrão OpenAI | Alta | Implementação do `FallbackToolParser` como interceptador transparente com regex tolerante a markdown. |
| Oscilação intermitente de rede gerando falsos positivos de cota | Média | Circuit Breaker com contador de falhas consecutivas (threshold = 3) e TTL configurável (`locked_until`). |
