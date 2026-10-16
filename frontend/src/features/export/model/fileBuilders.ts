/**
 * Archivo para Moodle (HU-054, ADR-005). El paquete de Chamilo (SCORM 1.2) lo arma el backend (ADR-007).
 *
 * La IA nunca escribe XML: se arma aquí con plantillas fijas a partir de los recursos aprobados.
 *  - Moodle XML (<quiz>): misma estructura que `generar_moodle_xml` del backend (HU-043) y que la
 *    muestra importada con éxito en SP-003 (backend/tests/data/muestra_moodle_verificada.xml).
 *
 * Solo se exportan los distractores que el docente aceptó o editó, más la clave.
 */
import type { ItemOption, Resource } from '@/shared/types/domain';

/** Escapa texto para atributos y nodos XML. */
export function escapeXml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}

/** Texto plano → HTML de párrafos, escapado. */
function toHtml(text: string): string {
  return text
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean)
    .map((p) => `<p>${escapeXml(p).replace(/\n/g, '<br/>')}</p>`)
    .join('');
}

/** Envuelve en CDATA sin romperse si el texto contiene «]]>». */
function cdata(value: string): string {
  return `<![CDATA[${value.split(']]>').join(']]]]><![CDATA[>')}]]>`;
}

/** Clave y distractores que se exportan: los descartados quedan fuera. */
export function exportedOptions(resource: Resource): ItemOption[] {
  return (resource.options ?? []).filter((o) => o.isCorrect || o.decision !== 'descartado');
}

/** Retroalimentación general: la evidencia citada, para que el estudiante sepa dónde repasar. */
function generalFeedback(resource: Resource): string {
  const claims = resource.citations.map((c) => c.claim).filter(Boolean);
  return claims.length ? `Para repasar: ${claims.join(' ')}` : '';
}

/** `category`: carpeta del banco de preguntas de Moodle donde quedan las preguntas importadas. */
export function buildMoodleXml(resources: Resource[], category = 'Plataforma Docente'): string {
  const xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<quiz>'];
  xml.push(
    `  <question type="category"><category><text>$course$/top/${escapeXml(category)}</text></category><info format="html"><text></text></info><idnumber></idnumber></question>`,
  );
  for (const r of resources) {
    xml.push('  <question type="multichoice">');
    xml.push(`    <name><text>${escapeXml(r.title)}</text></name>`);
    xml.push(`    <questiontext format="html"><text>${cdata(toHtml(r.body))}</text></questiontext>`);
    xml.push(`    <generalfeedback format="html"><text>${cdata(toHtml(generalFeedback(r)))}</text></generalfeedback>`);
    xml.push('    <defaultgrade>1.0000000</defaultgrade>');
    xml.push('    <penalty>0.3333333</penalty>');
    xml.push('    <hidden>0</hidden>');
    xml.push('    <idnumber></idnumber>');
    xml.push('    <single>true</single>');
    xml.push('    <shuffleanswers>true</shuffleanswers>');
    xml.push('    <answernumbering>abc</answernumbering>');
    xml.push('    <showstandardinstruction>0</showstandardinstruction>');
    xml.push(`    <correctfeedback format="html"><text>${cdata('<p>Respuesta correcta.</p>')}</text></correctfeedback>`);
    xml.push(`    <partiallycorrectfeedback format="html"><text>${cdata('<p>Respuesta parcialmente correcta.</p>')}</text></partiallycorrectfeedback>`);
    xml.push(`    <incorrectfeedback format="html"><text>${cdata('<p>Respuesta incorrecta.</p>')}</text></incorrectfeedback>`);
    xml.push('    <shownumcorrect/>');
    for (const o of exportedOptions(r)) {
      xml.push(`    <answer fraction="${o.isCorrect ? '100' : '0'}" format="html">`);
      xml.push(`      <text>${cdata(toHtml(o.text))}</text>`);
      xml.push(`      <feedback format="html"><text>${cdata(toHtml(o.feedback))}</text></feedback>`);
      xml.push('    </answer>');
    }
    xml.push('  </question>');
  }
  xml.push('</quiz>');
  return xml.join('\n');
}
