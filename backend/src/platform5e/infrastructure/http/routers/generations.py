"""
Contrato HTTP HU-053 / EN-006: orquestación de generación RAG o catálogo demo.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.generation.generation_service import GenerationService
from platform5e.domain.generation.errors import GenerationError
from platform5e.domain.shared.errors import PersistenceUnavailableError
from platform5e.infrastructure.http.dependencies import extract_authorization_header
from platform5e.infrastructure.http.schemas.generation_request import GenerationRequestModel


class IntegratedGenerationRequest(GenerationRequestModel):
    """Solicitud unificada que extiende el esquema de entrada con parámetros pedagógicos complementarios."""

    model_config = ConfigDict(extra="forbid")
    publico_objetivo: str = Field(default="", max_length=200)
    competencia: str = Field(default="", max_length=200)
    modalidades: list[Literal["Textual", "Gamificado", "Multimedia", "Kinestésico"]] = (
        Field(default_factory=list, max_length=4)
    )

    def to_domain_payload(self) -> dict[str, Any]:
        """Transforma el esquema HTTP al diccionario esperado por los servicios de generación."""
        return {
            "unitId": self.unit_id,
            "outcomeId": self.learning_outcome_id,
            "stage": self.stage_5e,
            "resourceType": self.resource_type,
            "quantity": self.quantity,
            "difficulty": self.difficulty,
            "optionCount": self.options_count,
            "topK": self.top_k,
            "evidenceThreshold": self.evidence_threshold,
            "instructions": self.instructions or "",
            "audience": self.publico_objetivo,
            "competency": self.competencia,
            "modalities": self.modalidades,
        }


class GenerationResponseSchema(BaseModel):
    """Estructura de respuesta HTTP para los recursos generados."""

    mode: Literal["api_demo", "rag"]
    notice: str
    generator: dict[str, Any] | None = None
    request: dict[str, Any]
    resources: list[dict[str, Any]]
    available: int
    fragments: list[dict[str, Any]]
    documents: list[dict[str, Any]]


def create_generations_router(
    generation_service: GenerationService,
    account_service: AccountService | None = None,
) -> APIRouter:
    """Construye el router HTTP para solicitudes y consulta de generaciones 5E."""
    router = APIRouter(
        prefix="/api/v1/generaciones", tags=["EP-003 Generación de recursos"]
    )

    @router.post("", response_model=GenerationResponseSchema)
    def generate_resources(
        request: IntegratedGenerationRequest,
        authorization: str | None = Depends(extract_authorization_header),
    ) -> Any:
        try:
            teacher_email = (
                account_service.authenticate_token(authorization)
                if authorization and account_service
                else None
            )
            if teacher_email and account_service:
                account_service.get_unit(teacher_email, request.unit_id)
            return generation_service.generate(
                request.to_domain_payload(), teacher_email
            )
        except GenerationError as exc:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "codigo": getattr(exc, "code", getattr(exc, "codigo", "ERROR_GENERACION")),
                        "mensaje": getattr(exc, "message", getattr(exc, "mensaje", str(exc))),
                    }
                },
            )
        except PersistenceUnavailableError:
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "codigo": "PERSISTENCIA_NO_DISPONIBLE",
                        "mensaje": "No se pudo guardar la solicitud. Comprueba la conexión de la base de datos.",
                    }
                },
            )

    @router.get("/{generation_id}", response_model=GenerationResponseSchema)
    def get_generation_by_id(
        generation_id: str,
        authorization: str | None = Depends(extract_authorization_header),
    ) -> Any:
        try:
            if account_service:
                account_service.verify_generation_ownership(
                    generation_id, authorization
                )
            return generation_service.get_by_id(generation_id)
        except GenerationError as exc:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "codigo": getattr(exc, "code", getattr(exc, "codigo", "GENERACION_NO_ENCONTRADA")),
                        "mensaje": getattr(exc, "message", getattr(exc, "mensaje", str(exc))),
                    }
                },
            )

    return router