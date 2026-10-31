---
id: STORY-005
title: "QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local"
epic_id: EP-02
round: ROUND-5
agent: "@barbara"
estimation: 4h
status: done
type: feature
layer: backend
depends_on:
  - STORY-004
tags:
  - quota-manager
  - circuit-breaker
  - failover
  - resilience
  - http-429
---

# STORY-005 — QuotaManager com Detecção de 429 e Failover Transparente Cloud -> Local

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado  
**Critérios INVEST:** Atendidos  
**Prioridade:** Essencial / Bloqueante para Round 5  

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado  
**Seções Técnicas:** OK (Scope, Interface Pydantic V2, Slices Verticais TDD, SRF Check, Anti-Padrões, Persistência Atômica, Zero Mocks em Prod)  
**Notas Técnicas:** Fatiamento vertical em 2 Slices aprovado com sucesso. Modelagem determinística de Circuit Breaker com failover < 2.0s. Dev Backend (@barbara) autorizada para início da queima TDD (RED -> GREEN -> REFACTOR).

---

## 1. Scope

**O que faz:**
Implementa o gerenciador de cotas `QuotaManager` com persistência física atômica em `~/.local/share/bombe-code/quota_state.json`, lógica de Circuit Breaker com bloqueio temporal configurável (`locked_until`, default 3 horas) e comutação graciosa imediata Cloud -> Local vLLM no `HybridRouter` ao interceptar status HTTP 429 ou `QuotaExhaustedError`, garantindo latência total de chaveamento inferior a 2.0s e ausência de stack trace para o desenvolvedor.

**O que NÃO faz:**
- ❌ Não realiza recarga financeira nem interação com APIs de faturamento de cartões.
- ❌ Não remove provedores de `providers.yaml`; apenas suspende temporariamente o tráfego via Circuit Breaker.
- ❌ Não implementa o parser de chamadas de ferramentas em markdown (`FallbackToolParser`, escopo da STORY-006).

---

## 2. Interface & Contratos de Dados

### 2.1 Modelos Pydantic V2 & Exceções (`src/bombe_code/routing/quota_manager.py`)
```python
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class QuotaExhaustedError(RuntimeError):
    """Exceção levantada quando um provedor atinge limite de cota ou rate limit 429."""

class ProviderQuotaStatus(BaseModel):
    """Estado auditável de cota de um provedor específico."""
    model_config = ConfigDict(frozen=True)

    status: Literal["healthy", "exhausted"] = "healthy"
    consecutive_failures: int = 0
    last_error_code: int | None = None
    last_error_message: str | None = None
    locked_until: datetime | None = None

class QuotaState(BaseModel):
    """Estado persistido global do gerenciador de cotas."""
    updated_at: datetime = Field(default_factory=lambda: datetime.now().astimezone())
    providers: dict[str, ProviderQuotaStatus] = Field(default_factory=dict)
```

---

## 3. Slices Verticais de Implementação

### SLICE-01: Modelos Pydantic V2 e `QuotaManager` com Persistência Atômica
- **Tipo:** Backend (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Complexity Score:** 2 (Pleno)
- **Arquivo de Teste:** `tests/unit/test_quota_failover.py`
- **Arquivo de Produção:** `src/bombe_code/routing/quota_manager.py`
- **Critérios de Aceite Cobertos:** AC-01, AC-02
- **Escopo Técnico:**
  - Definição de `QuotaExhaustedError`, `ProviderQuotaStatus` e `QuotaState`.
  - Implementação de `is_available`, `record_exhausted`, `reset` e `get_provider_status`.
  - Persistência física em `quota_state.json` com integridade atômica via `tempfile` + `os.replace`.
  - Validação de expiração temporal de `locked_until`.

### SLICE-02: Integração de Failover no `HybridRouter` e Interceptador Assíncrono
- **Tipo:** Backend (TDD Estrito: RED -> GREEN -> REFACTOR)
- **Complexity Score:** 2 (Pleno)
- **Arquivo de Teste:** `tests/unit/test_quota_failover.py`
- **Arquivo de Produção:** `src/bombe_code/routing/router.py`
- **Critérios de Aceite Cobertos:** AC-03, AC-04
- **Escopo Técnico:**
  - Atualização do `HybridRouter` para suportar injeção direta de `QuotaManager`.
  - Implementação de `execute_with_failover` interceptando HTTP 429 e `QuotaExhaustedError`.
  - Comutação transparente Cloud -> Local em tempo < 2.0s sem emissão de stack trace.
  - Registro de log estruturado de warning alertando sobre a cota esgotada.
  - Curto-circuito imediato: se `is_available(provider)` for falso, a requisição cloud é evitada completamente.

---

## 4. Acceptance Criteria (ACs Testáveis)
- **AC-01 (Detecção de Erro 429):** Ao receber HTTP 429 ou `QuotaExhaustedError`, o `QuotaManager` marca o provedor como `exhausted` e calcula a janela de bloqueio em `locked_until`.
- **AC-02 (Persistência Atômica de Estado):** O estado de contingência é persistido em `quota_state.json` com integridade estrutural e permissões seguras.
- **AC-03 (Chaveamento em Menos de 2s):** O tempo total entre a interceptação da falha de cota e a conclusão do fallback local é inferior a 2000ms.
- **AC-04 (Silenciamento de Exceção ao Usuário):** A falha de cota não aborta a operação nem exibe stack trace ao operador, completando com sucesso via cluster local.

---

## 5. Definition of Done (DoD)
- [x] Código implementado em `src/bombe_code/routing/quota_manager.py` e integrado ao `HybridRouter`.
- [x] Testes unitários cobrindo SLICE-01 e SLICE-02 passando em `tests/unit/test_quota_failover.py`.
- [x] Validação do arquivo `quota_state.json` contra o schema Pydantic V2 oficial.
- [x] Tipagem estrita aprovada com `mypy --strict` e zero warnings do `ruff`.
- [x] Ausência de stubs, dead code, prints soltos ou corpos vazios (`pass`, `...`).
- [x] Code review aprovado por @unclebob.

## 6. Code Review & Approval
| Data | Reviewer | Eixos Avaliados | Status | Notas |
| :--- | :--- | :--- | :--- | :--- |
| 2026-10-31 | @hoare | Story Compliance & Traceability | APPROVED | 100% dos ACs atendidos e verificados |
| 2026-10-31 | @unclebob | Correctness, Readability, Architecture, Security, Performance | APPROVED | Zero violações de SOLID; persistência atômica validada |

## 7. Dependências
- **Bloqueado por:** `STORY-004` (Round 4 concluído e validado).
- **Desbloqueia:** `STORY-006` (Round 6).
