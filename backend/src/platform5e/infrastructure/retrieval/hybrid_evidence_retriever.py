"""
HU-011: Adaptador de recuperación híbrida (BM25 léxico + pgvector HNSW semántico) con fusión RRF (k=60).
Filtra por unidad temática antes de buscar y degrada limpiamente a BM25 si no hay soporte vectorial.
"""

from __future__ import annotations

from typing import Any

from platform5e.application.ports.outbound.chunk_repository_port import ChunkRepositoryPort
from platform5e.application.ports.outbound.embedding_port import (
    ChunkEmbeddingRepositoryPort,
    EmbeddingGeneratorPort,
)
from platform5e.domain.materials.text_analysis import retrieve_relevant_chunks


class HybridEvidenceRetriever:
    """Recuperador híbrido que combina coincidencia léxica (BM25) y similitud semántica (HNSW)."""

    description = "búsqueda híbrida (BM25 + pgvector HNSW)"

    def __init__(
        self,
        chunk_repository: ChunkRepositoryPort | ChunkEmbeddingRepositoryPort,
        embedding_generator: EmbeddingGeneratorPort | None = None,
        rrf_k: int = 60,
    ) -> None:
        self._chunk_repository = chunk_repository
        self._embedding_generator = embedding_generator
        self._rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        chunks: list[dict[str, Any]] | None = None,
        top_k: int = 5,
        unit_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Recupera fragmentos aplicando RRF sobre los rankings de BM25 y búsqueda vectorial."""
        # 1. Resolver fragmentos base para BM25 filtrados por unidad (C01)
        target_chunks = list(chunks) if chunks is not None else []
        if not target_chunks and unit_id and hasattr(self._chunk_repository, "get_chunks_by_unit"):
            target_chunks = self._chunk_repository.get_chunks_by_unit("", unit_id)

        if unit_id and target_chunks:
            target_chunks = [
                c for c in target_chunks if (c.get("unit_id") or c.get("unitId")) == unit_id
            ]

        # 2. Ranking Léxico (BM25)
        lexical_results = retrieve_relevant_chunks(query, target_chunks, top_k=max(top_k * 2, 20))

        # 3. Ranking Semántico (pgvector HNSW filtrado por unit_id)
        semantic_results: list[dict[str, Any]] = []
        if (
            self._embedding_generator is not None
            and hasattr(self._chunk_repository, "vector_store_available")
            and self._chunk_repository.vector_store_available()
            and hasattr(self._chunk_repository, "search_similar_chunks")
        ):
            try:
                query_vector = self._embedding_generator.embed_query(query)
                if query_vector:
                    semantic_results = self._chunk_repository.search_similar_chunks(
                        vector=query_vector,
                        limit=max(top_k * 2, 20),
                        unit_id=unit_id,
                    )
            except Exception:
                semantic_results = []

        # Si no hubo resultados vectoriales disponibles, degradación directa a BM25
        if not semantic_results:
            return lexical_results[:top_k]

        # 4. Fusión mediante Reciprocal Rank Fusion (RRF k=60)
        scores: dict[str, float] = {}
        chunk_map: dict[str, dict[str, Any]] = {}

        for rank, chunk in enumerate(lexical_results):
            cid = str(chunk["id"])
            chunk_map[cid] = chunk
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (self._rrf_k + rank + 1))

        for rank, chunk in enumerate(semantic_results):
            cid = str(chunk["id"])
            if cid not in chunk_map:
                chunk_map[cid] = {
                    "id": chunk["id"],
                    "documentId": chunk.get("documentId") or chunk.get("documento"),
                    "location": chunk.get("location") or chunk.get("ubicacion"),
                    "text": chunk.get("text") or chunk.get("texto"),
                    "unitId": unit_id,
                }
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (self._rrf_k + rank + 1))

        # 5. Ordenar por score RRF acumulado descendente y normalizar llaves de salida (C02)
        sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

        results: list[dict[str, Any]] = []
        for cid in sorted_ids[:top_k]:
            item = dict(chunk_map[cid])
            item["relevance"] = round(scores[cid], 5)
            results.append(item)

        return results