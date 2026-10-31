---
id: STORY-008
title: "Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local"
epic_id: EP-04
round: ROUND-8
agent: "@fowler"
estimation: 4h
status: done
type: e2e
layer: backend
depends_on:
  - STORY-007
tags:
  - e2e
  - contingency
  - zai-429
  - resilience
  - validation
---

# STORY-008 — Teste E2E de Contingência Real com Cota Z.ai Esgotada e Queima Local

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado  
**Critérios INVEST:** Atendidos  
**Prioridade:** Crítica / Fechamento da MISSION-01  

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado  
**Seções Técnicas:** OK (Scope, Interface, Slices Verticais TDD, SRF Check, Anti-Padrões, Resiliência E2E)  
**Notas Técnicas:** Fatiamento vertical atômico validado. O teste E2E certifica a integridade da contingência real (429 -> Circuit Breaker -> Fallback vLLM :18096 < 2.0s). Engenheiro de Testes (@fowler) autorizado para queima TDD estrita (RED -> GREEN -> REFACTOR).

---

## 1. Scope

**O que faz:**
Implementa a suíte completa de teste E2E em `tests/e2e/test_contingency_mission.py` validando o fluxo de contingência real ponta a ponta: chamada ao provedor cloud Z.ai rejeitada com HTTP 429, interceptação silenciosa sem interrupção nem stack trace, persistência atômica do estado `exhausted` e `locked_until` em `quota_state.json`, comutação dinâmica em tempo < 2.0s para o motor `vllm-local` na porta 18096 e inferência local bem-sucedida com resultado 100% verde (passed).

**O que NÃO faz:**
- ❌ Não adiciona saldo comercial nem recarrega chaves de API da Z.ai.
- ❌ Não substitui as suítes de testes unitários existentes em `tests/unit/` do Bombe Code.
- ❌ Não altera assinaturas públicas dos módulos de produção consolidados nos rounds anteriores.

**Limites:**
- [x] Apenas camada de teste E2E em `tests/e2e/test_contingency_mission.py` e fixtures associadas.
- [x] Zero modificações em pastas de runtime do Bombe Core (`.agents/`, `CLAUDE.md`, `.bombeconfig`).
- [x] Zero mocks em código de produção em `src/bombe_code/`.

---

## 2. Interface (Input / Output)

### Contrato do Teste E2E (`tests/e2e/test_contingency_mission.py`)
```python
# Cenários assíncronos executáveis via pytest
async def test_contingency_failover_z_ai_429_to_local_vllm_e2e(tmp_path: Path) -> None: ...
async def test_contingency_persists_quota_state_json_atomically(tmp_path: Path) -> None: ...
async def test_contingency_short_circuits_subsequent_calls_to_local(tmp_path: Path) -> None: ...
async def test_contingency_local_vllm_produces_green_completion(tmp_path: Path) -> None: ...
```

### Regras de Validação & Invariantes:
- **AC-01 (Interceptação 429):** O erro HTTP 429 da Z.ai deve ser capturado pelo `HybridRouter` sem propagação de exceção para a camada superior e sem exibição de stack trace.
- **AC-02 (Latência de Comutação):** O intervalo entre a detecção do erro e a conclusão da chamada de fallback para `vllm-local` deve ser estritamente `< 2.0s`.
- **AC-03 (Execução Local Green):** A inferência de contingência deve invocar o endpoint local `http://127.0.0.1:18096/v1`, completando o ciclo com status de sucesso.
- **AC-04 (Persistência Atômica):** O arquivo físico `quota_state.json` deve registrar `providers.cloud_zai.status == "exhausted"` com `last_error_code == 429` e `locked_until > now()`.

---

## 3. Slices Verticais de Implementação

