---
round: 1
story_id: STORY-015
epic_id: EP-06
status: in_progress
started_at: "2026-10-31T21:10:00"
maturity_level: mvp
layer: backend
agent: "@barbara"
---

# Objetivo do ROUND-1 — STORY-015: Implementação do LocalModelManager e VRAMGate

## 1. Round Goal
Implementar o gestor de ciclo de vida de modelos locais `LocalModelManager`, a barreira de hardware `VRAMGate` e seus contratos de domínio para orquestração segura do binário `llama-server` (b11985 + CUDA 13.2) em regime de Fila Indiana estrita, garantindo que alocações concorrentes sejam bloqueadas e que a VRAM residual antes e após qualquer execução seja inferior a 300 MiB com 100% dos testes unitários passando.

## 2. Escopo do Round
- **Story Alocada:** `STORY-015` (Implementação do LocalModelManager e VRAMGate).
- **Entregável Técnico:**
  - Contratos e enums em `src/bombe_code/local/contracts.py`.
  - Barreira de inspeção e asserção de VRAM em `src/bombe_code/local/vram_gate.py`.
  - Gerenciador de ciclo de vida com polling de `/health` e shutdown gracioso (SIGTERM/SIGKILL) em `src/bombe_code/local/local_manager.py`.
  - Suíte completa de testes unitários em `tests/unit/test_local_manager.py`.
- **Fronteira Negativa:** Não implementar perfis avançados de hardware com offload de MoE e KV cache Q8_0 (Round 2), drafts de aceleração MTP (Round 3) ou integração ao HybridRouter e benchmark (Round 4).

## 3. Checklist de Definition of Done (DoD) do Round
- [ ] Pacote `src/bombe_code/local/` criado com `__init__.py`.
- [ ] Modelos e exceções implementados em `src/bombe_code/local/contracts.py` (`ModelStatus`, `ModelProfile`, `LocalModelError`, `VRAMThresholdExceededError`, `ModelStartupTimeoutError`, `ModelConcurrencyError`, `NvidiaSmiNotFoundError`).
- [ ] Classe `VRAMGate` implementada em `src/bombe_code/local/vram_gate.py` com runner injetável e asserção de teto de 300 MiB.
- [ ] Classe `LocalModelManager` implementada em `src/bombe_code/local/local_manager.py` com injeção de dependências, montagem de CLI para `llama-server`, propagação de `LD_LIBRARY_PATH`, controle de concorrência e lifecycle com polling de `/health` e terminação com SIGTERM / fallback SIGKILL.
- [ ] Suíte de testes em `tests/unit/test_local_manager.py` cobrindo cenários felizes e de erro com 100% de aprovação.
- [ ] Zero ocorrências de `NotImplementedError`, `pass`, `// TODO` ou stubs em código de produção.
- [ ] Conformidade de lint com Ruff e tipagem estrita.
