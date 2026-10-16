"""
Caso de uso: exporta únicamente los recursos formativos aprobados por el docente.
"""

from __future__ import annotations

from typing import Any

from platform5e.application.ports.outbound.resource_exporter_port import ResourceExporterPort
from platform5e.domain.shared.errors import NoApprovedResourcesError


class ExportApprovedResourcesUseCase:
    """Orquesta la obtención y serialización de recursos aprobados hacia formatos externos."""

    def __init__(
        self,
        review_service: Any,
        exporter: ResourceExporterPort,
    ) -> None:
        self._review_service = review_service
        self._exporter = exporter

    def execute(self, export_format: str) -> str:
        """Valida el formato solicitado y ejecuta la exportación."""
        if export_format not in ("moodle_xml", "qti21", "documento"):
            raise ValueError("Formato no soportado")

        approved = self._review_service.get_approved_for_export()
        if not approved:
            raise NoApprovedResourcesError("Sin recursos aprobados para exportar")

        return self._exporter.export(approved)