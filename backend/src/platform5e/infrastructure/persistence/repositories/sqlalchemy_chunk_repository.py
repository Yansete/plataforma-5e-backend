"""
Fragmentos del material y estado de procesamiento de los documentos (EN-012).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select

from platform5e.application.ports.outbound.chunk_repository_port import ChunkRepositoryPort
from platform5e.infrastructure.persistence.database import SessionLocal
from platform5e.infrastructure.persistence.error_translation import translate_persistence_errors
from platform5e.infrastructure.persistence.repositories.sqlalchemy_account_repository import (
    ChunkORM,
    DocumentORM,
)


def _serialize_chunk_entity(entity: ChunkORM) -> dict[str, Any]:
    """Convierte la entidad ORM Chunk a diccionario canónico con compatibilidad dual."""
    return {
        "id": entity.id,
        "document_id": entity.document_id,
        "documentId": entity.document_id,
        "documento_id": entity.document_id,
        "unit_id": entity.unit_id,
        "unitId": entity.unit_id,
        "order": entity.order_index,
        "orden": entity.order_index,
        "location": entity.location,
        "ubicacion": entity.location,
        "text": entity.text_content,
        "texto": entity.text_content,
    }


class SQLAlchemyChunkRepository(ChunkRepositoryPort):
    """Adaptador de infraestructura para almacenamiento de fragmentos de texto."""

    @translate_persistence_errors
    def replace_chunks(
        self, teacher_id: str, document_id: str, unit_id: str, chunks: list[dict[str, Any]]
    ) -> None:
        with SessionLocal() as session:
            session.execute(
                delete(ChunkORM).where(
                    ChunkORM.document_id == document_id, ChunkORM.teacher_id == teacher_id
                )
            )
            new_entities = [
                ChunkORM(
                    id=chunk["id"],
                    teacher_id=teacher_id,
                    document_id=document_id,
                    unit_id=unit_id,
                    order_index=chunk.get("order", chunk.get("orden", idx)),
                    location=chunk.get("location", chunk.get("ubicacion", "")),
                    text_content=chunk.get("text", chunk.get("texto", "")),
                )
                for idx, chunk in enumerate(chunks)
            ]
            session.add_all(new_entities)
            session.commit()

    @translate_persistence_errors
    def get_chunks_by_document(self, teacher_id: str, document_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            statement = (
                select(ChunkORM)
                .where(ChunkORM.teacher_id == teacher_id, ChunkORM.document_id == document_id)
                .order_by(ChunkORM.order_index)
            )
            return [_serialize_chunk_entity(entity) for entity in session.scalars(statement)]

    @translate_persistence_errors
    def get_chunks_by_unit(self, teacher_id: str, unit_id: str) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            statement = (
                select(ChunkORM)
                .where(ChunkORM.teacher_id == teacher_id, ChunkORM.unit_id == unit_id)
                .order_by(ChunkORM.document_id, ChunkORM.order_index)
            )
            return [_serialize_chunk_entity(entity) for entity in session.scalars(statement)]

    @translate_persistence_errors
    def update_document(self, teacher_id: str, document_data: dict[str, Any]) -> None:
        with SessionLocal() as session:
            doc = session.get(DocumentORM, document_data["id"])
            if doc and doc.teacher_id == teacher_id:
                doc.metadata_json = document_data
                session.commit()