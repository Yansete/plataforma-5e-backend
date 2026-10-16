"""
Contrato de salida para exportar recursos revisados a formatos externos (Moodle XML, GIFT, etc.).
"""

from __future__ import annotations

from typing import Protocol

from platform5e.domain.review.learning_resource import LearningResourceDomain


class ResourceExporterPort(Protocol):
    """Puerto para la serialización y exportación de recursos formativos aprobados."""

    def export(self, resources: list[LearningResourceDomain]) -> str:
        """Convierte una lista de recursos de dominio aprobados en el formato destino."""
        ...