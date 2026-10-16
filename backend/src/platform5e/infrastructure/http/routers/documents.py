"""
API de ingesta y RAG: procesamiento de documentos, consulta de fragmentos y búsqueda en fuentes abiertas.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.materials.material_service import MaterialService
from platform5e.infrastructure.http.dependencies import extract_authorization_header


class TopicSearchInput(BaseModel):
    """Esquema para solicitar la búsqueda y creación de material a partir de un tema."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    unitId: str = Field(
        min_length=1,
        max_length=120,
        description="Identificador de la unidad temática que recibirá el material generado.",
        examples=["u2"],
    )
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    topic: str = Field(
        alias="tema",
        min_length=3,
        max_length=120,
        description="Tópico o concepto a consultar en fuentes académicas abiertas (ej. Wikipedia).",
        examples=["Arquitectura Hexagonal en Software"],
    )
    max_results: int = Field(
        alias="maximo",
        default=3,
        ge=1,
        le=5,
        description="Número máximo de artículos o secciones a extraer e indexar.",
    )


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
        status_code=status.HTTP_201_CREATED,
        summary="Buscar un tema en fuentes abiertas y guardarlo como material procesado",
        description=(
            "Consulta el tema especificado en fuentes abiertas autorizadas (Wikipedia), "
            "extrae el contenido relevante, lo limpia, lo fragmenta semánticamente y lo guarda "
            "directamente como material disponible para la unidad académica."
        ),
        responses={
            201: {"description": "Material temático extraído, fragmentado e indexado con éxito."},
            400: {"description": "No se encontraron resultados relevantes o parámetros inválidos."},
            401: {"description": "No autorizado."},
        },
    )
    def create_material_from_topic(
        request: TopicSearchInput,
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return material_service.create_from_topic(
            teacher_email, request.unitId, request.topic, request.max_results
        )

    @router.post(
        "/documentos/{document_id}/procesar",
        summary="Extraer el texto del documento y partirlo en fragmentos",
        description=(
            "Inicia el pipeline de extracción de texto y fragmentación semántica (chunking) "
            "sobre un documento previamente cargado por el docente, dejándolo listo para la búsqueda por similitud."
        ),
        responses={
            200: {"description": "Documento procesado correctamente. Retorna fragmentos generados."},
            404: {"description": "Documento no encontrado o no pertenece al docente."},
            401: {"description": "No autorizado."},
        },
    )
    def process_document(
        document_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> dict[str, Any]:
        return material_service.process_material(teacher_email, document_id)

    @router.get(
        "/documentos/{document_id}/fragmentos",
        summary="Ver los fragmentos de un documento procesado",
        description=(
            "Recupera la lista ordenada de fragmentos semánticos (chunks) indexados para el documento especificado, "
            "permitiendo al docente verificar el contenido textual que utilizará la IA como evidencia RAG."
        ),
        responses={
            200: {"description": "Listado de fragmentos recuperado con su orden y texto."},
            404: {"description": "Documento no encontrado o aún sin procesar."},
            401: {"description": "No autorizado."},
        },
    )
    def get_document_chunks(
        document_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> list[dict[str, Any]]:
        return material_service.get_document_chunks(teacher_email, document_id)

    @router.get(
        "/ia",
        summary="Obtener metadatos del generador activo (IA o reglas)",
        description=(
            "Consulta la configuración activa del motor de generación didáctica: "
            "indica si está operando mediante un modelo LLM (Gemini) o por el motor determinístico de reglas, "
            "así como los parámetros del modelo en ejecución."
        ),
        responses={
            200: {"description": "Metadatos informativos del proveedor activo de generación."},
        },
    )
    def get_generator_info() -> dict[str, Any]:
        return active_generator_info

    return router