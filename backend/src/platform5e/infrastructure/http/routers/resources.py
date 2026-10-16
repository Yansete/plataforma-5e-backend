"""
API de revisión docente (HU-010) e historial de descargas por unidad didáctica.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.review.resource_review_service import ResourceReviewService
from platform5e.infrastructure.http.dependencies import extract_authorization_header

DiscardReasonType = Literal[
    "sin_sentido",
    "tambien_correcto",
    "duplicado",
    "fuera_de_unidad",
    "otro",
    "regenerado",
]


class BaseContract(BaseModel):
    """Contrato base restrictivo para esquemas de revisión."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReviewedOptionInput(BaseContract):
    """Esquema para una alternativa de respuesta revisada."""

    id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=600)
    feedback: str = Field(default="", max_length=600)
    decision: Literal["pendiente", "aceptado", "descartado"]
    discardReason: DiscardReasonType | None = None
    edited: bool = False


class ReviewedResourceInput(BaseContract):
    """Esquema para la actualización del estado y contenido de un recurso docente."""

    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=8000)
    status: Literal["pendiente", "aprobado", "descartado"]
    discardReason: DiscardReasonType | None = None
    edited: bool = False
    options: list[ReviewedOptionInput] | None = Field(default=None, max_length=10)


class DownloadRegistrationInput(BaseContract):
    """Esquema de entrada para registrar una descarga en el historial de la unidad."""

    format: Literal["moodle_xml", "scorm_zip", "documento"]
    fileName: str = Field(min_length=1, max_length=200)
    resourceCount: int = Field(ge=0, le=500)


def create_resources_router(
    review_service: ResourceReviewService,
    account_service: AccountService,
) -> APIRouter:
    """Construye el router HTTP para la revisión docente y descargas de recursos."""
    router = APIRouter(prefix="/api/v1", tags=["Revisión y descargas"])

    def get_current_teacher(
        authorization: str | None = Depends(extract_authorization_header),
    ) -> str:
        return account_service.authenticate_token(authorization)

    @router.get(
        "/resumen",
        summary="Obtener resumen de recursos aprobados y pendientes por unidad",
    )
    def get_review_summary(
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return review_service.get_summary(teacher_email)

    @router.get(
        "/unidades/{unit_id}/recursos",
        summary="Listar los recursos generados para una unidad con su estado de revisión",
    )
    def list_unit_resources(
        unit_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> list[dict[str, Any]]:
        return review_service.list_resources(teacher_email, unit_id)

    @router.put(
        "/unidades/{unit_id}/recursos/{resource_id}",
        summary="Guardar la revisión y decisiones sobre un recurso",
    )
    def update_resource_review(
        unit_id: str,
        resource_id: str,
        request: ReviewedResourceInput,
        teacher_email: str = Depends(get_current_teacher),
    ) -> dict[str, Any]:
        return review_service.update_resource(
            teacher_email, unit_id, resource_id, request.model_dump()
        )

    @router.delete(
        "/unidades/{unit_id}/recursos/{resource_id}",
        status_code=204,
        summary="Eliminar un recurso formativo",
    )
    def delete_resource(
        unit_id: str,
        resource_id: str,
        teacher_email: str = Depends(get_current_teacher),
    ) -> Response:
        review_service.delete_resource(teacher_email, unit_id, resource_id)
        return Response(status_code=204)

    @router.get(
        "/unidades/{unit_id}/descargas",
        summary="Obtener el historial de descargas de la unidad",
    )
    def get_downloads_history(
        unit_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> list[dict[str, Any]]:
        return review_service.get_downloads_history(teacher_email, unit_id)

    @router.post(
        "/unidades/{unit_id}/descargas",
        status_code=201,
        summary="Registrar un evento de descarga de recursos",
    )
    def register_download(
        unit_id: str,
        request: DownloadRegistrationInput,
        teacher_email: str = Depends(get_current_teacher),
    ) -> dict[str, Any]:
        return review_service.register_download(
            teacher_email, unit_id, request.model_dump()
        )

    @router.delete(
        "/unidades/{unit_id}/descargas",
        status_code=204,
        summary="Limpiar el historial de descargas de la unidad",
    )
    def clear_downloads_history(
        unit_id: str, teacher_email: str = Depends(get_current_teacher),
    ) -> Response:
        review_service.clear_downloads_history(teacher_email, unit_id)
        return Response(status_code=204)

    return router