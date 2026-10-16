"""
Persistencia de recursos revisados e historial de descargas por unidad (HU-010).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from platform5e.application.ports.outbound.resource_repository_port import (
    LearningResourceRepositoryPort,
    ResourceReviewRepositoryPort,
)
from platform5e.domain.review.learning_resource import (
    AlternativeDomain,
    LearningResourceDomain,
)
from platform5e.infrastructure.persistence.database import SessionLocal
from platform5e.infrastructure.persistence.error_translation import translate_persistence_errors
from platform5e.infrastructure.persistence.repositories.sqlalchemy_account_repository import (
    DownloadORM,
    TeacherResourceORM,
)


class SQLAlchemyResourceRepository(ResourceReviewRepositoryPort, LearningResourceRepositoryPort):
    """Adaptador SQLAlchemy para revisión de recursos generados, descargas y persistencia individual."""

    @translate_persistence_errors
    def get_resources_by_unit(self, teacher_id: str, unit_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            statement = (
                select(TeacherResourceORM)
                .where(
                    TeacherResourceORM.teacher_id == teacher_id,
                    TeacherResourceORM.unit_id == unit_id,
                )
                .order_by(TeacherResourceORM.created_at.desc())
            )
            return [entity.resource_data for entity in session.scalars(statement)]

    @translate_persistence_errors
    def get_resource_by_id(self, teacher_id: str, resource_id: str) -> dict[str, Any] | None:
        with SessionLocal() as session:
            entity = session.get(TeacherResourceORM, resource_id)
            return entity.resource_data if entity and entity.teacher_id == teacher_id else None

    @translate_persistence_errors
    def save_resources(
        self, teacher_id: str, unit_id: str, resources: list[dict[str, Any]]
    ) -> None:
        with SessionLocal() as session:
            for res in resources:
                session.merge(
                    TeacherResourceORM(
                        id=res["id"],
                        teacher_id=teacher_id,
                        unit_id=unit_id,
                        created_at=res.get("createdAt", ""),
                        resource_data=res,
                    )
                )
            session.commit()

    @translate_persistence_errors
    def delete_resource(self, teacher_id: str, resource_id: str) -> None:
        with SessionLocal() as session:
            session.execute(
                delete(TeacherResourceORM).where(
                    TeacherResourceORM.id == resource_id,
                    TeacherResourceORM.teacher_id == teacher_id,
                )
            )
            session.commit()

    @translate_persistence_errors
    def get_downloads(self, teacher_id: str, unit_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            statement = (
                select(DownloadORM)
                .where(DownloadORM.teacher_id == teacher_id, DownloadORM.unit_id == unit_id)
                .order_by(DownloadORM.created_at.desc())
            )
            return [entity.download_data for entity in session.scalars(statement)]

    @translate_persistence_errors
    def save_download(
        self, teacher_id: str, unit_id: str, download_record: dict[str, Any]
    ) -> None:
        with SessionLocal() as session:
            session.add(
                DownloadORM(
                    id=download_record["id"],
                    teacher_id=teacher_id,
                    unit_id=unit_id,
                    created_at=download_record.get("createdAt", ""),
                    download_data=download_record,
                )
            )
            session.commit()

    @translate_persistence_errors
    def delete_downloads(self, teacher_id: str, unit_id: str) -> None:
        with SessionLocal() as session:
            session.execute(
                delete(DownloadORM).where(
                    DownloadORM.teacher_id == teacher_id, DownloadORM.unit_id == unit_id
                )
            )
            session.commit()

    # -----------------------------------------------------------------------
    # Métodos del contrato LearningResourceRepositoryPort (entidades individuales)
    # -----------------------------------------------------------------------
    @translate_persistence_errors
    def save(self, resource: LearningResourceDomain) -> LearningResourceDomain:
        """Guarda una entidad LearningResourceDomain serializándola en la tabla TeacherResourceORM."""
        with SessionLocal() as session:
            options_payload = [
                {
                    "letter": opt.letter,
                    "text": opt.text,
                    "is_correct": opt.is_correct,
                    "justification": opt.justification,
                    "review_status": opt.review_status,
                    "citations": opt.citations,
                    "source_chunks": opt.source_chunks,
                }
                for opt in resource.alternatives
            ]
            serialized_payload = {
                "id": resource.id,
                "title": resource.title,
                "prompt": resource.prompt,
                "feedback": resource.feedback,
                "alternatives": options_payload,
                "review_status": resource.review_status,
                "citations": resource.citations,
            }

            session.merge(
                TeacherResourceORM(
                    id=resource.id,
                    teacher_id="integration-test",
                    unit_id="unit-integration",
                    created_at="",
                    resource_data=serialized_payload,
                )
            )
            session.commit()
        return resource

    @translate_persistence_errors
    def get_by_id(self, resource_id: str) -> LearningResourceDomain | None:
        """Obtiene un recurso por ID y lo deserializa hacia LearningResourceDomain."""
        with SessionLocal() as session:
            entity = session.get(TeacherResourceORM, resource_id)
            if not entity:
                return None

            data = entity.resource_data
            options = [
                AlternativeDomain(
                    letter=opt["letter"],
                    text=opt["text"],
                    is_correct=opt["is_correct"],
                    justification=opt.get("justification", ""),
                    review_status=opt.get("review_status", "pendiente"),
                    citations=opt.get("citations", []),
                    source_chunks=opt.get("source_chunks", []),
                )
                for opt in data.get("alternatives", [])
            ]

            return LearningResourceDomain(
                id=data["id"],
                title=data["title"],
                prompt=data["prompt"],
                feedback=data.get("feedback", ""),
                alternatives=options,
                review_status=data.get("review_status", "borrador"),
                citations=data.get("citations", []),
            )

    @translate_persistence_errors
    def get_all(self) -> list[LearningResourceDomain]:
        """Obtiene todos los recursos pedagógicos almacenados."""
        with SessionLocal() as session:
            statement = select(TeacherResourceORM)
            entities = session.scalars(statement).all()
            result: list[LearningResourceDomain] = []
            for entity in entities:
                data = entity.resource_data
                options = [
                    AlternativeDomain(
                        letter=opt["letter"],
                        text=opt["text"],
                        is_correct=opt["is_correct"],
                        justification=opt.get("justification", ""),
                        review_status=opt.get("review_status", "pendiente"),
                    )
                    for opt in data.get("alternatives", [])
                ]
                result.append(
                    LearningResourceDomain(
                        id=data["id"],
                        title=data["title"],
                        prompt=data["prompt"],
                        feedback=data.get("feedback", ""),
                        alternatives=options,
                        review_status=data.get("review_status", "borrador"),
                    )
                )
            return result

    def reset_demo(self) -> list[LearningResourceDomain]:
        return self.get_all()


# Alias en español para compatibilidad
SQLAlchemyRecursoRepository = SQLAlchemyResourceRepository