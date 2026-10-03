"""Registro e Fábrica de LEGO de Snippets do Bombe Code (ST-025).

Contém blocos de código auditados e prontos para reuso em Python, Go e Node.js.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_SNIPPETS_DIR = Path(__file__).resolve().parent.parent / "registry" / "snippets"


BUILTIN_SNIPPETS: list[dict[str, Any]] = [
    {
        "name": "validar-cpf",
        "platform": "python",
        "category": "data-validation",
        "description": "Valida se uma sequência numérica constitui um CPF brasileiro válido segundo o algoritmo oficial.",
        "tags": ["cpf", "documento", "brasil", "validação"],
        "filename": "validar_cpf.py",
        "test_filename": "test_validar_cpf.py",
        "code": '''"""Validação de CPF brasileiro."""

import re

def validar_cpf(cpf: str) -> bool:
    """Verifica os dois dígitos verificadores do CPF."""
    cpf_limpo = re.sub(r"\\D", "", cpf or "")
    if len(cpf_limpo) != 11:
        return False
    if cpf_limpo == cpf_limpo[0] * 11:
        return False

    # Primeiro dígito
    soma = sum(int(cpf_limpo[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    if int(cpf_limpo[9]) != digito1:
        return False

    # Segundo dígito
    soma = sum(int(cpf_limpo[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    return int(cpf_limpo[10]) == digito2
''',
        "tests": '''"""Testes para validar_cpf."""

from validar_cpf import validar_cpf

def test_validar_cpf_valido():
    # CPFs de teste matematicamente válidos
    assert validar_cpf("52998224725") is True
    assert validar_cpf("529.982.247-25") is True

def test_validar_cpf_invalido():
    assert validar_cpf("111.111.111-11") is False
    assert validar_cpf("12345678900") is False
    assert validar_cpf("") is False
''',
    },
    {
        "name": "validar-cnpj",
        "platform": "python",
        "category": "data-validation",
        "description": "Valida se uma sequência numérica constitui um CNPJ brasileiro válido com cálculo dos 2 dígitos.",
        "tags": ["cnpj", "empresa", "brasil", "validação"],
        "filename": "validar_cnpj.py",
        "test_filename": "test_validar_cnpj.py",
        "code": '''"""Validação de CNPJ brasileiro."""

import re

def validar_cnpj(cnpj: str) -> bool:
    """Verifica os dígitos verificadores do CNPJ."""
    cnpj_limpo = re.sub(r"\\D", "", cnpj or "")
    if len(cnpj_limpo) != 14:
        return False
    if cnpj_limpo == cnpj_limpo[0] * 14:
        return False

    # Primeiro dígito
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj_limpo[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    d1 = 0 if resto < 2 else 11 - resto
    if int(cnpj_limpo[12]) != d1:
        return False

    # Segundo dígito
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj_limpo[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    d2 = 0 if resto < 2 else 11 - resto
    return int(cnpj_limpo[13]) == d2
''',
        "tests": '''"""Testes para validar_cnpj."""

from validar_cnpj import validar_cnpj

def test_validar_cnpj():
    assert validar_cnpj("11.222.333/0001-81") is True
    assert validar_cnpj("00.000.000/0000-00") is False
''',
    },
    {
        "name": "format-phone",
        "platform": "python",
        "category": "utils",
        "description": "Formata telefone brasileiro para padrão (XX) XXXXX-XXXX ou (XX) XXXX-XXXX.",
        "tags": ["telefone", "celular", "formatação", "brasil"],
        "filename": "format_phone.py",
        "test_filename": "test_format_phone.py",
        "code": '''"""Formatação de telefone brasileiro."""

import re

def formatar_telefone(telefone: str) -> str:
    nums = re.sub(r"\\D", "", telefone or "")
    if len(nums) == 11:
        return f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
    if len(nums) == 10:
        return f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
    return telefone
''',
        "tests": '''"""Testes para formatar_telefone."""

from format_phone import formatar_telefone

def test_formatar_telefone():
    assert formatar_telefone("11987654321") == "(11) 98765-4321"
    assert formatar_telefone("1133334444") == "(11) 3333-4444"
''',
    },
    {
        "name": "hash-password",
        "platform": "python",
        "category": "auth",
        "description": "Funções seguras de hash e verificação de senha usando HMAC e PBKDF2/SHA256 nativo.",
        "tags": ["segurança", "auth", "hash", "senha", "crypto"],
        "filename": "hash_password.py",
        "test_filename": "test_hash_password.py",
        "code": '''"""Hash de senhas seguro."""

import hashlib
import os

def gerar_hash_senha(senha: str) -> str:
    salt = os.urandom(16)
    kdf = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{kdf.hex()}"

def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        salt_hex, kdf_hex = hash_armazenado.split(":")
        salt = bytes.fromhex(salt_hex)
        novo_kdf = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 100_000)
        return novo_kdf.hex() == kdf_hex
    except Exception:
        return False
''',
        "tests": '''"""Testes para hash de senha."""

from hash_password import gerar_hash_senha, verificar_senha

def test_hash_e_verificacao():
    h = gerar_hash_senha("minha-senha-secreta")
    assert verificar_senha("minha-senha-secreta", h) is True
    assert verificar_senha("senha-errada", h) is False
''',
    },
    {
        "name": "validar-cpf",
        "platform": "go",
        "category": "data-validation",
        "description": "Validador de CPF brasileiro em Go com dígitos verificadores.",
        "tags": ["cpf", "documento", "brasil", "go"],
        "filename": "validar_cpf.go",
        "test_filename": "validar_cpf_test.go",
        "code": """package utils

