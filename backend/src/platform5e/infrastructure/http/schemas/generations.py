"""Esquemas de la generación de recursos con el material de la unidad (RAG)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from platform5e.infrastructure.http.schemas.common import ApiRequest, ApiResponse
from platform5e.infrastructure.http.schemas.resources import ResourceResponse

Stage = Literal["engage", "explore", "explain", "elaborate", "evaluate"]
ResourceType = Literal[
    "pregunta_detonante",
    "sondeo_diagnostico",
    "guia_exploracion",
    "caso_indagacion",
    "explicacion",
    "glosario",
    "ejercicio_aplicacion",
    "item_opcion_multiple",
]
Difficulty = Literal["basica", "intermedia", "avanzada"]


class GenerationRequest(ApiRequest):
    unit_id: str = Field(description="Unit whose processed material is used.", examples=["unidad-1"])
    outcome_id: str | None = Field(default=None, description="Learning outcome of the unit, optional.")
    stage: Stage = Field(description="5E stage of the requested resource.", examples=["evaluate"])
    resource_type: ResourceType = Field(examples=["item_opcion_multiple"])
    quantity: int = Field(default=1, ge=1, le=5)
    difficulty: Difficulty = "intermedia"
    option_count: int = Field(default=4, ge=2, le=5, description="Options per multiple-choice item.")
    top_k: int = Field(default=10, ge=1, le=50, description="Chunks retrieved from the material (BM25).")
    evidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    instructions: str = Field(default="", max_length=500, description="Free text from the teacher.")
    audience: str = Field(default="", max_length=200, examples=["Tercer ciclo"])
    competency: str = Field(default="", max_length=200)
    # Sprint 1: solo texto (HU-053, alcance acordado con el docente). Otra modalidad responde 422.
    modalities: list[Literal["Textual"]] = Field(
        default_factory=lambda: ["Textual"], max_length=1, description="Sprint 1 generates text only."
    )

    def to_domain(self) -> dict[str, Any]:
        """El diccionario que esperan los servicios de generación."""
        return {
            "unitId": self.unit_id,
            "outcomeId": self.outcome_id,
            "stage": self.stage,
            "resourceType": self.resource_type,
            "quantity": self.quantity,
            "difficulty": self.difficulty,
            "optionCount": self.option_count,
            "topK": self.top_k,
            "evidenceThreshold": self.evidence_threshold,
            "instructions": self.instructions,
            "audience": self.audience,
            "competency": self.competency,
            "modalities": self.modalities,
        }


class GeneratorInfo(ApiResponse):
    description: str = Field(examples=["Gemini (gemini-2.5-flash)"])
    uses_ai: bool = Field(description="False when the rule-based generator is active.")
    provider: str = Field(examples=["gemini", "rules"])
    model: str | None = None


class GenerationGenerator(ApiResponse):
    description: str
    uses_ai: bool
    fallback: bool = Field(description="True when the AI failed and the rule-based generator answered.")


class GenerationRequestRecord(ApiResponse):
    """The request as it was saved: GET /generations lists them, newest first."""

    id: str
    unit_id: str
    created_at: str
    stage: str
    resource_type: str
    quantity: int


class GeneratedChunk(ApiResponse):
    id: str
    location: str | None = None
    text: str | None = None
    relevance: float = 0.0


class GenerationResult(ApiResponse):
    mode: Literal["api_demo", "rag"] = Field(description="`rag`: the teacher's material; `api_demo`: test catalog.")
    notice: str = Field(description="Message shown to the teacher.")
    generator: GenerationGenerator | None = None
    request: dict[str, Any] = Field(description="The saved request, with its id.")
    resources: list[ResourceResponse] = Field(description="Generated resources, saved as `pendiente` for review.")
    available: int
    fragments: list[dict[str, Any]] = Field(description="Chunks cited by the resources.")
    documents: list[dict[str, Any]] = Field(description="Documents those chunks come from.")
    retrieved_chunks: list[GeneratedChunk] = Field(
        default=[], description="Everything retrieved, not only what was cited. Used by the Ragas evaluation."
    )
