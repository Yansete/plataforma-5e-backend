# Despliegue del sistema completo

El frontend sigue en Vercel (el mismo enlace de siempre) y ahora llama a un backend publicado en Render,
con la base de datos en Neon. Los tres servicios tienen plan gratuito y no piden tarjeta.

```
Navegador ──► Vercel (frontend React) ──► Render (backend FastAPI) ──► Neon (PostgreSQL)
                                                   └──► Gemini, Anthropic u OpenAI (si hay clave de IA)
                                                   └──► Wikipedia (búsqueda por tema)
```

## 1. Base de datos (Neon)

1. Entrar a https://neon.com, registrarse con GitHub y crear un proyecto en **AWS US East (N. Virginia)**.
2. Copiar la *Connection string* (empieza con `postgresql://`). El backend la acepta tal cual: la convierte
   al controlador psycopg 3 y desactiva las sentencias preparadas para funcionar con el *pooler* de Neon.

El backend crea sus tablas al arrancar (también las nuevas: `ep002_usuarios`, `ep002_recursos` y `ep002_descargas`);
no hace falta correr migraciones para este despliegue.

## 2. Backend (Render)

1. En https://render.com: **New → Web Service → Public Git Repository** y pegar
   `https://github.com/Yansete/plataforma-5e-taller-integrador`.
2. Configurar:

| Campo | Valor |
|---|---|
| Name | `plataforma5e-api` (Render agrega letras si el nombre está ocupado) |
| Region | Virginia (US East), la misma zona que la base de Neon |
| Branch | la rama a publicar (después del merge, `main`) |
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install .` |
| Start Command | `uvicorn platform5e.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |
| Health Check Path | `/health` |

3. Variables de entorno (*Environment*):

| Variable | Valor | Para qué |
|---|---|---|
| `PYTHON_VERSION` | `3.12.7` | Misma versión que la CI |
| `DATABASE_URL` | la *Connection string* de Neon | Base de datos persistente |
| `CORS_ALLOWED_ORIGINS` | `https://plataforma-5e-taller-integrador.vercel.app` | Permite que el frontend publicado llame al backend |
| `LLM_PROVIDER` | `gemini` (o `anthropic`, `openai`, `rules`) | Proveedor del modelo de lenguaje |
| `LLM_API_KEY` | la clave del proveedor | Sin clave se usa el generador por reglas |
| `LLM_MODEL` | opcional | Por defecto `gemini-3.8-flash`, `claude-sonnet-5-5` o `gpt-5.4-mini` |
| `LLM_BASE_URL` | opcional | Para servicios compatibles con la API de OpenAI |
| `LLM_TIMEOUT_SECONDS` | opcional | Tiempo de espera por respuesta (por defecto 90) |
| `TOPIC_SEARCH_ENABLED` | `true` (por defecto) | `false` desactiva la búsqueda en Wikipedia |
| `MEDIA_GENERATION_ENABLED` | `true` (por defecto) | Imágenes y voz con Gemini (necesita `LLM_PROVIDER=gemini`); `false` usa siempre los respaldos |
| `IMAGE_MODEL` | opcional | Por defecto `gemini-3.1-flash-lite-image`. La capa gratuita de Gemini no genera imágenes: requiere facturación |
| `SPEECH_MODEL` y `SPEECH_VOICE` | opcional | Por defecto `gemini-3.8-flash-tts` y la voz `Kore` |
| `BOOTSTRAP_TEACHER_EMAIL` y `BOOTSTRAP_TEACHER_PASSWORD` | opcional | Crean una cuenta inicial configurada en el servidor. Sin ellas, cada docente usa «Crear cuenta». |

`DEMO_CATALOG` no se define en producción: solo lo usan las pruebas automáticas (curso y cuenta de ejemplo).

