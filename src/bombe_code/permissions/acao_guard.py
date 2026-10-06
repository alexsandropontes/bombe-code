"""Guardiã Determinística de Ações — anti-alucinação de verdade.

Premissa: TIMEOUT DE EXECUÇÃO NÃO GARANTE segurança contra alucinação —
uma LLM alucinando no segundo 200 pode causar estrago nos 280s restantes.
A proteção real é validar CADA AÇÃO antes de executá-la, com semântica de
evolução de conteúdo (não contagem burra de repetições):

1. FRAUDE DE CONTEÚDO: NotImplementedError, TODO/FIXME, mocks, vazio → VETO.
2. ESCRITA DUPLICADA EXATA: mesmo conteúdo regravado → VETO (desperdício).
3. CONSTRUÇÃO PROGRESSIVA (LEGÍTIMA): nova escrita CONTÉM a anterior
   (arquivo grande construído em partes) → permitido, sem contagem de churn.
4. BRIGA DE CONTEÚDO: escritas divergentes (nem duplicata, nem extensão)
   repetidas no mesmo arquivo → VETO (a LLM está "brigando" consigo mesma).
5. LEITURA REPETIDA: arquivos grandes exigem releituras — limite frouxo com
   aviso ao agente; red flag só em excesso claro.
6. LOOP DE AÇÃO GENÉRICO: mesma assinatura tool+args → BANDEIRA VERMELHA.

Bandeira vermelha ≠ timeout: é evidência determinística de comportamento
indevido, capturada ANTES do estrago — e o trabalho já gravado permanece.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field

# Padrões de conteúdo que NUNCA podem ser gravados como código de produção
FRAUDES_CONTEUDO: tuple[tuple[str, str], ...] = (
    (r"NotImplementedError", "NotImplementedError (código fingido)"),
    (r"^\s*(#|//|/\*)\s*TODO\b", "TODO aberto em vez de implementação"),
    (r"^\s*(#|//)\s*FIXME\b", "FIXME aberto em vez de implementação"),
    (r"\bunittest\.mock\b|\bMagicMock\b|\bAsyncMock\b", "mock de teste em produção"),
    (r"pass\s*(#.*)?$", "corpo vazio com pass"),
)

# Limites (todos determinísticos)
MAX_ESCRITAS_DUPLICADAS = 1  # 2ª escrita idêntica veta (1 > 1 falso, 2 > 1 veto)
MAX_BRIGAS_CONTEUDO = 1  # 2ª escrita divergente (nem dup, nem extensão) veta
AVISO_LEITURAS = 5  # relê o mesmo alvo 5x → aviso ao agente
RED_FLAG_LEITURAS = 8  # 8x → bandeira vermelha (claro excesso)
MAX_VETOS = 3  # 3 vetos na execução → bandeira vermelha
MAX_ASSINATURAS_IGUAIS = 3  # loop genérico de ação
_TAMANHO_MAX_CONTEUDO_ARMAZENADO = 400_000  # cap de memória por arquivo


class RedFlagError(Exception):
    """Bandeira vermelha: a LLM perde o direito de continuar agindo."""


@dataclass
class GuardaDeAcoes:
    """Estado de governança de UMA execução de agente."""

    agente: str = "@desconhecido"

    vetoes: int = 0
    escritas: int = 0
    red_flag: str | None = None
    _escritas_por_arquivo: Counter = field(default_factory=Counter)
    _assinaturas: Counter = field(default_factory=Counter)
    _leituras: Counter = field(default_factory=Counter)
    # path → {"conteudo": str, "hash": str} (último estado conhecido)
    _ultimo_conteudo: dict[str, dict[str, str]] = field(default_factory=dict)

    # ----------------------------------------------------------- escrita
    def validar_escrita(self, path: str, content: str) -> str | None:
        """Valida UMA escrita antes de gravar. Retorna motivo de veto ou None."""
        if self.red_flag:
            return f"execução interrompida por bandeira vermelha: {self.red_flag}"

        # 1. Fraude de conteúdo (sempre primeiro)
        for pattern, motivo in FRAUDES_CONTEUDO:
            if re.search(pattern, content or "", re.MULTILINE):
                return self._vetar(f"escrita de '{path}' bloqueada: {motivo}")

        # 2. Conteúdo vazio disfarçado de entrega
        if not (content or "").strip():
            return self._vetar(f"escrita de '{path}' bloqueada: conteúdo vazio")

        chave = path.strip().lower()
        h_atual = hashlib.sha256((content or "").encode()).hexdigest()
        estado_anterior = self._ultimo_conteudo.get(chave)

        if estado_anterior:
            # 3. Escrita duplicada exata (desperdício puro)
            if h_atual == estado_anterior["hash"]:
                self._escritas_por_arquivo[chave] += 1
                if self._escritas_por_arquivo[chave] >= MAX_ESCRITAS_DUPLICADAS:
                    return self._vetar(
                        f"'{path}' regravado com conteúdo IDÊNTICO ao já gravado "
                        f"({self._escritas_por_arquivo[chave]}x) — ação desperdiçada"
                    )
            # 4. Construção progressiva: nova versão CONTÉM a anterior → legítimo
            elif estado_anterior["conteudo"] and estado_anterior["conteudo"].strip() in (
                content or ""
            ):
                self._escritas_por_arquivo[chave] = 0
            else:
                # 5. Briga de conteúdo: divergente (nem dup, nem extensão)
                self._escritas_por_arquivo[chave] += 1
                if self._escritas_por_arquivo[chave] >= MAX_BRIGAS_CONTEUDO + 1:
                    return self._vetar(
                        f"'{path}' regravado com conteúdo divergente repetidamente "
                        f"(briga de conteúdo — {self._escritas_por_arquivo[chave]} versões conflitantes)"
                    )

        # Registra o novo estado (com cap de memória)
        if len(content or "") <= _TAMANHO_MAX_CONTEUDO_ARMAZENADO:
            self._ultimo_conteudo[chave] = {"conteudo": content or "", "hash": h_atual}
        else:
            self._ultimo_conteudo[chave] = {"conteudo": "", "hash": h_atual}

        self.escritas += 1
        return None

    # ----------------------------------------------------------- leitura
    def registrar_leitura(self, path: str) -> str:
        """Registra leitura repetida do mesmo alvo. Retorna aviso (ou '').
        Arquivos grandes LEGITIMAMENTE exigem releituras — limite frouxo."""
        chave = (path or "").strip().lower()
        self._leituras[chave] += 1
        n = self._leituras[chave]
        if n > RED_FLAG_LEITURAS and not self.red_flag:
            self.red_flag = f"excesso de leituras do mesmo alvo: '{path}' lido {n}x nesta execução"
        if n >= AVISO_LEITURAS:
            return (
                f"\n⚠️ AVISO DA GUARDIÃ: esta é a {n}ª leitura de '{path}' nesta execução. "
                "Se o conteúdo já foi obtido, prossiga com a missão."
            )
        return ""

    # ------------------------------------------------------- ação genérica
    def registrar_acao(self, tool_name: str, args: str) -> None:
        """Detecta loop de ação: mesma assinatura tool+args repetida."""
        if self.red_flag:
            return
        assinatura = hashlib.sha256(f"{tool_name}:{args or ''}".encode()).hexdigest()[:16]
        self._assinaturas[assinatura] += 1
        if self._assinaturas[assinatura] > MAX_ASSINATURAS_IGUAIS:
            self.red_flag = (
                f"loop de ação detectado: {tool_name} com os mesmos argumentos "
                f"{self._assinaturas[assinatura]}x nesta execução"
            )

    # -------------------------------------------------------------- interno
    def _vetar(self, motivo: str) -> str:
        self.vetoes += 1
        if self.vetoes >= MAX_VETOS and not self.red_flag:
            self.red_flag = f"{self.vetoes} vetos da Guardiã nesta execução (último: {motivo})"
        return f"🚩 VETO DA GUARDIÃ: {motivo}. Corrija o conteúdo e tente de novo."
