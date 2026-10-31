---
id: STORY-007
title: "Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI"
epic_id: EP-03
round: ROUND-7
agent: "@barbara"
estimation: 4h
status: ready
type: feature
layer: backend
depends_on:
  - STORY-006
tags:
  - kanban
  - cli
  - execution-engine
  - round-start
  - round-full
  - round-all
---

# STORY-007 — Motor de Execução Kanban (1 Round = 1 Story) e Tríade CLI

## 1. Contexto & Racional de Negócio
A grande simplificação operacional do Bombe Code é a consolidação da regra **1 Round = 1 Story**. O motor de execução precisa garantir de forma determinística que um round contenha exatamente uma história ativa no quadro Kanban, permitindo revisões de escopo atômico pelo @unclebob. Além disso, os operadores necessitam da tríade completa de comandos CLI (`round-start`, `round-full`, `round-all`) com controle absoluto de parada e validação de Definition of Ready (DoR) e Definition of Done (DoD).

## 2. Escopo

### O que a História Cobre
- Implementação do `RoundExecutionEngine` em `src/bombe_code/orchestration/engine.py`.
- Implementação dos comandos CLI via Typer:
  - `round-start [round]`: Inicializa o Upstream, valida DoR, cria scaffold do round e para.
  - `round-full [round]`: Executa Upstream + Downstream (Queima TDD dos slices) + Validate da história, parando no final do round.
  - `round-all`: Orquestra o avanço contínuo sequencial do primeiro ao último round pendente da missão.
- Validação estrita da invariante: 1 Round possui exatamente 1 Story vinculada.
- Bloqueio determinístico de transição de round caso o anterior possua pendências de DoD.

### O que a História NÃO Cobre
- Não altera a lógica interna de execução TDD slice a slice (permanece Red/Green/Refactor).
- Não remove a exigência de Round 0 para a Inception Macro.

## 3. User Story
- **Como:** Desenvolvedor ou agente autônomo operando o Bombe Code,
- **Quero:** Comandos CLI determinísticos e uma esteira Kanban orientada a 1 Round = 1 Story,
- **Para que:** Minhas entregas sejam incrementais, fáceis de auditar e livres de sobrecarga de contexto.

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Invariante 1:1):** O motor de execução deve rejeitar qualquer tentativa de registrar mais de uma história no mesmo round com erro `InvalidRoundScopeError`.
- **AC-02 (Comando round-start):** Deve criar os artefatos do round, atualizar o status da story para `in_progress` e interromper a execução deterministamente na fronteira do DoR.
- **AC-03 (Comando round-full):** Deve executar a queima de todos os slices daquela story, acionar a subfase de validate do @unclebob e finalizar o round sem avançar para o próximo.
- **AC-04 (Comando round-all):** Deve iterar sequencialmente por todos os rounds da missão ativa, parando apenas diante de falha de teste, erro técnico ou conclusão da missão.
- **AC-05 (Bloqueio por Pendência de DoD):** Nenhuma execução de round novo pode iniciar se o round anterior contiver itens `- [ ]` não concluídos.

## 5. Definition of Done (DoD)
- [ ] Código implementado em `src/bombe_code/orchestration/` com tipagem estrita e testes abrangentes.
- [ ] Suíte de testes da tríade CLI passando em `tests/unit/test_round_execution_engine.py`.
- [ ] Comandos registrados e disponíveis no entrypoint CLI principal (`bombe`).
- [ ] Code review aprovado por @unclebob.

## 6. Notas Técnicas & Diretrizes Arquiteturais
- Seguir fielmente a Seção 4.5 da arquitetura do projeto e a Seção I.I-A da Constituição Bombe Core.
- O motor de execução deve manter o arquivo `mission.md` sincronizado em disco a cada transição de fase de round.

## 7. Dependências
- **Bloqueado por:** `STORY-006` (Round 6 concluído).
- **Desbloqueia:** `STORY-008` (Round 8).
