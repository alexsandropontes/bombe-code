---
round: 6
capacity_hours: 4.0
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Python & Async Systems)"
  "@unclebob": "100% (Tech Lead & Architectural Review)"
  "@david": "100% (Flow & Governance)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-6

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 4.0 horas (1 Story de Complexidade Nível 2).
- **Capacidade Comprometida:** 3.0 horas (alocada para STORY-006).
- **Margem de Segurança:** 1.0 hora (buffer para calibração de regex e testes de edge cases de parsing sintático).
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência estrita 1 Round = 1 Story).

## 2. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR Processo):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing Técnico & DoR Dev):** 20 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - FallbackToolParser + Regex + Edge Cases):** 120 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 35 min (@unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 20 min (@david)

## 3. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Foco unívoco na entrega atômica da STORY-006 antes de iniciar qualquer atividade do Round 7.
2. **TDD Estrito & Performance de Parsing:** Implementação orientada a testes em `tests/unit/test_fallback_tool_parser.py` assegurando latência < 5ms por chunk e regex pré-compilado em nível de classe.
3. **Resiliência Silenciosa:** O parser deve operar sob o princípio de absorção graciosa de anomalias sintáticas de LLMs menores, garantindo zero interrupções do loop de inferência.
4. **Zero Assinaturas Persistidas:** Veto a metadados decorativos, rodapés institucionais ou comentários supérfluos em arquivos de código e testes.
5. **Portão de Transição:** Estação 1 concluída e aprovada; liberação formal para a Estação 2 (@unclebob).
