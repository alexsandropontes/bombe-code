---
id: STORY-003
title: "Contrato LLMProviderProtocol e Adapter Local vLLM (Porta 18096, Fila Indiana)"
epic_id: EP-02
round: ROUND-3
agent: "@barbara"
estimation: 4h
status: ready
type: feature
layer: backend
depends_on:
  - STORY-002
tags:
  - providers
  - vllm
  - protocol
  - streaming
  - fila-indiana
---

# STORY-003 — Contrato LLMProviderProtocol e Adapter Local vLLM (Porta 18096, Fila Indiana)

## 1. Contexto & Racional de Negócio
Para viabilizar a orquestração híbrida de modelos de IA e garantir que o Bombe Code funcione com custo zero de tokens em hardware local, é indispensável estabelecer uma camada de abstração sólida de provedores. Esse contrato deve suportar streaming assíncrono de tokens e tool calling, além de disponibilizar um adapter robusto para o motor vLLM local operando na porta dedicada `18096` sob o princípio de **Fila Indiana** (um modelo por vez na VRAM para evitar estouro de memória GPU).

## 2. Escopo

### O que a História Cobre
- Definição do contrato `LLMProviderProtocol` via `typing.Protocol` em `src/bombe_code/providers/protocol.py`.
- Modelagem das estruturas de dados imutáveis `CompletionChunk` e `ToolCallChunk`.
- Implementação do `LocalVllmAdapter` consumindo a API HTTP OpenAI-compatible do vLLM local (`http://127.0.0.1:18096/v1`).
- Implementação do gerenciador de **Fila Indiana** (`SingleModelQueueManager`) que assegura que apenas um modelo seja mantido ativo na VRAM.
- Testes de unidade e integração utilizando mock de socket HTTP local assíncrono.

### O que a História NÃO Cobre
- Não implementa o classificador de complexidade ou as regras de chaveamento (STORY-004).
- Não implementa o gerenciador de cotas e circuit breaker de APIs externas (STORY-005).

## 3. User Story
- **Como:** Subsistema de inferência do Bombe Code,
- **Quero:** Um contrato unificado de provedor e um adapter especializado para o motor local vLLM na porta 18096,
- **Para que:** O harness execute chamadas com streaming em alta velocidade sem concorrer por VRAM nem depender de conexões externas.

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Conformidade de Protocolo):** `LocalVllmAdapter` deve implementar integralmente `LLMProviderProtocol` e passar na verificação `isinstance(adapter, LLMProviderProtocol)` em runtime.
- **AC-02 (Streaming Assíncrono):** O método `stream_chat()` deve emitir assincronamente instâncias de `CompletionChunk` contendo o delta textual gerado.
- **AC-03 (Política de Fila Indiana):** O `SingleModelQueueManager` deve recusar o carregamento simultâneo de mais de um modelo na porta 18096, garantindo a liberação explícita da VRAM antes de carregar um novo peso.
- **AC-04 (Healthcheck Deterministico):** O método `check_health()` deve retornar `True` quando a porta 18096 responder HTTP 200 em tempo inferior a 2000ms, e `False` em caso de recusa de conexão.

## 5. Definition of Done (DoD)
- [ ] Código implementado em `src/bombe_code/providers/` sob tipagem estrita com `httpx.AsyncClient`.
- [ ] Suíte de testes com cobertura de streaming, reconexão e fila indiana passando em `tests/unit/test_vllm_adapter.py`.
- [ ] Zero vazamento de conexões ou recursos de rede não finalizados.
- [ ] Code review aprovado por @unclebob.

## 6. Notas Técnicas & Diretrizes Arquiteturais
- Seguir fielmente o schema apresentado na seção 4.1 da arquitetura (`CompletionChunk`, `ToolCallChunk`, `LLMProviderProtocol`).
- Porta padrão configurável, com default estrito em `18096`.

## 7. Dependências
- **Bloqueado por:** `STORY-002` (Round 2 concluído).
- **Desbloqueia:** `STORY-004` (Round 4).
