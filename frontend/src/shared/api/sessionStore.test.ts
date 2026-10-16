import { describe, expect, it, afterEach, vi } from 'vitest';
import { getSession, onSessionChange, setSession } from '@/shared/api/sessionStore';

afterEach(() => { setSession(null); vi.unstubAllGlobals(); });


describe('sesión del navegador', () => {
  it('avisa los cambios de sesión y deja de avisar al desuscribirse', () => {
    const listener = vi.fn();
    const off = onSessionChange(listener);
    setSession({ email: 'a@b.pe', name: 'Ana', token: 't' });
    expect(getSession()?.name).toBe('Ana');
    off();
    setSession(null);
    expect(listener).toHaveBeenCalledTimes(1);
    expect(getSession()).toBeNull();
  });

  it('lee y guarda la sesión en el almacenamiento del navegador', async () => {
    const data = new Map<string, string>([['plataforma-docente.sesion', JSON.stringify({ email: 'a@b.pe', name: 'Ana', token: 'guardado' })]]);
    vi.stubGlobal('localStorage', { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => data.set(k, v), removeItem: (k: string) => data.delete(k) });
    vi.resetModules();
    const fresh = await import('@/shared/api/sessionStore');
    expect(fresh.getSession()?.token).toBe('guardado');
    expect(JSON.parse(data.get('platform5e.session')!).token).toBe('guardado');
    expect(data.has('plataforma-docente.sesion')).toBe(false);
    fresh.setSession(null);
    expect(data.has('plataforma-docente.sesion')).toBe(false);
    fresh.setSession({ email: 'b@c.pe', name: 'Beto', token: 'nuevo' });
    expect(JSON.parse(data.get('platform5e.session')!).token).toBe('nuevo');
  });

  it('ignora una sesión guardada que no se puede leer', async () => {
    vi.stubGlobal('localStorage', { getItem: () => '{roto', setItem: () => undefined, removeItem: () => undefined });
    vi.resetModules();
    expect((await import('@/shared/api/sessionStore')).getSession()).toBeNull();
  });
});


describe('clave de sesión en inglés', () => {
  it('prefiere la clave nueva y al cerrar elimina ambas claves', async () => {
    const data = new Map([
      ['platform5e.session', JSON.stringify({ email: 'a@b.pe', name: 'Ana', token: 'actual' })],
      ['plataforma-docente.sesion', JSON.stringify({ email: 'a@b.pe', name: 'Ana', token: 'anterior' })],
    ]);
    vi.stubGlobal('localStorage', { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => data.set(k, v), removeItem: (k: string) => data.delete(k) });
    vi.resetModules();
    const session = await import('@/shared/api/sessionStore');
    expect(session.getSession()?.token).toBe('actual');
    session.setSession(null);
    expect(data.size).toBe(0);
  });

  it('conserva la sesión en memoria cuando el navegador bloquea el almacenamiento', async () => {
    vi.stubGlobal('localStorage', { getItem: () => { throw new Error('denegado'); }, setItem: () => { throw new Error('denegado'); }, removeItem: () => { throw new Error('denegado'); } });
    vi.resetModules();
    const session = await import('@/shared/api/sessionStore');
    expect(session.getSession()).toBeNull();
    session.setSession({ email: 'a@b.pe', name: 'Ana', token: 'memoria' });
    expect(session.getSession()?.token).toBe('memoria');
    session.setSession(null);
    expect(session.getSession()).toBeNull();
  });
});
