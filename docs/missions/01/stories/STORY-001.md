---
id: STORY-001
title: "Migração de Configuração e Runtime Slice-Code"
epic_id: EP-01
round: ROUND-1
agent: "@fowler"
estimation: 2h
status: ready
type: refactor
layer: backend
complexity: 1
depends_on: []
tags:
  - configuration
  - bombeconfig
  - runtime
  - slice-code
  - enterprise-grade
---

# STORY-001 — Migração de Configuração e Runtime Slice-Code

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado
**Critérios INVEST:** Atendidos
**Prioridade:** Essencial / Bloqueante para Round 1

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (scope, interface, validações, SRF, anti-padrões, fatiamento em slices, contratos de teste)
**Notas Técnicas:** Fatiamento vertical atômico em 2 Slices de Complexidade Nível 1. Schema Pydantic V2 blindado com `InvalidModeError`.

---

## 1. Scope

**O que faz:**
Atualiza o schema declarativo `ProjectConfig` e o gerenciador `ProjectConfigManager` para adotar `mode: slice-code` como padrão soberano, incorporar os metadados de rastreabilidade histórica (`mode_origin` e `mode_migrated_at`), elevar o `delivery_target` default para `enterprise-grade`, rejeitar modos inválidos/descontinuados via `InvalidModeError` e fornecer suíte de testes unitários completa em `tests/unit/test_config.py`.

**O que NÃO faz:**
- ❌ Não altera prompts, workflows ou dossiês de agentes (escopo da `STORY-002`).
- ❌ Não altera contratos de provedores de LLM ou arquivos `providers.yaml` (escopo da `STORY-003`).
- ❌ Não implementa CLI de migração interativa ou comandos TUI (escopo da `STORY-007`).

**Limites:**
- [x] Apenas camada de configuração (`src/bombe_code/config/project_config.py`).
- [x] Apenas testes de unidade em `tests/unit/test_config.py`.
- [x] Zero alteração em runtime de agentes em `.agents/`.

---

## 2. Interface & Contratos de Dados

### 2.1 Modelo `ProjectConfig` & Exceções
```python
from __future__ import annotations
from pydantic import BaseModel, Field, field_validator

class InvalidModeError(ValueError):
    """Exceção levantada quando um modo não suportado ou extinto é configurado."""
    pass

class ProjectConfig(BaseModel):
    name: str = Field(default="bombe-project", description="Nome do projeto")
    type: str = Field(default="web", description="Tipo do projeto: web, api, mobile, cli, lib")
    backend_language: str = Field(default="python", description="Linguagem backend primária")
    frontend_stack: str = Field(default="react", description="Stack de interface frontend")
    root_src: str = Field(default="src/", description="Diretório raiz do código fonte")
    backend_path: str = Field(default="src/backend/", description="Subdiretório de código backend")
    frontend_path: str = Field(default="src/frontend/", description="Subdiretório de interface frontend")
    docs_root: str = Field(default="docs/", description="Diretório raiz de documentação")
    branch: str = Field(default="dev", description="Branch de trabalho da IA")
    mode: str = Field(default="slice-code", description="Modo de engenharia: slice-code ou vibe-code")
    mode_origin: str | None = Field(default=None, description="Modo de origem pré-migração (ex: tdd-code)")
    mode_migrated_at: str | None = Field(default=None, description="Timestamp ISO 8601 da migração")
    autonomy: str = Field(default="auto", description="Modo de autonomia: auto, semi-auto, manual")
    verbosity: str = Field(default="verbose", description="Verbosidade: verbose ou quiet")
    delivery_target: str = Field(
        default="enterprise-grade",
        description="Nível de maturidade: poc, mvp, enterprise-grade",
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid_modes = {"slice-code", "vibe-code"}
        if v not in valid_modes:
            raise InvalidModeError(
                f"Modo '{v}' é inválido ou foi descontinuado. Modos permitidos: {sorted(valid_modes)}"
            )
        return v
```

### 2.2 Regras de Validação e Migração em `ProjectConfigManager`
- `VALID_MODES = {"slice-code", "vibe-code"}`.
- Ao carregar `.bombeconfig` via `load()`:
  - Se `mode` for `"tdd-code"` ou `"spec-code"` e `mode_origin` estiver ausente: normaliza automaticamente definindo `mode = "slice-code"`, `mode_origin = raw_mode` e `mode_migrated_at = <iso_now>`.
  - Se `mode` for string não reconhecida fora dos modos válidos ou legados conhecidos, levanta `InvalidModeError`.
  - Ao salvar via `save()`: persiste ordenadamente `mode`, `mode_origin`, `mode_migrated_at` e `delivery_target`.

### 2.3 Exemplos de Entrada & Saída

