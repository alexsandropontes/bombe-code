---
id: EP-03
title: "Ponte de Retrocompatibilidade Wave Bridge"
status: ready
created_at: "2026-10-31"
author: "@grace"
mission_id: "MISSION-02"
tags:
  - wave-bridge
  - deprecation-warning
  - backward-compatibility
  - rich-ui
---

# EP-03 — Ponte de Retrocompatibilidade Wave Bridge

## 1. Problema de Negócio
Usuários, scripts de automação e rotinas de CI/CD anteriores utilizam comandos da família `bombe wave ...` (`wave start`, `wave run`, `wave cycle`, `wave validate`, `wave status`, `wave promote`, `wave end`). A remoção súbita dessas instruções causaria interrupções operacionais e frustração (Breaking Change). É imperativo fornecer uma transição pedagógica suave que redirecione a execução automaticamente para a nova arquitetura de rounds.

## 2. Valor de Negócio
- **Zero Interrupção de Automações:** Pipelines legados continuam operando sem falhas imediatas de comando não encontrado.
- **Educação Ativa do Desenvolvedor:** O terminal emite banners visuais explicativos informando a equivalência direta no novo padrão Core v4.
- **Eliminação de Código Duplicado:** O interceptor atua puramente como proxy de roteamento para os novos motores, sem reter lógica de onda.

## 3. Escopo

### O que o Épico Cobre
- Sub-app Typer `wave_app` em `src/bombe_code/cli/commands/wave_bridge.py`.
- Tabela de mapeamento completa dos 7 subcomandos legados de ondas para suas primitivas canônicas:
  - `bombe wave start [ID]` -> `bombe round start [N]`
  - `bombe wave run` -> `bombe round all`
  - `bombe wave cycle [ID]` -> `bombe round burn [N]`
  - `bombe wave validate` -> `bombe round validate`
  - `bombe wave status` -> `bombe round status`
  - `bombe wave promote [env]` -> `bombe project ship [env]`
  - `bombe wave end` -> `bombe mission end`
- Renderização de painel formatado Rich com aviso pedagógico de depreciação.

### O que o Épico NÃO Cobre
- Manutenção do motor antigo de ondas (`WaveOrchestrator`), que é formalmente extirpado.
- Criação de novos subcomandos de ondas.

## 4. User Stories Vinculadas

| Story ID | Round | Título da História | Agente Atribuído | Estimativa |
| :--- | :---: | :--- | :---: | :---: |
| `STORY-012` | Round 4 | Wave Bridge e Interceptor de Depreciação | @barbara | 3h |

## 5. Dependências
- **Upstream:** Conclusão dos Épicos EP-01 e EP-02 (o bridge depende dos handlers de missão e round).
- **Downstream:** Bloqueia a homologação E2E final do EP-05.

## 6. Critérios de Sucesso
- A execução de qualquer um dos 7 comandos `bombe wave ...` exibe o banner de aviso em stderr/stdout.
- O redirecionamento ocorre com exit code 0 e preserva os efeitos colaterais do comando de destino.
- Parâmetros passados na chamada legada (como ID ou env) são devidamente repassados ao handler de destino.

## 7. Riscos & Mitigações
| Risco Identificado | Severidade | Mitigação Arquitetural |
| :--- | :---: | :--- |
| Scripts de CI que parseiam stdout quebrarem devido ao banner de deprecation | Média | Garantir que o banner seja formatado de forma limpa e os códigos de saída POSIX sejam mantidos estritamente. |
| Usuário presumir que "ondas" continuam existindo internamente | Baixa | Texto claro no banner alertando que o conceito foi extinto e substituído por rounds e slices. |
