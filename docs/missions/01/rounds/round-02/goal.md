---
round: 2
story_id: STORY-002
epic_id: EP-01
status: done
started_at: "2026-10-31T16:00:00"
completed_at: "2026-10-31T16:17:00"
maturity_level: enterprise-grade
layer: backend
agent: "@andrej"
---

# Objetivo do ROUND-2 — STORY-002: Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes

## 1. Round Goal
Atualizar deterministicamente os dossiês de todos os agentes em `src/bombe_code/agents/definitions/*.md` para o padrão PDW 4.0 (Prompt Definition Workflow) mantendo 100% dos nomes e identidades consolidados (pioneiros brasileiros e especialistas globais), acompanhado da implementação do validador de integridade `AgentDossierValidator` e testes unitários correspondentes.

## 2. Escopo do Round
- **Story Alocada:** `STORY-002` (Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes).
- **Entregável Técnico:**
  1. Dossiês em `src/bombe_code/agents/definitions/*.md` refatorados nas 6 seções canônicas do PDW 4.0.
  2. Validador determinístico de integridade em `src/bombe_code/agents/validator.py`.
  3. Suíte de testes unitários passando em `tests/unit/test_agents_pdw.py`.
- **Fronteira Negativa:** Não renomear nenhum arquivo de agente, não alterar orquestrador de LLMs (Round 3) e não implementar código de produção fora do escopo de agentes.

## 3. Checklist de Definition of Done (DoD) do Round
- [x] 100% dos dossiês de agentes em `src/bombe_code/agents/definitions/*.md` atualizados para o padrão PDW 4.0 com frontmatter canônico e as 6 seções obrigatórias.
- [x] Nomes de arquivos, handles e identidades dos agentes (incluindo pioneiros brasileiros e especialistas globais) 100% preservados sem renomeações ou deleções.
- [x] Implementado validador determinístico de integridade de dossiês (`AgentDossierValidator`) em `src/bombe_code/agents/validator.py`.
- [x] Suíte de testes unitários implementada e verde em `tests/unit/test_agents_pdw.py` cobrindo AC-01 a AC-04.
- [x] Veto explícito de atuação cruzada e restrições de soberania configurados nos dossiês de especialistas.
- [x] Ausência de assinaturas de personas ou rodapés institucionais persistidos em código-fonte ou arquivos de configuração.
- [x] Código em conformidade com tipagem estrita (`mypy --strict`) e linter ruff sem advertências.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob) e Arquiteto de Prompts (@andrej).
- [x] Validação final do round executada pelo Agile Master (@david).
