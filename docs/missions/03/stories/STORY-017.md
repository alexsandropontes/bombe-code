---
id: STORY-017
title: "Suporte e Parametrização de MTP (Multi-Token Prediction)"
epic_id: EP-08
type: backend
agent: "@barbara"
estimation: "3h"
depends_on: ["STORY-016"]
status: in_progress
---

# STORY-017: Suporte e Parametrização de MTP (Multi-Token Prediction)

## ✅ VALIDAÇÃO PROCESSO (DOR)
- [x] Template ai-story utilizado corretamente
- [x] Frontmatter preenchido (id, type, agent, estimation, depends_on)
- [x] Acceptance Criteria definidos (visão de negócio/sistema)
- [x] DoD definido
- [x] Critérios INVEST atendidos

## ✅ VALIDAÇÃO DEV (DOR)
- [x] Slicing técnico validado em 4 slices atômicos (@unclebob)
- [x] Estratégia TDD estrita (Red -> Green -> Refactor)
- [x] Contratos e exceções definidos (`DraftModelNotFoundError`, campos MTP em `ModelProfile`)
- [x] Dependência STORY-016 concluída e validada

## Contexto & Visão do Usuário
Como engenheiro de sistemas, eu quero que o `LocalModelManager` configure o suporte a MTP no `llama-server`, baixando e apontando os drafts adicionais do Gemma e ativando o draft nativo no Qwen, para acelerar a taxa de geração de tokens.

## Acceptance Criteria
- [ ] **AC-1:** Se o modelo for Gemma 4 E4B com MTP ativo, a linha de comando deve conter:
  `--model-draft <path>/mtp-gemma-4-E4B-it-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 3 -fa off`.
- [ ] **AC-2:** Se o modelo for Gemma 4 26B com MTP ativo, a linha de comando deve conter:
  `--model-draft <path>/mtp-gemma-4-26B-A4B-it-Q8_0.gguf --spec-type draft-mtp --spec-draft-n-max 3 -fa on --n-cpu-moe 999`.
- [ ] **AC-3:** Se o modelo for Qwen 3.8-9B com MTP ativo, a linha de comando deve conter:
  `--spec-type draft-mtp --spec-draft-n-max 2 -fa on` (sem flag `--model-draft`).
- [ ] **AC-4:** O sistema deve verificar a existência física do arquivo `.gguf` de draft antes de tentar iniciar o servidor, levantando erro explicativo se ausente.

## Definition of Done (DoD)
- [ ] Atualização em `src/bombe_code/engine/local_manager.py` e `src/bombe_code/engine/profiles.py` com validação de drafts MTP.
- [ ] Testes de unidade em `tests/unit/test_mtp_launcher.py` validando os argumentos gerados com e sem MTP habilitado.

## Dependências
- `STORY-016`
