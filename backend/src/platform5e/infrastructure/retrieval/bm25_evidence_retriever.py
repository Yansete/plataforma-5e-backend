"""
Adaptador del puerto EvidenceRetrieverPort con BM25, la búsqueda por palabras del dominio (text_analysis.py).
"""

from __future__ import annotations

from typing import Any

from platform5e.domain.materials.text_analysis import retrieve_relevant_chunks


class Bm25EvidenceRetriever:
    """Busca la evidencia por coincidencia de palabras: no necesita red, modelo ni base vectorial."""

    description = "búsqueda por palabras (BM25)"

    def retrieve(self, query: str, chunks: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        return retrieve_relevant_chunks(query, chunks, top_k)
