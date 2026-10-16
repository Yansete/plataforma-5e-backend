/** Material: validación del archivo, subida en dos pasos, búsqueda por tema y resumen. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { deleteDocument, fileProblem, listDocuments, listFragments, materialSummary, processDocument, searchTopic, unitDocuments, uploadAndProcess } from '@/features/materials/api/materialsApi';
import { mockFetch } from '@/test/fixtures';
import type { MaterialDocument } from '@/shared/types/domain';

afterEach(() => vi.unstubAllGlobals());

function doc(overrides: Partial<MaterialDocument>): MaterialDocument {
  return {
    id: 'd1', fileName: 'a.pdf', kind: 'pdf', sizeBytes: 10, unitId: 'u1', outcomeIds: [], documentType: 'Guía de práctica', status: 'procesado',
    registeredAt: '2026-10-10', processedAt: null, fragmentCount: 4, pageCount: 1, errorMessage: null, ...overrides,
  };
}

describe('material', () => {
  it('acepta PDF, PPTX y TXT de hasta 25 MB', () => {
    expect(fileProblem({ name: 'apuntes.PDF', size: 10 })).toBeNull();
    expect(fileProblem({ name: 'apuntes.docx', size: 10 })).toMatch(/PDF, PPTX o TXT/);
    expect(fileProblem({ name: 'sin-extension', size: 10 })).toMatch(/PDF/);
    expect(fileProblem({ name: 'vacio.txt', size: 0 })).toMatch(/vacío/);
    expect(fileProblem({ name: 'grande.pdf', size: 26 * 1024 * 1024 })).toMatch(/25 MB/);
  });

  it('sube el archivo con su contexto y luego lo procesa', async () => {
    const calls = mockFetch({ status: 201, body: doc({ status: 'registrado' }) }, { body: doc({}) });
    const steps: string[] = [];
    const result = await uploadAndProcess(new File(['hola'], 'a.txt'), { unitId: 'u1', outcomeIds: ['ra1'], documentType: 'Guía de práctica' }, (s) => steps.push(s));
    expect(result.status).toBe('procesado');
    expect(steps).toEqual(['subiendo', 'procesando']);
    const form = calls[0].body as FormData;
    expect(JSON.parse(String(form.get('contexto')))).toEqual({ unitId: 'u1', outcomeIds: ['ra1'], documentType: 'Guía de práctica', suggestedStage: null, usePermission: true });
    expect(calls[1].url).toBe('/api/v1/documentos/d1/procesar');
  });

  it('lista, procesa, muestra fragmentos, borra y busca por tema', async () => {
    const calls = mockFetch({ body: [doc({}), doc({ id: 'd2', unitId: 'u2' })] }, { body: doc({}) }, { body: [] }, { status: 204 }, { status: 201, body: [doc({ id: 'd3' })] });
    const all = await listDocuments();
    expect(unitDocuments(all, 'u2').map((d) => d.id)).toEqual(['d2']);
    await processDocument('d1');
    await listFragments('d1');
    await deleteDocument('d1');
    expect(await searchTopic('u1', '  TCP  ', 2)).toHaveLength(1);
    expect(calls[4]).toMatchObject({ url: '/api/v1/documentos/desde-tema', body: { unitId: 'u1', tema: 'TCP', maximo: 2 } });
  });

  it('resume lo procesado de la unidad', () => {
    expect(materialSummary([doc({}), doc({ id: 'd2', fragmentCount: 6 }), doc({ id: 'd3', status: 'error', fragmentCount: 0 })])).toEqual({ processed: 2, withError: 1 });
  });
});
