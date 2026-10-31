---
id: STORY-016
title: "Implementação dos Perfis de Hardware e Tetos de Contexto"
epic_id: EP-07
type: backend
agent: "@barbara"
estimation: "2h30m"
depends_on: ["STORY-015"]
status: in_progress
---

# STORY-016: Implementação dos Perfis de Hardware e Tetos de Contexto

## ✅ VALIDAÇÃO PROCESSO (DOR)
- [x] Template ai-story utilizado corretamente
- [x] Frontmatter preenchido (id, type, agent, estimation, depends_on)
- [x] Acceptance Criteria definidos (visão de negócio/sistema)
- [x] DoD definido
- [x] Critérios INVEST atendidos

## ✅ VALIDAÇÃO DEV (DOR)
- [x] Slicing técnico validado em 3 slices atômicos (@unclebob)
- [x] Estratégia TDD estrita (Red -> Green -> Refactor)
- [x] Contratos e enums definidos (`ModelKey`, `HardwareProfile`, `HARDWARE_PROFILES`)
- [x] Dependência STORY-015 concluída e validada

## Contexto & Visão do Usuário
Como desenvolvedor, eu quero que o launcher aplique os parâmetros exatos de balanceamento de VRAM, RAM e SSD para cada modelo, limitando o contexto a 128K ou 64K conforme a capacidade, para maximizar o desempenho sem incorrer em swap de memória.

## Acceptance Criteria
- [ ] **AC-1:** Para Gemma 4 E4B e LFM3, o comando gerado deve incluir `-c 131072` (128K).
- [ ] **AC-2:** Para Gemma 4 26B-A4B e Qwen 3.8-9B, o comando gerado deve incluir `-c 65536` (64K).
- [ ] **AC-3:** Para todos os perfis, as flags de quantização do cache KV `-ctk q8_0 -ctv q8_0` devem ser injetadas.
- [ ] **AC-4:** Para Gemma 4 26B-A4B, a flag `--n-cpu-moe 999` e `-fa on` devem ser incluídas.
- [ ] **AC-5:** Para Gemma 4 E4B, a flag `-fa off` deve ser configurada obrigatoriamente.

## Definition of Done (DoD)
- [ ] Módulo `src/bombe_code/local/profiles.py` implementado com as dataclasses de perfil.
- [ ] Testes de unidade em `tests/unit/test_profiles.py` cobrindo a montagem dos argumentos de linha de comando para cada um dos 4 modelos.

## Dependências
- `STORY-015`
