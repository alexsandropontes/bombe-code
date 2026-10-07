"""Testes da Política de Branches e Promoção (implementada no produto).

dev-working-ia = memória operacional da IA (nunca no remoto, histórico sujo OK)
dev/hml/main   = estados aprovados; promoção para dev SEMPRE via squash (1 commit)
"""

import subprocess
from pathlib import Path

import pytest

from bombe_code.turing.promocao import BRANCH_TRABALHO, PromotorDeBranches


@pytest.fixture
def repo_ia(tmp_path: Path) -> Path:
    """Repositório de projeto com trabalho da IA em dev-working-ia."""

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=str(tmp_path), capture_output=True, check=True)

    git("init", "-b", "main")
    git("config", "user.email", "ia@teste")
    git("config", "user.name", "IA")
    (tmp_path / "app.py").write_text("print('oi')\n")
    git("add", "-A")
    git("commit", "-m", "início do projeto")
    git("switch", "-c", BRANCH_TRABALHO)
    # trabalho sujo da IA: vários commits, inclusive quebrando e consertando
    (tmp_path / "feature.py").write_text("def a(): ...\n")
    git("add", "-A")
    git("commit", "-m", "tenta 1")
    (tmp_path / "feature.py").write_text("def a(): raise NotImplementedError\n")
    git("add", "-A")
    git("commit", "-m", "quebrou (código fingido)")
    (tmp_path / "feature.py").write_text("def a(): return 'real'\n")
    git("add", "-A")
    git("commit", "-m", "consertou — estado estável")
    return tmp_path


def test_garantir_branch_trabalho_cria_e_assume(repo_ia: Path):
    promotor = PromotorDeBranches(repo_ia)
    res = promotor.garantir_branch_trabalho()
    assert res.success
    assert promotor.branch_atual() == BRANCH_TRABALHO


def test_promocao_dev_consolida_em_um_commit(repo_ia: Path):
    promotor = PromotorDeBranches(repo_ia)

    def count_commits(branch: str) -> int:
        out = subprocess.run(
            ["git", "rev-list", "--count", branch],
            cwd=str(repo_ia),
            capture_output=True,
            text=True,
            check=False,
        )
        return int(out.stdout.strip())

    res = promotor.promover_para_dev("feat(ONDA-001): entrega homologada")
    assert res.success, res.mensagem

    assert count_commits("dev") == 1, "squash falhou: dev não é um commit único do estado"
    # A branch de trabalho preserva a memória operacional (3+ commits sujos)
    assert count_commits(BRANCH_TRABALHO) >= 3
    # O conteúdo aprovado está em dev
    subprocess.run(["git", "switch", "dev"], cwd=str(repo_ia), capture_output=True, check=True)
    assert "return 'real'" in (repo_ia / "feature.py").read_text()
    assert "NotImplementedError" not in (repo_ia / "feature.py").read_text()
    subprocess.run(
        ["git", "switch", BRANCH_TRABALHO], cwd=str(repo_ia), capture_output=True, check=True
    )


def test_promocao_hml_e_main_passo_a_passo(repo_ia: Path):
    promotor = PromotorDeBranches(repo_ia)
    assert promotor.promover_para_dev("feat: onda homologada").success

    r_hml = promotor.promover_fase("hml")
    assert r_hml.success, r_hml.mensagem
    r_main = promotor.promover_fase("main")
    assert r_main.success, r_main.mensagem

    # A hierarquia é fixa: não existe promoção direta working→main nem
    # destino fora da cadeia (trunk/dev/main a partir de main etc.)
    assert promotor.promover_fase("trunk").success is False
    assert promotor.promover_fase("dev").success is False


def test_promocao_sem_repositorio_falha_limpo(tmp_path: Path):
    res = PromotorDeBranches(tmp_path).promover_para_dev("qualquer")
    assert res.success is False
    assert "Git" in res.mensagem


def test_release_calcula_versao_por_tema_dos_commits(repo_ia: Path):
    """feat desde a última tag → minor; só correção → patch."""
    promotor = PromotorDeBranches(repo_ia)

    # Sem tag ainda: 0.1.0
    assert promotor.calcular_proxima_versao() == "0.1.0"
    r = promotor.gerar_release(mensagem="chore(release): v0.1.0")
    assert r.success and r.mensagem.startswith("Release v0.1.0")

    # Só correções → patch
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=str(repo_ia), capture_output=True, check=True)

    (repo_ia / "fix.txt").write_text("x\n")
    git("add", "-A")
    git("commit", "-m", "fix: corrige overflow")
    assert promotor.calcular_proxima_versao() == "0.1.1"

    # Com feat → minor
    (repo_ia / "feat.txt").write_text("y\n")
    git("add", "-A")
    git("commit", "-m", "feat: nova funcionalidade")
    assert promotor.calcular_proxima_versao() == "0.2.0"

    # Versão IMPOSTA pelo usuário vence a sugestão
    r = promotor.gerar_release(mensagem="chore(release): v9.9.9", versao="9.9.9")
    assert r.success and "v9.9.9" in r.mensagem
    import subprocess as _sp

    tags = _sp.run(
        ["git", "tag", "-l", "v*"],
        cwd=str(repo_ia),
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    assert "v9.9.9" in tags and "v0.1.0" in tags
