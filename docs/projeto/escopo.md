---
title: "Escopo Geral do Produto — Bombe Code"
date: "2026-10-31"
author: "@grace"
status: approved
version: "1.0.0"
tags:
  - escopo
  - inception
  - bombe-code
  - strategy
---

# Escopo Geral do Produto — Bombe Code

## 1. Visão de Produto Sniper

> **Para** desenvolvedores de software, engenheiros de IA e equipes ágeis que buscam autonomia e economia operacional,  
> **o Bombe Code** é um harness autônomo CLI/TUI nativo em Python que orquestra agentes de inteligência artificial sob o rigor metodológico do Bombe Core,  
> **que** automatiza a entrega de software ponta a ponta através de fatiamento atômico (Slice Code) com roteamento híbrido inteligente entre modelos locais e cloud,  
> **diferentemente de** assistentes genéricos de chat ou extensões proprietárias acopladas a nuvens corporativas que geram dependência e custos astronômicos,  
> **nós** oferecemos independência de infraestrutura, redução de 80%+ nos custos de tokens e garantia de continuidade operacional mesmo com esgotamento de cotas de APIs.

---

## 2. O que o Bombe Code É vs. O que NÃO É

| O que o Bombe Code É | O que o Bombe Code NÃO É |
| :--- | :--- |
| **Harness CLI/TUI Nativo em Python:** Runtime completo e desacoplado que governa o ciclo de vida, ferramentas e execução de agentes de IA locais e remotos. | **Não é uma extensão de IDE:** Não é plugin para VS Code, JetBrains ou Cursor; opera como software de engenharia autônomo de terminal. |
| **Orquestrador Determinístico de Slices:** Implementação estrita da esteira Slice Code (Round 0 Inception + Rounds 1..n com Slices Backend TDD + Frontend Construction). | **Não é um "Chatbot de Geração Livre":** Não aceita código gerado por achismo sem teste de unidade falhante prévio (RED) ou validação de gates. |
| **Roteador Híbrido e Resiliente de LLMs:** Engine inteligente capaz de despachar requisições por pontuação de complexidade e chavear instantaneamente para LLMs locais ao detectar estouro de cota (HTTP 429) em cloud. | **Não é um simples wrapper de API única:** Não está amarrado a um único fornecedor de modelo nem depende de créditos de terceiros para continuar operando. |
| **Compatível com PDW 4.0 do Bombe Core:** Incorpora os padrões comportamentais, posturas cognitivas e protocolos rigorosos do Bombe Core v4. | **Não é fork estático do OpenCode:** É uma evolução autônoma que substitui harnesses legados externos, tornando o código fonte auditável em Python. |
| **Esteira Kanban Granular:** Operação orientada a fluxo onde 1 Round = 1 Story, garantindo revisões atômicas por @unclebob e lead time reduzido. | **Não é esteira em cascata (Waterfall):** Não acumula múltiplas histórias em rounds monolíticos que sobrecarregam a janela de contexto de revisão. |

---

## 3. Objetivos de Negócio

1. **Redução Drástica de Custos Operacionais (Meta: 80%+):**
   - Direcionamento sistemático de tarefas rotineiras, fatiamento mecânico, geração de boilerplate, testes unitários e refatorações para modelos locais quantizados (ex: Qwen 2.5 Coder, DeepSeek Coder via Ollama/vLLM/LlamaCpp).
   - Reserva de chamadas Cloud apenas para tarefas de alta complexidade estratégica ou síntese arquitetural inicial.

2. **Soberania e Autonomia de Desenvolvimento:**
   - Capacidade de manter a esteira de desenvolvimento 100% operacional em ambientes com conectividade restrita, ar-gap, ou diante do bloqueio/esgotamento súbito de contas e limites de taxa de provedores de nuvem.

3. **Substituição do Harness Legado por Runtime Nativo Python:**
   - Eliminar a dependência de harnesses externos em TypeScript/Node (como opencode legado), centralizando o runtime do Bombe Code no ecossistema Python moderno (3.12+), facilitando a extensão e integração direta com bibliotecas de ML/IA.

4. **Throughput de Engenharia Acelerado (Cycle Time Otimizado):**
   - Reduzir o tempo de ciclo de revisão e entrega através da regra "1 Round = 1 Story", diminuindo a carga cognitiva dos agentes auditores (@unclebob e @hoare) e eliminando gargalos de aprovação.

---

## 4. Personas Atendidas

### 4.1. Engenheiro de Software / Desenvolvedor Autônomo
- **Perfil:** Desenvolvedor focado em entregar código limpo e testado rapidamente, sem pagar faturas de centenas de dólares mensais em tokens de IA.
- **Dor Central:** Bloqueio de trabalho por estouro de rate limit (429) em APIs comerciais e frustração com alucinações de assistentes que geram código sem testes.
- **Garantia Bombe Code:** Continuidade ininterrupta com fallback local automático e execução disciplinada por TDD.

### 4.2. Tech Lead / Arquiteto de Sistemas
- **Perfil:** Responsável pela governança, manutenibilidade e integridade da arquitetura de múltiplos projetos corporativos.
- **Dor Central:** Perda de rastreabilidade do código gerado por IA, dívida técnica inflada e falta de aderência a padrões arquiteturais corporativos.
- **Garantia Bombe Code:** Revisão formal atômica a cada story concluída, artefatos persistidos obrigatoriamente em disco e auditoria de conformidade (DoR/DoD).

### 4.3. Agente de IA Especialista (Subagente do Sistema)
- **Perfil:** Agente autônomo (ex: @barbara, @ryan, @ada, @unclebob) operando sob uma persona técnica especializada.
- **Dor Central:** Janelas de contexto poluídas por escopos gigantescos de rounds multifacetados, resultando em perda de foco instrucional e erros de sintaxe.
- **Garantia Bombe Code:** Contexto hiperfocado via fatiamento atômico em Slices e rounds de escopo unitário (1 Story).

---

## 5. Restrições Operacionais

1. **Paridade Comportamental e Nomenclatura Histórica:**
   - Os nomes de agentes e comandos consagrados no ecossistema Bombe Code devem ser mantidos para preservar compatibilidade com fluxos estabelecidos; no entanto, o motor comportamental interno, prompts e contratos devem incorporar 100% da inteligência PDW 4.0 do Bombe Core v4.
2. **Ambiente Operacional Prioritário:**
   - Suporte primário a Linux POSIX e compatibilidade total com operação headless via terminal CLI.
3. **Consumo de Hardware Local Gerenciável:**
   - O orquestrador local de LLMs não deve monopolizar recursos de memória VRAM/RAM a ponto de inviabilizar a execução dos testes e compilações de produção da máquina do desenvolvedor.
4. **Armazenamento Canônico em Filesystem:**
   - Proibido manter estado volátil de missões apenas em memória. Toda decisão, especificação e transição de estado deve residir fisicamente sob a árvore `docs/`.
