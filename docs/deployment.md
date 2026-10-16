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
| Start Command | `uvicorn plataforma5e.bootstrap.app:crear_aplicacion --factory --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |
| Health Check Path | `/salud` |

3. Variables de entorno (*Environment*):

| Variable | Valor | Para qué |
|---|---|---|
| `PYTHON_VERSION` | `3.12.7` | Misma versión que la CI |
| `DATABASE_URL` | la *Connection string* de Neon | Base de datos persistente |
| `CORS_ORIGENES` | `https://plataforma-5e-taller-integrador.vercel.app` | Permite que el frontend publicado llame al backend |
| `IA_PROVEEDOR` | `gemini` (o `anthropic`, `openai`) | Proveedor del modelo de lenguaje |
| `IA_API_KEY` | la clave del proveedor | Sin clave se usa el generador por reglas |
| `IA_MODELO` | opcional | Por defecto `gemini-3.8-flash`, `claude-sonnet-5-5` o `gpt-5.4-mini` |
| `IA_URL_BASE` | opcional | Para servicios compatibles con la API de OpenAI |
| `BUSQUEDA_POR_TEMA` | `true` (por defecto) | `false` desactiva la búsqueda en Wikipedia |
| `EP002_DOCENTE_EMAIL` y `EP002_DOCENTE_PASSWORD` | opcional | Crean una cuenta inicial configurada en el servidor. Sin ellas, cada docente usa «Crear cuenta». |

`CATALOGO_DEMO` no se define en producción: solo lo usan las pruebas automáticas (curso y cuenta de ejemplo).

La clave de Gemini se crea en Google AI Studio (https://aistudio.google.com, opción *Get API key*). La clave solo
se escribe en *Environment* de Render: nunca en el código, en `vercel.json` ni en un commit.

4. **Create Web Service**. Al terminar, probar `https://<servicio>.onrender.com/salud` y
   `https://<servicio>.onrender.com/api/v1/ia` (dice qué generador está activo). Swagger queda en `/docs`.

Con «Public Git Repository» Render no se actualiza solo: después de cada cambio en la rama, usar
**Manual Deploy → Deploy latest commit**. El plan gratuito se apaga tras 15 minutos sin uso; la primera
petición después tarda cerca de un minuto (el inicio de sesión ya espera hasta 90 segundos).

## 3. Frontend (Vercel)

`frontend/vercel.json` compila con la dirección del backend (sin `/` al final):

```json
"buildCommand": "VITE_API_URL=https://plataforma5e-api.onrender.com npm run build"
```

Cada cambio integrado en `main` vuelve a publicar el mismo enlace. El frontend siempre trabaja con el backend: no hay
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
| La consola del navegador dice *CORS* | `CORS_ORIGENES` no coincide exactamente con el dominio de Vercel (sin `/` al final). |
| La generación avisa que «se usó el generador de respaldo» aunque hay clave | Revisar `IA_API_KEY` y `IA_PROVEEDOR`. El motivo exacto (clave inválida, límite 429, modelo inexistente…) queda en los *Logs* de Render, en la línea «Generación con respaldo: …». |
| La cuenta `docente@5e.demo` ya no entra | Desde esta versión la cuenta de ejemplo solo existe en las pruebas. Usar «Crear cuenta» o definir `EP002_DOCENTE_EMAIL` y `EP002_DOCENTE_PASSWORD`. |
| Un PDF queda en «error» | Es un PDF escaneado (imágenes, sin texto) o protegido: subir una versión con texto o un TXT. |
| Los datos desaparecen | `DATABASE_URL` no está definida y se está usando SQLite dentro del servidor, que se borra en cada despliegue. |
