# AUDITORIA DE GAPS — AUTONOMIA & EFICIÊNCIA DE TOKENS

> **Auditor:** @unclebob (Robert C. Martin — Tech Lead & Architectural Guardian), incorporado por @turing
> **Régua:** A Premissa do Bombe Code — *Ação Mínima do Ser Humano* (`docs/status/bombe-code-status.md` §1)
> **Escopo:** todos os fluxos de orquestração (TUI, CLI, runtime) contra a premissa
> **Data:** 2026-10-05
> **Status:** AUDITADO — gaps de severidade ALTA corrigidos neste ciclo

---

## 1. A Régua (contrato da auditoria)

1. AUTO = parada mínima absoluta (só furo de informação real) + máxima eficiência de tokens.
2. SEMI-AUTO = pausa **apenas na fronteira de fase** (fim do Upstream, fim do Downstream). Dentro da fase, encadeia sozinho. A pausa é um CHECKPOINT (o usuário lê, dá OK, continua quando quiser) — não é turno de trabalho humano.
3. MANUAL = pausa **ao final de cada ETAPA** — depois de TODOS os agentes da etapa e dos gates de validação da etapa rodarem. Nunca por agente.
4. O humano nunca precisa saber que houve erro interno (autocura); nunca é pedido para "mandar continuar".

## 2. Gaps encontrados e vereditos

| # | Severidade | Gap | Correção |
| :--- | :--- | :--- | :--- |
| GAP-1 | **ALTA** | `/wave start` em SEMI-AUTO não continuava a etapa corrente (condição `== "AUTO"`): onda nascida em PLAN parava sem rodar o plano. Continuação de etapa ≠ fronteira de fase. | ✅ Corrigido — AUTO e SEMI encadeiam a continuação; tag do modo correta no anúncio. |
| GAP-2 | **ALTA** | Mensagem de resume com tag fixa "MODO AUTO" mesmo em SEMI-AUTO (usuário enganado sobre quem está dirigindo). | ✅ Corrigido — tag derivada da autonomia real persistida. |
| GAP-3 | **ALTA** | CLI `wave run` no modo MANUAL executava DISCUSS→PLAN→EXECUTE→VALIDATE→END de uma vez, ignorando a pausa por etapa. | ✅ Corrigido — MANUAL pausa ao fim de cada etapa (DISCOVERY, PLAN, EXECUTE, VALIDATE) com instrução de continuação. SEMI já pausava nas fronteiras (fim da Onda Zero, fim das ondas). |
| GAP-4 | MÉDIA | SEMI-AUTO antes deste ciclo comportava-se como MANUAL (só AUTO encadeava) — a pausa por FASE não existia de fato. | ✅ Corrigido neste ciclo — política centralizada `turing/autonomia.py` (`deve_encadear`) aplicada a todos os handlers. |
| GAP-5 | MÉDIO | `run_execute` tem mecanismo de pausa por story (`confirm_callback`) — potencial violação do "nunca por agente". | ✅ Verificado: a UI/CLI **nunca** passa o callback; mecanismo restrito à API interna/testes. Sem ação. |
| GAP-6 | BAIXA | Orçamentos anti-loop presentes e corretos: wall-clock por agente (480s), rodadas de retrabalho por onda (3), não-convergência por assinatura, orçamento do audit (1 chamada). | Sem ação (monitorar em produção). |
| GAP-7 | RECOMENDAÇÃO (economia de tokens no AUTO) | O re-burn TDD re-executa o plano de testes do @aniche mesmo quando `ST-xxx_test_plan.md` já existe e a story não mudou. Cache de plano com invalidação por hash da story reduziria ~25% dos tokens por ciclo. | Registrado como candidato a próxima onda (um passo de cada vez). |
| GAP-8 | RECOMENDAÇÃO | Triagem de contexto na VALIDATE: @edith recebe PRD inteiro + cards + código; a recomendação da própria @nina no make-books (redução de 40–60% de payload) segue válida. | Registrado como candidato a próxima onda. |

## 3. Veredito do Guardian

> [SELO TECH LEAD: APROVADO COM RESSALVAS REGISTRADAS]
>
> A premissa agora é CÓDIGO, não discurso: a política de autonomia vive num único módulo (`turing/autonomia.py`), os handlers a obedecem, e os orçamentos impedem que a autonomia vire incêndio de tokens. Os gaps de severidade ALTA foram eliminados; as recomendações (GAP-7/8) são otimizações de economia, não violações da premissa.
>
> — Princípio final: o humano é acionado por FALTA DE INFORMAÇÃO, nunca por FALTA DE PERMISSÃO. Qualquer PR futuro que adicione um pedágio sem ser furo de informação será rejeitado nesta casa.

---
*Auditoria executada determinísticamente sobre o código (grep de pontos de interação, condições de cascade e orçamentos) — custo: 0 tokens de LLM.*
