---
id: STORY-009
title: "Porteiro Atômico e Lifecycle de Missões"
epic_id: EP-01
round: ROUND-1
agent: "@barbara"
estimation: 3h
status: done
type: feature
layer: backend
complexity: 2
depends_on: []
tags:
  - mission-lifecycle
  - atomic-gatekeeper
  - cli-dispatch
  - docs-scaffold
---

# STORY-009 — Porteiro Atômico e Lifecycle de Missões

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado
**Critérios INVEST:** Atendidos
**Prioridade:** Essencial / Bloqueante para Round 1

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (scope, interface, validações, SRF, anti-padrões, contratos de teste)
**Notas Técnicas:** Decomposição Typer limpa em `mission.py`, motor de domínio `MissionLifecycleEngine` com trava atômica `assert_no_open_mission()`.

---

## 1. Contexto de Negócio
O ecossistema Bombe Core v4 adota o conceito soberano de Missão (`MISSION-NN`) como a unidade agregadora de valor. Para evitar concorrência desordenada e corrupção na árvore `docs/missions/`, o Bombe Code deve possuir um ciclo de vida explícito governado pelos comandos `bombe mission new`, `bombe mission status` e `bombe mission end`, assegurando que o porteiro atômico bloqueie qualquer tentativa de abrir uma nova missão se outra estiver ativa.

---

## 2. Escopo

**O que faz:**
Implementa o submódulo Typer `src/bombe_code/cli/commands/mission.py` e o motor `MissionLifecycleEngine` em `src/bombe_code/orchestration/mission_engine.py`, oferecendo os comandos `bombe mission new '<demanda>'`, `bombe mission status` e `bombe mission end`. Inclui a guarda atômica `assert_no_open_mission()` baseada em filesystem, scaffolding físico em `docs/missions/NN/` e exibição de kanban tabular via Rich.

**O que NÃO faz:**
- ❌ Não executa queima TDD de stories de execução (escopo de rounds).
- ❌ Não intercepta comandos legados de ondas (escopo da Wave Bridge).
- ❌ Não realiza merge ou push de branches Git (escopo de ship).

**Limites:**
- [x] Apenas camada de comando e orquestração de missões.
- [x] Zero mocks em código de produção.
- [x] Testes unitários e de integração em `tests/unit/test_mission_lifecycle.py`.

---

## 3. User Story & Intenção do Usuário
**Como** Desenvolvedor ou Operador de Terminal,  
**Quero** inicializar, consultar o status e encerrar missões através de comandos CLI canônicos com porteiro atômico,  
**Para que** eu tenha garantia de foco único de trabalho (WIP = 1) e integridade referencial dos artefatos em `docs/missions/`.

---

## 4. Acceptance Criteria (ACs Testáveis)
- [x] **AC-01 (Porteiro Atômico Bloqueante):** Invocação de `bombe mission new 'demanda'` com missão existente em status `open`, `active` ou `in_progress` aborta com exit code 1 e mensagem de erro informando a missão aberta.
- [x] **AC-02 (Scaffolding Físico Completo):** Em caminho feliz, `bombe mission new 'demanda'` determina o próximo ID sequencial (`01`, `02`, ...), cria `docs/missions/NN/mission.md` com frontmatter válido e subpastas estruturais (`prd/`, `architecture/`, `epics/`, `stories/`, `rounds/`).
- [x] **AC-03 (Inspeção de Status com Rich):** `bombe mission status` localiza a missão ativa no diretório e imprime tabela formatada contendo ID, título, status e quadro de rounds.
- [x] **AC-04 (Encerramento com Gate de DoD):** `bombe mission end` valida se todos os rounds estão concluídos; se houver pendência, aborta com erro. Em caso aprovado, atualiza status para `completed` e grava timestamp de término.

---

## 5. Definition of Done (DoD)
- [x] Módulos `src/bombe_code/cli/commands/mission.py` e `src/bombe_code/orchestration/mission_engine.py` criados e integrados à CLI raiz em `src/bombe_code/cli/main.py`.
- [x] Modelos Pydantic V2 `MissionState` e `MissionStatus` em `src/bombe_code/domain/contracts/mission.py`.
- [x] Suíte de testes `tests/unit/test_mission_lifecycle.py` passando com 100% de sucesso usando `tmp_path`.
- [x] Zero ocorrências de `NotImplementedError`, `pass` ou stubs em código de produção.
- [x] Conformidade de linter com Ruff e tipagem com Mypy.

---

## 6. Notas Técnicas & Contratos

### 6.1 Contrato da CLI (Subcomandos Typer)
```text
bombe mission new "<demanda>" [--project-dir PATH]
bombe mission status [--project-dir PATH]
bombe mission end [--project-dir PATH] [--force-abort]
```

### 6.2 Estrutura de Código & SRF Check
| Função / Método | Assinatura | Responsabilidade | Limite |
|---|---|---|---|
| `MissionLifecycleEngine.assert_no_open_mission` | `(project_dir: Path) -> None` | Valida ausência de missão ativa no filesystem | < 25 linhas |
| `MissionLifecycleEngine.get_next_mission_id` | `(project_dir: Path) -> str` | Calcula próximo ID sequencial zero-padded | < 20 linhas |
| `MissionLifecycleEngine.init_mission` | `(project_dir: Path, demand: str) -> MissionState` | Gera scaffold e persiste mission.md | < 30 linhas |
| `MissionLifecycleEngine.get_active_mission` | `(project_dir: Path) -> MissionState | None` | Localiza e desserializa a missão ativa | < 25 linhas |
| `MissionLifecycleEngine.complete_mission` | `(project_dir: Path, force: bool) -> MissionState` | Valida DoD e finaliza a missão | < 30 linhas |

**SRF Check:**
- [x] Nenhuma função possui "e" no nome.
- [x] Cada função possui uma responsabilidade única.
- [x] Nenhuma função excede 30 linhas.

### 6.3 O que NÃO Fazer (Anti-padrões)
- ⛔ NÃO permitir criar pasta de missão sem validar se outra missão está aberta.
- ⛔ NÃO guardar estado de missão apenas em memória ou variáveis globais.
- ⛔ NÃO encerrar missão silenciosamente se houver rounds com pendência de DoD sem flag `--force-abort`.

---

## 7. Dependências
- **Blocked by:** Round 0 da MISSION-02 aprovado.
- **Required by:** `STORY-010` (Rounds Manuais) e `STORY-011` (Rounds Autônomos).
