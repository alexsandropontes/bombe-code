# ST-044: Protocolo Caroli PBB: Criação Mandatória da STORY-0

## Épico: EP-010
## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

### Descrição
Garantir que, na fase de PLAN/PBB, `@caroli` verifique a existência de `docs/arquitetura/TEMPLATE_STARTER.md`. Caso presente, `@caroli` deve criar obrigatoriamente a `STORY-0: Implementar Fundação do Projeto via Starter <starter-id>` como primeira história do backlog, com tarefas atômicas estritas atribuídas ao Tech Lead (@unclebob).

### Critérios de Aceite
1. Método em `PBBDecomposer.create_story_zero(starter_id, starter_info)`.
2. Tarefas atômicas de Story-0:
   - `STORY-0-T1`: Scaffolding Determinístico (`@unclebob`, tipo FOUNDATION)
   - `STORY-0-T2`: Baseline de Testes e Sanity Check (`@unclebob`, tipo BACKEND_TDD / E2E)
3. Prioridade absoluta: Story-0 precede Story-1 e bloqueia a execução até ser finalizada.
4. Testes unitários cobrindo a geração da Story-0 e dependências.
