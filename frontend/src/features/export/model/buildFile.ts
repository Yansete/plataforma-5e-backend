// Moodle XML y el documento de la unidad se arman en el navegador; el paquete SCORM lo arma el backend (exportUnit).
import { buildMoodleXml } from '@/features/export/model/fileBuilders';
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
  const label = `${course.code} · Unidad ${unit.number}`;
  let data: string;
  if (format === 'moodle_xml') data = buildMoodleXml(resources, label);
  else data = buildUnitDocument(resources, course, unit, date);
  return { fileName, mimeType: info.mimeType, data, resourceCount: resources.length };
}
