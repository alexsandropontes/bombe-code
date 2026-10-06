# ST-042: Ferramenta de Matching e Inspeção Arquitetural de Templates

## Épico: EP-010
## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

### Descrição
Implementar `TemplateCatalogTool` com as tools `template_match` e `template_inspect` para que agentes LLM (especialmente Tech Lead e Arquiteto) identifiquem starters aderentes e inspecionem schemas e convenções.

### Critérios de Aceite
1. `template_match`:
   - Parâmetros: `product_type`, `backend_language`, `frontend_stack`, `multitenancy`, `database`.
   - Matching determinístico com score/regras para os 38 starters.
   - Retorna informações do starter e manifesto de convenções arquiteturais (nomes de tabelas, entidades, endpoints).
2. `template_inspect`:
   - Parâmetros: `starter_id`.
   - Retorna estrutura completa, arquivos, blueprint e composição.
3. Registro das ferramentas no catálogo central de ferramentas (`src/bombe_code/tools/builtin/`).
4. Testes unitários com 100% de cobertura.
