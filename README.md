# Platform 5E · Plataforma Docente

Generación asistida de recursos educativos a partir del material del docente: modelo instruccional 5E, recuperación de evidencia (RAG), revisión docente obligatoria y exportación a Moodle (XML) y Chamilo (SCORM 1.2). Proyecto del curso Taller Integrador 1 (UPAO, 2026-II).

**Monorepo con dos aplicaciones independientes.** `frontend/` y `backend/` se instalan, prueban y despliegan por separado, y solo se comunican por HTTP según el contrato [`docs/api/openapi.json`](docs/api/openapi.json). Ninguna importa código de la otra.

| Aplicación | Carpeta | Tecnología | Despliegue |
| --- | --- | --- | --- |
| Frontend (SPA) | [`frontend/`](frontend/README.md) | React 18, TypeScript, Vite | Vercel: https://plataforma-5e-taller-integrador.vercel.app |
| Backend (API REST) | [`backend/`](backend/README.md) | Python 3.12, FastAPI, SQLAlchemy, PostgreSQL + pgvector | Render ([`render.yaml`](render.yaml)), base de datos en Neon |

## Estructura

~~~text
.
├── frontend/     SPA React + TypeScript (Vercel)
├── backend/      API FastAPI con arquitectura hexagonal (Render)
├── docs/         Arquitectura, contrato de la API, decisiones, despliegue, pruebas, spikes y entregables
├── .github/      CI por proyecto (Frontend CI, Backend CI) y recorrido End-to-end
└── render.yaml   Configuración del servicio del backend en Render
~~~

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
