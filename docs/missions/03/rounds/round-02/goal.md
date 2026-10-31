---
round: 2
story_id: STORY-016
epic_id: EP-07
status: validated
started_at: "2026-10-31T21:20:00"
maturity_level: mvp
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-2 — STORY-016: Implementação dos Perfis de Hardware e Tetos de Contexto

## 1. Round Goal
Implementar o catálogo de perfis de hardware (`HardwareProfile`) e normalização de chaves de modelos (`ModelKey`), fixando tetos determinísticos de context window (128K para Gemma 4 E4B e LFM3; 64K para Gemma 4 26B-A4B e Qwen 3.8-9B), offload de MoE com `--n-cpu-moe 999` para o modelo de 26B, configuração estrita de Flash Attention (`-fa on`/`-fa off`) e quantização de KV cache `Q8_0` (`-ctk q8_0 -ctv q8_0`), garantindo 100% de cobertura de testes unitários sem risco de OOM ou swap de memória.

## 2. Escopo do Round
- **Story Alocada:** `STORY-016` (Implementação dos Perfis de Hardware e Tetos de Contexto).
- **Entregável Técnico:**
  - Enum `ModelKey`, dataclass imutável `HardwareProfile` e catálogo `HARDWARE_PROFILES` em `src/bombe_code/local/profiles.py`.
  - Exceção canônica `UnknownModelProfileError` herdando de `LocalModelError`.
  - Funções de fábrica `normalize_model_key`, `get_hardware_profile` e `build_model_profile`.
  - Integração com `LocalModelManager.build_cli_command` respeitando os 5 Critérios de Aceite da Story.
  - Exportação pública dos contratos em `src/bombe_code/local/__init__.py`.
  - Suíte completa de testes unitários em `tests/unit/test_profiles.py` cobrindo os 3 slices do Tech Lead.
- **Fronteira Negativa:** Não implementar orquestração de download/integração de drafts de aceleração MTP (Round 3) ou integração ao HybridRouter e benchmark E2E (Round 4).

## 3. Checklist de Definition of Done (DoD) do Round
- [x] Enum `ModelKey` criado cobrindo Gemma 4 E4B, Gemma 4 26B-A4B, Qwen 3.8-9B e LFM3.
- [x] Dataclass `HardwareProfile` implementada com método `.to_model_profile()`.
- [x] Catálogo `HARDWARE_PROFILES` configurado com tetos de contexto (128K / 64K), KV cache `q8_0`, MoE e Flash Attention corretos.
- [x] Exceção `UnknownModelProfileError` implementada e testada.
- [x] Funções `normalize_model_key`, `get_hardware_profile` e `build_model_profile` operacionais com type hints estritos.
- [x] Testes unitários em `tests/unit/test_profiles.py` cobrindo Slice 1, Slice 2 e Slice 3 com 100% de aprovação.
- [x] Integração com `LocalModelManager.build_cli_command` validando todos os ACs (AC-1 ao AC-5).
- [x] Zero ocorrências de `NotImplementedError`, `pass`, `// TODO` ou stubs em código de produção.
- [x] Conformidade de lint com Ruff e MyPy sem erros.
