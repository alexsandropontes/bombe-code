---
id: STORY-013
title: "Equalização de Comandos Standalone e Governança"
epic_id: EP-04
round: ROUND-5
agent: "@barbara"
estimation: 3h
status: validated
type: feature
layer: backend
complexity: 2
depends_on: ["STORY-012"]
tags:
  - standalone-commands
  - project-governance
  - ship-engine
  - cli-dispatch
---

# STORY-013 — Equalização de Comandos Standalone e Governança

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado
**Critérios INVEST:** Atendidos
**Prioridade:** Essencial / Bloqueante para Round 5

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (scope, interface, validações, SRF, anti-padrões, contratos de teste)
**Notas Técnicas:** Decomposição dos comandos de governança e standalone em `project.py` (`project configure`, `project ship`) e `standalone.py` (`mode`, `task`, `rca`, `review`, `simplify`, `status-report`).

---

## 1. Contexto de Negócio
Além das rotinas de ciclo de vida de missões e rounds, a equipe de engenharia e os operadores necessitam de ferramentas auxiliares desvinculadas de missões para configuração de ambiente, promoção de código via Git e análise técnica sob demanda, em total conformidade com a Categoria B e C da Constituição Bombe Core.

---

## 2. Escopo

**O que faz:**
Implementa os submódulos Typer `src/bombe_code/cli/commands/project.py` e `src/bombe_code/cli/commands/standalone.py`, oferecendo:
- `bombe project configure`: setup de paths, stack tecnológica e guardrails.
- `bombe project ship [env]`: promoção protegida de branches Git com execução prévia de testes.
- `bombe mode [slice-code | vibe-code]`: comutação de modo com auditoria no `.bombeconfig`.
- `bombe task '<desc>'`: despacho avulso para subagentes via Protocolo Garçom.
- `bombe rca '<incidente>'`: Root Cause Analysis determinística.
- `bombe review [alvo]`: code review avulso multi-eixo.
- `bombe simplify [alvo]`: refatoração para redução de complexidade.
- `bombe status-report`: relatório executivo geral do repositório.

**O que NÃO faz:**
- ❌ Não altera arquivos de configuração sem validação Pydantic.
- ❌ Não executa promoção Git se a suíte de testes estiver quebrada.

**Limites:**
- [x] Camada de comandos de apoio e governança.
- [x] Zero mocks em código de produção.
- [x] Testes unitários em `tests/unit/test_standalone_commands.py`.

---

## 3. User Story & Intenção do Usuário
**Como** Desenvolvedor ou Tech Lead,  
**Quero** executar tarefas pontuais, comutar modos operacionais e promover branches Git protegidas por testes,  
**Para que** eu tenha governança técnica completa sem atritos operacionais.

---

## 4. Acceptance Criteria (ACs Testáveis)
- [x] **AC-01 (Setup de Projeto):** `bombe project configure` valida e atualiza o `.bombeconfig` sem corromper chaves existentes.
- [x] **AC-02 (Promoção Protegida Git Ship):** `bombe project ship [env]` executa a suíte de testes antes do merge; se os testes falharem, a promoção é abortada com exit code 1.
- [x] **AC-03 (Comutação Auditada de Modo):** `bombe mode [modo]` comuta entre `slice-code` e `vibe-code` gravando `mode_origin` e `mode_migrated_at`.
- [x] **AC-04 (Despacho de Tasks Avulsas):** `bombe task '<desc>'` despacha para o subagente correto via Protocolo Garçom.
- [x] **AC-05 (Comandos de Qualidade Operacionais):** `bombe rca`, `bombe review`, `bombe simplify` e `bombe status-report` executam de forma standalone sem exigir missão ativa.

---

## 5. Definition of Done (DoD)
- [x] Sub-apps `project_app` e `standalone_app` registrados no `main.py`.
- [x] Motor `ShipEngine` em `src/bombe_code/orchestration/ship_engine.py` com proteção de testes pré-flight.
- [x] Suíte de testes `tests/unit/test_standalone_commands.py` passando com 100% de sucesso.
- [x] Código aprovado no Ruff e Mypy.

---

## 6. Notas Técnicas & Contratos

### 6.1 Contrato da CLI
```text
bombe project configure [--project-dir PATH]
bombe project ship [dev | hml | prd] [--project-dir PATH]
bombe mode [slice-code | vibe-code] [--project-dir PATH]
bombe task "<descrição>" [--agent @especialista] [--project-dir PATH]
bombe rca "<incidente>" [--project-dir PATH]
bombe review [TARGET_PATH] [--project-dir PATH]
bombe simplify [TARGET_PATH] [--project-dir PATH]
bombe status-report [--project-dir PATH]
```

### 6.2 Estrutura de Código & SRF Check
| Função / Método | Assinatura | Responsabilidade | Limite |
|---|---|---|---|
| `ShipEngine.promote_to_environment` | `(target: ShipTarget, project_dir: Path) -> PromotionResult` | Executa testes e merge seguro | < 30 linhas |
| `ShipEngine._run_pre_flight_tests` | `(project_dir: Path) -> bool` | Executa testes antes de push | < 20 linhas |
| `StandaloneEngine.switch_mode` | `(mode: str, project_dir: Path) -> ProjectConfig` | Altera modo com rastreabilidade | < 25 linhas |
| `StandaloneEngine.generate_status_report`| `(project_dir: Path) -> dict` | Compila métricas do repositório | < 25 linhas |

**SRF Check:**
- [x] Nenhuma função possui "e" no nome.
- [x] Cada função possui escopo delimitado.
- [x] Nenhuma função excede 30 linhas.

---

## 7. Dependências
- **Blocked by:** `STORY-012` (Wave Bridge).
- **Required by:** `STORY-014` (Suíte E2E).