Los nombres anteriores en español (`CORS_ORIGENES`, `IA_PROVEEDOR`, `IA_API_KEY`, `IA_MODELO`, `IA_URL_BASE`,
`BUSQUEDA_POR_TEMA`, `EP002_DOCENTE_EMAIL`, `EP002_DOCENTE_PASSWORD`, `CATALOGO_DEMO`) se siguen leyendo si el nombre
nuevo no está definido (`backend/src/platform5e/infrastructure/settings.py`). Conviene renombrarlos en el panel de Render
cuanto antes; el Sprint 2 quita la compatibilidad.

La clave de Gemini se crea en Google AI Studio (https://aistudio.google.com, opción *Get API key*). La clave solo
se escribe en *Environment* de Render: nunca en el código, en `vercel.json` ni en un commit.

4. **Create Web Service**. Al terminar, probar `https://<servicio>.onrender.com/health` y
   `https://<servicio>.onrender.com/api/v1/generator` (dice qué generador está activo). Swagger queda en `/docs` y
   ReDoc en `/redoc`.

Con «Public Git Repository» Render no se actualiza solo: después de cada cambio en la rama, usar
**Manual Deploy → Deploy latest commit**. El plan gratuito se apaga tras 15 minutos sin uso; la primera
petición después tarda cerca de un minuto (el inicio de sesión ya espera hasta 90 segundos).

## 3. Frontend (Vercel)

La dirección del backend no está en el código: es una variable de entorno del proyecto en Vercel
(*Settings → Environment Variables*), marcada para *Production* y *Preview*, sin `/` al final:

```
VITE_API_URL=https://plataforma5e-api.onrender.com
```

`frontend/vercel.json` solo ejecuta `npm run build`; Vite lee la variable al compilar. Si cambia la dirección
del backend, se edita la variable y se vuelve a desplegar (*Redeploy*). El *Root Directory* del proyecto es `frontend`.

Para no gastar despliegues cuando un cambio solo toca el backend o la documentación, *Settings → Git →
Ignored Build Step* usa la opción *Custom* con este comando (sale con código 0 y cancela el despliegue si nada
cambió dentro de `frontend/`):

```
git diff HEAD^ HEAD --quiet -- .
```

Cada cambio integrado en `main` que toque `frontend/` vuelve a publicar el mismo enlace. El frontend siempre trabaja con el backend: no hay
modo local ni datos de demostración.

## 4. Comprobación

1. Abrir el enlace de Vercel → **Crear cuenta** (la primera conexión del día puede tardar un minuto).
2. **Nuevo curso** con sumilla, logro, una unidad y sus resultados de aprendizaje.
3. Abrir la unidad → **Material**: subir un PDF, PPTX o TXT (o buscar el tema) y ver sus fragmentos.
4. **Generación**: elegir opciones o escribir el pedido → generar.
5. **Revisión**: decidir los distractores → aprobar. Recargar la página: lo revisado sigue ahí.
6. **Exportación**: descargar para Moodle (.xml), Chamilo (.zip) o el documento de la unidad (.html); el archivo lleva el
   código del curso y el número de la unidad. Probar «Borrar historial».

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| «No se pudo conectar con el servidor» al iniciar sesión | El servicio está despertando: esperar un minuto y reintentar. Si persiste, revisar los *Logs* de Render. |
| La consola del navegador dice *CORS* | `CORS_ALLOWED_ORIGINS` no coincide exactamente con el dominio de Vercel (sin `/` al final). |
| La generación avisa que «se usó el generador de respaldo» aunque hay clave | Revisar `LLM_API_KEY` y `LLM_PROVIDER`. El motivo exacto (clave inválida, límite 429, modelo inexistente…) queda en los *Logs* de Render, en la línea «Generación con respaldo: …». |
| La cuenta `docente@5e.demo` ya no entra | Desde esta versión la cuenta de ejemplo solo existe en las pruebas. Usar «Crear cuenta» o definir `BOOTSTRAP_TEACHER_EMAIL` y `BOOTSTRAP_TEACHER_PASSWORD`. |
| Un PDF queda en «error» | Es un PDF escaneado (imágenes, sin texto) o protegido: subir una versión con texto o un TXT. |
| Los datos desaparecen | `DATABASE_URL` no está definida y se está usando SQLite dentro del servidor, que se borra en cada despliegue. |
