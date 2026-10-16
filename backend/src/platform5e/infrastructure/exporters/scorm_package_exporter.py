"""Exportador SCORM 1.2 para Chamilo (Lecciones → Importar AICC, SCORM y Chamilo).

Cada recurso aprobado es un SCO: una página HTML propia, en el orden de la clase 5E. Las páginas de
contenido se marcan «completadas» al abrirse; los ítems de opción múltiple se califican en la página
y envían el puntaje al LMS con la API de SCORM 1.2. Todo va en la raíz del .zip, sin carpeta contenedora.
"""
from __future__ import annotations

import html
import io
import re
import zipfile
from collections.abc import Mapping, Sequence

from platform5e.application.ports.outbound.unit_exporter_port import ExportedFile, UnitExporterPort

STAGE_ORDER = ("engage", "explore", "explain", "elaborate", "evaluate")
STAGE_LABELS = {
    "engage": "Para iniciar la clase",
    "explore": "Para explorar",
    "explain": "Para explicar",
    "elaborate": "Para aplicar",
    "evaluate": "Para evaluar",
}
# Quitar "descartado" cuando los valores guardados estén migrados al inglés.
DISCARDED = {"discarded", "descartado"}
LETTERS = "abcdefghij"
FIXED_DATE = (2026, 1, 1, 0, 0, 0)  # fecha fija en el zip: el mismo contenido da el mismo archivo


def _esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _paragraphs(text: str) -> str:
    parts = [p.strip() for p in re.split(r"\n{2,}", text or "") if p.strip()]
    return "".join(f"<p>{_esc(p).replace(chr(10), '<br>')}</p>" for p in parts)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-") or "unidad"


def _exported_options(resource: Mapping) -> list[Mapping]:
    """La clave y los distractores aceptados o editados; los descartados no se exportan."""
    return [o for o in (resource.get("options") or []) if o.get("isCorrect") or o.get("decision") not in DISCARDED]


def _sources(resource: Mapping) -> str:
    seen, items = set(), []
    for evidence in resource.get("evidence") or []:
        label = ", ".join(x for x in (evidence.get("documentName"), evidence.get("location")) if x)
        if label and label not in seen:
            seen.add(label)
            items.append(f"<li>{_esc(label)}</li>")
    return f'<footer><h2>Fuentes del material</h2><ul>{"".join(items)}</ul></footer>' if items else ""


def _question(options: list[Mapping]) -> str:
    choices = "".join(
        f'<label class="choice"><input type="radio" name="answer" value="{i}" '
        f'data-correct="{"true" if o.get("isCorrect") else "false"}" data-feedback="{_esc(o.get("feedback"))}"> '
        f"<span>{LETTERS[i]}) {_esc(o.get('text'))}</span></label>"
        for i, o in enumerate(options)
    )
    return (
        '<form id="question"><fieldset><legend>Elige una respuesta</legend>'
        f"{choices}</fieldset>"
        '<button type="submit">Comprobar</button><p class="feedback" role="status" aria-live="polite"></p></form>'
    )


def _sco_page(resource: Mapping) -> str:
    options = _exported_options(resource) if resource.get("options") else []
    kind = "question" if options else "content"
    stage = STAGE_LABELS.get(resource.get("stage", ""), "")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(resource.get("title"))}</title>
<link rel="stylesheet" href="../shared/style.css">
<script src="../shared/scorm.js"></script>
</head>
<body data-kind="{kind}">
<main>
<p class="stage">{_esc(stage)}</p>
<h1>{_esc(resource.get("title"))}</h1>
{_paragraphs(resource.get("body", ""))}
{_question(options) if options else ""}
{_sources(resource)}
</main>
</body>
</html>
"""


def _manifest(package_id: str, title: str, pages: list[tuple[str, str]]) -> str:
    items = "".join(
        f'\n      <item identifier="ITEM_{n}" identifierref="RES_{n}" isvisible="true"><title>{_esc(t)}</title></item>'
        for n, (_, t) in enumerate(pages, start=1)
    )
    resources = "".join(
        f'\n    <resource identifier="RES_{n}" type="webcontent" adlcp:scormtype="sco" href="{href}">'
        f'<file href="{href}"/><dependency identifierref="SHARED"/></resource>'
        for n, (href, _) in enumerate(pages, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="{package_id}" version="1.0"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata><schema>ADL SCORM</schema><schemaversion>1.2</schemaversion></metadata>
  <organizations default="ORG_1">
    <organization identifier="ORG_1">
      <title>{_esc(title)}</title>{items}
    </organization>
  </organizations>
  <resources>{resources}
    <resource identifier="SHARED" type="webcontent" adlcp:scormtype="asset">
      <file href="shared/scorm.js"/><file href="shared/style.css"/>
    </resource>
  </resources>
</manifest>
"""


