---
round: 8
capacity_hours: 4.0
stories_count: 1
wip_limit: 1
team_availability:
  "@fowler": "100% (Test Engineering & Refactoring)"
  "@unclebob": "100% (Tech Lead & Architectural Review)"
  "@david": "100% (Flow & Governance)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-8

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 4.0 horas (1 Story de Complexidade Nível 2).
- **Capacidade Comprometida:** 4.0 horas (alocada integralmente para STORY-008).
- **Margem de Segurança:** 0.0h (Buffer de contingência absorvido na arquitetura de failover).
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência estrita 1 Round = 1 Story).

## 2. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR Processo):** 15 min (@david) — [Concluído/Aprovado]
- **Estação 2 (Slicing Técnico & DoR Dev):** 25 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - Implementação do Teste E2E & Validação de Failover):** 140 min (@fowler)
- **Estação 4 (Compliance & Code Review):** 35 min (@unclebob)
- **Estação 5 (Validação de DoD do Round, Homologação Final da Missão & Encerramento):** 25 min (@david)

## 3. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Foco absoluto na conclusão e homologação da STORY-008, o último round da MISSION-01.
2. **Invariante 1 Round = 1 Story:** Nenhuma outra demanda é aceita neste round.
3. **Resiliência e Zero Mocks Frágeis:** O teste E2E deve comprovar a transição real para a porta 18096 com persistência de estado em `quota_state.json`.
4. **Zero Assinaturas Persistidas:** Veto a metadados decorativos, rodapés institucionais ou comentários supérfluos em arquivos de código e testes.
5. **Portão de Transição:** Estação 1 aprovada; liberação formal imediata para a Estação 2 (@unclebob).
