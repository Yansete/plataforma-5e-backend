import { afterEach, describe, expect, it, vi } from 'vitest';
import { deleteResource, listResources, regenerate, reviewBody, saveResource } from '@/features/review/api/reviewApi';
import { decideOption, setStatus } from '@/features/review/model/reviewRules';
import { item, mockFetch, text } from '@/test/fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('servidor', () => {
  it('guarda solo lo editable de la revisión', () => {
    const body = reviewBody(decideOption(setStatus(item(), 'descartado', 'sin_sentido'), 'b', 'aceptado'));
    expect(body).toMatchObject({ status: 'descartado', discardReason: 'sin_sentido', edited: false });
    expect(body.options![1]).toEqual({ id: 'b', text: 'TCP', feedback: 'Retro b', decision: 'aceptado', discardReason: null, edited: false });
    expect(reviewBody(text()).options).toBeNull();
    expect(reviewBody(item()).discardReason).toBeNull();
    expect(reviewBody(item())).not.toHaveProperty('approvalBlockers');
  });

  it('lista, guarda y borra en la ruta de la unidad', async () => {
    const calls = mockFetch({ body: [item()] }, { body: item({ status: 'aprobado' }) }, { status: 204 });
    expect(await listResources('u1')).toHaveLength(1);
    expect((await saveResource(item())).status).toBe('aprobado');
    await deleteResource(item());
    expect(calls.map((c) => `${c.method} ${c.url}`)).toEqual(['GET /api/v1/units/u1/resources', 'PUT /api/v1/units/u1/resources/r1', 'DELETE /api/v1/units/u1/resources/r1']);
  });

  it('regenera con los mismos parámetros y descarta la versión anterior', async () => {
    const nuevo = item({ id: 'r9' });
    const calls = mockFetch({ body: { resources: [nuevo], generator: { fallback: false } } }, { body: item({ status: 'descartado', discardReason: 'regenerado' }) });
    const result = await regenerate(item());
    expect(result.created).toEqual([nuevo]);
    expect(result.replaced.discardReason).toBe('regenerado');
    expect(calls[0].body).toMatchObject({ resourceType: 'item_opcion_multiple', quantity: 1, difficulty: 'avanzada', outcomeId: 'ra1', instructions: 'Usa videollamadas' });
    expect(calls[1].body).toMatchObject({ status: 'descartado', discardReason: 'regenerado' });
  });

  it('sin parámetros guardados regenera con los datos del recurso', async () => {
    const calls = mockFetch({ body: { resources: [] } }, { body: text({ status: 'descartado' }) });
    await regenerate(text({ params: undefined, outcomeId: '' }));
    expect(calls[0].body).toMatchObject({ resourceType: 'explicacion', difficulty: 'intermedia', outcomeId: null, optionCount: 4 });
    mockFetch({ body: { resources: [] } }, { body: item() });
    await regenerate(item({ params: undefined }));
  });
});
