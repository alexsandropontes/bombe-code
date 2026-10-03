"""Turing Prompt Assembler — Montador Modular de Prompts ("Lego de Prompts").

Monta deterministamente o prompt de execução dos agentes combinando blocos
de acordo com o DELIVERY_TARGET e o Modo de Engenharia (tdd-code vs vibe-code).
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class DeliveryTarget(str, Enum):
    """Níveis de maturidade e objetivo de entrega do produto."""

    SNIPPET = "snippet"
    PROTOTYPE = "prototype"
    POC = "poc"
    MVP = "mvp"
    PRODUCTION = "production"
    ENTERPRISE = "enterprise"

    @classmethod
    def from_str(cls, value: str | None) -> DeliveryTarget:
        if not value:
            return cls.MVP
        val = value.strip().lower()
        for member in cls:
            if member.value == val:
                return member
        return cls.MVP


class TuringPromptAssembler:
    """Montador determinístico de prompts do Turing Runtime."""

    CANONICAL_CLAUSE = (
        "The system MUST NOT assume MVP, production or enterprise requirements "
        "unless explicitly required by the selected target."
    )

    ANTI_SCOPE_CREEP_BLOCK = (
        "### 🛡️ DIRETRIZ FUNDAMENTAL: TETO MÁXIMO DA DEMANDA E SOBERANIA DO PEDIDO (ANTI-SCOPE CREEP / YAGNI RADICAL E CORTE DE INVENTIVIDADE DA LLM)\n"
        "1. SOBERANIA ABSOLUTA DO PEDIDO: O pedido do usuário é o TETO MÁXIMO DA DEMANDA. Tudo o que o usuário explicitamente pedir é MANDATÓRIO e inegociável. "
        "A IA NUNCA tem autoridade para julgar o pedido do usuário como 'supérfluo' ou cortá-lo. "
        "Se o usuário pediu um botão rosa, entregue o botão rosa. Se pediu um quiz com 10 perguntas, entregue exatamente o quiz com 10 perguntas.\n"
        "2. CORTE DO SUPÉRFLUO DA PRÓPRIA LLM: O que deve ser rigorosamente cortado é APENAS o que a LLM inventar por conta própria. "
        "É TERMINANTEMENTE PROIBIDO inventar modelos de negócio SaaS, planos de assinatura, cobrança (billing), "
        "painéis de CRM, multi-tenancy, analytics complexo, CPF ou módulos adicionais que o usuário NÃO solicitou.\n"
        "3. DETALHES NÃO ESPECIFICADOS: Se o usuário não definiu um detalhe estético ou secundário, corte o supérfluo dessa decisão e adote "
        "a solução mais neutra, sóbria e limpa possível. NUNCA use a ausência de detalhes para amputar o miolo da funcionalidade pedida.\n"
        f"4. CLÁUSULA CANÔNICA: {CANONICAL_CLAUSE}"
    )


    TARGET_BLOCKS: dict[DeliveryTarget, str] = {
        DeliveryTarget.SNIPPET: (
            "### 🎯 DELIVERY TARGET: SNIPPET\n"
            "- Objetivo: Resolver uma necessidade pontual de código, algoritmo ou função isolada.\n"
            "- Rigor: Teste unitário estrito da função ou bloco.\n"
            "- Restrição: Zero infraestrutura, zero persistência, zero telas ou arquivos desnecessários."
        ),
        DeliveryTarget.POC: (
            "### 🎯 DELIVERY TARGET: POC (Proof of Concept)\n"
            "- Objetivo: Validar uma hipótese técnica ou conceitual isolada.\n"
            "- Rigor: Escopo estritamente restrito à hipótese investigada.\n"
            "- Restrição: Mocks são permitidos onde não invalidarem a hipótese. Hardening de produção não é necessário."
        ),
        DeliveryTarget.PROTOTYPE: (
            "### 🎯 DELIVERY TARGET: PROTOTYPE\n"
            "- Objetivo: Explorar interface, jornada visual e experiência do usuário (UX).\n"
            "- Rigor: Interface funcional e navegável com estados de tela claros.\n"
            "- Restrição: Backend e persistência em memória/simulados são permitidos. Foco em usabilidade."
        ),
        DeliveryTarget.MVP: (
            "### 🎯 DELIVERY TARGET: MVP OPERACIONAL\n"
            "- Objetivo: Versão mínima funcional capaz de ser utilizada por usuários externos reais.\n"
            "- Rigor: Não é POC nem protótipo. Funcionalidades essenciais não podem ser simuladas por mocks, "
            "stubs ou dados falsos. Persistência real e integrações reais necessárias para o fluxo.\n"
            "- Restrição: Zero Scope Creep. Não adicione nenhum recurso além da demanda estrita solicitada."
        ),
        DeliveryTarget.PRODUCTION: (
            "### 🎯 DELIVERY TARGET: PRODUCTION\n"
            "- Objetivo: Sistema operacional estável e robusto para operação real de produção.\n"
            "- Rigor: Hardening de segurança, tratamento abrangente de falhas, resiliência e migrações formais.\n"
            "- Restrição: Cobertura de testes abrangente e tolerância a falhas."
        ),
        DeliveryTarget.ENTERPRISE: (
            "### 🎯 DELIVERY TARGET: ENTERPRISE\n"
            "- Objetivo: Sistema operacional de alta escala com rigor corporativo elevado.\n"
            "- Rigor: Requisitos avançados de segurança (RLS, isolamento), observabilidade, auditoria formal, "
            "resiliência, escalabilidade e conformidade (LGPD/compliance).\n"
            "- Restrição: Governança técnica e integridade arquitetural absolutas."
        ),
    }

    def assemble(
        self,
        agent_handle: str,
        task_instruction: str,
        delivery_target: DeliveryTarget | str = DeliveryTarget.MVP,
        mode: str = "tdd-code",
        context: dict[str, Any] | None = None,
    ) -> str:
        """Monta o prompt final combinando blocos modulares."""
        # Modo vibe-code: entrega prompt livre sem amarras rígidas
        if mode == "vibe-code":
            if context:
                ctx_str = "\n".join(f"- {k}: {v}" for k, v in context.items())
                return f"{task_instruction}\n\nContexto:\n{ctx_str}"
            return task_instruction

        # Modo tdd-code: montagem de blocos governados
        target = (
            delivery_target
            if isinstance(delivery_target, DeliveryTarget)
            else DeliveryTarget.from_str(delivery_target)
        )

        blocks: list[str] = [
            f"# INSTRUÇÃO DE TRABALHO PARA {agent_handle.upper()}",
            self.ANTI_SCOPE_CREEP_BLOCK,
            self.TARGET_BLOCKS.get(target, self.TARGET_BLOCKS[DeliveryTarget.MVP]),
            f"### 📋 TAREFA ESPECÍFICA:\n{task_instruction.strip()}",
        ]

        if context:
            ctx_lines = [f"- {k}: {v}" for k, v in context.items()]
            blocks.append("### 📁 CONTEXTO E ARTEFATOS EM DISCO:\n" + "\n".join(ctx_lines))

        return "\n\n".join(blocks)
