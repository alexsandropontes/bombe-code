"""Unit: regras de permissão (F6 do PRD: RN1, RN3, RN4)."""

from bombe_code.permissions.rules import PermissionService, Rule
from bombe_code.permissions.shell_scan import is_external, scan_shell_command


def test_default_e_ask():
    service = PermissionService()
    assert service.evaluate("read", "qualquer.py") == "ask"


def test_ultima_regra_vence():
    service = PermissionService(
        rules=[
            Rule(permission="read", pattern="*", action="ask"),
            Rule(permission="read", pattern="*.py", action="allow"),
        ]
    )
    assert service.evaluate("read", "app.py") == "allow"
    assert service.evaluate("read", "nota.txt") == "ask"


def test_wildcard_no_permission_e_no_pattern():
    service = PermissionService(rules=[Rule(permission="*", pattern="*", action="deny")])
    assert service.evaluate("webfetch", "http://x") == "deny"


def test_regras_aprovadas_sao_prioritarias():
    base = [Rule(permission="bash", pattern="rm", action="ask")]
    approved = [Rule(permission="bash", pattern="rm", action="allow")]
    service = PermissionService(rules=base, approved=approved)
    assert service.evaluate("bash", "rm") == "allow"


def test_disabled_tools_esconde_deny_star():
    service = PermissionService(
        rules=[
            Rule(permission="webfetch", pattern="*", action="deny"),
            Rule(permission="read", pattern="*.env", action="deny"),
        ]
    )
    assert service.disabled_tools() == {"webfetch"}


def test_scan_shell_separa_comandos_base():
    assert scan_shell_command("rm -rf / && echo ok | grep x") == [
        "rm",
        "echo",
        "grep",
    ]
    assert scan_shell_command("ls -la") == ["ls"]


def test_is_external_detecta_fora_do_worktree(tmp_path):
    interno = tmp_path / "src" / "a.py"
    interno.parent.mkdir(parents=True)
    interno.write_text("x", encoding="utf-8")
    assert is_external(str(interno), str(tmp_path)) is False
    assert is_external("/etc/passwd", str(tmp_path)) is True
