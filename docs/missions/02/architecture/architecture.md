---
title: "Arquitetura Técnica — Equalização de Comandos CLI, Typer Sub-Apps e Wave Bridge"
mission_id: MISSION-02
status: approved
approved_by: "@unclebob"
approved_at: "2026-10-31T18:00:00"
date: "2026-10-31"
author: "@unclebob"
version: "1.0.0"
maturity_level: enterprise-grade
scope_type: legacy-parity
tags:
  - architecture
  - cli-dispatch
  - typer
  - pydantic-v2
  - wave-bridge
  - round-engine
---

# Arquitetura Técnica — MISSION-02

## 1. Visão Geral e Princípios Arquiteturais

A MISSION-02 refatora a camada de comando e orquestração do Bombe Code para atingir 100% de paridade com as diretrizes do Bombe Core v4. A arquitetura segue os princípios de **Clean Architecture**, **SOLID** e **Hexagonal Ports & Adapters**.

### Princípios Inegociáveis:
1. **Separação Rígida entre Interface e Domínio:** Os módulos sob `src/bombe_code/cli/commands/` são adaptadores primários (Driving Adapters). Eles realizam apenas parsing de CLI, validação de argumentos e formatação de saída (via Rich). Toda a lógica de negócio reside nos motores de domínio (`MissionLifecycleEngine`, `RoundExecutionEngine`, `ShipEngine`).
2. **Invariante 1 Round = 1 Story:** O motor de rounds proíbe a atribuição de mais de uma história por round.
3. **Porteiro Atômico de Missão Única (WIP = 1):** O filesystem (`docs/missions/`) atua como fonte da verdade; tentativas de abrir uma nova missão com outra aberta resultam em erro bloqueante.
4. **Wave Bridge Desacoplada e Pedagógica:** Interceptador que não duplica lógica, despachando programaticamente para os novos comandos canônicos enquanto emite aviso Rich educativo.
5. **Zero Mocks em Produção:** Proibição de stubs, `pass` ou stores voláteis simulando execução real em `src/bombe_code/`.

---

## 2. Visão de Componentes e Módulos CLI

```mermaid
flowchart TD
    subgraph CLI["CLI Entrypoint: src/bombe_code/cli/main.py"]
        RootTyper["Typer App Root ('bombe')"]
    end

    subgraph SubApps["Command Domains: src/bombe_code/cli/commands/"]
        MissionApp["mission.py\n(mission_app)"]
        RoundApp["round.py\n(round_app)"]
        ProjectApp["project.py\n(project_app)"]
        StandaloneApp["standalone.py\n(standalone_app)"]
        WaveBridge["wave_bridge.py\n(wave_app interceptor)"]
    end

    subgraph CoreEngines["Core Domain Engines: src/bombe_code/orchestration/"]
        MissionEngine["MissionLifecycleEngine\n(assert_no_open_mission, init, end)"]
        RoundEngine["RoundExecutionEngine\n(start, burn, review, validate, full, all)"]
        ShipEngine["ShipEngine\n(branch validation, test gate, git promotion)"]
    end

    subgraph DomainModels["Data Contracts (Pydantic V2): src/bombe_code/domain/"]
        MissionState["MissionState"]
        RoundState["RoundState"]
        WaveBridgeRedirect["WaveBridgeRedirect"]
        ShipTarget["ShipTarget"]
    end

    RootTyper -->|add_typer 'mission'| MissionApp
    RootTyper -->|add_typer 'round'| RoundApp
    RootTyper -->|add_typer 'project'| ProjectApp
    RootTyper -->|standalone commands| StandaloneApp
    RootTyper -->|add_typer 'wave' (compat)| WaveBridge

    MissionApp --> MissionEngine
    RoundApp --> RoundEngine
    ProjectApp --> ShipEngine
    WaveBridge -.->|programmatic dispatch| RoundApp
    WaveBridge -.->|programmatic dispatch| MissionApp
    WaveBridge -.->|programmatic dispatch| ProjectApp

    MissionEngine --> MissionState
    RoundEngine --> RoundState
    WaveBridge --> WaveBridgeRedirect
    ShipEngine --> ShipTarget
```

### 2.1. Estrutura de Diretórios de Comandos

