"""
API EP-002 y HU-001: gestión de cuentas de docentes, sesiones, cursos y documentos base.
"""

from __future__ import annotations

import json
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from platform5e.application.services.accounts.account_service import (
    MAX_FILE_SIZE,
    AccountService,
)
from platform5e.domain.accounts.teacher_account import AccountConfigurationError
from platform5e.infrastructure.http.dependencies import extract_authorization_header


class BaseContract(BaseModel):
    """Contrato base que prohíbe atributos adicionales y limpia espacios superfluos."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginRequest(BaseContract):
    """Esquema de entrada para el inicio de sesión del docente."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)
    # La contraseña conserva los espacios exactos
    model_config = ConfigDict(extra="forbid")


class RegistrationRequest(BaseContract):
    """Esquema de entrada para el registro de una nueva cuenta docente."""

    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=200)
    model_config = ConfigDict(extra="forbid")


class LearningOutcomeInput(BaseContract):
    """Esquema para definir o editar un resultado de aprendizaje en la unidad."""

    id: str | None = None
    code: str | None = Field(default=None, max_length=20)
    text: str = Field(min_length=1, max_length=400)


class CourseUnitInput(BaseContract):
    """Esquema para la configuración de una unidad académica."""

    id: str | None = None
    title: str = Field(min_length=1, max_length=150)
    outcomes: list[LearningOutcomeInput] | None = Field(default=None, max_length=20)


class CourseInput(BaseContract):
    """Esquema de entrada para la creación o actualización de un curso."""

    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=150)
    term: str = Field(min_length=1, max_length=30)
    sumilla: str | None = Field(default=None, max_length=3000)
    logro: str | None = Field(default=None, max_length=1000)
    units: list[CourseUnitInput] = Field(min_length=1, max_length=50)


class DocumentContextInput(BaseContract):
    """Metadatos pedagógicos asociados a la carga de un documento de estudio."""

    unitId: str
    outcomeIds: list[str] = Field(default_factory=list, max_length=50)
    documentType: str
    suggestedStage: (
        Literal["engage", "explore", "explain", "elaborate", "evaluate"] | None
    ) = None
    usePermission: bool


def create_accounts_router(account_service: AccountService) -> APIRouter:
    """Construye y configura el enrutador HTTP para la administración de cuentas y cursos."""
    router = APIRouter(prefix="/api/v1", tags=["Cuentas, cursos y documentos"])

    def get_current_teacher(
        authorization: str | None = Depends(extract_authorization_header),
    ) -> str:
        return account_service.authenticate_token(authorization)

    @router.post(
        "/cuentas",
        status_code=201,
        summary="Crear una cuenta de docente e iniciar sesión",
    )
    def register_account(request: RegistrationRequest) -> dict[str, Any]:
        return account_service.register_account(
            request.name, request.email, request.password
        )

    @router.post("/sesiones", summary="Iniciar sesión con correo y contraseña")
    def login(request: LoginRequest) -> dict[str, Any]:
        return account_service.login(request.email, request.password)

    @router.get("/sesiones/actual", summary="Obtener el perfil de la sesión actual")
    def get_current_profile(
        teacher_email: str = Depends(get_current_teacher),
    ) -> dict[str, Any]:
        return account_service.get_profile(teacher_email)

    @router.delete(
        "/sesiones/actual", status_code=204, summary="Cerrar la sesión activa"
    )
    def logout(
        authorization: str | None = Depends(extract_authorization_header),
    ) -> Response:
        account_service.logout(authorization)
        return Response(status_code=204)

    @router.get(
        "/cursos", summary="Listar todos los cursos pertenecientes al docente"
    )
    def list_courses(
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return account_service.list_courses(teacher_email)

    @router.post(
        "/cursos", status_code=201, summary="Registrar un nuevo curso curricular"
    )
    def create_course(
        request: CourseInput, teacher_email: str = Depends(get_current_teacher)
    ) -> dict[str, Any]:
        return account_service.save_course(teacher_email, request.model_dump())

    @router.put("/cursos/{course_id}", summary="Actualizar los datos de un curso")
    def update_course(
        course_id: str,
        request: CourseInput,
        teacher_email: str = Depends(get_current_teacher),
    ) -> dict[str, Any]:
        return account_service.save_course(
            teacher_email, request.model_dump(), course_id
        )

    @router.delete(
        "/cursos/{course_id}",
        status_code=204,
        summary="Borrar un curso con su material, recursos y descargas",
    )
    def delete_course(
        course_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> Response:
        account_service.delete_course(teacher_email, course_id)
        return Response(status_code=204)

    @router.get(
        "/documentos", summary="Listar los documentos subidos por el docente"
    )
    def list_documents(
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return account_service.list_documents(teacher_email)

    @router.post(
        "/documentos",
        status_code=201,
        summary="Cargar un nuevo archivo binario de referencia",
    )
    async def upload_document(
        file: UploadFile = File(...),
        contexto: str = Form(...),
        teacher_email: str = Depends(get_current_teacher),
    ) -> dict[str, Any]:
        try:
            try:
                parsed_context = DocumentContextInput.model_validate(
                    json.loads(contexto)
                ).model_dump()
            except (ValueError, TypeError):
                raise AccountConfigurationError(
                    "CONTEXTO_INVALIDO", "Revisa los datos del documento.", 422
                )
            content_bytes = await file.read(MAX_FILE_SIZE + 1)
            filename_str = file.filename or "archivo_adjunto"
            return account_service.register_document(
                teacher_email, filename_str, content_bytes, parsed_context
            )
        finally:
            await file.close()

    @router.get(
        "/documentos/{document_id}/archivo",
        summary="Descargar el binario del documento de estudio",
    )
    def download_document(
        document_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> Response:
        metadata, binary_content = account_service.get_document(
            teacher_email, document_id
        )
        content_types = {
            "txt": "text/plain; charset=utf-8",
            "pdf": "application/pdf",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }
        media_type = content_types.get(
            metadata["kind"], "application/octet-stream"
        )
        encoded_filename = quote(metadata["fileName"], safe="")
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
        return Response(
            binary_content, media_type=media_type, headers=headers
        )

    @router.delete(
        "/documentos/{document_id}",
        status_code=204,
        summary="Eliminar un documento del repositorio",
    )
    def delete_document(
        document_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> Response:
        account_service.delete_document(teacher_email, document_id)
        return Response(status_code=204)

    @router.get(
        "/solicitudes",
        summary="Obtener el historial de solicitudes de generación",
    )
    def list_generation_requests(
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return account_service.list_generation_requests(teacher_email)

    return router