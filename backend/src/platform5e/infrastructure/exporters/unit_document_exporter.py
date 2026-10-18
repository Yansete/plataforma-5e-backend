"""Documento HTML de la unidad: plantilla fija, recursos aprobados y evidencia del material."""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
import re
from string import Template
import unicodedata

from platform5e.application.ports.outbound.unit_exporter_port import ExportedFile
from platform5e.domain.generation.resource_formats import AUDIO, IMAGE, INTERACTIVE, VISUAL, resource_format
from platform5e.infrastructure.exporters.visual_renderer import SvgVisualRenderer, can_render
from platform5e.infrastructure.html_sanitizer import clean_html

# Las etiquetas reproducen el documento existente; los valores guardados siguen en español.
RESOURCE_LABELS = {
    "pregunta_detonante": ("Para iniciar la clase", "Pregunta detonante"),
    "sondeo_diagnostico": ("Para iniciar la clase", "Sondeo de ideas previas"),
    "guia_exploracion": ("Para explorar", "Guía de exploración"),
    "caso_indagacion": ("Para explorar", "Caso con preguntas"),
    "explicacion": ("Para explicar", "Explicación del tema"),
    "glosario": ("Para explicar", "Glosario"),
    "ejercicio_aplicacion": ("Para aplicar", "Ejercicio de aplicación"),
    "item_opcion_multiple": ("Para evaluar", "Pregunta de opción múltiple"),
    "audio_detonante": ("Para iniciar la clase", "Cápsula de audio"),
    "imagen_ilustrativa": ("Para explorar", "Imagen ilustrativa"),
    "diagrama_proceso": ("Para explorar", "Diagrama de proceso"),
    "mapa_conceptual": ("Para explicar", "Mapa conceptual"),
    "infografia": ("Para explicar", "Infografía"),
    "podcast_resumen": ("Para explicar", "Resumen en pódcast"),
    "emparejamiento": ("Para aplicar", "Relacionar conceptos"),
    "ordenar_pasos": ("Para aplicar", "Ordenar pasos"),
    "verdadero_falso": ("Para evaluar", "Verdadero o falso"),
    "completar_espacios": ("Para evaluar", "Completar espacios"),
}
GROUPS = tuple(dict.fromkeys(group for group, _ in RESOURCE_LABELS.values()))
MONTHS = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre")
LETTERS = "abcdefghij"
TEMPLATE = Template(Path(__file__).with_name("unit_document.html").read_text(encoding="utf-8"))


def _esc(value: object) -> str:
    return escape(str(value or ""), quote=True)


def _safe_url(value: str | None) -> str | None:
    return value if value and re.match(r"^https?://", value, re.IGNORECASE) else None


def _source(evidence: Mapping) -> str:
    url = _safe_url(evidence.get("sourceUrl"))
    name = _esc(evidence.get("documentName") or "Material de la unidad")
    location = f', {_esc(evidence["location"])}' if evidence.get("location") else ""
    license_label = f' ({_esc(evidence["license"])})' if evidence.get("license") else ""
    link = f' · <a href="{_esc(url)}">fuente</a>{license_label}' if url else ""
    return f'<span class="src">{name}{location}{link}</span>'


def _media_html(resource: Mapping) -> str:
    """Gráfico o imagen dentro del documento (un solo archivo), guion del audio o actividad para imprimir."""
    kind = resource_format(resource.get("type", ""))
    structure = resource.get("structure") or {}
    stored = resource.get("mediaFile")
    if kind == IMAGE and stored:
        encoded = base64.b64encode(stored["content"]).decode("ascii")
        caption = f'<figcaption>{_esc(structure.get("caption"))}</figcaption>' if structure.get("caption") else ""
        return f'<figure><img src="data:{_esc(stored["mimeType"])};base64,{encoded}" alt="{_esc(structure.get("alt"))}">{caption}</figure>'
    if kind in (VISUAL, IMAGE) and structure and can_render(resource.get("type", "")):
        return f'<figure class="graphic">{SvgVisualRenderer().render(resource)}</figure>'
    if kind == AUDIO:
        note = "El audio está en el paquete SCORM." if stored else "Guion para leer en voz alta o escuchar en la plataforma."
        return f'<div class="script"><p class="meta">{note}</p><p>{_esc(structure.get("script"))}</p></div>'
    if kind != INTERACTIVE:
        return ""
    rows, key = [], []
    kind_type = resource.get("type")
    if kind_type == "emparejamiento":
        pairs = structure.get("pairs") or []
        definitions = sorted((p["definition"] for p in pairs), key=lambda d: d.casefold())
        rows = [f"<li>{_esc(p['term'])} → ______</li>" for p in pairs]
        rows.append('</ol><p class="meta">Descripciones:</p><ol type="A">' + "".join(f"<li>{_esc(d)}</li>" for d in definitions))
        key = [f"{_esc(p['term'])}: {_esc(p['definition'])}" for p in pairs]
    elif kind_type == "verdadero_falso":
        rows = [f"<li>{_esc(st['text'])} (V / F)</li>" for st in structure.get("statements") or []]
        key = [f"{n}. {'Verdadero' if st['isTrue'] else 'Falso'}. {_esc(st.get('feedback'))}" for n, st in enumerate(structure.get("statements") or [], 1)]
    elif kind_type == "completar_espacios":
        rows = [f"<li>{_esc(b['sentence'])}</li>" for b in structure.get("blanks") or []]
        key = [f"{n}. {_esc(b['answer'])}" for n, b in enumerate(structure.get("blanks") or [], 1)]
    elif kind_type == "ordenar_pasos":
        sequence = list(structure.get("sequence") or [])
        rows = [f"<li>{_esc(step)}</li>" for step in sorted(sequence, key=lambda x: x.casefold())]
        key = [f"{n}. {_esc(step)}" for n, step in enumerate(sequence, 1)]
    answer_key = "<details><summary>Clave de respuestas</summary><ul>" + "".join(f"<li>{k}</li>" for k in key) + "</ul></details>"
    return f'<ol class="activity">{"".join(rows)}</ol>{answer_key}'


