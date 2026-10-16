"""
Servicio de aplicación para la gestión y aprobación de recursos pedagógicos individuales.
"""

from __future__ import annotations

from typing import Any

from platform5e.application.ports.outbound.resource_repository_port import (
    LearningResourceRepositoryPort,
)
from platform5e.domain.review.learning_resource import (
    AlternativeDomain,
    LearningResourceDomain,
)
from platform5e.domain.shared.errors import EntityNotFoundError


class LearningResourceService:
    """Gestiona el ciclo de vida, decisiones de alternativas y aprobación de recursos individuales."""

    def __init__(self, repository: LearningResourceRepositoryPort) -> None:
        self.repository = repository

    def get_resource(self, resource_id: str) -> LearningResourceDomain:
        resource = self.repository.get_by_id(resource_id)
        if not resource:
            raise EntityNotFoundError("Recurso no encontrado")
        return resource

    def get_all_resources(self) -> list[LearningResourceDomain]:
        return self.repository.get_all()

    def get_approved_for_export(self) -> list[LearningResourceDomain]:
        return [
            r
            for r in self.repository.get_all()
            if getattr(r, "review_status", getattr(r, "estado_revision", "")) in ("aprobado", "approved")
        ]

    def decide_option(
        self, resource_id: str, letter: str, decision: str, new_text: str | None = None
    ) -> LearningResourceDomain:
        if decision not in ("aceptar", "descartar", "editar"):
            raise ValueError("Decisión inválida")
        resource = self.get_resource(resource_id)
        target_option = next((opt for opt in resource.alternatives if opt.letter == letter), None)
        if not target_option:
            raise ValueError("Alternativa no encontrada")

        if decision == "aceptar":
            target_option.review_status = "aceptado"
        elif decision == "descartar":
            target_option.review_status = "descartado"
        elif decision == "editar":
            target_option.review_status = "editado"
            if new_text is not None:
                target_option.text = new_text

        self.repository.save(resource)
        return resource

    def approve_resource(self, resource_id: str) -> LearningResourceDomain:
        resource = self.get_resource(resource_id)
        pending = [
            opt
            for opt in resource.alternatives
            if getattr(opt, "review_status", getattr(opt, "estado", "")) in ("pendiente", "pending")
        ]
        if pending:
            raise ValueError("aprobacion_bloqueada: Existen alternativas pendientes")
        resource.review_status = "aprobado"
        self.repository.save(resource)
        return resource

    def generate_or_reset_resources(self) -> list[LearningResourceDomain]:
        return self.repository.reset_demo()


RecursoService = LearningResourceService