---
id: STORY-005
title: "QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local"
epic_id: EP-02
round: ROUND-5
agent: "@barbara"
estimation: 4h
status: ready
type: feature
layer: backend
depends_on:
  - STORY-004
tags:
  - quota-manager
  - circuit-breaker
  - failover
  - resilience
  - http-429
---

# STORY-005 — QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local

## 1. Contexto & Racional de Negócio
No ecossistema de desenvolvimento assistido por IA, a exaustão de saldo em contas de APIs cloud ou o atingimento súbito de rate limits (HTTP 429) é uma causa recorrente de quebra no fluxo de trabalho. Na conjuntura específica da MISSION-01, a chave da Z.AI encontra-se estourada. O Bombe Code deve possuir um mecanismo de resiliência ativo que detecte imediatamente a indisponibilidade de cota, registre o bloqueio em disco e comute a chamada para o cluster local sem interrupção para o desenvolvedor.

## 2. Escopo

### O que a História Cobre
- Implementação do `QuotaManager` com persistência física de estado em `~/.local/share/bombe-code/quota_state.json`.
- Implementação da lógica de Circuit Breaker com trava temporal configurável (`locked_until`, default 3 horas).
- Interceptador de respostas HTTP que captura códigos 429 / Too Many Requests ou mensagens de "insufficient balance".
- Mecanismo de failover transparente no `HybridRouter`: comutação imediata Cloud -> Local vLLM em tempo < 2.0 segundos.
- Registro de log de advertência estruturado informando o incidente de cota esgotada.

### O que a História NÃO Cobre
- Não realiza recarga automática de cartões de crédito ou interação com consoles de faturamento.
- Não remove provedores da lista de configuração; apenas desativa temporariamente via circuit breaker.

## 3. User Story
- **Como:** Engenheiro utilizando o Bombe Code em missão crítica,
- **Quero:** Que o sistema intercepte erros de cota 429 de provedores cloud e comute automaticamente para a inferência local,
- **Para que:** O ciclo TDD continue rodando sem nenhuma interrupção, mesmo quando os créditos em nuvem acabarem.

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Detecção de Erro 429):** Ao receber HTTP 429 de qualquer provedor cloud, o `QuotaManager` deve marcar o provedor como `exhausted` e calcular a janela de bloqueio em `locked_until`.
- **AC-02 (Persistência Atômica de Estado):** O estado de contingência deve ser persistido em `quota_state.json` com permissões seguras e integridade estrutural.
- **AC-03 (Chaveamento em Menos de 2s):** O tempo total entre o disparo da requisição rejeitada na cloud e o início da inferência no provedor local de contingência deve ser inferior a 2000ms.
- **AC-04 (Silenciamento de Exceção ao Usuário):** A falha de cota não deve abortar o comando CLI nem exibir stack trace ao operador, completando a entrega via contingência local.

## 5. Definition of Done (DoD)
- [ ] Código implementado em `src/bombe_code/routing/quota_manager.py` e integrado ao `HybridRouter`.
- [ ] Testes de integração simulando resposta 429 com failover automático passando em `tests/unit/test_quota_failover.py`.
- [ ] Validação do arquivo `quota_state.json` contra o schema Pydantic oficial.
- [ ] Code review aprovado por @unclebob.

## 6. Notas Técnicas & Diretrizes Arquiteturais
- Seguir o modelo de dados de cota especificado na Seção 3.2 da arquitetura.
- Assegurar que chamadas subsequentes enquanto o provedor estiver em `locked_until` nem sequer tentem conexão de rede com a cloud, despachando direto para a máquina local.

## 7. Dependências
- **Bloqueado por:** `STORY-004` (Round 4 concluído).
- **Desbloqueia:** `STORY-006` (Round 6).
