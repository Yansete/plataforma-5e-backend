"""
API EP-002 y HU-001: gestión de cuentas de docentes, sesiones, cursos y documentos base.
"""

from __future__ import annotations

import json
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
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

    email: str = Field(
        min_length=3,
        max_length=254,
        description="Correo electrónico institucional o personal del docente.",
        examples=["docente@universidad.edu.pe"],
    )
    password: str = Field(
        min_length=1,
        max_length=200,
        description="Contraseña de acceso a la cuenta del docente.",
    )
    # La contraseña conserva los espacios exactos
    model_config = ConfigDict(extra="forbid")


class RegistrationRequest(BaseContract):
    """Esquema de entrada para el registro de una nueva cuenta docente."""

    name: str = Field(
        min_length=2,
        max_length=100,
        description="Nombre completo del docente para su perfil de cátedra.",
        examples=["Prof. Carlos Mendoza"],
    )
    email: str = Field(
        min_length=3,
        max_length=254,
        description="Dirección de correo electrónico válida para identificación única.",
        examples=["carlos.mendoza@universidad.edu.pe"],
    )
    password: str = Field(
        min_length=8,
        max_length=200,
        description="Contraseña segura con un mínimo de 8 caracteres.",
    )
    model_config = ConfigDict(extra="forbid")


class LearningOutcomeInput(BaseContract):
    """Esquema para definir o editar un resultado de aprendizaje en la unidad."""

    id: str | None = Field(
        default=None,
        description="Identificador único del resultado de aprendizaje si ya fue persistido.",
    )
    code: str | None = Field(
        default=None,
        max_length=20,
        description="Código curricular del resultado de aprendizaje (ej. RA-01).",
        examples=["RA-01"],
    )
    text: str = Field(
        min_length=1,
        max_length=400,
        description="Enunciado descriptivo de la competencia o habilidad a alcanzar.",
        examples=["Aplica principios de encapsulamiento y modularidad en el diseño."],
    )


class CourseUnitInput(BaseContract):
    """Esquema para la configuración de una unidad académica."""

    id: str | None = Field(
        default=None,
        description="Identificador único de la unidad temática (ej. u1, u2).",
    )
    title: str = Field(
        min_length=1,
        max_length=150,
        description="Título representativo de la unidad temática de aprendizaje.",
        examples=["Unidad 2: Arquitectura Hexagonal y Puertos"],
    )
    outcomes: list[LearningOutcomeInput] | None = Field(
        default=None,
        max_length=20,
        description="Lista de resultados de aprendizaje formalmente asociados a la unidad.",
    )


class CourseInput(BaseContract):
    """Esquema de entrada para la creación o actualización de un curso."""

    code: str = Field(
        min_length=1,
        max_length=30,
        description="Código identificador de la asignatura según el plan de estudios.",
        examples=["TI-501"],
    )
    name: str = Field(
        min_length=1,
        max_length=150,
        description="Denominación formal del curso académico.",
        examples=["Taller Integrador I"],
    )
    term: str = Field(
        min_length=1,
        max_length=30,
        description="Periodo o semestre académico de impartición.",
        examples=["2026-II"],
    )
    sumilla: str | None = Field(
        default=None,
        max_length=3000,
        description="Sumilla oficial del curso que resume propósitos y alcances.",
    )
    logro: str | None = Field(
        default=None,
        max_length=1000,
        description="Competencia o logro formativo general esperado de la asignatura.",
    )
    units: list[CourseUnitInput] = Field(
        min_length=1,
        max_length=50,
        description="Listado estructurado de unidades académicas que componen el curso.",
    )


class DocumentContextInput(BaseContract):
    """Metadatos pedagógicos asociados a la carga de un documento de estudio."""

    unitId: str = Field(
        description="Identificador de la unidad académica vinculada al material.",
        examples=["u2"],
    )
    outcomeIds: list[str] = Field(
        default_factory=list,
        max_length=50,
        description="Identificadores de los resultados de aprendizaje correlacionados.",
    )
    documentType: str = Field(
        description="Clasificación didáctica del material (ej. lectura, presentación, ejercicio).",
        examples=["lectura"],
    )
    suggestedStage: (
        Literal["engage", "explore", "explain", "elaborate", "evaluate"] | None
    ) = Field(
        default=None,
        description="Fase sugerida dentro del modelo pedagógico 5E para su aplicación.",
    )
    usePermission: bool = Field(
        description="Consentimiento docente para procesar e indexar el archivo con fines formativos.",
    )


