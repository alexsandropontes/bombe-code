---
id: EP-04
title: "Validação Real End-to-End & Resiliência"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-01"
tags:
  - e2e
  - contingency
  - resilience
  - validation
---

# EP-04 — Validação Real End-to-End & Resiliência

## 1. Problema de Negócio
Sistemas autônomos frequentemente falham ao transitar da teoria para a prática quando expostos a condições adversas do mundo real. O usuário relatou explicitamente que a chave da API Z.AI configurada no ambiente encontra-se atualmente com a cota exaurida (HTTP 429). Se o sistema não for homologado em um teste fim a fim sob essas circunstâncias exatas, não há garantia de que o Bombe Code suportará a operação diária sem intervenção humana.

## 2. Valor de Negócio
- **Garantia de Entrega Production-Ready:** Comprovação empírica de que a arquitetura híbrida sustenta a execução autônoma de software mesmo diante do pior cenário de infraestrutura externa.
- **Evidência Documental Auditável:** Relatório forense completo demonstrando a captura do erro 429, comutação de provedor e queima de testes em ambiente local.
- **Homologação da MISSION-01:** Conclusão formal do ciclo de modernização do Bombe Code v4 sob os mais altos padrões de qualidade enterprise.

## 3. Escopo

### O que o Épico Cobre
- Construção de suíte de testes de integração e contrato ponta a ponta (`tests/e2e/test_contingency_mission.py`).
- Simulação de execução de missão com provedor cloud Z.AI retornando HTTP 429.
- Verificação do registro estruturado de incidente no `QuotaManager` (`quota_state.json`).
- Execução real do ciclo TDD (Red -> Green -> Refactor) para um slice utilizando o endpoint vLLM local (`18096`).
- Validação final do DoD completo da missão pelo Tech Lead (@unclebob) e Agile Master (@david).

### O que o Épico NÃO Cobre
- Não renova ou adiciona saldo à conta comercial da Z.AI.
- Não substitui as suítes de testes unitários desenvolvidas nos rounds anteriores.

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-008` | Round 8 | Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local | @fowler | 4h |

## 5. Dependências
- **Upstream:** Épicos EP-01, EP-02 e EP-03 100% integrados e validados.
- **Downstream:** Homologação e encerramento da `MISSION-01`.

## 6. Critérios de Sucesso
- Teste E2E executa sem falhas não tratadas em ambiente de CI/terminal limpo.
- Log de auditoria evidencia o chaveamento Cloud -> Local em tempo < 2.0s.
- O slice teste passa pelo ciclo completo RED -> GREEN -> REFACTOR com inferência gerada pelo modelo local.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Instância vLLM local não estar em execução no momento do teste | Alta | Teste automatizado realiza verificação prévia do endpoint `:18096` e emite diagnóstico claro caso o daemon local precise ser acionado. |
| Variação de latência na inferência local afetar timeouts de teste | Média | Configuração de timeouts adaptativos e assíncronos no cliente HTTP do teste E2E. |
