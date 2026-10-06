# ST-045: Execução Downstream da STORY-0 pelo Tech Lead com Baseline Test Runner & Fallback

## Épico: EP-010
## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

### Descrição
No início do ciclo de execução (`run_cycle`), se a story for `STORY-0`, o Tech Lead (@unclebob) executa deterministamente o scaffolding do starter via `StarterEngine.apply_starter` e roda a verificação de baseline de testes. Se os testes passarem sem erros, a Story-0 é concluída. Se houver falha, o erro é capturado e entregue ao Tech Lead (@unclebob) para autocorreção e registro de não-conformidade.

### Critérios de Aceite
1. Executor de Story-0 integrado ao `WaveOrchestrator` / `TaskLevelTddDispatcher`.
2. Execução determinística de scaffolding e verificação de testes.
3. Tratamento de erro com fallback e notificação ao Tech Lead.
4. Testes unitários simulando sucesso imediato e fallback de correção.