def create_accounts_router(account_service: AccountService) -> APIRouter:
    """Construye y configura el enrutador HTTP para la administración de cuentas y cursos."""
    router = APIRouter(prefix="/api/v1", tags=["Cuentas, cursos y documentos"])

    def get_current_teacher(
        authorization: str | None = Depends(extract_authorization_header),
    ) -> str:
        return account_service.authenticate_token(authorization)

    @router.post(
        "/cuentas",
        status_code=status.HTTP_201_CREATED,
        summary="Crear una cuenta de docente e iniciar sesión",
        description=(
            "Registra un nuevo docente en la plataforma con credenciales únicas "
            "y retorna inmediatamente la sesión iniciada con su token de autenticación."
        ),
        responses={
            201: {"description": "Cuenta creada exitosamente con token y perfil retornado."},
            400: {"description": "Datos de registro inválidos o correo electrónico ya en uso."},
        },
    )
    def register_account(request: RegistrationRequest) -> dict[str, Any]:
        return account_service.register_account(
            request.name, request.email, request.password
        )

    @router.post(
        "/sesiones",
        summary="Iniciar sesión con correo y contraseña",
        description=(
            "Verifica las credenciales del docente y genera un token de autenticación Bearer "
            "necesario para interactuar con las rutas protegidas del sistema."
        ),
        responses={
            200: {"description": "Autenticación satisfactoria. Retorna token y datos del docente."},
            401: {"description": "Credenciales inválidas (correo o contraseña incorrectos)."},
        },
    )
    def login(request: LoginRequest) -> dict[str, Any]:
        return account_service.login(request.email, request.password)

    @router.get(
        "/sesiones/actual",
        summary="Obtener el perfil de la sesión actual",
        description=(
            "Recupera la información del docente activo descifrando el token provisto "
            "en el encabezado `Authorization: Bearer <token>`."
        ),
        responses={
            200: {"description": "Datos del perfil docente y estado de la sesión actual."},
            401: {"description": "Token inválido, expirado o ausente."},
        },
    )
    def get_current_profile(
        teacher_email: str = Depends(get_current_teacher),
    ) -> dict[str, Any]:
        return account_service.get_profile(teacher_email)

    @router.delete(
        "/sesiones/actual",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Cerrar la sesión activa",
        description=(
            "Revoca el token actual del docente invalidando futuros accesos con las mismas credenciales de sesión."
        ),
        responses={
            204: {"description": "Sesión revocada correctamente."},
            401: {"description": "No se proporcionó una sesión válida para revocar."},
        },
    )
    def logout(
        authorization: str | None = Depends(extract_authorization_header),
    ) -> Response:
        account_service.logout(authorization)
        return Response(status_code=204)

    @router.get(
        "/cursos",
        summary="Listar todos los cursos pertenecientes al docente",
        description=(
            "Obtiene el catálogo de asignaturas creadas por el docente autenticado, "
            "incluyendo sus unidades didácticas y resultados de aprendizaje configurados."
        ),
        responses={
            200: {"description": "Listado de cursos obtenido correctamente."},
            401: {"description": "No autorizado para consultar el catálogo de asignaturas."},
        },
    )
    def list_courses(
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return account_service.list_courses(teacher_email)

    @router.post(
        "/cursos",
        status_code=status.HTTP_201_CREATED,
        summary="Registrar un nuevo curso curricular",
        description=(
            "Crea una nueva asignatura en el sistema vinculada al perfil del docente, "
            "validando la estructura de unidades y resultados de aprendizaje mínimos."
        ),
        responses={
            201: {"description": "Curso curricular creado exitosamente."},
            400: {"description": "Estructura de curso incompleta o inválida."},
            401: {"description": "Sesión no válida o no autenticada."},
        },
    )
    def create_course(
        request: CourseInput, teacher_email: str = Depends(get_current_teacher)
    ) -> dict[str, Any]:
        return account_service.save_course(teacher_email, request.model_dump())

    @router.put(
        "/cursos/{course_id}",
        summary="Actualizar los datos de un curso",
        description=(
            "Modifica los metadatos, sumilla, competencias y unidades didácticas "
            "de un curso previamente registrado por el docente."
        ),
        responses={
            200: {"description": "Datos del curso actualizados correctamente."},
            404: {"description": "El curso solicitado no existe o pertenece a otro usuario."},
            401: {"description": "No autorizado."},
        },
    )
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
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Borrar un curso con su material, recursos y descargas",
        description=(
            "Elimina de forma irreversible una asignatura junto a todos los materiales cargados, "
            "recursos generados y registros de descargas vinculados."
        ),
        responses={
            204: {"description": "Curso y datos asociados eliminados satisfactoriamente."},
            404: {"description": "El curso no existe."},
            401: {"description": "No autorizado."},
        },
    )
    def delete_course(
        course_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> Response:
        account_service.delete_course(teacher_email, course_id)
        return Response(status_code=204)

    @router.get(
        "/documentos",
        summary="Listar los documentos subidos por el docente",
        description=(
            "Retorna todos los archivos didácticos subidos por el docente a través de sus cursos, "
            "indicando el estado del procesamiento y su unidad asociada."
        ),
        responses={
            200: {"description": "Listado de documentos recuperado correctamente."},
            401: {"description": "No autorizado."},
        },
    )
    def list_documents(
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return account_service.list_documents(teacher_email)

    @router.post(
        "/documentos",
        status_code=status.HTTP_201_CREATED,
        summary="Cargar un nuevo archivo binario de referencia",
        description=(
            "Recibe un archivo didáctico (PDF, DOCX, TXT o PPTX) junto con su contexto pedagógico serializado en JSON. "
            "Valida que el archivo no supere el tamaño límite institucional y lo asocia a la unidad docente."
        ),
        responses={
            201: {"description": "Archivo cargado y registrado en el repositorio docente."},
            413: {"description": "El archivo excede el tamaño máximo permitido."},
            422: {"description": "Contexto pedagógico no válido o con formato JSON corrupto."},
            401: {"description": "No autorizado."},
        },
    )
    async def upload_document(
        file: UploadFile = File(..., description="Archivo binario de cátedra a registrar."),
        contexto: str = Form(
            ...,
            description="Cadena JSON serializada con la estructura de DocumentContextInput.",
            examples=['{"unitId": "u2", "outcomeIds": [], "documentType": "lectura", "suggestedStage": "explore", "usePermission": true}'],
        ),
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
        description=(
            "Recupera el contenido binario original del documento cargado, "
            "adjuntando la cabecera `Content-Disposition` con su nombre codificado."
        ),
        responses={
            200: {"description": "Contenido binario transmitido con el Content-Type respectivo."},
            404: {"description": "Documento no encontrado o no pertenece al docente."},
            401: {"description": "No autorizado."},
        },
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
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Eliminar un documento del repositorio",
        description="Elimina de la base de datos el archivo didáctico y sus fragmentos semánticos indexados.",
        responses={
            204: {"description": "Documento eliminado correctamente."},
            404: {"description": "El documento no existe."},
            401: {"description": "No autorizado."},
        },
    )
    def delete_document(
        document_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> Response:
        account_service.delete_document(teacher_email, document_id)
        return Response(status_code=204)

    @router.get(
        "/solicitudes",
        summary="Obtener el historial de solicitudes de generación",
        description=(
            "Retorna el registro cronológico de peticiones de generación realizadas por el docente, "
            "incluyendo parámetros pedagógicos, fecha y estado de procesamiento."
        ),
        responses={
            200: {"description": "Historial de solicitudes obtenido satisfactoriamente."},
            401: {"description": "No autorizado."},
        },
    )
    def list_generation_requests(
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return account_service.list_generation_requests(teacher_email)

    return router