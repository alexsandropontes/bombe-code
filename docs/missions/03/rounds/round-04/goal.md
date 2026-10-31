---
round: 4
story_id: STORY-018
epic_id: EP-09
status: validated
started_at: "2026-10-31T21:52:00"
maturity_level: mvp
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-4 — STORY-018: Integração com HybridRouter e Execução E2E do Rate Limiter

## 1. Round Goal
Integrar o `LocalModelManager` ao `HybridRouter` para inicialização sob demanda do modelo local correto (com aceleração MTP e teto de contexto) e implementar o algoritmo de `TokenBucketRateLimiter` thread-safe com suporte a recarga temporal determinística e capacidade máxima, validando a esteira ponta a ponta com testes de unidade e teste de integração E2E.

## 2. Escopo do Round
- **Story Alocada:** `STORY-018` (Integração com HybridRouter e Execução E2E do Rate Limiter).
- **Entregáveis Técnicos:**
  - Pacote de features `src/bombe_code/features/` e módulo `src/bombe_code/features/rate_limiter.py` com classe `TokenBucketRateLimiter`.
  - Suíte de testes unitários `tests/unit/test_rate_limiter.py` cobrindo rajada, recarga temporal injetável e concorrência multithreaded (50 threads sem race conditions).
  - Atualização do `HybridRouter` em `src/bombe_code/routing/router.py` para suportar `LocalModelManager`, verificação de endpoint ativo/saudável e método `ensure_local_model_ready`.
  - Suíte de testes unitários `tests/unit/test_hybrid_router_local.py` validando o comportamento de lifecycle do modelo sob o roteador.
  - Teste de integração E2E `tests/integration/test_rate_limiter_e2e.py` simulando roteamento, ativação com flags MTP no `llama-server` e proteção por rate limiter.
- **Fronteira Negativa:** Não alterar endpoints externos de nuvem nem lógica já validada de VRAMGate ou perfis de hardware.

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Implementação de `TokenBucketRateLimiter` em `src/bombe_code/features/rate_limiter.py`.
- [x] Testes unitários do rate limiter em `tests/unit/test_rate_limiter.py` com 100% de aprovação.
- [x] Atualização do `HybridRouter` em `src/bombe_code/routing/router.py` com `ensure_local_model_ready`.
- [x] Testes unitários do `HybridRouter` com `LocalModelManager` em `tests/unit/test_hybrid_router_local.py`.
- [x] Teste de integração E2E em `tests/integration/test_rate_limiter_e2e.py` validando flags MTP e interceptação do rate limiter.
- [x] Suíte completa do repositório (`pytest`) e linter (`ruff`) verdes sem regressões.
- [x] Métodos com SRF (< 30 linhas), type hints estritos e zero mocks em código de produção (`src/`).