### SLICE-01: Suíte de Teste E2E de Contingência e Failover Cloud -> Local
- **Tipo:** Backend / E2E (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Complexity Score:** 2 (Pleno)
- **Arquivo de Teste:** `tests/e2e/test_contingency_mission.py`
- **Módulos Exercitados em Produção:**
  - `src/bombe_code/routing/quota_manager.py`
  - `src/bombe_code/routing/router.py`
  - `src/bombe_code/providers/local_vllm.py`
  - `src/bombe_code/providers/protocol.py`
- **Critérios de Aceite Cobertos:** AC-01, AC-02, AC-03, AC-04
- **Escopo Técnico:**
  1. Criação do diretório `tests/e2e/` e arquivo `tests/e2e/test_contingency_mission.py`.
  2. Implementação de cenário reproduzindo chamada Z.ai com HTTP 429 / `QuotaExhaustedError`.
  3. Asserção determinística de comutação para `vllm-local` (:18096) com medição de tempo (`duration < 2.0s`).
  4. Inspeção forense do arquivo `quota_state.json` validando integridade do schema Pydantic V2 (`QuotaState`).
  5. Asserção de curto-circuito em chamadas subsequentes enquanto o lock de 3h estiver vigente.
  6. Validação de geração de output textual de inferência sem falhas.

---

## 4. Estrutura de Código & SRF Check

**Funções de Teste em `tests/e2e/test_contingency_mission.py`:**

| Função | Assinatura | Responsabilidade | Limite |
|---|---|---|---|
| `test_contingency_failover_z_ai_429_to_local_vllm_e2e` | `async (tmp_path: Path) -> None` | Valida fluxo completo 429 -> local com tempo < 2.0s | < 30 linhas |
| `test_contingency_persists_quota_state_json_atomically` | `async (tmp_path: Path) -> None` | Valida persistência física e schema do quota_state.json | < 25 linhas |
| `test_contingency_short_circuits_subsequent_calls_to_local` | `async (tmp_path: Path) -> None` | Valida bypass de rede cloud quando provedor está em lock | < 25 linhas |
| `test_contingency_local_vllm_produces_green_completion` | `async (tmp_path: Path) -> None` | Valida inferência local completando com sucesso | < 25 linhas |

**SRF Check (pré-implementação):**
- [x] Nenhuma função acima tem "e" no nome.
- [x] Cada função possui uma única responsabilidade de validação.
- [x] Nenhuma função excede o limite estrito de 30 linhas.

---

## 5. Regras de Implementação & Anti-Padrões

### Regras Determinísticas:
1. Utilizar `pytest.mark.anyio` para assincronismo idiomático compatível com a suíte existente.
2. Usar `tmp_path` para isolar a persistência de `quota_state.json`, garantindo contaminação zero do diretório do usuário.
3. Utilizar medição precisa de relógio monotônico (`time.monotonic()`) para garantir que o failover ocorre em `< 2.0s`.
4. Garantir tipagem estrita total compatível com `mypy --strict`.

### Anti-Padrões Proibidos:
- ⛔ PROIBIDO usar `dependency_overrides` simulando integração sem testar o roteador real.
- ⛔ PROIBIDO criar mocks voláteis em memória que não exercitem a escrita em disco de `quota_state.json`.
- ⛔ PROIBIDO aceitar testes com tolerância a vazamento de exceções ou prints de stack trace.
- ⛔ PROIBIDO adicionar delays artificiais (`sleep`) desnecessários que aumentem o tempo de execução da suíte.

---

## 6. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Simulação/Captura 429):** A chamada rejeitada com HTTP 429 pelo provedor cloud deve ser interceptada sem crash da aplicação nem vazamento de stack trace.
- **AC-02 (Transição de Roteamento em Tempo Real):** O log e telemetria devem comprovar a transição `Cloud (Z.ai) -> Local vLLM (18096)` em tempo < 2.0s.
- **AC-03 (Execução Local Green):** A inferência local deve ser acionada, os chunks de completion recebidos e o resultado validado como 100% verde (passed).
- **AC-04 (Persistência de Estado):** O arquivo `quota_state.json` deve registrar o provedor `cloud_zai` em estado `exhausted` com `locked_until` ativo e correspondente ao TTL configurado.

---

## 7. Definition of Done (DoD)
- [x] Teste E2E implementado em `tests/e2e/test_contingency_mission.py` e passando na suíte de testes (`pytest tests/e2e/test_contingency_mission.py -v`).
- [x] Verificação de 100% dos testes verdes sem dependência de credenciais reais externas ativas.
- [x] Ausência de stubs, bodies vazios (`pass`, `...`) ou decorators cosméticos.
- [x] Tipagem estrita validada via `mypy --strict`.
- [x] Code review do diff atômico aprovado pelo Tech Lead (@unclebob).
- [x] Validação final do Round 8 e encerramento da MISSION-01 chancelados por @unclebob e @david.

## 8. Code Review & Approval
| Data | Reviewer | Status | Notas |
| :---: | :---: | :---: | :--- |
| 2026-10-31 | @hoare | APPROVED | Story compliance 100% validada (AC-01 a AC-04 rastreáveis no código de teste). |
| 2026-10-31 | @unclebob | APPROVED | Gate arquitetural aprovado nos 5 eixos. Resiliência atestada, failover < 2.0s e zero débito técnico. |

## 9. Dependências
- **Bloqueado por:** `STORY-007` (Round 7 concluído).
- **Desbloqueia:** Homologação e encerramento formal da MISSION-01.