import (
	"regexp"
	"strconv"
)

func ValidarCPF(cpf string) bool {
	re := regexp.MustCompile(`\\D`)
	clean := re.ReplaceAllString(cpf, "")
	if len(clean) != 11 {
		return false
	}
	allEqual := true
	for i := 1; i < 11; i++ {
		if clean[i] != clean[0] {
			allEqual = false
			break
		}
	}
	if allEqual {
		return false
	}

	var sum int
	for i := 0; i < 9; i++ {
		num, _ := strconv.Atoi(string(clean[i]))
		sum += num * (10 - i)
	}
	rem := sum % 11
	d1 := 0
	if rem >= 2 {
		d1 = 11 - rem
	}
	realD1, _ := strconv.Atoi(string(clean[9]))
	if realD1 != d1 {
		return false
	}

	sum = 0
	for i := 0; i < 10; i++ {
		num, _ := strconv.Atoi(string(clean[i]))
		sum += num * (11 - i)
	}
	rem = sum % 11
	d2 := 0
	if rem >= 2 {
		d2 = 11 - rem
	}
	realD2, _ := strconv.Atoi(string(clean[10]))
	return realD2 == d2
}
""",
        "tests": """package utils

import "testing"

func TestValidarCPF(t *testing.T) {
	if !ValidarCPF("52998224725") {
		t.Errorf("Esperado valido")
	}
	if ValidarCPF("11111111111") {
		t.Errorf("Esperado invalido")
	}
}
""",
    },
    {
        "name": "validar-cpf",
        "platform": "nodejs",
        "category": "data-validation",
        "description": "Validador de CPF brasileiro em TypeScript/JavaScript.",
        "tags": ["cpf", "documento", "brasil", "node", "typescript"],
        "filename": "validarCpf.ts",
        "test_filename": "validarCpf.test.ts",
        "code": """export function validarCpf(cpf: string): boolean {
  const clean = (cpf || "").replace(/\\D/g, "");
  if (clean.length !== 11) return false;
  if (/^(\\d)\\1{10}$/.test(clean)) return false;

  let sum = 0;
  for (let i = 0; i < 9; i++) {
    sum += parseInt(clean.charAt(i), 10) * (10 - i);
  }
  let rest = sum % 11;
  const d1 = rest < 2 ? 0 : 11 - rest;
  if (parseInt(clean.charAt(9), 10) !== d1) return false;

  sum = 0;
  for (let i = 0; i < 10; i++) {
    sum += parseInt(clean.charAt(i), 10) * (11 - i);
  }
  rest = sum % 11;
  const d2 = rest < 2 ? 0 : 11 - rest;
  return parseInt(clean.charAt(10), 10) === d2;
}
""",
        "tests": """import { describe, it, expect } from "vitest";
