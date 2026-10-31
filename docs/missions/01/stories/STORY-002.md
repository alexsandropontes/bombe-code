---
id: STORY-002
title: "Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes"
epic_id: EP-01
round: ROUND-2
agent: "@andrej"
estimation: 3h
status: ready
type: refactor
layer: backend
complexity: 1
depends_on:
  - STORY-001
tags:
  - agents
  - pdw-4.0
  - personas
  - governance
  - enterprise-grade
---

# STORY-002 — Atualização dos Dossiês dos Agentes para PDW 4.0 Preservando Nomes

### ✅ VALIDAÇÃO PROCESSO (@david)
**Status:** [x] Validado
**Critérios INVEST:** Atendidos
**Prioridade:** Essencial / Bloqueante para Round 2

### ✅ VALIDAÇÃO DEV (@unclebob)
**Status:** [x] Aprovado
**Seções Técnicas:** OK (scope, interface, validações, SRF, anti-padrões, fatiamento em slices, contratos de teste)
**Notas Técnicas:** Fatiamento vertical atômico em 2 Slices de Complexidade Nível 1. Validador determinístico `AgentDossierValidator` em `src/bombe_code/agents/validator.py` e equalização estrita de 25 personas para PDW 4.0.

---

## 1. Scope

**O que faz:**
- Implementa a classe utilitária e de auditoria `AgentDossierValidator` em `src/bombe_code/agents/validator.py` para validar conformidade estrutural com o padrão PDW 4.0.
- Equaliza integralmente os 25 arquivos de definição de agentes em `src/bombe_code/agents/definitions/*.md` para o formato canônico PDW 4.0:
  - Frontmatter YAML canônico estruturado: `name`, `description`, `version: 4.0`, `author`, `metadata` (`type: agent`), `authority` (`is_lead`, `can_route`, `can_veto`, `order`), `identity` (`name`, `role`, `seniority`, `background`), `vibe` (`tone`, `signature`, `personality`), `constraints` (lista de regras determinísticas), `routing_triggers` (gatilhos de acionamento) e `skills` (skills autorizadas).
  - Remoção/Rejeição estrita de atributos místicos ou biográficos (`sign`, `mbti`, `age`, `gender`, `Signo`, `Idade`, `Gênero`) em todo o arquivo (frontmatter e corpo).
  - Presença ordenada e determinística das 6 seções canônicas de markdown:
    1. `# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA` com os 6 campos obrigatórios: `- **Autoridade:**`, `- **Postura Cognitiva:**`, `- **Viés Operacional:**`, `- **Temperamento Técnico:**`, `- **Tom de Voz:**`, `- **Heurísticas Sentinelas:**`.
    2. `# 2. MISSÃO`
    3. `# 3. BASE`
    4. `# 4. REGRAS` (ou `# 4. REGRAS (MODO OPERACIONAL)`)
    5. `# 5. RESTRIÇÕES`
    6. `# 6. ENTREGA`
- Preserva rigorosamente os nomes de arquivos, slugs e handles dos 25 agentes existentes (50% Pioneiros Brasileiros de TI: `@meira`, `@ieru`, `@barreto`, `@diego`, `@guto`, `@caroli`, `@valim`, `@aniche`, `@edith`, `@demi`, `@claudia`, `@nelson`, `@nina`; e 50% Globais/Universal: `@turing`, `@grace`, `@alan`, `@norman`, `@codd`, `@barbara`, `@scott`, `@ryan`, `@james`, `@ada`, `@unclebob`, etc.).
- Fornece suíte completa de testes unitários em `tests/unit/test_agents_pdw.py`.

**O que NÃO faz:**
- ❌ Não renomeia, exclui ou adiciona handles de agentes (preservação estrita dos 25 existentes).
- ❌ Não altera contratos de provedores de LLM, adapters locais ou quotas (escopo do EP-02 / STORY-003 a STORY-006).
- ❌ Não altera o fluxo da máquina de estados do Turing (escopo de STORY-007).
- ❌ Não adiciona dependências externas fora de `pydantic`, `pyyaml` e `pathlib`.

**Limites:**
- [x] Apenas domínio de agentes (`src/bombe_code/agents/validator.py` e `src/bombe_code/agents/definitions/*.md`).
- [x] Apenas testes de unidade em `tests/unit/test_agents_pdw.py`.
- [x] Zero impacto em arquivos fora do módulo de agentes.

