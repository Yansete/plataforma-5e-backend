/**
 * Catálogos de la interfaz. Los tipos de recurso se agrupan por momento de la clase; cada uno
 * corresponde a una etapa del modelo instruccional, que se envía al servidor pero no se muestra.
 */
import type { DiscardReason, Difficulty, ResourceType, Stage5E } from '@/shared/types/domain';

export interface ResourceTypeInfo {
  id: ResourceType;
  /** Nombre en la lista de opciones. */
  name: string;
  /** Nombre de un recurso de este tipo (singular). */
  singular: string;
  /** Para el botón: «Generar 1 glosario», «Generar 3 preguntas». */
  count: [string, string];
  stage: Stage5E;
  group: string;
}

export const RESOURCE_TYPES: ResourceTypeInfo[] = [
  { id: 'pregunta_detonante', name: 'Pregunta detonante', singular: 'Pregunta detonante', count: ['pregunta detonante', 'preguntas detonantes'], stage: 'engage', group: 'Para iniciar la clase' },
  { id: 'sondeo_diagnostico', name: 'Sondeo de ideas previas', singular: 'Sondeo de ideas previas', count: ['sondeo', 'sondeos'], stage: 'engage', group: 'Para iniciar la clase' },
  { id: 'guia_exploracion', name: 'Guía de exploración', singular: 'Guía de exploración', count: ['guía', 'guías'], stage: 'explore', group: 'Para explorar' },
  { id: 'caso_indagacion', name: 'Caso con preguntas', singular: 'Caso con preguntas', count: ['caso', 'casos'], stage: 'explore', group: 'Para explorar' },
  { id: 'explicacion', name: 'Explicación del tema', singular: 'Explicación del tema', count: ['explicación', 'explicaciones'], stage: 'explain', group: 'Para explicar' },
  { id: 'glosario', name: 'Glosario', singular: 'Glosario', count: ['glosario', 'glosarios'], stage: 'explain', group: 'Para explicar' },
  { id: 'ejercicio_aplicacion', name: 'Ejercicio de aplicación', singular: 'Ejercicio de aplicación', count: ['ejercicio', 'ejercicios'], stage: 'elaborate', group: 'Para aplicar' },
  { id: 'item_opcion_multiple', name: 'Preguntas de opción múltiple', singular: 'Pregunta de opción múltiple', count: ['pregunta', 'preguntas'], stage: 'evaluate', group: 'Para evaluar' },
];

/** «1 glosario», «3 preguntas». */
export function countLabel(type: ResourceType, quantity: number): string {
  const [one, many] = typeInfo(type).count;
  return `${quantity} ${quantity === 1 ? one : many}`;
}

/** Momentos de la clase, en el orden en que se usan. */
export const GROUPS = ['Para iniciar la clase', 'Para explorar', 'Para explicar', 'Para aplicar', 'Para evaluar'];

export const DOCUMENT_TYPES = [
  'Separata o apuntes de clase',
  'Diapositivas de clase',
  'Guía de práctica',
  'Sílabo de la unidad',
  'Transcripción de clase',
];

export const DIFFICULTIES: { value: Difficulty; label: string }[] = [
  { value: 'basica', label: 'Básica' },
  { value: 'intermedia', label: 'Intermedia' },
  { value: 'avanzada', label: 'Avanzada' },
];

// Sprint 1: solo texto. Imágenes, video y otras modalidades llegan en el Sprint 2.
export const MODALITIES = ['Textual'];

export const DISCARD_REASONS: { value: DiscardReason; label: string }[] = [
  { value: 'sin_sentido', label: 'No tiene sentido o es confuso' },
  { value: 'tambien_correcto', label: 'También es correcto' },
  { value: 'duplicado', label: 'Repite otra alternativa' },
  { value: 'fuera_de_unidad', label: 'No corresponde a la unidad' },
  { value: 'otro', label: 'Otro motivo' },
];

export const MAX_FILE_MB = 25;

export function typeInfo(type: ResourceType): ResourceTypeInfo {
  return RESOURCE_TYPES.find((t) => t.id === type) ?? RESOURCE_TYPES[RESOURCE_TYPES.length - 1];
}

export function hasOptions(type: ResourceType): boolean {
  return type === 'item_opcion_multiple';
}

export function discardReasonLabel(reason: DiscardReason | null): string {
  if (reason === 'regenerado') return 'Reemplazado por una nueva versión';
  return DISCARD_REASONS.find((r) => r.value === reason)?.label ?? 'Sin motivo';
}

/** Posición del recurso en la clase (para ordenar el documento de la unidad). */
export function groupIndex(type: ResourceType): number {
  return GROUPS.indexOf(typeInfo(type).group);
}
