/**
 * Cliente HTTP del backend: añade la sesión, traduce los errores a mensajes para el docente y
 * cierra la sesión si el servidor dice que venció.
 */
import { apiUrl } from '@/config/env';
import { getSession, setSession } from '@/shared/api/sessionStore';

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  json?: unknown;
  form?: FormData;
  timeoutMs?: number;
  /** false: no envía la sesión (iniciar sesión, crear cuenta). */
  auth?: boolean;
}

export const CONNECTION_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Si es la primera conexión del día, espera un minuto y vuelve a intentar.';
export const TIMEOUT_ERROR_MESSAGE = 'El servidor tardó demasiado en responder. Vuelve a intentar.';

export async function apiFetch<T>(path: string, { method = 'GET', json, form, timeoutMs = 30000, auth = true }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const session = auth ? getSession() : null;
  if (session) headers.Authorization = `Bearer ${session.token}`;
  let body: BodyInit | undefined;
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  } else if (form) {
    body = form;
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(apiUrl(path), { method, headers, body, signal: controller.signal });
  } catch (error) {
    const aborted = (error as Error)?.name === 'AbortError';
    throw new ApiError(0, aborted ? 'TIEMPO_AGOTADO' : 'SIN_CONEXION', aborted ? TIMEOUT_ERROR_MESSAGE : CONNECTION_ERROR_MESSAGE);
  } finally {
    clearTimeout(timer);
  }
  if (response.status === 204) return undefined as T;
  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    const error = (data as { error?: { codigo?: string; mensaje?: string } } | null)?.error;
    if (response.status === 401 && session) setSession(null);
    throw new ApiError(response.status, error?.codigo ?? `HTTP_${response.status}`, error?.mensaje ?? 'El servidor no pudo completar la operación. Vuelve a intentar.');
  }
  return data as T;
}

/** Mensaje para mostrar de cualquier error. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return 'Ocurrió un error inesperado. Vuelve a intentar.';
}
