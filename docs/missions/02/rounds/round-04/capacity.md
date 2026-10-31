---
round: 4
capacity_hours: 3.0
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Developer & CLI Implementation)"
  "@hoare": "100% (Code Reviewer & Quality Gatekeeper)"
  "@unclebob": "100% (Tech Lead & Architectural Guardian)"
  "@david": "100% (Agile Master & Flow Architect)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-4

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 3.0 horas (1 Story de Complexidade Nível 2 / Pleno).
- **Capacidade Comprometida:** 3.0 horas (100% alocada para STORY-012).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência canônica 1 Round = 1 Story).

## 2. Alocação da Equipe Multi-Estação
- **Dev Backend:** @barbara — Implementação TDD do submódulo `wave_bridge.py`, interceptores Typer e despacho programático.
- **Reviewer:** @hoare — Auditoria de conformidade, repasse correto de exit codes e suíte de testes unitários.
- **Tech Lead:** @unclebob — Guardião arquitetural, SRF check (métodos < 25 linhas) e isolamento da bridge.
- **Agile Master:** @david — Governança de fluxo, validação de DoR, limites de WIP e validação de DoD.

## 3. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 15 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - Red/Green/Refactor):** 90 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 30 min (@hoare & @unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 30 min (@david)

## 4. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Apenas a STORY-012 entra na bancada de trabalho. Proibido iniciar implementações dos Rounds 5 e 6.
2. **Backward-Compatibility First:** Zero falhas de "comando não encontrado" para chamadas `bombe wave ...`; todas devem ser capturadas e educadas pedagogicamente.
3. **Preservação de Exit Code:** A ponte nunca deve alterar ou mascarar o código de saída de um comando delegado.
4. **Parada Determinística em DoR:** A estação Upstream conclui com DoR aprovado; a implementação técnica aguarda acionamento explícito da estação de queima (`round-burn`).
