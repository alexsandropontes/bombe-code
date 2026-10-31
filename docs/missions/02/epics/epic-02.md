---
id: EP-02
title: "Tríade de Execução de Rounds e Slices"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-02"
tags:
  - round-engine
  - slice-code
  - triage-execution
  - tdd
---

# EP-02 — Tríade de Execução de Rounds e Slices

## 1. Problema de Negócio
A esteira de execução prévia operava em blocos de tarefas rígidos e parava com frequência para confirmações vazias de cortesia ("Deseja prosseguir?"). Além disso, não existia uma distinção clara entre condução manual (necessária quando o desenvolvedor precisa auditar o fatiamento antes de codar) e condução autônoma (necessária para queima desatendida de pipeline contínuo), violando o protocolo da Tríade de Execução do Bombe Core v4.

## 2. Valor de Negócio
- **Autonomia Operacional Escolhida:** O desenvolvedor escolhe o nível de controle da esteira: Manual com parada na DoR (`round start`), Semi-Auto por história (`round full`) ou Contínuo hands-free (`round all`).
- **Eliminação de Confirmações Vazias:** A esteira contínua avança de forma desatendida, parando apenas diante de falhas técnicas ou impasses de negócio.
- **Garantia de Qualidade TDD:** Cada round encapsula estritamente 1 Story, fatiada em Slices verticais executados com TDD rigoroso.

## 3. Escopo

### O que o Épico Cobre
- Sub-app Typer `round_app` em `src/bombe_code/cli/commands/round.py`.
- Comandos manuais: `bombe round start [N]` (com parada obrigatória na DoR), `bombe round burn [N]`, `bombe round review [N]`, `bombe round validate [N]`.
- Comandos autônomos: `bombe round full [N]` (upstream -> burn -> review -> validate da story com parada ao final) e `bombe round all` (loop contínuo para todos os rounds pendentes).
- Comando de inspeção: `bombe round status`.
- Integração com `RoundExecutionEngine` e modelos de dados `RoundState` e `SliceState`.

### O que o Épico NÃO Cobre
- Interceptação de comandos legados `bombe wave` (escopo do EP-03).
- Promoção de código para branches de produção via Git Ship (escopo do EP-04).

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-010` | Round 2 | Engine de Rounds Manuais com DoR Gate | @barbara | 4h |
| `STORY-011` | Round 3 | Engine de Rounds Autônomos: Full & All | @barbara | 4h |

## 5. Dependências
- **Upstream:** Conclusão da `STORY-009` (EP-01) para ter o lifecycle de missão operacional.
- **Downstream:** Bloqueia a `STORY-012` (a Wave Bridge redireciona para as primitivas construídas neste épico).

## 6. Critérios de Sucesso
- `bombe round start` gera os artefatos de upstream da story e para deterministicamente na DoR sem queimar código.
- `bombe round full [N]` processa a story completa e encerra com exit code 0.
- `bombe round all` processa sequencialmente todos os rounds pendentes sem solicitar input no stdin.
- Qualquer falha de teste em `round burn` interrompe o pipeline e impede o avanço.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Loop infinito em execuções desatendidas (`round all`) | Alta | Injeção de timeout global e verificação de idempotência em cada round. |
| Violação do gate de DoR em execuções manuais | Alta | Asserção estrita no engine que bloqueia `round burn` se `dor_ready` for falso. |
