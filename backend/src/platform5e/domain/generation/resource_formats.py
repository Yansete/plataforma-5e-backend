"""
Catálogo de tipos de recurso por etapa 5E y su formato: texto, visual (SVG), imagen, audio o actividad interactiva.

Los recursos que no son solo texto guardan su contenido estructurado en `structure` (claves en inglés). Este módulo
valida y limpia esa estructura; lo usan la generación (IA o reglas), la revisión docente y las exportaciones.
"""

from __future__ import annotations

import re
from typing import Any

TEXT = "text"
VISUAL = "visual"
IMAGE = "image"
AUDIO = "audio"
INTERACTIVE = "interactive"

# Tipo de recurso (valor guardado) -> (etapa 5E, formato).
RESOURCE_CATALOG: dict[str, tuple[str, str]] = {
    "pregunta_detonante": ("engage", TEXT),
    "sondeo_diagnostico": ("engage", TEXT),
    "audio_detonante": ("engage", AUDIO),
    "guia_exploracion": ("explore", TEXT),
    "caso_indagacion": ("explore", TEXT),
    "imagen_ilustrativa": ("explore", IMAGE),
    "diagrama_proceso": ("explore", VISUAL),
    "explicacion": ("explain", TEXT),
    "glosario": ("explain", TEXT),
    "mapa_conceptual": ("explain", VISUAL),
    "infografia": ("explain", VISUAL),
    "podcast_resumen": ("explain", AUDIO),
    "ejercicio_aplicacion": ("elaborate", TEXT),
    "emparejamiento": ("elaborate", INTERACTIVE),
    "ordenar_pasos": ("elaborate", INTERACTIVE),
    "item_opcion_multiple": ("evaluate", TEXT),
    "verdadero_falso": ("evaluate", INTERACTIVE),
    "completar_espacios": ("evaluate", INTERACTIVE),
}

BLANK = "____"
MAX_ITEMS = 10
MAX_SHORT = 160
MAX_LONG = 600
MAX_SCRIPT = 2400

# Mínimo de elementos para que la actividad o el gráfico tengan sentido.
MIN_ITEMS: dict[str, int] = {
    "mapa_conceptual": 3,
    "infografia": 3,
    "diagrama_proceso": 3,
    "emparejamiento": 3,
    "ordenar_pasos": 3,
    "verdadero_falso": 3,
    "completar_espacios": 2,
}


def resource_format(resource_type: str) -> str:
    return RESOURCE_CATALOG.get(resource_type, ("", TEXT))[1]


def resource_stage(resource_type: str) -> str:
    return RESOURCE_CATALOG.get(resource_type, ("", TEXT))[0]


def needs_structure(resource_type: str) -> bool:
    return resource_format(resource_type) != TEXT


def _short(value: Any, limit: int = MAX_SHORT) -> str:
    return " ".join(value.split())[:limit] if isinstance(value, str) else ""


def _items(value: Any) -> list[Any]:
    return value[:MAX_ITEMS] if isinstance(value, list) else []


def _is_true(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "verdadero", "verdadera", "v", "sí", "si")
    return value is True


def _titled_points(value: Any) -> list[dict[str, str]]:
    points = []
    for item in _items(value):
        if isinstance(item, dict):
            title, text = _short(item.get("title")), _short(item.get("text"), MAX_LONG)
            if title or text:
                points.append({"title": title or text[:60], "text": text})
    return points


def _with_blank(sentence: str, answer: str) -> str:
    """Asegura el espacio en blanco: si la oración trae la respuesta, la oculta."""
    if BLANK in sentence or re.search(r"_{3,}", sentence):
        return re.sub(r"_{3,}", BLANK, sentence, count=1)
    masked = re.sub(rf"(?<!\w){re.escape(answer)}(?!\w)", BLANK, sentence, count=1, flags=re.IGNORECASE)
    return masked if masked != sentence else ""


