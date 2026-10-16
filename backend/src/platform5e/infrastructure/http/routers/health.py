"""
Endpoint de monitoreo y verificación de disponibilidad del servicio (Health Check).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter


def create_health_router() -> APIRouter:
    """Crea el router para la comprobación de salud de la API."""
    router = APIRouter()

    @router.get("/salud", summary="Verificar el estado activo de la API")
    def check_health() -> dict[str, Any]:
        return {"estado": "ok"}

    return router