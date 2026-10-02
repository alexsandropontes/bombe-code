"""Motor de Scaffolding de Projetos do Bombe Code (ST-023, ST-024).

Permite listar e aplicar starters oficiais e customizados com arquitetura limpa,
configurações de teste e manifesto .bombeconfig pré-configurado.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from bombe_code.config.project_config import ProjectConfig, ProjectConfigManager

logger = logging.getLogger(__name__)


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
    """Motor de scaffolding de projetos."""

    def __init__(self, starters_dict: dict[str, dict[str, Any]] | None = None) -> None:
        self.starters = starters_dict or BUILTIN_STARTERS

    def list_starters(self) -> list[dict[str, Any]]:
        """Retorna a lista de starters disponíveis no catálogo."""
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "category": s.get("category", "general"),
                "stack": s.get("stack", "polyglot"),
                "description": s.get("description", ""),
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
            # Ignora pasta oculta do git caso já tenha sido dado git init
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
        files = starter.get("files", {})

        for rel_path, template_content in files.items():
            file_dest = dest / rel_path
            file_dest.parent.mkdir(parents=True, exist_ok=True)

            formatted_content = template_content.replace("{project_name}", final_project_name)
            file_dest.write_text(formatted_content, encoding="utf-8")
            created_files.append(rel_path)

        # Grava o .bombeconfig customizado
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
        created_files.append(".bombeconfig")

        return {
            "success": True,
            "starter_id": starter_id,
            "project_name": final_project_name,
            "target_dir": str(dest),
            "created_files": created_files,
            "message": f"Starter '{starter_id}' aplicado com sucesso em {dest}.",
        }
