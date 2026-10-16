"""
Redacción de recursos pedagógicos con evidencia: prepara el contexto,
construye los prompts para el LLM y valida formalmente el esquema devuelto.
"""

from __future__ import annotations

import json
import re
from typing import Any

PHASES_5E: dict[str, tuple[str, str]] = {
    "engage": ("Enganchar", "activar ideas previas y despertar la curiosidad"),
    "explore": ("Explorar", "que el estudiante indague y descubra a partir de actividades"),
    "explain": ("Explicar", "formalizar el concepto con lenguaje disciplinar preciso"),
    "elaborate": ("Elaborar", "aplicar lo aprendido a situaciones nuevas"),
    "evaluate": ("Evaluar", "comprobar el logro del resultado de aprendizaje"),
}

RESOURCE_TYPES: dict[str, tuple[str, str]] = {
    "pregunta_detonante": (
        "Pregunta detonante",
        "Una situación breve tomada del material y una pregunta abierta que despierte curiosidad.",
    ),
    "sondeo_diagnostico": (
        "Sondeo diagnóstico de ideas previas",
        "Entre 4 y 6 afirmaciones de verdadero o falso para detectar concepciones alternativas.",
    ),
    "guia_exploracion": (
        "Guía de exploración",
        "Objetivo, materiales y de 4 a 6 pasos de indagación guiada con preguntas de registro.",
    ),
    "caso_indagacion": (
        "Caso con preguntas de indagación",
        "Un caso breve basado en el material y de 3 a 4 preguntas reflexivas.",
    ),
    "explicacion": (
        "Explicación citada",
        "Una explicación estructurada de 3 a 5 párrafos donde cada párrafo se apoya en una cita.",
    ),
    "glosario": (
        "Glosario de la unidad",
        "De 6 a 10 términos clave con su definición tomada estrictamente del material.",
    ),
    "ejercicio_aplicacion": (
        "Ejercicio de aplicación",
        "Un ejercicio de transferencia a un contexto nuevo con consigna y criterios de logro.",
    ),
    "item_opcion_multiple": (
        "Ítem de opción múltiple",
        "Un enunciado con 1 respuesta correcta y distractores plausibles con retroalimentación.",
    ),
}

DIFFICULTY_LABELS: dict[str, str] = {
    "basica": "básica",
    "intermedia": "intermedia",
    "avanzada": "avanzada",
}

MAX_TITLE_CHARS: int = 160
MAX_CONTENT_CHARS: int = 8000
MAX_CLAIM_CHARS: int = 600
MAX_OPTION_CHARS: int = 600


def format_fragment_tag(index: int) -> str:
    """Retorna la etiqueta canónica de citación (F1, F2...)."""
    return f"F{index + 1}"


def build_generation_context(
    course: dict[str, Any],
    unit: dict[str, Any],
    request_data: dict[str, Any],
    chunks: list[dict[str, Any]],
    documents: dict[str, str],
) -> dict[str, Any]:
    """Empaqueta los metadatos y fragmentos rotulados para alimentar el generador."""
    matched_outcomes = [
        outcome
        for outcome in unit.get("outcomes", [])
        if not request_data.get("outcomeId") or outcome["id"] == request_data["outcomeId"]
    ]
    return {
        "curso": {
            "nombre": course.get("name", ""),
            "sumilla": course.get("sumilla", ""),
            "logro": course.get("logro", ""),
        },
        "unidad": {
            "numero": unit.get("number"),
            "titulo": unit.get("title", ""),
            "resultados": [f"{o.get('code', '')}: {o.get('text', '')}" for o in matched_outcomes],
        },
        "solicitud": {
            "etapa": request_data["stage"],
            "tipo": request_data["resourceType"],
            "cantidad": request_data["quantity"],
            "dificultad": request_data.get("difficulty", "intermedia"),
            "alternativas": request_data.get("optionCount", 4),
            "indicaciones": request_data.get("instructions", ""),
            "publico": request_data.get("audience", ""),
            "competencia": request_data.get("competency", ""),
            "modalidades": request_data.get("modalities", []),
        },
        "fragmentos": [
            {
                "etiqueta": format_fragment_tag(i),
                "id": chunk["id"],
                "ubicacion": chunk.get("location") or chunk.get("ubicacion", ""),
                "documento": documents.get(chunk.get("documentId") or chunk.get("documento_id", ""), ""),
                "texto": chunk.get("text") or chunk.get("texto", ""),
            }
            for i, chunk in enumerate(chunks)
        ],
    }


