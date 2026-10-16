/** Descargas: nombres con el curso, archivos para Moodle y Chamilo, documento de la unidad e historial. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { clearDownloads, listDownloads, registerDownload } from '@/features/export/api/exportApi';
import { buildFile } from '@/features/export/model/buildFile';
import { FORMATS, fileNameFor, formatInfo, isQuestion, resourcesFor, slug } from '@/features/export/model/exportFormats';
import { buildUnitDocument } from '@/features/export/model/unitDocument';
import { buildMoodleXml, exportedOptions } from '@/features/export/model/fileBuilders';
import { decideOption, setStatus } from '@/features/review/model/reviewRules';
import { course, item, mockFetch, text, unit } from '@/test/fixtures';
import type { Resource } from '@/shared/types/domain';

afterEach(() => vi.unstubAllGlobals());

/** Pregunta aprobada: B y C aceptados, D descartado. */
function approvedItem(overrides: Partial<Resource> = {}): Resource {
  let r = item(overrides);
  r = decideOption(decideOption(decideOption(r, 'b', 'aceptado'), 'c', 'aceptado'), 'd', 'descartado', 'duplicado');
  return setStatus(r, 'aprobado');
}

describe('nombres y formatos', () => {
  it('el nombre del archivo lleva el curso y la unidad', () => {
    expect(slug('  Redes & Comunicación 2026  ')).toBe('redes-comunicacion-2026');
    expect(fileNameFor({ code: 'RED-301' }, { number: 1 }, 'moodle_xml')).toBe('red-301-unidad-1-moodle.xml');
    expect(fileNameFor({ code: 'RED-301' }, { number: 2 }, 'scorm_zip')).toBe('red-301-unidad-2-scorm.zip');
    expect(fileNameFor({ code: '***' }, { number: 3 }, 'documento')).toBe('curso-unidad-3-documento.html');
    expect(FORMATS.map((f) => f.title)).toEqual(['Moodle', 'Chamilo', 'Documento de la unidad']);
    expect(formatInfo('scorm_zip').extension).toBe('zip');
  });

  it('Moodle y Chamilo reciben solo preguntas aprobadas; el documento, todo lo aprobado', () => {
    const list = [approvedItem(), item({ id: 'pend' }), text({ status: 'aprobado' })];
    expect(isQuestion(list[2])).toBe(false);
    expect(resourcesFor('moodle_xml', list).map((r) => r.id)).toEqual(['r1']);
    expect(resourcesFor('documento', list).map((r) => r.id)).toEqual(['r1', 'r2']);
  });
});

describe('archivos', () => {
  it('Moodle XML: la clave con 100 % y solo los distractores no descartados', () => {
    const r = approvedItem({ title: 'TCP & UDP', body: 'Enunciado <b>' });
    expect(exportedOptions(r).map((o) => o.id)).toEqual(['a', 'b', 'c']);
    const xml = buildMoodleXml([r], 'RED-301 · Unidad 1');
    expect(xml.startsWith('<?xml')).toBe(true);
    expect(xml).toContain('<text>$course$/top/RED-301 · Unidad 1</text>');
    expect(xml).toContain('<name><text>TCP &amp; UDP</text></name>');
    expect(xml.match(/fraction="100"/g)).toHaveLength(1);
    expect(xml.match(/<answer /g)).toHaveLength(3);
    expect(xml).toContain('Enunciado &lt;b&gt;');
    expect(xml).not.toContain('<p>DNS</p>');
    expect(buildMoodleXml([])).toContain('Plataforma Docente');
  });

  it('arma cada formato con el nombre correcto', () => {
    const list = [approvedItem(), text({ status: 'aprobado' })];
    const moodle = buildFile('moodle_xml', list, course(), unit());
    expect(moodle).toMatchObject({ fileName: 'red-301-unidad-1-moodle.xml', mimeType: 'application/xml', resourceCount: 1 });
    const html = buildFile('documento', list, course(), unit(), new Date(2026, 9, 10));
    expect(html).toMatchObject({ fileName: 'red-301-unidad-1-documento.html', mimeType: 'text/html', resourceCount: 2 });
  });
});

describe('documento de la unidad', () => {
  it('ordena por momento de la clase, escapa el texto y cita las fuentes', () => {
    const html = buildUnitDocument([approvedItem(), text({ status: 'aprobado' }), text({ id: 'no', status: 'pendiente', title: 'Pendiente' })], course(), unit(), new Date(2026, 9, 10));
    expect(html.indexOf('<h2>Para explicar</h2>')).toBeGreaterThan(-1);
    expect(html.indexOf('<h2>Para explicar</h2>')).toBeLessThan(html.indexOf('<h2>Para evaluar</h2>'));
    expect(html).not.toContain('Pendiente');
    expect(html).toContain('Segundo &lt;párrafo&gt;');
    expect(html).toContain('(respuesta correcta)');
    expect(html).toContain('<a href="https://es.example.org/wiki/UDP">fuente</a> (CC BY-SA 4.0)');
    expect(html).toContain('2 recursos aprobados');
    expect(html).toContain('RED-301 · Unidad 1');
    expect(html).not.toMatch(/5E|Wikipedia|Gemini/);
  });

  it('sin fuentes abiertas no agrega la nota de licencias', () => {
    const local = text({ status: 'aprobado', evidence: [{ ...item().evidence[0] }], citations: [{ claim: 'TCP', fragmentIds: ['f1'] }] });
    const html = buildUnitDocument([local], course({ sumilla: '' }), unit({ outcomes: [] }), new Date(2026, 9, 10));
    expect(html).not.toContain('licencia');
    expect(html).toContain('1 recurso aprobado');
    expect(buildUnitDocument([], course(), unit())).toContain('No hay recursos aprobados.');
    const unsafe = text({ status: 'aprobado', evidence: [{ ...item().evidence[1], sourceUrl: 'javascript:alert(1)' }], citations: [{ claim: 'UDP', fragmentIds: ['f2'] }] });
    expect(buildUnitDocument([unsafe], course(), unit())).not.toContain('javascript:');
  });
});

describe('historial', () => {
  it('lista, registra y borra las descargas de la unidad', async () => {
    const calls = mockFetch({ body: [] }, { status: 201, body: { id: 'x' } }, { status: 204 });
    await listDownloads('u1');
    await registerDownload('u1', { fileName: 'red-301-unidad-1-moodle.xml', resourceCount: 2 }, 'moodle_xml');
    await clearDownloads('u1');
    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/v1/unidades/u1/descargas', 'POST /api/v1/unidades/u1/descargas', 'DELETE /api/v1/unidades/u1/descargas']);
    expect(calls[1].body).toEqual({ format: 'moodle_xml', fileName: 'red-301-unidad-1-moodle.xml', resourceCount: 2 });
  });
});
