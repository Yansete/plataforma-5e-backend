/** Historial de descargas guardado en el servidor y paquete SCORM armado en el backend. */
import { apiDownload, apiFetch } from '@/shared/api/httpClient';
import type { BuiltFile } from '@/features/export/model/buildFile';
import type { Download, DownloadFormat } from '@/shared/types/domain';

/* ——— Historial en el servidor ——— */

const base = (unitId: string) => `/api/v1/unidades/${encodeURIComponent(unitId)}/descargas`;

export const listDownloads = (unitId: string) => apiFetch<Download[]>(base(unitId));

export const registerDownload = (unitId: string, file: Pick<BuiltFile, 'fileName' | 'resourceCount'>, format: DownloadFormat) =>
  apiFetch<Download>(base(unitId), { method: 'POST', json: { format, fileName: file.fileName, resourceCount: file.resourceCount } });

export const clearDownloads = (unitId: string) => apiFetch<void>(base(unitId), { method: 'DELETE' });

/** Paquete SCORM 1.2 para Chamilo: lo arma el backend, que además registra la descarga en el historial. */
export const exportUnit = (unitId: string, format: DownloadFormat, resourceIds: string[]) =>
  apiDownload(`/api/v1/units/${encodeURIComponent(unitId)}/exports`, { format, resourceIds });
