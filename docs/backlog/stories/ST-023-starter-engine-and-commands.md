# STORY ST-023: StarterEngine & Comandos de Scaffolding de Projeto

> **Épico:** [EP-005: Starters Engine, Snippets Registry & LLM Snippet Tool](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/epics/EP-005-starters-and-snippets-engine.md)  
> **Status:** DONE
> **Prioridade:** ALTA  
> **Responsáveis:** @ieru (Software Architecture), @unclebob (Tech Lead)  
> **Modo:** tdd-code  

---

## 1. Descrição
Como desenvolvedor de software ou agente autônomo,  
Desejo ter um motor de aplicação de starters (`StarterEngine`) que liste templates disponíveis e aplique scaffolding determinístico no workspace,  
Para que novos projetos sejam inicializados em segundos com padrões de Clean Architecture, configs de teste e `.bombeconfig` corretos.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Listagem de starters disponíveis
* **Dado** que o `StarterEngine` foi instanciado
* **Quando** eu invocar `list_starters()`
* **Então** deve retornar uma lista de dicionários contendo `id`, `name`, `category`, `description` e `stack`.

### Cenário 2: Aplicação de starter com sucesso em diretório limpo
* **Dado** um diretório temporário vazio
* **Quando** eu aplicar o starter `python-fastapi-clean` com o nome `meu-app`
* **Então** os arquivos essenciais (`pyproject.toml`, `src/`, `tests/`, `.bombeconfig`) devem ser criados
* **E** o método deve retornar `{"success": True, "created_files": [...]}`.

### Cenário 3: Veto de diretório sujo
* **Dado** um diretório contendo arquivos existentes e `force=False`
* **Quando** eu tentar aplicar qualquer starter
* **Então** deve falhar com erro explicativo sem sobrescrever os arquivos existentes.

### Cenário 4: Comandos CLI e TUI
* **Dado** o comando CLI `bombe-code project starter list` ou TUI `/project starter list`
* **Quando** executado
* **Então** deve exibir a listagem formatada dos starters.
* **Dado** o comando `bombe-code project starter apply <nome>` ou TUI `/project starter apply <nome>`
* **Quando** executado
* **Então** deve aplicar o scaffold e relatar os arquivos criados.
