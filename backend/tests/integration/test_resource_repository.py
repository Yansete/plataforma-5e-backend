"""
Prueba de integración para la persistencia real del repositorio de recursos en SQLAlchemy.
"""

from __future__ import annotations

from platform5e.domain.review.learning_resource import (
    AlternativeDomain,
    LearningResourceDomain,
)
from platform5e.infrastructure.persistence.repositories.sqlalchemy_resource_repository import (
    SQLAlchemyResourceRepository,
)


def test_guardar_y_recuperar_recurso_integration():
    """Valida la persistencia real a través del adaptador SQLAlchemy."""
    repo = SQLAlchemyResourceRepository()

    option = AlternativeDomain(
        letter="A",
        text="Respuesta de integración",
        is_correct=True,
        justification="Justificación válida",
    )
    resource = LearningResourceDomain(
        id="rec-int-001",
        title="Integración Repositorio",
        prompt="¿Persiste el modelo correctamente?",
        feedback="Verificado con éxito",
        alternatives=[option],
    )

    repo.save(resource)

    retrieved = repo.get_by_id("rec-int-001")

    assert retrieved is not None
    assert retrieved.id == "rec-int-001"
    assert len(retrieved.alternativas) == 1
    assert retrieved.alternativas[0].texto == "Respuesta de integración"