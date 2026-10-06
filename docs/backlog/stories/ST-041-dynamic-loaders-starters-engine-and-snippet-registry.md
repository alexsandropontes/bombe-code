# ST-041: Refatoração dos Motores Dinâmicos (`StarterEngine` e `SnippetRegistry`) & Testes de Integração

## Épico: EP-009
## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

### Descrição
Refatorar `StarterEngine` e `SnippetRegistry` para que descubram, carreguem e processem dinamicamente os starters e snippets armazenados em `src/bombe_code/registry/`.

### Critérios de Aceite
1. `StarterEngine.list_starters()` e `get_starter()` carregam os 38 starters a partir dos YAMLs em disco, com fallback aos `BUILTIN_STARTERS`.
2. Suporte no `StarterEngine.apply_starter()` para extrair e renderizar arquivos a partir dos blueprints físicos (`blueprints/<blueprint_id>`), processando templates `.tmpl` e substituindo variáveis como `{project_name}`. Suporte a composição (ex: backend + portal web).
3. `SnippetRegistry.list_snippets()`, `search()` e `get_snippet()` carregam dinamicamente os 55 snippets dos arquivos `snippet.yaml` no disco, lendo seus arquivos de código e testes.
4. Suíte de testes atualizada cobrindo:
   - Carregamento de todos os starters (contagem >= 38)
   - Carregamento de todos os snippets (contagem >= 55)
   - Aplicação de starter baseado em blueprint real
   - Cópia de snippet a partir do catálogo físico
5. 100% dos testes da suíte completa do Bombe Code passando.
