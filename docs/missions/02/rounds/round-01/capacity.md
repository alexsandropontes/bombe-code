---
round: 1
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

# Capacidade e Políticas de Fluxo — ROUND-1

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 3.0 horas (1 Story de Complexidade Nível 2 / Pleno).
- **Capacidade Comprometida:** 3.0 horas (100% alocada para STORY-009).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência canônica 1 Round = 1 Story).

## 2. Alocação da Equipe Multi-Estação
- **Dev Backend:** @barbara — Implementação TDD dos comandos Typer, engine e contratos de missão.
- **Reviewer:** @hoare — Verificação estrita de cobertura, linter, type hints e ausência de stubs.
- **Tech Lead:** @unclebob — Guardião arquitetural, SRF check e revisão estrutural de código.
- **Agile Master:** @david — Governança de fluxo, limites de WIP e validação de DoD.

## 3. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 15 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - Red/Green/Refactor):** 90 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 30 min (@hoare & @unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 30 min (@david)

## 4. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Apenas a STORY-009 entra na bancada de trabalho. Proibido iniciar implementações do Round 2 antes do DoD 100% aprovado do Round 1.
2. **TDD Estrito (Zero Mocks em Produção):** Código de produção em `src/bombe_code/` requer teste prévio falhante (RED) e fixtures baseadas em filesystem real via `tmp_path`.
3. **Parada Determinística em DoR:** O Upstream Station conclui aprovado; a implementação só inicia com o acionamento explícito da estação de queima (`round-burn`).
