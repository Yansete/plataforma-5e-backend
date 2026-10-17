/** Archivos solicitados al servidor: selección, sesión, nombre y errores. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { clearDownloads, exportUnit, listDownloads } from '@/features/export/api/exportApi';
import { FORMATS, formatInfo, isQuestion, resourcesFor } from '@/features/export/model/exportFormats';
import { setSession, getSession } from '@/shared/api/sessionStore';
import { item, mockFetch, text } from '@/test/fixtures';

afterEach(() => { setSession(null); vi.unstubAllGlobals(); });

describe('formatos y selección', () => {
  it('Moodle recibe preguntas aprobadas; Chamilo y HTML, todo lo aprobado', () => {
    const list = [item({ status: 'aprobado' }), item(), text({ status: 'aprobado' })];
    expect(isQuestion(list[2])).toBe(false);
    expect(resourcesFor('moodle_xml', list)).toEqual([list[0]]);
    expect(resourcesFor('scorm_zip', list)).toEqual([list[0], list[2]]);
    expect(resourcesFor('documento', list)).toEqual([list[0], list[2]]);
    expect(FORMATS.map((f) => f.title)).toEqual(['Moodle', 'Chamilo', 'Documento de la unidad']);
    expect(formatInfo('scorm_zip').extension).toBe('zip');
  });
});

describe('descargas del servidor', () => {
  it.each(['documento', 'moodle_xml', 'scorm_zip'] as const)('pide %s y conserva el archivo y nombre del servidor', async (format) => {
    setSession({ token: 'session-token', email: 'ana@correo.pe', name: 'Ana' });
    const fetch = vi.fn().mockResolvedValue(new Response('archivo del servidor', {
      headers: { 'Content-Type': formatInfo(format).mimeType, 'Content-Disposition': 'attachment; filename="curso-unidad-1.html"' },
    }));
    vi.stubGlobal('fetch', fetch);
    const file = await exportUnit('u/1', format, ['r1']);
    expect(file.fileName).toBe('curso-unidad-1.html');
    expect(await file.blob.text()).toBe('archivo del servidor');
    const [url, request] = fetch.mock.calls[0];
    expect(url).toBe('/api/v1/units/u%2F1/exports');
    expect(request.method).toBe('POST');
    expect(request.headers.Authorization).toBe('Bearer session-token');
    expect(JSON.parse(request.body)).toEqual({ format, resourceIds: ['r1'] });
  });

  it('muestra el error del servidor y cierra la sesión vencida', async () => {
    setSession({ token: 'expired', email: 'ana@correo.pe', name: 'Ana' });
    mockFetch({ status: 401, body: { error: { code: 'UNAUTHORIZED', message: 'Inicia sesión.' } } });
    await expect(exportUnit('u1', 'documento', ['r1'])).rejects.toMatchObject({ status: 401, message: 'Inicia sesión.' });
    expect(getSession()).toBeNull();
    mockFetch({ status: 422, body: { error: { code: 'NO_APPROVED_RESOURCES', message: 'Elige un recurso aprobado.' } } });
    await expect(exportUnit('u1', 'documento', [])).rejects.toMatchObject({ code: 'NO_APPROVED_RESOURCES' });
  });

  it('informa fallos de conexión y respuestas sin JSON', async () => {
    mockFetch(new Error('offline'));
    await expect(exportUnit('u1', 'documento', ['r1'])).rejects.toMatchObject({ code: 'NO_CONNECTION' });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('Bad gateway', { status: 502 })));
    await expect(exportUnit('u1', 'documento', ['r1'])).rejects.toMatchObject({ status: 502, message: 'No se pudo generar el archivo.' });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('data')));
    expect((await exportUnit('u1', 'scorm_zip', ['r1'])).fileName).toBe('exportacion.zip');
  });

  it('lista y borra el historial sin registrar otra descarga desde el navegador', async () => {
    const calls = mockFetch({ body: [] }, { status: 204 });
    await listDownloads('u1');
    await clearDownloads('u1');
    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/v1/units/u1/downloads', 'DELETE /api/v1/units/u1/downloads']);
  });
});
