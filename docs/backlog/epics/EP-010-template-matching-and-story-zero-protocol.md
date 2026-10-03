# EP-010: Classificador Determinístico de Templates & Protocolo STORY-0

## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

## 1. Visão Geral e Contexto
Com a migração de 100% dos 38 starters e 55 snippets concluída (EP-009 / ONDA 1), o Bombe Code dispõe do acervo enterprise de blueprints. A **ONDA 2** estabelece o elo determinístico entre a concepção do produto no Upstream e a execução da fundação no Downstream.

### O Protocolo da STORY-0
1. **Upstream (DISCUSS / ADR / Inception):**
   - O Tech Lead (@unclebob) e o Arquiteto (@ieru) utilizam a ferramenta determinística `template_match` para verificar se o projeto se encaixa em algum starter do catálogo oficial, considerando:
     - `product_type` (SaaS, Chatbot, API REST, Web Portal, Omnichannel/BFF WhatsApp)
     - `backend_language` (Python, Go, Node.js, .NET, Java)
     - `frontend_stack` (React, Streamlit, None)
     - `multitenancy` (Monotenant / Mono, Multi-logical, Multi-physical)
     - `database` (PostgreSQL, None)
   - A ferramenta expõe o **Manifesto Arquitetural** do template (nomes de tabelas, entidades base como `User`, `Tenant`, `Product`, endpoints base) para que `@codd` (DBA) e `@ieru` (Arquiteto) desenhem o MER e o ADR estendendo a estrutura existente, prevenindo *Architectural Drift*.
   - A decisão é persistida deterministamente em `docs/arquitetura/TEMPLATE_STARTER.md` e anotada no ADR.
2. **PBB & Caroli (Breakdown de Stories):**
   - Durante a quebra de stories no PBB, `@caroli` inspeciona a presença de `TEMPLATE_STARTER.md`.
   - Se houver starter selecionado: `@caroli` OBRIGATORIAMENTE cria a **STORY-0: Implementar Fundação do Projeto via Starter <starter-id>** como a primeira história do backlog, prioritária e bloqueante para as demais.
   - Se não houver starter: o fluxo segue normalmente sem Story-0.
3. **Downstream (Execução do Ciclo pelo Tech Lead):**
   - O Tech Lead (@unclebob) é sempre o responsável técnico pela `STORY-0`.
   - A execução da Story-0 aplica o scaffolding determinístico via `StarterEngine` e executa a suíte de testes de fundação da stack.
   - Se os testes passarem sem erros: Story-0 é finalizada com sucesso e o ciclo avança para a Story-1.
   - Se houver erro: o determinístico captura o log de falha e aciona o Tech Lead (@unclebob) para eliminação do erro (fallback e registro de não-conformidade).

---

## 2. Stories do Épico
- [x] **ST-042**: Ferramenta de Matching e Inspeção Arquitetural de Templates (`TemplateCatalogTool` / `template_match` / `template_inspect`)
- [x] **ST-043**: Protocolo Upstream do Tech Lead: Decisão de Template no ADR & Prevenção de Architectural Drift
- [x] **ST-044**: Protocolo Caroli PBB: Criação Mandatória da STORY-0 com Decomposição Atômica de Fundação
- [x] **ST-045**: Execução Downstream da STORY-0 pelo Tech Lead com Baseline Test Runner & Fallback de Autocorreção
