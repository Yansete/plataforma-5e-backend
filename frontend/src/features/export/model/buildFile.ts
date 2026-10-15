// Existing client-side export, retained until the backend export endpoint is integrated.
import { buildMoodleXml, buildQti21Package } from '@/features/export/model/fileBuilders';
import { buildUnitDocument } from '@/features/export/model/unitDocument';
import { fileNameFor, formatInfo, resourcesFor, slug } from '@/features/export/model/exportFormats';
import type { Course, DownloadFormat, Resource, Unit } from '@/shared/types/domain';

export interface BuiltFile {
  fileName: string;
  mimeType: string;
  data: string | Uint8Array;
  resourceCount: number;
}

export function buildFile(format: DownloadFormat, selected: Resource[], course: Course, unit: Unit, date = new Date()): BuiltFile {
  const resources = resourcesFor(format, selected);
  const info = formatInfo(format);
  const fileName = fileNameFor(course, unit, format);
  const label = `${course.code} · Unidad ${unit.number}`;
  let data: string | Uint8Array;
  if (format === 'moodle_xml') data = buildMoodleXml(resources, label);
  else if (format === 'qti21') data = buildQti21Package(resources, `${slug(course.code)}-unidad-${unit.number}`);
  else data = buildUnitDocument(resources, course, unit, date);
  return { fileName, mimeType: info.mimeType, data, resourceCount: resources.length };
}
