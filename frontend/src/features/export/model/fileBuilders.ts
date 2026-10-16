/**
 * Utilidades del documento de la unidad. Los archivos para Moodle (Moodle XML) y Chamilo (SCORM 1.2)
 * los arma el backend con plantillas fijas (ADR-005, ADR-007).
 *
 * Solo se muestran los distractores que el docente aceptó o editó, más la clave.
 */
import type { ItemOption, Resource } from '@/shared/types/domain';

/** Escapa texto para atributos y nodos XML. */
export function escapeXml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}

/** Clave y distractores que se exportan: los descartados quedan fuera. */
export function exportedOptions(resource: Resource): ItemOption[] {
  return (resource.options ?? []).filter((o) => o.isCorrect || o.decision !== 'descartado');
}
