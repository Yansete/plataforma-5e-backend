"""
Puertos de la ingesta de material: leer archivos, guardar fragmentos y buscar fuentes abiertas.
"""

from __future__ import annotations

from typing import Any, Protocol


class TextExtractorPort(Protocol):
    """Puerto para la extracción de texto sin formato a partir de documentos binarios."""

    def extract(self, file_type: str, content: bytes) -> list[tuple[str, str]]:
        """Devuelve [(ubicación, texto)]: una entrada por página, diapositiva o sección."""
        ...


class ChunkRepositoryPort(Protocol):
    """Puerto para la persistencia y consulta de fragmentos de material educativo."""

    def replace_chunks(
        self, teacher_id: str, document_id: str, unit_id: str, chunks: list[dict[str, Any]]
    ) -> None:
        """Reemplaza los fragmentos asociados a un documento y unidad."""
        ...

    def get_chunks_by_document(self, teacher_id: str, document_id: str) -> list[dict[str, Any]]:
        """Obtiene todos los fragmentos asociados a un documento."""
        ...

    def get_chunks_by_unit(self, teacher_id: str, unit_id: str) -> list[dict[str, Any]]:
        """Obtiene todos los fragmentos asociados a una unidad pedagógica."""
        ...

    def update_document(self, teacher_id: str, document_data: dict[str, Any]) -> None:
        """Actualiza los metadatos o estado de un documento educativo."""
        ...


class OpenEducationalResourcePort(Protocol):
    """Puerto para la consulta de recursos y fuentes abiertas externas."""

    def search(self, topic: str, limit: int) -> list[dict[str, Any]]:
        """Devuelve [{'titulo', 'url', 'texto', 'licencia', 'fuente'}] sobre el tema solicitado."""
        ...