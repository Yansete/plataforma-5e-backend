import type { DownloadFormat, Resource } from '@/shared/types/domain';

export interface FormatInfo {
  id: DownloadFormat;
  title: string;
  description: string;
  extension: 'xml' | 'zip' | 'html';
  mimeType: string;
  /** Moodle y Chamilo solo importan preguntas de opción múltiple. */
  onlyQuestions: boolean;
  /** Cómo usar el archivo. */
  howTo: string;
}

export const FORMATS: FormatInfo[] = [
  {
    id: 'moodle_xml',
    title: 'Moodle',
    description: 'Banco de preguntas en formato Moodle XML.',
    extension: 'xml',
    mimeType: 'application/xml',
    onlyQuestions: true,
    howTo: 'En Moodle: Banco de preguntas › Importar › Formato Moodle XML.',
  },
  {
    id: 'scorm_zip',
    title: 'Chamilo',
    description: 'Paquete SCORM 1.2: cada recurso aprobado es una página de la lección.',
    extension: 'zip',
    mimeType: 'application/zip',
    onlyQuestions: false,
    howTo: 'En Chamilo: Lecciones › Importar AICC, SCORM y Chamilo.',
  },
  {
    id: 'documento',
    title: 'Documento de la unidad',
    description: 'Todos los recursos aprobados, en el orden de la clase y con su evidencia. Para imprimir o compartir.',
    extension: 'html',
    mimeType: 'text/html',
    onlyQuestions: false,
    howTo: 'Se abre en cualquier navegador y se puede guardar como PDF.',
  },
];

export function formatInfo(id: DownloadFormat): FormatInfo {
  return FORMATS.find((f) => f.id === id) ?? FORMATS[0];
}

export function isQuestion(resource: Resource): boolean {
  return Boolean(resource.options?.length);
}

/** Recursos que entran en el archivo del formato elegido. */
export function resourcesFor(format: DownloadFormat, selected: Resource[]): Resource[] {
  const approved = selected.filter((r) => r.status === 'aprobado');
  return formatInfo(format).onlyQuestions ? approved.filter(isQuestion) : approved;
}
