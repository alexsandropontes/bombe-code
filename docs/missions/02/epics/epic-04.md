---
id: EP-04
title: "Governança de Projeto & Comandos Standalone"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-02"
tags:
  - project-governance
  - ship-engine
  - standalone-commands
  - git-flow
---

# EP-04 — Governança de Projeto & Comandos Standalone

## 1. Problema de Negócio
Além do ciclo de missões e rounds, os desenvolvedores necessitam de utilitários autônomos para tarefas pontuais de engenharia (análise de incidentes, code review avulso, simplificação de complexidade ciclomática, alternância de modos operacionais e promoção de código via Git). Esses comandos estavam dispersos, inconsistentes com a nomenclatura do Core v4 ou com documentação incompleta.

## 2. Valor de Negócio
- **Autonomia Multitarefa:** Possibilidade de rodar tarefas técnicas cirúrgicas sem exigir a abertura de uma missão completa.
- **Deploy e Promoção Seguros:** O utilitário `bombe project ship` garante que merges entre branches (`working-ia` -> `dev` -> `hml` -> `prd`) sejam protegidos por testes prévios automatizados.
- **Alinhamento Constitucional:** Paridade total com os comandos standalone definidos na Constituição do Bombe Core.

## 3. Escopo

### O que o Épico Cobre
- Sub-app `project_app` em `src/bombe_code/cli/commands/project.py`:
  - `bombe project configure`: setup interativo/declarativo de `.bombeconfig`.
  - `bombe project ship [env]`: promoção de branches Git com execução de testes de validação.
- Sub-app `standalone_app` em `src/bombe_code/cli/commands/standalone.py`:
  - `bombe mode [slice-code | vibe-code]`: comutação de modo com metadados de migração.
  - `bombe task '<desc>'`: despacho direto para especialista via Protocolo Garçom.
  - `bombe rca '<incidente>'`: Root Cause Analysis forense.
  - `bombe review [alvo]`: code review estrito e adversarial.
  - `bombe simplify [alvo]`: refatoração limpa para redução de complexidade.
  - `bombe status-report`: painel executivo geral do projeto.

### O que o Épico NÃO Cobre
- Modificação dos motores de execução de rounds (escopo do EP-02).
- Alteração direta de prompts de agentes em tempo de execução.

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-013` | Round 5 | Equalização de Comandos Standalone e Governança | @barbara | 3h |

## 5. Dependências
- **Upstream:** Conclusão do EP-01 e EP-02.
- **Downstream:** Bloqueia a homologação final do EP-05.

## 6. Critérios de Sucesso
- `bombe mode` altera o `.bombeconfig` registrando timestamp e modo de origem.
- `bombe project ship` executa a suíte de testes antes do merge e aborta se houver falhas.
- Comandos avulsos (`task`, `rca`, `review`, `simplify`, `status-report`) executam sem dependência de missão ativa.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Promoção Git de código com testes quebrados via `project ship` | Alta | Bloqueio mandatório: a promoção falha atomicamente se a suíte de testes falhar. |
| Inconsistência de paths no `.bombeconfig` ao rodar standalone | Média | Validação de diretórios com Pydantic V2 e fallback para defaults seguros. |
