---
id: STORY-012
title: "Wave Bridge e Interceptor de Depreciação"
epic_id: EP-03
round: ROUND-4
agent: "@barbara"
estimation: 3h
status: done
type: feature
layer: backend
complexity: 2
depends_on: ["STORY-011"]
tags:
  - wave-bridge
  - deprecation-warning
  - backward-compatibility
  - rich-ui
---

# STORY-012 — Wave Bridge e Interceptor de Depreciação

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado
**Critérios INVEST:** Atendidos
**Prioridade:** Essencial / Bloqueante para Round 4

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (scope, interface, validações, SRF, anti-padrões, contratos de teste)
**Notas Técnicas:** Interceptor `wave_bridge.py` acoplado à CLI Typer. Exibe banner pedagógico Rich e redireciona programaticamente chamadas legadas `bombe wave ...` para as primitivas de `round`, `mission` e `project`.

---

## 1. Contexto de Negócio
Operadores de terminal e rotinas automatizadas legadas foram construídas utilizando comandos `bombe wave ...`. Com a extinção formal do conceito de ondas e a padronização em Rounds e Slices, é mandatório interceptar essas invocações, emitir um aviso visual educativo em console e despachar a execução de forma transparente para a instrução moderna equivalente sem quebrar scripts.

---

## 2. Escopo

**O que faz:**
Cria o submódulo `src/bombe_code/cli/commands/wave_bridge.py` registrado como sub-app `wave` na CLI raiz. Intercepta os 7 comandos legados (`start`, `run`, `cycle`, `validate`, `status`, `promote`, `end`), exibe painel Rich informativo sobre a transição para Rounds/Slices e repassa a chamada programaticamente para os handlers de `round.py`, `mission.py` e `project.py`.

**O que NÃO faz:**
- ❌ Não executa motores legados de ondas ou SQLite proprietário.
- ❌ Não adiciona novos comandos de ondas.

**Limites:**
- [x] Apenas camada de interceptação e bridge de compatibilidade.
- [x] Zero mocks em código de produção.
- [x] Testes unitários e de integração em `tests/unit/test_wave_bridge.py`.

---

## 3. User Story & Intenção do Usuário
**Como** Desenvolvedor ou Mantenedor de Scripts Legados,  
**Quero** executar comandos `bombe wave ...` sem que ocorra erro de comando inexistente,  
**Para que** minha rotina continue funcionando e eu aprenda a sintaxe moderna canônica via terminal.

---

## 4. Acceptance Criteria (ACs Testáveis)
- [x] **AC-01 (Banner Educativo de Depreciação):** Toda invocação de `bombe wave <cmd>` renderiza um painel Rich informando que "ondas" foram substituídas por "rounds e slices" no Core v4.
- [x] **AC-02 (Redirecionamento 1:1 de `wave start`):** `bombe wave start [ID]` mapeia o ID para número de round e despacha para `bombe round start [N]`.
- [x] **AC-03 (Redirecionamento 1:1 de `wave run`):** `bombe wave run` despacha para `bombe round all`.
- [x] **AC-04 (Redirecionamento 1:1 de `wave cycle`):** `bombe wave cycle [ID]` despacha para `bombe round burn [N]`.
- [x] **AC-05 (Redirecionamento de `validate`, `status`, `promote`, `end`):** Mapeamento estrito para `round validate`, `round status`, `project ship` e `mission end`.
- [x] **AC-06 (Preservação de Exit Code):** O código de saída POSIX retornado pela bridge é idêntico ao comando canônico despachado.

---

## 5. Definition of Done (DoD)
- [x] Sub-app `wave_app` registrado no entrypoint Typer `src/bombe_code/cli/main.py`.
- [x] Contratos `WaveBridgeRedirect` e `LegacyWaveCommand` em `src/bombe_code/domain/contracts/wave_bridge.py`.
- [x] Suíte `tests/unit/test_wave_bridge.py` testando o redirecionamento dos 7 comandos legados.
- [x] Código aprovado no Ruff e Mypy.

---

## 6. Notas Técnicas & Contratos

### 6.1 Mapeamento Canônico de Redirecionamento
```text
bombe wave start [ID]    -->  bombe round start [N]
bombe wave run           -->  bombe round all
bombe wave cycle [ID]    -->  bombe round burn [N]
bombe wave validate      -->  bombe round validate
bombe wave status        -->  bombe round status
bombe wave promote [ENV] -->  bombe project ship [ENV]
bombe wave end           -->  bombe mission end
```

### 6.2 Estrutura de Código & SRF Check
| Função / Método | Assinatura | Responsabilidade | Limite |
|---|---|---|---|
| `render_wave_deprecation_banner` | `(legacy: str, canonical: str) -> None` | Imprime painel Rich formatado | < 20 linhas |
| `dispatch_wave_start` | `(round_id: int, project_dir: Path) -> None` | Intercepta e despacha round start | < 15 linhas |
| `dispatch_wave_run` | `(project_dir: Path) -> None` | Intercepta e despacha round all | < 15 linhas |
| `dispatch_wave_cycle` | `(round_id: int, project_dir: Path) -> None` | Intercepta e despacha round burn | < 15 linhas |
| `dispatch_wave_generic` | `(cmd: LegacyWaveCommand, ...) -> None` | Roteador genérico dos demais subcomandos | < 25 linhas |

**SRF Check:**
- [x] Nenhuma função possui "e" no nome.
- [x] Funções com menos de 25 linhas.
- [x] Despacho direto sem duplicar lógica de negócio.

---

## 7. Dependências
- **Blocked by:** `STORY-011` (Rounds Autônomos).
- **Required by:** `STORY-013` (Comandos Standalone) e `STORY-014` (Suíte E2E).
