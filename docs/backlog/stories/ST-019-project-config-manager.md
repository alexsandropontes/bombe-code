---
id: "ST-019"
type: "feature"
agent: "@ieru"
tdd: true
test_of: "src/bombe_code/config/project_config.py"
test_type: "unit"
adr_ref: "docs/architecture/bombe-code-foundation-master.md"
depends_on: ["ST-015"]
ux_approved: true
snippet_ref: "ProjectConfigManager"
estimation: "2h"
---

# ST-019: Gerenciador de Configuração do Projeto (.bombeconfig e /project config)

## Scope

**O que faz:**
Implementa a classe `ProjectConfigManager` e o modelo `ProjectConfig` em `src/bombe_code/config/project_config.py` para carregar, autodetectar, validar e persistir o arquivo `.bombeconfig` na raiz do projeto:
- Campos: `project.name`, `project.type`, `project.language` (backend, frontend), `project.structure` (root_src, backend, frontend, docs_root), `project.branch`, `mode`, `autonomy`.
- Método de auto-detecção de estrutura e stacks a partir dos arquivos presentes no diretório.
- Integração com o comando `/project config` na TUI e `bombe-code project config` na CLI.

**O que NÃO faz:**
- ❌ Não executa scaffolding de starters (postergado para onda futura).

## Interface (Input / Output)

```python
class ProjectConfig(BaseModel):
    name: str = "meu-projeto"
    type: str = "web"
    backend_language: str = "python"
    frontend_stack: str = "react"
    root_src: str = "src/"
    backend_path: str = "src/backend/"
    frontend_path: str = "src/frontend/"
    docs_root: str = "docs/"
    branch: str = "dev"
    mode: str = "tdd-code"
    autonomy: str = "auto"

class ProjectConfigManager:
    def __init__(self, project_dir: str = ".") -> None: ...
    def load(self) -> ProjectConfig: ...
    def save(self, config: ProjectConfig) -> None: ...
    def autodetect(self) -> ProjectConfig: ...
```

## Critérios de Aceite

1. `load()` retorna configuração default caso `.bombeconfig` não exista.
2. `save()` grava `.bombeconfig` no formato YAML com formatação válida.
3. `autodetect()` reconhece `pyproject.toml` como python, `package.json` como node/react, `*.csproj` como csharp, etc.
