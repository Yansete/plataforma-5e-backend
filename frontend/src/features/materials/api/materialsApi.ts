/** Material de la unidad: subir y procesar archivos, buscar un tema y ver los fragmentos. */
import { apiFetch } from '@/shared/api/httpClient';
import { MAX_FILE_MB } from '@/features/generation/model/resourceCatalog';
import type { Fragment, MaterialDocument } from '@/shared/types/domain';

export const listDocuments = () => apiFetch<MaterialDocument[]>('/api/v1/documents');

export function unitDocuments(documents: MaterialDocument[], unitId: string): MaterialDocument[] {
  return documents.filter((d) => d.unitId === unitId);
}

/** Problema del archivo elegido, o null si se puede subir. */
export function fileProblem(file: { name: string; size: number }): string | null {
  const extension = file.name.split('.').pop()?.toLowerCase();
  if (!extension || !['pdf', 'pptx', 'txt'].includes(extension)) return 'Usa un archivo PDF, PPTX o TXT.';
  if (file.size === 0) return 'El archivo está vacío.';
  if (file.size > MAX_FILE_MB * 1024 * 1024) return `El archivo supera los ${MAX_FILE_MB} MB.`;
  return null;
}

export interface UploadContext {
  unitId: string;
  outcomeIds: string[];
  documentType: string;
}

/** Guarda el archivo en el servidor y lo procesa (texto y fragmentos). `onStep` informa en qué paso va. */
export async function uploadAndProcess(file: File, context: UploadContext, onStep?: (step: 'subiendo' | 'procesando') => void): Promise<MaterialDocument> {
  const form = new FormData();
  form.append('file', file);
  form.append('context', JSON.stringify({ ...context, suggestedStage: null, usePermission: true }));
  onStep?.('subiendo');
  const saved = await apiFetch<MaterialDocument>('/api/v1/documents', { method: 'POST', form, timeoutMs: 120000 });
  onStep?.('procesando');
  return processDocument(saved.id);
}

export const processDocument = (id: string) =>
  apiFetch<MaterialDocument>(`/api/v1/documents/${encodeURIComponent(id)}/process`, { method: 'POST', timeoutMs: 180000 });

export const listFragments = (id: string) => apiFetch<Fragment[]>(`/api/v1/documents/${encodeURIComponent(id)}/chunks`);

export const deleteDocument = (id: string) => apiFetch<void>(`/api/v1/documents/${encodeURIComponent(id)}`, { method: 'DELETE' });

/** Busca el tema en fuentes abiertas y deja cada documento encontrado procesado en la unidad. */
export const searchTopic = (unitId: string, topic: string, maxResults: number) =>
  apiFetch<MaterialDocument[]>('/api/v1/documents/from-topic', { method: 'POST', json: { unitId, topic: topic.trim(), maxResults }, timeoutMs: 180000 });

export function materialSummary(documents: MaterialDocument[]): { processed: number; withError: number } {
  const processed = documents.filter((d) => d.status === 'procesado');
  return {
    processed: processed.length,
    withError: documents.filter((d) => d.status === 'error').length,
  };
}
