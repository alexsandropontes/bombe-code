"""Modelos de dados para o subsistema de Skills sob Demanda."""

from pydantic import BaseModel, Field


class SkillSummary(BaseModel):
    """Resumo compacto de uma skill para catálogos e buscas leves."""

    name: str = Field(..., description="Identificador único da skill em kebab-case")
    description: str = Field(..., description="Descrição resumida do propósito da skill")
    category: str = Field(default="general", description="Categoria temática da skill")


class SkillDefinition(BaseModel):
    """Definição completa de uma skill, contendo o corpo instrucional."""

    name: str = Field(..., description="Identificador único da skill em kebab-case")
    description: str = Field(..., description="Descrição resumida do propósito da skill")
    category: str = Field(default="general", description="Categoria temática da skill")
    instruction_content: str = Field(..., description="Corpo instrucional da skill em Markdown")

    def to_summary(self) -> SkillSummary:
        """Converte a definição completa para um resumo compacto."""
        return SkillSummary(
            name=self.name,
            description=self.description,
            category=self.category,
        )
