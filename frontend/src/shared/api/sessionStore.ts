import type { Session } from '@/shared/types/domain';

const SESSION_KEY = 'platform5e.session';
const LEGACY_SESSION_KEY = 'plataforma-docente.sesion';
const listeners = new Set<() => void>();
let cached: Session | null | undefined;

function storage(): Storage | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage;
  } catch {
    return null;
  }
}

export function getSession(): Session | null {
  if (cached !== undefined) return cached;
  try {
    const store = storage();
    const raw = store?.getItem(SESSION_KEY) ?? store?.getItem(LEGACY_SESSION_KEY);
    const parsed = raw ? (JSON.parse(raw) as Session) : null;
    cached = parsed && typeof parsed.token === 'string' ? parsed : null;
  } catch {
    cached = null;
  }
  if (cached) {
    try {
      storage()?.setItem(SESSION_KEY, JSON.stringify(cached));
      storage()?.removeItem(LEGACY_SESSION_KEY);
    } catch { /* Keep the in-memory session if storage is unavailable. */ }
  }
  return cached;
}

export function setSession(session: Session | null): void {
  cached = session;
  try {
    if (session) storage()?.setItem(SESSION_KEY, JSON.stringify(session));
    else storage()?.removeItem(SESSION_KEY);
    storage()?.removeItem(LEGACY_SESSION_KEY);
  } catch {
    /* sin almacenamiento: la sesión dura mientras la pestaña esté abierta */
  }
  listeners.forEach((listener) => listener());
}

export function onSessionChange(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
