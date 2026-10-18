"""
Adaptador HTTP de la revisión docente de los recursos generados (HU-010).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response, status

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.review.resource_review_service import ResourceReviewService
from platform5e.application.use_cases.media.get_resource_media import GetResourceMediaUseCase
from platform5e.infrastructure.http.dependencies import current_teacher_dependency
from platform5e.infrastructure.http.schemas.common import error_responses
from platform5e.infrastructure.http.schemas.resources import (
    ResourceResponse,
    ReviewedResourceInput,
    UnitSummaryResponse,
)


def create_resources_router(
    review_service: ResourceReviewService,
    account_service: AccountService,
    media_use_case: GetResourceMediaUseCase,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["resources"])
    current_teacher = current_teacher_dependency(account_service)

    @router.get(
        "/review-summary",
        response_model=list[UnitSummaryResponse],
        summary="Count approved and pending resources per unit",
        responses=error_responses(401),
    )
    def get_review_summary(teacher_id: str = Depends(current_teacher)) -> list[dict[str, Any]]:
        """One row per unit of the teacher's courses."""
        return review_service.get_summary(teacher_id)

    @router.get(
        "/units/{unit_id}/resources",
        response_model=list[ResourceResponse],
        summary="List the resources of a unit",
        responses=error_responses(401, 404),
    )
    def list_unit_resources(unit_id: str, teacher_id: str = Depends(current_teacher)) -> list[dict[str, Any]]:
        """Generated resources of the unit with their review, newest first."""
        return review_service.list_resources(teacher_id, unit_id)

    @router.put(
        "/units/{unit_id}/resources/{resource_id}",
        response_model=ResourceResponse,
        summary="Save the review of a resource",
        responses=error_responses(400, 401, 404, 409, 422),
    )
    def update_resource(
        unit_id: str, resource_id: str, body: ReviewedResourceInput, teacher_id: str = Depends(current_teacher)
    ) -> dict[str, Any]:
        """Saves edits and decisions. `aprobado` needs a key, no pending distractors and at least two accepted
        (409 APPROVAL_BLOCKED otherwise): the same rule the review screen shows."""
        return review_service.update_resource(
            teacher_id, unit_id, resource_id, body.model_dump(by_alias=True, exclude_unset=True)
        )

    @router.get(
        "/units/{unit_id}/resources/{resource_id}/media",
        summary="Get the image, graphic or audio of a resource",
        response_class=Response,
        responses={
            200: {
                "content": {"image/svg+xml": {}, "image/png": {}, "image/jpeg": {}, "audio/mpeg": {}, "audio/wav": {}},
                "description": "The file. Graphics are drawn as SVG from the resource structure.",
            },
            **error_responses(401, 404),
        },
    )
    def get_resource_media(unit_id: str, resource_id: str, teacher_id: str = Depends(current_teacher)) -> Response:
        """Concept maps, infographics and process diagrams are drawn as SVG from their items. Illustrations and
        audio return the generated file; without one, an illustration returns a card with its description and an
        audio resource answers 404 NO_MEDIA (the review reads the script with the browser's voice)."""
        media = media_use_case.execute(teacher_id, unit_id, resource_id)
        return Response(
            media.content,
            media_type=media.media_type,
            headers={"Content-Disposition": f'inline; filename="{media.file_name}"', "Cache-Control": "private, max-age=60"},
        )

    @router.delete(
        "/units/{unit_id}/resources/{resource_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        summary="Delete a resource",
        responses=error_responses(401, 404),
    )
    def delete_resource(unit_id: str, resource_id: str, teacher_id: str = Depends(current_teacher)) -> Response:
        """Deletes the resource from the unit."""
        review_service.delete_resource(teacher_id, unit_id, resource_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
