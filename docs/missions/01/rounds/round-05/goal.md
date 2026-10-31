---
round: 5
story_id: STORY-005
epic_id: EP-02
status: done
started_at: "2026-10-31T16:45:00"
completed_at: "2026-10-31T16:51:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-5 — STORY-005: QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local

## 1. Round Goal
Implementar o `QuotaManager` com persistência física de estado em `~/.local/share/bombe-code/quota_state.json`, lógica de Circuit Breaker com trava temporal (`locked_until`, default 3 horas) e comutação automática Cloud -> Local vLLM (< 2.0s) em caso de erro HTTP 429 ou exaustão de cota, garantindo continuidade ininterrupta do ciclo TDD sem interrupção para o desenvolvedor.

## 2. Escopo do Round
- **Story Alocada:** `STORY-005` (QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local).
- **Entregáveis Técnicos:**
  1. Modelo de dados Pydantic V2 `QuotaState` e implementação do `QuotaManager` em `src/bombe_code/routing/quota_manager.py`.
  2. Persistência atômica e segura do estado de cota em disco (`~/.local/share/bombe-code/quota_state.json`).
  3. Lógica de Circuit Breaker com marcação de provedor `exhausted` e cálculo da janela de bloqueio (`locked_until`).
  4. Interceptador de falhas integrado ao `HybridRouter` executando comutação transparente Cloud -> Local em tempo < 2.0s sem abortar a CLI.
  5. Despacho imediato para a máquina local sem requisições externas para provedores com bloqueio ativo.
  6. Suíte de testes em `tests/unit/test_quota_failover.py` cobrindo 100% dos cenários de chaveamento e resiliência.
- **Fronteira Negativa:** Não realiza recarga financeira nem altera credenciais em disco; não implementa o parser de chamadas de ferramentas (`FallbackToolParser`, escopo da STORY-006).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Schema `QuotaState` implementado e validado com Pydantic V2.
- [x] `QuotaManager` implementado em `src/bombe_code/routing/quota_manager.py` com persistência atômica em `quota_state.json`.
- [x] Circuit Breaker ativado imediatamente ao capturar HTTP 429 ou mensagem de saldo insuficiente.
- [x] Janela temporal de bloqueio (`locked_until`, default 3 horas) respeitada em chamadas subsequentes sem chamadas de rede externas.
- [x] `HybridRouter` executando failover transparente Cloud -> Local vLLM em tempo inferior a 2000ms.
- [x] Exceção de rede ou cota devidamente tratada, com log estruturado de advertência e zero abort da CLI.
- [x] Suíte de testes unitários e de integração implementada em `tests/unit/test_quota_failover.py` cobrindo AC-01 a AC-04 com 100% de sucesso.
- [x] Código em conformidade com tipagem estrita (`mypy --strict`) e sem advertências do linter ruff.
- [x] Ausência de stubs, dead code, prints de debug ou bodies vazios (`pass`, `...`) em código de produção.
- [x] Zero metadados decorativos, assinaturas de personas ou rodapés institucionais persistidos em arquivos de código.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob).
- [x] Validação formal do round executada pelo Agile Master (@david).
