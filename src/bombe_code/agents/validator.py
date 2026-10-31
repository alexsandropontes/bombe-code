"""Validador determinístico de integridade de Dossiês de Agentes (PDW 4.0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import yaml
from pydantic import BaseModel, Field


class DossierValidationReport(BaseModel):
    """Resultado determinístico da validação de um dossiê de agente."""

    is_valid: bool = Field(..., description="Indica se o dossiê atende 100% ao padrão PDW 4.0")
    file_path: str = Field(default="", description="Caminho do arquivo validado")
    errors: list[str] = Field(
        default_factory=list, description="Lista de inconformidades encontradas"
    )


class AgentDossierValidator:
    """Validador estrito de conformidade de Dossiês PDW 4.0."""

    REQUIRED_FRONTMATTER_KEYS: ClassVar[set[str]] = {
        "name",
        "description",
        "version",
        "author",
        "metadata",
        "authority",
        "identity",
        "vibe",
        "constraints",
        "routing_triggers",
        "skills",
    }

    FORBIDDEN_ATTRIBUTES: ClassVar[set[str]] = {
        "sign",
        "mbti",
        "age",
        "gender",
    }

    REQUIRED_COGNITIVE_FIELDS: ClassVar[list[str]] = [
        "- **Autoridade:**",
        "- **Postura Cognitiva:**",
        "- **Viés Operacional:**",
        "- **Temperamento Técnico:**",
        "- **Tom de Voz:**",
        "- **Heurísticas Sentinelas:**",
    ]

    REQUIRED_CANONICAL_SECTIONS: ClassVar[list[str]] = [
        "1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA",
        "2. MISSÃO",
        "3. BASE",
        "4. REGRAS",
        "5. RESTRIÇÕES",
        "6. ENTREGA",
    ]

    def _check_forbidden_keys(self, data: Any, prefix: str = "") -> list[str]:
        errors: list[str] = []
        if isinstance(data, dict):
            for k, v in data.items():
                k_lower = str(k).lower()
                if k_lower in self.FORBIDDEN_ATTRIBUTES:
                    errors.append(
                        f"Atributo proibido '{k}' encontrado em {prefix or 'frontmatter'}"
                    )
                errors.extend(self._check_forbidden_keys(v, f"{prefix}.{k}" if prefix else str(k)))
        return errors

    def _validate_frontmatter(self, fm: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not isinstance(fm, dict):
            return ["Bloco de frontmatter YAML inválido (não é dicionário)"]

        missing = self.REQUIRED_FRONTMATTER_KEYS - set(fm.keys())
        if missing:
            errors.append(f"Chaves obrigatórias ausentes no frontmatter: {sorted(missing)}")

        errors.extend(self._check_forbidden_keys(fm))
        return errors

    def _validate_sections(self, body: str) -> list[str]:
        errors: list[str] = []
        if "# 1. IDENTIDADE" in body:
            errors.append(
                "Uso de '# 1. IDENTIDADE' é proibido; use '# 1. PERFIL COMPORTAMENTAL & POSTURA COGNITIVA'"
            )

        for sec in self.REQUIRED_CANONICAL_SECTIONS:
            # Aceita variações como "# 4. REGRAS (MODO OPERACIONAL)"
            expected_prefix = f"# {sec.split()[0]}"
            if expected_prefix not in body and f"# {sec}" not in body:
                errors.append(f"Seção canônica obrigatória ausente: '{sec}'")
        return errors

    def _validate_cognitive_profile(self, body: str) -> list[str]:
        errors: list[str] = []
        for marker in self.REQUIRED_COGNITIVE_FIELDS:
            if marker not in body:
                name = marker.replace("- **", "").replace(":**", "")
                errors.append(f"Campo de postura cognitiva ausente na Seção 1: '{name}'")
        return errors

    def validate_content(self, content: str, file_path: str = "") -> DossierValidationReport:
        errors: list[str] = []
        trimmed = content.strip()
        if not trimmed.startswith("---"):
            return DossierValidationReport(
                is_valid=False,
                file_path=file_path,
                errors=["Arquivo não inicia com bloco de frontmatter YAML '---'"],
            )

        parts = trimmed.split("---", 2)
        if len(parts) < 3:
            return DossierValidationReport(
                is_valid=False,
                file_path=file_path,
                errors=["Bloco de frontmatter YAML malformado ou não encerrado com '---'"],
            )

        fm_text = parts[1]
        body = parts[2]

        try:
            fm_data = yaml.safe_load(fm_text) or {}
            errors.extend(self._validate_frontmatter(fm_data))
        except (yaml.YAMLError, ValueError) as exc:
            errors.append(f"Erro de parsing YAML no frontmatter: {exc}")

        errors.extend(self._validate_sections(body))
        errors.extend(self._validate_cognitive_profile(body))

        return DossierValidationReport(
            is_valid=len(errors) == 0,
            file_path=file_path,
            errors=errors,
        )

    def validate_file(self, file_path: Path | str) -> DossierValidationReport:
        p = Path(file_path).resolve()
        if not p.is_file():
            return DossierValidationReport(
                is_valid=False,
                file_path=str(p),
                errors=[f"Arquivo não encontrado: {p}"],
            )
        content = p.read_text(encoding="utf-8")
        return self.validate_content(content, file_path=str(p))

    def validate_all(self, directory: Path | str) -> dict[str, DossierValidationReport]:
        dir_path = Path(directory).resolve()
        reports: dict[str, DossierValidationReport] = {}
        for md_file in sorted(dir_path.glob("*.md")):
            reports[md_file.name] = self.validate_file(md_file)
        return reports
