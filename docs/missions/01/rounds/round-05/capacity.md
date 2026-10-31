---
round: 5
capacity_hours: 4.0
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Python & Async Systems)"
  "@unclebob": "100% (Tech Lead & Architectural Review)"
  "@david": "100% (Flow & Governance)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-5

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 4.0 horas (1 Story de Complexidade Nível 3).
- **Capacidade Comprometida:** 3.5 horas (alocada para STORY-005).
- **Margem de Segurança:** 0.5 hora (buffer para calibração de timeouts e testes assíncronos).
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência estrita 1 Round = 1 Story).

## 2. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR Processo):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing Técnico & DoR Dev):** 25 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - QuotaManager + Router Failover + Testes):** 135 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 45 min (@unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 20 min (@david)

## 3. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Foco unívoco na entrega atômica da STORY-005 antes de qualquer ação preparatória para a STORY-006.
2. **TDD Estrito & Resiliência Silenciosa:** O failover deve ser desenvolvido orientado a testes em `tests/unit/test_quota_failover.py` com garantia de captura graciosa de exceções HTTP.
3. **Respeito à Fila Indiana Local:** As requisições desviadas para o cluster vLLM local devem obrigatoriamente honrar a serialização via lock de concorrência definida na STORY-003.
4. **Zero Assinaturas Persistidas:** Veto a metadados decorativos ou rodapés institucionais persistidos em código-fonte.
5. **Portão de Transição:** Estação 1 concluída; liberação imediata para a Estação 2 (@unclebob).
