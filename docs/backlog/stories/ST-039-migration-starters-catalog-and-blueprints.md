# ST-039: Migração Física do Catálogo de Starters (38 YAMLs + 27 Blueprints)

## Épico: EP-009
## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

### Descrição
Transferir de forma limpa e determinística todos os 38 arquivos de especificação YAML de starters e todos os 27 diretórios de blueprints físicos de `code-forge-2/src/code_forge/registry/starters/` para `src/bombe_code/registry/starters/`.

### Critérios de Aceite
1. Todos os 38 arquivos `.yaml` de starters presentes em `src/bombe_code/registry/starters/`.
2. Todos os 27 diretórios sob `blueprints/` presentes com seus arquivos de template (`.tmpl`, código, configs).
3. Zero arquivos `__pycache__` ou `*.pyc` copiados.
4. Permissões de arquivo íntegras e arquivos legíveis.
