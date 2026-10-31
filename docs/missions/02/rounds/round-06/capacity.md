---
round: 6
capacity_hours: 3.0
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend & CLI Test Engineering Implementation)"
  "@hoare": "100% (Code Reviewer & Quality Gatekeeper)"
  "@unclebob": "100% (Tech Lead & Architectural Guardian)"
  "@david": "100% (Agile Master & Flow Architect)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-6

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 3.0 horas (1 Story de Complexidade Nível 2 / Pleno).
- **Capacidade Comprometida:** 3.0 horas (100% alocada para STORY-014).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência canônica 1 Round = 1 Story).

## 2. Alocação da Equipe Multi-Estação
- **Dev Backend:** @barbara — Implementação TDD da suíte E2E em `tests/e2e/test_cli_parity.py` cobrindo os 6 slices definidos pelo Tech Lead.
- **Reviewer:** @hoare — Auditoria de conformidade, verificação dos 19 entry points e gates G1-G6.
- **Tech Lead:** @unclebob — Guardião arquitetural, validação da auditoria AST e ausência de stores voláteis/mocks.
- **Agile Master:** @david — Governança de fluxo, validação de DoR, limites de WIP e validação de DoD final da missão.

## 3. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 15 min (@unclebob) — [Concluído]
- **Estação 3 (Queima TDD Downstream - Red/Green/Refactor):** 90 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 30 min (@hoare & @unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento da Missão):** 30 min (@david)

## 4. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Apenas a STORY-014 está em execução ativa até a conclusão do DoD.
2. **Real CLI Testing:** Todo teste E2E invoca a CLI via `CliRunner` contra ambientes descartáveis `tmp_path`, sem mockar a camada CLI.
3. **Paridade Canônica 1:1:** Os 19 entry points canônicos e os 7 subcomandos legados da Wave Bridge devem ser estritamente auditados.
4. **Gates G1-G6 Inegociáveis:** Nenhum stub, mock em produção ou corpo `pass` será tolerado na homologação.
