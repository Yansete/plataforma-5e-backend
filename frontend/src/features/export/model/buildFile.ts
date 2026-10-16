// El documento de la unidad se arma en el navegador; los archivos para Moodle y Chamilo los arma el backend (exportUnit).
import { buildUnitDocument } from '@/features/export/model/unitDocument';
import { fileNameFor, formatInfo, resourcesFor } from '@/features/export/model/exportFormats';
import type { Course, DownloadFormat, Resource, Unit } from '@/shared/types/domain';

export interface BuiltFile {
  fileName: string;
  mimeType: string;
  data: string;
  resourceCount: number;
}

export function buildFile(format: DownloadFormat, selected: Resource[], course: Course, unit: Unit, date = new Date()): BuiltFile {
  const resources = resourcesFor(format, selected);
  const info = formatInfo(format);
  const fileName = fileNameFor(course, unit, format);
  const data = buildUnitDocument(resources, course, unit, date);
  return { fileName, mimeType: info.mimeType, data, resourceCount: resources.length };
}
