---
round: 4
story_id: STORY-004
epic_id: EP-02
status: done
started_at: "2026-10-31T16:35:00"
completed_at: "2026-10-31T16:41:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-4 — STORY-004: Classificador de Complexidade de Slice e Roteador Híbrido Dinâmico

## 1. Round Goal
Implementar o classificador de complexidade estático (`ComplexityClassifier`) validado via schema Pydantic V2 (`ComplexityAnalysis`) e o roteador híbrido dinâmico (`HybridRouter`), garantindo avaliação determinística de notas 1 (Júnior/Local), 2 (Pleno/Local Qwen 9B) e 3 (Sênior/Cloud ou Local Sênior) com justificativas técnicas auditáveis e zero latência de rede externa para a análise de código.

## 2. Escopo do Round
- **Story Alocada:** `STORY-004` (Classificador de Complexidade de Slice e Roteador Híbrido Dinâmico).
- **Entregáveis Técnicos:**
  1. Modelo de dados Pydantic V2 `ComplexityAnalysis` com validação de campos `score` (1..3), `reasons` (min_length=1) e `recommended_tier` ("junior"|"pleno"|"senior") em `src/bombe_code/routing/classifier.py`.
  2. Implementação do `ComplexityClassifier` com heurísticas de avaliação estática (AST / análise de caminhos e linhas) sem invocar chamadas de rede externas.
  3. Implementação do `HybridRouter` em `src/bombe_code/routing/router.py` aplicando a matriz de decisão entre provedores locais e cloud.
  4. Suíte de testes unitários em `tests/unit/test_complexity_router.py` cobrindo 100% dos cenários de classificação e despacho.
- **Fronteira Negativa:** Não implementar o circuit breaker de cotas 429 (`QuotaManager`, escopo da STORY-005) nem o parser resiliente de tool calls (`FallbackToolParser`, escopo da STORY-006).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Schema `ComplexityAnalysis` implementado com Pydantic V2 contendo `score` (int 1..3), `reasons` (list[str]) e `recommended_tier` (str).
- [x] `ComplexityClassifier` implementado em `src/bombe_code/routing/classifier.py` classificando corretamente Slices nos Tiers 1, 2 e 3 com base em regras estáticas.
- [x] Justificativa técnica auditável presente em 100% das saídas do classificador no campo `reasons`.
- [x] `HybridRouter` implementado em `src/bombe_code/routing/router.py` despachando para provedores conforme a matriz de complexidade.
- [x] Ausência de dependências de rede ou chamadas de LLM para avaliar a complexidade da tarefa (execução estática pura).
- [x] Suíte de testes unitários implementada em `tests/unit/test_complexity_router.py` cobrindo AC-01 a AC-04 com 100% de sucesso.
- [x] Código em conformidade com tipagem estrita (`mypy --strict`) e sem advertências do linter ruff.
- [x] Ausência de stubs, dead code, prints de debug ou bodies vazios (`pass`, `...`) em código de produção.
- [x] Zero metadados decorativos, assinaturas de personas ou rodapés institucionais persistidos em arquivos de código.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob).
- [x] Validação formal do round executada pelo Agile Master (@david).
