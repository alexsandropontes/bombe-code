---
id: EP-01
title: "Gestão de Ciclo de Vida de Missões"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-02"
tags:
  - mission-lifecycle
  - atomic-gatekeeper
  - cli-dispatch
  - docs-scaffold
---

# EP-01 — Gestão de Ciclo de Vida de Missões

## 1. Problema de Negócio
No modelo preliminar, o Bombe Code não possuía uma gestão estrita do ciclo de vida de missões. Desenvolvedores podiam inicializar novas demandas sem formalizar o encerramento da anterior, gerando sobreposição de pastas em `docs/missions/`, concorrência indesejada em branches Git e violação do princípio de foco de fluxo (WIP = 1). Além disso, não existia uma interface canônica de terminal para inspecionar o progresso consolidado da missão ou arquivá-la com validação de DoD.

## 2. Valor de Negócio
- **Disciplina Operacional (WIP = 1):** Garante que apenas uma missão aberta exista por vez, forçando a conclusão do trabalho em andamento antes do início de novas demandas.
- **Rastreabilidade Documental SSOT:** O filesystem em `docs/missions/NN/` torna-se a fonte única da verdade, com scaffold automatizado e histórico preservado.
- **Transparência Executiva:** O comando `bombe mission status` fornece visão instantânea do kanban da missão ativa para humanos e IAs.

## 3. Escopo

### O que o Épico Cobre
- Criação do sub-app Typer `mission_app` em `src/bombe_code/cli/commands/mission.py` integrado à raiz `bombe`.
- Implementação de `bombe mission new '<demanda>'` com invocação mandatória de `assert_no_open_mission()`.
- Geração determinística do scaffold da missão (`mission.md`, subpastas `prd/`, `architecture/`, `epics/`, `stories/`, `rounds/`).
- Implementação de `bombe mission status` com renderização de tabela Rich do progresso de rounds.
- Implementação de `bombe mission end` com trava de validação de DoD geral.

### O que o Épico NÃO Cobre
- Execução individual de queima de rounds ou slices (escopo do EP-02).
- Interceptação de comandos legados `bombe wave` (escopo do EP-03).
- Configuração de credenciais de provedores ou `.bombeconfig` (escopo do EP-04).

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-009` | Round 1 | Porteiro Atômico e Lifecycle de Missões | @barbara | 3h |

## 5. Dependências
- **Upstream:** Aprovação do Round 0 da MISSION-02 (PRD, Arquitetura e Sequenciador).
- **Downstream:** Bloqueia a execução do EP-02 (os comandos de rounds dependem da missão inicializada e gerenciada).

## 6. Critérios de Sucesso
- Tentativa de executar `bombe mission new` existindo missão com status `open` ou `active` retorna exit code 1 e mensagem explicativa.
- Em caminho feliz, `bombe mission new` gera a estrutura de diretórios e o arquivo `mission.md` íntegro.
- `bombe mission status` exibe o kanban da missão em console Rich sem erros de renderização.
- `bombe mission end` bloqueia se houver rounds com pendências de DoD.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Concorrência de processos criando missões no mesmo milissegundo | Média | Verificação atômica de diretórios no filesystem com tratamento de exceções de I/O. |
| Usuário ficar bloqueado sem conseguir fechar missão corrompida | Média | Disponibilização do parâmetro de emergência `--force-abort` no encerramento. |
