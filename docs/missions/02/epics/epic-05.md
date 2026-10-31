---
id: EP-05
title: "Validação Integrada E2E e Quality Gates"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-02"
tags:
  - testing-e2e
  - quality-gates
  - cli-verification
  - enterprise-grade
---

# EP-05 — Validação Integrada E2E e Quality Gates

## 1. Problema de Negócio
Após a refatoração e decomposição da CLI nos submódulos e motores, é imperativo comprovar que a experiência do usuário final, a integração dos 19 entry points e a camada de retrocompatibilidade operam de forma robusta e resiliente em ambientes de terminal reais. Testes unitários isolados não são suficientes para garantir paridade 1:1 sem falhas de regressão em pipelines POSIX.

## 2. Valor de Negócio
- **Confiança Operacional Enterprise:** Certificação cabal de que a CLI `bombe` pode ser utilizada em produção sem quebras inesperadas ou comandos não reconhecidos.
- **Eliminação de Código Morto:** Auditoria de 100% da codebase em `src/bombe_code/` para garantir ausência total de mocks, stubs ou corpos vazios (`pass`).
- **Homologação dos Gates G1 a G6:** Validação formal dos critérios de maturidade enterprise definidos na Constituição do Bombe Core.

## 3. Escopo

### O que o Épico Cobre
- Criação da suíte de testes E2E da CLI em `tests/e2e/test_cli_parity.py` usando `CliRunner` e subprocessos reais.
- Teste integrado do ciclo de vida: `mission new` -> `round start` -> `round full` -> `round all` -> `mission end`.
- Teste de regressão completo da Wave Bridge para todos os 7 subcomandos legados.
- Teste de bloqueio do Porteiro Atômico com tentativa de abertura concorrente.
- Auditoria de compliance estrita: varredura por `NotImplementedError`, stubs e comentários `TODO`.

### O que o Épico NÃO Cobre
- Criação de novos comandos ou funcionalidades fora do catálogo aprovado no PRD.
- Alteração da lógica de domínio já homologada nos épicos anteriores.

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-014` | Round 6 | Suíte E2E da CLI e Homologação de Gates G1-G6 | @fowler | 3h |

## 5. Dependências
- **Upstream:** Conclusão de todos os épicos anteriores (EP-01, EP-02, EP-03, EP-04).
- **Downstream:** Desbloqueia o encerramento formal da MISSION-02 e autorização para ship.

## 6. Critérios de Sucesso
- 100% dos testes E2E executando com sucesso no pytest (`pytest tests/e2e/`).
- Zero ocorrências de `NotImplementedError` ou corpos vazios `pass` em `src/bombe_code/`.
- Tempo de resposta dos comandos CLI < 120ms para operações síncronas.
- Gates G1 a G6 com 100% de conformidade documental e técnica.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Testes E2E poluírem o diretório de trabalho do repositório | Alta | Utilização obrigatória da fixture `tmp_path` do pytest isolando completamente cada execução de CLI. |
| Inconsistências de terminal em diferentes sistemas operacionais (Linux/macOS) | Média | Execução padronizada contra a API CLI do Typer e tratamento seguro de caminhos via `pathlib.Path`. |
