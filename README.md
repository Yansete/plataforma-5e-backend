# Platform 5E · Plataforma Docente

Generación asistida de recursos educativos a partir del material del docente: modelo instruccional 5E, recuperación de evidencia (RAG), revisión docente obligatoria y exportación a Moodle (XML) y Chamilo (SCORM 1.2). Proyecto del curso Taller Integrador 1 (UPAO, 2026-II).

**Repositorio del backend de Plataforma 5E.** La API se encuentra en `backend/`. El frontend se mantiene en [su propio repositorio](https://github.com/Yansete/plataforma-5e-frontend). Ambos se comunican por HTTP conforme al [contrato OpenAPI](docs/api/openapi.json).

| Aplicación | Carpeta | Tecnología | Despliegue |
| --- | --- | --- | --- |
| Frontend (SPA) | [Repositorio independiente](https://github.com/Yansete/plataforma-5e-frontend) | React 18, TypeScript, Vite | Vercel: https://plataforma-5e-taller-integrador.vercel.app |
| Backend (API REST) | [`backend/`](backend/README.md) | Python 3.12, FastAPI, SQLAlchemy, PostgreSQL + pgvector | Render ([`render.yaml`](render.yaml)), base de datos en Neon |

## Estructura

~~~text
.
├── backend/      API FastAPI con arquitectura hexagonal (Render)
├── docs/         Arquitectura, contrato de la API, decisiones, despliegue, pruebas, spikes y entregables
├── .github/      Backend CI y recorrido End-to-end con el repositorio del frontend
└── render.yaml   Configuración del servicio del backend en Render
~~~

## API publicada

- [Swagger del backend publicado](https://plataforma5e-api.onrender.com/docs)
- [OpenAPI del backend publicado](https://plataforma5e-api.onrender.com/openapi.json)
- [Contrato OpenAPI versionado](docs/api/openapi.json)

Cada operación publicada incluye su descripción y un ejemplo de llamada en Swagger y en el contrato versionado. Los ejemplos son de Bash con cURL y usan datos ilustrativos: reemplaza los identificadores por los devueltos para tu propia cuenta. Para rutas privadas, registra una cuenta o inicia sesión y conserva el `token` de la respuesta. En Swagger, pulsa **Authorize** y pega solo ese token.

Para ejecutar los ejemplos con cURL en Bash, define estas variables con tus datos reales:

```bash
export BASE_URL="https://plataforma5e-api.onrender.com"
export TOKEN="token-de-tu-sesion"
export COURSE_ID="id-de-tu-curso"
export UNIT_ID="id-de-tu-unidad"
export DOCUMENT_ID="id-de-tu-documento"
export GENERATION_ID="id-de-tu-generacion"
export RESOURCE_ID="id-de-tu-recurso"
export DOWNLOAD_ID="id-de-tu-descarga"
```

Los identificadores dentro de los cuerpos JSON (por ejemplo `unidad-1`) también deben sustituirse. El recorrido habitual es crear el curso, subir y procesar material, generar recursos, revisarlos y exportar los aprobados. Los ejemplos de borrado eliminan los datos indicados; ejecútalos solo con datos de prueba. Las descargas guardan el archivo y sus cabeceras por separado; una respuesta 204 no tiene cuerpo. La búsqueda por tema y la generación multimedia dependen de la configuración del servidor.

## Documentación

- [Arquitectura](docs/architecture/overview.md)
- [Contrato de la API (OpenAPI)](docs/api/openapi.json) y [contratos 5E](docs/api/contracts/)
- [Decisiones técnicas](docs/decisions/technical-decisions.md)
- [Despliegue](docs/deployment.md) · [Pruebas](docs/testing.md) · [Guía de Git](docs/git-guide.md)
- [Spikes](docs/spikes/) · [Sistema de diseño](docs/design/ui-design-system.docx) · [Entregables del curso](docs/project-management/)

## Forma de trabajo

Una rama y un pull request por tarea; solo el líder de la semana fusiona a `main`. Detalles en [CONTRIBUTING.md](CONTRIBUTING.md).

## Equipo

| Integrante | GitHub | Responsabilidad principal |
| --- | --- | --- |
| Juan Alegria | `iamjuanyouarenot` | Product Owner, pruebas y medición |
| Silvana Diaz | `SilvanaD12` | Scrum Master, configuración del docente y diseño de la interfaz |
| Yan Liu Dai | `Yansete` | Ingesta y RAG, despliegue del frontend |
| Sergio Celi | `sceliv` | Arquitectura del backend e integración |