```
src/bombe_code/
├── cli/
│   ├── __init__.py
│   ├── main.py                    # Entrypoint Typer limpo (< 100 linhas)
│   └── commands/
│       ├── __init__.py
│       ├── mission.py             # mission_app: new, status, end
│       ├── round.py               # round_app: start, burn, review, validate, full, all, status
│       ├── wave_bridge.py         # wave_app: interceptor amigável com Rich banner
│       ├── project.py             # project_app: configure, ship
│       └── standalone.py          # mode, task, rca, review, simplify, status-report
├── domain/
│   ├── contracts/
│   │   ├── __init__.py
│   │   ├── mission.py             # MissionState, MissionStatus
│   │   ├── round.py               # RoundState, SliceState, RoundStatus
│   │   ├── wave_bridge.py         # WaveBridgeRedirect, LegacyWaveCommand
│   │   └── ship.py                # ShipTarget, PromotionResult
├── orchestration/
│   ├── mission_engine.py          # MissionLifecycleEngine & assert_no_open_mission()
│   ├── engine.py                  # RoundExecutionEngine (evolução)
│   └── ship_engine.py             # ShipEngine
```

---

## 3. Contratos de Dados (Pydantic V2)

Os contratos de dados asseguram tipagem estrita, imutabilidade operacional e serialização segura com o filesystem YAML.

### 3.1. `MissionState` & `MissionStatus`
```python
from __future__ import annotations
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, field_validator

class MissionStatus(str, Enum):
    OPEN = "open"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class MissionMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(..., pattern=r"^MISSION-\d{2,}$")
    title: str = Field(..., min_length=5)
    status: MissionStatus = MissionStatus.OPEN
    maturity_level: str = "enterprise-grade"
    scope_type: str = "legacy-parity"
    created_at: str
    completed_at: str | None = None

class MissionState(BaseModel):
    model_config = ConfigDict(frozen=False)
    metadata: MissionMetadata
    mission_dir: Path
    active_round: int | None = None
    rounds_count: int = Field(default=0, ge=0)

    @field_validator("mission_dir")
    @classmethod
    def validate_mission_dir(cls, v: Path) -> Path:
        if not v.is_dir() and not v.parent.is_dir():
            raise ValueError(f"Diretório de missão inválido: {v}")
        return v
```

### 3.2. `RoundState` & `SliceState`
```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class RoundStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DOR_READY = "dor_ready"
    BURNING = "burning"
    REVIEWING = "reviewing"
    VALIDATED = "validated"

class SliceType(str, Enum):
    BACKEND_TDD = "backend_tdd"
    FRONTEND_CONSTRUCTION = "frontend_construction"

class SliceState(BaseModel):
    model_config = ConfigDict(frozen=True)
    slice_id: str
    name: str
    type: SliceType
    status: str = "pending"  # red, green, refactor, done

class RoundState(BaseModel):
    model_config = ConfigDict(frozen=False)
    round_number: int = Field(..., ge=0)
    story_id: str = Field(..., pattern=r"^STORY-\d{3,}$")
    status: RoundStatus = RoundStatus.PENDING
    slices: list[SliceState] = Field(default_factory=list)
    dor_ready: bool = False
    dod_validated: bool = False
    started_at: str | None = None
    completed_at: str | None = None
```

### 3.3. `WaveBridgeRedirect`
```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class LegacyWaveCommand(str, Enum):
    START = "start"
    RUN = "run"
    CYCLE = "cycle"
    VALIDATE = "validate"
    STATUS = "status"
    PROMOTE = "promote"
    END = "end"

class WaveBridgeRedirect(BaseModel):
    model_config = ConfigDict(frozen=True)
    legacy_command: str
    canonical_target: str
    mapped_args: list[str] = Field(default_factory=list)
    explanation: str
```

### 3.4. `ShipTarget` & `PromotionResult`
```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, ConfigDict

class ShipEnvironment(str, Enum):
    DEV = "dev"
    HML = "hml"
    PRD = "prd"

class ShipTarget(BaseModel):
    model_config = ConfigDict(frozen=True)
    environment: ShipEnvironment
    source_branch: str = "working-ia"
    target_branch: str
    fast_forward_only: bool = False
    run_pre_flight_tests: bool = True

class PromotionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    success: bool
    source_commit: str
    target_branch: str
    message: str
```

---

## 4. Arquitetura de Módulos CLI Detalhada

### 4.1. `src/bombe_code/cli/commands/mission.py`
Responsável pelos comandos de ciclo de vida da missão:
- `bombe mission new '<demanda>'`:
  1. Invoca `MissionLifecycleEngine.assert_no_open_mission(project_dir)`.
  2. Determina o próximo ID de missão (`01`, `02`, ...).
  3. Inicializa o scaffold físico em `docs/missions/NN/` (`mission.md`, `prd/`, `architecture/`).
  4. Executa o Round 0 (Upstream Macro).
  5. Retorna status `active` com resumo em tabela Rich.
