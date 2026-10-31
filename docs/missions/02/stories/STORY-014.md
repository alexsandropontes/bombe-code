---
id: STORY-014
title: "Suíte E2E da CLI e Homologação de Gates G1-G6"
epic_id: EP-05
round: ROUND-6
agent: "@fowler"
estimation: 3h
status: validated
completed_at: "2026-10-31T20:05:00Z"
type: test
layer: backend
complexity: 2
depends_on: ["STORY-013"]
tags:
  - testing-e2e
  - quality-gates
  - cli-verification
  - enterprise-grade
---

# STORY-014 — Suíte E2E da CLI e Homologação de Gates G1-G6

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado
**Critérios INVEST:** Atendidos
**Prioridade:** Essencial / Bloqueante para Round 6

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (scope, interface, validações, SRF, anti-padrões, contratos de teste)
**Notas Técnicas:** Construção da suíte E2E da CLI em `tests/e2e/test_cli_parity.py`, validação dos 19 entry points canônicos, auditoria estrita de ausência de stubs/mocks e verificação de conformidade com os Quality Gates G1-G6.

---

## 1. Contexto de Negócio
Para concluir formalmente a MISSION-02 e certificar a paridade 1:1 com o Bombe Core v4, é imperativo dispor de uma suíte de testes de ponta a ponta (E2E) que simule a interação do desenvolvedor no terminal, cobrindo todo o ciclo operacional de missões, a tríade de rounds, o bridge de compatibilidade de ondas e a ausência absoluta de débito técnico ou mocks em produção.

---

## 2. Escopo

**O que faz:**
Cria a suíte `tests/e2e/test_cli_parity.py` utilizando o `CliRunner` do Typer e subprocessos reais, validando o fluxo completo de ponta a ponta:
1. `bombe mission new` -> trava atômica de missão duplicada.
2. `bombe round start` -> parada determinística na DoR.
3. `bombe round burn`, `review` e `validate`.\
4. `bombe round full` e `bombe round all` (sem confirmações vazias).
5. `bombe wave ...` -> interceptação e despacho com Rich banner.
6. `bombe project ship`, `mode` e comandos standalone.
7. Auditoria de compliance estrita: varredura por `NotImplementedError`, stubs e comentários `TODO` em `src/bombe_code/`.

**O que NÃO faz:**
- ❌ Não utiliza mocks para simular o comportamento da CLI.
- ❌ Não ignora falhas de exit code.

**Limites:**
- [x] Apenas testes de integração e validação E2E.
- [x] Execução contra ambientes temporários isolados com fixture `tmp_path`.

---

## 3. User Story & Intenção do Usuário
**Como** Tech Lead e Arquiteto de Software (@unclebob / @fowler),  
**Quero** uma suíte de testes E2E automatizada validando todos os 19 entry points e os gates G1-G6,  
**Para que** tenhamos prova cabal de paridade funcional com o Bombe Core v4 e zero regressões.

---

## 4. Acceptance Criteria (ACs Testáveis)
- [x] **AC-01 (Cobertura Integral dos 19 Entry Points):** Todos os 19 entry points (EP-01 a EP-19) possuem casos de teste automatizados em `tests/e2e/test_cli_parity.py`.
- [x] **AC-02 (Fluxo de Missão e Rounds E2E):** O ciclo `mission new` -> `round start` -> `round full` -> `round all` -> `mission end` executa com sucesso em diretório temporário.
- [x] **AC-03 (Validação da Wave Bridge):** Os 7 subcomandos legados `bombe wave ...` são validados comprovando que emitem o banner e executam a ação de destino.
- [x] **AC-04 (Auditoria Zero Mocks / Zero Stubs):** Teste de auditoria varre recursivamente `src/bombe_code/` e falha se encontrar `NotImplementedError`, corpos vazios `pass` ou tags `TODO`.
- [x] **AC-05 (Homologação Gates G1 a G6):** Suíte comprova que os gates G1 a G6 estabelecidos em `docs/projeto/mvp.md` estão 100% satisfeitos.

---

## 5. Definition of Done (DoD)
- [x] Arquivo `tests/e2e/test_cli_parity.py` criado e executando com 100% de aprovação no pytest.
- [x] Varredura estrita de linter e typesafe sem warnings.
- [x] Relatório de conformidade E2E emitido para encerramento da missão.
- [x] Story aprovada por @hoare e @unclebob.

---

## 6. Notas Técnicas & Contratos

### 6.1 Casos de Teste Obrigatórios em `test_cli_parity.py`
```python
def test_e2e_mission_lifecycle_with_atomic_lock(tmp_path: Path): ...
def test_e2e_round_start_stops_deterministically_at_dor(tmp_path: Path): ...
def test_e2e_round_full_executes_single_story_end_to_end(tmp_path: Path): ...
def test_e2e_round_all_runs_unattended_pipeline(tmp_path: Path): ...
def test_e2e_wave_bridge_redirects_all_legacy_commands(tmp_path: Path): ...
def test_e2e_standalone_commands_execute_independently(tmp_path: Path): ...
def test_e2e_zero_stubs_and_mocks_in_production_code(): ...
```

### 6.2 O que NÃO Fazer (Anti-padrões)
- ⛔ NÃO usar mocks para interceptar chamadas Typer.
- ⛔ NÃO rodar testes E2E tocando a raiz do repositório real de desenvolvimento.

---

## 7. Dependências
- **Blocked by:** `STORY-013` (Equalização de Comandos Standalone).
- **Required by:** Encerramento formal da MISSION-02 (`bombe mission end`).
