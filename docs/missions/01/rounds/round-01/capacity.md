---
round: 1
capacity_hours: 2.0
stories_count: 1
wip_limit: 1
team_availability:
  "@fowler": "100% (Backend & Test Engineering)"
  "@unclebob": "100% (Tech Lead & Architectural Review)"
  "@david": "100% (Flow & Governance)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-1

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 2.0 horas (1 Story de Complexidade Nível 1).
- **Capacidade Comprometida:** 2.0 horas (100% alocada para STORY-001).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência estrita 1 Round = 1 Story).

## 2. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 15 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - Red/Green/Refactor):** 60 min (@fowler)
- **Estação 4 (Compliance & Code Review):** 20 min (@unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 10 min (@david)

## 3. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Nenhuma outra tarefa ou story pode ser iniciada antes do fechamento formal de todos os checkboxes de DoD de `goal.md`.
2. **TDD Estrito:** Nenhum código em `src/bombe_code/config/` pode ser criado ou alterado sem um teste unitário falhante prévio (RED).
3. **Parada Determinística em DoR:** O Upstream entrega o round pronto para implementação; a queima é acionada via comando de downstream (`round-burn`).
