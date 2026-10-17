/** Historial y archivos de Moodle, Chamilo y HTML gestionados por el backend. */
import { apiDownload, apiFetch } from '@/shared/api/httpClient';
import type { Download, DownloadFormat } from '@/shared/types/domain';

/* ——— Historial en el servidor ——— */

const base = (unitId: string) => `/api/v1/units/${encodeURIComponent(unitId)}/downloads`;

export const listDownloads = (unitId: string) => apiFetch<Download[]>(base(unitId));

export const clearDownloads = (unitId: string) => apiFetch<void>(base(unitId), { method: 'DELETE' });

/** Archivo para Moodle, Chamilo o documento HTML: lo arma el backend, que además registra la descarga en el historial. */
export const exportUnit = (unitId: string, format: DownloadFormat, resourceIds: string[]) =>
  apiDownload(`/api/v1/units/${encodeURIComponent(unitId)}/exports`, { format, resourceIds });
