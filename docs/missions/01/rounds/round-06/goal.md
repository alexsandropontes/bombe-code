---
round: 6
story_id: STORY-006
epic_id: EP-02
status: done
started_at: "2026-10-31T16:55:00"
completed_at: "2026-10-31T17:01:00"
maturity_level: enterprise-grade
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-6 — STORY-006: FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON

## 1. Round Goal
Implementar o `FallbackToolParser` em `src/bombe_code/tools/parser.py` para extração resiliente de chamadas de ferramentas encapsuladas em blocos Markdown JSON (````json {"tool": ...} ````) ou texto puro por modelos de linguagem compactos locais (LFM 1.7B, Gemma 4B, Qwen 9B), normalizando o payload para objetos canônicos `ToolCallChunk` com latência de parsing inferior a 5ms por chunk e tolerância a erros sintáticos.

## 2. Escopo do Round
- **Story Alocada:** `STORY-006` (FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON).
- **Entregáveis Técnicos:**
  1. Implementação da classe `FallbackToolParser` com expressão regular compilada no nível de classe (`_PATTERN = re.compile(...)`) em `src/bombe_code/tools/parser.py`.
  2. Suporte à extração de blocos markdown delimitados (````json ... ````) e payloads JSON brutos embutidos no corpo da resposta com chaves `"tool"` / `"name"` e `"arguments"`.
  3. Normalização e conversão segura para a estrutura de chamada canônica do Bombe Code (`ToolCallChunk`).
  4. Parser resiliente e tolerante a falhas (não lança exceções de crash em payloads malformados ou incompletos; ignora blocos corrompidos graciosamente).
  5. Preservação estrita de integridade estrutural para tipos de dados complexos (JSON aninhado, arrays, caracteres escapados).
  6. Suíte de testes unitários em `tests/unit/test_fallback_tool_parser.py` cobrindo no mínimo 8 cenários de edge cases de formatação (quebras de linha, aspas simples/duplas, caracteres especiais, múltiplos blocos).
- **Fronteira Negativa:** Não executa chamadas no sistema operacional (escopo do `ExecutionEngine`); não modifica adaptadores de streaming já homologados.

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Implementação de `FallbackToolParser` em `src/bombe_code/tools/parser.py` sob tipagem estrita (`mypy --strict`).
- [x] Regex de identificação compilado no nível de classe (`re.compile`) para otimização de runtime.
- [x] Extração de tool calls em blocos markdown delimitados (AC-01) implementada e verificada.
- [x] Extração em texto puro sem delimitadores markdown (AC-02) implementada e verificada.
- [x] Tolerância a erros sintáticos e JSON inválido sem abortar a esteira (AC-03).
- [x] Desserialização de argumentos complexos (objetos aninhados, arrays, escapes) preservando integridade (AC-04).
- [x] Latência de parsing < 5ms por chunk em benchmark/teste unitário.
- [x] Suíte com ≥ 8 cenários de teste cobrindo edge cases em `tests/unit/test_fallback_tool_parser.py`.
- [x] Ausência de stubs, dead code, prints de depuração ou bodies vazios (`pass`, `...`) em código de produção.
- [x] Zero metadados decorativos, assinaturas de personas ou rodapés institucionais persistidos em arquivos de código.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob).
- [x] Validação formal do round executada pelo Agile Master (@david).
