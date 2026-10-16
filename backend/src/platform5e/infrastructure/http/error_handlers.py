"""
Manejadores estandarizados de excepciones HTTP (C02 de EN-006).
Traduce excepciones de negocio y de validación a respuestas JSON uniformes.
"""

from __future__ import annotations


from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from platform5e.domain.accounts.teacher_account import AccountConfigurationError
from platform5e.domain.generation.errors import GenerationError
from platform5e.domain.materials.chunking import MaterialError
from platform5e.domain.shared.errors import (
    DuplicateRecordError,
    EntityNotFoundError,
    PersistenceUnavailableError,
)


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Maneja errores de validación estándar de Python."""
    return JSONResponse(
        status_code=400,
        content={
            "error": {"codigo": "ERROR_VALIDACION", "mensaje": str(exc)},
            "detail": str(exc),
        },
    )


async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Maneja fallos de esquema y validación de parámetros de FastAPI/Pydantic."""
    details = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "codigo": "PARAMETROS_INVALIDOS",
                "mensaje": "La API rechazó los parámetros. Revisa la unidad, etapa, tipo, cantidad y contexto.",
            },
            "detail": details,
        },
    )


async def resource_not_found_handler(request: Request, exc: EntityNotFoundError) -> JSONResponse:
    """Maneja entidades no encontradas en el dominio."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {"codigo": "RECURSO_NO_ENCONTRADO", "mensaje": str(exc)},
            "detail": str(exc),
        },
    )


async def configuration_error_handler(
    request: Request, exc: AccountConfigurationError | MaterialError | GenerationError
) -> JSONResponse:
    """Maneja errores tipados de dominio de configuración docente, materiales y generación."""
    status_code = getattr(exc, "status_code", 400)
    error_code = getattr(exc, "code", "ERROR_CONFIGURACION")
    error_message = getattr(exc, "message", str(exc))
    return JSONResponse(
        status_code=status_code,
        content={"error": {"codigo": error_code, "mensaje": error_message}},
    )


async def conflict_error_handler(request: Request, exc: DuplicateRecordError) -> JSONResponse:
    """Maneja colisiones por registros duplicados o claves únicas en la persistencia."""
    return JSONResponse(
        status_code=409,
        content={"error": {"codigo": "REGISTRO_DUPLICADO", "mensaje": str(exc)}},
    )


async def persistence_unavailable_handler(
    request: Request, exc: PersistenceUnavailableError
) -> JSONResponse:
    """Maneja caídas de conectividad o indisponibilidad en la base de datos."""
    return JSONResponse(
        status_code=503,
        content={"error": {"codigo": "PERSISTENCIA_NO_DISPONIBLE", "mensaje": str(exc)}},
    )