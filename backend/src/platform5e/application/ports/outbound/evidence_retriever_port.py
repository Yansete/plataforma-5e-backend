"""
Puerto de recuperación de evidencia (la «R» de RAG): elige los fragmentos del material que sustentan un pedido.

Hoy lo implementa la búsqueda por palabras BM25; la búsqueda por significado con vectores (pgvector, EN-013 y
HU-011) será otro adaptador del mismo puerto, sin tocar el servicio de generación.
"""

from __future__ import annotations

from typing import Any, Protocol


class EvidenceRetrieverPort(Protocol):
    """Contrato del buscador de evidencia dentro del material procesado de una unidad."""

    description: str

    def retrieve(self, query: str, chunks: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        """Devuelve hasta `top_k` fragmentos de `chunks`, del más al menos relacionado con `query`.

        Cada fragmento conserva sus llaves y agrega 'relevance', un valor entre 0 y 1.
        """
        ...
