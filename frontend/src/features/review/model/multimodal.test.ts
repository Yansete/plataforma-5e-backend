/** Selección múltiple, revisión unificada en orden 5E, edición con formato y elementos de las actividades. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { RESOURCE_TYPES, formatOf, selectionLabel, typeInfo } from '@/features/generation/model/resourceCatalog';
import { generateMany } from '@/features/generation/api/generationApi';
import { detectType } from '@/features/generation/model/requestInterpreter';
import { fetchResourceMedia, reviewBody } from '@/features/review/api/reviewApi';
import { byStage, editContent, editStructure } from '@/features/review/model/reviewRules';
import { addItem, listItems, moveItem, removeItem, setField, setItem, structureProblem, structureSpec } from '@/features/review/model/structureFields';
import { escapeHtml, textToHtml } from '@/shared/lib/html';
import { setSession } from '@/shared/api/sessionStore';
import { defaultInput } from '@/features/generation/api/generationApi';
import { item, mockFetch, text } from '@/test/fixtures';
import type { Resource } from '@/shared/types/domain';

afterEach(() => {
  setSession(null);
  vi.unstubAllGlobals();
});

describe('catálogo multimodal', () => {
  it('cada etapa ofrece al menos dos recursos y hay imagen, audio, gráficos y actividades', () => {
    for (const group of new Set(RESOURCE_TYPES.map((t) => t.group))) {
      expect(RESOURCE_TYPES.filter((t) => t.group === group).length).toBeGreaterThanOrEqual(2);
    }
    expect(new Set(RESOURCE_TYPES.map((t) => t.format))).toEqual(new Set(['text', 'visual', 'image', 'audio', 'interactive']));
    expect(formatOf('podcast_resumen')).toBe('audio');
    expect(typeInfo('verdadero_falso').stage).toBe('evaluate');
  });

  it('nombra la selección: el tipo si es uno, el total si son varios', () => {
    expect(selectionLabel(['mapa_conceptual'], 1)).toBe('1 mapa conceptual');
    expect(selectionLabel(['mapa_conceptual', 'infografia', 'audio_detonante'], 2)).toBe('6 recursos');
    expect(selectionLabel(['glosario', 'infografia'], 1)).toBe('2 recursos');
  });

  it('el pedido escrito reconoce los formatos nuevos sin confundir palabras', () => {
    expect(detectType('Un mapa conceptual de TCP')).toBe('mapa_conceptual');
    expect(detectType('Una cápsula de audio para empezar')).toBe('audio_detonante');
    expect(detectType('5 afirmaciones de verdadero o falso')).toBe('verdadero_falso');
    expect(detectType('Una actividad para relacionar conceptos')).toBe('emparejamiento');
    expect(detectType('Una imagen sobre la red')).toBe('imagen_ilustrativa');
    expect(detectType('Explica la encapsulación')).toBe('explicacion');
  });
});

describe('generación de varios tipos', () => {
  it('pide cada tipo marcado, sigue si uno falla y avisa el respaldo', async () => {
    const calls = mockFetch(
      { body: { resources: [text({ id: 'a' })], generator: { fallback: false } } },
      { status: 503, body: { error: { code: 'AI_DOWN', message: 'La IA no respondió.' } } },
      { body: { resources: [text({ id: 'b' })], generator: { fallback: true } } },
    );
    const progress: number[] = [];
    const result = await generateMany(defaultInput('u1'), ['audio_detonante', 'mapa_conceptual', 'verdadero_falso'], (p) => progress.push(p.done));
    expect(calls.map((c) => (c.body as { resourceType: string }).resourceType)).toEqual(['audio_detonante', 'mapa_conceptual', 'verdadero_falso']);
    expect(calls.map((c) => (c.body as { stage: string }).stage)).toEqual(['engage', 'explain', 'evaluate']);
    expect(result.resources.map((r) => r.id)).toEqual(['a', 'b']);
    expect(result.failed).toEqual([{ type: 'mapa_conceptual', message: 'La IA no respondió.' }]);
    expect(result.fallbackTypes).toEqual(['verdadero_falso']);
    expect(progress).toEqual([0, 1, 2, 3]);
  });
});

describe('revisión', () => {
  it('agrupa por etapa en el orden de la clase', () => {
    const list = [item({ id: 'q', stage: 'evaluate' }), text({ id: 'e', stage: 'engage' }), text({ id: 'x', stage: 'explain' })];
    expect(byStage(list).map((g) => [g.stage, g.resources.map((r) => r.id)])).toEqual([
      ['engage', ['e']],
      ['explain', ['x']],
      ['evaluate', ['q']],
    ]);
  });

  it('guarda el formato del editor y la estructura editada', () => {
    const base = text({ structure: { pairs: [] } as Resource['structure'] });
    const edited = editContent(base, base.title, 'Texto', '<p><strong>Texto</strong></p>');
    expect(edited.bodyHtml).toBe('<p><strong>Texto</strong></p>');
    expect(edited.edited).toBe(true);
    expect(editContent(base, base.title, base.body).bodyHtml).toBeUndefined();
    expect(reviewBody(edited)).toMatchObject({ bodyHtml: '<p><strong>Texto</strong></p>', structure: { pairs: [] } });
    expect(reviewBody(text())).not.toHaveProperty('bodyHtml');
    expect(editStructure(base, { pairs: [{ term: 'TCP', definition: 'Confiable' }] }).structure?.pairs?.[0].term).toBe('TCP');
  });

  it('pide el archivo del recurso con la sesión', async () => {
    setSession({ token: 'tok', email: 'a@b.pe', name: 'Ana' });
    const fetch = vi.fn().mockResolvedValue(new Response('<svg/>', { headers: { 'Content-Type': 'image/svg+xml' } }));
    vi.stubGlobal('fetch', fetch);
    const blob = await fetchResourceMedia(text({ id: 'r/1', unitId: 'u1' }));
    expect(await blob.text()).toBe('<svg/>');
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/units/u1/resources/r%2F1/media');
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer tok');
    mockFetch({ status: 404, body: { error: { code: 'NO_MEDIA', message: 'Sin archivo.' } } });
    await expect(fetchResourceMedia(text())).rejects.toMatchObject({ code: 'NO_MEDIA' });
  });
});

describe('elementos de las actividades', () => {
  it('edita, agrega, mueve y quita elementos', () => {
    const spec = structureSpec('emparejamiento')!;
    let s = { pairs: [{ term: 'TCP', definition: 'Confiable' }] };
    s = addItem(s, spec) as typeof s;
    s = setItem(s, spec, 1, 'term', 'UDP') as typeof s;
    s = setItem(s, spec, 1, 'definition', 'Rápido') as typeof s;
    s = moveItem(s, spec, 1, -1) as typeof s;
    expect(listItems(s, spec)).toEqual([{ term: 'UDP', definition: 'Rápido' }, { term: 'TCP', definition: 'Confiable' }]);
    expect(moveItem(s, spec, 0, -1)).toBe(s);
    expect(structureProblem('emparejamiento', s)).toMatch(/al menos 3/);
    s = removeItem(s, spec, 0) as typeof s;
    expect(listItems(s, spec)).toHaveLength(1);
    expect(structureProblem('emparejamiento', addItem(s, spec))).toMatch(/vacíos/);
  });

  it('valida verdadero o falso, completar, ordenar y los campos sueltos', () => {
    const allTrue = { statements: [1, 2, 3].map((n) => ({ text: `A${n}`, isTrue: true, feedback: '' })) };
    expect(structureProblem('verdadero_falso', allTrue)).toMatch(/verdaderas y falsas/);
    expect(structureProblem('verdadero_falso', { statements: [...allTrue.statements, { text: 'B', isTrue: false, feedback: '' }] })).toBeNull();
    const blanks = { blanks: [{ sentence: 'El ____ es rápido.', answer: 'UDP' }, { sentence: 'Sin espacio.', answer: 'TCP' }] };
    expect(structureProblem('completar_espacios', blanks)).toMatch(/____/);
    const sequence = structureSpec('ordenar_pasos')!;
    const steps = setItem({ sequence: ['a', 'b', 'c'] }, sequence, 2, null, 'z');
    expect(steps.sequence).toEqual(['a', 'b', 'z']);
    expect(structureProblem('ordenar_pasos', steps)).toBeNull();
    expect(structureProblem('podcast_resumen', { script: '  ' })).toMatch(/Guion/);
    expect(structureProblem('mapa_conceptual', setField({ nodes: [] }, 'central', 'Redes'))).toMatch(/al menos 3/);
    expect(structureProblem('explicacion', {})).toBeNull();
    expect(structureSpec('glosario')).toBeNull();
    expect(addItem({}, structureSpec('podcast_resumen')!)).toEqual({});
  });
});

describe('texto a HTML', () => {
  it('convierte párrafos y escapa el texto', () => {
    expect(textToHtml('Uno <b>\nsigue\n\nDos')).toBe('<p>Uno &lt;b&gt;<br>sigue</p><p>Dos</p>');
    expect(escapeHtml('"&"')).toBe('&quot;&amp;&quot;');
  });
});
