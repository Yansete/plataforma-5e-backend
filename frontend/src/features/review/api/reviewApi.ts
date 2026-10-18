import { apiBlob, apiFetch } from '@/shared/api/httpClient';
import { generate } from '@/features/generation/api/generationApi';
import { hasOptions } from '@/features/generation/model/resourceCatalog';
import { setStatus } from '@/features/review/model/reviewRules';
import type { Resource } from '@/shared/types/domain';

/* ——— Servidor ——— */

const base = (unitId: string) => `/api/v1/units/${encodeURIComponent(unitId)}/resources`;

export const listResources = (unitId: string) => apiFetch<Resource[]>(base(unitId));

export function reviewBody(resource: Resource) {
  return {
    title: resource.title,
    body: resource.body,
    status: resource.status,
    discardReason: resource.status === 'descartado' ? resource.discardReason : null,
    edited: resource.edited,
    ...(resource.bodyHtml !== undefined ? { bodyHtml: resource.bodyHtml } : {}),
    ...(resource.structure ? { structure: resource.structure } : {}),
    options: resource.options?.map((o) => ({
      id: o.id,
      text: o.text,
      feedback: o.feedback,
      decision: o.decision,
      discardReason: o.decision === 'descartado' ? o.discardReason : null,
      edited: o.edited,
    })) ?? null,
  };
}

export const saveResource = (resource: Resource) =>
  apiFetch<Resource>(`${base(resource.unitId)}/${encodeURIComponent(resource.id)}`, { method: 'PUT', json: reviewBody(resource) });

/** Gráfico (SVG), imagen o audio del recurso, para mostrarlo en la revisión. */
export const fetchResourceMedia = (resource: Resource) =>
  apiBlob(`${base(resource.unitId)}/${encodeURIComponent(resource.id)}/media`);

/** Vuelve a generar la imagen o el audio con la descripción o el guion actual (por ejemplo, después de editarlo). */
export const regenerateMedia = (resource: Resource) =>
  apiFetch<Resource>(`${base(resource.unitId)}/${encodeURIComponent(resource.id)}/media`, { method: 'POST', timeoutMs: 150000 });

export const deleteResource = (resource: Resource) =>
  apiFetch<void>(`${base(resource.unitId)}/${encodeURIComponent(resource.id)}`, { method: 'DELETE' });

/**
 * Pide una versión nueva con los mismos parámetros y deja la anterior en «Descartados»
 * (motivo: reemplazado por una nueva versión). Devuelve los recursos nuevos.
 */
export async function regenerate(resource: Resource): Promise<{ created: Resource[]; usedFallback: boolean; replaced: Resource }> {
  const p = resource.params;
  const result = await generate({
    unitId: resource.unitId,
    outcomeId: p ? p.outcomeId : resource.outcomeId || null,
    resourceType: p?.resourceType ?? resource.type,
    quantity: 1,
    difficulty: p?.difficulty ?? 'intermedia',
    optionCount: p?.optionCount ?? (hasOptions(resource.type) ? resource.options?.length || 4 : 4),
    instructions: p?.instructions ?? '',
    audience: p?.audience ?? '',
    competency: p?.competency ?? '',
    modalities: p?.modalities ?? [],
  });
  const replaced = await saveResource(setStatus(resource, 'descartado', 'regenerado'));
  return { created: result.resources, usedFallback: result.usedFallback, replaced };
}
