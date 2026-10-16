"""
Fábrica para instanciar el generador LLM principal y de respaldo según variables de entorno.

IA_PROVEEDOR  gemini | anthropic | openai | reglas (por defecto: gemini si hay clave, si no reglas)
IA_API_KEY    clave de API del proveedor
IA_MODELO     opcional; por defecto gemini-2.5-flash, claude-sonnet-5-5 o gpt-5.4-mini
IA_URL_BASE   opcional; para proxies o servicios compatibles con OpenAI
IA_TIEMPO_MAX tiempo de espera en segundos por respuesta (por defecto 90)
"""

from __future__ import annotations

import os
from typing import Any

from platform5e.application.ports.outbound.language_model_port import ResourceGeneratorPort
from platform5e.application.services.generation.rule_based_generator import RuleBasedGenerator
from platform5e.infrastructure.llm.gemini_language_model import GeminiLanguageModel


def create_generators(
    environment: dict[str, str] | None = None,
) -> tuple[ResourceGeneratorPort, ResourceGeneratorPort]:
    """Crea los generadores principal y de respaldo (fallback). Si no hay clave, usa reglas."""
    env = os.environ if environment is None else environment
    fallback_generator = RuleBasedGenerator()
    api_key = (env.get("IA_API_KEY") or "").strip()
    provider = (env.get("IA_PROVEEDOR") or ("gemini" if api_key else "reglas")).strip().lower()

    if provider == "reglas" or not api_key:
        return fallback_generator, fallback_generator

    primary_generator = GeminiLanguageModel(
        provider=provider,
        api_key=api_key,
        model=(env.get("IA_MODELO") or "").strip() or None,
        base_url=(env.get("IA_URL_BASE") or "").strip() or None,
        timeout=float(env.get("IA_TIEMPO_MAX") or 90.0),
    )
    return primary_generator, fallback_generator


def describe_generator(generator: ResourceGeneratorPort) -> dict[str, Any]:
    """Retorna los metadatos de configuración del generador activo para la UI."""
    return {
        "descripcion": generator.description,
        "usaIA": bool(getattr(generator, "uses_ai", getattr(generator, "usa_ia", False))),
        "proveedor": getattr(generator, "provider", getattr(generator, "proveedor", "reglas")),
        "modelo": getattr(generator, "model", getattr(generator, "modelo", None)),
    }