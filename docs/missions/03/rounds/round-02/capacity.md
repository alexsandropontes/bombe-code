---
round: 2
capacity_hours: 2.5
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Developer & Hardware Profiling)"
  "@hoare": "100% (Code Reviewer & Quality Gatekeeper)"
  "@unclebob": "100% (Tech Lead & Architectural Guardian)"
  "@david": "100% (Agile Master & Flow Architect)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-2

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 2.5 horas (1 Story de Complexidade Nível 2 / Pleno).
- **Capacidade Comprometida:** 2.5 horas (100% alocada para STORY-016).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência canônica 1 Round = 1 Story).

## 2. Alocação da Equipe Multi-Estação
- **Dev Backend:** @barbara — Implementação TDD de `HardwareProfile`, `ModelKey`, catálogo de modelos e flags de CLI.
- **Reviewer:** @hoare — Verificação estrita de cobertura de ACs, tipagem e ausência de stubs.
- **Tech Lead:** @unclebob — Guardião arquitetural, SRF check e conformidade estrutural.
- **Agile Master:** @david — Governança de fluxo, rastreabilidade e validação de DoD.

## 3. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 15 min (@unclebob) — [Concluído]
- **Estação 3 (Queima TDD Downstream - Red/Green/Refactor):** 75 min (@barbara) — [Em Execução]
- **Estação 4 (Compliance & Code Review):** 25 min (@hoare & @unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 20 min (@david)

## 4. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Apenas a STORY-016 está ativa na bancada.
2. **TDD Estrito (Zero Mocks em Produção):** Código limpo em `src/bombe_code/local/profiles.py` com testes unitários em `tests/unit/test_profiles.py`.
3. **Parada Determinística em DoR:** DoR validado; execução TDD até suite completa verde.
