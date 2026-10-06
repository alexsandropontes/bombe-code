"""Motor de Scaffolding de Projetos do Bombe Code (ST-023, ST-024).

Permite listar e aplicar starters oficiais e customizados com arquitetura limpa,
configurações de teste e manifesto .bombeconfig pré-configurado.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from bombe_code.config.project_config import ProjectConfig, ProjectConfigManager

logger = logging.getLogger(__name__)

DEFAULT_STARTERS_DIR = Path(__file__).resolve().parent.parent / "registry" / "starters"


BUILTIN_STARTERS: dict[str, dict[str, Any]] = {
    "python-fastapi-clean": {
        "id": "python-fastapi-clean",
        "name": "Python FastAPI Clean Architecture",
        "category": "backend",
        "stack": "python",
        "description": "API assíncrona moderna em FastAPI com pytest, Pydantic v2, Ruff e Dockerfile.",
        "files": {
            "pyproject.toml": """[project]
name = "{project_name}"
version = "0.1.0"
description = "API FastAPI gerada via Bombe Code"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.8.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.5.0",
]

[tool.ruff]
target-version = "py311"
line-length = 100
""",
            "src/main.py": '''"""Entrypoint da API FastAPI."""

from fastapi import FastAPI

app = FastAPI(title="{project_name}", version="0.1.0")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "{project_name}"}
''',
            "tests/test_health.py": '''"""Testes de saúde da API."""

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app


@pytest.mark.anyio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
''',
            "README.md": """# {project_name}

Projeto inicializado via **Bombe Code** utilizando o starter `python-fastapi-clean`.

## Executando Localmente
```bash
uv sync
uv run uvicorn src.main:app --reload --port 8000
```

## Executando Testes
```bash
uv run pytest
```
""",
            ".gitignore": """__pycache__/
*.py[cod]
.venv/
.pytest_cache/
.ruff_cache/
.bombe-code/
""",
        },
        "config": {
            "type": "api",
            "backend_language": "python",
            "frontend_stack": "none",
            "root_src": "src/",
            "backend_path": "src/",
            "frontend_path": "",
            "mode": "tdd-code",
            "autonomy": "auto",
        },
    },
    "go-gin-clean": {
        "id": "go-gin-clean",
        "name": "Go Gin Clean Architecture",
        "category": "backend",
        "stack": "go",
        "description": "API REST de alta concorrência em Go com framework Gin e testes nativos.",
        "files": {
            "go.mod": """module {project_name}

go 1.22

require (
	github.com/gin-gonic/gin v1.10.0
)
""",
            "main.go": """package main

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

func setupRouter() *gin.Engine {
	r := gin.Default()
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "ok",
			"service": "{project_name}",
		})
	})
	return r
}

func main() {
	r := setupRouter()
	r.Run(":8080")
}
""",
            "main_test.go": """package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthCheck(t *testing.T) {
	router := setupRouter()

	w := httptest.NewRecorder()
	req, _ := http.NewRequest("GET", "/health", nil)
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("Esperado 200, recebido %d", w.Code)
	}
}
""",
            "README.md": """# {project_name}

Projeto Go Gin inicializado via **Bombe Code**.

## Executar
```bash
go run main.go
```
""",
            ".gitignore": """bin/
*.exe
.bombe-code/
""",
        },
        "config": {
            "type": "api",
            "backend_language": "go",
            "frontend_stack": "none",
            "root_src": "./",
            "backend_path": "./",
            "frontend_path": "",
            "mode": "tdd-code",
            "autonomy": "auto",
        },
    },
    "node-ts-clean": {
        "id": "node-ts-clean",
        "name": "Node.js TypeScript Clean API",
        "category": "backend",
        "stack": "node",
        "description": "API backend em Node.js com TypeScript estrito, Fastify e Vitest.",
        "files": {
            "package.json": """{{
  "name": "{project_name}",
  "version": "0.1.0",
  "type": "module",
  "scripts": {{
    "dev": "tsx watch src/index.ts",
    "build": "tsc",
    "test": "vitest run"
  }},
  "dependencies": {{
    "fastify": "^4.28.0"
  }},
  "devDependencies": {{
    "@types/node": "^20.14.0",
    "tsx": "^4.16.0",
    "typescript": "^5.5.0",
    "vitest": "^2.0.0"
  }}
}}
""",
            "tsconfig.json": """{{
  "compilerOptions": {{
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "./dist"
  }},
  "include": ["src/**/*", "tests/**/*"]
}}
""",
            "src/index.ts": """import Fastify from "fastify";