```python
# Caso Válido (Default):
cfg = ProjectConfig()
assert cfg.mode == "slice-code"
assert cfg.delivery_target == "enterprise-grade"
assert cfg.mode_origin is None

# Caso Válido com Origem de Migração:
cfg = ProjectConfig(mode="slice-code", mode_origin="tdd-code", mode_migrated_at="2026-10-31T15:30:00Z")
assert cfg.mode == "slice-code"
assert cfg.mode_origin == "tdd-code"

# Caso Inválido (Modo Extinto direto no construtor sem tratamento):
try:
    ProjectConfig(mode="tdd-code")
except InvalidModeError as exc:
    print(exc)  # "Modo 'tdd-code' é inválido ou foi descontinuado..."
```

---

## 3. Estrutura de Código & SRF Check

### Funções e Métodos:

| Função / Método | Assinatura | Responsabilidade | Limite |
|---|---|---|---|
| `InvalidModeError.__init__` | `(self, message: str) -> None` | Inicialização da exceção de domínio | < 10 linhas |
| `ProjectConfig.validate_mode` | `(cls, v: str) -> str` | Validação determinística de modos permitidos | < 15 linhas |
| `ProjectConfigManager.load` | `(self) -> ProjectConfig` | Leitura, normalização e migração de `.bombeconfig` | < 30 linhas |
| `ProjectConfigManager._migrate_legacy_data` | `(self, raw_data: dict) -> dict` | Tratamento e migração de chaves legadas (`tdd-code`) | < 25 linhas |
| `ProjectConfigManager.save` | `(self, config: ProjectConfig) -> None` | Serialização YAML com novos campos de rastreabilidade | < 25 linhas |

**SRF Check (pré-implementação):**
- [x] Nenhuma função possui conjunção "e" no nome.
- [x] Cada função possui uma responsabilidade única e inequívoca.
- [x] Nenhuma função excede 30 linhas.

**Onde Modificar / Criar:**
- **Modificar:** `src/bombe_code/config/project_config.py`
- **Criar:** `tests/unit/test_config.py`

---

## 4. Fatiamento em Slices Verticais Atômicos

### 🔹 SLICE-01: Schema `ProjectConfig`, `InvalidModeError` & Validação Pydantic
- **Classificação:** Complexidade Nível 1 (Júnior).
- **Justificativa:** Refatoração pura de modelo em memória com Pydantic V2 sem acoplamento de I/O de disco.
- **Ciclo TDD:**
  1. **RED:** Criar `tests/unit/test_config.py` asserindo defaults `mode="slice-code"`, `delivery_target="enterprise-grade"` e levantamento de `InvalidModeError` para `mode="tdd-code"`. Executar `pytest tests/unit/test_config.py` e comprovar falha.
  2. **GREEN:** Atualizar classe `ProjectConfig` e definir `InvalidModeError` em `src/bombe_code/config/project_config.py`. Testes passam.
  3. **REFACTOR:** Limpar tipagem estrita e docstrings sem alterar comportamento.

### 🔹 SLICE-02: `ProjectConfigManager` — Migração em `load()` & Persistência em `save()`
- **Classificação:** Complexidade Nível 1 (Júnior).
- **Justificativa:** Manipulação determinística de arquivo YAML e preservação de metadados legados.
- **Ciclo TDD:**
  1. **RED:** Adicionar testes em `tests/unit/test_config.py` simulando `.bombeconfig` legado (`mode: tdd-code`) esperando migração automática em `load()` com `mode_origin="tdd-code"` e persistência completa em `save()`.
  2. **GREEN:** Implementar `_migrate_legacy_data` e atualizar `load()` e `save()` em `ProjectConfigManager`.
  3. **REFACTOR:** Extrair normalização de verbosidade e chaves para método auxiliar com < 25 linhas.

---

## 5. Contratos de Testes Unitários (`tests/unit/test_config.py`)

A suíte em `tests/unit/test_config.py` deve implementar estritamente os seguintes casos:

