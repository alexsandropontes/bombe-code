---
id: STORY-018
title: "Integração com HybridRouter e Execução E2E do Rate Limiter"
epic_id: EP-09
type: fullstack
agent: "@barbara"
estimation: "3h30m"
depends_on: ["STORY-017"]
status: done
---

# STORY-018: Integração com HybridRouter e Execução E2E do Rate Limiter

## ✅ VALIDAÇÃO PROCESSO (DOR)
- [x] Template ai-story utilizado corretamente
- [x] Frontmatter preenchido (id, type, agent, estimation, depends_on)
- [x] Acceptance Criteria definidos (visão de negócio/sistema)
- [x] DoD definido
- [x] Critérios INVEST atendidos

## ✅ VALIDAÇÃO DEV (DOR)
- [x] Slicing técnico validado em 3 slices atômicos (@unclebob)
- [x] Estratégia TDD estrita (Red -> Green -> Refactor)
- [x] Contratos e interfaces definidos (`TokenBucketRateLimiter`, `HybridRouter.ensure_local_model_ready`)
- [x] Dependência STORY-017 concluída e validada

## Contexto & Visão do Usuário
Como usuário do framework, eu quero que o `HybridRouter` conecte requisições aos modelos locais gerenciados e execute com sucesso a implementação do algoritmo de Token Bucket Rate Limiter, validando a esteira ponta a ponta.

## Acceptance Criteria
- [x] **AC-1:** O `HybridRouter` deve requisitar ao `LocalModelManager` a inicialização do modelo correto caso o servidor local não esteja respondendo ou estiver rodando modelo divergente.
- [x] **AC-2:** A implementação do `TokenBucketRateLimiter` deve suportar taxa de recarga (`refill_rate`), capacidade máxima (`capacity`) e método `consume(tokens: int) -> bool` thread-safe.
- [x] **AC-3:** Suíte completa de testes unitários do Rate Limiter executada via `pytest` com 100% de aprovação.
- [x] **AC-4:** Evidência de geração de código via modelo local acelerado com MTP registrada no log de execução e interceptação do rate limiter.

## Definition of Done (DoD)
- [x] Implementação de `TokenBucketRateLimiter` em `src/bombe_code/features/rate_limiter.py`.
- [x] Suíte de testes unitários do rate limiter em `tests/unit/test_rate_limiter.py`.
- [x] Integração no `HybridRouter` em `src/bombe_code/routing/router.py`.
- [x] Suíte de testes unitários do `HybridRouter` com `LocalModelManager` em `tests/unit/test_hybrid_router_local.py`.
- [x] Testes de integração e unitários em `tests/integration/test_rate_limiter_e2e.py`.

## Dependências
- `STORY-017`