---

## 2. Interface & Contratos de Dados

### 2.1 Modelo `DossierValidationReport` & `AgentDossierValidator`

```python
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, Field

class DossierValidationReport(BaseModel):
    """Resultado determinístico da validação de um dossiê de agente."""
    is_valid: bool = Field(..., description="Indica se o dossiê atende 100% ao padrão PDW 4.0")
    file_path: str = Field(default="", description="Caminho do arquivo validado")
    errors: list[str] = Field(default_factory=list, description="Lista de inconformidades encontradas")

class AgentDossierValidator:
    """Validador estrito de conformidade de Dossiês PDW 4.0."""

    REQUIRED_FRONTMATTER_KEYS: ClassVar[set[str]] = {
        "name", "description", "version", "author", "metadata",
        "authority", "identity", "vibe", "constraints", "routing_triggers", "skills"
    }

    FORBIDDEN_ATTRIBUTES: ClassVar[set[str]] = {
        "sign", "mbti", "age", "gender"
    }

    REQUIRED_COGNITIVE_FIELDS: ClassVar[list[str]] = [
        "- **Autoridade:**",
        "- **Postura Cognitiva:**",
        "- **Viés Operacional:**",
        "- **Temperamento Técnico:**",
        "- **Tom de Voz:**",
        "- **Heurísticas Sentinelas:**",
    ]

    REQUIRED_CANONICAL_SECTIONS: ClassVar[list[str]] = [
        "1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA",
        "2. MISSÃO",
        "3. BASE",
        "4. REGRAS",
        "5. RESTRIÇÕES",
        "6. ENTREGA",
    ]

    def validate_content(self, content: str, file_path: str = "") -> DossierValidationReport: ...
    def validate_file(self, file_path: Path | str) -> DossierValidationReport: ...
    def validate_all(self, directory: Path | str) -> dict[str, DossierValidationReport]: ...
```

### 2.2 Regras de Validação Estrutural
1. **Frontmatter YAML:** Deve estar delimitado por `---` no início do arquivo e conter todas as chaves obrigatórias.
2. **Rejeição de Atributos Proibidos:** O frontmatter não pode conter `sign`, `mbti`, `age`, `gender` (em qualquer nível de aninhamento). O corpo do markdown não pode conter menções a `Signo:`, `Idade:`, `MBTI:`, `Gênero:`.
3. **Seções Canônicas:** Devem existir exatamente as 6 seções numeradas de 1 a 6. A seção 1 DEVE ser `# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA` (e não a antiga `# 1. IDENTIDADE`).
4. **Campos Cognitivos:** A seção 1 deve conter todos os 6 marcadores canônicos de postura cognitiva.

---

## 3. Estrutura de Código & SRF Check

### Funções e Métodos:

| Função / Método | Assinatura | Responsabilidade | Limite |
|---|---|---|---|
| `DossierValidationReport` | Model Pydantic | Representação de resultado de validação | < 15 linhas |
| `AgentDossierValidator.validate_content` | `(self, content: str, file_path: str = "") -> DossierValidationReport` | Validação completa de string Markdown PDW 4.0 | < 30 linhas |
| `AgentDossierValidator.validate_file` | `(self, file_path: Path \| str) -> DossierValidationReport` | Leitura de arquivo e delegação de validação | < 15 linhas |
| `AgentDossierValidator.validate_all` | `(self, directory: Path \| str) -> dict[str, DossierValidationReport]` | Varredura em lote de pasta `definitions/*.md` | < 25 linhas |
| `AgentDossierValidator._validate_frontmatter` | `(self, fm: dict) -> list[str]` | Checagem de chaves obrigatórias e proibidas | < 30 linhas |
| `AgentDossierValidator._validate_sections` | `(self, body: str) -> list[str]` | Checagem das 6 seções canônicas de 1 a 6 | < 25 linhas |
| `AgentDossierValidator._validate_cognitive_profile` | `(self, body: str) -> list[str]` | Checagem dos 6 marcadores da Seção 1 | < 25 linhas |

**SRF Check (pré-implementação):**
- [x] Nenhuma função possui conjunção "e" no nome.
- [x] Cada função possui uma responsabilidade única e inequívoca.
- [x] Nenhuma função excede 30 linhas.