def build_prompt_instructions(context: dict[str, Any]) -> tuple[str, str]:
    """Genera las instrucciones estructuradas del sistema y del usuario para el LLM."""
    req = context["solicitud"]
    stage_name, purpose = PHASES_5E[req["etapa"]]
    type_name, format_desc = RESOURCE_TYPES[req["tipo"]]

    system_prompt = (
        f"Eres un asistente pedagógico que redacta recursos para la etapa «{stage_name}» del modelo 5E ({purpose}). "
        "Escribes en español claro para docentes universitarios del Perú. "
        "No menciones el modelo 5E ni el nombre de la etapa en los títulos ni en el contenido. "
        "Usa SOLO la información de los FRAGMENTOS del material: no agregues datos ajenos. "
        "Cada afirmación importante debe citar las etiquetas de los fragmentos que la respaldan (F1, F2…). "
        "Si los fragmentos no alcanzan, devuelve menos recursos. "
        "Genera solo texto: no incluyas imágenes, enlaces a video o audio, ni instrucciones para producir material multimedia. "
        "Responde únicamente con JSON válido, sin delimitadores adicionales."
    )

    course, unit = context["curso"], context["unidad"]
    lines = [
        f"CURSO: {course['nombre']}",
        f"SUMILLA: {course['sumilla'] or 'no registrada'}",
        f"LOGRO DEL CURSO: {course['logro'] or 'no registrado'}",
        f"UNIDAD {unit['numero']}: {unit['titulo']}",
        "RESULTADOS DE APRENDIZAJE: " + ("; ".join(unit["resultados"]) or "no registrados"),
        "",
        f"PEDIDO: {req['cantidad']} recurso(s) de tipo «{type_name}». {format_desc}",
        f"Dificultad: {DIFFICULTY_LABELS.get(req['dificultad'], req['dificultad'])}.",
    ]

    if req["tipo"] == "item_opcion_multiple":
        lines.append(
            f"Cada ítem debe tener exactamente {req['alternativas']} alternativas: 1 correcta y {req['alternativas'] - 1} distractores."
        )
    if req["publico"]:
        lines.append(f"Público: {req['publico']}.")
    if req["competencia"]:
        lines.append(f"Competencia a desarrollar: {req['competencia']}.")
    if req["indicaciones"]:
        lines.append(f"Indicaciones del docente: {req['indicaciones']}")

    lines += [
        "",
        "FORMATO DE RESPUESTA (JSON):",
        '{"recursos": [{"titulo": "...", "contenido": "...",',
        ' "citas": [{"afirmacion": "...", "fragmentos": ["F1"]}],',
        ' "alternativas": [{"texto": "...", "correcta": true, "retroalimentacion": "...", "fragmentos": ["F2"]}]}]}',
        "«alternativas» solo se llena en ítems de opción múltiple; en los demás tipos usa [].",
        "",
        "FRAGMENTOS DEL MATERIAL:",
    ]

    for frag in context["fragmentos"]:
        origin = ", ".join(x for x in (frag["documento"], frag["ubicacion"]) if x)
        lines += [f"[{frag['etiqueta']}] ({origin})", frag["texto"], ""]

    return system_prompt, "\n".join(lines).strip()


