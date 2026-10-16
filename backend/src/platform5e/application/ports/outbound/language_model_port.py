"""
Puerto del modelo de lenguaje / motor generativo de recursos pedagógicos.
"""

from __future__ import annotations

from typing import Any, Protocol


class ResourceGeneratorPort(Protocol):
    """Contrato del generador de recursos (LLM o generador determinista por reglas)."""

    description: str
    uses_ai: bool

    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Recibe el contexto estructurado y devuelve {'resources': [...]}.

        Cada recurso contiene título, contenido, citas de fragmentos del contexto
        y alternativas justificadas.
        """
        ...