export const server = Fastify({ logger: true });

server.get("/health", async () => {
  return { status: "ok", service: "{project_name}" };
});

if (process.env.NODE_ENV !== "test") {
  server.listen({ port: 3000, host: "0.0.0.0" }, (err) => {
    if (err) {
      server.log.error(err);
      process.exit(1);
    }
  });
}
""",
            "tests/health.test.ts": """import { describe, it, expect } from "vitest";
import { server } from "../src/index.js";

describe("Health Route", () => {
  it("deve responder 200 no /health", async () => {
    const response = await server.inject({
      method: "GET",
      url: "/health",
    });
    expect(response.statusCode).toBe(200);
    const body = JSON.parse(response.payload);
    expect(body.status).toBe("ok");
  });
});
""",
            ".gitignore": """node_modules/
dist/
.bombe-code/
""",
        },
        "config": {
            "type": "api",
            "backend_language": "node",
            "frontend_stack": "none",
            "root_src": "src/",
            "backend_path": "src/",
            "frontend_path": "",
            "mode": "tdd-code",
            "autonomy": "auto",
        },
    },
    "react-tailwind-clean": {
        "id": "react-tailwind-clean",
        "name": "React 19 Tailwind CSS Frontend",
        "category": "frontend",
        "stack": "react",
        "description": "Single Page Application em React 19, TypeScript, Vite e Tailwind CSS.",
        "files": {
            "package.json": """{{
  "name": "{project_name}",
  "version": "0.1.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.400.0"
  }},
  "devDependencies": {{
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "typescript": "^5.5.0",
    "vite": "^5.3.0"
  }}
}}
""",
            "vite.config.ts": """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
});
""",
            "index.html": """<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
  </head>
  <body class="bg-slate-900 text-slate-100">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
""",
            "src/main.tsx": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""",
            "src/App.tsx": """import React from 'react';

export default function App() {
  return (
    <main className="min-h-screen flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-slate-800 p-8 rounded-xl border border-slate-700 shadow-xl text-center">
        <h1 className="text-2xl font-bold text-white mb-2">{project_name}</h1>
        <p className="text-slate-400 text-sm mb-6">Iniciado via Bombe Code Starter</p>
        <button className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg transition-colors">
          Começar
        </button>
      </div>
    </main>
  );
}
""",
            "src/index.css": """@tailwind base;
@tailwind components;
@tailwind utilities;
""",
            ".gitignore": """node_modules/
dist/
.bombe-code/
""",
        },
        "config": {
            "type": "web",
            "backend_language": "none",
            "frontend_stack": "react",
            "root_src": "src/",
            "backend_path": "",
            "frontend_path": "src/",
            "mode": "tdd-code",
            "autonomy": "auto",
        },
    },
}


