---
round: 5
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

# Capacidade e Políticas de Fluxo — ROUND-5

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 3.0 horas (1 Story de Complexidade Nível 2 / Pleno).
- **Capacidade Comprometida:** 3.0 horas (100% alocada para STORY-013).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência canônica 1 Round = 1 Story).

## 2. Alocação da Equipe Multi-Estação
- **Dev Backend:** @barbara — Implementação TDD dos submódulos `project.py`, `standalone.py` e motor `ShipEngine`.
- **Reviewer:** @hoare — Auditoria de conformidade, pre-flight test enforcement e suíte de testes unitários.
- **Tech Lead:** @unclebob — Guardião arquitetural, SRF check (métodos < 30 linhas) e isolamento dos sub-apps Typer.
- **Agile Master:** @david — Governança de fluxo, validação de DoR, limites de WIP e validação de DoD.

## 3. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 15 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - Red/Green/Refactor):** 90 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 30 min (@hoare & @unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 30 min (@david)

## 4. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Apenas a STORY-013 entra na bancada de trabalho. Proibido iniciar o Round 6 antes do DoD completo do Round 5.
2. **Pre-Flight Mandatory Protection:** O `ShipEngine` não pode contornar a suíte de testes. Falha em testes = aborto imediato de promoção com exit code 1.
3. **Standalone Autonomy:** Comandos de análise (`rca`, `review`, `simplify`, `status-report`) e task devem operar com autonomia determinística sem depender de missões ativas.
4. **Parada Determinística em DoR:** A estação Upstream conclui com DoR aprovado; a implementação técnica aguarda acionamento explícito da estação de queima (`round-burn`).
