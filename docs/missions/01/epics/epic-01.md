---
id: EP-01
title: "Equalização Core v4 e PDW 4.0"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-01"
tags:
  - core-v4
  - pdw-4.0
  - legacy-parity
  - configuration
---

# EP-01 — Equalização Core v4 e PDW 4.0

## 1. Problema de Negócio
O Bombe Code nasceu sob o modo legado `tdd-code`, que foi integralmente descontinuado no ecossistema Bombe Core v4. O repositório possui configurações obsoletas em `.bombeconfig`, scripts de runtime defasados e dossiês de agentes que não atendem às especificações modernas de engenharia comportamental do PDW 4.0. Isso impede o alinhamento de governança, causa falhas na esteira e expõe o sistema a alucinações de escopo e quebra de posturas cognitivas.

## 2. Valor de Negócio
- **Conformidade Operacional:** Alinha 100% da governança do Bombe Code ao padrão de mercado do Bombe Core v4.
- **Preservação do Patrimônio Histórico:** Atualiza a postura comportamental e os limites de soberania dos agentes (50% Pioneiros Brasileiros de TI e 50% Mundiais) mantendo seus nomes e identidades intactos.
- **Fundação Técnica Segura:** Fornece a base estável em `slice-code` necessária para que o orquestrador híbrido e a nova esteira Kanban possam operar com segurança determinística.

## 3. Escopo

### O que o Épico Cobre
- Migração formal do `.bombeconfig` para `mode: slice-code` com rastreabilidade histórica (`mode_origin: tdd-code`).
- Remoção de qualquer resquício ou checagem de código acoplada ao modo `tdd-code`.
- Refatoração integral dos arquivos de definição de agentes em `.agents/agents/*.md` para o formato PDW 4.0 (frontmatter canônico, 6 pilares cognitivos, viés operacional, guardrails de soberania e selos de encerramento).
- Validação determinística da inicialização do runtime sem alertas de inconsistência.

### O que o Épico NÃO Cobre
- Não altera os nomes ou apelidos consolidados dos agentes históricos do Bombe Code.
- Não implementa lógica de inferência de LLM ou adaptadores de provedores de rede (escopo do EP-02).
- Não altera a árvore de diretórios de código produtivo em `src/bombe_code/`.

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-001` | Round 1 | Migração de Configuração e Runtime Slice-Code | @fowler | 2h |
| `STORY-002` | Round 2 | Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes | @andrej | 3h |

## 5. Dependências
- **Upstream:** Aprovação formal do Round 0 (PRD, Arquitetura e Sequenciador).
- **Downstream:** Bloqueia a execução do Épico EP-02 (o roteador e os adapters dependem de runtime e agentes equalizados).

## 6. Critérios de Sucesso
- Comando de verificação de ambiente executa com sucesso e reporta `mode: slice-code`.
- 100% dos dossiês de agentes contêm os 6 pilares cognitivos do PDW 4.0 e passam por linter estrutural.
- Zero advertências de governança na carga do runtime.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Quebra de scripts existentes que procuravam por `mode: tdd-code` | Alta | Adicionar chave de rastreabilidade `mode_origin: tdd-code` no `.bombeconfig` e tratar compatibilidade retroativa com aviso de depreciação. |
| Perda de identidade ou traços dos agentes originais do Bombe Code | Média | Preservar integralmente o nome do arquivo, apelido e especialidade histórica, atualizando apenas a mecânica de guardrails e temperamento cognitivo. |