class StarterEngine:
    """Motor de scaffolding de projetos com carregamento dinâmico de starters e blueprints."""

    def __init__(
        self,
        starters_dict: dict[str, dict[str, Any]] | None = None,
        registry_dir: Path | str | None = None,
    ) -> None:
        self.registry_dir = Path(registry_dir).resolve() if registry_dir else DEFAULT_STARTERS_DIR
        self.blueprints_dir = self.registry_dir / "blueprints"
        self.starters: dict[str, dict[str, Any]] = {}

        # 1. Carrega builtins como baseline inicial
        for k, v in BUILTIN_STARTERS.items():
            self.starters[k] = dict(v)

        # 2. Se registry_dir existir, carrega starters dinâmicos dos YAMLs oficiais
        if self.registry_dir.is_dir():
            self._load_yaml_starters()

        # 3. Sobrescreve com dicionário customizado caso fornecido
        if starters_dict:
            self.starters.update(starters_dict)

    def _load_yaml_starters(self) -> None:
        """Carrega todos os starters declarados em arquivos .yaml do catálogo."""
        for yaml_path in sorted(self.registry_dir.glob("*.yaml")):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or not isinstance(data, dict):
                    continue
                s_id = data.get("name")
                if not s_id:
                    continue

                tech_stack = data.get("tech_stack", {}) or {}
                backend_lang = str(tech_stack.get("backend", "")).lower()
                frontend_stack = str(tech_stack.get("frontend", "")).lower()
                category = data.get("category", "general")
                stype = data.get("type", "server")
                blueprint = data.get("blueprint") or s_id

                # Deriva configuração para ProjectConfig
                cfg_type = (
                    "web"
                    if (
                        "frontend" in tech_stack
                        or stype == "fullstack"
                        or category.lower() in ("saas", "frontend")
                    )
                    else "api"
                )

                # Deriva linguagem principal
                lang = "python"
                if "go" in backend_lang or "gin" in backend_lang:
                    lang = "go"
                elif "node" in backend_lang or "ts" in backend_lang or "javascript" in backend_lang:
                    lang = "nodejs"
                elif "dotnet" in backend_lang or "c#" in backend_lang:
                    lang = "dotnet"
                elif "java" in backend_lang or "spring" in backend_lang:
                    lang = "java"
                elif "python" in backend_lang:
                    lang = "python"
                elif category.lower() == "frontend":
                    lang = "none"

                fstack = "none"
                if "react" in frontend_stack:
                    fstack = "react"
                elif "streamlit" in frontend_stack:
                    fstack = "streamlit"
                elif "vue" in frontend_stack:
                    fstack = "vue"

                starter_record = {
                    "id": s_id,
                    "name": data.get("name", s_id),
                    "blueprint": blueprint,
                    "category": category,
                    "type": stype,
                    "description": data.get("description", ""),
                    "tech_stack": tech_stack,
                    "stack": tech_stack.get("backend") or category,
                    "composition": data.get("composition", []) or [],
                    "structure": data.get("structure", []) or [],
                    "required_agents": data.get("required_agents", []) or [],
                    "yaml_path": str(yaml_path),
                    "config": {
                        "type": cfg_type,
                        "backend_language": lang,
                        "frontend_stack": fstack,
                        "root_src": "src/",
                        "backend_path": "src/backend/"
                        if stype in ("fullstack", "server")
                        else "src/",
                        "frontend_path": "src/frontend/"
                        if stype in ("fullstack", "frontend")
                        else "",
                        "mode": "tdd-code",
                        "autonomy": "auto",
                    },
                }
                self.starters[s_id] = starter_record
            except (OSError, yaml.YAMLError, ValueError, KeyError) as e:
                logger.warning(f"Erro ao carregar starter YAML '{yaml_path}': {e}")

    def list_starters(self) -> list[dict[str, Any]]:
        """Retorna a lista de starters disponíveis no catálogo."""
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "category": s.get("category", "general"),
                "stack": s.get("stack", "polyglot"),
                "description": s.get("description", ""),
                "type": s.get("type", "server"),
                "tech_stack": s.get("tech_stack", {}),
                "composition": s.get("composition", []),
            }
            for s in self.starters.values()
        ]

    def get_starter(self, starter_id: str) -> dict[str, Any] | None:
        """Retorna a definição do starter especificado."""
        return self.starters.get(starter_id)

    def apply_starter(
        self,
        starter_id: str,
        target_dir: str = ".",
        project_name: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Aplica o scaffolding do starter no diretório de destino."""
        dest = Path(target_dir).resolve()
        starter = self.get_starter(starter_id)

        if not starter:
            return {
                "success": False,
                "error": f"Starter '{starter_id}' não encontrado no catálogo.",
            }

        # Valida diretório vazio (se não for force)
        if dest.exists() and not force:
            items = list(dest.iterdir())
            non_git_items = [it for it in items if it.name != ".git"]
            if non_git_items:
                return {
                    "success": False,
                    "error": (
                        f"Diretório não está vazio: {dest}. "
                        "Para aplicar o starter, o diretório deve estar limpo ou use force=True."
                    ),
                }

        dest.mkdir(parents=True, exist_ok=True)
        final_project_name = project_name or dest.name or "bombe-project"
        created_files: list[str] = []

        # 1. Se tem files declarados diretamente (BUILTIN_STARTERS legados)
        if starter.get("files"):
            for rel_path, template_content in starter["files"].items():
                file_dest = dest / rel_path
                file_dest.parent.mkdir(parents=True, exist_ok=True)
                formatted_content = template_content.replace("{project_name}", final_project_name)
                file_dest.write_text(formatted_content, encoding="utf-8")
                created_files.append(rel_path)

        # 2. Se tem composition (modular scaffolding), aplica sub-starters recursivamente
        composition = starter.get("composition") or []
        for sub_id in composition:
            sub_starter = self.get_starter(sub_id)
            if sub_starter:
                self._apply_starter_files(sub_starter, dest, final_project_name, created_files)

        # 3. Aplica o blueprint do próprio starter (se houver diretório de blueprint)
        self._apply_starter_files(starter, dest, final_project_name, created_files)

        # 4. Grava o .bombeconfig customizado
        cfg_data = starter.get("config", {})
        config = ProjectConfig(
            name=final_project_name,
            type=cfg_data.get("type", "web"),
            backend_language=cfg_data.get("backend_language", "python"),
            frontend_stack=cfg_data.get("frontend_stack", "react"),
            root_src=cfg_data.get("root_src", "src/"),
            backend_path=cfg_data.get("backend_path", "src/backend/"),
            frontend_path=cfg_data.get("frontend_path", "src/frontend/"),
            mode=cfg_data.get("mode", "tdd-code"),
            autonomy=cfg_data.get("autonomy", "auto"),
        )
        cfg_mgr = ProjectConfigManager(str(dest))
        cfg_mgr.save(config)
        if ".bombeconfig" not in created_files:
            created_files.append(".bombeconfig")

        return {
            "success": True,
            "starter_id": starter_id,
            "project_name": final_project_name,
            "target_dir": str(dest),
            "created_files": sorted(set(created_files)),
            "message": f"Starter '{starter_id}' aplicado com sucesso em {dest}.",
        }

    def _apply_starter_files(
        self,
        starter: dict[str, Any],
        dest: Path,
        project_name: str,
        created_files: list[str],
    ) -> None:
        """Renderiza os arquivos de um starter a partir de seu blueprint e structure."""
        blueprint_name = starter.get("blueprint") or starter.get("name")
        if not blueprint_name:
            return

        blueprint_dir = self.blueprints_dir / blueprint_name
        if not blueprint_dir.is_dir():
            return

        structure = starter.get("structure") or []

        if structure:
            for item in structure:
                target_path = dest / item
                source_path = self._resolve_blueprint_item(blueprint_dir, item)

                if source_path:
                    if source_path.is_dir():
                        self._copy_blueprint_dir(
                            source_path, target_path, project_name, dest, created_files
                        )
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        self._write_rendered_file(source_path, target_path, project_name)
                        rel = str(target_path.relative_to(dest))
                        created_files.append(rel)
                else:
                    if item.endswith("/") or "." not in Path(item).name:
                        target_path.mkdir(parents=True, exist_ok=True)
        else:
            self._copy_blueprint_dir(blueprint_dir, dest, project_name, dest, created_files)

    def _resolve_blueprint_item(self, blueprint_dir: Path, item: str) -> Path | None:
        """Localiza um item do structure dentro do diretório do blueprint."""
        potential_names = [
            item,
            item.replace("src/backend/", ""),
            item.replace("src/frontend/", ""),
            item.replace("src/", ""),
            Path(item).name,
        ]
        for name in potential_names:
            clean_name = name.rstrip("/")
            for variant in [clean_name, f"{clean_name}.tmpl"]:
                ps = blueprint_dir / variant
                if ps.exists():
                    return ps
        return None

    def _copy_blueprint_dir(
        self,
        src: Path,
        dst: Path,
        project_name: str,
        base_dest: Path,
        created_files: list[str],
    ) -> None:
        """Copia recursivamente diretório de blueprint renderizando templates."""
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.name == "__pycache__" or item.name.endswith(".pyc"):
                continue
            clean_name = item.name.removesuffix(".tmpl")
            target_item = dst / clean_name
            if item.is_dir():
                self._copy_blueprint_dir(item, target_item, project_name, base_dest, created_files)
            else:
                target_item.parent.mkdir(parents=True, exist_ok=True)
                self._write_rendered_file(item, target_item, project_name)
                rel = str(target_item.relative_to(base_dest))
                created_files.append(rel)

    def _write_rendered_file(self, src_file: Path, dst_file: Path, project_name: str) -> None:
        """Lê arquivo fonte, substitui placeholders e grava no destino."""
        try:
            content = src_file.read_text(encoding="utf-8")
            rendered = content.replace("{project_name}", project_name).replace(
                "{name}", project_name
            )
            dst_file.write_text(rendered, encoding="utf-8")
        except UnicodeDecodeError:
            dst_file.write_bytes(src_file.read_bytes())
