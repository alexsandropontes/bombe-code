---
round: 3
story_id: STORY-003
epic_id: EP-02
status: done
started_at: "2026-10-31T16:20:00"
completed_at: "2026-10-31T16:31:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-3 — STORY-003: Contrato LLMProviderProtocol e Adapter Local vLLM (Porta 18096, Fila Indiana)

## 1. Round Goal
Definir e implementar o contrato unificado de inferência `LLMProviderProtocol` e o adapter local `LocalVllmAdapter` para o motor vLLM operando na porta `18096`, integrando o gerenciador de VRAM com política estrita de **Fila Indiana** (`SingleModelQueueManager`) e garantindo streaming assíncrono de tokens e healthcheck com cobertura unitária e de integração em 100%.

## 2. Escopo do Round
- **Story Alocada:** `STORY-003` (Contrato LLMProviderProtocol e Adapter Local vLLM (Porta 18096, Fila Indiana)).
- **Entregáveis Técnicos:**
  1. Contrato `LLMProviderProtocol` e dataclasses imutáveis `CompletionChunk` e `ToolCallChunk` em `src/bombe_code/providers/protocol.py`.
  2. Adapter local `LocalVllmAdapter` com streaming assíncrono via `httpx.AsyncClient` consumindo `http://127.0.0.1:18096/v1` em `src/bombe_code/providers/local_vllm.py`.
  3. Gerenciador de concorrência de VRAM `SingleModelQueueManager` garantindo modelo único ativo na GPU.
  4. Suíte de testes unitários e de integração em `tests/unit/test_vllm_adapter.py`.
- **Fronteira Negativa:** Não implementar o classificador de complexidade ou roteador dinâmico (Round 4 / STORY-004), nem o gerenciador de cotas e circuit breaker (Round 5 / STORY-005), nem parsers de fallback (Round 6 / STORY-006).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Contrato `LLMProviderProtocol` implementado como `@runtime_checkable` Protocol com métodos assíncronos `stream_chat` e `check_health` em `src/bombe_code/providers/protocol.py`.
- [x] Dataclasses imutáveis e congeladas `CompletionChunk` e `ToolCallChunk` definidas rigorosamente conforme a especificação arquitetural.
- [x] `LocalVllmAdapter` implementado em `src/bombe_code/providers/local_vllm.py` consumindo endpoint local `127.0.0.1:18096` com streaming assíncrono de tokens via `httpx.AsyncClient`.
- [x] `SingleModelQueueManager` implementado garantindo a política de Fila Indiana (rejeição ou enfileiramento determinístico de requisições concorrentes para modelos distintos, evitando colisão de VRAM).
- [x] Healthcheck determinístico no método `check_health()` validando disponibilidade da porta 18096 com timeout de 2000ms.
- [x] Suíte de testes unitários e de integração implementada em `tests/unit/test_vllm_adapter.py` com 100% dos testes passando (AC-01 a AC-04 cobertos).
- [x] Código em conformidade com tipagem estrita (`mypy --strict`), tratamento assíncrono seguro de sockets HTTP e sem vazamento de conexões.
- [x] Ausência de stubs, dead code, prints de debug ou bodies vazios (`pass`, `...`) em código de produção.
- [x] Zero metadados decorativos, assinaturas de personas ou rodapés institucionais persistidos em arquivos de código.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob).
- [x] Validação formal do round executada pelo Agile Master (@david).
