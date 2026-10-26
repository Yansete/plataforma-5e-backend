"""
Adaptador HTTP del historial de descargas de cada unidad
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.review.resource_review_service import ResourceReviewService
from platform5e.application.use_cases.export.export_unit_resources import ExportUnitResourcesUseCase
from platform5e.domain.accounts.teacher_account import AccountConfigurationError
from platform5e.infrastructure.http.dependencies import current_teacher_dependency
from platform5e.infrastructure.http.schemas.common import error_responses
from platform5e.infrastructure.http.schemas.downloads import DownloadInput, DownloadResponse


def create_downloads_router(
    review_service: ResourceReviewService,
    account_service: AccountService,
    export_use_case: ExportUnitResourcesUseCase | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/units/{unit_id}/downloads", tags=["downloads"])
    current_teacher = current_teacher_dependency(account_service)

    @router.get("", response_model=list[DownloadResponse], summary="List the downloads of a unit", responses=error_responses(401, 404))
    def list_downloads(unit_id: str, teacher_id: str = Depends(current_teacher)) -> list[dict[str, Any]]:
        """The last 50 downloads, newest first."""
        return review_service.get_downloads_history(teacher_id, unit_id)

    @router.get(
        "/{download_id}",
        summary="Re-download an exported package",
        response_class=Response,
        responses={
            200: {
                "content": {"application/zip": {}, "application/xml": {}, "text/html": {}},
                "description": "The re-downloaded file; its name comes in Content-Disposition.",
            },
            **error_responses(401, 404, 422),
        },
    )
    def redownload_package(
        unit_id: str,
        download_id: str,
        teacher_id: str = Depends(current_teacher),
    ) -> Response:
        """Re-downloads an exported package recorded in the unit's download history (HU-010 C02)."""
        if export_use_case is None:
            raise AccountConfigurationError("SERVICE_UNAVAILABLE", "Export service not configured.", 500)

        record = review_service.get_download_record(teacher_id, unit_id, download_id)
        exported = export_use_case.execute(teacher_id, unit_id, record["format"])
        return Response(
            exported.content,
            media_type=exported.media_type,
            headers={"Content-Disposition": f'attachment; filename="{exported.file_name}"'},
        )

    @router.post(
        "",
        status_code=status.HTTP_201_CREATED,
        response_model=DownloadResponse,
        summary="Record a download",
        responses=error_responses(401, 404, 422),
    )
    def register_download(unit_id: str, body: DownloadInput, teacher_id: str = Depends(current_teacher)) -> dict[str, Any]:
        """Records a file built in the browser (the unit document). Exports built by the backend record themselves."""
        return review_service.register_download(teacher_id, unit_id, body.model_dump(by_alias=True))

    @router.delete(
        "",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Clear the download history",
        responses=error_responses(401, 404),
    )
    def clear_downloads(unit_id: str, teacher_id: str = Depends(current_teacher)) -> Response:
        """Deletes the history of the unit. The files already downloaded are not affected."""
        review_service.clear_downloads_history(teacher_id, unit_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router