- `bombe mission status`:
  1. Localiza a missão ativa ou mais recente.
  2. Apresenta o Kanban consolidado dos rounds e status dos gates.
- `bombe mission end`:
  1. Valida se todos os rounds estão no status `validated`.
  2. Bloqueia com erro se houver pendências de DoD.
  3. Atualiza status para `completed` e arquiva a missão.

### 4.2. `src/bombe_code/cli/commands/round.py`
Expansão integral da Tríade de Rounds:
- `bombe round start [N]`: Inicia round, valida DoD de N-1, gera DoR e **para deterministicamente**.
- `bombe round burn [N]`: Queima atômica TDD dos slices (Slice Backend RED/GREEN/REFACTOR + Slice Frontend).
- `bombe round review [N]`: Valida compliance técnica (@hoare) e qualidade arquitetural (@unclebob).
- `bombe round validate [N]`: Valida critérios de aceitação e DoD (@david).
- `bombe round full [N]`: Orquestra Upstream -> Burn -> Review -> Validate para o round N e **para ao final**.
- `bombe round all`: Executa em loop contínuo desatendido todos os rounds pendentes até o encerramento da missão.
- `bombe round status`: Apresenta o Kanban detalhado do round corrente e progresso de slices.

### 4.3. `src/bombe_code/cli/commands/wave_bridge.py`
Interceptor de compatibilidade para `bombe wave <cmd>`:
- Intercepta comandos legados:
  - `bombe wave start [ID]` -> `bombe round start [N]`
  - `bombe wave run` -> `bombe round all`
  - `bombe wave cycle [ID]` -> `bombe round burn [N]`
  - `bombe wave validate` -> `bombe round validate`
  - `bombe wave status` -> `bombe round status`
  - `bombe wave promote [env]` -> `bombe project ship [env]`
  - `bombe wave end` -> `bombe mission end`
- Emite painel Rich educativo formatado:
  ```text
  ┌─ [AVISO DE TRANSIÇÃO] ────────────────────────────────────────────────────────┐
  │ O conceito de 'ONDA' foi substituído por 'ROUNDS' e 'SLICES' no Bombe Core v4.  │
  │ Seu comando foi redirecionado automaticamente com sucesso:                     │
  │   bombe wave run  ──>  bombe round all                                        │
  │ Dica: Atualize seus scripts para a nova sintaxe canônica 'bombe round ...'.   │
  └───────────────────────────────────────────────────────────────────────────────┘
  ```
- Executa o despacho programático chamando diretamente os handlers do respectivo módulo (`round.py`, `mission.py`, `project.py`).

### 4.4. `src/bombe_code/cli/commands/project.py`
- `bombe project configure`: Configuração de paths, stack tecnológica e validação de `.bombeconfig`.
- `bombe project ship [env]`: Roteador de promoção de branches (`dev`, `hml`, `prd`). Executa testes pré-flight antes de push/merge.

### 4.5. `src/bombe_code/cli/commands/standalone.py`
Comandos auxiliares desvinculados do ciclo estrito de rounds:
- `bombe mode [vibe-code | slice-code]`: Alternância auditada com validação de impacto.
- `bombe task '<desc>'`: Despacho pontual via Protocolo Garçom.
- `bombe rca '<incidente>'`: Root Cause Analysis determinística (5 Porquês + Ishikawa).
- `bombe review [alvo]`: Code review cirúrgico sob demanda.
- `bombe simplify [alvo]`: Refatoração focada em redução de complexidade ciclomática.
- `bombe status-report`: Relatório executivo do repositório e saúde da esteira.

---

## 5. Architecture Decision Records (ADRs)

### ADR-01: Adoção do Typer Sub-App Pattern para Domínios de Comandos
- **Status:** Aprovado
- **Contexto:** O `src/bombe_code/cli/main.py` acumulava mais de 1.100 linhas em um único arquivo, gerando violações severas do Single Responsibility Principle (SRP) e dificuldade de manutenção e teste de comandos individuais.
- **Decisão:** Decompor a CLI em submódulos Typer independentes sob `src/bombe_code/cli/commands/` (`mission.py`, `round.py`, `project.py`, `wave_bridge.py`, `standalone.py`) agregados na raiz via `app.add_typer(...)`.
- **Consequências:**
  - *Positivas:* Código modular, testabilidade isolada por domínio, inicialização preguiçosa (lazy loading) e manutenção cirúrgica.
  - *Mitigações:* Manter consistência na injeção do parâmetro global `--project-dir`.

