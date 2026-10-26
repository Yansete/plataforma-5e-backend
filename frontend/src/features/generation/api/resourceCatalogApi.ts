/** Tipos y etiquetas publicados por el backend; no mantiene una copia local de producción. */
import { ApiError, apiFetch } from '@/shared/api/httpClient';
import { installResourceCatalog } from '@/features/generation/model/resourceCatalog';

let pending: Promise<void> | null = null;

async function requestResourceCatalog(): Promise<void> {
  const response = await apiFetch<unknown>('/api/v1/resource-types', { auth: false });
  try {
    installResourceCatalog(response);
  } catch {
    throw new ApiError(502, 'INVALID_RESOURCE_CATALOG', 'No se pudo cargar el catálogo de recursos. Vuelve a intentar.');
  }
}

/** Comparte la petición en curso, también durante el montaje doble de StrictMode. */
export function loadResourceCatalog(): Promise<void> {
  if (!pending) pending = requestResourceCatalog().finally(() => { pending = null; });
  return pending;
}
