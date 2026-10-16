"""Esquemas del historial de descargas y de la exportación en el backend."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from platform5e.infrastructure.http.schemas.common import ApiRequest, ApiResponse

DownloadFormat = Literal["moodle_xml", "scorm_zip", "documento"]


class DownloadInput(ApiRequest):
    """A file built in the browser (the unit document) and saved by the teacher."""

    format: DownloadFormat
    file_name: str = Field(min_length=1, max_length=200, examples=["red-301-unidad-1-documento.html"])
    resource_count: int = Field(ge=0, le=500)


class DownloadResponse(ApiResponse):
    id: str
    unit_id: str
    format: str
    file_name: str
    resource_count: int
    created_at: str


class ExportRequest(ApiRequest):
    format: Literal["scorm_zip", "moodle_xml"] = Field(
        description="`scorm_zip`: SCORM 1.2 package for Chamilo. `moodle_xml`: Moodle question bank (multiple choice)."
    )
    resource_ids: list[str] = Field(
        default_factory=list,
        max_length=500,
        description="Approved resources to export; empty exports every approved resource that fits the format.",
    )