**Onde Modificar / Criar:**
- **Criar:** `src/bombe_code/agents/validator.py`
- **Criar:** `tests/unit/test_agents_pdw.py`
- **Modificar:** `src/bombe_code/agents/definitions/*.md` (25 arquivos equalizados)

---

## 4. Fatiamento em Slices Verticais Atômicos

### 🔹 SLICE-01: Implementação do `AgentDossierValidator` & Testes Unitários Isolados
- **Classificação:** Complexidade Nível 1 (Júnior).
- **Justificativa:** Lógica pura de validação determinística de strings, parsing YAML e verificação de regras em memória sem dependência de I/O externo complexo.
- **Ciclo TDD:**
  1. **RED:** Criar `tests/unit/test_agents_pdw.py` asserindo aprovação de dossiê sintético válido e rejeição detalhada em casos de frontmatter incompleto, presença de `sign`/`mbti`, seções ausentes e marcadores cognitivos faltantes. Executar `pytest tests/unit/test_agents_pdw.py` e comprovar falha com `ModuleNotFoundError`.
  2. **GREEN:** Implementar `DossierValidationReport` e `AgentDossierValidator` em `src/bombe_code/agents/validator.py`. Executar testes sintéticos e comprovar 100% de passagem.
  3. **REFACTOR:** Assegurar SRF (< 30 linhas por método), tipagem estrita com `from __future__ import annotations` e zero anotações anêmicas.

### 🔹 SLICE-02: Equalização dos 25 Dossiês em `definitions/*.md` & Validação Verde
- **Classificação:** Complexidade Nível 1 (Júnior).
- **Justificativa:** Refatoração e padronização determinística dos 25 arquivos de agentes preservando integralmente os nomes históricos e eliminando ruído místico/biográfico.
- **Ciclo TDD:**
  1. **RED:** Adicionar teste `test_all_production_agent_dossiers_are_valid_pdw4` em `tests/unit/test_agents_pdw.py` que executa `AgentDossierValidator.validate_all` sobre `src/bombe_code/agents/definitions/`. Executar e comprovar falha nos 25 arquivos legados que ainda contêm `# 1. IDENTIDADE`, `sign`, `mbti`, etc.
  2. **GREEN:** Atualizar os 25 arquivos em `src/bombe_code/agents/definitions/*.md` convertendo a Seção 1 para `# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA`, removendo `sign`/`mbti`/`age`/`gender` e assegurando os 6 pilares. Executar `pytest tests/unit/test_agents_pdw.py` e comprovar 100% verde em todos os 25 agentes.
  3. **REFACTOR:** Garantir que `AgentRegistry.default()` em `src/bombe_code/agents/registry.py` e `load_all_agents()` continuem funcionando sem nenhuma regressão.

---

## 5. Contratos de Testes Unitários (`tests/unit/test_agents_pdw.py`)

A suíte em `tests/unit/test_agents_pdw.py` deve implementar estritamente os seguintes casos:

```python
from __future__ import annotations
from pathlib import Path
import pytest
from bombe_code.agents.validator import AgentDossierValidator

VALID_SYNTHETIC_DOSSIER = """---
name: sample
description: "Agente especialista de teste sintético."
version: 4.0
author: "@andrej"
metadata:
  type: agent
authority:
  is_lead: true
  can_route: false
  can_veto: true
  order: 1
identity:
  name: Sample Agent
  role: Test Specialist
  seniority: Principal
  background: Especialista em testes unitários e governança de software.
vibe:
  tone: Direto e factual.
  signature: "— Sample test signature."
  personality: Rigoroso e focado em qualidade.
constraints:
  - "PROIBIDO ACESSAR AMBIENTE SEM AUTORIZAÇÃO."
routing_triggers:
  - "@sample"
  - sample
skills:
  - clean-code
  - tdd-methodology
---

# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA
- **Autoridade:** Autoridade técnica em execução de testes sintéticos.
- **Postura Cognitiva:** Cético Adversarial e Guardião de Qualidade.
- **Viés Operacional:** Presunção de erro até que os testes comprovem conformidade.
- **Temperamento Técnico:** Intransigente contra amadorismo e hacks.
- **Tom de Voz:** Cirúrgico, direto e analítico.
- **Heurísticas Sentinelas:**
  - Se faltar asserção de teste, reprove.

# 2. MISSÃO
Executar validações automatizadas e assegurar integridade estrutural.

# 3. BASE
- Plataforma: Bombe Code Runtime
- Skills disponíveis: clean-code, tdd-methodology

# 4. REGRAS
Limites de atuação estritos em escopo de validação sintética.

# 5. RESTRIÇÕES
PROIBIDO executar ações destrutivas.

# 6. ENTREGA
Template de entrega padronizado com veredito determinístico.
"""

def test_validator_approves_valid_pdw4_dossier():
    """Valida que um dossiê perfeitamente aderente ao PDW 4.0 seja aprovado."""
    validator = AgentDossierValidator()
    report = validator.validate_content(VALID_SYNTHETIC_DOSSIER, file_path="sample.md")
    assert report.is_valid is True
    assert len(report.errors) == 0

def test_validator_rejects_missing_frontmatter():
    """Rejeita conteúdo sem bloco de frontmatter YAML."""
    validator = AgentDossierValidator()
    report = validator.validate_content("# Sem frontmatter\nConteúdo puro.", file_path="broken.md")
    assert report.is_valid is False
    assert any("frontmatter" in err.lower() for err in report.errors)

def test_validator_rejects_forbidden_mystical_attributes():
    """Rejeita dossiês contendo sign, mbti, age ou gender no frontmatter."""
    legacy_dossier = VALID_SYNTHETIC_DOSSIER.replace(
        "seniority: Principal",
        "seniority: Principal\n  sign: Escorpião\n  mbti: INTJ\n  age: '40'\n  gender: Masculino"
    )
    validator = AgentDossierValidator()
    report = validator.validate_content(legacy_dossier, file_path="legacy.md")
    assert report.is_valid is False
    assert any("mbti" in err.lower() or "sign" in err.lower() for err in report.errors)

def test_validator_rejects_legacy_section_identity():
    """Rejeita dossiês que usam '# 1. IDENTIDADE' em vez de '# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA'."""
    legacy_section = VALID_SYNTHETIC_DOSSIER.replace(
        "# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA",
        "# 1. IDENTIDADE"
    )
    validator = AgentDossierValidator()
    report = validator.validate_content(legacy_section, file_path="legacy_sec.md")
    assert report.is_valid is False
    assert any("perfil comportamental" in err.lower() for err in report.errors)

def test_validator_rejects_missing_cognitive_profile_bullets():
    """Rejeita dossiês que omitam qualquer um dos 6 campos de postura cognitiva."""
    incomplete_cognitive = VALID_SYNTHETIC_DOSSIER.replace("- **Viés Operacional:** Presunção de erro até que os testes comprovem conformidade.", "")
    validator = AgentDossierValidator()
    report = validator.validate_content(incomplete_cognitive, file_path="incomplete.md")
    assert report.is_valid is False
    assert any("viés operacional" in err.lower() for err in report.errors)

def test_all_production_agent_dossiers_are_valid_pdw4():
    """Garante que todos os 25 dossiês de produção atendam 100% ao PDW 4.0."""
    definitions_dir = Path(__file__).parents[2] / "src" / "bombe_code" / "agents" / "definitions"
    assert definitions_dir.is_dir(), f"Diretório não encontrado: {definitions_dir}"
    
    md_files = list(definitions_dir.glob("*.md"))
    assert len(md_files) >= 24, f"Esperado ao menos 24 agentes em produção, encontrados {len(md_files)}"

    validator = AgentDossierValidator()
    reports = validator.validate_all(definitions_dir)

    failures: list[str] = []
    for file_name, report in reports.items():
        if not report.is_valid:
            failures.append(f"{file_name}: {'; '.join(report.errors)}")

    assert not failures, f"Dossiês com inconformidade PDW 4.0:\n" + "\n".join(failures)
```

---

## 6. Regras de Implementação