```python
import pytest
from pathlib import Path
from bombe_code.config.project_config import ProjectConfig, ProjectConfigManager, InvalidModeError

def test_project_config_defaults():
    """Valida defaults soberanos: slice-code e enterprise-grade."""
    cfg = ProjectConfig()
    assert cfg.mode == "slice-code"
    assert cfg.delivery_target == "enterprise-grade"
    assert cfg.mode_origin is None
    assert cfg.mode_migrated_at is None

def test_project_config_invalid_mode_raises():
    """Garante que modos inválidos ou legados levantem InvalidModeError diretamente."""
    with pytest.raises(InvalidModeError, match="descontinuado"):
        ProjectConfig(mode="tdd-code")
    with pytest.raises(InvalidModeError, match="descontinuado"):
        ProjectConfig(mode="spec-code")
    with pytest.raises(InvalidModeError, match="inválido"):
        ProjectConfig(mode="invalid-random-mode")

def test_project_config_valid_vibe_code():
    """Garante suporte ao modo vibe-code."""
    cfg = ProjectConfig(mode="vibe-code")
    assert cfg.mode == "vibe-code"

def test_config_manager_load_and_migrate_legacy(tmp_path: Path):
    """Testa leitura e migração transparente de arquivo legado tdd-code."""
    legacy_file = tmp_path / ".bombeconfig"
    legacy_file.write_text("mode: tdd-code\nproject:\n  name: legacy-app\n", encoding="utf-8")
    
    mgr = ProjectConfigManager(project_dir=str(tmp_path))
    cfg = mgr.load()
    
    assert cfg.mode == "slice-code"
    assert cfg.mode_origin == "tdd-code"
    assert cfg.mode_migrated_at is not None
    assert cfg.name == "legacy-app"

def test_config_manager_save_persists_migration_fields(tmp_path: Path):
    """Garante que campos de migração sejam persistidos no YAML gerado."""
    mgr = ProjectConfigManager(project_dir=str(tmp_path))
    cfg = ProjectConfig(
        name="migrated-app",
        mode="slice-code",
        mode_origin="tdd-code",
        mode_migrated_at="2026-10-31T15:00:00Z",
    )
    mgr.save(cfg)
    
    reloaded = mgr.load()
    assert reloaded.mode == "slice-code"
    assert reloaded.mode_origin == "tdd-code"
    assert reloaded.mode_migrated_at == "2026-10-31T15:00:00Z"
    assert reloaded.delivery_target == "enterprise-grade"
```

---

## 6. Regras de Implementação

1. **Tipagem Estrita:** Uso obrigatório de `from __future__ import annotations`, tipos `str | None` e zero anotações `Any` sem justificativa técnica.
2. **Invariantes em Rust/Pydantic:** Toda validação de campos deve ser executada via `@field_validator` do Pydantic V2.
3. **Isolamento de Teste com `tmp_path`:** Nenhum teste deve tocar no arquivo `.bombeconfig` real do workspace; todos devem usar a fixture `tmp_path`.
4. **Sem Assinaturas de Persona:** Proibido adicionar comentários decorativos ou menções a agentes nos arquivos `.py`.

---

## 7. O que NÃO Fazer (Anti-padrões)

- ⛔ NÃO aceitar strings arbitrárias no campo `mode`.
- ⛔ NÃO silenciar erros de validação retornando defaults quando o modo especificado for intencionalmente inválido.
- ⛔ NÃO alterar a estrutura de diretórios do projeto nem remover suporte a projetos sem `.bombeconfig` existente.
- ⛔ NÃO utilizar bibliotecas externas adicionais além de `pydantic` e `pyyaml`.

---

## 8. Acceptance Criteria (ACs Testáveis)

- [ ] **AC-01 (Validação de Schema Pydantic):** `ProjectConfig()` inicializa com `mode="slice-code"`, `delivery_target="enterprise-grade"` e validação estrita.
- [ ] **AC-02 (Rastreabilidade Histórica):** Suporte total a `mode_origin` e `mode_migrated_at` na instanciação e no `.bombeconfig`.
- [ ] **AC-03 (Rejeição Determinística de Modos Extintos):** Tentativa de inicializar `ProjectConfig(mode="tdd-code")` levanta `InvalidModeError`.
- [ ] **AC-04 (Migração Automática em I/O):** `ProjectConfigManager.load()` converte arquivos com `mode: tdd-code` para `slice-code` preenchendo `mode_origin="tdd-code"`.
- [ ] **AC-05 (Cobertura Unitária 100%):** Suíte `tests/unit/test_config.py` passando com sucesso no pytest sem warnings.

---

## 9. Definition of Done (DoD)

- [ ] Ciclo TDD executado para SLICE-01 e SLICE-02 (RED -> GREEN -> REFACTOR).
- [ ] Código em `src/bombe_code/config/project_config.py` em conformidade com Ruff e Mypy.
- [ ] Testes em `tests/unit/test_config.py` executados com 100% de sucesso.
- [ ] Story aprovada no Story Compliance por @hoare.
- [ ] Code review e validação de arquitetura aprovados por @unclebob antes do commit.

---

## 10. 🚨 Risk Register

#### RSC-01: Incompatibilidade com Projetos Legados sem `mode_origin`
| Campo | Descrição |
|---|---|
| **Risco** | Arquivos `.bombeconfig` legados que ainda possuem `mode: tdd-code` falharem sumariamente ao carregar o CLI. |
| **Mitigação** | Interceptar no método `load()` do `ProjectConfigManager` e injetar automaticamente a migração antes de submeter ao construtor `ProjectConfig`. |
| **Plano de Ação** | 1. Implementar método `_migrate_legacy_data` no manager. 2. Cobrir o cenário com teste unitário com fixture `tmp_path`. |
| **Severidade** | 🟡 Média |
| **Owner** | @fowler |

---

## 11. Quality Gates

- [x] Story validation (frontmatter checks)
- [ ] TDD: Red-Green-Refactor por slice
- [ ] Code review (@hoare) — Story compliance
- [ ] Architectural validation (@unclebob) — SRF & clean code gate
