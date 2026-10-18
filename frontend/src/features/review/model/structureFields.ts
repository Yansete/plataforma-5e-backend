/**
 * Qué elementos se editan en cada tipo de recurso con estructura (mapa, infografía, diagrama, actividades,
 * guion del audio y descripción de la imagen), y cuándo están completos. Espeja las reglas del backend.
 */
import type { ResourceStructure, ResourceType } from '@/shared/types/domain';

export type FieldKind = 'text' | 'textarea' | 'boolean';

export interface FieldSpec {
  key: string;
  label: string;
  kind: FieldKind;
  /** Puede quedar vacío (retroalimentación, detalle). */
  optional?: boolean;
}

export interface StructureSpec {
  /** Campos sueltos (concepto central, titular, guion…). */
  fields: FieldSpec[];
  /** Lista de elementos (nodos, pasos, pares…), si el tipo la tiene. */
  list?: { key: keyof ResourceStructure; label: string; item: string; fields: FieldSpec[] | 'string'; min: number };
}

const text = (key: string, label: string): FieldSpec => ({ key, label, kind: 'text' });
const area = (key: string, label: string): FieldSpec => ({ key, label, kind: 'textarea' });
const optionalArea = (key: string, label: string): FieldSpec => ({ key, label, kind: 'textarea', optional: true });

export const STRUCTURE_SPECS: Partial<Record<ResourceType, StructureSpec>> = {
  mapa_conceptual: {
    fields: [text('central', 'Concepto central')],
    list: { key: 'nodes', label: 'Conceptos relacionados', item: 'Concepto', fields: [text('label', 'Concepto'), optionalArea('detail', 'Relación o detalle')], min: 3 },
  },
  infografia: {
    fields: [text('headline', 'Titular')],
    list: { key: 'points', label: 'Ideas clave', item: 'Idea', fields: [text('title', 'Título'), area('text', 'Explicación')], min: 3 },
  },
  diagrama_proceso: {
    fields: [],
    list: { key: 'steps', label: 'Pasos del proceso', item: 'Paso', fields: [text('title', 'Título'), area('text', 'Explicación')], min: 3 },
  },
  ordenar_pasos: {
    fields: [],
    list: { key: 'sequence', label: 'Pasos en el orden correcto', item: 'Paso', fields: 'string', min: 3 },
  },
  emparejamiento: {
    fields: [],
    list: { key: 'pairs', label: 'Pares para relacionar', item: 'Par', fields: [text('term', 'Término'), area('definition', 'Descripción')], min: 3 },
  },
  verdadero_falso: {
    fields: [],
    list: {
      key: 'statements',
      label: 'Afirmaciones',
      item: 'Afirmación',
      fields: [area('text', 'Afirmación'), { key: 'isTrue', label: 'Es verdadera', kind: 'boolean' }, optionalArea('feedback', 'Retroalimentación')],
      min: 3,
    },
  },
  completar_espacios: {
    fields: [],
    list: { key: 'blanks', label: 'Oraciones para completar', item: 'Oración', fields: [area('sentence', 'Oración con ____'), text('answer', 'Respuesta')], min: 2 },
  },
  audio_detonante: { fields: [area('script', 'Guion del audio')] },
  podcast_resumen: { fields: [area('script', 'Guion del audio')] },
  imagen_ilustrativa: { fields: [area('prompt', 'Descripción de la ilustración'), text('alt', 'Texto alternativo'), text('caption', 'Leyenda')] },
};

type Item = Record<string, string | boolean> | string;

export function structureSpec(type: ResourceType): StructureSpec | null {
  return STRUCTURE_SPECS[type] ?? null;
}

export function listItems(structure: ResourceStructure, spec: StructureSpec): Item[] {
  return spec.list ? ((structure[spec.list.key] as Item[] | undefined) ?? []) : [];
}

export function setField(structure: ResourceStructure, key: string, value: string): ResourceStructure {
  return { ...structure, [key]: value };
}

export function setItem(structure: ResourceStructure, spec: StructureSpec, index: number, key: string | null, value: string | boolean): ResourceStructure {
  if (!spec.list) return structure;
  const items = listItems(structure, spec).map((item, i) => {
    if (i !== index) return item;
    return key === null || typeof item === 'string' ? String(value) : { ...item, [key]: value };
  });
  return { ...structure, [spec.list.key]: items };
}

export function addItem(structure: ResourceStructure, spec: StructureSpec): ResourceStructure {
  if (!spec.list) return structure;
  const fields = spec.list.fields;
  const blank: Item = fields === 'string' ? '' : Object.fromEntries(fields.map((f) => [f.key, f.kind === 'boolean' ? true : '']));
  return { ...structure, [spec.list.key]: [...listItems(structure, spec), blank] };
}

export function removeItem(structure: ResourceStructure, spec: StructureSpec, index: number): ResourceStructure {
  if (!spec.list) return structure;
  return { ...structure, [spec.list.key]: listItems(structure, spec).filter((_, i) => i !== index) };
}

export function moveItem(structure: ResourceStructure, spec: StructureSpec, index: number, delta: -1 | 1): ResourceStructure {
  if (!spec.list) return structure;
  const items = [...listItems(structure, spec)];
  const target = index + delta;
  if (target < 0 || target >= items.length) return structure;
  [items[index], items[target]] = [items[target], items[index]];
  return { ...structure, [spec.list.key]: items };
}

/** Problema que impide guardar la estructura editada, o null. */
export function structureProblem(type: ResourceType, structure: ResourceStructure): string | null {
  const spec = structureSpec(type);
  if (!spec) return null;
  for (const field of spec.fields) {
    const value = structure[field.key as keyof ResourceStructure];
    if (field.key !== 'alt' && field.key !== 'caption' && (typeof value !== 'string' || !value.trim())) return `Completa «${field.label}».`;
  }
  if (spec.list) {
    const items = listItems(structure, spec);
    const complete = items.filter((item) =>
      typeof item === 'string' ? item.trim() : (spec.list!.fields as FieldSpec[]).every((f) => f.kind === 'boolean' || f.optional || String(item[f.key] ?? '').trim()),
    );
    if (complete.length !== items.length) return `Completa o quita los elementos vacíos de «${spec.list.label}».`;
    if (items.length < spec.list.min) return `Agrega al menos ${spec.list.min} elementos en «${spec.list.label}».`;
    if (type === 'verdadero_falso') {
      const answers = new Set((items as Record<string, unknown>[]).map((i) => Boolean(i.isTrue)));
      if (answers.size < 2) return 'Incluye afirmaciones verdaderas y falsas.';
    }
    if (type === 'completar_espacios' && (items as Record<string, string>[]).some((i) => !/_{3,}/.test(i.sentence) && !i.sentence.toLowerCase().includes(i.answer.toLowerCase()))) {
      return 'Cada oración debe tener ____ en el lugar de la respuesta.';
    }
  }
  return null;
}