def parse_json_response(raw_text: str) -> Any:
    """Extrae y parsea el objeto JSON incluso si viene encerrado en bloques markdown."""
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise ValueError("La respuesta del modelo está vacía.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx > start_idx:
        try:
            return json.loads(cleaned[start_idx : end_idx + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError("La respuesta del modelo no es JSON válido.")


def _clean_inline_text(value: Any, max_len: int) -> str:
    """Limpia saltos de línea y normaliza espacios simples."""
    return " ".join(value.split())[:max_len] if isinstance(value, str) else ""


def _clean_multiline_block(value: Any, max_len: int) -> str:
    """Conserva párrafos y saltos de línea intencionales limitando el largo total."""
    if not isinstance(value, str):
        return ""
    lines = [" ".join(line.split()) for line in value.replace("\r", "").split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()[:max_len]


def _resolve_fragment_ids(value: Any, tag_mapping: dict[str, str]) -> list[str]:
    """Mapea etiquetas F1, F2 a sus identificadores de base de datos."""
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        value = [value]
    if not isinstance(value, list):
        return []
    resolved_ids: list[str] = []
    for item in value:
        if isinstance(item, bool):
            continue
        digits = [str(item)] if isinstance(item, int) else re.findall(r"\d+", str(item))
        for digit in digits:
            tag_key = f"F{int(digit)}"
            if tag_key in tag_mapping and tag_mapping[tag_key] not in resolved_ids:
                resolved_ids.append(tag_mapping[tag_key])
    return resolved_ids


def _parse_is_correct(alternative: dict[str, Any]) -> bool:
    """Determina si una opción es la clave correcta aceptando variantes sintácticas."""
    raw_val = next(
        (alternative[k] for k in ("correcta", "esCorrecta", "correct", "isCorrect") if k in alternative),
        False,
    )
    if isinstance(raw_val, str):
        return raw_val.strip().lower() in ("true", "sí", "si", "verdadero", "correcta")
    return raw_val is True


def normalize_generated_resources(raw_payload: Any, context: dict[str, Any]) -> list[dict[str, Any]]:
    """Valida que cada recurso tenga contenido, evidencia verificable y alternativas válidas."""
    tag_mapping = {f["etiqueta"]: f["id"] for f in context["fragmentos"]}
    req = context["solicitud"]
    items_list = raw_payload.get("recursos") if isinstance(raw_payload, dict) else raw_payload
    if not isinstance(items_list, list):
        return []

    verified_resources: list[dict[str, Any]] = []
    for raw_item in items_list:
        if len(verified_resources) >= req["cantidad"] or not isinstance(raw_item, dict):
            continue

        body = _clean_multiline_block(raw_item.get("contenido"), MAX_CONTENT_CHARS)
        valid_citations: list[dict[str, Any]] = []

        for cit in raw_item.get("citas") or []:
            if isinstance(cit, dict):
                matched_ids = _resolve_fragment_ids(cit.get("fragmentos"), tag_mapping)
                claim = _clean_inline_text(cit.get("afirmacion"), MAX_CLAIM_CHARS)
                if matched_ids and claim:
                    valid_citations.append({"claim": claim, "fragmentIds": matched_ids})

        if not body or not valid_citations:
            continue

        title = (
            _clean_inline_text(raw_item.get("titulo"), MAX_TITLE_CHARS)
            or f"{RESOURCE_TYPES[req['tipo']][0]} {len(verified_resources) + 1}"
        )

        alternatives = None
        if req["tipo"] == "item_opcion_multiple":
            alternatives = _validate_alternatives(
                raw_item.get("alternativas"),
                tag_mapping,
                valid_citations,
                req["alternativas"],
            )
            if alternatives is None:
                continue

        verified_resources.append(
            {
                "titulo": title,
                "contenido": body,
                "citas": valid_citations,
                "alternativas": alternatives,
            }
        )

    return verified_resources


def _validate_alternatives(
    raw_options: Any,
    tag_mapping: dict[str, str],
    citations: list[dict[str, Any]],
    target_count: int,
) -> list[dict[str, Any]] | None:
    """Valida que exista exactamente una clave correcta y el número requerido de distractores."""
    if not isinstance(raw_options, list):
        return None

    fallback_citations = citations[0]["fragmentIds"]
    seen_texts: set[str] = set()
    correct_key: dict[str, Any] | None = None
    distractors: list[dict[str, Any]] = []

    for option in raw_options:
        if not isinstance(option, dict):
            continue
        text = _clean_inline_text(option.get("texto"), MAX_OPTION_CHARS)
        if not text or text.casefold() in seen_texts:
            continue
        seen_texts.add(text.casefold())

        parsed_option = {
            "texto": text,
            "correcta": _parse_is_correct(option),
            "retroalimentacion": (
                _clean_inline_text(option.get("retroalimentacion"), MAX_OPTION_CHARS)
                or "Revisa el fragmento citado del material."
            ),
            "fragmentos": _resolve_fragment_ids(option.get("fragmentos"), tag_mapping)
            or fallback_citations,
        }

        if parsed_option["correcta"]:
            if correct_key is not None:
                return None  # Múltiples claves: ítem inválido
            correct_key = parsed_option
        else:
            distractors.append(parsed_option)

    if correct_key is None or len(distractors) < target_count - 1:
        return None

    return [correct_key, *distractors[: target_count - 1]]