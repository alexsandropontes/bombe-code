---
id: STORY-015
title: "Implementação do LocalModelManager e VRAMGate"
epic_id: EP-06
type: backend
agent: "@barbara"
estimation: "3h"
depends_on: []
status: ready
---

# STORY-015: Implementação do LocalModelManager e VRAMGate

## ✅ VALIDAÇÃO PROCESSO (DOR)
- [x] Template ai-story utilizado corretamente
- [x] Frontmatter preenchido (id, type, agent, estimation, depends_on)
- [x] Acceptance Criteria definidos (visão de negócio/sistema)
- [x] DoD definido
- [x] Critérios INVEST atendidos

## Contexto & Visão do Usuário
Como engenheiro e orquestrador do Bombe Code, eu quero um gestor de processos local (`LocalModelManager`) que suba instâncias do `llama-server` em Fila Indiana e impeça alocações concorrentes através de um gate de VRAM, para que a GPU nunca sofra crash de memória (OOM).

## Acceptance Criteria
- [ ] **AC-1:** O `LocalModelManager` deve manter no máximo uma instância ativa de `llama-server`.
- [ ] **AC-2:** Antes de executar qualquer subprocesso, a classe `VRAMGate` deve invocar `nvidia-smi` e certificar que a VRAM ocupada está abaixo de 300MiB.
- [ ] **AC-3:** O encerramento de um modelo ativo deve emitir `SIGTERM`, aguardar até 15 segundos e, se o processo persistir, emitir `SIGKILL`.
- [ ] **AC-4:** O método `start_model(profile)` deve realizar polling no endpoint `http://127.0.0.1:8080/health` e só retornar sucesso quando receber HTTP 200 dentro do timeout de 120s.

## Definition of Done (DoD)
- [ ] Módulo `src/bombe_code/engine/local_manager.py` implementado.
- [ ] Testes de unidade em `tests/unit/test_local_manager.py` com 100% de cobertura nos métodos de lifecycle e parsing de VRAM.
- [ ] Teste de integração validando o comportamento de shutdown gracioso e falha de VRAM ocupada.

## Dependências
- Binário do `llama-server` (`b11985` com CUDA 13.2) disponível no path do sistema ou diretório binário configurado.
