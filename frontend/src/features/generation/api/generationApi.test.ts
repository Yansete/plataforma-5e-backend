/** Generación: cuerpo de la petición, aviso del generador de respaldo y catálogo de tipos. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { GROUPS, RESOURCE_TYPES, countLabel, discardReasonLabel, groupIndex, hasOptions, typeInfo } from '@/features/generation/model/resourceCatalog';
import { defaultInput, generate, generationBody } from '@/features/generation/api/generationApi';
import { item, mockFetch } from '@/test/fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('catálogo', () => {
  it('agrupa los tipos por momento de la clase, en orden', () => {
    expect(GROUPS).toEqual(['Para iniciar la clase', 'Para explorar', 'Para explicar', 'Para aplicar', 'Para evaluar']);
    expect(RESOURCE_TYPES.every((t) => GROUPS.includes(t.group))).toBe(true);
    expect(groupIndex('pregunta_detonante')).toBe(0);
    expect(groupIndex('item_opcion_multiple')).toBe(4);
    expect(typeInfo('glosario').stage).toBe('explain');
  });

  it('nombra cantidades y motivos', () => {
    expect(countLabel('item_opcion_multiple', 1)).toBe('1 pregunta');
    expect(countLabel('item_opcion_multiple', 3)).toBe('3 preguntas');
    expect(countLabel('explicacion', 2)).toBe('2 explicaciones');
    expect(hasOptions('glosario')).toBe(false);
    expect(discardReasonLabel('regenerado')).toMatch(/nueva versión/);
    expect(discardReasonLabel('duplicado')).toMatch(/Repite/);
    expect(discardReasonLabel(null)).toBe('Sin motivo');
  });

  it('no muestra los nombres de las etapas del modelo instruccional', () => {
    const visible = JSON.stringify(RESOURCE_TYPES.map(({ name, singular, count, group }) => ({ name, singular, count, group })));
    expect(visible).not.toMatch(/5E|engage|explore|explain|elaborate|evaluate/i);
  });
});

describe('generación', () => {
  it('arma la petición con la etapa interna y límites válidos', () => {
    const body = generationBody({ ...defaultInput('u1'), resourceType: 'glosario', quantity: 9, optionCount: 5, instructions: ` ${'x'.repeat(600)} `, audience: ' 5.º ciclo ', competency: '', modalities: ['Textual'] });
    expect(body).toMatchObject({ unidad_id: 'u1', etapa_5e: 'explain', tipo_recurso: 'glosario', cantidad: 5, alternativas: 4, publico_objetivo: '5.º ciclo' });
    expect(body.indicaciones).toHaveLength(500);
    expect(generationBody({ ...defaultInput('u1'), quantity: 0, optionCount: 3 })).toMatchObject({ cantidad: 1, alternativas: 3, etapa_5e: 'evaluate' });
  });

  it('avisa si se usó el generador de respaldo', async () => {
    const calls = mockFetch({ body: { resources: [item()], generator: { fallback: true } } }, { body: { resources: [] } });
    expect(await generate(defaultInput('u1'))).toEqual({ resources: [item()], usedFallback: true });
    expect(await generate(defaultInput('u1'))).toEqual({ resources: [], usedFallback: false });
    expect(calls[0]).toMatchObject({ url: '/api/v1/generaciones', method: 'POST' });
  });
});
