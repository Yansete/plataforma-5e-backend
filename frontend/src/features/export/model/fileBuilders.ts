/**
 * Archivos para Moodle y Chamilo (HU-054, ADR-005).
 *
 * La IA nunca escribe XML: se arma aquí con plantillas fijas a partir de los recursos aprobados.
 *  - Moodle XML (<quiz>): misma estructura que `generar_moodle_xml` del backend (HU-043) y que la
 *    muestra importada con éxito en SP-003 (backend/tests/data/muestra_moodle_verificada.xml).
 *  - QTI 2.1 (Chamilo): un `assessmentItem` con `choiceInteraction` por ítem y un `imsmanifest.xml`,
 *    empaquetados en ZIP.
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

/** Identificador válido para QTI (NCName): letras, dígitos, guion y guion bajo; no empieza con dígito. */
export function qtiIdentifier(value: string): string {
  const clean = value.replace(/[^A-Za-z0-9_-]/g, '_');
  return /^[A-Za-z_]/.test(clean) ? clean : `i_${clean}`;
}

export function qti21FileName(resource: Resource): string {
  return `${qtiIdentifier(resource.id)}.xml`;
}

export function buildQti21Item(resource: Resource): string {
  const id = qtiIdentifier(resource.id);
  const options = exportedOptions(resource);
  const correct = options.find((o) => o.isCorrect);
  const choiceId = (o: ItemOption) => qtiIdentifier(`opcion_${o.id}`);
  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"',
    '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
    '  xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/qti/qtiv2p1/imsqti_v2p1.xsd"',
    `  identifier="${id}" title="${escapeXml(resource.title)}" adaptive="false" timeDependent="false">`,
    '  <responseDeclaration identifier="RESPONSE" cardinality="single" baseType="identifier">',
    '    <correctResponse>',
    `      <value>${correct ? choiceId(correct) : ''}</value>`,
    '    </correctResponse>',
    '  </responseDeclaration>',
    '  <outcomeDeclaration identifier="SCORE" cardinality="single" baseType="float">',
    '    <defaultValue><value>0</value></defaultValue>',
    '  </outcomeDeclaration>',
    '  <outcomeDeclaration identifier="FEEDBACK" cardinality="single" baseType="identifier"/>',
    '  <itemBody>',
    `    <div>${toHtml(resource.body)}</div>`,
    '    <choiceInteraction responseIdentifier="RESPONSE" shuffle="true" maxChoices="1">',
    ...options.map((o) => `      <simpleChoice identifier="${choiceId(o)}">${escapeXml(o.text)}</simpleChoice>`),
    '    </choiceInteraction>',
    '  </itemBody>',
    '  <responseProcessing template="http://www.imsglobal.org/question/qti_v2p1/rptemplates/match_correct"/>',
    ...options
      .filter((o) => o.feedback.trim())
      .map(
        (o) =>
          `  <modalFeedback outcomeIdentifier="FEEDBACK" identifier="${choiceId(o)}" showHide="show">${escapeXml(o.feedback)}</modalFeedback>`,
      ),
    '</assessmentItem>',
  ];
  return lines.join('\n');
}

export function buildQti21Manifest(resources: Resource[], packageId = 'plataforma-docente'): string {
  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    `<manifest xmlns="http://www.imsglobal.org/xsd/imscp_v1p1" identifier="${qtiIdentifier(packageId)}"`,
    '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
    '  xsi:schemaLocation="http://www.imsglobal.org/xsd/imscp_v1p1 http://www.imsglobal.org/xsd/imscp_v1p1.xsd">',
    '  <metadata>',
    '    <schema>IMS Content</schema>',
    '    <schemaversion>1.1</schemaversion>',
    '  </metadata>',
    '  <organizations/>',
    '  <resources>',
    ...resources.flatMap((r) => [
      `    <resource identifier="${qtiIdentifier(`res_${r.id}`)}" type="imsqti_item_xmlv2p1" href="${qti21FileName(r)}">`,
      `      <file href="${qti21FileName(r)}"/>`,
      '    </resource>',
    ]),
    '  </resources>',
    '</manifest>',
  ];
  return lines.join('\n');
}

/* ---------- ZIP sin compresión (método «stored»), suficiente para el paquete QTI ---------- */

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

export function crc32(data: Uint8Array): number {
  let crc = 0xffffffff;
  for (let i = 0; i < data.length; i++) crc = CRC_TABLE[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

/** Crea un ZIP con los archivos dados (texto UTF-8). */
export function createZip(files: { name: string; content: string }[], date = new Date()): Uint8Array {
  const encoder = new TextEncoder();
  const dosTime = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
  const dosDate = ((date.getFullYear() - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  const locals: Uint8Array[] = [];
  const centrals: Uint8Array[] = [];
  let offset = 0;

  for (const file of files) {
    const name = encoder.encode(file.name);
    const data = encoder.encode(file.content);
    const crc = crc32(data);

    const local = new Uint8Array(30 + name.length + data.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 0x04034b50, true);
    lv.setUint16(4, 20, true);
    lv.setUint16(6, 0x0800, true); // nombres en UTF-8
    lv.setUint16(8, 0, true); // sin compresión
    lv.setUint16(10, dosTime, true);
    lv.setUint16(12, dosDate, true);
    lv.setUint32(14, crc, true);
    lv.setUint32(18, data.length, true);
    lv.setUint32(22, data.length, true);
    lv.setUint16(26, name.length, true);
    lv.setUint16(28, 0, true);
    local.set(name, 30);
    local.set(data, 30 + name.length);

    const central = new Uint8Array(46 + name.length);
    const cv = new DataView(central.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(4, 20, true);
    cv.setUint16(6, 20, true);
    cv.setUint16(8, 0x0800, true);
    cv.setUint16(10, 0, true);
    cv.setUint16(12, dosTime, true);
    cv.setUint16(14, dosDate, true);
    cv.setUint32(16, crc, true);
    cv.setUint32(20, data.length, true);
    cv.setUint32(24, data.length, true);
    cv.setUint16(28, name.length, true);
    cv.setUint32(42, offset, true);
    central.set(name, 46);

    locals.push(local);
    centrals.push(central);
    offset += local.length;
  }

  const centralSize = centrals.reduce((n, c) => n + c.length, 0);
  const end = new Uint8Array(22);
  const ev = new DataView(end.buffer);
  ev.setUint32(0, 0x06054b50, true);
  ev.setUint16(8, files.length, true);
  ev.setUint16(10, files.length, true);
  ev.setUint32(12, centralSize, true);
  ev.setUint32(16, offset, true);

  const out = new Uint8Array(offset + centralSize + end.length);
  let pos = 0;
  for (const part of [...locals, ...centrals, end]) {
    out.set(part, pos);
    pos += part.length;
  }
  return out;
}

export function buildQti21Package(resources: Resource[], packageId?: string): Uint8Array {
  return createZip([
    { name: 'imsmanifest.xml', content: buildQti21Manifest(resources, packageId) },
    ...resources.map((r) => ({ name: qti21FileName(r), content: buildQti21Item(r) })),
  ]);
}
