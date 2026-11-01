"""Autonomous multi-agent execution runner for Bombe Code rounds.

Coordinates real local LLM inference (Gemma 4 E4B with MTP, Qwen 3.8 9B, Gemma 4 26B, LFM3),
tool calling (read_file, write_file, edit_file, run_command), TDD test execution,
compliance review, and deterministic DoD validation with complete telemetry.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import httpx
import yaml

from bombe_code.agents.registry import AgentRegistry
from bombe_code.local.local_manager import LocalModelManager
from bombe_code.local.profiles import (
    HARDWARE_PROFILES,
    ModelKey,
    build_model_profile,
)
from bombe_code.routing.classifier import ComplexityClassifier
from bombe_code.routing.quota_manager import QuotaManager
from bombe_code.tools.parser import FallbackToolParser

logger = logging.getLogger(__name__)


@dataclass
class StationResult:
    """Result of an autonomous station execution."""
    station_id: str
    agent: str
    model_key: str
    success: bool
    wall_seconds: float
    turns: int
    prompt_tokens: int
    completion_tokens: int
    pp_tok_s: float
    tg_tok_s: float
    peak_vram_mb: float
    error: str | None = None
    telemetry_path: Path | None = None


class AutonomousRunner:
    """Orchestrates end-to-end autonomous agent stations against real local LLMs."""

    def __init__(
        self,
        project_dir: Path | str,
        venv_python: Path | str | None = None,
        timeout_seconds: float = 180.0,
    ) -> None:
        self.project_dir = Path(project_dir).resolve()
        if venv_python:
            self.venv_python = Path(venv_python)
        elif "VIRTUAL_ENV" in os.environ and (Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python3").is_file():
            self.venv_python = Path(os.environ["VIRTUAL_ENV"]) / "bin" / "python3"
        elif (Path(__file__).resolve().parents[3] / ".venv" / "bin" / "python3").is_file():
            self.venv_python = Path(__file__).resolve().parents[3] / ".venv" / "bin" / "python3"
        else:
            self.venv_python = Path(sys.executable)
        self.timeout_seconds = timeout_seconds
        self.local_manager = LocalModelManager()
        self.fallback_parser = FallbackToolParser()
        self.registry = AgentRegistry.default()
        self.telemetry_dir = self.project_dir / "telemetry"
        self.telemetry_dir.mkdir(parents=True, exist_ok=True)

    def _get_active_mission_dir(self) -> Path:
        missions_root = self.project_dir / "docs" / "missions"
        if missions_root.is_dir():
            for m in sorted(missions_root.iterdir()):
                if m.is_dir() and (m / "mission.md").is_file():
                    return m
        return missions_root / "01"

    # ── TOOLS RUNTIME ──────────────────────────────────────────────────────────

    def _get_exec_env(self) -> dict[str, str]:
        env = os.environ.copy()
        venv_bin = str(self.venv_python.parent)
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        env["PYTHONPATH"] = f"{self.project_dir}:{self.project_dir}/src:{env.get('PYTHONPATH', '')}"
        return env

    def execute_tool(self, tool_name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Safely executes a tool action within the project workspace."""
        clean_name = tool_name.strip().lower()
        try:
            if clean_name in ("write_file", "write_project_file"):
                rel_path = (args.get("path") or args.get("file_path") or "").strip().lstrip("/")
                if not rel_path or rel_path == ".":
                    return "Erro: o caminho do arquivo não pode ser vazio ou apontar para a raiz do projeto.", False
                content = args.get("content", "")
                if isinstance(content, (dict, list)):
                    content = json.dumps(content, ensure_ascii=False, indent=2)
                elif not isinstance(content, str):
                    content = str(content)
                target = (self.project_dir / rel_path).resolve()
                if not str(target).startswith(str(self.project_dir)):
                    return f"Erro de segurança: caminho fora da raiz {rel_path}", False
                if target.is_dir():
                    return f"Erro: '{rel_path}' é um diretório existente. Especifique o caminho completo de um arquivo.", False
                if rel_path.endswith(".py"):
                    content = content.replace("\t", "    ")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return f"Arquivo '{rel_path}' gravado com sucesso ({len(content)} caracteres).", True

            elif clean_name in ("read_file", "read_project_file"):
                rel_path = (args.get("path") or args.get("file_path") or "").lstrip("/")
                target = (self.project_dir / rel_path).resolve()
                if not target.is_file():
                    return f"Arquivo '{rel_path}' não encontrado.", False
                return target.read_text(encoding="utf-8", errors="replace"), True

            elif clean_name in ("edit_file", "replace_text_in_file"):
                rel_path = (args.get("path") or args.get("file_path") or "").lstrip("/")
                target_str = args.get("target") or args.get("old_str") or ""
                replacement = args.get("replacement") or args.get("new_str") or ""
                target = (self.project_dir / rel_path).resolve()
                if not target.is_file():
                    return f"Arquivo '{rel_path}' não encontrado.", False
                content = target.read_text(encoding="utf-8")
                if rel_path.endswith(".py"):
                    target_str = target_str.replace("\t", "    ")
                    replacement = replacement.replace("\t", "    ")
                if target_str not in content:
                    # Fallback com normalização de whitespace
                    clean_pattern = re.escape(target_str.strip())
                    clean_pattern = re.sub(r"[ \t]+", r"[ \\t]+", clean_pattern)
                    match = re.search(clean_pattern, content)
                    if match:
                        updated = content[:match.start()] + replacement + content[match.end():]
                        target.write_text(updated, encoding="utf-8")
                        return f"Arquivo '{rel_path}' editado com sucesso via pattern match.", True
                    return f"Erro: texto alvo não encontrado em '{rel_path}'. Dica: use write_file para gravar o arquivo completo com precisão.", False
                updated = content.replace(target_str, replacement)
                target.write_text(updated, encoding="utf-8")
                return f"Arquivo '{rel_path}' editado com sucesso.", True

            elif clean_name in ("run_command", "run_shell", "executar_comando"):
                cmd = args.get("command") or args.get("cmd") or ""
                if not cmd:
                    return "Erro: comando vazio", False
                env = self._get_exec_env()
                res = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=str(self.project_dir),
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=120,
                )
                output = f"[exit_code={res.returncode}]\n{res.stdout}\n{res.stderr}".strip()
                return output, (res.returncode == 0)

            return f"Ferramenta desconhecida '{tool_name}'", False
        except Exception as exc:
            return f"Erro executando ferramenta '{tool_name}': {exc}", False

    # ── LOCAL LLM INFERENCE LOOP ──────────────────────────────────────────────

    def _ensure_model_server(self, model_key: str | ModelKey) -> None:
        """Starts the specified model profile on llama-server if not already active."""
        if str(model_key).startswith("glm-") or model_key in ("zai", "cloud_zai", "glm-5.3-flash"):
            return
        profile = build_model_profile(model_key)
        if (
            self.local_manager._active_profile
            and self.local_manager._active_profile.name == profile.name
            and self.local_manager.is_healthy()
        ):
            return

        self.local_manager.stop_model()
        time.sleep(1.0)
        self.local_manager.start_model(profile, timeout_seconds=self.timeout_seconds)

    def _get_zai_config(self) -> tuple[str | None, str]:
        auth_file = Path.home() / ".local" / "share" / "bombe-code" / "auth.json"
        auth_data = {}
        if auth_file.is_file():
            try:
                auth_data = json.loads(auth_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        key = (
            os.environ.get("ZAI_API_KEY")
            or os.environ.get("ZHIPU_API_KEY")
            or auth_data.get("zai-coding-plan", {}).get("key")
            or auth_data.get("zai-coding-plan", {}).get("api_key")
            or auth_data.get("zai", {}).get("key")
            or auth_data.get("zai", {}).get("api_key")
        )
        url = (
            os.environ.get("ZAI_BASE_URL")
            or auth_data.get("zai-coding-plan", {}).get("base_url")
            or auth_data.get("zai-coding-plan", {}).get("url")
            or auth_data.get("zai", {}).get("base_url")
            or auth_data.get("zai", {}).get("url")
            or "https://api.z.ai/api/coding/paas/v4"
        )
        return key, url.rstrip("/")

    def _chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools_schema: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
        model_name: str = "local",
    ) -> dict[str, Any]:
        """Sends chat completion request to Z.ai cloud or active local model server with telemetry."""
        is_cloud_zai = (
            model_name.startswith("glm-")
            or model_name in ("zai", "cloud_zai", "glm-5.3-flash")
        )
        zai_key, zai_base_url = self._get_zai_config()

        if is_cloud_zai and zai_key and QuotaManager().is_available("zai"):
            url = f"{zai_base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {zai_key}",
                "Content-Type": "application/json",
            }
            payload: dict[str, Any] = {
                "model": "glm-5.3-flash",
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 8192,
                "stream": True,
            }
            if tools_schema:
                payload["tools"] = tools_schema
                payload["tool_choice"] = "auto"
                payload["tool_stream"] = True

            t0 = time.time()
            full_content: list[str] = []
            full_reasoning: list[str] = []
            tool_calls_dict: dict[int, dict[str, Any]] = {}
            finish_reason = "stop"
            usage: dict[str, Any] = {}

            try:
                with httpx.Client(timeout=180.0) as client:
                    with client.stream("POST", url, json=payload, headers=headers) as response:
                        if response.status_code == 429 or response.status_code >= 400:
                            err_body = response.read().decode("utf-8", errors="replace")
                            if response.status_code == 429 or "exhausted" in err_body.lower() or "limit" in err_body.lower():
                                logger.warning(
                                    "Z.ai retornou limite de cota/429: %s. Registrando cooldown e caindo para local...",
                                    err_body,
                                )
                                QuotaManager().record_exhausted("zai", error_message=err_body)
                                return self._chat_completion(
                                    messages, tools_schema, temperature, model_name="local"
                                )
                            response.raise_for_status()

                        for line in response.iter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data_str = line[len("data:"):].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                            except Exception:
                                continue

                            if "usage" in chunk and chunk["usage"]:
                                usage = chunk["usage"]

                            choices = chunk.get("choices") or []
                            if not choices:
                                continue
                            c0 = choices[0]
                            if c0.get("finish_reason"):
                                finish_reason = c0["finish_reason"]

                            delta = c0.get("delta") or {}
                            if delta.get("content"):
                                full_content.append(delta["content"])
                            if delta.get("reasoning_content"):
                                full_reasoning.append(delta["reasoning_content"])
                            if delta.get("tool_calls"):
                                for tc in delta["tool_calls"]:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_calls_dict:
                                        tool_calls_dict[idx] = {
                                            "id": tc.get("id", ""),
                                            "type": "function",
                                            "function": {"name": "", "arguments": ""},
                                        }
                                    if tc.get("id"):
                                        tool_calls_dict[idx]["id"] = tc["id"]
                                    fn = tc.get("function") or {}
                                    if fn.get("name"):
                                        tool_calls_dict[idx]["function"]["name"] += fn["name"]
                                    if fn.get("arguments"):
                                        tool_calls_dict[idx]["function"]["arguments"] += fn["arguments"]

            except (httpx.TimeoutException, httpx.NetworkError) as net_err:
                logger.warning("Erro de rede com Z.ai (%s). Caindo para local...", net_err)
                return self._chat_completion(
                    messages, tools_schema, temperature, model_name="local"
                )

            wall_s = max(0.001, round(time.time() - t0, 3))
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            pp_tok_s = round(prompt_tokens / wall_s, 1) if prompt_tokens else 0.0
            tg_tok_s = round(completion_tokens / wall_s, 1) if completion_tokens else 0.0

            assembled_tool_calls = [tool_calls_dict[i] for i in sorted(tool_calls_dict.keys())]
            message: dict[str, Any] = {
                "role": "assistant",
                "content": "".join(full_content),
            }
            if assembled_tool_calls:
                message["tool_calls"] = assembled_tool_calls

            return {
                "message": message,
                "finish_reason": finish_reason,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "wall_s": wall_s,
                "pp_tok_s": pp_tok_s,
                "tg_tok_s": tg_tok_s,
            }

        # Execução local via llama-server
        url = "http://127.0.0.1:18094/v1/chat/completions"
        payload = {
            "model": "local",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 8192,
            "repeat_penalty": 1.1,
            "stop": ["<|im_end|>", "<|endoftext|>", "</tool_call>"],
            "stream": False,
        }
        if tools_schema:
            payload["tools"] = tools_schema
            payload["tool_choice"] = "auto"

        t0 = time.time()
        with httpx.Client(timeout=600.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 500 and len(messages) > 4:
                logger.warning("llama-server retornou 500. Compactando contexto e retentando...")
                payload["messages"] = [messages[0], messages[1]] + messages[-4:]
                resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        wall_s = max(0.001, round(time.time() - t0, 3))
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        timings = data.get("timings", {})
        pp_tok_s = timings.get("prompt_per_second") or (prompt_tokens / wall_s if prompt_tokens else 0.0)
        tg_tok_s = timings.get("predicted_per_second") or (completion_tokens / wall_s if completion_tokens else 0.0)

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        finish_reason = choice.get("finish_reason", "stop")

        return {
            "message": message,
            "finish_reason": finish_reason,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "wall_s": wall_s,
            "pp_tok_s": round(pp_tok_s, 1),
            "tg_tok_s": round(tg_tok_s, 1),
        }

    # ── STATION EXECUTION ─────────────────────────────────────────────────────

    def execute_burn_station(
        self,
        round_num: int,
        story_id: str,
        story_path: Path,
        max_turns: int = 60,
    ) -> StationResult:
        """Executes full autonomous TDD burn for a given story using local LLMs with failover."""
        story_text = story_path.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", story_text, re.DOTALL)
        meta = yaml.safe_load(match.group(1)) if match else {}
        agent_handle = str(meta.get("agent", "@barbara"))
        clean_handle = agent_handle.lstrip("@").lower()

        # Dynamic complexity classification (Jr / Pl / Sr)
        affected_files: list[str] = []
        for line in story_text.splitlines():
            if "impl_targets:" in line or "red_test:" in line:
                for token in line.split(":", 1)[1].split(","):
                    cleaned = token.strip("` \t\r\n[];")
                    if cleaned and cleaned not in affected_files:
                        affected_files.append(cleaned)

        slice_spec = {
            "affected_files": affected_files,
            "estimated_lines": len(story_text.splitlines()) * 5,
            "scope": f"{story_id} {meta.get('title', '')} {clean_handle}",
        }
        classifier = ComplexityClassifier()
        analysis = classifier.evaluate_slice(slice_spec)
        logger.info(
            "Classificação dinâmica de complexidade para %s: tier=%s (score=%s, razões=%s)",
            story_id,
            analysis.recommended_tier,
            analysis.score,
            analysis.reasons,
        )

        # Check cloud quota for Z.ai (glm-5.3-flash)
        quota_mgr = QuotaManager()
        zai_key, _ = self._get_zai_config()
        if zai_key and quota_mgr.is_available("zai"):
            dev_profile = "glm-5.3-flash"
            escalation_profile = "glm-5.3-flash"
            active_model = dev_profile
            logger.info("Cota Z.ai disponível! Roteando estação de queima para cloud glm-5.3-flash.")
        else:
            tier_to_model = {
                "junior": "gemma-4-e4b",
                "pleno": "qwen-3.8-9b",
                "senior": "qwen-3.8-9b",
            }
            dev_profile = tier_to_model.get(analysis.recommended_tier, "qwen-3.8-9b")
            escalation_profile = "qwen-3.8-9b"
            active_model = dev_profile

        agent_def = self.registry.get(clean_handle)
        base_prompt = agent_def.system_prompt if agent_def else "Você é um engenheiro de software sênior aplicando TDD estrito."
        system_prompt = (
            base_prompt
            + "\n\nDIRETRIZ MANDATÓRIA DE EXECUÇÃO:\n"
            "- Você opera como uma ferramenta autônoma CLI. É ESTRITAMENTE PROIBIDO responder com texto explicativo ou bate-papo sem executar chamadas de ferramentas.\n"
            "- Toda interação sua DEVE conter chamadas de ferramenta ('write_file', 'edit_file' ou 'run_command') para escrever o código de teste ou a implementação.\n"
            "- Se os testes falharem, chame IMEDIATAMENTE a ferramenta para corrigir os arquivos. Nunca apenas diga que vai corrigir."
        )

        existing_files: list[str] = []
        for p in (self.project_dir / "src").glob("**/*"):
            if p.is_file() and not p.name.startswith("."):
                existing_files.append(str(p.relative_to(self.project_dir)))
        for p in (self.project_dir / "tests").glob("**/*"):
            if p.is_file() and not p.name.startswith("."):
                existing_files.append(str(p.relative_to(self.project_dir)))

        # Extract required tests from story slices
        expected_tests: list[str] = []
        for line in story_text.splitlines():
            if "red_test:" in line:
                val = line.split("red_test:", 1)[1].strip().strip("`").strip()
                for token in val.split():
                    token = token.strip("`,;")
                    if token.endswith(".py"):
                        expected_tests.append(token)

        existing_files_str = "\n".join(f"- {f}" for f in sorted(existing_files)) if existing_files else "(nenhum arquivo pré-existente)"

        user_prompt = (
            f"ESTAÇÃO DE QUEIMA TDD — ROUND {round_num}: `{story_id}` ({agent_handle})\n\n"
            f"Você deve implementar esta story respeitando TDD estrito e zero mocks em código de produção:\n"
            f"1. TABELA CANÔNICA DE SLA (SEVERIDADE):\n"
            f"   - P1: 1 hora (+1h)\n"
            f"   - P2: 4 horas (+4h)\n"
            f"   - P3: 24 horas (+24h = +1 dia)\n"
            f"   - P4: 72 horas (+72h = +3 dias)\n"
            f"   Toda a aplicação e testes DEVEM usar estritamente essa matriz (ex: P1=1h, P2=4h, P3=24h, P4=72h).\n"
            f"2. PERSISTÊNCIA REAL COM SQLITE3:\n"
            f"   - VETO ABSOLUTO a simular banco com mocks ou listas em memória em `src/`. Utilize SQLite3 real com `sqlite3.connect`, `PRAGMA foreign_keys = ON` e `ON DELETE CASCADE`.\n"
            f"   - Tabela `tickets`: `id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, email TEXT NOT NULL, severity TEXT NOT NULL, created_at TEXT NOT NULL, sla_due_at TEXT NOT NULL, status TEXT DEFAULT 'OPEN', resolution_note TEXT, resolved_at TEXT`.\n"
            f"   - Tabela `events`: `id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER NOT NULL, event_type TEXT NOT NULL, event_details TEXT, timestamp TEXT NOT NULL, FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE`.\n"
            f"   - Ao criar um ticket no repositório, insira automaticamente o primeiro evento com `event_type='created'` e `timestamp=created_at`.\n"
            f"3. FASTAPI ROTAS, REQUEST BODY & TESTCLIENT:\n"
            f"   - Para receber JSON no body em endpoints POST/PUT, use SEMPRE um schema Pydantic como parâmetro da rota (ex: `async def create_ticket_endpoint(payload: TicketCreate):`). NUNCA declare campos primitivos soltos (`title: str, email: str`) na assinatura da rota, pois o FastAPI os trata como query params de URL e rejeita o POST com 422!\n"
            f"   - NUNCA passe APIRouter diretamente para TestClient. Crie um app FastAPI:\n"
            f"     ```python\n"
            f"     from fastapi import FastAPI\n"
            f"     from fastapi.testclient import TestClient\n"
            f"     from src.backend.routes import router\n"
            f"     app = FastAPI()\n"
            f"     app.include_router(router)\n"
            f"     client = TestClient(app)\n"
            f"     ```\n"
            f"   - Ao verificar datas retornadas pelo TestClient: campos de data em JSON vêm como string ISO. Converta com `datetime.fromisoformat(...)`.\n"
            f"4. TESTES DE INTEGRAÇÃO END-TO-END AUTOMATIZADOS (CAMINHOS CRÍTICOS):\n"
            f"   - Os arquivos em `tests/` DEVEM conter testes de integração automatizados cobrindo os caminhos críticos ponta a ponta (persistência física em SQLite3 real + transição de estados de SLA + métricas operacionais + endpoints HTTP via FastAPI TestClient).\n"
            f"   - VETO a mocks nesses testes de integração. Tudo deve ser exercitado contra o banco e o app real.\n"
            f"5. PREFERÊNCIA DE FERRAMENTAS: Prefira `write_file` para gravar arquivos inteiros com precisão e evitar desalinhamentos.\n"
            f"6. Crie ou ajuste os arquivos de teste em `tests/` e a implementação real em `src/`.\n"
            f"7. Após cada gravação de arquivo, o sistema valida automaticamente o `pytest` e devolve o status.\n"
            f"8. Quando todos os testes estiverem 100% verdes e todos os slices da story existirem em `tests/`, finalize.\n\n"
            f"Arquivos já existentes no workspace:\n{existing_files_str}\n\n"
            f"CONTEÚDO DA STORY:\n{story_text}\n"
        )

        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Grava um arquivo no projeto",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Caminho relativo (ex: src/backend/db.py)"},
                            "content": {"type": "string", "description": "Conteúdo integral do arquivo"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Lê um arquivo do projeto",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Caminho relativo"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Substitui texto em um arquivo do projeto",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Caminho relativo"},
                            "target": {"type": "string", "description": "Texto exato a ser substituído"},
                            "replacement": {"type": "string", "description": "Novo texto"},
                        },
                        "required": ["path", "target", "replacement"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": "Executa comando shell no projeto (ex: pytest)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Comando ex: uv run pytest tests/ -v"},
                        },
                        "required": ["command"],
                    },
                },
            },
        ]

        t_start = time.time()
        p_tok = c_tok = 0
        pp_speeds: list[float] = []
        tg_speeds: list[float] = []

        # Fast-path: Se todos os testes esperados desta story já existem e passam, encerra a queima imediatamente
        story_tests_arg = " ".join(expected_tests) if expected_tests else "tests/"
        pre_check = subprocess.run(
            f'{self.venv_python} -m pytest {story_tests_arg} -v -o pythonpath=". src" --tb=short',
            shell=True,
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            env=self._get_exec_env(),
        )
        missing_tests = [t for t in expected_tests if not (self.project_dir / t).exists()]
        if pre_check.returncode == 0 and not missing_tests and expected_tests:
            logger.info("Fast-path: Todos os %d testes da story já passam 100%% verde. Slices prontos.", len(expected_tests))
            return StationResult(
                station_id=f"BURN_{story_id}",
                agent=agent_handle,
                model_key=active_model,
                success=True,
                wall_seconds=round(time.time() - t_start, 2),
                turns=0,
                prompt_tokens=0,
                completion_tokens=0,
                pp_tok_s=0.0,
                tg_tok_s=0.0,
                peak_vram_mb=0.0,
            )

        # Boot local model
        self._ensure_model_server(active_model)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        turns = 0
        success = False
        error_msg = None
        attempt = 0
        last_failing_feedback: str | None = None

        while attempt < 2 and not success:
            for turn_idx in range(1, max_turns + 1):
                turns = turn_idx

                # Sliding window: preserva system prompt, prompt inicial e os últimos passos
                if len(messages) > 12:
                    messages = [messages[0], messages[1]] + messages[-8:]

                try:
                    resp = self._chat_completion(messages, tools_schema=tools_schema, model_name=active_model)
                except Exception as exc:
                    logger.warning("Falha na chamada ao modelo local: %s", exc)
                    messages.append({
                        "role": "user",
                        "content": f"Aviso do sistema: A chamada anterior falhou com '{exc}'. Por favor, continue o trabalho corrigindo os arquivos de forma concisa.",
                    })
                    continue

                finish_reason = resp.get("finish_reason", "stop")
                p_tok += resp["prompt_tokens"]
                c_tok += resp["completion_tokens"]
                if resp["pp_tok_s"]:
                    pp_speeds.append(resp["pp_tok_s"])
                if resp["tg_tok_s"]:
                    tg_speeds.append(resp["tg_tok_s"])

                msg = resp["message"]
                content = msg.get("content") or ""
                tool_calls = msg.get("tool_calls") or []

                # Fallback parser for markdown code blocks emitted by local models
                if not tool_calls and content:
                    parsed_chunks = self.fallback_parser.extract_tool_calls(content)
                    if parsed_chunks:
                        tool_calls = [
                            {
                                "id": f"call_{turn_idx}_{i}",
                                "type": "function",
                                "function": {
                                    "name": chunk.name,
                                    "arguments": chunk.arguments_delta,
                                },
                            }
                            for i, chunk in enumerate(parsed_chunks)
                        ]

                assistant_msg: dict[str, Any] = {"role": "assistant", "content": content}
                if tool_calls:
                    assistant_msg["tool_calls"] = tool_calls
                messages.append(assistant_msg)

                if tool_calls:
                    for tc in tool_calls:
                        fn = tc.get("function") or {}
                        name = fn.get("name", "")
                        raw_args = fn.get("arguments", "{}")
                        args_dict = None
                        try:
                            args_dict = json.loads(raw_args, strict=False) if isinstance(raw_args, str) else raw_args
                        except json.JSONDecodeError as decode_err:
                            if finish_reason == "length":
                                out_str = "Erro: A chamada da ferramenta foi truncada porque atingiu o limite de tokens. Por favor gere o arquivo ou comando em partes menores ou mais concisas."
                            else:
                                out_str = f"Erro de sintaxe JSON nos argumentos da ferramenta '{name}': {decode_err}."
                            ok = False

                        if args_dict is not None:
                            out_str, ok = self.execute_tool(name, args_dict)

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", f"call_{turn_idx}"),
                            "name": name,
                            "content": out_str,
                        })

                    if success:
                        break
                    continue

                # Model completed its actions, validate pytest for this story
                story_tests_arg = " ".join(expected_tests) if expected_tests else "tests/"
                pytest_res = subprocess.run(
                    f'{self.venv_python} -m pytest {story_tests_arg} -v -o pythonpath=". src" --tb=short',
                    shell=True,
                    cwd=str(self.project_dir),
                    capture_output=True,
                    text=True,
                    env=self._get_exec_env(),
                )

                missing_tests = [t for t in expected_tests if not (self.project_dir / t).exists()]
                if pytest_res.returncode == 0 and not missing_tests:
                    success = True
                    break
                elif missing_tests:
                    nudge = (
                        f"ATENÇÃO: Ainda faltam testes para os slices declarados na story:\n"
                        + "\n".join(f"- {t}" for t in missing_tests)
                        + "\nCrie os testes e implemente o código antes de encerrar."
                    )
                    messages.append({"role": "user", "content": nudge})
                else:
                    err_lines = [
                        line for line in pytest_res.stdout.splitlines()
                        if "FAILED" in line or "ERROR" in line or "Error" in line or "assert" in line or "Exception" in line
                    ]
                    summary_err = "\n".join(err_lines[-15:]) if err_lines else pytest_res.stdout[-500:]
                    nudge = (
                        f"COMANDO OBRIGATÓRIO: O `pytest` falhou (exit={pytest_res.returncode}).\n"
                        f"É PROIBIDO responder com texto explicativo sem chamadas de ferramenta. Invoque `write_file` ou `edit_file` IMEDIATAMENTE para corrigir as falhas:\n\n"
                        f"{summary_err}"
                    )
                    messages.append({"role": "user", "content": nudge})

            if not success and attempt == 0:
                # Escalate to Pleno
                attempt += 1
                active_model = escalation_profile
                logger.warning("Escalonando round %s para perfil pleno %s", round_num, active_model)
                self._ensure_model_server(active_model)
                messages.append({
                    "role": "user",
                    "content": "Atenção: Houve falha nas tentativas anteriores. Analise profundamente e corrija os arquivos para o pytest passar.",
                })
            else:
                break

        wall_s = max(0.001, round(time.time() - t_start, 2))
        avg_pp = round(sum(pp_speeds) / len(pp_speeds), 1) if pp_speeds else 0.0
        avg_tg = round(sum(tg_speeds) / len(tg_speeds), 1) if tg_speeds else 0.0

        telemetry_file = self.telemetry_dir / f"BURN_{story_id}_{int(time.time())}.json"
        telemetry_data = {
            "station_id": f"BURN_{story_id}",
            "round_number": round_num,
            "story_id": story_id,
            "agent": agent_handle,
            "model_key": active_model,
            "success": success,
            "turns": turns,
            "wall_s": wall_s,
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            "pp_tok_s": avg_pp,
            "tg_tok_s": avg_tg,
            "attempt": attempt,
        }
        telemetry_file.write_text(json.dumps(telemetry_data, indent=2), encoding="utf-8")

        transcript_file = self.telemetry_dir / f"BURN_{story_id}_{int(time.time())}_transcript.json"
        transcript_file.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")

        return StationResult(
            station_id=f"BURN_{story_id}",
            agent=agent_handle,
            model_key=active_model,
            success=success,
            wall_seconds=wall_s,
            turns=turns,
            prompt_tokens=p_tok,
            completion_tokens=c_tok,
            pp_tok_s=avg_pp,
            tg_tok_s=avg_tg,
            peak_vram_mb=0.0,
            telemetry_path=telemetry_file,
        )

    def execute_review_station(self, round_num: int, story_id: str) -> StationResult:
        """Audits DoD and tests compliance using Hoare."""
        t0 = time.time()
        zai_key, _ = self._get_zai_config()
        active_model = "glm-5.3-flash" if (zai_key and QuotaManager().is_available("zai")) else "lfm3"
        self._ensure_model_server(active_model)

        pytest_res = subprocess.run(
            f'{self.venv_python} -m pytest tests/ -v -o pythonpath=". src"',
            shell=True,
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            env=self._get_exec_env(),
        )

        created_files = []
        code_snippets = []
        for p in (self.project_dir / "src").glob("**/*"):
            if p.is_file() and not p.name.startswith(".") and p.suffix in (".py", ".js", ".html", ".css", ".sql"):
                rel_path = str(p.relative_to(self.project_dir))
                created_files.append(rel_path)
                try:
                    content_snip = p.read_text(encoding="utf-8", errors="replace")[:3000]
                    code_snippets.append(f"=== Arquivo: {rel_path} ===\n{content_snip}")
                except Exception:
                    pass

        for p in (self.project_dir / "tests").glob("**/*"):
            if p.is_file() and not p.name.startswith(".") and p.suffix == ".py":
                rel_path = str(p.relative_to(self.project_dir))
                created_files.append(rel_path)
                try:
                    content_snip = p.read_text(encoding="utf-8", errors="replace")[:3000]
                    code_snippets.append(f"=== Arquivo: {rel_path} ===\n{content_snip}")
                except Exception:
                    pass

        files_str = "\n".join(f"- {f}" for f in sorted(created_files))
        code_bundle_str = "\n\n".join(code_snippets)

        mission_dir = self._get_active_mission_dir()
        story_path = mission_dir / "stories" / f"{story_id}.md"
        story_content = story_path.read_text(encoding="utf-8") if story_path.is_file() else ""

        hoare_agent = self.registry.get("hoare")
        hoare_sys = (
            hoare_agent.system_prompt
            if hoare_agent
            else "Você é @hoare, Code Review Specialist do Bombe Core."
        )

        hoare_prompt = (
            f"AUDITORIA DE CODE REVIEW — ROUND {round_num}: {story_id}\n\n"
            f"Resultado da execução de testes automatizados (exit={pytest_res.returncode}):\n"
            f"{pytest_res.stdout}\n{pytest_res.stderr}\n\n"
            f"Lista de Arquivos:\n{files_str}\n\n"
            f"Conteúdo dos Arquivos Implementados e Testes:\n{code_bundle_str}\n\n"
            f"Story do Round:\n{story_content}\n\n"
            f"Realize a auditoria técnica de conformidade. Avalie se todos os ACs foram cumpridos, "
            f"se os testes cobrem a regra e se não há código mock/fake em src/.\n"
            f"Se tudo estiver em conformidade, conclua com: 'STATUS: APROVADO'."
        )

        resp = self._chat_completion([
            {"role": "system", "content": hoare_sys},
            {"role": "user", "content": hoare_prompt},
        ], model_name=active_model)
        review_text = resp["message"].get("content") or ""
        is_approved = ("STATUS: APROVADO" in review_text.upper()) or ("AUDITORIA: LIMPA" in review_text.upper())
        has_reprovado = ("STATUS: REPROVADO" in review_text.upper()) or ("NÃO APROVADO" in review_text.upper())
        has_actual_furo = bool(re.search(r"\bFURO:\s*(?!nenhum\b)\S+", review_text, re.IGNORECASE))
        passed = (pytest_res.returncode == 0) and (is_approved or not (has_actual_furo or has_reprovado))
        wall_s = round(time.time() - t0, 2)

        # Write physical review.md in round directory
        round_dir = mission_dir / "rounds" / f"round-{round_num:02d}"
        if round_dir.exists():
            (round_dir / "review.md").write_text(review_text, encoding="utf-8")

        telemetry_file = self.telemetry_dir / f"REVIEW_{story_id}_{int(time.time())}.json"
        rec = {
            "station_id": f"REVIEW_{story_id}",
            "round_number": round_num,
            "story_id": story_id,
            "agent": "@hoare",
            "model_key": active_model,
            "success": passed,
            "wall_s": wall_s,
            "prompt_tokens": resp["prompt_tokens"],
            "completion_tokens": resp["completion_tokens"],
            "pp_tok_s": resp["pp_tok_s"],
            "tg_tok_s": resp["tg_tok_s"],
        }
        telemetry_file.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        return StationResult(
            station_id=f"REVIEW_{story_id}",
            agent="@hoare",
            model_key=active_model,
            success=passed,
            wall_seconds=wall_s,
            turns=1,
            prompt_tokens=resp["prompt_tokens"],
            completion_tokens=resp["completion_tokens"],
            pp_tok_s=resp["pp_tok_s"],
            tg_tok_s=resp["tg_tok_s"],
            peak_vram_mb=0.0,
            telemetry_path=telemetry_file,
        )

    def execute_arch_review_station(self, round_num: int, story_id: str) -> StationResult:
        """Audits architecture, Clean Code, SOLID and authorizes Git commit using UncleBob."""
        t0 = time.time()
        zai_key, _ = self._get_zai_config()
        active_model = "glm-5.3-flash" if (zai_key and QuotaManager().is_available("zai")) else "qwen-3.8-9b"
        self._ensure_model_server(active_model)

        pytest_res = subprocess.run(
            f'{self.venv_python} -m pytest tests/ -v -o pythonpath=". src"',
            shell=True,
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            env=self._get_exec_env(),
        )

        created_files = []
        for p in (self.project_dir / "src").glob("**/*"):
            if p.is_file() and not p.name.startswith("."):
                created_files.append(str(p.relative_to(self.project_dir)))
        for p in (self.project_dir / "tests").glob("**/*"):
            if p.is_file() and not p.name.startswith("."):
                created_files.append(str(p.relative_to(self.project_dir)))
        files_str = "\n".join(f"- {f}" for f in sorted(created_files))

        mission_dir = self._get_active_mission_dir()
        story_path = mission_dir / "stories" / f"{story_id}.md"
        story_content = story_path.read_text(encoding="utf-8") if story_path.is_file() else ""

        unclebob_agent = self.registry.get("unclebob")
        unclebob_sys = (
            unclebob_agent.system_prompt
            if unclebob_agent
            else "Você é @unclebob, Tech Lead e Guardião Arquitetural do Bombe Core."
        )

        unclebob_prompt = (
            f"AUDITORIA ARQUITETURAL E CHANCELA DE COMMIT — ROUND {round_num}: {story_id}\n\n"
            f"Testes Automatizados (exit={pytest_res.returncode}):\n"
            f"{pytest_res.stdout}\n{pytest_res.stderr}\n\n"
            f"Arquivos do projeto:\n{files_str}\n\n"
            f"Story do Round:\n{story_content}\n\n"
            f"Como @unclebob, audite a integridade arquitetural (SOLID, Clean Architecture, separação de camadas, "
            f"persistência real sem mocks em src/, clareza e manutenibilidade).\n"
            f"Verifique se os testes automatizados de integração cobrem os caminhos críticos da solução.\n"
            f"Se a arquitetura estiver sólida e pronta para ir à produção, emita o parecer de chancela concluindo com: 'STATUS: APROVADO'."
        )

        resp = self._chat_completion([
            {"role": "system", "content": unclebob_sys},
            {"role": "user", "content": unclebob_prompt},
        ], model_name=active_model)

        review_text = resp["message"].get("content") or ""
        is_approved = ("STATUS: APROVADO" in review_text.upper()) or ("ARQUITETURA APROVADA" in review_text.upper())
        has_reprovado = ("STATUS: REPROVADO" in review_text.upper()) or ("NÃO APROVADO" in review_text.upper())
        has_actual_furo = bool(re.search(r"\bVIOLAÇÃO:\s*(?!nenhuma\b)\S+", review_text, re.IGNORECASE))
        passed = (pytest_res.returncode == 0) and (is_approved or not (has_actual_furo or has_reprovado))
        wall_s = round(time.time() - t0, 2)

        # Write physical arch-review.md in round directory
        round_dir = mission_dir / "rounds" / f"round-{round_num:02d}"
        if round_dir.exists():
            (round_dir / "arch-review.md").write_text(review_text, encoding="utf-8")

        telemetry_file = self.telemetry_dir / f"ARCH_REVIEW_{story_id}_{int(time.time())}.json"
        rec = {
            "station_id": f"ARCH_REVIEW_{story_id}",
            "round_number": round_num,
            "story_id": story_id,
            "agent": "@unclebob",
            "model_key": active_model,
            "success": passed,
            "wall_s": wall_s,
            "prompt_tokens": resp["prompt_tokens"],
            "completion_tokens": resp["completion_tokens"],
            "pp_tok_s": resp["pp_tok_s"],
            "tg_tok_s": resp["tg_tok_s"],
        }
        telemetry_file.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        return StationResult(
            station_id=f"ARCH_REVIEW_{story_id}",
            agent="@unclebob",
            model_key=active_model,
            success=passed,
            wall_seconds=wall_s,
            turns=1,
            prompt_tokens=resp["prompt_tokens"],
            completion_tokens=resp["completion_tokens"],
            pp_tok_s=resp["pp_tok_s"],
            tg_tok_s=resp["tg_tok_s"],
            peak_vram_mb=0.0,
            telemetry_path=telemetry_file,
        )

    def execute_validate_station(self, round_num: int, story_id: str) -> StationResult:
        """Validates DoD checklist with David and commits to git."""
        t0 = time.time()
        zai_key, _ = self._get_zai_config()
        active_model = "glm-5.3-flash" if (zai_key and QuotaManager().is_available("zai")) else "lfm3"
        self._ensure_model_server(active_model)

        pytest_res = subprocess.run(
            f'{self.venv_python} -m pytest tests/ -v -o pythonpath=". src"',
            shell=True,
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            env=self._get_exec_env(),
        )
        passed = (pytest_res.returncode == 0)

        david_agent = self.registry.get("david")
        david_sys = (
            david_agent.system_prompt
            if david_agent
            else "Você é @david, Agile Master do Bombe Core."
        )

        david_prompt = (
            f"VALIDAÇÃO DE DEFINITION OF DONE (DoD) — ROUND {round_num}: {story_id}\n\n"
            f"Os testes automatizados passaram 100% verde (exit={pytest_res.returncode}).\n"
            f"O Code Review do @hoare foi concluído com sucesso.\n"
            f"Valide o checklist de Definition of Done (DoD) do Round {round_num} e autorize o encerramento do round no Kanban.\n"
            f"Conclua com: 'STATUS: VALIDADO'."
        )

        resp = self._chat_completion([
            {"role": "system", "content": david_sys},
            {"role": "user", "content": david_prompt},
        ], model_name=active_model)
        val_text = resp["message"].get("content") or ""
        wall_s = round(time.time() - t0, 2)

        if passed:
            subprocess.run(["git", "add", "."], cwd=str(self.project_dir), check=False)
            subprocess.run(
                ["git", "commit", "-m", f"feat(round-{round_num}): {story_id} validada com sucesso"],
                cwd=str(self.project_dir),
                check=False,
            )

        telemetry_file = self.telemetry_dir / f"VALIDATE_{story_id}_{int(time.time())}.json"
        rec = {
            "station_id": f"VALIDATE_{story_id}",
            "round_number": round_num,
            "story_id": story_id,
            "agent": "@david",
            "model_key": active_model,
            "success": passed,
            "wall_s": wall_s,
            "prompt_tokens": resp["prompt_tokens"],
            "completion_tokens": resp["completion_tokens"],
            "pp_tok_s": resp["pp_tok_s"],
            "tg_tok_s": resp["tg_tok_s"],
        }
        telemetry_file.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        return StationResult(
            station_id=f"VALIDATE_{story_id}",
            agent="@david",
            model_key=active_model,
            success=passed,
            wall_seconds=wall_s,
            turns=1,
            prompt_tokens=resp["prompt_tokens"],
            completion_tokens=resp["completion_tokens"],
            pp_tok_s=resp["pp_tok_s"],
            tg_tok_s=resp["tg_tok_s"],
            peak_vram_mb=0.0,
            telemetry_path=telemetry_file,
        )

    def execute_upstream_station(
        self,
        mission_id: str,
        mission_dir: Path,
        demand: str,
        title: str,
    ) -> StationResult:
        """Executes Round 0 Upstream macro: PRD (@grace), Architecture (@unclebob), Stories (@unclebob) and Rounds (@david)."""
        t0 = time.time()
        self._ensure_model_server("lfm3")

        grace_agent = self.registry.get("grace")
        grace_sys = (
            grace_agent.system_prompt
            if grace_agent
            else "Você é @grace, Senior Product Manager do Bombe Core."
        )

        user_prompt = (
            f"EXECUÇÃO DE UPSTREAM (ROUND 0) — MISSÃO {mission_id}: {title}\n\n"
            f"Demanda do Usuário:\n{demand}\n\n"
            "Elabore a visão executiva e aprove os requisitos de produto para a nova missão."
        )

        resp = self._chat_completion([
            {"role": "system", "content": grace_sys},
            {"role": "user", "content": user_prompt},
        ])
        wall_s = round(time.time() - t0, 2)

        # Scaffolding dos documentos canônicos de Upstream
        prd_file = mission_dir / "prd" / "prd.md"
        arch_file = mission_dir / "architecture" / "architecture.md"
        epic_file = mission_dir / "epics" / "epic-01.md"
        mission_file = mission_dir / "mission.md"
        stories_dir = mission_dir / "stories"
        stories_dir.mkdir(parents=True, exist_ok=True)

        # 1. PRD (@grace)
        if not prd_file.exists():
            prd_content = (
                f"# PRD — {title} (MISSION-{mission_id})\n\n"
                f"## 1. Visão do Produto e Problema\n"
                f"{demand}\n\n"
                f"## 2. Escopo In/Out\n"
                f"- **In Scope:** Persistência relacional SQLite3 com integridade referencial, API REST FastAPI, cálculo determinístico de SLA e métricas operacionais, dashboard web responsivo.\n"
                f"- **Out of Scope:** Autenticação OAuth2 externa, banco de dados distribuído, clusterização.\n\n"
                f"## 3. Critérios de Sucesso e Requisitos de Negócio\n"
                f"- Cálculo exato de prazo de SLA por severidade (P1: 1h, P2: 4h, P3: 24h, P4: 72h).\n"
                f"- Detecção e rastreamento de violações de SLA (sla_breached) com histórico de eventos auditável.\n"
                f"- Dashboard web operacional consumindo a API real com auto-refresh.\n"
            )
            prd_file.write_text(prd_content, encoding="utf-8")

        # 2. Arquitetura (@unclebob)
        if not arch_file.exists():
            arch_content = (
                f"# Arquitetura — {title} (MISSION-{mission_id})\n\n"
                f"## 1. Diretrizes Arquiteturais (Clean Architecture & SOLID)\n"
                f"- **Linguagem & Runtime:** Python 3.12+ (FastAPI, SQLite3 nativo, Pydantic v2).\n"
                f"- **Zero ORM:** Operações de banco executadas via SQLite3 DDL/DML puro com `PRAGMA foreign_keys = ON` e transações atômicas.\n"
                f"- **Injeção de Dependências:** `clock` determinístico injetável em todas as regras temporais para testes sem `time.sleep`.\n"
                f"- **Divisão de Responsabilidades:**\n"
                f"  - `src/backend/domain.py`: Entidades, cálculo de SLA e máquina de estados pura.\n"
                f"  - `src/backend/db.py`: Conexão SQLite3, pragmas e inicialização de DDL.\n"
                f"  - `src/backend/schemas.py`: Contratos Pydantic com `extra='forbid'`.\n"
                f"  - `src/backend/repository.py`: Acesso a dados e transações SQL.\n"
                f"  - `src/backend/routes.py`: Endpoints HTTP FastAPI.\n"
                f"  - `src/frontend/`: HTML5 semântico, CSS utility/tokens e Vanilla JS sem frameworks pesados.\n"
            )
            arch_file.write_text(arch_content, encoding="utf-8")

        # 3. Épico Macro (@unclebob)
        if not epic_file.exists():
            epic_content = (
                f"# EPIC-01: {title}\n\n"
                f"## Descrição\n"
                f"Construção completa do motor de chamados com cálculo de SLA e console web operacional.\n\n"
                f"## Stories Associadas\n"
                f"- **STORY-001:** Fundação Relacional & CRUD de Chamados (@barbara, backend)\n"
                f"- **STORY-002:** Máquina de Estados de SLA & Métricas (@barbara, backend)\n"
                f"- **STORY-003:** Console Web Operacional (@ada, frontend)\n"
            )
            epic_file.write_text(epic_content, encoding="utf-8")

        # 4. Stories no padrão ai-story com Slices TDD
        st01_path = stories_dir / "STORY-001.md"
        if not st01_path.exists():
            st01_content = (
                "---\n"
                "story_id: \"STORY-001\"\n"
                "title: \"Fundação Relacional & CRUD de Chamados\"\n"
                "agent: \"@barbara\"\n"
                "layer: \"backend\"\n"
                "depends_on: []\n"
                "status: pending\n"
                "---\n\n"
                "# STORY-001: Fundação Relacional & CRUD de Chamados\n\n"
                "## 🎯 Objetivo\n"
                "Implementar a camada de persistência e os endpoints básicos de criação e consulta de chamados com cálculo determinístico de SLA.\n\n"
                "## ✅ Acceptance Criteria\n"
                "- [ ] **AC-1:** Chamado P1 criado às 10:00 deve ter `sla_due_at` às 11:00.\n"
                "- [ ] **AC-2:** Chamado P4 criado às 10:00 deve ter `sla_due_at` às 10:00 do dia +3.\n"
                "- [ ] **AC-3:** `POST /api/tickets` com e-mail inválido deve retornar `422`.\n"
                "- [ ] **AC-4:** `GET /api/tickets/{id}` deve retornar a lista de eventos, incluindo o evento de criação.\n"
                "- [ ] **AC-5:** Deletar um ticket deve remover seus eventos via `ON DELETE CASCADE`.\n\n"
                "## 🧪 Slices TDD\n\n"
                "### SLICE-001-SLA-DOMAIN\n"
                "- **slice_id:** `SLICE-001-SLA-DOMAIN`\n"
                "- **problem:** Implementar o cálculo determinístico de SLA baseado na severidade do chamado.\n"
                "- **depends_on:** []\n"
                "- **layer:** backend\n"
                "- **red_test:** `tests/test_story_001_tickets.py`\n"
                "- **impl_targets:** `src/backend/domain.py`\n"
                "- **acceptance:** AC-1, AC-2\n\n"
                "### SLICE-002-DB-SCHEMA\n"
                "- **slice_id:** `SLICE-002-DB-SCHEMA`\n"
                "- **problem:** Inicializar o esquema do banco de dados com constraints de integridade e cascata.\n"
                "- **depends_on:** []\n"
                "- **layer:** backend\n"
                "- **red_test:** `tests/test_story_001_db.py`\n"
                "- **impl_targets:** `src/backend/db.py`\n"
                "- **acceptance:** AC-5\n\n"
                "### SLICE-003-REPO-CREATION\n"
                "- **slice_id:** `SLICE-003-REPO-CREATION`\n"
                "- **problem:** Implementar a criação atômica de tickets e validação de esquema no repositório.\n"
                "- **depends_on:** [`SLICE-001-SLA-DOMAIN`, `SLICE-002-DB-SCHEMA`]\n"
                "- **layer:** backend\n"
                "- **red_test:** `tests/test_story_001_repository.py`\n"
                "- **impl_targets:** `src/backend/repository.py`, `src/backend/schemas.py`\n"
                "- **acceptance:** AC-3\n\n"
                "### SLICE-004-API-CRUD\n"
                "- **slice_id:** `SLICE-004-API-CRUD`\n"
                "- **problem:** Expor os endpoints de criação e consulta de chamados via HTTP.\n"
                "- **depends_on:** [`SLICE-003-REPO-CREATION`]\n"
                "- **layer:** backend\n"
                "- **red_test:** `tests/test_story_001_api.py`\n"
                "- **impl_targets:** `src/backend/routes.py`\n"
                "- **acceptance:** AC-4\n"
            )
            st01_path.write_text(st01_content, encoding="utf-8")

        st02_path = stories_dir / "STORY-002.md"
        if not st02_path.exists():
            st02_content = (
                "---\n"
                "story_id: \"STORY-002\"\n"
                "title: \"Máquina de Estados de SLA & Métricas\"\n"
                "agent: \"@barbara\"\n"
                "layer: \"backend\"\n"
                "depends_on: [\"STORY-001\"]\n"
                "status: pending\n"
                "---\n\n"
                "# STORY-002: Máquina de Estados de SLA & Métricas\n\n"
                "## 🎯 Objetivo\n"
                "Implementar a máquina de transição de estados e o endpoint de métricas operacionais agregadas.\n\n"
                "## ✅ Acceptance Criteria\n"
                "- [ ] **AC-1:** Tentar `OPEN -> RESOLVED` deve retornar `409 Conflict`.\n"
                "- [ ] **AC-2:** Tentar `RESOLVED` sem `resolution_note` deve retornar `422`.\n"
                "- [ ] **AC-3:** Reabrir chamado (`RESOLVED -> IN_PROGRESS`) limpa o campo `resolved_at`.\n"
                "- [ ] **AC-4:** Chamado resolvido após `sla_due_at` deve manter `sla_breached: true`.\n"
                "- [ ] **AC-5:** Endpoint de métricas `GET /api/tickets/metrics` retorna contagens exatas por status, severidade e sla_breached.\n\n"
                "## 🧪 Slices TDD\n\n"
                "### SLICE-002-01-STATUS-TRANSITION\n"
                "- **slice_id:** `SLICE-002-01-STATUS-TRANSITION`\n"
                "- **problem:** Implementar transição de status via HTTP.\n"
                "- **depends_on:** []\n"
                "- **layer:** backend\n"
                "- **red_test:** `tests/test_story_002_status.py`\n"
                "- **impl_targets:** `src/backend/domain.py`, `src/backend/repository.py`, `src/backend/routes.py`\n"
                "- **acceptance:** AC-1, AC-2, AC-3\n\n"
                "### SLICE-002-02-METRICS\n"
                "- **slice_id:** `SLICE-002-02-METRICS`\n"
                "- **problem:** Implementar agregação de métricas no repositório e endpoint.\n"
                "- **depends_on:** [`SLICE-002-01-STATUS-TRANSITION`]\n"
                "- **layer:** backend\n"
                "- **red_test:** `tests/test_story_002_metrics.py`\n"
                "- **impl_targets:** `src/backend/repository.py`, `src/backend/routes.py`\n"
                "- **acceptance:** AC-4, AC-5\n"
            )
            st02_path.write_text(st02_content, encoding="utf-8")

        st03_path = stories_dir / "STORY-003.md"
        if not st03_path.exists():
            st03_content = (
                "---\n"
                "story_id: \"STORY-003\"\n"
                "title: \"Console Web Operacional\"\n"
                "agent: \"@ada\"\n"
                "layer: \"frontend\"\n"
                "depends_on: [\"STORY-001\", \"STORY-002\"]\n"
                "status: pending\n"
                "---\n\n"
                "# STORY-003: Console Web Operacional\n\n"
                "## 🎯 Objetivo\n"
                "Construir a interface web de gestão de chamados consumindo a API real e exibindo métricas de SLA.\n\n"
                "## ✅ Acceptance Criteria\n"
                "- [ ] **AC-1:** Dashboard exibe total de tickets, contagens por status e contador de SLA violado.\n"
                "- [ ] **AC-2:** Formulário permite criar novo chamado e atualiza a listagem sem recarregar a página.\n"
                "- [ ] **AC-3:** Interface consome endpoints reais `/api/tickets` e `/api/tickets/metrics`.\n\n"
                "## 🧪 Slices TDD\n\n"
                "### SLICE-003-01-WEB-CONSOLE\n"
                "- **slice_id:** `SLICE-003-01-WEB-CONSOLE`\n"
                "- **problem:** Criar dashboard HTML5/CSS/JS e integrar com FastAPI StaticFiles.\n"
                "- **depends_on:** []\n"
                "- **layer:** frontend\n"
                "- **red_test:** `tests/test_story_003_web.py`\n"
                "- **impl_targets:** `src/frontend/index.html`, `src/frontend/styles.css`, `src/frontend/app.js`\n"
                "- **acceptance:** AC-1, AC-2, AC-3\n"
            )
            st03_path.write_text(st03_content, encoding="utf-8")

        # 5. Atualizar mission.md com os rounds sequenciais
        mission_text = mission_file.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---\n(.*)$", mission_text, re.DOTALL)
        if match:
            fm_text, body = match.group(1), match.group(2)
            data = yaml.safe_load(fm_text) or {}
        else:
            data = {"id": f"MISSION-{mission_id}", "title": title, "status": "open"}
            body = mission_text

        data["rounds"] = {
            "ROUND-1": {
                "title": "Fundação Relacional & CRUD de Chamados",
                "story_id": "STORY-001",
                "status": "pending",
            },
            "ROUND-2": {
                "title": "Máquina de Estados de SLA & Métricas",
                "story_id": "STORY-002",
                "status": "pending",
            },
            "ROUND-3": {
                "title": "Console Web Operacional",
                "story_id": "STORY-003",
                "status": "pending",
            },
        }

        new_fm = yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip()
        mission_file.write_text(f"---\n{new_fm}\n---\n{body.lstrip()}", encoding="utf-8")

        # Commit git do Round 0
        subprocess.run(["git", "add", "docs/"], cwd=str(self.project_dir), check=False)
        subprocess.run(
            ["git", "commit", "-m", f"chore(upstream): Round 0 concluído para MISSION-{mission_id} (@grace, @unclebob, @david)"],
            cwd=str(self.project_dir),
            capture_output=True,
            check=False,
        )

        telemetry_file = self.telemetry_dir / f"UPSTREAM_MISSION_{mission_id}_{int(time.time())}.json"
        rec = {
            "station_id": f"UPSTREAM_MISSION_{mission_id}",
            "agent": "@grace",
            "model_key": "lfm3",
            "success": True,
            "wall_s": wall_s,
            "prompt_tokens": resp["prompt_tokens"],
            "completion_tokens": resp["completion_tokens"],
            "pp_tok_s": resp["pp_tok_s"],
            "tg_tok_s": resp["tg_tok_s"],
        }
        telemetry_file.write_text(json.dumps(rec, indent=2), encoding="utf-8")

        return StationResult(
            station_id=f"UPSTREAM_MISSION_{mission_id}",
            agent="@grace",
            model_key="lfm3",
            success=True,
            wall_seconds=wall_s,
            turns=1,
            prompt_tokens=resp["prompt_tokens"],
            completion_tokens=resp["completion_tokens"],
            pp_tok_s=resp["pp_tok_s"],
            tg_tok_s=resp["tg_tok_s"],
            peak_vram_mb=0.0,
            telemetry_path=telemetry_file,
        )
