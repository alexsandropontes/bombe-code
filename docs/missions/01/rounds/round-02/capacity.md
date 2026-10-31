---
round: 2
capacity_hours: 3.0
stories_count: 1
wip_limit: 1
team_availability:
  "@andrej": "100% (Prompt Architect & PDW 4.0)"
  "@fowler": "100% (Backend & Test Engineering)"
  "@unclebob": "100% (Tech Lead & Architectural Review)"
  "@david": "100% (Flow & Governance)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-2

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 3.0 horas (1 Story de Complexidade Nível 1).
- **Capacidade Comprometida:** 3.0 horas (100% alocada para STORY-002).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência estrita 1 Round = 1 Story).

## 2. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 20 min (@unclebob / @andrej)
- **Estação 3 (Queima Downstream - Dossiês + Validador + Testes):** 105 min (@andrej / @fowler)
- **Estação 4 (Compliance & Code Review):** 25 min (@unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 15 min (@david)

## 3. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Foco exclusivo na entrega atômica da STORY-002.
2. **Preservação Rígida de Identidades:** Rejeição imediata em code review de qualquer alteração de nome de arquivo ou handle de agente.
3. **Validação Automatizada:** Nenhum dossiê é considerado pronto sem validação verde pelo `AgentDossierValidator`.
4. **Zero Assinaturas Persistidas:** Veto a assinaturas de agentes ou rodapés institucionais no código-fonte.
