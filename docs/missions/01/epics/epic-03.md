---
id: EP-03
title: "Esteira Kanban 1 Round = 1 Story & Tríade CLI"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-01"
tags:
  - kanban
  - 1-round-1-story
  - cli-triad
  - execution-engine
---

# EP-03 — Esteira Kanban 1 Round = 1 Story & Tríade CLI

## 1. Problema de Negócio
No modelo anterior do framework, rounds agrupavam múltiplas histórias simultaneamente. Isso sobrecarregava as janelas de contexto dos agentes auditores (@unclebob e @hoare), elevava o risco de retrabalho cruzado e gerava lentidão para validar o incremento de produto. Adicionalmente, a falta de comandos CLI com granularidade de controle gerava paradas desnecessárias ou perda de governança sobre a queima.

## 2. Valor de Negócio
- **Cadência Ágil Granular:** Cada Round entrega e valida exatamente 1 Story, estabelecendo fluxo contínuo e visibilidade transparente no quadro Kanban.
- **Code Review Preciso:** @unclebob inspeciona exclusivamente o diff unitário da história em fechamento, reduzindo o tempo de review em 40% e aumentando a detecção de defeitos.
- **Governança via Tríade CLI:** Três modos operacionais bem definidos (`round-start`, `round-full`, `round-all`) que dão total previsibilidade para desenvolvimento manual ou pipelines autônomos.

## 3. Escopo

### O que o Épico Cobre
- Refatoração do motor de execução `RoundExecutionEngine` para a política **1 Round = 1 Story**.
- Implementação dos comandos CLI via Typer:
  - `round-start [round]`: Executa o Upstream da Story, valida DOR e para antes da queima.
  - `round-full [round]`: Executa Upstream + Downstream TDD + Validação do round especificado, parando deterministicamente no final.
  - `round-all`: Pipeline contínuo que itera sequencialmente pelos rounds da missão ativa até a conclusão do último round pendente.
- Atualização determinística do frontmatter e tabelas de status em `mission.md` e nos arquivos de round.

### O que o Épico NÃO Cobre
- Não modifica as regras de fatiamento vertical em Slices dentro da história (Backend TDD + Frontend Construction).
- Não gerencia a camada física de inferência de LLMs (escopo do EP-02).

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-007` | Round 7 | Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI | @barbara | 4h |

## 5. Dependências
- **Upstream:** Épicos EP-01 e EP-02 homologados.
- **Downstream:** Pré-requisito para o teste E2E final em cenário de contingência (EP-04).

## 6. Critérios de Sucesso
- Tentativa de associar mais de uma história ativa ao mesmo round é rejeitada com erro de governança.
- Cada comando da tríade CLI executa estritamente a política definida na Constituição.
- O quadro Kanban reflete com precisão o estado atômico de cada história concluída.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Operador tentar pular a ordem sequencial prioritária dos rounds | Média | Emissão de confirmação substantiva bloqueante no CLI caso o round solicitado não seja o próximo da fila. |
| Sobrecarga de I/O em atualizações frequentes de arquivos de estado | Baixa | Escrita atômica em disco utilizando serializadores otimizados em Python nativo. |
