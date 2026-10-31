---
id: STORY-006
title: "FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON"
epic_id: EP-02
round: ROUND-6
agent: "@barbara"
estimation: 3h
status: done
type: feature
layer: backend
depends_on:
  - STORY-005
tags:
  - tool-calling
  - parser
  - regex
  - fallback
  - small-models
---

# STORY-006 — FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON

## 1. Contexto & Racional de Negócio
Ao operar com modelos locais compactos (LFM 1.7B, Gemma 4B, Qwen 9B), é comum que o modelo não formate chamadas de ferramentas através do protocolo nativo de function calling, emitindo ao invés disso blocos de JSON embutidos no corpo da mensagem em sintaxe markdown (````json {"tool": ...} ````). Sem um mecanismo de extração resiliente, essas respostas são descartadas pelo harness como texto comum, impedindo a execução de operações de terminal e manipulação de arquivos.

## 2. Escopo

### O que a História Cobre
- Implementação da classe `FallbackToolParser` em `src/bombe_code/tools/parser.py`.
- Expressão regular otimizada e compilada para identificação de blocos JSON com chaves `"tool"` / `"name"` e `"arguments"`.
- Normalização de dados e conversão transparente para objetos `ToolCallChunk` canônicos.
- Interceptação de streaming no pipeline de resposta para os adaptadores que operam com modelos compactos.
- Suíte exaustiva de testes com edge cases de formatação (aspas simples, quebras de linha, caracteres especiais).

### O que a História NÃO Cobre
- Não executa as ferramentas diretamente no sistema operacional (responsabilidade do `ExecutionEngine`).
- Não força o modelo local a aprender gramáticas formais de amostragem (trata na recepção pós-geração).

## 3. User Story
- **Como:** Motor de orquestração de ferramentas do Bombe Code,
- **Quero:** Um parser resiliente capaz de extrair chamadas de tool embutidas em texto puro ou markdown por modelos menores,
- **Para que:** Agentes rodando em hardware local consigam executar comandos de arquivos e testes com a mesma precisão de grandes modelos proprietários.

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Extração de Blocos Markdown):** Respostas contendo blocos ````json {"tool": "read_file", "arguments": {"path": "..."}} ```` devem ser extraídas como chamadas de tool estruturadas.
- **AC-02 (Extração em Texto Puro):** Payloads JSON sem delimitadores de bloco markdown, mas contendo os pares válidos de chamada, devem ser recuperados com sucesso.
- **AC-03 (Tolerância a Erros de Sintaxe):** Blocos com JSON inválido ou corrompido devem ser ignorados sem propagar exceção de crash para a esteira.
- **AC-04 (Preservação de Integridade de Argumentos):** Argumentos com estruturas complexas (objetos aninhados, arrays, caracteres de escape) devem ser desserializados com exatidão.

## 5. Slices Verticais de Implementação

### SLICE-01: Classe FallbackToolParser e Normalização Canônica
- **Tipo:** Backend (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Arquivo de Teste:** `tests/unit/test_fallback_tool_parser.py`
- **Arquivo de Produção:** `src/bombe_code/tools/parser.py`
- **Critérios de Aceite Cobertos:** AC-01, AC-02, AC-03
- **Escopo Técnico:**
  - Definição da classe `FallbackToolParser` com regexes pré-compilados no nível de classe (`_MARKDOWN_JSON_PATTERN` e `_RAW_JSON_PATTERN`).
  - Implementação do método `extract_tool_calls(text: str) -> list[ToolCallChunk]`.
  - Normalização flexível de chaves (`tool`/`name`, `arguments`/`parameters`).
  - Conversão de argumentos para string JSON compacta garantindo compatibilidade com o protocolo canônico `ToolCallChunk`.
  - Tolerância estrita a falhas sintáticas sem propagar exceções ao chamador.

### SLICE-02: Suíte de Edge Cases, Tolerância a Falhas e Benchmark de Latência
- **Tipo:** Backend (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Arquivo de Teste:** `tests/unit/test_fallback_tool_parser.py`
- **Arquivo de Produção:** `src/bombe_code/tools/parser.py`
- **Critérios de Aceite Cobertos:** AC-03, AC-04, DoD Latência < 5ms
- **Escopo Técnico:**
  - Suíte com no mínimo 8 cenários exaustivos cobrindo:
    1. Bloco markdown com tag ````json ... ````
    2. Bloco markdown genérico sem tag ```` ... ````
    3. Payload JSON em texto puro sem tags
    4. Múltiplos blocos de chamada em uma mesma resposta
    5. Estruturas complexas (objetos aninhados, arrays, aspas e caracteres escapados)
    6. Sinônimos de chave (`name` ao invés de `tool`, `parameters` ao invés de `arguments`)
    7. JSON corrompido / truncado (retorna lista vazia sem crash)
    8. Benchmark de performance (tempo médio de parsing < 5ms por chunk em 100 iterações).

## 6. Definition of Done (DoD)
- [x] Implementação de `FallbackToolParser` em `src/bombe_code/tools/parser.py` sob tipagem estrita.
- [x] Suíte de testes com pelo menos 8 cenários de edge case passando em `tests/unit/test_fallback_tool_parser.py`.
- [x] Zero impacto perceptível de performance no streaming de tokens (tempo de parsing < 5ms por chunk).
- [x] Code review aprovado por @unclebob.

## 7. Code Review & Approval
| Data | Reviewer | Eixos Avaliados | Status | Notas |
| :--- | :--- | :--- | :--- | :--- |
| 2026-10-31 | @hoare | Story Compliance & Traceability | APPROVED | 100% dos ACs atendidos e verificados |
| 2026-10-31 | @unclebob | Correctness, Readability, Architecture, Security, Performance | APPROVED | Zero violações de SOLID; latência < 5ms e robustez validadas |

## 8. Notas Técnicas & Diretrizes Arquiteturais
- Seguir o design pattern especificado na Seção 4.4 da arquitetura do projeto.
- Compilar o regex no nível de classe (`_PATTERN = re.compile(...)`) para máxima performance em runtime.

## 8. Dependências
- **Bloqueado por:** `STORY-005` (Round 5 concluído).
- **Desbloqueia:** `STORY-007` (Round 7).

---

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (Scope, Interface canônica ToolCallChunk, Slices Verticais TDD, SRF Check, Regex Pré-Compilado, Latência < 5ms)
**Notas Técnicas:** Fatiamento em 2 slices atômicos aprovado. O executor backend (@barbara) está autorizado a iniciar a queima do SLICE-01 sob ciclo Red/Green/Refactor.
