---
id: STORY-002
title: "Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes"
epic_id: EP-01
round: ROUND-2
agent: "@andrej"
estimation: 3h
status: ready
type: refactor
layer: backend
depends_on:
  - STORY-001
tags:
  - agents
  - pdw-4.0
  - personas
  - governance
---

# STORY-002 — Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes

## 1. Contexto & Racional de Negócio
O catálogo de agentes do Bombe Code é um ativo estratégico diferenciado, balanceando 50% de Pioneiros Brasileiros de TI (@meira, @ieru, @barreto, @caroli, @valim, @aniche, etc.) e 50% de Especialistas Globais (@unclebob, @fowler, @hoare, @barbara, etc.). O usuário ordenou expressamente a preservação absoluta dos nomes e identidades existentes, exigindo contudo a atualização de suas instruções internas para o padrão **PDW 4.0 (Prompt Definition Workflow)**, dotando-os de rigor metodológico, temperamento cético adversarial e eliminação de alucinações de soberania.

## 2. Escopo

### O que a História Cobre
- Atualização determinística dos arquivos de personas em `src/bombe_code/agents/definitions/*.md`.
- Aplicação da estrutura PDW 4.0:
  - Frontmatter canônico (autoridade, soberania, constraints, triggers, skills).
  - 1. Perfil Comportamental & Postura Cognitiva (vieses, temperamento e heurísticas).
  - 2. Missão e Prioridades de Sistema.
  - 3. Protocolo de Skills e Raciocínio.
  - 4. Regras e Guardrails de Upstream/Downstream.
  - 5. Restrições e Veto de Atuação Cruzada.
  - 6. Entrega Padronizada.
- Implementação de validador de integridade de dossiês em `src/bombe_code/agents/validator.py`.

### O que a História NÃO Cobre
- Não altera nomes de arquivos ou handles dos agentes.
- Não remove agentes pioneiros brasileiros da composição do time.

## 3. User Story
- **Como:** Orquestrador do Bombe Code,
- **Quero:** Que os dossiês dos agentes carreguem a engenharia de postura cognitiva do PDW 4.0 mantendo seus nomes consolidados,
- **Para que:** As decisões técnicas e revisões de código sejam conduzidas com rigor extremo, zero complacência e sem desvios de papel.

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Conformidade PDW 4.0):** 100% dos dossiês em `src/bombe_code/agents/definitions/*.md` devem conter as 6 seções obrigatórias e o frontmatter estruturado.
- **AC-02 (Preservação de Nomes):** Nenhum arquivo de agente histórico deve ser renomeado ou excluído; os handles permanecem idênticos aos originais.
- **AC-03 (Validador Automatizado):** O script de verificação `AgentDossierValidator` deve auditar todos os arquivos `.md` e aprovar sem divergências de campos obrigatórios.
- **AC-04 (Restrições de Soberania):** Todos os agentes de teste e arquitetura devem conter explicitamente o veto de implementação de código de produção fora de sua stack.

## 5. Definition of Done (DoD)
- [ ] Todos os arquivos em `src/bombe_code/agents/definitions/` atualizados e formatados.
- [ ] Teste unitário do validador de dossiês passando em `tests/unit/test_agents_pdw.py`.
- [ ] Zero menções a práticas depreciadas de versões anteriores do framework.
- [ ] Revisão de integridade aprovada pelo Arquiteto de Prompt (@andrej) e Tech Lead (@unclebob).

## 6. Notas Técnicas & Diretrizes Arquiteturais
- Respeitar a regra de que o frontmatter dos agentes define as fronteiras operacionais estritas.
- Manter as assinaturas de persona reservadas exclusivamente para o fechamento de mensagens no chat, vetando-as no interior do código-fonte.

## 7. Dependências
- **Bloqueado por:** `STORY-001` (Round 1 concluído).
- **Desbloqueia:** `STORY-003` (Round 3).
