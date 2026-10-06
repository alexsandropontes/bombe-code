# STORY ST-026: Tool de Snippets para Agentes LLM (snippet_search & snippet_get)

> **Épico:** [EP-005: Starters Engine, Snippets Registry & LLM Snippet Tool](file:///home/lexpontes/projetos/struct/bombe-code/docs/backlog/epics/EP-005-starters-and-snippets-engine.md)  
> **Status:** DONE
> **Prioridade:** ALTA  
> **Responsáveis:** @andrej (AI Prompt & Context), @turing (Autônomo da ONDA)  
> **Modo:** tdd-code  

---

## 1. Descrição
Como agente de código autônomo (ex: @unclebob, @barbara, @ryan, @scott),  
Desejo ter acesso a ferramentas de schema (`snippet_search` e `snippet_get`) integradas ao `ToolRegistry`,  
Para que eu possa consultar o catálogo de LEGO e obter implementações e testes auditados sem alucinações nem desperdício de tokens gerando rotinas utilitárias do zero.

---

## 2. Critérios de Aceite (BDD)

### Cenário 1: Descoberta de snippet pela LLM
* **Dado** que o agente recebe uma tarefa envolvendo validação de documento brasileiro ou utilitários
* **Quando** o agente invocar a ferramenta `snippet_search(query="validar-cpf", platform="python")`
* **Então** a ferramenta deve retornar um sumário JSON com os snippets encontrados (nome, descrição, plataforma e tags).

### Cenário 2: Recuperação de código completo pela LLM
* **Dado** um snippet existente no registry
* **Quando** o agente invocar `snippet_get(name="validar-cpf", platform="python")`
* **Então** a ferramenta deve retornar o código-fonte integral da função, exemplos de uso e os testes unitários associados.

### Cenário 3: Registro em `ToolRegistry`
* **Dado** a inicialização padrão de ferramentas com `builtin_registry()`
* **Quando** consultado
* **Então** as ferramentas `snippet_search` e `snippet_get` devem estar presentes e disponíveis para despacho do modelo LLM.
