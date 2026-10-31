---
id: STORY-011
title: "Engine de Rounds Autônomos: Full & All"
epic_id: EP-02
round: ROUND-3
agent: "@barbara"
estimation: 4h
status: done
type: feature
layer: backend
complexity: 3
depends_on: ["STORY-010"]
tags:
  - round-engine
  - autonomous-pipeline
  - anti-confirmations
  - round-all
---

# STORY-011 — Engine de Rounds Autônomos: Full & All

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado
**Critérios INVEST:** Atendidos
**Prioridade:** Essencial / Bloqueante para Round 3

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (scope, interface, validações, SRF, anti-padrões, contratos de teste)
**Notas Técnicas:** Implementação de `bombe round full [N]` (semi-automático de 1 story) e `bombe round all` (pipeline contínuo desatendido para todos os rounds da missão sem perguntas vazias de cortesia).

---

## 1. Contexto de Negócio
Desenvolvedores autônomos e pipelines de CI/CD necessitam de velocidade de vazão e automação máxima. Perguntar "Deseja continuar?" entre etapas é desperdício de tempo e bloqueia o desenvolvimento autônomo. O Bombe Code deve fornecer o comando `bombe round full [N]` (que executa a story inteira ponta a ponta e para ao final) e `bombe round all` (que itera ininterruptamente por todos os rounds pendentes da missão até o encerramento).

---

## 2. Escopo

**O que faz:**
Adiciona os comandos autônomos `bombe round full [N]` e `bombe round all` em `src/bombe_code/cli/commands/round.py`, orquestrando as estações de Upstream, Burn TDD, Review e Validate de forma sequencial automatizada, emitindo diagnósticos Rich em console e parando exclusivamente sob quebra real de teste ou erro de sintaxe.

**O que NÃO faz:**
- ❌ Não pede confirmação ao usuário entre rounds ou subfases ("Posso seguir?").
- ❌ Não mascara falhas de testes: se um teste quebrar, o loop contínuo para imediatamente.

**Limites:**
- [x] Camada de automação da Tríade de Rounds.
- [x] Zero mocks em código de produção.
- [x] Testes unitários e de integração em `tests/unit/test_round_autonomous_engine.py`.

---

## 3. User Story & Intenção do Usuário
**Como** Desenvolvedor Autônomo,  
**Quero** disparar a execução de uma story completa (`round full`) ou da missão inteira (`round all`) com um único comando,  
**Para que** a esteira construa e valide o software sem interrupções manuais desnecessárias.

---

## 4. Acceptance Criteria (ACs Testáveis)
- [x] **AC-01 (Execução Semi-Automática `round full`):** `bombe round full [N]` executa sequencialmente Upstream -> Burn -> Review -> Validate para o round N e para ao final com relatório consolidado.
- [x] **AC-02 (Pipeline Contínuo `round all`):** `bombe round all` localiza todos os rounds pendentes da missão ativa e os executa ordenadamente do primeiro ao último.
- [x] **AC-03 (Zero Confirmações Vazias):** Durante a execução de `round all`, o sistema não solicita entrada no stdin e não emite prompts de confirmação de cortesia.
- [x] **AC-04 (Interrupção por Falha Real):** Se qualquer round falhar no teste TDD ou no review de arquitetura, o comando `round all` aborta imediatamente com exit code 1, preservando o estado do repositório para diagnóstico.
- [x] **AC-05 (Encerramento de Missão):** Ao concluir o último round em `round all`, exibe sumário de sucesso orientando o encerramento via `bombe mission end`.

---

## 5. Definition of Done (DoD)
- [x] Comandos `full` e `all` registrados no `round_app` e despachados pelo `RoundExecutionEngine`.
- [x] Tratamento de timeout global e captura de sinais de interrupção (SIGINT / Ctrl+C).
- [x] Testes em `tests/unit/test_round_autonomous_engine.py` cobrindo cenários de sucesso e falha no meio da esteira.
- [x] Código aprovado no Ruff e Mypy.

---

## 6. Notas Técnicas & Contratos

### 6.1 Contrato da CLI
```text
bombe round full [ROUND_NUMBER] [--project-dir PATH]
bombe round all [--project-dir PATH] [--timeout SECONDS]
```

### 6.2 Estrutura de Código & SRF Check
| Função / Método | Assinatura | Responsabilidade | Limite |
|---|---|---|---|
| `RoundExecutionEngine.execute_round_full` | `(round_num: int, project_dir: Path) -> RoundState` | Executa ciclo completo de 1 round | < 25 linhas |
| `RoundExecutionEngine.execute_round_all` | `(project_dir: Path, timeout: int) -> list[RoundState]` | Loop desatendido por todos os rounds | < 30 linhas |
| `RoundExecutionEngine._assert_no_test_failures` | `(state: RoundState) -> None` | Valida ausência de quebras antes de avançar | < 15 linhas |

**SRF Check:**
- [x] Nenhuma função possui "e" no nome.
- [x] Cada função possui uma responsabilidade única.
- [x] Nenhuma função excede 30 linhas.

### 6.3 O que NÃO Fazer (Anti-padrões)
- ⛔ NÃO pausar perguntando "Deseja continuar para o próximo round?".
- ⛔ NÃO engolir exceções de testes falhantes para "seguir em frente".
- ⛔ NÃO permitir que `round all` seja executado se não houver missão ativa.

---

## 7. Dependências
- **Blocked by:** `STORY-010` (Rounds Manuais).
- **Required by:** `STORY-012` (Wave Bridge) e `STORY-014` (Suíte E2E).
