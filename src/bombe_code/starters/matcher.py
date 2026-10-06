"""Classificador e Matcher Determinístico de Templates & Starters (ST-042).

Permite que Tech Lead e Arquiteto encontrem starters aderentes ao produto,
stack e multitenancy, expondo o manifesto arquitetural para prevenir Architectural Drift.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .engine import StarterEngine

logger = logging.getLogger(__name__)


@dataclass
class ArchitecturalManifest:
    """Convenções arquiteturais e entidades expostas pelo starter."""

    starter_id: str
    multitenancy_type: str
    expected_entities: list[str] = field(default_factory=list)
    suggested_tables: list[str] = field(default_factory=list)
    base_endpoints: list[str] = field(default_factory=list)
    guidelines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "starter_id": self.starter_id,
            "multitenancy_type": self.multitenancy_type,
            "expected_entities": self.expected_entities,
            "suggested_tables": self.suggested_tables,
            "base_endpoints": self.base_endpoints,
            "guidelines": self.guidelines,
        }


@dataclass
class TemplateMatchResult:
    """Resultado do matching determinístico de template."""

    matched: bool
    starter_id: str | None = None
    name: str | None = None
    blueprint: str | None = None
    category: str | None = None
    type: str | None = None
    description: str = ""
    tech_stack: dict[str, Any] = field(default_factory=dict)
    composition: list[str] = field(default_factory=list)
    manifest: ArchitecturalManifest | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "starter_id": self.starter_id,
            "name": self.name,
            "blueprint": self.blueprint,
            "category": self.category,
            "type": self.type,
            "description": self.description,
            "tech_stack": self.tech_stack,
            "composition": self.composition,
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "notes": self.notes,
        }


class TemplateMatcher:
    """Motor de matching determinístico de Starters do catálogo oficial."""

    def __init__(self, engine: StarterEngine | None = None) -> None:
        self.engine = engine or StarterEngine()

    def match(
        self,
        product_type: str,
        backend_language: str,
        frontend_stack: str | None = None,
        multitenancy: str | None = None,
        database: str | None = "postgresql",
    ) -> TemplateMatchResult:
        """Encontra o starter mais adequado para as especificações técnicas fornecidas."""
        p_type = product_type.strip().lower()
        b_lang = self._normalize_lang(backend_language)
        f_stack = self._normalize_frontend(frontend_stack)
        m_tenancy = self._normalize_tenancy(multitenancy)

        candidate_id: str | None = None

        # 1. Chatbot
        if "chatbot" in p_type or "bot" in p_type:
            if b_lang == "python" and (f_stack == "streamlit" or f_stack == "none"):
                candidate_id = "chatbot-py-streamlit"
            elif b_lang == "go" and f_stack == "react":
                candidate_id = "chatbot-go-react"
            elif b_lang == "nodejs" and f_stack == "react":
                candidate_id = "chatbot-node-react"
            elif b_lang == "python":
                candidate_id = "chatbot-py-streamlit"

        # 2. WhatsApp / Omnichannel BFF
        elif any(k in p_type for k in ("whatsapp", "bff", "omnichannel")):
            lang_map = {
                "python": "whatsapp-bff-python",
                "go": "whatsapp-bff-go",
                "nodejs": "whatsapp-bff-node",
                "dotnet": "whatsapp-bff-dotnet",
                "java": "whatsapp-bff-spring",
            }
            candidate_id = lang_map.get(b_lang)

        # 3. Frontend Standalone
        elif p_type in ("frontend", "portal", "web") and (b_lang == "none" or not b_lang):
            candidate_id = "react-portal"

        # 4. SaaS Fullstack vs Backend Standalone
        else:
            is_fullstack = (
                f_stack == "react" or p_type in ("saas", "fullstack") or "fullstack" in p_type
            )

            # Matriz de resolução por linguagem e multitenancy
            matrix: dict[str, dict[str, dict[str, str]]] = {
                "python": {
                    "mono": {"fullstack": "python-mono", "backend": "python-mono-backend"},
                    "multi-logical": {
                        "fullstack": "python-multi-logical",
                        "backend": "python-multi-logical-backend",
                    },
                    "multi-physical": {
                        "fullstack": "python-multi-physical",
                        "backend": "python-multi-physical-backend",
                    },
                },
                "go": {
                    "mono": {"fullstack": "go-mono", "backend": "go-mono-backend"},
                    "multi-logical": {
                        "fullstack": "go-multi-logical",
                        "backend": "go-multi-logical-backend",
                    },
                    "multi-physical": {
                        "fullstack": "go-multi-physical",
                        "backend": "go-multi-physical-backend",
                    },
                },
                "nodejs": {
                    "mono": {
                        "fullstack": "node-mono",
                        "backend": "node-multi-logical-e-mono-backend",
                    },
                    "multi-logical": {
                        "fullstack": "node-multi-logical-e-mono",
                        "backend": "node-multi-logical-e-mono-backend",
                    },
                    "multi-physical": {
                        "fullstack": "node-multi-physical",
                        "backend": "node-multi-physical-backend",
                    },
                },
                "dotnet": {
                    "mono": {"fullstack": "dotnet-mono", "backend": "dotnet-mono-backend"},
                    "multi-logical": {
                        "fullstack": "dotnet-multi-logical",
                        "backend": "dotnet-multi-logical-backend",
                    },
                    "multi-physical": {
                        "fullstack": "dotnet-multi-physical",
                        "backend": "dotnet-multi-physical-backend",
                    },
                },
                "java": {
                    "mono": {"fullstack": "spring-mono", "backend": "spring-mono-backend"},
                    "multi-logical": {
                        "fullstack": "spring-multi-logical",
                        "backend": "spring-multi-logical-backend",
                    },
                    "multi-physical": {
                        "fullstack": "spring-multi-physical",
                        "backend": "spring-multi-physical-backend",
                    },
                },
            }

            lang_dict = matrix.get(b_lang)
            if lang_dict:
                tenancy_dict = lang_dict.get(m_tenancy, lang_dict.get("mono"))
                if tenancy_dict:
                    scope_key = "fullstack" if is_fullstack else "backend"
                    candidate_id = tenancy_dict.get(scope_key)

        if not candidate_id:
            return TemplateMatchResult(
                matched=False,
                notes=(
                    f"Nenhum starter oficial encontrado para o perfil: "
                    f"tipo='{product_type}', backend='{backend_language}', frontend='{frontend_stack}', multitenancy='{multitenancy}'."
                ),
            )

        starter = self.engine.get_starter(candidate_id)
        if not starter:
            return TemplateMatchResult(
                matched=False,
                notes=f"Starter '{candidate_id}' recomendado mas não encontrado no catálogo carregado.",
            )

        manifest = self._build_manifest(starter, m_tenancy)
        return TemplateMatchResult(
            matched=True,
            starter_id=starter["id"],
            name=starter["name"],
            blueprint=starter.get("blueprint"),
            category=starter.get("category"),
            type=starter.get("type"),
            description=starter.get("description", ""),
            tech_stack=starter.get("tech_stack", {}),
            composition=starter.get("composition", []),
            manifest=manifest,
            notes=(
                f"Starter compatível identificado: '{starter['id']}'. "
                "O Tech Lead deve registrar este starter no ADR e Caroli deve criar a STORY-0 no PBB."
            ),
        )

    def _normalize_lang(self, lang: str | None) -> str:
        if not lang:
            return "python"
        l_str = lang.strip().lower()
        if "py" in l_str or "fastapi" in l_str:
            return "python"
        if "go" in l_str or "gin" in l_str:
            return "go"
        if any(k in l_str for k in ("node", "ts", "typescript", "js", "javascript")):
            return "nodejs"
        if any(k in l_str for k in ("dotnet", "c#", "csharp", ".net")):
            return "dotnet"
        if any(k in l_str for k in ("java", "spring")):
            return "java"
        return l_str

    def _normalize_frontend(self, f: str | None) -> str:
        if not f:
            return "none"
        f_str = f.strip().lower()
        if "react" in f_str:
            return "react"
        if "streamlit" in f_str:
            return "streamlit"
        if "none" in f_str or "nao" in f_str or "não" in f_str:
            return "none"
        return f_str

    def _normalize_tenancy(self, t: str | None) -> str:
        if not t:
            return "mono"
        t_str = t.strip().lower()
        if "physical" in t_str or "fisic" in t_str or "físic" in t_str:
            return "multi-physical"
        if "logical" in t_str or "logic" in t_str or "lógic" in t_str:
            return "multi-logical"
        return "mono"

    def _build_manifest(self, starter: dict[str, Any], multitenancy: str) -> ArchitecturalManifest:
        """Gera o manifesto arquitetural detalhado para o DBA e Arquiteto."""
        s_id = starter["id"]
        if multitenancy == "multi-physical":
            entities = ["Tenant", "Customer"]
            tables = ["tenants", "customers"]
            endpoints = ["/health", "/api/v1/tenants", "/api/v1/customers"]
            guidelines = [
                "Isolamento físico por Schema (PostgreSQL schema-per-tenant).",
                "Conexões devem setar search_path dinamicamente via TenantContext.",
                "Não renomeie a tabela 'tenants' para evitar quebra de middleware.",
            ]
        elif multitenancy == "multi-logical":
            entities = ["Tenant", "Product"]
            tables = ["tenants", "products"]
            endpoints = ["/health", "/api/v1/tenants", "/api/v1/products"]
            guidelines = [
                "Isolamento lógico via tenant_id em todas as tabelas de negócio.",
                "TenantContextFilter injeta tenant_id nas queries automaticamente.",
                "Tabela base: 'tenants' com campos id (UUID), name e status.",
            ]
        elif "chatbot" in s_id:
            entities = ["Message", "Conversation", "Agent"]
            tables = ["messages", "conversations"]
            endpoints = ["/health", "/api/chat", "/api/history"]
            guidelines = [
                "Backend orquestrador com streaming e sessões em memória ou cache.",
                "Frontend em Streamlit / React desacoplado via API REST.",
            ]
        elif "whatsapp" in s_id or "bff" in s_id:
            entities = ["WebhookEvent", "MessagePayload", "Sender"]
            tables = ["webhook_events"]
            endpoints = ["/webhook", "/health", "/api/send"]
            guidelines = [
                "Validação de assinatura HMAC SHA256 da Meta obrigatória no endpoint /webhook.",
                "Processamento idempotente de mensagens recebidas.",
            ]
        else:
            # Monotenant padrão
            entities = ["User", "Role"]
            tables = ["users", "roles"]
            endpoints = ["/health", "/api/v1/auth/login", "/api/v1/users"]
            guidelines = [
                "Arquitetura Monotenant limpa com autenticação JWT.",
                "Tabela de usuários canônica é 'users' (campos: id, email, password_hash).",
                "DBA e Arquiteto devem estender 'users' em vez de criar 'usuarios' ou 'clientes_tb'.",
            ]

        return ArchitecturalManifest(
            starter_id=s_id,
            multitenancy_type=multitenancy,
            expected_entities=entities,
            suggested_tables=tables,
            base_endpoints=endpoints,
            guidelines=guidelines,
        )
