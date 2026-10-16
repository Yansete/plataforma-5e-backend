"""
Adaptador HTTP de cuentas y sesiones (HU-001): registro, inicio y cierre de sesión.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.infrastructure.http.dependencies import current_teacher_dependency, extract_authorization_header
from platform5e.infrastructure.http.schemas.accounts import (
    LoginRequest,
    ProfileResponse,
    RegistrationRequest,
    SessionResponse,
)
from platform5e.infrastructure.http.schemas.common import error_responses


def create_accounts_router(account_service: AccountService) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    current_teacher = current_teacher_dependency(account_service)

    @router.post(
        "/accounts",
        tags=["accounts"],
        status_code=status.HTTP_201_CREATED,
        response_model=SessionResponse,
        summary="Register a teacher account",
        responses=error_responses(400, 409, 422),
    )
    def register_account(body: RegistrationRequest) -> dict[str, Any]:
        """Creates the account (PBKDF2 password hash) and opens a session right away. 409 if the e-mail is taken."""
        return account_service.register_account(body.name, body.email, body.password)

    @router.post(
        "/sessions",
        tags=["sessions"],
        response_model=SessionResponse,
        summary="Sign in",
        responses=error_responses(401, 422),
    )
    def login(body: LoginRequest) -> dict[str, Any]:
        """Checks e-mail and password and returns a bearer token valid for 8 hours."""
        return account_service.login(body.email, body.password)

    @router.get(
        "/sessions/current",
        tags=["sessions"],
        response_model=ProfileResponse,
        summary="Get the signed-in teacher",
        responses=error_responses(401),
    )
    def get_current_session(teacher_id: str = Depends(current_teacher)) -> dict[str, Any]:
        """Returns the e-mail and name of the teacher who owns the token."""
        return account_service.get_profile(teacher_id)

    @router.delete(
        "/sessions/current",
        tags=["sessions"],
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Sign out",
        responses=error_responses(401),
    )
    def logout(authorization: str | None = Depends(extract_authorization_header)) -> Response:
        """Revokes the token: later requests with it get 401."""
        account_service.logout(authorization)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
