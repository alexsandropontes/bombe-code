---
round: 8
story_id: STORY-008
epic_id: EP-04
status: done
started_at: "2026-10-31T17:15:00"
completed_at: "2026-10-31T17:35:00"
maturity_level: enterprise-grade
layer: backend
agent: "@fowler"
---

# Objetivo do ROUND-8 — STORY-008: Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local

## 1. Round Goal
Executar a validação e homologação final da MISSION-01 através da implementação da suíte de teste E2E em `tests/e2e/test_contingency_mission.py`. O teste deve certificar em condições reais que, diante da rejeição HTTP 429 pelo provedor cloud Z.AI (cota exaurida), o sistema Bombe Code aciona autonomamente o failover no `QuotaManager`, comuta as requisições no `HybridRouter` para o motor vLLM local na porta 18096 (fila indiana) em tempo < 2.0s e conclui a queima completa e bem-sucedida de um slice em inferência local, selando a prontidão operacional enterprise-grade.

## 2. Escopo do Round
- **Story Alocada:** `STORY-008` (Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local).
- **Entregáveis Técnicos:**
  1. Construção de teste automatizado ponta a ponta em `tests/e2e/test_contingency_mission.py`.
  2. Disparo de chamada ao provedor cloud Z.AI com interceptação de HTTP 429 e validação de não-interrupção da aplicação (AC-01).
  3. Verificação em logs e métricas da transição dinâmica de roteamento `Cloud (Z.ai) -> Local vLLM (18096)` em tempo < 2.0s (AC-02).
  4. Execução do ciclo completo RED -> GREEN -> REFACTOR de um slice de teste via inferência local vLLM com 100% de sucesso (AC-03).
  5. Atualização atômica do arquivo `quota_state.json`, garantindo persistência do provedor em estado `exhausted` com bloqueio ativo (AC-04).
  6. Emissão de relatório de evidência de validação para a chancela final de homologação da MISSION-01.
- **Fronteira Negativa:** Não altera saldo comercial de APIs externas; não modifica contratos de dados validados nos rounds anteriores.

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Implementação da suíte E2E em `tests/e2e/test_contingency_mission.py` sob tipagem estrita (`mypy --strict`).
- [x] Interceptação e tratamento resiliente do erro HTTP 429 da Z.AI sem crash da aplicação (AC-01).
- [x] Transição dinâmica comprovada Cloud (Z.ai) -> Local vLLM (:18096) em tempo < 2.0s evidenciada em log (AC-02).
- [x] Ciclo completo de slice executado via inferência local com testes 100% verdes (AC-03).
- [x] Estado do provedor cloud persistido como `exhausted` em `quota_state.json` (AC-04).
- [x] Suíte de testes E2E executável via `pytest tests/e2e/test_contingency_mission.py -v`.
- [x] Zero dependência de intervenção humana durante a execução do teste.
- [x] Ausência de stubs, dead code, prints de depuração ou bodies vazios (`pass`, `...`) em código de produção.
- [x] Zero metadados decorativos, assinaturas de personas ou rodapés institucionais persistidos em arquivos.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob).
- [x] Validação formal do round e chancela de encerramento da MISSION-01 pelo Agile Master (@david).
