"""
Caso de uso: exporta los recursos aprobados de una unidad en el formato pedido y registra la descarga en el historial.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import uuid4

from platform5e.application.ports.outbound.resource_repository_port import ResourceReviewRepositoryPort
from platform5e.application.ports.outbound.teacher_repository_port import TeacherRepositoryPort
from platform5e.application.ports.outbound.unit_exporter_port import ExportedFile, UnitExporterPort
from platform5e.domain.accounts.teacher_account import AccountConfigurationError

# Quitar "aprobado" cuando los valores guardados estén migrados al inglés.
APPROVED_STATUSES: set[str] = {"approved", "aprobado"}


class ExportUnitResourcesUseCase:
    """Busca la unidad del docente, filtra lo aprobado y delega el archivo al exportador del formato pedido."""

    def __init__(
        self,
        teacher_repository: TeacherRepositoryPort,
        review_repository: ResourceReviewRepositoryPort,
        exporters: Sequence[UnitExporterPort],
    ) -> None:
        self._teacher_repository = teacher_repository
        self._review_repository = review_repository
        self._exporters = {exporter.format: exporter for exporter in exporters}

    @property
    def formats(self) -> list[str]:
        return sorted(self._exporters)

    def execute(
        self, teacher_id: str, unit_id: str, export_format: str, resource_ids: Sequence[str] = ()
    ) -> ExportedFile:
        course, unit = next(
            (
                (course, unit)
                for course in self._teacher_repository.get_courses(teacher_id)
                for unit in course["units"]
                if unit["id"] == unit_id
            ),
            (None, None),
        )
        if unit is None:
            raise AccountConfigurationError("UNIDAD_NO_ENCONTRADA", "La unidad no pertenece a tus cursos.", 404)

        exporter = self._exporters.get(export_format)
        if exporter is None:
            raise AccountConfigurationError("FORMATO_INVALIDO", "El formato de exportación no es válido.", 422)

        wanted = set(resource_ids)
        approved = [
            resource
            for resource in self._review_repository.get_resources_by_unit(teacher_id, unit_id)
            if resource.get("status") in APPROVED_STATUSES and (not wanted or resource["id"] in wanted)
        ]
        if not approved:
            raise AccountConfigurationError(
                "SIN_RECURSOS_APROBADOS", "Elige al menos un recurso aprobado.", 422
            )

        exported = exporter.export(approved, course, unit)
        self._review_repository.save_download(
            teacher_id,
            unit_id,
            {
                "id": f"descarga-{uuid4()}",
                "unitId": unit_id,
                "format": export_format,
                "fileName": exported.file_name,
                "resourceCount": len(approved),
                "createdAt": datetime.now(timezone.utc).isoformat(),
            },
        )
        return exported
