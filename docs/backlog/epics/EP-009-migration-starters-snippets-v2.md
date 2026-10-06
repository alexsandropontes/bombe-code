# EP-009: Migração Completa de Starters e Snippets V2

## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

## 1. Visão Geral e Contexto
O ecossistema Bombe Code absorveu integralmente o acervo testado e validado do Code Forge 2 (`code-forge-2`), composto por:
- **38 Starters oficiais** (declarados via manifests YAML)
- **27 Blueprints arquiteturais físicos completos** (estruturas reais de backend, frontend, chatbots, multitenancy e omnichannel)
- **55 Snippets modulares** (manifests `snippet.yaml`, código e testes em `dotnet`, `go`, `java`, `nodejs`, `python` e `react`)

Essa migração eleva a capacidade do Bombe Code de gerar aplicações enterprise prontas para produção sem sintetizar boilerplate do zero, preparando a fundação para a **ONDA 2** (Classificador Determinístico & Protocolo da STORY-0).

---

## 2. Objetivos Principais
1. Copiar 100% dos 38 starters e seus 27 blueprints físicos para `src/bombe_code/registry/starters/`, omitindo artefatos temporários/cache. [CONCLUÍDO]
2. Copiar 100% dos 55 snippets e seus testes unitários para `src/bombe_code/registry/snippets/`. [CONCLUÍDO]
3. Atualizar o `StarterEngine` para carregamento dinâmico a partir do disco (`src/bombe_code/registry/starters/`), mantendo fallback aos builtins e suportando a resolução de blueprints e composição de starters fullstack. [CONCLUÍDO]
4. Atualizar o `SnippetRegistry` para carregamento dinâmico a partir do disco (`src/bombe_code/registry/snippets/`), com busca por tags, plataforma e categoria. [CONCLUÍDO]
5. Garantir 100% de testes unitários e de integração verdes sem regressões. [CONCLUÍDO]

---

## 3. Stories do Épico
- [x] **ST-039**: Migração Física do Catálogo de Starters (38 YAMLs + 27 Blueprints)
- [x] **ST-040**: Migração Física do Registro de Snippets (55 Manifests + Código + Testes)
- [x] **ST-041**: Refatoração dos Motores Dinâmicos (`StarterEngine` e `SnippetRegistry`) & Testes de Integração
