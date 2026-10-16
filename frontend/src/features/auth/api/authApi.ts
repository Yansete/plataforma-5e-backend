/** Cuentas y sesión del docente. */
import { apiFetch } from '@/shared/api/httpClient';
import { setSession } from '@/shared/api/sessionStore';
import type { Session } from '@/shared/types/domain';

interface SessionResponse {
  email: string;
  name: string;
  token: string;
}

/** El servidor gratuito puede tardar cerca de un minuto en despertar: la primera petición espera más. */
const WAKE_UP_TIMEOUT_MS = 90000;

function open(response: SessionResponse): Session {
  const session = { email: response.email, name: response.name, token: response.token };
  setSession(session);
  return session;
}

export async function login(email: string, password: string): Promise<Session> {
  return open(await apiFetch<SessionResponse>('/api/v1/sesiones', { method: 'POST', json: { email, password }, auth: false, timeoutMs: WAKE_UP_TIMEOUT_MS }));
}

export async function register(name: string, email: string, password: string): Promise<Session> {
  return open(await apiFetch<SessionResponse>('/api/v1/cuentas', { method: 'POST', json: { name, email, password }, auth: false, timeoutMs: WAKE_UP_TIMEOUT_MS }));
}

export async function logout(): Promise<void> {
  try {
    await apiFetch<void>('/api/v1/sesiones/actual', { method: 'DELETE' });
  } catch {
    /* aunque el servidor no responda, la sesión se cierra en este navegador */
  } finally {
    setSession(null);
  }
}

/** Revisa los datos de la cuenta antes de enviarlos. Devuelve el primer problema o null. */
export function registrationProblem(name: string, email: string, password: string, confirm: string): string | null {
  if (name.trim().length < 2) return 'Escribe tu nombre.';
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) return 'Escribe un correo válido.';
  if (password.length < 8) return 'La contraseña debe tener al menos 8 caracteres.';
  if (password !== confirm) return 'Las contraseñas no coinciden.';
  return null;
}
