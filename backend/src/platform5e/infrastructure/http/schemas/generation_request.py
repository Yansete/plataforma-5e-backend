"""
Módulo de contratos de entrada para la solicitud de generación de recursos.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GenerationRequestModel(BaseModel):
    """
    Especificación de entrada para el servicio de generación de secuencias didácticas.
    Soporta nombres canónicos en inglés y alias en español para interoperabilidad con E2E.
    """

    model_config = ConfigDict(populate_by_name=True)

    unit_id: str = Field(
        ...,
        alias="unidad_id",
        description="Identificador de la unidad académica curricular (ej. u2).",
    )
    learning_outcome_id: str | None = Field(
        default=None,
        alias="resultado_aprendizaje_id",
        description="Código del resultado de aprendizaje específico a cubrir (ej. ra-2-1).",
    )
    stage_5e: Literal["engage", "explore", "explain", "elaborate", "evaluate"] = Field(
        ...,
        alias="etapa_5e",
        description="Etapa instruccional del modelo pedagógico 5E solicitada.",
    )
    resource_type: str = Field(
        ...,
        alias="tipo_recurso",
        description="Subtipo de recurso didáctico a producir (ej. item_opcion_multiple, pregunta_detonante).",
    )
    quantity: int = Field(
        default=1,
        alias="cantidad",
        ge=1,
        le=5,
        description="Número de variantes o instancias de recursos a generar.",
    )
    difficulty: Literal["basica", "intermedia", "avanzada"] = Field(
        default="intermedia",
        alias="dificultad",
        description="Nivel de complejidad cognitiva estimada para el recurso.",
    )
    options_count: int = Field(
        default=4,
        alias="alternativas",
        ge=2,
        le=5,
        description="Cantidad de opciones de respuesta a generar en recursos de evaluación.",
    )
    top_k: int = Field(
        default=10,
        alias="top_k",
        ge=1,
        le=50,
        description="Cantidad máxima de fragmentos contextuales a recuperar del repositorio.",
    )
    evidence_threshold: float = Field(
        default=0.6,
        alias="umbral_evidencia",
        ge=0.0,
        le=1.0,
        description="Umbral mínimo de similitud semántica requerido para admitir un fragmento.",
    )
    instructions: str | None = Field(
        default="",
        alias="indicaciones",
        max_length=500,
        description="Instrucciones docentes complementarias para guiar el enfoque pedagógico.",
    )