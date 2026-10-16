"""
Fábrica del generador principal (modelo de lenguaje) y del de respaldo (por reglas), según las
variables LLM_* descritas en platform5e.infrastructure.settings.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from platform5e.application.ports.outbound.language_model_port import ResourceGeneratorPort
from platform5e.application.services.generation.rule_based_generator import RuleBasedGenerator
from platform5e.infrastructure.llm.gemini_language_model import GeminiLanguageModel
from platform5e.infrastructure.settings import read_setting

RULES_PROVIDERS = {"rules", "reglas"}  # «reglas»: nombre anterior, se acepta mientras se actualizan los paneles


def create_generators(
    environment: Mapping[str, str] | None = None,
) -> tuple[ResourceGeneratorPort, ResourceGeneratorPort]:
    """Crea los generadores principal y de respaldo (fallback). Si no hay clave, usa reglas."""

    def setting(name: str) -> str:
        return read_setting(name, "", environment).strip()

    fallback_generator = RuleBasedGenerator()
    api_key = setting("LLM_API_KEY")
    provider = (setting("LLM_PROVIDER") or ("gemini" if api_key else "rules")).lower()

    if provider in RULES_PROVIDERS or not api_key:
        return fallback_generator, fallback_generator

    primary_generator = GeminiLanguageModel(
        provider=provider,
        api_key=api_key,
        model=setting("LLM_MODEL") or None,
        base_url=setting("LLM_BASE_URL") or None,
        timeout=float(setting("LLM_TIMEOUT_SECONDS") or 90.0),
    )
    return primary_generator, fallback_generator


def describe_generator(generator: ResourceGeneratorPort) -> dict[str, Any]:
    """Retorna los metadatos de configuración del generador activo para la UI."""
    return {
        "description": generator.description,
        "usesAi": bool(getattr(generator, "uses_ai", False)),
        "provider": getattr(generator, "provider", "rules"),
        "model": getattr(generator, "model", None),
    }