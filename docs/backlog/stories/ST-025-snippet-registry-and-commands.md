# STORY ST-025: SnippetRegistry & Comandos de Snippets (Fábrica de LEGO)

> **Épico:** [EP-005: Starters Engine, Snippets Registry & LLM Snippet Tool](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/epics/EP-005-starters-and-snippets-engine.md)  
> **Status:** READY  
> **Prioridade:** ALTA  
> **Responsáveis:** @ieru (Software Architecture), @unclebob (Clean Code)  
> **Modo:** tdd-code  

---

## 1. Descrição
Como desenvolvedor de software ou agente,  
Desejo ter um `SnippetRegistry` que armazene, categorize e pesquise blocos de código comprovados (validação de CPF, CNPJ, telefone, CEP, hash de senha, uuid, slugify, etc.),  
Para que funções utilitárias repetitivas sejam reutilizadas com testes incluídos.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Busca de snippets por query e linguagem
* **Dado** um registro de snippets carregado com blocos em Python, Go e Node
* **Quando** eu buscar por `validar-cpf` com filtro `python`
* **Então** deve retornar o snippet de validação de CPF contendo metadados, código-fonte e testes.

### Cenário 2: Cópia e instalação de snippet no projeto
* **Dado** o comando `copy(snippet_name, target_dir)`
* **Quando** executado
* **Então** o arquivo de implementação e seus testes devem ser gravados no diretório especificado.

### Cenário 3: Comandos CLI e TUI de snippets
* **Dado** o comando CLI `bombe-code snippet list` ou TUI `/snippet list`
* **Quando** executado
* **Então** deve listar todos os snippets disponíveis no catálogo.
* **Dado** o comando `bombe-code snippet search <termo>` ou TUI `/snippet search <termo>`
* **Quando** executado
* **Então** deve filtrar e exibir os snippets correspondentes.
