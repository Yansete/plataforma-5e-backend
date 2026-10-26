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
  hasOptions: boolean;
}

/** Se completan con GET /api/v1/resource-types antes de renderizar las pestañas. */
export const RESOURCE_TYPES: ResourceTypeInfo[] = [];
export const GROUPS: string[] = [];

const STAGES = ['engage', 'explore', 'explain', 'elaborate', 'evaluate'];
const FORMATS = ['text', 'visual', 'image', 'audio', 'interactive'];

export function parseResourceCatalog(raw: unknown): ResourceTypeInfo[] {
  if (!Array.isArray(raw) || raw.length === 0) throw new Error('El catálogo está vacío.');
  const ids = new Set<string>();
  const result = raw.map((value) => {
    const entry = value as Record<string, unknown> | null;
    if (!entry || typeof entry !== 'object' ||
        !['id', 'name', 'singular', 'group'].every((key) => typeof entry[key] === 'string' && (entry[key] as string).trim()) ||
        !STAGES.includes(entry.stage as string) || !FORMATS.includes(entry.format as string) ||
        !Array.isArray(entry.count) || entry.count.length !== 2 ||
        !entry.count.every((part) => typeof part === 'string' && part.trim()) ||
        typeof entry.hasOptions !== 'boolean' || ids.has(entry.id as string)) {
      throw new Error('El catálogo de recursos no es válido.');
    }
    ids.add(entry.id as string);
    return { id: entry.id, name: entry.name, singular: entry.singular, count: [...entry.count],
      stage: entry.stage, group: entry.group, format: entry.format, hasOptions: entry.hasOptions } as ResourceTypeInfo;
  });
  if (!ids.has('item_opcion_multiple')) throw new Error('Falta el tipo de recurso predeterminado.');
  return result;
}

export function installResourceCatalog(raw: unknown): void {
  const entries = parseResourceCatalog(raw);
  // Solo se reemplaza después de validar toda la respuesta.
  RESOURCE_TYPES.splice(0, RESOURCE_TYPES.length, ...entries);
  GROUPS.splice(0, GROUPS.length, ...new Set(entries.map((entry) => entry.group)));
}

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
  const entry = RESOURCE_TYPES.find((t) => t.id === type) ?? RESOURCE_TYPES.find((t) => t.id === 'item_opcion_multiple');
  if (!entry) throw new Error('El catálogo de recursos todavía no está disponible.');
  return entry;
}

export function hasOptions(type: ResourceType): boolean {
  return typeInfo(type).hasOptions;
}

export function discardReasonLabel(reason: DiscardReason | null): string {
  if (reason === 'regenerado') return 'Reemplazado por una nueva versión';
  return DISCARD_REASONS.find((r) => r.value === reason)?.label ?? 'Sin motivo';
}

/** Posición del recurso en la clase (para ordenar el documento de la unidad). */
export function groupIndex(type: ResourceType): number {
  return GROUPS.indexOf(typeInfo(type).group);
}
