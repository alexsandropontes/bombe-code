# STORY ST-024: Catálogo de Starters Oficiais (Python, Go, Node, React)

> **Épico:** [EP-005: Starters Engine, Snippets Registry & LLM Snippet Tool](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/epics/EP-005-starters-and-snippets-engine.md)  
> **Status:** READY  
> **Prioridade:** ALTA  
> **Responsáveis:** @barbara (Python/Go), @ryan (Node/TS), @ada (Frontend), @unclebob (Clean Code)  
> **Modo:** tdd-code  

---

## 1. Descrição
Como arquiteto de software ou desenvolvedor,  
Desejo ter um catálogo oficial de starters builtin pré-empacotados com arquitetura limpa e testes,  
Para que as principais stacks backend e frontend do ecossistema possam ser inicializadas sem depender de downloads externos.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Starter Python FastAPI Clean
* **Dado** o starter `python-fastapi-clean`
* **Quando** gerado
* **Então** deve incluir `pyproject.toml` com FastAPI/pytest/ruff, pasta `src/` com entrypoint HTTP, rota `/health` e teste unitário funcional em `tests/`.

### Cenário 2: Starter Go Gin Clean
* **Dado** o starter `go-gin-clean`
* **Quando** gerado
* **Então** deve incluir `go.mod`, `main.go`, handler `/health` com Gin e teste com pacote `testing`.

### Cenário 3: Starter Node Fastify/Express TypeScript
* **Dado** o starter `node-ts-clean`
* **Quando** gerado
* **Então** deve incluir `package.json`, `tsconfig.json`, `src/index.ts` e configuração de testes Vitest/Jest.

### Cenário 4: Starter Frontend React Tailwind
* **Dado** o starter `react-tailwind-clean`
* **Quando** gerado
* **Então** deve incluir `package.json`, `vite.config.ts`, `src/App.tsx` estilizado com classes utilitárias e componente base.