def _resource_html(resource: Mapping, unit: Mapping) -> str:
    options = resource.get("options")
    choices = ""
    if options is not None:
        exported = [o for o in options if o.get("isCorrect") or o.get("decision") != "descartado"]
        rows = []
        for index, option in enumerate(exported):
            key = ' <strong class="key">(respuesta correcta)</strong>' if option.get("isCorrect") else ""
            feedback = f'<div class="feedback">{_esc(option["feedback"])}</div>' if option.get("feedback") else ""
            rows.append(f'<li><span class="letter">{LETTERS[index]})</span> {_esc(option.get("text"))}{key}{feedback}</li>')
        choices = f'<ol class="options">{"".join(rows)}</ol>'
    by_id = {e["id"]: e for e in resource.get("evidence", [])}
    claims = []
    for citation in resource.get("citations", []):
        evidence = [by_id[key] for key in citation.get("fragmentIds", []) if key in by_id]
        if not evidence:
            continue
        sources = []
        for entry in evidence:
            text = entry.get("text", "")
            quote = text if len(text) <= 420 else text[:420].rstrip() + "…"
            sources.append(f'<li><span class="quote">«{_esc(quote)}»</span> {_source(entry)}</li>')
        claims.append(f'<li><strong>{_esc(citation.get("claim"))}</strong><ul>{"".join(sources)}</ul></li>')
    evidence_html = ('<details open><summary>Evidencia del material</summary><ul class="evidence">'
                     + "".join(claims) + '</ul></details>') if claims else ""
    outcome_code = next((o.get("code", "") for o in unit.get("outcomes", []) if o["id"] == resource.get("outcomeId")), "")
    label = RESOURCE_LABELS.get(resource.get("type"), RESOURCE_LABELS["item_opcion_multiple"])[1]
    meta = " · ".join(x for x in (label, outcome_code, "editado por el docente" if resource.get("edited") else "") if x)
    paragraphs = clean_html(resource.get("bodyHtml")) or "".join(
        f'<p>{_esc(part.strip()).replace(chr(10), "<br>")}</p>'
        for part in re.split(r"\n{2,}", resource.get("body", "")) if part.strip()
    )
    return (f'<article>\n  <h3>{_esc(resource.get("title"))}</h3>\n  <p class="meta">{_esc(meta)}</p>\n'
            f'  {paragraphs}\n  {_media_html(resource)}\n  {choices}\n  {evidence_html}\n</article>')


class UnitDocumentExporter:
    format = "documento"
    media_type = "text/html"

    def supports(self, resource: Mapping) -> bool:
        return True

    def export(self, resources: Sequence[Mapping], course: Mapping, unit: Mapping) -> ExportedFile:
        sections = []
        for group in GROUPS:
            items = [r for r in resources if RESOURCE_LABELS.get(r.get("type"), RESOURCE_LABELS["item_opcion_multiple"])[0] == group]
            if items:
                articles = "\n".join(_resource_html(r, unit) for r in items)
                sections.append(f'<section><h2>{_esc(group)}</h2>{articles}</section>')
        outcomes = "".join(f'<li><strong>{_esc(o.get("code"))}</strong> {_esc(o.get("text"))}</li>' for o in unit.get("outcomes", []))
        licensed = any(_safe_url(e.get("sourceUrl")) for r in resources for e in r.get("evidence", []))
        date = datetime.now(timezone(timedelta(hours=-5)))
        content = TEMPLATE.substitute(
            code=_esc(course.get("code")), name=_esc(course.get("name")), term=_esc(course.get("term")),
            number=_esc(unit.get("number")), title=_esc(unit.get("title")), count=len(resources),
            count_label="recurso aprobado" if len(resources) == 1 else "recursos aprobados",
            day=f"{date.day} de {MONTHS[date.month - 1]} de {date.year}",
            outcomes=f'<ul class="outcomes">{outcomes}</ul>' if outcomes else "",
            sections="\n".join(sections),
            license_note=" Los textos tomados de fuentes abiertas indican su enlace y su licencia junto a cada cita." if licensed else "",
        )
        normalized = unicodedata.normalize("NFD", str(course.get("code", "")))
        normalized = "".join(c for c in normalized if not unicodedata.combining(c))
        slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized).strip("-").lower() or "curso"
        return ExportedFile(f'{slug}-unidad-{unit["number"]}-documento.html', self.media_type, content.encode("utf-8"))
