# Arquitetura — Bombe Code (Onda 2)

> **Autor:** @unclebob (Tech Lead & Architectural Guardian)  
> **Data:** Outubro de 2026  
> **Status:** Aprovado  

---

## 1. Módulos e Estrutura de Diretórios

Para comportar as novas 5 capacidades sem violar os princípios SOLID ou o Single Responsibility Principle, definimos 5 módulos especializados dentro do pacote `bombe_code`:

```
src/bombe_code/
├── skills/               # F19: Descoberta, parsing e injeção de manifestos de skills
│   ├── __init__.py
│   ├── manifest.py       # Pydantic model para metadados e frontmatter YAML
│   └── discovery.py      # Scanner determinístico de .agent/skills e .bombe/skills
├── commands/             # F20: Comandos customizados em Markdown
│   ├── __init__.py
│   ├── templates.py      # Parser de templates Markdown e expansor de variáveis
│   └── loader.py         # Loader dinâmico em .bombe/commands e .opencode/commands
├── formatters/           # F21: Formatadores automáticos de código
│   ├── __init__.py
│   └── runner.py         # Detector e executor de ruff, black, prettier, etc.
├── worktree/             # F22: Isolamento de árvore de trabalho Git
│   ├── __init__.py
│   └── manager.py        # Comandos seguros de git worktree (add, list, remove)
└── images/               # F23: Processador de imagens multimodais
    ├── __init__.py
    └── processor.py      # Leitor de imagem, detecção MIME e serializador base64
```

---

## 2. Contratos e Interfaces

### 2.1 Módulo `skills` (F19)
```python
class SkillManifest(BaseModel):
    name: str
    description: str
    path: str
    content: str
    triggers: list[str] = Field(default_factory=list)

def discover_skills(project_dir: str) -> list[SkillManifest]: ...
def load_skill_content(manifest: SkillManifest) -> str: ...
```

### 2.2 Módulo `commands` (F20)
```python
class CustomCommand(BaseModel):
    name: str
    description: str
    template: str
    path: str

def load_custom_commands(project_dir: str) -> dict[str, CustomCommand]: ...
def render_command_template(template: str, arguments: str, file_path: str = "") -> str: ...
```

### 2.3 Módulo `formatters` (F21)
```python
def format_file(file_path: str, cwd: str = ".") -> bool: ...
```

### 2.4 Módulo `worktree` (F22)
```python
class WorktreeInfo(BaseModel):
    path: str
    commit: str
    branch: str

class WorktreeManager:
    def list_worktrees(self, repo_dir: str) -> list[WorktreeInfo]: ...
    def create_worktree(self, repo_dir: str, worktree_path: str, branch: str) -> WorktreeInfo: ...
    def remove_worktree(self, repo_dir: str, worktree_path: str, force: bool = True) -> bool: ...
```

### 2.5 Módulo `images` (F23)
```python
class ImageAttachment(BaseModel):
    file_path: str
    mime_type: str
    base64_data: str

def process_image(file_path: str, max_size_mb: float = 10.0) -> ImageAttachment: ...
```

---

## 3. Diretrizes de Clean Code & Governança
* **Zero Mocks em Produção:** Todas as chamadas de git ou subprocessos devem ser determinísticas e protegidas por validação de caminhos.
* **Resiliência e Falhas Silenciosas Controladas:** Formatadores de código não podem interromper a execução do agente em caso de ausência do binário; retornam booleano indicando sucesso.
* **Segurança:** Bloqueio de Path Traversal em templates de comandos e worktrees.
