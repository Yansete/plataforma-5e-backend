/**
 * Documento de la unidad (HTML): todos los recursos aprobados en el orden de la clase, con sus
 * alternativas y la evidencia del material. Se abre en el navegador y se puede guardar como PDF.
 * Moodle y Chamilo solo importan preguntas; este documento sirve para todo lo demás.
 */
import { GROUPS, typeInfo } from '@/features/generation/model/resourceCatalog';
import { escapeXml as esc, exportedOptions } from '@/features/export/model/fileBuilders';
import { citedEvidence } from '@/features/review/model/reviewRules';
import type { Course, Evidence, Resource, Unit } from '@/shared/types/domain';

const LETTERS = 'abcdefghij';

function paragraphs(text: string): string {
  return text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${esc(p).replace(/\n/g, '<br>')}</p>`)
    .join('');
}

function shorten(text: string, max = 420): string {
  return text.length > max ? `${text.slice(0, max).trimEnd()}…` : text;
}

/** Enlaces http(s) solamente: el documento no debe abrir otra cosa. */
function safeUrl(url: string | null | undefined): string | null {
  return url && /^https?:\/\//i.test(url) ? url : null;
}

function source(e: Evidence): string {
  const url = safeUrl(e.sourceUrl);
  const name = esc(e.documentName || 'Material de la unidad');
  const where = e.location ? `, ${esc(e.location)}` : '';
  const link = url ? ` · <a href="${esc(url)}">fuente</a>${e.license ? ` (${esc(e.license)})` : ''}` : '';
  return `<span class="src">${name}${where}${link}</span>`;
}

function resourceHtml(r: Resource, outcomeCode: (id: string) => string): string {
  const options = r.options ? exportedOptions(r) : null;
  const evidence = citedEvidence(r)
    .map((c) => `<li><strong>${esc(c.claim)}</strong><ul>${c.evidence
      .map((e) => `<li><span class="quote">«${esc(shorten(e.text))}»</span> ${source(e)}</li>`)
      .join('')}</ul></li>`)
    .join('');
  const meta = [typeInfo(r.type).singular, outcomeCode(r.outcomeId), r.edited ? 'editado por el docente' : ''].filter(Boolean).join(' · ');
  return `<article>
  <h3>${esc(r.title)}</h3>
  <p class="meta">${esc(meta)}</p>
  ${paragraphs(r.body)}
  ${options ? `<ol class="options">${options
    .map((o, i) => `<li><span class="letter">${LETTERS[i]})</span> ${esc(o.text)}${o.isCorrect ? ' <strong class="key">(respuesta correcta)</strong>' : ''}${o.feedback ? `<div class="feedback">${esc(o.feedback)}</div>` : ''}</li>`)
    .join('')}</ol>` : ''}
  ${evidence ? `<details open><summary>Evidencia del material</summary><ul class="evidence">${evidence}</ul></details>` : ''}
</article>`;
}

export function buildUnitDocument(resources: Resource[], course: Course, unit: Unit, date = new Date()): string {
  const approved = resources.filter((r) => r.status === 'aprobado');
  const outcomeCode = (id: string) => unit.outcomes.find((o) => o.id === id)?.code ?? '';
  const sections = GROUPS.map((group) => {
    const items = approved.filter((r) => typeInfo(r.type).group === group);
    if (!items.length) return '';
    return `<section><h2>${esc(group)}</h2>${items.map((r) => resourceHtml(r, outcomeCode)).join('\n')}</section>`;
  })
    .filter(Boolean)
    .join('\n');
  const licensed = approved.some((r) => r.evidence.some((e) => safeUrl(e.sourceUrl)));
  const outcomes = unit.outcomes.map((o) => `<li><strong>${esc(o.code)}</strong> ${esc(o.text)}</li>`).join('');
  const day = date.toLocaleDateString('es-PE', { year: 'numeric', month: 'long', day: 'numeric' });
  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>${esc(course.code)} · Unidad ${unit.number}: ${esc(unit.title)}</title>
<style>
body{font-family:Georgia,'Times New Roman',serif;max-width:820px;margin:32px auto;padding:0 20px;color:#1a211e;line-height:1.55}
h1{font-size:26px;margin:4px 0}h2{font-size:21px;border-bottom:2px solid #1f5c4a;padding-bottom:4px;margin-top:36px}
h3{font-size:17px;margin:22px 0 4px}.meta,.src{color:#4a544f;font-size:13px}.overline{font-size:13px;letter-spacing:.06em;text-transform:uppercase;color:#4a544f}
article{page-break-inside:avoid;border-left:3px solid #dcd7cc;padding-left:14px}.options{list-style:none;padding-left:0}
.options li{margin:6px 0}.letter{font-weight:bold}.key{color:#1f5c4a}.feedback{font-size:13px;color:#4a544f;margin-left:22px}
.evidence{font-size:13px}.quote{font-style:italic}details summary{cursor:pointer;font-size:14px;color:#1f5c4a}
.outcomes{font-size:14px}footer{margin-top:40px;font-size:12px;color:#4a544f;border-top:1px solid #dcd7cc;padding-top:8px}
</style>
</head>
<body>
<p class="overline">${esc(course.code)} · ${esc(course.name)} · ${esc(course.term)}</p>
<h1>Unidad ${unit.number}: ${esc(unit.title)}</h1>
<p class="meta">${approved.length} ${approved.length === 1 ? 'recurso aprobado' : 'recursos aprobados'} por el docente · ${esc(day)}</p>
${outcomes ? `<ul class="outcomes">${outcomes}</ul>` : ''}
${sections || '<p>No hay recursos aprobados.</p>'}
<footer>Recursos preparados con el material del docente y revisados por el docente antes de su uso.${licensed ? ' Los textos tomados de fuentes abiertas indican su enlace y su licencia junto a cada cita.' : ''}</footer>
</body>
</html>
`;
}
