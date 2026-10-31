---
id: MISSION-03
title: "Infraestrutura de Modelos Locais, Tetos de Contexto, Aceleração MTP e Benchmark E2E"
status: in_progress
mode: slice-code
maturity: mvp
created_at: "2026-10-31"
owner: "@turing"
agile_master: "@david"
tech_lead: "@unclebob"
rounds:
  - id: round-00
    name: "Inception & Upstream Macro"
    status: done
  - id: round-01
    name: "LocalModelManager & Ciclo de Vida de Modelos"
    status: done
    epics: ["EP-06"]
    stories: ["STORY-015"]
  - id: round-02
    name: "Hardware Tuning & Tetos de Contexto (VRAM/RAM/SSD)"
    status: pending
    epics: ["EP-07"]
    stories: ["STORY-016"]
  - id: round-03
    name: "Suporte e Integração a MTP (Multi-Token Prediction)"
    status: pending
    epics: ["EP-08"]
    stories: ["STORY-017"]
  - id: round-04
    name: "HybridRouter & Benchmark E2E (Token Bucket Rate Limiter)"
    status: pending
    epics: ["EP-09"]
    stories: ["STORY-018"]
---

# MISSION-03: Infraestrutura de Modelos Locais, Tetos de Contexto, Aceleração MTP e Benchmark E2E

## 1. Demanda Verbatim do Usuário
> "Então vamos abrir uma nova mission no modo auto completo... para trazer todos os aprendizados que vc citou... os 4 aprendizados acima e ajustes... mas temos que ir além.. um pedido... tanto o Gemma 4 4B como o 26B tem MTP que é um arquivo adicional que baixa e taz nas configurações do llama.cpp para habilitar. dá uma estudada e baixa esse add on e coloca pra rodar nesse teste.. e o Qwen3.8 tem isso nativo mas tb tem que ver pq é uma chave que havilita ao subir o llama.cpp com ele.... entendido? são pedidos adicinais ao que já está combinado acima. Sobre contxto o combinado é o mesmo da POC.. 128K onde puder e 64K nos casos em que entendemos que não rola que acho que foi o caso do qwen ne?"

## 2. Visão Executiva & Objetivos da Missão
O objetivo central da MISSION-03 é consolidar uma camada de infraestrutura de inferência local de classe enterprise para o Bombe Code, capaz de:
1. Orquestrar dinamicamente o ciclo de vida do `llama-server` (b11985 + CUDA 13.2) em regime de Fila Indiana estrita, com verificação de VRAM residual (`nvidia-smi < 300MiB`) para eliminar OOMs e processos órfãos.
2. Definir e aplicar perfis de hardware otimizados (particionamento VRAM/RAM/SSD, offload de MoE com `--n-cpu-moe 999`, quantização de KV cache `Q8_0` `-ctk q8_0 -ctv q8_0`, e tetos de contexto de 128K/64K).
3. Habilitar decodificação especulativa via MTP (Multi-Token Prediction) no `llama-server`, suportando drafts externos (`.gguf` adicionais) para a família Gemma 4 (E4B e 26B) e draft nativo para Qwen 3.8-9B.
4. Integrar ao `HybridRouter` para seleção automatizada de modelos por complexidade e rodar a validação ponta a ponta com a tarefa de benchmark da POC (Token Bucket Rate Limiter).

## 3. Kanban de Execução
| Round | Épicos | Story | Agente | Escopo Técnico | Status |
|---|---|---|---|---|---|
| **Round 0** | - | - | @david / @unclebob | Inception Macro, PRD, Arquitetura, Sequenciador | **DONE** |
| **Round 1** | EP-06 | STORY-015 | @barbara | LocalModelManager, Process Launcher, VRAM Gate (< 300MiB) | **DONE** |
| **Round 2** | EP-07 | STORY-016 | @barbara | Hardware Profiles (MoE 999, KV Q8_0, Tetos 128K/64K) | PENDING |
| **Round 3** | EP-08 | STORY-017 | @barbara | Suporte a MTP (Gemma drafts + Qwen nativo) | PENDING |
| **Round 4** | EP-09 | STORY-018 | @barbara / @hoare | HybridRouter & Benchmark E2E Token Bucket | PENDING |
