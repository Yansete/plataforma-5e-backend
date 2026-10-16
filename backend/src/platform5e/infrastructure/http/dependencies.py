"""
Declara el esquema HTTP Bearer en OpenAPI para que Swagger transmita la cabecera Authorization.
"""

from __future__ import annotations

from fastapi import Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

teacher_security_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="TeacherSession",
    description="Obtén el token con POST /api/v1/sesiones. En Authorize pega únicamente el token, sin el prefijo Bearer.",
)


def extract_authorization_header(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(teacher_security_scheme),
) -> str | None:
    """Extrae el encabezado Authorization de la solicitud HTTP.

    Conserva también encabezados malformados para que sean rechazados formalmente en el servicio.
    auto_error=False permite la compatibilidad con solicitudes anónimas de demostración.
    """
    return request.headers.get("Authorization")