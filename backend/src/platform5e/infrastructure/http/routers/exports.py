"""
Adaptador HTTP de la exportación en el backend: POST /api/v1/units/{unit_id}/exports devuelve el archivo.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.use_cases.export.export_unit_resources import ExportUnitResourcesUseCase
from platform5e.infrastructure.http.dependencies import extract_authorization_header


class ExportRequest(BaseModel):
    """Formato pedido y, si se quiere, solo algunos recursos aprobados."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    format: Literal["scorm_zip"] = Field(description="Export format. `scorm_zip`: SCORM 1.2 package for Chamilo.")
    resource_ids: list[str] = Field(
        default_factory=list,
        alias="resourceIds",
        max_length=500,
        description="Approved resources to export; empty exports every approved resource of the unit.",
    )


def create_exports_router(use_case: ExportUnitResourcesUseCase, account_service: AccountService) -> APIRouter:
    """Construye el router de exportación; la autenticación la resuelve el servicio de cuentas."""
    router = APIRouter(prefix="/api/v1/units", tags=["exports"])

    @router.post(
        "/{unit_id}/exports",
        summary="Export the approved resources of a unit",
        response_class=Response,
        responses={200: {"content": {"application/zip": {}}, "description": "The file to download."}},
    )
    def export_unit(
        unit_id: str,
        body: ExportRequest,
        authorization: str | None = Depends(extract_authorization_header),
    ) -> Response:
        """Builds the file in the backend from the approved resources, records the download and returns the file."""
        teacher_id = account_service.authenticate_token(authorization)
        exported = use_case.execute(teacher_id, unit_id, body.format, body.resource_ids)
        return Response(
            exported.content,
            media_type=exported.media_type,
            headers={"Content-Disposition": f'attachment; filename="{exported.file_name}"'},
        )

    return router
