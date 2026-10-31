---
round: 3
story_id: STORY-017
epic_id: EP-08
status: in_progress
started_at: "2026-10-31T21:38:00"
maturity_level: mvp
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-3 — STORY-017: Suporte e Parametrização de MTP (Multi-Token Prediction)

## 1. Round Goal
Implementar o suporte e a parametrização de Multi-Token Prediction (MTP) no `LocalModelManager` e no catálogo de perfis de hardware (`HARDWARE_PROFILES`), habilitando aceleração especulativa com draft models externos para a família Gemma 4 (E4B e 26B-A4B) e draft nativo para o Qwen 3.8-9B, com validação antecipada da integridade física dos artefatos `.gguf` antes de acionar o `llama-server`.

## 2. Escopo do Round
- **Story Alocada:** `STORY-017` (Suporte e Parametrização de MTP (Multi-Token Prediction)).
- **Entregável Técnico:**
  - Exceção canônica `DraftModelNotFoundError` herdando de `LocalModelError` em `src/bombe_code/local/contracts.py`.
  - Extensão da dataclass `ModelProfile` com campos opcionais para MTP: `draft_model_path`, `spec_type`, `spec_draft_n_max`.
  - Configuração do catálogo `HARDWARE_PROFILES` com caminhos canônicos e parâmetros de draft para Gemma 4 E4B, Gemma 4 26B-A4B e Qwen 3.8-9B.
  - Suporte ao flag `enable_mtp` e override de `draft_model_path` em `HardwareProfile.to_model_profile` e `build_model_profile`.
  - Injeção das flags `--model-draft`, `--spec-type`, `--spec-draft-n-max` no `LocalModelManager.build_cli_command`.
  - Validação física do arquivo de draft via `LocalModelManager.validate_profile` antes do VRAMGate no `start_model`.
  - Exportação de `DraftModelNotFoundError` no módulo `src/bombe_code/local/__init__.py`.
  - Suíte completa de testes unitários em `tests/unit/test_mtp_launcher.py`.
- **Fronteira Negativa:** Não implementar integração do `HybridRouter` nem execução de benchmark E2E de rate limiting (Round 4 / STORY-018).

## 3. Checklist de Definition of Done (DoD) do Round
- [ ] Exceção `DraftModelNotFoundError` implementada e exportada em `src/bombe_code/local/__init__.py`.
- [ ] Dataclass `ModelProfile` atualizada com campos MTP opcionais (`draft_model_path`, `spec_type`, `spec_draft_n_max`).
- [ ] `HARDWARE_PROFILES` configurado com defaults de MTP para Gemma 4 E4B, Gemma 4 26B-A4B, Qwen 3.8-9B e LFM3.
- [ ] `to_model_profile` e `build_model_profile` suportando `enable_mtp: bool = True` e `draft_model_path: Path | str | None = None`.
- [ ] `LocalModelManager.build_cli_command` gerando flags de MTP estritamente conforme critérios de aceite.
- [ ] Método `LocalModelManager.validate_profile` checando existência física do arquivo de draft e levantando `DraftModelNotFoundError`.
- [ ] Chamada de `validate_profile` em `start_model` antes do VRAMGate.
- [ ] Suíte `tests/unit/test_mtp_launcher.py` cobrindo AC-1 a AC-4 e desativação com 100% de aprovação.
- [ ] Zero ocorrências de mocks em produção, bodies vazios (`pass`, `// TODO`) e conformidade estrita com Ruff e tipagem Python.
