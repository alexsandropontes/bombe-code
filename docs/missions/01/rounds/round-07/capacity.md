---
round: 7
capacity_hours: 4.0
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Python & Async Systems)"
  "@unclebob": "100% (Tech Lead & Architectural Review)"
  "@david": "100% (Flow & Governance)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-7

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 4.0 horas (1 Story de Complexidade Nível 3).
- **Capacidade Comprometida:** 4.0 horas (alocada integralmente para STORY-007).
- **Margem de Segurança:** Absorvida na arquitetura modular dos comandos CLI.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência estrita 1 Round = 1 Story).

## 2. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR Processo):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing Técnico & DoR Dev):** 25 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - RoundExecutionEngine + Typer CLI + Testes):** 140 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 35 min (@unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 25 min (@david)

## 3. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Foco exclusivo na entrega da STORY-007 antes de iniciar qualquer atividade do Round 8.
2. **Invariante 1 Round = 1 Story:** Vetada terminantemente a inclusão de qualquer história concorrente neste round.
3. **Tríade Determinística:** O motor e os comandos CLI devem operar estritamente de acordo com as regras de parada da Seção I.I-A da Constituição Bombe Core.
4. **Zero Assinaturas Persistidas:** Veto a metadados decorativos, rodapés institucionais ou comentários supérfluos em arquivos de código e testes.
5. **Portão de Transição:** Estação 1 concluída e aprovada; liberação formal para a Estação 2 (@unclebob).
