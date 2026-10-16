# Frontend · SPA de Platform 5E

React 18, TypeScript y Vite. Se despliega en Vercel (Root Directory: `frontend`). Habla con el backend solo por HTTP: en local, Vite reenvía `/api` a `http://127.0.0.1:8000`; en Vercel, `VITE_API_URL` apunta al backend en Render.

## Requisitos

Node.js 22 LTS (mínimo 18).

## Comandos

| Comando | Qué hace |
| --- | --- |
| `npm ci` | Instala las dependencias exactas de `package-lock.json` |
| `npm run dev` | Servidor de desarrollo en http://localhost:5173 |
| `npm run typecheck` | Comprueba los tipos de TypeScript |
| `npm test` | Pruebas unitarias (Vitest) |
| `npm run test:cobertura` | Pruebas con cobertura (umbral 80 %) |
| `npm run build` | Versión de producción en `dist/` |
| `npm run preview` | Sirve `dist/` en http://localhost:4173 |
| `npm run test:e2e` | Recorrido en Chromium con el backend real (requiere `pip install -e ../backend`) |

## Variables de entorno

Ver [`.env.example`](.env.example).
