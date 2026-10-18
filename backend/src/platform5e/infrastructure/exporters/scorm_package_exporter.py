"""Exportador SCORM 1.2 multirrecurso para Chamilo, Canvas y cualquier LMS compatible con SCORM 1.2.

Cada recurso aprobado es un SCO: una página HTML propia, en el orden de la clase 5E, con sus archivos (gráficos SVG,
imágenes y audios) dentro del paquete y declarados en el manifiesto. Las páginas de contenido se marcan «completadas»
al abrirse; las preguntas y las actividades interactivas se califican en la página y envían el puntaje al LMS con la
API de SCORM 1.2. Todo va en la raíz del .zip, sin carpeta contenedora.
"""
from __future__ import annotations

import html
import io
import json
import re
import zipfile
from collections.abc import Mapping, Sequence

from platform5e.application.ports.outbound.unit_exporter_port import ExportedFile, UnitExporterPort
from platform5e.domain.generation.resource_formats import AUDIO, IMAGE, INTERACTIVE, VISUAL, resource_format
from platform5e.infrastructure.exporters.visual_renderer import SvgVisualRenderer, can_render
from platform5e.infrastructure.html_sanitizer import clean_html

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


def body_html(resource: Mapping) -> str:
    """El texto con formato del editor (limpio) o, si no se editó, los párrafos del texto generado."""
    formatted = clean_html(resource.get("bodyHtml"))
    return formatted or _paragraphs(resource.get("body", ""))


def _json_for_script(value: object) -> str:
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def media_files(resource: Mapping, number: int) -> list[tuple[str, bytes]]:
    """Archivos del recurso dentro del paquete: el gráfico SVG o el archivo generado (imagen o audio)."""
    stored = resource.get("mediaFile")
    if stored:
        extension = str(stored.get("fileName", "")).rsplit(".", 1)[-1].lower() or "bin"
        return [(f"media/{number:02d}.{extension}", stored["content"])]
    kind = resource_format(resource.get("type", ""))
    if kind in (VISUAL, IMAGE) and can_render(resource.get("type", "")) and resource.get("structure"):
        return [(f"media/{number:02d}.svg", SvgVisualRenderer().render(resource).encode("utf-8"))]
    return []


def _media_block(resource: Mapping, files: list[tuple[str, bytes]]) -> str:
    kind = resource_format(resource.get("type", ""))
    structure = resource.get("structure") or {}
    if kind in (VISUAL, IMAGE) and files:
        alt = structure.get("alt") or resource.get("title")
        caption = structure.get("caption") if kind == IMAGE else ""
        figcaption = f"<figcaption>{_esc(caption)}</figcaption>" if caption else ""
        return f'<figure class="visual"><img src="../{files[0][0]}" alt="{_esc(alt)}">{figcaption}</figure>'
    if kind == AUDIO:
        script = structure.get("script") or resource.get("body", "")
        player = (
            f'<audio controls preload="metadata" src="../{files[0][0]}"></audio>'
            if files
            else '<button type="button" class="speak" data-speak="script">Escuchar con la voz del navegador</button>'
        )
        return (
            f'<section class="audio">{player}'
            f'<details{" open" if not files else ""}><summary>Guion del audio</summary>'
            f'<p id="script">{_esc(script)}</p></details></section>'
        )
    if kind == INTERACTIVE:
        data = {"type": resource.get("type"), "structure": structure}
        return (
            '<form id="activity" class="activity"><div class="activity__items"></div>'
            '<button type="submit">Comprobar</button><p class="feedback" role="status" aria-live="polite"></p></form>'
            f'<script type="application/json" id="activity-data">{_json_for_script(data)}</script>'
        )
    return ""


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


def _sco_page(resource: Mapping, files: list[tuple[str, bytes]] | None = None) -> str:
    options = _exported_options(resource) if resource.get("options") else []
    is_activity = resource_format(resource.get("type", "")) == INTERACTIVE
    kind = "question" if options else "activity" if is_activity else "content"
    stage = STAGE_LABELS.get(resource.get("stage", ""), "")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(resource.get("title"))}</title>
