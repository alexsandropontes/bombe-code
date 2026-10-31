---
round: 7
story_id: STORY-007
epic_id: EP-03
status: done
started_at: "2026-10-31T17:05:00"
completed_at: "2026-10-31T17:13:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-7 — STORY-007: Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI

## 1. Round Goal
Implementar o `RoundExecutionEngine` em `src/bombe_code/orchestration/engine.py` e os comandos CLI da tríade operacional (`round-start`, `round-full`, `round-all`) no entrypoint Typer, garantindo deterministicamente a invariante **1 Round = 1 Story**, a sincronização atômica do estado no `mission.md` e o bloqueio intransigente de avanço caso existam pendências de Definition of Done (DoD) no round anterior.

## 2. Escopo do Round
- **Story Alocada:** `STORY-007` (Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI).
- **Entregáveis Técnicos:**
  1. Implementação da classe `RoundExecutionEngine` em `src/bombe_code/orchestration/engine.py` com validação de escopo atômico (1 Round = 1 Story).
  2. Implementação e registro dos comandos CLI via Typer:
     - `round-start [round]`: Executa o Upstream da Story, valida bloqueios de DoR, cria o scaffold do round e interrompe deterministicamente na fronteira do DoR.
     - `round-full [round]`: Executa Upstream + Downstream (Queima TDD dos Slices) + Validate da história atômica daquele round, parando deterministicamente no final do round sem saltar para o próximo.
     - `round-all`: Pipeline contínuo que itera sequencialmente por todos os rounds declarados na missão ativa, parando apenas diante de quebra técnica, falha de testes ou conclusão da missão.
  3. Lançamento da exceção customizada `InvalidRoundScopeError` caso haja tentativa de registrar ou vincular mais de uma história ao mesmo round.
  4. Porteiro bloqueante de transição que impede o início de qualquer round caso o anterior possua critérios de DoD pendentes (`- [ ]`).
  5. Sincronização e persistência atômica do estado da missão em `mission.md` a cada transição de fase de round.
  6. Suíte de testes unitários abrangente em `tests/unit/test_round_execution_engine.py` cobrindo a tríade CLI, a invariante 1:1 e os bloqueios de transição.
- **Fronteira Negativa:** Não altera as regras internas de TDD por slice (Red/Green/Refactor); não remove o Round 0 (Inception Macro).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Implementação do `RoundExecutionEngine` em `src/bombe_code/orchestration/engine.py` sob tipagem estrita (`mypy --strict`).
- [x] Validação da invariante 1 Round = 1 Story com lançamento de `InvalidRoundScopeError` (AC-01).
- [x] Implementação do comando CLI `round-start [round]` com parada determinística na fronteira do DoR (AC-02).
- [x] Implementação do comando CLI `round-full [round]` com execução ponta a ponta e parada no final do round (AC-03).
- [x] Implementação do comando CLI `round-all` com orquestração iterativa contínua de rounds pendentes (AC-04).
- [x] Implementação do porteiro de verificação de DoD pendente bloqueando transições de round (AC-05).
- [x] Comandos registrados no entrypoint CLI principal (`bombe`).
- [x] Suíte de testes unitários passando em `tests/unit/test_round_execution_engine.py` com 100% de sucesso.
- [x] Atualização e sincronização atômica de `mission.md` em disco sem corrupção de frontmatter.
- [x] Ausência de stubs, dead code, prints de depuração ou bodies vazios (`pass`, `...`) em código de produção.
- [x] Zero metadados decorativos, assinaturas de personas ou rodapés institucionais persistidos em arquivos de código.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob).
- [x] Validação formal do round executada pelo Agile Master (@david).
