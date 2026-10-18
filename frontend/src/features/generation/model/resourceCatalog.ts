/**
 * Catálogos de la interfaz. Los tipos de recurso se agrupan por momento de la clase; cada uno
 * corresponde a una etapa del modelo instruccional, que se envía al servidor pero no se muestra.
 */
import type { DiscardReason, Difficulty, ResourceFormat, ResourceType, Stage5E } from '@/shared/types/domain';

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
  format: ResourceFormat;
}

const ENGAGE = 'Para iniciar la clase';
const EXPLORE = 'Para explorar';
const EXPLAIN = 'Para explicar';
const ELABORATE = 'Para aplicar';
const EVALUATE = 'Para evaluar';

export const RESOURCE_TYPES: ResourceTypeInfo[] = [
  { id: 'pregunta_detonante', name: 'Pregunta detonante', singular: 'Pregunta detonante', count: ['pregunta detonante', 'preguntas detonantes'], stage: 'engage', group: ENGAGE, format: 'text' },
  { id: 'sondeo_diagnostico', name: 'Sondeo de ideas previas', singular: 'Sondeo de ideas previas', count: ['sondeo', 'sondeos'], stage: 'engage', group: ENGAGE, format: 'text' },
  { id: 'audio_detonante', name: 'Cápsula de audio detonante', singular: 'Cápsula de audio', count: ['audio', 'audios'], stage: 'engage', group: ENGAGE, format: 'audio' },
  { id: 'guia_exploracion', name: 'Guía de exploración', singular: 'Guía de exploración', count: ['guía', 'guías'], stage: 'explore', group: EXPLORE, format: 'text' },
  { id: 'caso_indagacion', name: 'Caso con preguntas', singular: 'Caso con preguntas', count: ['caso', 'casos'], stage: 'explore', group: EXPLORE, format: 'text' },
  { id: 'imagen_ilustrativa', name: 'Imagen ilustrativa', singular: 'Imagen ilustrativa', count: ['imagen', 'imágenes'], stage: 'explore', group: EXPLORE, format: 'image' },
  { id: 'diagrama_proceso', name: 'Diagrama de proceso', singular: 'Diagrama de proceso', count: ['diagrama', 'diagramas'], stage: 'explore', group: EXPLORE, format: 'visual' },
  { id: 'explicacion', name: 'Explicación del tema', singular: 'Explicación del tema', count: ['explicación', 'explicaciones'], stage: 'explain', group: EXPLAIN, format: 'text' },
  { id: 'glosario', name: 'Glosario', singular: 'Glosario', count: ['glosario', 'glosarios'], stage: 'explain', group: EXPLAIN, format: 'text' },
  { id: 'mapa_conceptual', name: 'Mapa conceptual', singular: 'Mapa conceptual', count: ['mapa conceptual', 'mapas conceptuales'], stage: 'explain', group: EXPLAIN, format: 'visual' },
  { id: 'infografia', name: 'Infografía', singular: 'Infografía', count: ['infografía', 'infografías'], stage: 'explain', group: EXPLAIN, format: 'visual' },
  { id: 'podcast_resumen', name: 'Resumen en pódcast', singular: 'Resumen en pódcast', count: ['pódcast', 'pódcasts'], stage: 'explain', group: EXPLAIN, format: 'audio' },
  { id: 'ejercicio_aplicacion', name: 'Ejercicio de aplicación', singular: 'Ejercicio de aplicación', count: ['ejercicio', 'ejercicios'], stage: 'elaborate', group: ELABORATE, format: 'text' },
  { id: 'emparejamiento', name: 'Relacionar conceptos', singular: 'Actividad de relacionar', count: ['actividad de relacionar', 'actividades de relacionar'], stage: 'elaborate', group: ELABORATE, format: 'interactive' },
  { id: 'ordenar_pasos', name: 'Ordenar pasos', singular: 'Actividad de ordenar', count: ['actividad de ordenar', 'actividades de ordenar'], stage: 'elaborate', group: ELABORATE, format: 'interactive' },
  { id: 'item_opcion_multiple', name: 'Preguntas de opción múltiple', singular: 'Pregunta de opción múltiple', count: ['pregunta', 'preguntas'], stage: 'evaluate', group: EVALUATE, format: 'text' },
  { id: 'verdadero_falso', name: 'Verdadero o falso', singular: 'Verdadero o falso', count: ['verdadero o falso', 'verdadero o falso'], stage: 'evaluate', group: EVALUATE, format: 'interactive' },
  { id: 'completar_espacios', name: 'Completar espacios', singular: 'Completar espacios', count: ['completar espacios', 'completar espacios'], stage: 'evaluate', group: EVALUATE, format: 'interactive' },
];

/** Etiqueta corta del formato, para la lista de opciones y la revisión. */
export const FORMAT_LABELS: Record<ResourceFormat, string> = {
  text: 'Texto',
  visual: 'Gráfico',
  image: 'Imagen',
  audio: 'Audio',
  interactive: 'Interactivo',
};

/** «1 glosario», «3 preguntas». */
export function countLabel(type: ResourceType, quantity: number): string {
  const [one, many] = typeInfo(type).count;
  return `${quantity} ${quantity === 1 ? one : many}`;
}

/** Momentos de la clase, en el orden en que se usan. */
export const GROUPS = [ENGAGE, EXPLORE, EXPLAIN, ELABORATE, EVALUATE];

/** Varios tipos a la vez: «2 recursos», o el nombre del tipo si es uno solo. */
export function selectionLabel(types: ResourceType[], quantity: number): string {
  if (types.length === 1) return countLabel(types[0], quantity);
  const total = types.length * quantity;
  return `${total} ${total === 1 ? 'recurso' : 'recursos'}`;
}

export function formatOf(type: ResourceType): ResourceFormat {
  return typeInfo(type).format;
}

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

// La modalidad del pedido sigue siendo «Textual»: los formatos multimedia son tipos de recurso propios.
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
  return RESOURCE_TYPES.find((t) => t.id === type) ?? RESOURCE_TYPES.find((t) => t.id === 'item_opcion_multiple')!;
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
