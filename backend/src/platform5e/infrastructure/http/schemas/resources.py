"""Esquemas de los recursos generados y su revisión docente."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from platform5e.infrastructure.http.schemas.common import ApiRequest, ApiResponse

# Valores guardados en la base: pasan al inglés en el Sprint 2 junto con una migración de datos.
ReviewStatus = Literal["pendiente", "aprobado", "descartado"]
OptionDecision = Literal["pendiente", "aceptado", "descartado"]
DiscardReason = Literal["sin_sentido", "tambien_correcto", "duplicado", "fuera_de_unidad", "otro", "regenerado"]


class CitationResponse(ApiResponse):
    claim: str = Field(description="Sentence of the resource that needs support.")
    fragment_ids: list[str] = Field(description="Chunks of the teacher's material that support it.")


class EvidenceResponse(ApiResponse):
    """Copy of a cited chunk, saved with the resource when it was generated."""

    id: str
    text: str
    location: str
    document_id: str
    document_name: str
    source_url: str | None = None
    license: str | None = None


class ResourceOptionResponse(ApiResponse):
    id: str
    text: str
    is_correct: bool
    feedback: str = ""
    source_fragment_ids: list[str] = []
    decision: str = Field(description="Only distractors are decided: `pendiente`, `aceptado` or `descartado`.")
    discard_reason: str | None = None
    edited: bool = False


class ResourceResponse(ApiResponse):
    id: str
    unit_id: str
    outcome_id: str | None = None
    stage: str = Field(description="5E stage: engage, explore, explain, elaborate or evaluate.")
    type: str = Field(description="Resource type, e.g. `item_opcion_multiple`.")
    title: str
    body: str = Field(description="Content. In questions it is the prompt; paragraphs separated by a blank line.")
    options: list[ResourceOptionResponse] | None = None
    citations: list[CitationResponse] = []
    status: str = Field(description="`pendiente`, `aprobado` or `descartado`.")
    edited: bool = False
    discard_reason: str | None = None
    created_at: str
    updated_at: str | None = None
    decided_at: str | None = None
    evidence: list[EvidenceResponse] = []
    params: dict[str, Any] | None = Field(default=None, description="Request parameters, reused by «Regenerar».")


class ReviewedOptionInput(ApiRequest):
    id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=600)
    feedback: str = Field(default="", max_length=600)
    decision: OptionDecision
    discard_reason: DiscardReason | None = None
    edited: bool = False


class ReviewedResourceInput(ApiRequest):
    """The teacher's review. Approval is blocked while distractors are pending (409 APPROVAL_BLOCKED)."""

    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=8000)
    status: ReviewStatus
    discard_reason: DiscardReason | None = None
    edited: bool = False
    options: list[ReviewedOptionInput] | None = Field(default=None, max_length=10)


class UnitSummaryResponse(ApiResponse):
    course_id: str
    unit_id: str
    approved: int = Field(description="Approved resources of the unit.")
    pending: int = Field(description="Resources waiting for review.")
