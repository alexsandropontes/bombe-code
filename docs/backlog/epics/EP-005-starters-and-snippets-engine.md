# ÉPICO EP-005: Starters Engine, Snippets Registry & LLM Snippet Tool

> **Status:** PLANNING -> READY FOR IMPLEMENTATION  
> **Onda:** ONDA-005  
> **Modo:** tdd-code (Sem teste RED = Sem código de produção)  
> **Liderança:** @turing (Autônomo da ONDA), @grace (Product Strategy), @ieru (Software Architecture), @unclebob (Tech Lead)  

---

## 1. Contexto & Proposta de Valor (Fase DISCUSS)

### 1.1 Análise de Viabilidade Técnica e Estratégica (@meira)
O ecossistema do Bombe Code requer produtividade imediata no kickoff de novos projetos e reaproveitamento de soluções comprovadas. Em vez de criar projetos do zero ou forçar modelos LLM a gerarem código utilitário redundante (validação de CPF/CNPJ, máscaras de cartão, formatação de telefone, autenticação JWT), o framework implementa duas forças sinérgicas:
1. **Starters Engine (`/project starter`)**: Fábrica determinística de scaffolding de projetos com arquitetura limpa pré-configurada, testes, linter, `.bombeconfig` e estrutura de pastas.
2. **Snippets Registry (Fábrica de LEGO) & Tool para LLM**: Um catálogo de blocos de construção auditados que pode ser consumido tanto por desenvolvedores humanos via CLI/TUI (`/snippet`) quanto por **agentes de IA durante o ciclo autônomo** através da ferramenta `snippet_search` / `snippet_get`.

### 1.2 Documento de Requisitos de Produto / PRD (@grace)
* **Objetivo:** Fornecer scaffolding de projetos em < 3 segundos e disponibilizar biblioteca de componentes funcionais para humanos e LLMs.
* **Critérios RICE:**
  - **Reach:** 100% dos novos projetos e agentes de backend/frontend.
  - **Impact:** Altíssimo (elimina até 60% de código boilerplate e consumo inútil de tokens de geração).
  - **Confidence:** 100% (baseado na experiência consolidada do Code Forge e Bombe Core original).
  - **Effort:** Médio (estruturação de templates, registry e tools).

---

## 2. Arquitetura Técnica & Decisões Estruturais (Fase PLAN - @ieru & @unclebob)

### 2.1 Componentes Principais
1. **`StarterEngine` (`src/bombe_code/starters/engine.py`):**
   - Catálogo de templates embutidos e suporte a templates customizados.
   - Aplicação de variáveis (nome do projeto, caminhos de source, banco, stack).
   - Validação de diretório de destino limpo antes da aplicação.
2. **Templates Oficiais de Starters:**
   - `python-fastapi-clean`: Backend FastAPI, pytest, Pydantic v2, Ruff, Dockerfile.
   - `go-gin-clean`: Backend Go 1.22+, Gin, `go test`, Clean Architecture, Dockerfile.
   - `node-ts-clean`: Backend Node 20+, TypeScript, Fastify/Express, Vitest, ESLint.
   - `react-tailwind-clean`: Frontend React 19+, Tailwind CSS, Vite, TypeScript.
3. **`SnippetRegistry` (`src/bombe_code/snippets/registry.py`):**
   - Suporte a snippets categorizados (`data-validation`, `utils`, `auth`, `http`).
   - Metadados estruturados (`snippet.yaml`) com tags, linguagens (Python, Go, Node/TS), complexidade e testes.
   - Métodos de busca: por termo, linguagem e tags.
4. **LLM Snippet Tools (`src/bombe_code/tools/builtin/snippet_tools.py`):**
   - `snippet_search`: Permite à LLM buscar funções reutilizáveis prontas no registry antes de codificar.
   - `snippet_get`: Permite à LLM solicitar o código fonte exato e testes do snippet.
5. **Comandos CLI e TUI:**
   - `/project starter [list|apply <nome>]` e `bombe-code project starter`
   - `/snippet <search|list|get|copy> [termo]` e `bombe-code snippet`

---

## 3. Decomposição das Histórias de Usuário (ai-stories)

* [ST-023: StarterEngine & Comandos de Scaffolding de Projeto](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/stories/ST-023-starter-engine-and-commands.md)
* [ST-024: Catálogo de Starters Oficiais (Python, Go, Node, React)](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/stories/ST-024-builtin-starters-catalog.md)
* [ST-025: SnippetRegistry & Comandos de Snippets (Fábrica de LEGO)](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/stories/ST-025-snippet-registry-and-commands.md)
* [ST-026: Tool de Snippets para Agentes LLM (snippet_search & snippet_get)](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/stories/ST-026-llm-snippet-tools.md)
