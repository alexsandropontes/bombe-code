"""Gerenciador de plugins e hooks do Bombe Code."""

from __future__ import annotations

import importlib.util
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PluginManager:
    """Carrega dinamicamente módulos de extensão e gerencia hooks do ciclo de vida."""

    def __init__(self) -> None:
        self.plugins: dict[str, Any] = {}
        self.hooks: dict[str, list[Callable[..., Any]]] = {}

    def load_from_dir(self, directory: Path | str, registry: Any = None) -> list[str]:
        path = Path(directory)
        if not path.is_dir():
            return []

        loaded: list[str] = []
        for file in sorted(path.iterdir()):
            if file.is_file() and file.suffix == ".py" and not file.name.startswith("_"):
                name = file.stem
                try:
                    spec = importlib.util.spec_from_file_location(f"bombe_plugin_{name}", file)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        self.register_plugin_module(name, mod, registry=registry)
                        loaded.append(name)
                except Exception as exc:  # noqa: BLE001 - isolamento: falha em plugin não derruba o sistema
                    logger.warning("Falha ao carregar plugin %s: %s", name, exc)

        return loaded

    def register_plugin_module(self, name: str, module: Any, registry: Any = None) -> None:
        self.plugins[name] = module

        # Registra hooks comuns
        for hook in ("on_init", "on_tool_call", "on_prompt_start", "on_prompt_finish"):
            func = getattr(module, hook, None)
            if callable(func):
                self.hooks.setdefault(hook, []).append(func)

        # Registro de tools customizadas
        tool_registrar = getattr(module, "register_tools", None)
        if callable(tool_registrar) and registry is not None:
            try:
                tool_registrar(registry)
            except Exception as exc:  # noqa: BLE001 - falha em tool do plugin não afeta o registro
                logger.warning("Falha em register_tools no plugin %s: %s", name, exc)

    def emit(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        results: list[Any] = []
        for func in self.hooks.get(hook_name, []):
            try:
                results.append(func(*args, **kwargs))
            except Exception as exc:  # noqa: BLE001 - falha no hook isolada
                logger.warning("Erro no hook %s: %s", hook_name, exc)
        return results

    def list_plugins(self) -> list[str]:
        return list(self.plugins.keys())
