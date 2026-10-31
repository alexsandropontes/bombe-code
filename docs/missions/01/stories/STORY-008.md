---
id: STORY-008
title: "Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local"
epic_id: EP-04
round: ROUND-8
agent: "@fowler"
estimation: 4h
status: ready
type: e2e
layer: backend
depends_on:
  - STORY-007
tags:
  - e2e
  - contingency
  - zai-429
  - resilience
  - validation
---

# STORY-008 — Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local

## 1. Contexto & Racional de Negócio
Esta é a história de fechamento e validação final da MISSION-01. O ecossistema Bombe Code deve provar de ponta a ponta, em teste real de integração, que opera com resiliência total mesmo diante da indisponibilidade de cota de fornecedores externos. Como a chave Z.AI atual encontra-se com cota esgotada (situação explicitada na demanda inicial), a suíte deve exercitar uma chamada de geração de slice direcionada à Z.AI, registrar a captura do erro HTTP 429, comutar o roteamento para o motor vLLM local na porta 18096 e concluir a queima do slice com sucesso.

## 2. Escopo

### O que a História Cobre
- Implementação de teste E2E automatizado em `tests/e2e/test_contingency_mission.py`.
- Disparo de requisição para o provedor cloud Z.AI que retorna HTTP 429 real ou interceptado.
- Asserção de que o `QuotaManager` registrou o provedor como `exhausted` no `quota_state.json`.
- Asserção de que o `HybridRouter` chaveou imediatamente para o endpoint local (`http://127.0.0.1:18096/v1`).
- Execução completa do ciclo RED -> GREEN -> REFACTOR com inferência local.
- Relatório de validação emitido para auditoria final por @unclebob e @david.

### O que a História NÃO Cobre
- Não renova ou adiciona saldo à conta comercial da Z.AI.
- Não substitui as suítes de testes unitários desenvolvidas nos rounds anteriores.

## 3. User Story
- **Como:** Product Manager e Tech Lead do Bombe Code,
- **Quero:** Um teste E2E executando o cenário real de cota estourada com recuperação local autônoma,
- **Para que:** Tenhamos comprovação cabal de resiliência e estejamos aptos a homologar e encerrar a MISSION-01 com selo Enterprise-Grade.

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Simulação/Captura 429):** A chamada rejeitada com HTTP 429 pelo provedor cloud deve ser interceptada sem crash da aplicação.
- **AC-02 (Transição de Roteamento em Tempo Real):** O log de execução deve evidenciar a transição `Cloud (Z.ai) -> Local vLLM (18096)` em tempo < 2.0s.
- **AC-03 (Execução Local Green):** O slice sob teste deve ser implementado, os testes associados executados e o resultado final validado como 100% verde (passed).
- **AC-04 (Persistência de Estado):** O arquivo `quota_state.json` deve registrar o provedor cloud em estado `exhausted` e `locked_until` ativo.

## 5. Definition of Done (DoD)
- [ ] Teste E2E implementado em `tests/e2e/test_contingency_mission.py` e passando na suíte de testes.
- [ ] Relatório de evidência gerado com sucesso.
- [ ] Zero dependência de intervenção humana durante a execução do teste.
- [ ] Aprovação formal de encerramento do Round 8 e da MISSION-01 por @unclebob e @david.

## 6. Notas Técnicas & Diretrizes Arquiteturais
- Seguir as diretrizes de teste descritas na Seção 6.3 da arquitetura.
- Teste deve ser executável via `pytest tests/e2e/test_contingency_mission.py -v`.

## 7. Dependências
- **Bloqueado por:** `STORY-007` (Round 7 concluído).
- **Desbloqueia:** Homologação final da MISSION-01.
