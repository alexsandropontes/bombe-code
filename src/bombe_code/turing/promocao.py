"""Promotor de Branches — Política de Branches e Promoção do Bombe Code.

Hierarquia canônica:
- dev-working-ia = memória operacional da IA (commits livres, NUNCA no remoto)
- dev   = histórico oficial (só estados aprovados, SEMPRE via squash)
- hml   = homologação
- main  = produção

Regras implementadas:
1. O trabalho dos agentes acontece em `dev-working-ia` (a plataforma garante
   a branch no início da construção e na entrega).
2. Promoção para `dev` = SQUASH do estado final aprovado em UM commit
   (somente quando acionada — fim de onda homologada ou pedido do humano).
3. Promoção `dev → hml → main` = fusão controlada do estado, um passo por vez.
4. NUNCA push automático: o remoto é responsabilidade do humano.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BRANCH_TRABALHO = "dev-working-ia"
BRANCH_OFICIAL = "dev"
PROXIMA_PROMOCAO = {"dev": "hml", "hml": "main"}


@dataclass
class ResultadoPromocao:
    """Resultado de uma operação de promoção/branch."""

    success: bool
    acao: str
    mensagem: str
    detalhes: list[str] = field(default_factory=list)


class PromotorDeBranches:
    """Executa a política de branches do projeto governado pela ONDA."""

    def __init__(self, project_dir: str | Path) -> None:
        self.project_dir = Path(project_dir)

    # ------------------------------------------------------------- infra
    def _git(self, *args: str) -> tuple[int, str]:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(self.project_dir),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        saida = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, saida.strip()

    def eh_repositorio(self) -> bool:
        if not self.project_dir.exists():
            return False
        rc, _ = self._git("rev-parse", "--is-inside-work-tree")
        return rc == 0

    def branch_atual(self) -> str:
        rc, saida = self._git("rev-parse", "--abbrev-ref", "HEAD")
        return saida.strip() if rc == 0 else ""

    def tem_mudancas(self) -> bool:
        rc, saida = self._git("status", "--porcelain")
        return rc == 0 and bool(saida.strip())

    # -------------------------------------------------- branch de trabalho
    def garantir_branch_trabalho(self) -> ResultadoPromocao:
        """Garante que o projeto está em `dev-working-ia` (cria se não existir)."""
        if not self.eh_repositorio():
            return ResultadoPromocao(False, "garantir", "Projeto não é um repositório Git.")
        atual = self.branch_atual()
        if atual == BRANCH_TRABALHO:
            return ResultadoPromocao(True, "garantir", f"Já em {BRANCH_TRABALHO}.")
        rc, saida = self._git("switch", "-c", BRANCH_TRABALHO)
        if rc == 0:
            return ResultadoPromocao(
                True, "garantir", f"{BRANCH_TRABALHO} criada a partir de {atual}."
            )
        rc, saida = self._git("switch", BRANCH_TRABALHO)
        if rc == 0:
            return ResultadoPromocao(True, "garantir", f"Assumindo {BRANCH_TRABALHO} existente.")
        return ResultadoPromocao(False, "garantir", f"Falha ao assumir {BRANCH_TRABALHO}: {saida}")

    def _commit_estado_da_ia(self, mensagem: str) -> ResultadoPromocao:
        """Commita TODO o estado corrente na branch de trabalho (memória operacional)."""
        self._git("add", "-A")
        rc, saida = self._git("commit", "-m", mensagem, "--allow-empty")
        if rc == 0:
            return ResultadoPromocao(True, "commit", "Estado da IA registrado.")
        if "nothing to commit" in saida:
            return ResultadoPromocao(True, "commit", "Nada a registrar (estado já commitado).")
        return ResultadoPromocao(False, "commit", f"Falha ao commitar estado da IA: {saida}")

    # ---------------------------------------------------------- dev (squash)
    def ultima_versao(self) -> tuple[str, str]:
        """Última tag de versão (vX.Y.Z) e o commit dela. ("", "") se nenhuma."""
        rc, saida = self._git("tag", "--list", "v*", "--sort=-v:refname")
        if rc != 0 or not saida.strip():
            return "", ""
        tag = saida.splitlines()[0].strip()
        rc, commit = self._git("rev-parse", f"{tag}^{{commit}}")
        return (tag, commit.strip() if rc == 0 else "")

    def calcular_proxima_versao(self) -> str:
        """feat: desde a última tag → +0.1.0; só correções/outros → +0.0.1.

        Sem tag anterior: parte de 0.1.0.
        """
        tag, _ = self.ultima_versao()
        if not tag:
            return "0.1.0"
        try:
            maior, menor, patch = (int(x) for x in tag.lstrip("v").split("."))
        except ValueError:
            return "0.1.0"
        _, logs = self._git("log", f"{tag}..{BRANCH_TRABALHO}", "--pretty=%s")
        temas = (logs or "").lower()
        if "feat" in temas:
            return f"{maior}.{menor + 1}.0"
        return f"{maior}.{menor}.{patch + 1}"

    def _aplicar_versao_no_estado(self, versao: str) -> None:
        """Aplica a versão no pyproject.toml e __init__.py do estado corrente."""
        import re as _re

        for rel, pattern in (
            ("pyproject.toml", r'(^version\s*=\s*")[^"]+(")'),
            ("src/bombe_code/__init__.py", r'(^__version__\s*=\s*")[^"]+(")'),
        ):
            caminho = self.project_dir / rel
            if not caminho.exists():
                continue
            conteudo = caminho.read_text(encoding="utf-8")
            novo = _re.sub(
                pattern,
                lambda m: f"{m.group(1)}{versao}{m.group(2)}",
                conteudo,
                count=1,
                flags=_re.MULTILINE,
            )
            caminho.write_text(novo, encoding="utf-8")

    def promover_para_dev(self, mensagem: str) -> ResultadoPromocao:
        """Promove o ESTADO FINAL de `dev-working-ia` para `dev` em UM commit (squash).

        Embalagem pura — versão e tag são responsabilidade de `/project release`.
        Acionada por fim de onda homologada, pedido do humano ou ship. Nunca push.
        """
        detalhes: list[str] = []

        if not self.eh_repositorio():
            return ResultadoPromocao(False, "dev", "Projeto não é um repositório Git.")

        garantia = self.garantir_branch_trabalho()
        detalhes.append(garantia.mensagem)
        if not garantia.success:
            return ResultadoPromocao(False, "dev", garantia.mensagem, detalhes)

        commit_ia = self._commit_estado_da_ia(f"wip(ia): {mensagem}")
        detalhes.append(commit_ia.mensagem)
        if not commit_ia.success:
            return ResultadoPromocao(False, "dev", commit_ia.mensagem, detalhes)

        rc, _ = self._git("rev-parse", "--verify", BRANCH_OFICIAL)
        dev_existe = rc == 0

        if dev_existe:
            # EMBALAGEM DE RELEASE via commit-tree: o novo commit de dev recebe
            # a ÁRVORE EXATA do estado aprovado da working-ia (zero conflitos —
            # não há merge entre linhagens independentes) e pai = release
            # anterior de dev (linha de releases linear e limpa).
            rc, pai = self._git("rev-parse", BRANCH_OFICIAL)
            if rc != 0:
                return ResultadoPromocao(False, "dev", f"Falha ao ler dev: {pai}", detalhes)
            rc, arvore = self._git("rev-parse", f"{BRANCH_TRABALHO}^{{tree}}")
            if rc != 0:
                return ResultadoPromocao(
                    False, "dev", f"Falha ao ler árvore do estado: {arvore}", detalhes
                )
            rc, novo = self._git("commit-tree", arvore, "-p", pai.strip(), "-m", mensagem)
            if rc != 0:
                return ResultadoPromocao(
                    False, "dev", f"Falha ao embalar release: {novo}", detalhes
                )
            rc, _ = self._git("update-ref", f"refs/heads/{BRANCH_OFICIAL}", novo.strip())
            if rc != 0:
                return ResultadoPromocao(False, "dev", "Falha ao atualizar a branch dev.", detalhes)
            detalhes.append("Release embalado (árvore do estado aprovado, pai = release anterior).")
        else:
            # dev ainda não existe: nasce como snapshot de UM commit do estado aprovado
            rc, saida = self._git("switch", "--orphan", BRANCH_OFICIAL)
            if rc != 0:
                return ResultadoPromocao(False, "dev", f"Falha ao criar dev: {saida}", detalhes)
            rc, _ = self._git("checkout", BRANCH_TRABALHO, "--", ".")
            self._git("add", "-A")
            rc, saida = self._git("commit", "-m", mensagem)
            if rc != 0:
                return ResultadoPromocao(
                    False, "dev", f"Falha ao commitar dev inicial: {saida}", detalhes
                )

        detalhes.append(f"Estado aprovado consolidado em {BRANCH_OFICIAL} (squash, 1 commit).")
        self._git("switch", BRANCH_TRABALHO)
        detalhes.append(f"Retornando ao trabalho em {BRANCH_TRABALHO}.")
        return ResultadoPromocao(True, "dev", f"ONDA promovida para dev: {mensagem}", detalhes)

    # ----------------------------------------------------------- release
    def analisar_release(self) -> dict[str, Any]:
        """Analisa os commits desde a última tag e sugere a próxima versão."""
        tag, _ = self.ultima_versao()
        faixa = f"{tag}..{BRANCH_TRABALHO}" if tag else BRANCH_TRABALHO
        _, logs = self._git("log", faixa, "--pretty=%s")
        temas = [t.strip() for t in (logs or "").splitlines() if t.strip()]
        sugestao = self.calcular_proxima_versao()
        return {
            "ultima_tag": tag or "nenhuma",
            "commits": temas,
            "total": len(temas),
            "tem_feat": any(t.lower().startswith("feat") for t in temas),
            "versao_sugerida": sugestao,
        }

    def gerar_release(
        self, mensagem: str | None = None, versao: str | None = None
    ) -> ResultadoPromocao:
        """Empacota e TAGA a versão: analisa commits, aplica a versão (sugerida
        ou imposta pelo usuário), commita `chore(release)` e cria a tag vXY.Z
        na branch de trabalho. Não promove nem faz push (isso é o ship)."""
        if not self.eh_repositorio():
            return ResultadoPromocao(False, "release", "Projeto não é um repositório Git.")

        garantia = self.garantir_branch_trabalho()
        detalhes = [garantia.mensagem]
        if not garantia.success:
            return ResultadoPromocao(False, "release", garantia.mensagem, detalhes)

        analise = self.analisar_release()
        versao_final = (versao or "").strip() or analise["versao_sugerida"]
        msg_release = (
            mensagem
            or f"chore(release): v{versao_final} ({analise['total']} commits desde {analise['ultima_tag']})"
        )

        self._aplicar_versao_no_estado(versao_final)
        commit = self._commit_estado_da_ia(msg_release)
        detalhes.append(commit.mensagem)

        rc, _ = self._git("tag", "-a", f"v{versao_final}", "-m", f"v{versao_final} — release")
        if rc != 0:
            return ResultadoPromocao(
                False, "release", f"Falha ao criar a tag v{versao_final} (já existe?)", detalhes
            )

        detalhes.append(
            f"Commits considerados: {analise['total']} (feat presente: {analise['tem_feat']})."
        )
        return ResultadoPromocao(
            True,
            "release",
            f"Release v{versao_final} gerado e tagado em {BRANCH_TRABALHO}.",
            detalhes,
        )

    # ------------------------------------------------------ hml / main
    def promover_fase(self, destino: str) -> ResultadoPromocao:
        """Promove o estado um passo na hierarquia (dev→hml, hml→main).

        Fusão controlada do estado já aprovado (ff-only; divergência é erro,
        pois oficial não deve divergir do aprovado).
        """
        origem = {v: k for k, v in PROXIMA_PROMOCAO.items()}.get(destino)
        if not origem:
            return ResultadoPromocao(
                False, destino, f"Destino inválido: {destino}. Use hml ou main."
            )
        if not self.eh_repositorio():
            return ResultadoPromocao(False, destino, "Projeto não é um repositório Git.")

        rc, saida = self._git("rev-parse", "--verify", origem)
        if rc != 0:
            return ResultadoPromocao(False, destino, f"Origem '{origem}' não existe ainda.")
        rc, _ = self._git("rev-parse", "--verify", destino)
        if rc != 0:
            # destino nasce do estado aprovado da origem
            rc, saida = self._git("branch", destino, origem)
            if rc == 0:
                return ResultadoPromocao(
                    True, destino, f"'{destino}' criada a partir de '{origem}'."
                )
            return ResultadoPromocao(False, destino, f"Falha ao criar {destino}: {saida}")

        rc, _ = self._git("switch", destino)
        if rc != 0:
            return ResultadoPromocao(False, destino, f"Falha ao assumir {destino}.")
        # 1ª tentativa: fast-forward (histórico linear). Se divergiu, promoção
        # CONTROLADA com merge --no-ff (dois pais: produção + estado aprovado).
        rc, saida = self._git("merge", "--ff-only", origem)
        if rc != 0:
            rc, saida = self._git(
                "merge",
                "--no-ff",
                "--allow-unrelated-histories",
                "-m",
                f"promoção controlada: {origem} → {destino} (estado aprovado)",
                origem,
            )
            if rc != 0:
                self._git("merge", "--abort")
                self._git("switch", BRANCH_TRABALHO)
                return ResultadoPromocao(
                    False,
                    destino,
                    f"Conflito na promoção {origem} → {destino}: {saida}",
                )
            detalhes = ["merge --no-ff registrado (produção recebeu o estado aprovado)."]
        else:
            detalhes = ["fast-forward."]
        self._git("switch", BRANCH_TRABALHO)
        return ResultadoPromocao(
            True, destino, f"Estado promovido: {origem} → {destino}.", detalhes
        )
