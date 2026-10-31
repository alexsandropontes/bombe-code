---
round: 4
capacity_hours: 3.5
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Developer & Systems Specialist)"
  "@hoare": "100% (Code Reviewer & Quality Gatekeeper)"
  "@unclebob": "100% (Tech Lead & Architectural Guardian)"
  "@david": "100% (Agile Master & Flow Architect)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-4

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 3.5 horas (1 Story de Complexidade Nível 2 / Pleno).
- **Capacidade Comprometida:** 3.5 horas (100% alocada para STORY-018).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência canônica 1 Round = 1 Story).

## 2. Alocação da Equipe Multi-Estação
- **Dev Backend:** @barbara — Implementação TDD de `TokenBucketRateLimiter`, integração do `LocalModelManager` no `HybridRouter` e suíte E2E.
- **Reviewer:** @hoare — Verificação estrita de conformidade com os critérios de aceite (AC-1 a AC-4).
- **Tech Lead:** @unclebob — Guardião arquitetural, SRF check (< 30 linhas) e zero mocks em código de produção.
- **Agile Master:** @david — Governança de fluxo, rastreabilidade e validação de DoD.

## 3. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 15 min (@unclebob) — [Concluído]
- **Estação 3 (Queima TDD Downstream - Red/Green/Refactor):** 110 min (@barbara) — [Em Execução]
- **Estação 4 (Compliance & Code Review):** 40 min (@hoare & @unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 30 min (@david)

## 4. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Apenas a STORY-018 está ativa na esteira.
2. **TDD Estrito (Zero Mocks em Produção):** Código limpo em `src/bombe_code/features/` e `src/bombe_code/routing/` com testes unitários e de integração.
3. **Parada Determinística em DoR:** DoR validado por @david e @unclebob; execução TDD até suíte completa verde.
