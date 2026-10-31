---
id: STORY-004
title: "Classificador de Complexidade de Slice e Roteador Híbrido Dinâmico"
epic_id: EP-02
round: ROUND-4
agent: "@barbara"
estimation: 3h
status: done
type: feature
layer: backend
depends_on:
  - STORY-003
tags:
  - router
  - classifier
  - complexity
  - hybrid-orchestration
---

# STORY-004 — Classificador de Complexidade de Slice e Roteador Híbrido Dinâmico

## 1. Contexto & Racional de Negócio
Para equilibrar custo financeiro, velocidade de entrega e acurácia de código, o harness necessita de uma inteligência capaz de avaliar o escopo de cada tarefa antes de despachá-la. A estratégia arquitetural aprovada preconiza que tarefas rotineiras e puramente mecânicas sejam atribuídas a modelos locais eficientes, reservando requisições pagas em nuvem apenas para refatorações estruturais ou contratos críticos de alta complexidade.

## 2. Escopo

### O que a História Cobre
- Implementação do `ComplexityClassifier` em `src/bombe_code/routing/classifier.py` emitindo nota 1, 2 ou 3 com justificativas auditáveis.
- Modelagem do schema `ComplexityAnalysis` validado via Pydantic V2.
- Implementação do `HybridRouter` em `src/bombe_code/routing/router.py` aplicando a matriz de decisão entre provedores locais e cloud.
- Integração do roteador com a configuração unificada de provedores (`providers.yaml`).
- Testes unitários para múltiplos cenários de complexidade de código.

### O que a História NÃO Cobre
- Não implementa o circuit breaker para falhas de cota 429 (escopo da STORY-005).
- Não implementa parsing de markdown de ferramentas corrompidas (escopo da STORY-006).

## 3. User Story
- **Como:** Orquestrador de tarefas do Bombe Code,
- **Quero:** Que cada slice seja avaliado deterministamente quanto à sua complexidade e despachado para o provedor de IA mais adequado,
- **Para que:** A execução seja rápida, barata e confiável, sem desperdício de tokens cloud em tarefas simples.

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Classificação Nota 1):** Slices contendo apenas testes unitários simples, documentação ou arquivos isolados (< 50 linhas) devem receber nota 1 (Júnior) e serem atribuídos ao cluster local.
- **AC-02 (Classificação Nota 2):** Slices envolvendo criação de CRUDs, múltiplos arquivos ou integração de módulos (50 a 200 linhas) devem receber nota 2 (Pleno) com target prioritário no motor local Qwen 9B.
- **AC-03 (Classificação Nota 3):** Slices que tocam protocolos fundamentais de orquestração, segurança ou concorrência (> 200 linhas) devem receber nota 3 (Sênior) com target prioritário em provedores cloud ou modelo local sênior.
- **AC-04 (Justificativas Auditáveis):** O objeto de análise retornado deve conter no mínimo uma justificativa técnica clara no campo `reasons`.

## 5. Slices Verticais de Implementação

### SLICE-01: Modelo ComplexityAnalysis (Pydantic V2) e ComplexityClassifier Estático
- **Tipo:** Backend (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Arquivo de Teste:** `tests/unit/test_complexity_router.py`
- **Arquivo de Produção:** `src/bombe_code/routing/classifier.py`
- **Escopo:**
  - Schema Pydantic V2 `ComplexityAnalysis` com validações de `score` (1..3), `reasons` (min_length=1) e `recommended_tier` ("junior" | "pleno" | "senior").
  - Classe `ComplexityClassifier` com método `evaluate_slice(slice_spec: dict[str, Any]) -> ComplexityAnalysis`.
  - Heurísticas estáticas determinísticas baseadas em palavras-chave em `affected_files`, volume de linhas (`< 50`, `50-200`, `> 200`) e semântica de `scope`.
  - Zero dependências de I/O de rede ou chamadas externas de LLM.

### SLICE-02: HybridRouter e Matriz de Decisão Local vs Cloud
- **Tipo:** Backend (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Arquivo de Teste:** `tests/unit/test_complexity_router.py`
- **Arquivo de Produção:** `src/bombe_code/routing/router.py`
- **Escopo:**
  - Modelo `RoutingDecision` estruturado com `provider_name`, `model_name`, `tier`, `is_fallback` e `reason`.
  - Classe `HybridRouter` consumindo `ComplexityAnalysis` e aplicando a matriz arquitetural de despacho:
    - Score 1 (Júnior) -> `local_vllm` (`lfm-1.7b` ou `gemma-4b`).
    - Score 2 (Pleno) -> `local_vllm` (`qwen-9b`).
    - Score 3 (Sênior) -> Provedores cloud (`cloud_zai`, `cloud_anthropic`) ou `local_vllm` (`gemma-26b-awq`).
  - Suporte a `force_local: bool` e fallback gracioso com sinalização explícita de `is_fallback=True` e registro em `reason`.

## 6. Definition of Done (DoD)
- [x] Código implementado em `src/bombe_code/routing/` com 100% dos tipos anotados.
- [x] Testes de classificação e despacho passando em `tests/unit/test_complexity_router.py`.
- [x] Heurísticas implementadas sem dependência de chamadas externas de LLM para avaliar complexidade.
- [x] Code review aprovado por @unclebob.

## 7. Code Review & Approval
| Data | Reviewer | Eixos Avaliados | Status | Notas |
| :--- | :--- | :--- | :--- | :--- |
| 2026-10-31 | @hoare | Story Compliance & Traceability | APPROVED | 100% dos ACs atendidos e verificados |
| 2026-10-31 | @unclebob | Correctness, Readability, Architecture, Security, Performance | APPROVED | Zero violações de SOLID; separação SRP exemplar |

## 7. Notas Técnicas & Diretrizes Arquiteturais
- Seguir as regras de classificação estipuladas na Seção 3.3 e 4.2 da arquitetura do projeto.
- Vetada a consulta a APIs externas para inferir a complexidade (evitar latência de rede e custo prévio).

## 8. Dependências
- **Bloqueado por:** `STORY-003` (Round 3 concluído).
- **Desbloqueia:** `STORY-005` (Round 5).

---

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (Scope, Interface Pydantic V2, Slices Verticais TDD, SRF Check, Anti-Padrões, Zero Mocks)
**Notas Técnicas:** Fatiamento em 2 slices atômicos aprovado. O executor backend (@barbara) está autorizado a iniciar a queima do SLICE-01 sob ciclo Red/Green/Refactor.
