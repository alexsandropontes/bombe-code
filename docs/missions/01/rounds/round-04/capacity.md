---
round: 4
capacity_hours: 4.0
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Python & Async Systems)"
  "@unclebob": "100% (Tech Lead & Architectural Review)"
  "@david": "100% (Flow & Governance)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-4

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 4.0 horas (1 Story de Complexidade Nível 2).
- **Capacidade Comprometida:** 3.0 horas (100% alocada para STORY-004).
- **Margem de Segurança:** 1.0 hora (buffer de segurança para refactor e edge cases).
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência estrita 1 Round = 1 Story).

## 2. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR Processo):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing Técnico & DoR Dev):** 20 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - Classifier + Router + Testes):** 115 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 35 min (@unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 15 min (@david)

## 3. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Foco unívoco na entrega atômica da STORY-004 antes de qualquer preparativo para a STORY-005.
2. **TDD Estrito:** O desenvolvimento de `ComplexityClassifier` e `HybridRouter` deve seguir o ciclo RED -> GREEN -> REFACTOR com testes unitários em `tests/unit/test_complexity_router.py`.
3. **Avaliação Estática Pura:** Proibida a realização de chamadas de LLM para inferir a complexidade de slices. A análise deve ser determinística via AST e regras de escopo.
4. **Zero Assinaturas Persistidas:** Veto a metadados decorativos ou rodapés institucionais persistidos em código-fonte.
5. **Portão de Transição:** Estação 1 aprovada; liberação imediata para a Estação 2 (@unclebob).