<link rel="stylesheet" href="../shared/style.css">
<script src="../shared/scorm.js"></script>
<script src="../shared/activity.js"></script>
</head>
<body data-kind="{kind}">
<main>
<p class="stage">{_esc(stage)}</p>
<h1>{_esc(resource.get("title"))}</h1>
{body_html(resource)}
{_media_block(resource, files or [])}
{_question(options) if options else ""}
{_sources(resource)}
</main>
</body>
</html>
"""


def _file_tags(names: list[str]) -> str:
    return "".join('<file href="' + name + '"/>' for name in names)


def _manifest(package_id: str, title: str, pages: list[tuple[str, str]], files: list[list[str]] | None = None) -> str:
    files = files or [[] for _ in pages]
    items = "".join(
        f'\n      <item identifier="ITEM_{n}" identifierref="RES_{n}" isvisible="true"><title>{_esc(t)}</title></item>'
        for n, (_, t) in enumerate(pages, start=1)
    )
    resources = "".join(
        f'\n    <resource identifier="RES_{n}" type="webcontent" adlcp:scormtype="sco" href="{href}">'
        f'<file href="{href}"/>{_file_tags(extra)}<dependency identifierref="SHARED"/></resource>'
        for n, ((href, _), extra) in enumerate(zip(pages, files), start=1)
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
      <file href="shared/scorm.js"/><file href="shared/style.css"/><file href="shared/activity.js"/>
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

  function report(percent) {
    setValue('cmi.core.score.min', 0);
    setValue('cmi.core.score.max', 100);
    setValue('cmi.core.score.raw', Math.round(percent));
    setValue('cmi.core.lesson_status', percent >= 60 ? 'passed' : 'failed');
    if (api) api.LMSCommit('');
  }
  window.scorm5e = { report: report };

  function speak(button) {
    var target = document.getElementById(button.getAttribute('data-speak'));
    if (!target || !window.speechSynthesis) { button.textContent = 'Este navegador no puede leer el guion en voz alta.'; return; }
    window.speechSynthesis.cancel();
    var utterance = new SpeechSynthesisUtterance(target.textContent);
    utterance.lang = 'es-ES';
    window.speechSynthesis.speak(utterance);
  }

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
    var buttons = document.querySelectorAll('[data-speak]');
    for (var i = 0; i < buttons.length; i++) buttons[i].addEventListener('click', function (e) { speak(e.currentTarget); });
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
figure.visual{margin:1.5rem 0}figure.visual img{max-width:100%;height:auto;border:1px solid #d0d7de;border-radius:8px}
figcaption{font:.9rem/1.4 system-ui,sans-serif;color:#5b6470;margin-top:.5rem}
.audio{margin:1.5rem 0}.audio audio{width:100%}.audio summary{cursor:pointer;font:600 .95rem system-ui,sans-serif}
.speak{margin-bottom:.75rem}
.activity__items{display:grid;gap:.75rem;margin:1.5rem 0 1rem}
.row{border:1px solid #d0d7de;border-radius:8px;padding:.75rem;font-family:system-ui,sans-serif}
.row select,.row input[type=text]{font:1rem system-ui,sans-serif;padding:.35rem;margin-top:.35rem;max-width:100%}
.row .note{display:block;font-size:.9rem;margin-top:.35rem}
.row--ok{border-color:#1a7f37}.row--bad{border-color:#b42318}
.order{display:flex;gap:.5rem;align-items:center}.order span{flex:1}
.order button{padding:.2rem .6rem;background:#eef2f6;color:#1f2328}
h2,h3{font-family:system-ui,sans-serif}
"""

