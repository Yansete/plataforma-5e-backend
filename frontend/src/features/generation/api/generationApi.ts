/** Generación de recursos con el material de la unidad. */
import { apiFetch, errorMessage } from '@/shared/api/httpClient';
import { hasOptions, typeInfo } from '@/features/generation/model/resourceCatalog';
import type { GenerationInput, Resource, ResourceType } from '@/shared/types/domain';

/** Generar con IA puede tardar cerca de un minuto. */
export const GENERATION_TIMEOUT_MS = 150000;

export function generationBody(input: GenerationInput) {
  return {
    unitId: input.unitId,
    outcomeId: input.outcomeId,
    stage: typeInfo(input.resourceType).stage,
    resourceType: input.resourceType,
    quantity: Math.min(5, Math.max(1, Math.round(input.quantity))),
    difficulty: input.difficulty,
    optionCount: hasOptions(input.resourceType) ? input.optionCount : 4,
    topK: 8,
    evidenceThreshold: 0.6,
    instructions: input.instructions.trim().slice(0, 500),
    audience: input.audience.trim().slice(0, 200),
    competency: input.competency.trim().slice(0, 200),
    modalities: input.modalities,
  };
}

export interface GenerationResult {
  resources: Resource[];
  /** true: la IA no respondió y se usó el generador de respaldo. */
  usedFallback: boolean;
}

interface GenerationResponse {
  resources: Resource[];
  generator?: { fallback?: boolean } | null;
}

export async function generate(input: GenerationInput): Promise<GenerationResult> {
  const response = await apiFetch<GenerationResponse>('/api/v1/generations', { method: 'POST', json: generationBody(input), timeoutMs: GENERATION_TIMEOUT_MS });
  return { resources: response.resources ?? [], usedFallback: Boolean(response.generator?.fallback) };
}

export interface BatchProgress {
  done: number;
  total: number;
  current: ResourceType;
}

export interface BatchResult {
  resources: Resource[];
  /** Tipos que no se pudieron generar, con el motivo. */
  failed: { type: ResourceType; message: string }[];
  /** Tipos que redactó el generador de respaldo. */
  fallbackTypes: ResourceType[];
}

/**
 * Varios tipos de recurso en un solo pedido del docente: uno tras otro (la IA gratuita limita las solicitudes
 * por minuto). Si un tipo falla, los demás se generan igual.
 */
export async function generateMany(input: GenerationInput, types: ResourceType[], onProgress?: (p: BatchProgress) => void): Promise<BatchResult> {
  const result: BatchResult = { resources: [], failed: [], fallbackTypes: [] };
  for (const [index, type] of types.entries()) {
    onProgress?.({ done: index, total: types.length, current: type });
    try {
      const generated = await generate({ ...input, resourceType: type });
      result.resources.push(...generated.resources);
      if (generated.usedFallback) result.fallbackTypes.push(type);
    } catch (error) {
      result.failed.push({ type, message: errorMessage(error) });
    }
  }
  onProgress?.({ done: types.length, total: types.length, current: types[types.length - 1] });
  return result;
}

export function defaultInput(unitId: string): GenerationInput {
  return {
    unitId,
    outcomeId: null,
    resourceType: 'item_opcion_multiple',
    quantity: 2,
    difficulty: 'intermedia',
    optionCount: 4,
    instructions: '',
    audience: '',
    competency: '',
    modalities: ['Textual'],
  };
}
