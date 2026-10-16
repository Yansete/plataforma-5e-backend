import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, CONNECTION_ERROR_MESSAGE, TIMEOUT_ERROR_MESSAGE, apiFetch, errorMessage } from '@/shared/api/httpClient';
import { getSession, setSession } from '@/shared/api/sessionStore';
import { mockFetch } from '@/test/fixtures';

afterEach(() => { setSession(null); vi.unstubAllGlobals(); });

describe('apiFetch', () => {
  it('envía la sesión y el cuerpo JSON y devuelve la respuesta', async () => {
    setSession({ email: 'a@b.pe', name: 'Ana', token: 'tok' });
    const calls = mockFetch({ body: { ok: true } });
    await expect(apiFetch('/api/v1/courses', { method: 'POST', json: { a: 1 } })).resolves.toEqual({ ok: true });
    expect(calls[0]).toMatchObject({ url: '/api/v1/courses', method: 'POST', body: { a: 1 } });
    expect(calls[0].headers).toMatchObject({ Authorization: 'Bearer tok', 'Content-Type': 'application/json' });
  });

  it('no envía la sesión cuando auth es false y acepta formularios', async () => {
    setSession({ email: 'a@b.pe', name: 'Ana', token: 'tok' });
    const calls = mockFetch({ status: 204 });
    const form = new FormData();
    await expect(apiFetch('/x', { method: 'POST', form, auth: false })).resolves.toBeUndefined();
    expect(calls[0].headers.Authorization).toBeUndefined();
    expect(calls[0].body).toBe(form);
  });

  it('traduce el error del servidor y cierra la sesión vencida', async () => {
    setSession({ email: 'a@b.pe', name: 'Ana', token: 'tok' });
    mockFetch({ status: 401, body: { error: { code: 'SESSION_EXPIRED', message: 'La sesión venció.' } } });
    const error = await apiFetch('/x').catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 401, code: 'SESSION_EXPIRED', message: 'La sesión venció.' });
    expect(getSession()).toBeNull();
  });

  it('usa un mensaje general si el error no trae detalle', async () => {
    mockFetch({ status: 500, body: null });
    await expect(apiFetch('/x')).rejects.toMatchObject({ code: 'HTTP_500', message: expect.stringMatching(/no pudo completar/) });
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>', { status: 502 })));
    await expect(apiFetch('/x')).rejects.toMatchObject({ code: 'HTTP_502' });
  });

  it('distingue sin conexión de tiempo agotado', async () => {
    mockFetch(new TypeError('Failed to fetch'));
    await expect(apiFetch('/x')).rejects.toMatchObject({ status: 0, code: 'NO_CONNECTION', message: CONNECTION_ERROR_MESSAGE });
    vi.stubGlobal(
      'fetch',
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => init.signal?.addEventListener('abort', () => reject(Object.assign(new Error('abortado'), { name: 'AbortError' })))),
    );
    await expect(apiFetch('/x', { timeoutMs: 5 })).rejects.toMatchObject({ code: 'TIMEOUT', message: TIMEOUT_ERROR_MESSAGE });
  });

  it('errorMessage muestra el mensaje de la API o uno general', () => {
    expect(errorMessage(new ApiError(400, 'X', 'Detalle'))).toBe('Detalle');
    expect(errorMessage(new Error('interno'))).toMatch(/inesperado/);
  });
});
