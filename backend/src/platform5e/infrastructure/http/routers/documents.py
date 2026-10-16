"""
API de ingesta y RAG: procesamiento de documentos, consulta de fragmentos y búsqueda en fuentes abiertas.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.materials.material_service import MaterialService
from platform5e.infrastructure.http.dependencies import extract_authorization_header


class TopicSearchInput(BaseModel):
    """Esquema para solicitar la búsqueda y creación de material a partir de un tema."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    unitId: str = Field(min_length=1, max_length=120)
    tema: str = Field(min_length=3, max_length=120)
    maximo: int = Field(default=3, ge=1, le=5)


def create_materials_router(
    material_service: MaterialService,
    account_service: AccountService,
    active_generator_info: dict[str, Any],
) -> APIRouter:
    """Construye el router HTTP para la ingesta y consulta de fragmentos de material."""
    router = APIRouter(prefix="/api/v1", tags=["Ingesta y RAG"])

    def get_current_teacher(
        authorization: str | None = Depends(extract_authorization_header),
    ) -> str:
        return account_service.authenticate_token(authorization)

    @router.post(
        "/documentos/desde-tema",
        status_code=201,
        summary="Buscar un tema en fuentes abiertas y guardarlo como material procesado",
    )
    def create_material_from_topic(
        request: TopicSearchInput,
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return material_service.create_from_topic(
            teacher_email, request.unitId, request.tema, request.maximo
        )

    @router.post(
        "/documentos/{document_id}/procesar",
        summary="Extraer el texto del documento y partirlo en fragmentos",
    )
    def process_document(
        document_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> dict[str, Any]:
        return material_service.process_material(teacher_email, document_id)

    @router.get(
        "/documentos/{document_id}/fragmentos",
        summary="Ver los fragmentos de un documento procesado",
    )
    def get_document_chunks(
        document_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> list[dict[str, Any]]:
        return material_service.get_document_chunks(teacher_email, document_id)

    @router.get("/ia", summary="Obtener metadatos del generador activo (IA o reglas)")
    def get_generator_info() -> dict[str, Any]:
        return active_generator_info

    return router