def normalize_structure(resource_type: str, raw: Any) -> dict[str, Any] | None:
    """Devuelve la estructura limpia del tipo, o None si no alcanza para un recurso útil."""
    if not needs_structure(resource_type):
        return None
    data = raw if isinstance(raw, dict) else {}
    kind = resource_format(resource_type)
    structure: dict[str, Any]

    if resource_type == "mapa_conceptual":
        nodes = []
        for item in _items(data.get("nodes")):
            if isinstance(item, dict) and _short(item.get("label")):
                nodes.append({"label": _short(item.get("label"), 60), "detail": _short(item.get("detail"), 200)})
        structure = {"central": _short(data.get("central"), 80), "nodes": nodes}
        if not structure["central"]:
            return None
    elif resource_type == "infografia":
        structure = {"headline": _short(data.get("headline"), 120), "points": _titled_points(data.get("points"))}
    elif resource_type == "diagrama_proceso":
        structure = {"steps": _titled_points(data.get("steps"))}
    elif resource_type == "ordenar_pasos":
        sequence = [_short(step, MAX_LONG) for step in _items(data.get("sequence"))]
        structure = {"sequence": [step for step in sequence if step]}
    elif resource_type == "emparejamiento":
        pairs, seen = [], set()
        for item in _items(data.get("pairs")):
            if isinstance(item, dict):
                term, definition = _short(item.get("term"), 80), _short(item.get("definition"), MAX_LONG)
                if term and definition and term.casefold() not in seen:
                    seen.add(term.casefold())
                    pairs.append({"term": term, "definition": definition})
        structure = {"pairs": pairs}
    elif resource_type == "verdadero_falso":
        statements = []
        for item in _items(data.get("statements")):
            if isinstance(item, dict) and _short(item.get("text"), MAX_LONG):
                statements.append(
                    {
                        "text": _short(item.get("text"), MAX_LONG),
                        "isTrue": _is_true(item.get("isTrue")),
                        "feedback": _short(item.get("feedback"), MAX_LONG),
                    }
                )
        structure = {"statements": statements}
    elif resource_type == "completar_espacios":
        blanks = []
        for item in _items(data.get("blanks")):
            if isinstance(item, dict):
                answer = _short(item.get("answer"), 80)
                sentence = _with_blank(_short(item.get("sentence"), MAX_LONG), answer) if answer else ""
                if sentence:
                    blanks.append({"sentence": sentence, "answer": answer})
        structure = {"blanks": blanks}
    elif kind == AUDIO:
        script = data.get("script")
        structure = {"script": " ".join(script.split())[:MAX_SCRIPT] if isinstance(script, str) else ""}
        return structure if len(structure["script"].split()) >= 15 else None
    elif kind == IMAGE:
        structure = {
            "prompt": _short(data.get("prompt"), MAX_LONG),
            "alt": _short(data.get("alt"), 300),
            "caption": _short(data.get("caption"), 300),
        }
        if not structure["prompt"]:
            return None
        structure["alt"] = structure["alt"] or structure["prompt"][:300]
        return structure
    else:
        return None

    lists = [value for value in structure.values() if isinstance(value, list)]
    if lists and len(lists[0]) < MIN_ITEMS.get(resource_type, 1):
        return None
    if resource_type == "verdadero_falso":
        answers = {s["isTrue"] for s in structure["statements"]}
        if answers != {True, False}:
            return None  # una actividad de verdadero o falso necesita de los dos tipos
    return structure


def structure_problems(resource_type: str, structure: Any) -> list[str]:
    """Motivos que impiden aprobar un recurso con estructura (para la revisión docente)."""
    if not needs_structure(resource_type):
        return []
    if normalize_structure(resource_type, structure) is None:
        minimum = MIN_ITEMS.get(resource_type)
        if minimum:
            return [f"La actividad necesita al menos {minimum} elementos completos para poder aprobarla."]
        return ["Completa el contenido del recurso para poder aprobarlo."]
    return []
