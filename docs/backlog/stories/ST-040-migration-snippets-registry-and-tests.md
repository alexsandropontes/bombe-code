# ST-040: Migração Física do Registro de Snippets (55 Manifests + Código + Testes)

## Épico: EP-009
## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

### Descrição
Transferir todos os 55 snippets de `code-forge-2/src/code_forge/registry/snippets/` para `src/bombe_code/registry/snippets/`, cobrindo as 6 plataformas suportadas: dotnet, go, java, nodejs, python e react.

### Critérios de Aceite
1. Todos os 55 diretórios de snippets copiados com seus respectivos `snippet.yaml`, arquivos de implementação e testes unitários.
2. Todas as categorias presentes (`auth`, `data-validation`, `utils`, `multitenancy`, `omnichannel`, `components`, `hooks`).
3. Zero arquivos `__pycache__` ou `*.pyc` copiados.
4. Estrutura de diretórios preservada: `<plataforma>/<categoria>/<snippet-name>/`.