SCORM_JS = r"""/* API de SCORM 1.2: busca el objeto API que expone el LMS en las ventanas superiores. */
(function () {
  'use strict';
  function findApi(win) {
    for (var i = 0; win && i < 10; i++) {
      if (win.API) return win.API;
      if (win.parent === win) break;
      win = win.parent;
    }
    return null;
  }
  var api = findApi(window) || (window.opener ? findApi(window.opener) : null);
  var finished = false;

  function setValue(name, value) { if (api) api.LMSSetValue(name, String(value)); }

  function start() {
    if (!api) return; // fuera del LMS (vista previa local) la página funciona igual
    api.LMSInitialize('');
    var status = api.LMSGetValue('cmi.core.lesson_status');
    if (document.body.getAttribute('data-kind') === 'content') setValue('cmi.core.lesson_status', 'completed');
    else if (!status || status === 'not attempted') setValue('cmi.core.lesson_status', 'incomplete');
    api.LMSCommit('');
  }

  function finish() {
    if (!api || finished) return;
    finished = true;
    api.LMSCommit('');
    api.LMSFinish('');
  }

  function grade(event) {
    event.preventDefault();
    var form = event.currentTarget;
    var chosen = form.querySelector('input[name="answer"]:checked');
    var out = form.querySelector('.feedback');
    if (!chosen) { out.textContent = 'Elige una alternativa.'; return; }
    var correct = chosen.getAttribute('data-correct') === 'true';
    // La retroalimentación puede empezar con «Correcto.» o «Incorrecto.»: se quita para no repetirlo.
    var note = (chosen.getAttribute('data-feedback') || '').replace(/^\s*(in)?correcto[.:,]?\s*/i, '');
    out.textContent = (correct ? 'Correcto. ' : 'Incorrecto. ') + note;
    out.className = 'feedback ' + (correct ? 'is-correct' : 'is-wrong');
    setValue('cmi.core.score.min', 0);
    setValue('cmi.core.score.max', 100);
    setValue('cmi.core.score.raw', correct ? 100 : 0);
    setValue('cmi.core.lesson_status', correct ? 'passed' : 'failed');
    if (api) api.LMSCommit('');
  }

  window.addEventListener('load', function () {
    start();
    var form = document.getElementById('question');
    if (form) form.addEventListener('submit', grade);
  });
  window.addEventListener('pagehide', finish);
  window.addEventListener('beforeunload', finish);
})();
"""

STYLE_CSS = """body{margin:0;font-family:Georgia,'Times New Roman',serif;color:#1f2328;background:#fff;line-height:1.6}
main{max-width:46rem;margin:0 auto;padding:1.5rem 1rem 3rem}
h1{font-size:1.6rem;line-height:1.25;margin:.25rem 0 1rem}
.stage{margin:0;font:600 .8rem/1.4 system-ui,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:#5b6470}
fieldset{border:1px solid #d0d7de;border-radius:8px;padding:1rem;margin:1.5rem 0 1rem}
legend{font:600 .95rem system-ui,sans-serif;padding:0 .25rem}
.choice{display:flex;gap:.5rem;align-items:flex-start;padding:.4rem 0;cursor:pointer}
button{font:600 1rem system-ui,sans-serif;padding:.6rem 1.2rem;border:0;border-radius:6px;background:#1f5fae;color:#fff;cursor:pointer}
.feedback{min-height:1.5rem;font-family:system-ui,sans-serif}
.is-correct{color:#1a7f37}.is-wrong{color:#b42318}
footer{margin-top:2.5rem;border-top:1px solid #d0d7de;font:.85rem/1.5 system-ui,sans-serif;color:#5b6470}
footer h2{font-size:.85rem;margin:1rem 0 .25rem}
"""


class ScormPackageExporter(UnitExporterPort):
    """Implementa ResourceExporterPort para el formato SCORM 1.2 (.zip)."""

    format = "scorm_zip"
    media_type = "application/zip"

    def supports(self, resource: Mapping) -> bool:
        return True  # cada recurso aprobado es una página de la lección

    def export(self, resources: Sequence[Mapping], course: Mapping, unit: Mapping) -> ExportedFile:
        ordered = sorted(
            resources,
            key=lambda r: (STAGE_ORDER.index(r["stage"]) if r.get("stage") in STAGE_ORDER else 99, r.get("createdAt", "")),
        )
        number = unit.get("number", "")
        title = f"{course.get('code', '')} · Unidad {number}: {unit.get('title', '')}".strip()
        pages = [(f"sco/{n:02d}.html", r.get("title") or f"Recurso {n}") for n, r in enumerate(ordered, start=1)]
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
            def add(name: str, text: str) -> None:
                package.writestr(zipfile.ZipInfo(name, FIXED_DATE), text.encode("utf-8"), zipfile.ZIP_DEFLATED)

            add("imsmanifest.xml", _manifest(f"PKG_{_slug(course.get('code', ''))}_U{number}".replace("-", "_"), title, pages))
            add("shared/scorm.js", SCORM_JS)
            add("shared/style.css", STYLE_CSS)
            for (href, _), resource in zip(pages, ordered):
                add(href, _sco_page(resource))
        file_name = f"{_slug(course.get('code', ''))}-unidad-{number}-scorm.zip"
        return ExportedFile(file_name, self.media_type, buffer.getvalue())
