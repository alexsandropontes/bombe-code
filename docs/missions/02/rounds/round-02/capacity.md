---
round: 2
capacity_hours: 4.0
stories_count: 1
wip_limit: 1
team_availability:
  "@barbara": "100% (Backend Developer & CLI Implementation)"
  "@hoare": "100% (Code Reviewer & Quality Gatekeeper)"
  "@unclebob": "100% (Tech Lead & Architectural Guardian)"
  "@david": "100% (Agile Master & Flow Architect)"
status: committed
---

# Capacidade e Políticas de Fluxo — ROUND-2

## 1. Métricas de Capacidade
- **Capacidade Nominal Total:** 4.0 horas (1 Story de Complexidade Nível 3 / Sênior).
- **Capacidade Comprometida:** 4.0 horas (100% alocada para STORY-010).
- **Capacidade Remanescente:** 0.0 horas.
- **Limite de WIP (Work In Progress):** **1 Story** (Cadência canônica 1 Round = 1 Story).

## 2. Alocação da Equipe Multi-Estação
- **Dev Backend:** @barbara — Implementação TDD dos comandos Typer `round`, engine de orquestração e contratos.
- **Reviewer:** @hoare — Validação rigorosa de cobertura de testes, tipagem Pydantic/Mypy, linter Ruff e ausência de stubs.
- **Tech Lead:** @unclebob — Guardião arquitetural, SRF check (métodos < 30 linhas) e revisão do fatiamento em slices.
- **Agile Master:** @david — Governança de fluxo, garantia do gate DoR, limites de WIP e validação de DoD.

## 3. Distribuição Temporal Estimada (Esteira do Round)
- **Estação 1 (Upstream / Planning & DoR):** 15 min (@david) — [Concluído]
- **Estação 2 (Slicing & Design Técnico):** 20 min (@unclebob)
- **Estação 3 (Queima TDD Downstream - Red/Green/Refactor):** 120 min (@barbara)
- **Estação 4 (Compliance & Code Review):** 45 min (@hoare & @unclebob)
- **Estação 5 (Validação de DoD do Round & Encerramento):** 40 min (@david)

## 4. Políticas Explícitas de Fluxo
1. **Stop Starting, Start Finishing:** Apenas a STORY-010 entra na bancada de trabalho. Proibido adiantar desenvolvimento dos Rounds 3 e 4.
2. **TDD Estrito (Zero Mocks em Produção):** Implementação guiada por testes (RED primeiro). Mocks e stubs são sumariamente vetados do código de produção em `src/bombe_code/`.
3. **Parada Determinística em DoR:** O Upstream Station conclui aprovado; a implementação só inicia com o acionamento explícito da estação de queima (`round-burn`).
