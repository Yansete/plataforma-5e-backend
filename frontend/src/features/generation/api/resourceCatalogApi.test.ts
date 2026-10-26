import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadResourceCatalog } from '@/features/generation/api/resourceCatalogApi';
import { GROUPS, RESOURCE_TYPES, countLabel, formatOf, installResourceCatalog, typeInfo } from '@/features/generation/model/resourceCatalog';
import { defaultInput, generationBody } from '@/features/generation/api/generationApi';
import { resourceCatalogFixture } from '@/test/resourceCatalogFixture';
import { mockFetch } from '@/test/fixtures';
import { setSession } from '@/shared/api/sessionStore';

afterEach(() => { setSession(null); vi.unstubAllGlobals(); });

describe('catálogo publicado por el backend', () => {
  it('comparte la petición de consumidores simultáneos', async () => {
    const calls = mockFetch({ body: resourceCatalogFixture });
    await Promise.all([loadResourceCatalog(), loadResourceCatalog()]);
    expect(calls).toHaveLength(1);
  });
  it('usa nombres, cantidades, etapa y formato de la respuesta, sin enviar la sesión', async () => {
    setSession({ token: 'test-token', email: 'a@b.pe', name: 'Ana' });
    const response = resourceCatalogFixture.map((entry) => entry.id === 'glosario'
      ? { ...entry, name: 'Nombre del servidor', count: ['término', 'términos'], stage: 'engage', group: 'Para iniciar la clase', format: 'visual' }
      : entry);
    const calls = mockFetch({ body: response });
    await loadResourceCatalog();
    expect(calls[0]).toMatchObject({ url: '/api/v1/resource-types', method: 'GET', headers: {} });
    expect(typeInfo('glosario').name).toBe('Nombre del servidor');
    expect(countLabel('glosario', 2)).toBe('2 términos');
    expect(formatOf('glosario')).toBe('visual');
    expect(generationBody({ ...defaultInput('u1'), resourceType: 'glosario' }).stage).toBe('engage');
    expect(GROUPS).toHaveLength(5);
  });

  it('permite reintentar después de un error de conexión', async () => {
    const calls = mockFetch(new Error('sin conexión'), { body: resourceCatalogFixture });
    await expect(loadResourceCatalog()).rejects.toMatchObject({ code: 'NO_CONNECTION' });
    await loadResourceCatalog();
    expect(calls).toHaveLength(2);
    expect(RESOURCE_TYPES).toHaveLength(18);
  });

  it.each([
    null, [], {},
    [...resourceCatalogFixture, resourceCatalogFixture[0]],
    resourceCatalogFixture.filter((entry) => entry.id !== 'item_opcion_multiple'),
    resourceCatalogFixture.map((entry, index) => index ? entry : { ...entry, count: ['solo uno'] }),
    resourceCatalogFixture.map((entry, index) => index ? entry : { ...entry, format: 'unsupported' }),
  ])('rechaza una respuesta incompleta sin reemplazar el catálogo anterior: %j', async (response) => {
    mockFetch({ body: response });
    await expect(loadResourceCatalog()).rejects.toMatchObject({ code: 'INVALID_RESOURCE_CATALOG' });
    expect(typeInfo('glosario').name).toBe('Glosario');
    expect(RESOURCE_TYPES).toHaveLength(18);
  });

  it('copia los datos recibidos en lugar de retener arrays externos', () => {
    const response = structuredClone(resourceCatalogFixture);
    installResourceCatalog(response);
    response[0].count[0] = 'cambiado';
    expect(countLabel('pregunta_detonante', 1)).toBe('1 pregunta detonante');
  });
});
