"""Documento HTML de la unidad: plantilla fija, recursos aprobados y evidencia del material."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
import re
from string import Template
import unicodedata

from platform5e.application.ports.outbound.unit_exporter_port import ExportedFile

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
    paragraphs = "".join(f'<p>{_esc(part.strip()).replace(chr(10), "<br>")}</p>'
                         for part in re.split(r"\n{2,}", resource.get("body", "")) if part.strip())
    return (f'<article>\n  <h3>{_esc(resource.get("title"))}</h3>\n  <p class="meta">{_esc(meta)}</p>\n'
            f'  {paragraphs}\n  {choices}\n  {evidence_html}\n</article>')


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
