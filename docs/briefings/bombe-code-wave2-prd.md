# PRD & Auditoria de Gap — Bombe Code (Onda 2)

> **Projeto:** Bombe Code — Reimplementação 100% Python/UV do OpenCode  
> **Autores:** @demarco (Research & Gap Audit) e @grace (Product & Story Breakdown)  
> **Data:** Outubro de 2026  
> **Status:** Aprovado para TDD Cycle Full  

---

## 1. Auditoria Comparativa: OpenCode vs. Bombe Code

### 1.1 Escopo Declarado
* **Migração 100%:** Todas as funcionalidades do OpenCode open-source (runtime, CLI, TUI, servidor, provedores, MCP, LSP, plugins, snapshots).
* **Exclusões Declaradas:** Componentes Enterprise, SaaS pagos e telemetria comercial de nuvem (`packages/enterprise`, `packages/identity`, `packages/slack`, `packages/console`).

### 1.2 Status das Funcionalidades Auditadas

| Subsistema OpenCode | Status Bombe Code | Camada | Observação |
|---|---|---|---|
| Core Runtime & Config | Concluído (F1) | Backend | XDG, merge de config, locks |
| Provedores & models.dev | Concluído (F2) | Backend | Catálogo dinâmico, auth.json 600, consentimento explícito |
| Sessões, Mensagens e Parts | Concluído (F3) | Backend | Pydantic v2, 10 tipos de Part, CRUD |
| Sistema de Ferramentas | Concluído (F4) | Backend | 14 built-ins + custom tools |
| Permissões Granulares | Concluído (F5) | Backend | Wildcards, regras ask/reply persistentes |
| Agent Loop & Harness | Concluído (F6) | Backend | Stream SSE, subtasks, retry, doom-loop prevention |
| Servidor HTTP & SSE | Concluído (F7) | Backend | FastAPI com rotas parity completas |
| TUI Textual Básica | Concluído (F8) | Frontend | Chat view, diálogo de permissão |
| CLI Typer | Concluído (F9) | Backend | run, serve, tui, models, providers, version |
| Python SDK | Concluído (F10) | Backend | Cliente tipado assíncrono com SSE |
| Web UI (Reflex) | Concluído (F11) | Frontend | Espelhamento de packages/app |
| LSP & AST Diagnostics | Concluído (F12) | Backend | Diagnostics, AST inspection, formatter |
| Plugins Loader | Concluído (F13) | Backend | Carregamento dinâmico e hooks |
| MCP & ACP Client | Concluído (F14) | Backend | JSON-RPC stdio e ACP adapter |
| TUI Modais & Temas | Concluído (F15) | Frontend | CommandPalette, HelpDialog, temas |
| Desktop Shell | Concluído (F16) | Frontend | pywebview com detecção headless |
| TUI Vertical Layout | Concluído (F17) | Fullstack | Sidebar 40ch, métricas live, zero stubs |
| Suíte 28 Comandos / | Concluído (F18) | Fullstack | 28 comandos originais + autocompletar dinâmico |
| **Skills Discovery & Injection** | **PENDENTE (F19)** | **Backend** | Descoberta e injeção de `.agent/skills/` |
| **Custom Markdown Commands** | **PENDENTE (F20)** | **Fullstack** | Comandos customizados em `.bombe/commands/*.md` |
| **Code Formatters Automáticos** | **PENDENTE (F21)** | **Backend** | Execução de ruff/black/prettier pós-edição |
| **Git Worktrees Manager** | **PENDENTE (F22)** | **Backend** | Worktrees isolados para tarefas simultâneas |
| **Processador de Imagens / Visão** | **PENDENTE (F23)** | **Fullstack** | Extração MIME, base64 e envio multimodal |

---

## 2. Especificação das Novas Features (F19 a F23)

### F19: Skills Discovery & Context Injection (`skill-system`)
* **Layer:** Backend
* **Descrição:** Escanear diretórios de skills (`.agent/skills/` e `.bombe/skills/`), realizar parsing de frontmatter YAML e injetar no system prompt e catálogo de capacidades.
* **Critérios de Aceite:**
  * CA1: Carregar manifestos de skills contendo nome, descrição, gatilhos e instruções.
  * CA2: Disponibilizar a tool `skill` permitindo que o assistente consulte o conteúdo completo de uma skill sob demanda.
  * CA3: Fornecer listagem programática para a CLI e TUI.

### F20: Custom Markdown Command Templates (`custom-commands`)
* **Layer:** Fullstack
* **Descrição:** Permitir que o usuário crie templates de comandos em markdown (`.bombe/commands/<nome>.md` ou `.opencode/commands/<nome>.md`) que se transformam em comandos executáveis `/nome`.
* **Critérios de Aceite:**
  * CA1: Ler arquivos de template e substituir variáveis `$ARGUMENTS`, `$1`, `$FILE`.
  * CA2: Autocompletar dinâmico na TUI reconhecendo comandos customizados criados pelo usuário.
  * CA3: Executar o template preenchido como instrução para o prompt runner.

### F21: Automatic Code Formatters (`code-formatters`)
* **Layer:** Backend
* **Descrição:** Detectar formatadores instalados no ambiente (ruff, black, prettier, gofmt) e disparar formatação automática após alterações em ferramentas de escrita de arquivos.
* **Critérios de Aceite:**
  * CA1: Identificar se o formatador apropriado para a extensão do arquivo (.py, .ts, .go) existe no PATH.
  * CA2: Formatar silenciosamente o arquivo alterado sem quebrar a execução se o formatador falhar.
  * CA3: Suportar flag de ativação/desativação no `bombe.json`.

### F22: Git Worktrees Manager (`worktree-manager`)
* **Layer:** Backend
* **Descrição:** Gerenciar branches e worktrees git para execuções concorrentes ou isoladas sem poluir o diretório de trabalho ativo.
* **Critérios de Aceite:**
  * CA1: Criar worktree temporário via `git worktree add <path> <branch>`.
  * CA2: Remover worktree de forma limpa via `git worktree remove --force <path>`.
  * CA3: Listar worktrees ativos e validar sanidade de paths.

### F23: Multimodal Vision & Image Processing (`image-processor`)
* **Layer:** Fullstack
* **Descrição:** Processar arquivos de imagem (PNG, JPEG, WebP, GIF) e URLs locais passados nos prompts, codificando em base64 e estruturando `image_url` para adaptadores OpenAI e Anthropic.
* **Critérios de Aceite:**
  * CA1: Validar formato e tamanho máximo de imagens anexadas.
  * CA2: Formatar mensagens com blocos de imagem em conformidade com as APIs dos provedores.
  * CA3: Exibir indicação visual na TUI de imagens anexadas ao turno do usuário.
