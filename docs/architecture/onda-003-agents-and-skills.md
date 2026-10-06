# ONDA 3: SISTEMA DE PERSONAS, AGENTES ESPECIALISTAS & SKILLS SOB DEMANDA

> **Fase do Workflow:** ONDA 3 — Etapa **PLAN**  
> **Status:** Planejamento Arquitetural Concluído — Pronto para Execução TDD  
> **Equipe de Personas:** 50% Brasileiros / 50% Mundiais  

---

## 1. Arquitetura Geral do Módulo `bombe_code.agents` & `bombe_code.skills`

```
src/bombe_code/
├── agents/
│   ├── __init__.py
│   ├── models.py            # AgentDefinition, AgentInputContract, AgentOutputContract
│   ├── registry.py          # AgentRegistry (catálogo oficial com 11 agentes)
│   └── runner.py            # AgentRunner com PydanticAiFactory
└── skills/
    ├── __init__.py
    ├── models.py            # SkillDefinition, SkillMetadata
    ├── registry.py          # SkillRegistry (descoberta progressiva on-demand)
    └── tools.py             # Tools Pydantic AI: search_skills & load_skill
```

---

## 2. Contratos dos Agentes

### Metadados e Paridade de Homenagens (50% BR / 50% Mundial)
1. **Universal:**
   - `@turing` (Alan Turing) — Maestro do Runtime, sem criação direta de código de produção.
2. **5 Pioneiros Brasileiros:**
   - `@meira` (Silvio Meira) — Inovação & Viabilidade (Fase Zero / DISCUSS).
   - `@ieru` (Roberto Ierusalimschy) — Arquitetura de Software & ADRs (PLAN).
   - `@caroli` (Paulo Caroli) — Agile Master, Épicos & ai-stories (PLAN).
   - `@valim` (José Valim) — Backend Lead Engineer sob TDD estrito (EXECUTE).
   - `@edith` (Edith Ranzini) — QA Lead & Contract Validator (VALIDATE).
3. **5 Referências Mundiais:**
   - `@grace` (Grace Hopper) — Product Manager & PRD (DISCUSS).
   - `@codd` (Edgar F. Codd) — Database Architect & Schemas (PLAN).
   - `@norman` (Don Norman) — UI/UX Designer & Jornada (PLAN).
   - `@ada` (Ada Lovelace) — Frontend Developer Integrada (EXECUTE).
   - `@unclebob` (Robert C. Martin) — Tech Lead & Reviewer do Cycle (EXECUTE).

---

## 3. Skills sob Demanda (On-Demand Progressive Disclosure)
- Agentes possuem system prompts enxutos de 30-60 linhas.
- Duas tools universais injetadas nos agentes:
  - `search_skills(query: str) -> list[SkillSummary]`
  - `load_skill(name: str) -> str`
- Os corpos detalhados de regras (`solid-dry`, `clean-code`, `pbb-backlog`, `fastapi`, `tailwind`, etc.) são carregados em tempo de execução somente sob demanda.

---

## 4. Plano de Implementação TDD (RED → GREEN → REFACTOR)

- **Cycle 1: `bombe_code.skills` (Models & Registry)**
  - Teste RED: `tests/test_skills.py` (busca de skills, carregamento on-demand, cache).
  - Implementação GREEN: `SkillDefinition`, `SkillRegistry`, `search_skills`, `load_skill`.
  - Refactor & Validação: Ruff & Tipagem.

- **Cycle 2: `bombe_code.agents` (Models & Official Registry)**
  - Teste RED: `tests/test_agents.py` (validação de contratos de inputs/outputs, paridade 50/50, consulta por etapa).
  - Implementação GREEN: `AgentDefinition`, catálogo dos 11 agentes com prompts e homenagens.
  - Refactor & Validação: Verificação de constraints e gates.

- **Cycle 3: `AgentRunner` integrado com `PydanticAiFactory` & Turing State**
  - Teste RED: `tests/test_agent_runner.py` (execução simulada e despache de agentes com injeção de tools de skills).
  - Implementação GREEN: `AgentRunner`, despacho tipado e registro de eventos no SQLite `ProjectDatabase`.
  - Refactor & Validação: Suite completa de testes e verificação final.
