---
id: STORY-006
title: "FallbackToolParser para Extração Resiliente de Chamadas em Markdown JSON"
epic_id: EP-02
round: ROUND-6
agent: "@barbara"
estimation: 3h
status: ready
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

## 5. Definition of Done (DoD)
- [ ] Implementação de `FallbackToolParser` em `src/bombe_code/tools/parser.py` sob tipagem estrita.
- [ ] Suíte de testes com pelo menos 8 cenários de edge case passando em `tests/unit/test_fallback_tool_parser.py`.
- [ ] Zero impacto perceptível de performance no streaming de tokens (tempo de parsing < 5ms por chunk).
- [ ] Code review aprovado por @unclebob.

## 6. Notas Técnicas & Diretrizes Arquiteturais
- Seguir o design pattern especificado na Seção 4.4 da arquitetura do projeto.
- Compilar o regex no nível de classe (`_PATTERN = re.compile(...)`) para máxima performance em runtime.

## 7. Dependências
- **Bloqueado por:** `STORY-005` (Round 5 concluído).
- **Desbloqueia:** `STORY-007` (Round 7).
