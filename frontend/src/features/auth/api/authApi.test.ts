/** Cuentas: iniciar sesión, crear cuenta, cerrar sesión y validación del formulario. */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { getSession, setSession } from '@/shared/api/sessionStore';
import { login, logout, register, registrationProblem } from '@/features/auth/api/authApi';
import { mockFetch } from '@/test/fixtures';

afterEach(() => {
  setSession(null);
  vi.unstubAllGlobals();
});

describe('sesión', () => {
  it('inicia sesión sin enviar una sesión anterior y la guarda', async () => {
    const calls = mockFetch({ body: { email: 'ana@correo.pe', name: 'Ana', token: 't1', expiresIn: 10 } });
    const session = await login('ana@correo.pe', 'clave');
    expect(session).toEqual({ email: 'ana@correo.pe', name: 'Ana', token: 't1' });
    expect(getSession()?.token).toBe('t1');
    expect(calls[0]).toMatchObject({ url: '/api/v1/sessions', method: 'POST', body: { email: 'ana@correo.pe', password: 'clave' } });
    expect(calls[0].headers.Authorization).toBeUndefined();
  });

  it('crea la cuenta y entra', async () => {
    const calls = mockFetch({ status: 201, body: { email: 'b@c.pe', name: 'Beto', token: 't2', expiresIn: 10 } });
    await register('Beto', 'b@c.pe', 'clave-segura');
    expect(getSession()?.name).toBe('Beto');
    expect(calls[0]).toMatchObject({ url: '/api/v1/accounts', body: { name: 'Beto', email: 'b@c.pe', password: 'clave-segura' } });
  });

  it('cierra la sesión aunque el servidor no responda', async () => {
    setSession({ email: 'a@b.pe', name: 'Ana', token: 't' });
    const calls = mockFetch(new TypeError('sin red'));
    await logout();
    expect(calls[0]).toMatchObject({ url: '/api/v1/sessions/current', method: 'DELETE' });
    expect(getSession()).toBeNull();
  });

  it('revisa los datos de la cuenta antes de enviarlos', () => {
    expect(registrationProblem('A', 'a@b.pe', '12345678', '12345678')).toMatch(/nombre/);
    expect(registrationProblem('Ana', 'sin-arroba', '12345678', '12345678')).toMatch(/correo/);
    expect(registrationProblem('Ana', 'a@b.pe', 'corta', 'corta')).toMatch(/8 caracteres/);
    expect(registrationProblem('Ana', 'a@b.pe', '12345678', '87654321')).toMatch(/no coinciden/);
    expect(registrationProblem('Ana', ' a@b.pe ', '12345678', '12345678')).toBeNull();
  });
});
