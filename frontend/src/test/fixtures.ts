/** Datos y utilidades para las pruebas unitarias (no forman parte de la aplicación). */
import { vi } from 'vitest';
import type { Course, Evidence, ItemOption, Resource, Unit } from '@/shared/types/domain';

export interface FetchCall {
  url: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

type Prepared = { status?: number; body?: unknown } | Error;

/** Reemplaza fetch por respuestas preparadas, en orden. Devuelve las llamadas recibidas. */
export function mockFetch(...responses: Prepared[]): FetchCall[] {
  const calls: FetchCall[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const body = typeof init.body === 'string' ? JSON.parse(init.body) : init.body;
      calls.push({ url, method: init.method ?? 'GET', headers: (init.headers ?? {}) as Record<string, string>, body });
      const next = responses.shift();
      if (!next) throw new Error('No hay respuesta preparada para ' + url);
      if (next instanceof Error) throw next;
      const status = next.status ?? 200;
      return new Response(status === 204 ? null : JSON.stringify(next.body ?? null), { status, headers: { 'Content-Type': 'application/json' } });
    }),
  );
  return calls;
}

export function unit(overrides: Partial<Unit> = {}): Unit {
  return {
    id: 'u1',
    courseId: 'c1',
    number: 1,
    title: 'Modelo TCP/IP y protocolos de transporte',
    outcomes: [
      { id: 'ra1', code: 'RA1.1', text: 'Distingue las características y los usos de los protocolos TCP y UDP.' },
      { id: 'ra2', code: 'RA1.2', text: 'Explica la función de cada capa del modelo TCP/IP y la encapsulación.' },
    ],
    ...overrides,
  };
}

export function course(overrides: Partial<Course> = {}): Course {
  return { id: 'c1', code: 'RED-301', name: 'Redes de Computadoras', term: '2026-II', summary: 'Redes.', learningGoal: 'Configura redes.', units: [unit()], ...overrides };
}

export const EVIDENCE: Evidence[] = [
  {
    id: 'f1',
    text: 'TCP numera los segmentos. TCP garantiza una entrega confiable porque confirma la recepción y retransmite lo que se pierde. Es más lento.',
    location: 'p. 1',
    documentId: 'd1',
    documentName: 'separata.pdf',
  },
  {
    id: 'f2',
    text: 'UDP no confirma la entrega y por eso introduce menos retardo en las videollamadas.',
    location: 'p. 2',
    documentId: 'd2',
    documentName: 'Protocolo de datagramas de usuario.txt',
    sourceUrl: 'https://es.example.org/wiki/UDP',
    license: 'CC BY-SA 4.0',
  },
];

export function option(id: string, overrides: Partial<ItemOption> = {}): ItemOption {
  return { id, text: id.toUpperCase(), isCorrect: false, feedback: `Retro ${id}`, sourceFragmentIds: ['f1'], decision: 'pendiente', discardReason: null, edited: false, ...overrides };
}

export function item(overrides: Partial<Resource> = {}): Resource {
  return {
    id: 'r1',
    unitId: 'u1',
    outcomeId: 'ra1',
    stage: 'evaluate',
    type: 'item_opcion_multiple',
    title: 'UDP en una videollamada',
    body: '¿Qué protocolo no espera el reenvío de lo perdido?',
    options: [option('a', { text: 'UDP', isCorrect: true, sourceFragmentIds: ['f2'] }), option('b', { text: 'TCP' }), option('c', { text: 'IP' }), option('d', { text: 'DNS', sourceFragmentIds: ['zz'] })],
    citations: [
      { claim: 'TCP garantiza una entrega confiable y retransmite lo que se pierde', fragmentIds: ['f1'] },
      { claim: 'UDP introduce menos retardo', fragmentIds: ['f2', 'perdido'] },
    ],
    status: 'pendiente',
    edited: false,
    discardReason: null,
    createdAt: '2026-10-10T10:00:00Z',
    updatedAt: '2026-10-10T10:00:00Z',
    decidedAt: null,
    evidence: EVIDENCE,
    params: { resourceType: 'item_opcion_multiple', stage: 'evaluate', outcomeId: 'ra1', difficulty: 'avanzada', optionCount: 4, instructions: 'Usa videollamadas', audience: '', competency: '', modalities: ['Textual'] },
    generatorKind: 'ia',
    ...overrides,
  };
}

export function text(overrides: Partial<Resource> = {}): Resource {
  return item({ id: 'r2', type: 'explicacion', stage: 'explain', title: 'Las capas del modelo', body: 'Primer párrafo.\n\nSegundo <párrafo>.', options: null, ...overrides });
}
