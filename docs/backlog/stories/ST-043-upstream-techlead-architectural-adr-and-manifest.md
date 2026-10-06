# ST-043: Protocolo Upstream do Tech Lead: Decisão de Template no ADR & Prevenção de Architectural Drift

## Épico: EP-010
## Status: DONE
## Prioridade: ALTA
## Data: 2026-10-03

---

### Descrição
Estabelecer no Upstream (fase DISCUSS) o protocolo onde o Tech Lead (@unclebob) e Arquiteto (@ieru) consultam `template_match`. Se houver starter adequado, gravam o manifesto em `docs/arquitetura/TEMPLATE_STARTER.md` e referenciam no ADR, orientando `@codd` para usar as entidades existentes (ex: `User`, `Tenant`, `Product`) evitando divergência no MER.

### Critérios de Aceite
1. Mecanismo de persistência e leitura de `docs/arquitetura/TEMPLATE_STARTER.md`.
2. Extensão do `ArchitectureGate` para validar que, se um starter foi selecionado, a documentação de arquitetura referencia o starter e respeita as convenções de schema.
3. Testes unitários para validação do gate com e sem starter.