1. **Tipagem Estrita:** Uso obrigatório de `from __future__ import annotations`, tipos exatos e zero `Any` sem justificativa.
2. **Preservação Soberana de Nomes:** Nenhum arquivo em `src/bombe_code/agents/definitions/` pode ser renomeado. A chave `name` deve preservar o slug histórico de invocação (ex: `valim`, `meira`, `unclebob`).
3. **Eliminação de Atributos Proibidos:** Todo vestígio de signo, idade, gênero ou MBTI deve ser sumariamente eliminado do frontmatter e do markdown.
4. **Isolamento de Teste:** Testes de rejeição e casos de borda utilizam strings sintéticas; teste de produção audita os arquivos reais em lote.

---

## 7. O que NÃO Fazer (Anti-padrões)

- ⛔ NÃO renomear os arquivos `.md` existentes (ex: não mudar `valim.md` para `jose_valim.md`).
- ⛔ NÃO aceitar dossiê sem os 6 pilares canônicos completos.
- ⛔ NÃO manter campos biográficos/místicos em nenhum lugar do arquivo.
- ⛔ NÃO utilizar mocks no teste de validação dos 25 arquivos de produção.

---

## 8. Acceptance Criteria (ACs Testáveis)

- [ ] **AC-01 (Validador Determinístico):** `AgentDossierValidator` implementado em `src/bombe_code/agents/validator.py` valida frontmatter, 6 seções e perfil cognitivo.
- [ ] **AC-02 (Rejeição de Atributos Proibidos):** O validador rejeita dossiês contendo `sign`, `mbti`, `age`, `gender` ou faltando seções canônicas.
- [ ] **AC-03 (Equalização Integral dos 25 Dossiês):** 100% dos 25 arquivos em `src/bombe_code/agents/definitions/` são convertidos para o padrão PDW 4.0.
- [ ] **AC-04 (Preservação Absoluta de Nomes):** Todos os 25 arquivos mantêm seus nomes originais e handles intactos.
- [ ] **AC-05 (Compatibilidade com Loader & Registry):** `AgentRegistry.default()` carrega todos os agentes sem erros ou regressões.
- [ ] **AC-06 (Cobertura Unitária 100%):** Suíte `tests/unit/test_agents_pdw.py` passa 100% verde no pytest.

---

## 9. Definition of Done (DoD)

- [ ] Ciclo TDD executado para SLICE-01 e SLICE-02 (RED -> GREEN -> REFACTOR).
- [ ] `AgentDossierValidator` em conformidade estrita com SRF (< 30 linhas por método).
- [ ] Todos os 25 arquivos de agentes em `src/bombe_code/agents/definitions/*.md` equalizados para PDW 4.0.
- [ ] Testes em `tests/unit/test_agents_pdw.py` executados com 100% de sucesso.
- [ ] Story aprovada no Story Compliance por @hoare.
- [ ] Code review e validação de arquitetura aprovados por @unclebob antes do commit.

---

## 10. 🚨 Risk Register

#### RSC-01: Incompatibilidade no Carregamento em `loader.py`
| Campo | Descrição |
|---|---|
| **Risco** | O método `load_agent_from_file` em `loader.py` acessar campos legados removidos (`gender`, `age`) e lançar `KeyError`. |
| **Mitigação** | Inspecionar e garantir que `loader.py` utilize `.get()` com fallbacks seguros ao desserializar `identity`. |
| **Plano de Ação** | 1. Auditar `loader.py`. 2. Executar `AgentRegistry.default()` na suíte de testes unitários para certificar ausência de regressões. |
| **Severidade** | 🟡 Média |
| **Owner** | @andrej |

#### RSC-02: Omissão de Dossiê na Varredura Manual
| Campo | Descrição |
|---|---|
| **Risco** | Um ou mais dos 25 arquivos de agentes passar desapercebido na equalização e falhar no runtime. |
| **Mitigação** | O teste `test_all_production_agent_dossiers_are_valid_pdw4` utiliza `validate_all()` em lote, asserindo contagem mínima de 24 arquivos e 100% de conformidade. |
| **Plano de Ação** | 1. Executar varredura automatizada pelo pytest. 2. Tratar qualquer arquivo reprovado antes do fechamento do round. |
| **Severidade** | 🔴 Alta |
| **Owner** | @andrej |

---

## 11. Quality Gates

- [x] Story validation (frontmatter checks & Upstream discovery)
- [ ] TDD: Red-Green-Refactor por slice
- [ ] Code review (@hoare) — Story compliance
- [ ] Architectural validation (@unclebob) — SRF & clean code gate
