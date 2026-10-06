# ÉPICO EP-004: CONFIGURAÇÃO DE PROJETO & GOVERNANÇA OPERACIONAL

> **Status:** Aberto / Em Execução  
> **Onda:** ONDA-004 (Extensão de Governança Operacional)  
> **Dependência:** EP-001 (Turing Runtime Foundation), EP-002 (Elenco de Agentes), EP-003 (Wave Orchestrator)  
> **Nota de Escopo:** O motor de starters (`/project init-starter`) foi deliberadamente postergado para uma onda futura dedicada aos templates de boilerplate.

---

## 1. Visão do Épico

Este épico introduz os comandos utilitários e de governança operacional herdados do Bombe Core original, adaptados para a nomenclatura nativa do Bombe Code (com prefixo `/` na TUI e subcomandos na CLI):
- **Configuração do Projeto (`/project config`):** Gestão declarativa do arquivo `.bombeconfig` (stacks, caminhos de backend/frontend, banco e branch de trabalho).
- **Alternância de Modos (`/mode`):** Controle em tempo real do nível de autonomia (`auto`, `semi-auto`, `manual`) e disciplina de engenharia (`tdd-code`, `vibe-code`).
- **Análise Forense de Incidentes (`/rca`):** Condução de Root Cause Analysis com `@unclebob` e `@diego` (5 Porquês, Ishikawa e plano de contenção).
- **Simplificação e Antientropia (`/simplify`):** Refatoração cirúrgica com `@ieru` e `@unclebob` para expurgar complexidade acidental e overengineering.
- **Tarefas Pontuais (`/task`) & Relatório Consolidado (`/report status`):** Execução de demandas rápidas sem poluir o fluxo formal da ONDA.

---

## 2. Mapa dos Comandos

| Comando | Agente Líder | Escopo | Artefato / Saída |
| :--- | :--- | :--- | :--- |
| **`/project config`** | `@turing` / `@ieru` | Setup e estrutura de pastas | `.bombeconfig` (YAML) |
| **`/mode [autonomia/eng]`** | `@turing` | Ajuste de autonomia e engenharia | `.bombeconfig` + SQLite |
| **`/rca <incidente>`** | `@unclebob` / `@diego` | Investigação forense de bugs | `docs/rca/RCA-XXX.md` |
| **`/simplify <alvo>`** | `@ieru` / `@unclebob` | Refatoração YAGNI | Refatoração de código |
| **`/task <descrição>`** | Agente especialista | Tarefa avulsa | SQLite `agent_tasks` |
| **`/report status`** | `@turing` / `@nina` | Relatório executivo | Saída rica com métricas |

---

## 3. Stories do Épico

- **ST-019:** Gerenciador de Configuração do Projeto (`.bombeconfig` e `/project config`).
- **ST-020:** Gerenciador de Modos de Operação (`/mode`).
- **ST-021:** Módulo Forense RCA (`/rca`) e Simplificação YAGNI (`/simplify`).
- **ST-022:** Tasks Pontuais (`/task`) e Relatório Consolidado (`/report status`).