### ADR-02: Wave Bridge com Redirecionamento Programático e Deprecation Warning via Rich
- **Status:** Aprovado
- **Contexto:** Scripts de CI/CD e operadores legados ainda dependem de chamadas `bombe wave ...`. Uma remoção abrupta (Breaking Change) paralisaria fluxos existentes.
- **Decisão:** Implementar a `WaveBridge` em `wave_bridge.py` que intercepta qualquer invocação de `bombe wave`, renderiza um banner visual instrutivo via Rich Console e despacha programaticamente a execução para o handler correspondente da nova arquitetura.
- **Consequências:**
  - *Positivas:* Zero quebra de compatibilidade (0% de regressions), transição suave e pedagógica para a comunidade.
  - *Mitigações:* A camada é puramente de roteamento; nenhuma lógica de negócio ou estado de onda é mantido.

### ADR-03: Porteiro Atômico de Missão Única Baseado em Filesystem (`assert_no_open_mission`)
- **Status:** Aprovado
- **Contexto:** A execução desordenada de comandos de criação de missão (`bombe mission new`) sem encerramento da missão anterior corrompe a árvore `docs/missions/` e sobrecarrega a governança de branches Git.
- **Decisão:** Estabelecer a função guardiã `assert_no_open_mission(project_dir: Path)` que inspeciona todos os manifestos `docs/missions/*/mission.md`. Se qualquer missão possuir status `open`, `active` ou `in_progress`, o comando aborta atomicamente com código de saída 1 antes de criar qualquer arquivo.
- **Consequências:**
  - *Positivas:* Integridade referencial absoluta no repositório, disciplina operacional (WIP = 1) e idempotência comprovável por testes.
  - *Mitigações:* Se o usuário desejar cancelar ou reabrir, deve utilizar explicitamente os comandos de gestão de ciclo de vida (`mission end` ou parâmetro `--force-abort`).

### ADR-04: Extirpação do Motor Monolítico de Ondas em favor do `RoundExecutionEngine`
- **Status:** Aprovado
- **Contexto:** O antigo `WaveOrchestrator` acumulava fatiamento de ondas, persistência local SQLite proprietária e passos de esteira acoplados em lotes.
- **Decisão:** Extirpar o motor de ondas e consolidar a orquestração no `RoundExecutionEngine`, apoiado no `MissionLifecycleEngine`, operando diretamente sobre os artefatos de markdown canônicos em `docs/missions/NN/`.
- **Consequências:**
  - *Positivas:* Adoção nativa do paradigma 1 Round = 1 Story, auditorias atômicas de diffs, eliminação de código morto e alinhamento total com o Bombe Core v4.
  - *Mitigações:* Adaptação das suítes de testes antigas para utilizarem as primitivas de round.

---

## 6. Matriz de Segurança, Zero Mocks e Limites de Recursos

### 6.1. Segurança na Execução CLI (Hardening)
- **Sanitização de Entradas:** Todas as strings de demanda e IDs recebidas via CLI são validadas contra injeção de shell (evitando execução com `shell=True` em chamadas Git ou testes).
- **Tratamento de Argumentos Nulos ou Maliciosos:** Bloqueio preventivo de caminhos fora da raiz do projeto (`project_dir.resolve()` validado contra traversal attacks).

### 6.2. Política Estrita de Zero Mocks em Produção (Gate G3/G4)
- Em conformidade com o padrão `enterprise-grade`, o diretório `src/bombe_code/` não contém mocks, fake repositories, stubs `pass` ou exceções cosméticas `NotImplementedError`.
- Os testes de integração da CLI operam contra processos reais de terminal (`subprocess.run` / `CliRunner` do Typer) e estruturas reais temporárias no filesystem via fixtures isoladas.

### 6.3. Limites de Recursos e Resiliência
- **Timeouts Controlados:** Operações de build, teste e chamadas de subprocessos possuem timeout rígido (default: 300s) para evitar loops infinitos em execuções desatendidas (`round all`).
- **Recuperação de Falhas no Pipeline:** Em `round all`, se qualquer round falhar no teste TDD ou na revisão de arquitetura, o pipeline é interrompido imediatamente com diagnóstico claro, preservando o estado do repositório sem corrupção.
