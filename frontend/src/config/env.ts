/**
 * Dirección del backend. VITE_API_URL se fija al compilar (variable de entorno en Vercel), por ejemplo
 * https://plataforma5e-api.onrender.com. Si no se define, el frontend llama a /api en el mismo dominio
 * (en local, Vite lo redirige al puerto 8000).
 */
export const API_BASE_URL = (import.meta.env?.VITE_API_URL ?? '').trim().replace(/\/+$/, '');

/** Dirección completa de una ruta de la API, por ejemplo apiUrl('/api/v1/courses'). */
export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}
