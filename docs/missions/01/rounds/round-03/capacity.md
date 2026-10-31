---
round: 3
capacity_hours: 4.0
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Python & Async Systems)"
  "@unclebob": "100% (Tech Lead & Architectural Review)"
  "@david": "100% (Flow & Governance)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-3

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 4.0 horas (1 Story de Complexidade Nível 2).
- **Capacidade Comprometida:** 4.0 horas (100% alocada para STORY-003).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência estrita 1 Round = 1 Story).

## 2. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 20 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - Protocolo + Adapter + Fila Indiana + Testes):** 155 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 35 min (@unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 15 min (@david)

## 3. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Foco unívoco na entrega atômica da STORY-003 antes de tocar em qualquer elemento do Round 4.
2. **TDD Estrito:** O desenvolvimento dos adapters e fila indiana deve seguir estritamente o ciclo RED -> GREEN -> REFACTOR com testes assíncronos.
3. **Respeito Incondicional à Fila Indiana:** O adapter local não pode permitir concorrência de múltiplos modelos na porta 18096 sob pena de violação arquitetural de VRAM.
4. **Zero Assinaturas Persistidas:** Veto a metadados decorativos ou rodapés institucionais persistidos em código-fonte.
5. **Parada Determinística em DoR:** Estação 1 concluída; a esteira aguarda o despacho da Estação 2 (Slicing técnico).