import { validarCpf } from "./validarCpf";

describe("validarCpf", () => {
  it("valida CPF correto", () => {
    expect(validarCpf("52998224725")).toBe(true);
  });
  it("rejeita digitos repetidos", () => {
    expect(validarCpf("11111111111")).toBe(false);
  });
});
""",
    },
]


class SnippetRegistry:
    """Catálogo e gerenciador de blocos de snippets reutilizáveis com suporte a catálogo dinâmico."""

    def __init__(
        self,
        snippets: list[dict[str, Any]] | None = None,
        registry_dir: Path | str | None = None,
    ) -> None:
        self.registry_dir = Path(registry_dir).resolve() if registry_dir else DEFAULT_SNIPPETS_DIR
        self.snippets: list[dict[str, Any]] = []

        if snippets:
            self.snippets = list(snippets)
        else:
            self._load_snippets()

    def _load_snippets(self) -> None:
        """Carrega todos os snippets do catálogo em disco e combina com built-ins."""
        seen: set[tuple[str, str]] = set()

        # 1. Carrega snippets do catálogo físico
        if self.registry_dir.is_dir():
            for yaml_path in sorted(self.registry_dir.glob("**/*/snippet.yaml")):
                folder = yaml_path.parent
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                    if not data or not isinstance(data, dict):
                        continue

                    name = data.get("name")
                    if not name:
                        continue

                    plat = data.get("platform") or yaml_path.relative_to(self.registry_dir).parts[0]
                    cat = data.get("category") or yaml_path.relative_to(self.registry_dir).parts[1]
                    key = (name.lower(), plat.lower())

                    # Localiza arquivo de código
                    code_files = [
                        f
                        for f in folder.iterdir()
                        if f.is_file()
                        and f.name not in ("snippet.yaml", "__init__.py")
                        and not f.name.endswith(".pyc")
                    ]
                    test_folder = folder / "tests"
                    test_files = (
                        [
                            f
                            for f in test_folder.iterdir()
                            if f.is_file()
                            and f.name not in ("__init__.py",)
                            and not f.name.endswith(".pyc")
                        ]
                        if test_folder.is_dir()
                        else []
                    )

                    code_file = code_files[0] if code_files else None
                    test_file = test_files[0] if test_files else None

                    code_content = code_file.read_text(encoding="utf-8") if code_file else ""
                    test_content = test_file.read_text(encoding="utf-8") if test_file else ""

                    # Determina nomes de arquivo para exportação
                    # Se for snippet.py/js/go, usa nome amigável derivado
                    code_filename = code_file.name if code_file else "snippet.txt"
                    if code_filename == "snippet.py":
                        code_filename = f"{name.replace('-', '_')}.py"
                    elif code_filename == "snippet.js":
                        code_filename = f"{name.replace('-', '_')}.js"
                    elif code_filename == "snippet.go":
                        code_filename = f"{name.replace('-', '_')}.go"
                    elif code_filename == "snippet.ts":
                        code_filename = f"{name.replace('-', '_')}.ts"

                    test_filename = test_file.name if test_file else "test_snippet.txt"

                    entry = {
                        "name": name,
                        "platform": plat,
                        "category": cat,
                        "description": data.get("description", ""),
                        "tags": data.get("tags", []) or [],
                        "filename": code_filename,
                        "test_filename": test_filename,
                        "code": code_content,
                        "tests": test_content,
                        "dependencies": data.get("dependencies", []) or [],
                        "invariants": data.get("invariants", []) or [],
                        "exports": data.get("exports", []) or [],
                        "folder_path": str(folder),
                    }
                    self.snippets.append(entry)
                    seen.add(key)
                except (OSError, yaml.YAMLError, ValueError, KeyError) as e:
                    logger.warning(f"Erro ao carregar snippet em '{yaml_path}': {e}")

        # 2. Adiciona ou sobrescreve com builtins
        for b in BUILTIN_SNIPPETS:
            b_key = (b["name"].lower(), b["platform"].lower())
            if b_key not in seen:
                self.snippets.append(dict(b))
                seen.add(b_key)
            else:
                # Se o builtin tem filename específico e documentado, preserva para compatibilidade estrita
                for s in self.snippets:
                    if (s["name"].lower(), s["platform"].lower()) == b_key:
                        if "filename" in b:
                            s["filename"] = b["filename"]
                        if "test_filename" in b:
                            s["test_filename"] = b["test_filename"]

    def list_snippets(
        self, platform: str | None = None, category: str | None = None
    ) -> list[dict[str, Any]]:
        """Lista os snippets disponíveis com filtros opcionais."""
        res = []
        for s in self.snippets:
            if platform and s.get("platform", "").lower() != platform.lower():
                continue
            if category and s.get("category", "").lower() != category.lower():
                continue
            res.append(
                {
                    "name": s["name"],
                    "platform": s["platform"],
                    "category": s.get("category", "utils"),
                    "description": s.get("description", ""),
                    "tags": s.get("tags", []),
                }
            )
        return res

    def search(self, query: str, platform: str | None = None) -> list[dict[str, Any]]:
        """Pesquisa snippets por termo no nome, descrição ou tags."""
        q = query.strip().lower()
        res = []
        for s in self.snippets:
            if platform and s.get("platform", "").lower() != platform.lower():
                continue
            name = s.get("name", "").lower()
            desc = s.get("description", "").lower()
            tags = [t.lower() for t in s.get("tags", [])]

            if q in name or q in desc or any(q in t for t in tags):
                res.append(
                    {
                        "name": s["name"],
                        "platform": s["platform"],
                        "category": s.get("category", "utils"),
                        "description": s.get("description", ""),
                        "tags": s.get("tags", []),
                    }
                )
        return res

    def get_snippet(self, name: str, platform: str = "python") -> dict[str, Any] | None:
        """Obtém a definição completa do snippet com código e testes."""
        clean_name = name.strip().lower()
        clean_plat = platform.strip().lower()

        for s in self.snippets:
            if (
                s.get("name", "").lower() == clean_name
                and s.get("platform", "").lower() == clean_plat
            ):
                return dict(s)
        return None

    def copy_snippet(self, name: str, to_dir: str, platform: str = "python") -> dict[str, Any]:
        """Copia os arquivos de código e teste do snippet para a pasta de destino."""
        snip = self.get_snippet(name, platform=platform)
        if not snip:
            return {
                "success": False,
                "error": f"Snippet '{name}' ({platform}) não encontrado no catálogo.",
            }

        dest = Path(to_dir).resolve()
        dest.mkdir(parents=True, exist_ok=True)

        code_file = dest / snip["filename"]
        test_file = dest / snip["test_filename"]

        code_file.write_text(snip["code"], encoding="utf-8")
        test_file.write_text(snip["tests"], encoding="utf-8")

        return {
            "success": True,
            "name": name,
            "platform": platform,
            "target_dir": str(dest),
            "files": [str(code_file), str(test_file)],
            "message": f"Snippet '{name}' ({platform}) instalado com sucesso em {dest}.",
        }