ACTIVITY_JS = r"""/* Actividades interactivas: emparejar, verdadero o falso, completar y ordenar. Envían el puntaje con scorm5e. */
(function () {
  'use strict';
  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    for (var key in attrs) node.setAttribute(key, attrs[key]);
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function shuffle(list) {
    var copy = list.slice();
    for (var i = copy.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = copy[i]; copy[i] = copy[j]; copy[j] = t; }
    return copy;
  }
  function norm(text) {
    return String(text || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9ñ ]/g, ' ').replace(/\s+/g, ' ').trim();
  }
  function mark(row, ok, note) {
    row.className = 'row ' + (ok ? 'row--ok' : 'row--bad');
    var out = row.querySelector('.note') || row.appendChild(el('span', { 'class': 'note' }));
    out.textContent = (ok ? 'Correcto. ' : 'Revisa: ') + (note || '');
  }

  var builders = {
    emparejamiento: function (s, box) {
      var definitions = shuffle(s.pairs.map(function (p) { return p.definition; }));
      return s.pairs.map(function (pair, i) {
        var row = el('div', { 'class': 'row' });
        var id = 'm' + i;
        row.appendChild(el('label', { 'for': id }, pair.term));
        var select = el('select', { id: id });
        select.appendChild(el('option', { value: '' }, 'Elige la descripción…'));
        definitions.forEach(function (d) { select.appendChild(el('option', { value: d }, d)); });
        row.appendChild(select);
        box.appendChild(row);
        return function () { var ok = select.value === pair.definition; mark(row, ok, ok ? '' : pair.definition); return ok; };
      });
    },
    verdadero_falso: function (s, box) {
      return s.statements.map(function (st, i) {
        var row = el('fieldset', { 'class': 'row' });
        row.appendChild(el('legend', {}, st.text));
        ['Verdadero', 'Falso'].forEach(function (label, k) {
          var wrap = el('label', { 'class': 'choice' });
          wrap.appendChild(el('input', { type: 'radio', name: 't' + i, value: k === 0 ? 'true' : 'false' }));
          wrap.appendChild(el('span', {}, label));
          row.appendChild(wrap);
        });
        box.appendChild(row);
        return function () {
          var chosen = row.querySelector('input:checked');
          var ok = !!chosen && (chosen.value === 'true') === st.isTrue;
          mark(row, ok, st.feedback || (st.isTrue ? 'Es verdadera.' : 'Es falsa.'));
          return ok;
        };
      });
    },
    completar_espacios: function (s, box) {
      return s.blanks.map(function (b, i) {
        var row = el('div', { 'class': 'row' });
        var id = 'c' + i;
        row.appendChild(el('label', { 'for': id }, b.sentence));
        var input = el('input', { type: 'text', id: id, autocomplete: 'off' });
        row.appendChild(input);
        box.appendChild(row);
        return function () { var ok = norm(input.value) === norm(b.answer); mark(row, ok, ok ? '' : 'La respuesta es «' + b.answer + '».'); return ok; };
      });
    },
    ordenar_pasos: function (s, box) {
      var list = el('ol', { 'class': 'activity__order' });
      shuffle(s.sequence).forEach(function (step) {
        var li = el('li', { 'class': 'row order' });
        li.appendChild(el('span', {}, step));
        var up = el('button', { type: 'button', 'aria-label': 'Subir' }, '↑');
        var down = el('button', { type: 'button', 'aria-label': 'Bajar' }, '↓');
        up.addEventListener('click', function () { if (li.previousSibling) list.insertBefore(li, li.previousSibling); });
        down.addEventListener('click', function () { if (li.nextSibling) list.insertBefore(li.nextSibling, li); });
        li.appendChild(up); li.appendChild(down);
        list.appendChild(li);
      });
      box.appendChild(list);
      return [function () {
        var items = list.querySelectorAll('li');
        var ok = true;
        for (var i = 0; i < items.length; i++) {
          var right = items[i].querySelector('span').textContent === s.sequence[i];
          items[i].className = 'row order ' + (right ? 'row--ok' : 'row--bad');
          ok = ok && right;
        }
        return ok;
      }];
    }
  };

  window.addEventListener('load', function () {
    var form = document.getElementById('activity');
    var data = document.getElementById('activity-data');
    if (!form || !data) return;
    var activity = JSON.parse(data.textContent);
    var build = builders[activity.type];
    if (!build) return;
    var checks = build(activity.structure, form.querySelector('.activity__items'));
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var right = checks.filter(function (check) { return check(); }).length;
      var percent = checks.length ? (100 * right) / checks.length : 0;
      var out = form.querySelector('.feedback');
      out.textContent = right + ' de ' + checks.length + ' correctas (' + Math.round(percent) + ' %).';
      out.className = 'feedback ' + (percent >= 60 ? 'is-correct' : 'is-wrong');
      if (window.scorm5e) window.scorm5e.report(percent);
    });
  });
})();
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
        files = [media_files(r, n) for n, r in enumerate(ordered, start=1)]
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
            def add(name: str, content: str | bytes) -> None:
                data = content.encode("utf-8") if isinstance(content, str) else content
                package.writestr(zipfile.ZipInfo(name, FIXED_DATE), data, zipfile.ZIP_DEFLATED)

            package_id = f"PKG_{_slug(course.get('code', ''))}_U{number}".replace("-", "_")
            add("imsmanifest.xml", _manifest(package_id, title, pages, [[name for name, _ in f] for f in files]))
            add("shared/scorm.js", SCORM_JS)
            add("shared/style.css", STYLE_CSS)
            add("shared/activity.js", ACTIVITY_JS)
            for (href, _), resource, resource_files in zip(pages, ordered, files):
                add(href, _sco_page(resource, resource_files))
                for name, content in resource_files:
                    add(name, content)
        file_name = f"{_slug(course.get('code', ''))}-unidad-{number}-scorm.zip"
        return ExportedFile(file_name, self.media_type, buffer.getvalue())
