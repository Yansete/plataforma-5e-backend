# Arquitectura y estado de la Plataforma Docente

Actualizado el 16/10/2026: backend hexagonal en `src/platform5e/`, API en inglés documentada en OpenAPI y exportación
SCORM. Antes, 10/10/2026: rediseño de la interfaz con cuentas reales y todo guardado en la base de datos. Este documento reúne el estado del proyecto, la integración
con el backend y las convenciones para retomar el trabajo.

## Estado actual

Existe un frontend React 18, TypeScript y Vite 5 y un backend FastAPI con SQLAlchemy. El frontend siempre trabaja con
el backend: no hay modo local ni datos de demostración. El backend extrae el texto del material, lo parte en
fragmentos, recupera los relacionados con cada pedido (BM25) y un generador redacta los recursos citándolos (RAG).
Solo genera texto (alcance del Sprint 1). El generador es un modelo de lenguaje si hay clave de IA o un generador por reglas si no la hay (o si la IA falla).
La revisión docente y el historial de descargas se guardan en el servidor. Los archivos para Moodle y Chamilo se
arman con plantillas fijas. La importación en instancias reales de Moodle y Chamilo permanece pendiente (TA-006).

El modelo instruccional 5E sigue siendo la base: cada tipo de recurso pertenece a una etapa, que se envía al
backend y orienta la redacción. En la interfaz no se nombran las etapas; se muestran como momentos de la clase.

| Momento en la interfaz | Etapa 5E | Tipos de recurso |
|---|---|---|
| Para iniciar la clase | Enganchar (*engage*) | Pregunta detonante, sondeo de ideas previas |
| Para explorar | Explorar (*explore*) | Guía de exploración, caso con preguntas |
| Para explicar | Explicar (*explain*) | Explicación del tema, glosario |
| Para aplicar | Elaborar (*elaborate*) | Ejercicio de aplicación |
| Para evaluar | Evaluar (*evaluate*) | Preguntas de opción múltiple |

| Área | Funcionamiento actual | Límite |
|---|---|---|
| Cuentas y sesión | «Crear cuenta» con contraseña cifrada (PBKDF2) y sesión con token revocable de ocho horas | Sin recuperación de contraseña ni roles |
| Cursos y unidades | Creación, edición y borrado (con su material, recursos y descargas), con sumilla, logro y resultados de aprendizaje | Las unidades guardadas no se quitan de un curso; se borra el curso completo |
| Material | Archivo en la BD, extracción de PDF, PPTX y TXT, fragmentos de unas 220 palabras con su página, búsqueda por tema en Wikipedia en español. El docente no ve conteos de fragmentos: el documento queda «Listo para generar» | Los PDF escaneados (solo imágenes) no tienen texto; no hay OCR. Sin embeddings todavía (EN-013) |
| Pedido | «Elegir opciones» (agrupadas por momento de la clase) o «Escribir pedido»: reglas que interpretan tipo, cantidad, dificultad, alternativas y resultado, y muestran lo entendido; el texto completo va como indicación | La interpretación del pedido escrito es por reglas, no por IA |
| Generación | Recuperación BM25 y redacción con IA (Gemini, Anthropic u OpenAI) o por reglas; solo se aceptan recursos con citas válidas. Cada recurso guarda una copia de su evidencia y los parámetros del pedido | Un solo agente por pedido; el orquestador entre etapas es HU-003. El umbral de evidencia aún no filtra |
| Revisión | En el servidor: aceptar, editar o descartar distractores (con motivo), aprobar con las mismas reglas que el backend, regenerar (la versión anterior pasa a «Descartados») y borrar | No hay «Aceptar todos» (decisión del equipo: se revisa uno por uno) |
| Descargas | Moodle XML (preguntas aprobadas) y paquete SCORM 1.2 para Chamilo (todos los recursos aprobados), armados en el backend; y el documento de la unidad (HTML) con su evidencia. Nombres con el curso y la unidad. Historial en el servidor, con «Borrar historial» | SCORM probado en SCORM Cloud; importación en las instancias del curso pendiente (TA-006) |

## Backend hexagonal

El backend vive en `backend/src/platform5e/` y sigue la arquitectura hexagonal (puertos y adaptadores) en tres capas.
La regla de dependencia apunta hacia adentro y la vigila `tests/architecture/test_layer_dependencies.py`; los nombres
en inglés los vigila `tests/architecture/test_english_names.py`.

```
backend/src/platform5e/
├── domain/                     Reglas puras, sin FastAPI ni SQLAlchemy
│   ├── accounts/               Errores de la cuenta y la configuración del docente
│   ├── generation/             Errores de la generación
│   ├── materials/              Fragmentación (chunking.py) y búsqueda BM25 (text_analysis.py)
│   └── shared/                 Errores comunes (no encontrado, duplicado, persistencia no disponible)
├── application/                Casos de uso; solo conoce el dominio y sus puertos
│   ├── ports/outbound/         Puertos (typing.Protocol): repositorios, modelo de lenguaje, fuente abierta, exportador
│   ├── services/               accounts, materials, generation (redacción, generador por reglas) y review
│   └── use_cases/export/       ExportUnitResourcesUseCase: lo aprobado de una unidad → archivo del formato pedido
├── infrastructure/             Adaptadores
│   ├── http/                   Rutas FastAPI (routers/), esquemas Pydantic (schemas/), errores y autenticación
│   ├── persistence/            Repositorios SQLAlchemy (PostgreSQL en Neon o SQLite)
│   ├── llm/                    Gemini, Anthropic u OpenAI por HTTP y la fábrica que elige el generador
│   ├── exporters/              SCORM 1.2 (Chamilo) y Moodle XML: dos adaptadores del mismo puerto UnitExporterPort
│   ├── extraction/             Texto de PDF (pypdf), PPTX (python-pptx) y TXT
│   ├── sources/                Wikipedia en español (CC BY-SA 4.0)
│   └── settings.py             Variables de entorno
└── main.py                     Punto de composición: crea los adaptadores, los inyecta y registra las rutas
```

El dominio y la aplicación no leen variables de entorno ni importan frameworks: `main.py` lee la configuración, crea
los adaptadores y se los pasa a los servicios por constructor. Por eso las pruebas unitarias usan puertos falsos en
memoria y no necesitan base de datos ni red.

Las cuentas se crean con `POST /api/v1/accounts` y se guardan con su sal y la huella PBKDF2 de la contraseña.
Opcionalmente, `main.py` pasa una cuenta inicial (`BOOTSTRAP_TEACHER_EMAIL` y `BOOTSTRAP_TEACHER_PASSWORD`).
`DEMO_CATALOG=true` (solo pruebas) activa la cuenta y el curso de ejemplo y las propuestas preparadas para unidades
sin material.

Un recurso solo queda «aprobado» si no hay distractores pendientes, hay al menos dos aceptados y una clave: la misma
regla que muestra la pantalla. La exportación usa solo lo aprobado y registra la descarga en el historial.

**Pendiente declarado (Sprint 2).** Los nombres de tablas y columnas de la base (`ep002_cursos`, `docente`…) y los
valores guardados (`pendiente`, `aprobado`, `item_opcion_multiple`, `intermedia`…) siguen en español: cambiarlos exige
migrar los datos de Neon. En el código, los atributos del ORM ya están en inglés y apuntan a esas columnas. Los cursos,
documentos y generaciones guardados antes del contrato en inglés se adaptan al leerlos. Ver
[technical-decisions.md](../decisions/technical-decisions.md).

## API y contratos

Swagger está en `/docs` y ReDoc en `/redoc` (en local, `http://localhost:8000/docs`); el contrato versionado está en
[openapi.json](../api/openapi.json) y lo regenera `python scripts/export_openapi.py` desde `backend/`. Cada operación
tiene resumen, descripción, modelo de respuesta y sus errores; `tests/integration/test_openapi_documentation.py`
falla si falta algo, si una ruta o una clave del JSON no está en inglés, o si el archivo versionado no está al día.

Autenticación: `POST /accounts` o `POST /sessions` devuelven un token; en Swagger se pega en *Authorize*
(esquema `TeacherSession`). Todos los errores tienen la forma `{"error": {"code": "UNIT_NOT_FOUND", "message": "…"}}`:
el código es estable y en inglés; el mensaje lo lee el docente y va en español.

| Ruta (prefijo `/api/v1`) | Operaciones |
|---|---|
| `/accounts` | POST crear la cuenta (abre la sesión) |
| `/sessions` y `/sessions/current` | POST iniciar sesión; GET docente en sesión; DELETE cerrar sesión |
| `/courses` y `/courses/{course_id}` | GET lista; POST crear; PUT editar; DELETE borrar con su material, recursos y descargas |
| `/documents` y `/documents/{document_id}` | GET lista; POST subir (multipart: `file` y `context`); DELETE borrar |
| `/documents/{document_id}/file` | GET archivo original |
| `/documents/{document_id}/process` | POST extraer el texto y crear los fragmentos |
| `/documents/{document_id}/chunks` | GET fragmentos del documento |
| `/documents/from-topic` | POST buscar el tema en Wikipedia y guardarlo como material procesado |
| `/generations` y `/generations/{generation_id}` | POST generar con el material de la unidad; GET historial; GET una generación |
| `/generator` | GET generador activo (modelo de lenguaje o reglas) |
| `/review-summary` | GET recursos aprobados y por revisar de cada unidad |
| `/units/{unit_id}/resources` y `/units/{unit_id}/resources/{resource_id}` | GET recursos con su revisión; PUT guardar la revisión; DELETE borrar |
| `/units/{unit_id}/downloads` | GET historial; POST registrar una descarga; DELETE borrar el historial |
| `/units/{unit_id}/exports` | POST archivo para Chamilo (`scorm_zip`) o Moodle (`moodle_xml`) armado en el backend |
| `/health` (sin prefijo) | GET comprobación de salud para Render |

Los contratos 5E (estructura de cada tipo de recurso) están en `backend/src/platform5e/infrastructure/http/schemas/`
(`engage.py` … `evaluate.py`). `python scripts/export_contracts.py` regenera sus JSON Schema en `docs/api/contracts/`
y `tests/unit/test_five_e_contracts.py` comprueba que un ítem sin evidencia se rechace.

## Frontend y puntos de integración

Rutas: `/login`, `/register`, `/courses` (Mis cursos), `/courses/new`, `/courses/:id`, `/courses/:id/edit` y
`/courses/:id/units/:unitId/:tab` (`materials`, `generation`, `review`, `export`). Sin sesión, las rutas
internas llevan a «Inicio de sesión» y luego regresan a donde estaba el docente.

El código está en `frontend/src/`, organizado por funcionalidad. Cada carpeta de `features/` tiene `api/` (llamadas
al backend), `model/` (reglas sin React), `components/` y `pages/`.

| Parte | Qué hace |
|---|---|
| `shared/api/httpClient.ts` | Cliente HTTP: agrega la sesión, lee los errores `{error: {code, message}}`, distingue «sin conexión» de «tiempo agotado» y cierra la sesión vencida |
| `features/auth`, `features/courses` | Cuentas y sesión; cursos con borrado y resumen de recursos por unidad |
| `features/materials` | Subir, procesar y borrar documentos; buscar un tema en fuentes abiertas |
| `features/generation` | Formulario y pedido escrito (interpretado por reglas); llamada a `POST /generations` |
| `features/review` | Reglas para aprobar (iguales a las del backend), cambios del docente, regeneración y evidencia |
| `features/export` | Pide al backend el archivo para Moodle o Chamilo (`POST /units/{id}/exports`), arma el documento de la unidad (HTML) y muestra el historial |
| `features/units` | La página de la unidad con sus cuatro pestañas; los recursos se cargan una vez y las pestañas los comparten |
| `app/` | Rutas, sesión requerida y datos compartidos (`DataProvider`) |

La sesión se guarda en `localStorage` (`platform5e.session` (migra la clave anterior `plataforma-docente.sesion`)); los datos del docente viven en el servidor.
Una edición no aprueba un recurso: solo la acción «Aprobar recurso» lo vuelve descargable.

## Diseño y convenciones

El diseño de referencia está en `docs/design/ui-design-system.docx`. Se conservan tokens de
`frontend/src/styles/tokens.css`, componentes compartidos en `components/ui.tsx` e iconos de trazo.
Fraunces se usa para títulos y Public Sans para texto. Hay etiquetas visibles, foco visible y controles de 44 px.
La barra lateral pasa a menú bajo 960 px. Los textos y comentarios se escriben en español.

Antes de modificar requisitos, consultar el backlog, planificación, Charter, Inception y Product Discovery de
`docs/project-management/`. Se continúa sobre el código existente. Las decisiones y su estado se registran en
[technical-decisions.md](../decisions/technical-decisions.md); los cambios visuales requieren revisar el sistema de diseño.
No se atribuyen aprobaciones académicas ni pruebas con docentes sin evidencia.

## Persistencia y entorno

El backend usa SQLite por defecto y admite PostgreSQL con
`DATABASE_URL=postgresql+psycopg://...`. La URL `postgres://...` de `backend/.env.example` corresponde al entorno
de dbmate y no se utiliza directamente para SQLAlchemy. La configuración se establece en la terminal del backend.
Las dependencias del backend se definen en `backend/pyproject.toml`.

El entorno de EN-011 en `backend/database/` usa PostgreSQL 17 y pgvector 0.8.1, migraciones dbmate, fragmentos de 768
dimensiones e índices HNSW y GIN. Es distinto del almacenamiento que usa hoy el backend. Ver
[la guía de base de datos](../../backend/database/README.md). Las migraciones y `backend/database/schema.sql` no se modifican en esta limpieza.
No se editarán migraciones ya aplicadas; los futuros cambios de esquema requieren una nueva migración.

## Ejecución y verificación

Desde `backend/`, con Python 3.11 o superior:

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn platform5e.main:app --reload --port 8000
```

Desde `frontend/`, en otra terminal:

```bash
npm ci
npm run dev
```

Comprobaciones antes de entregar:

```bash
# En frontend/
npm run typecheck
npm test
npm run build
npm run test:e2e          # levanta el backend (Python con el backend instalado) y Vite
# En backend/, con .venv activo
pytest
pytest tests/unit tests/architecture tests/integration --cov=platform5e.domain --cov=platform5e.application --cov-fail-under=80
```

Las pruebas e2e del backend usan HTTP y una BD temporal SQLite, o PostgreSQL si se define `E2E_DATABASE_URL`
para una base exclusiva de pruebas. No debe apuntar a datos de trabajo. Las pruebas de arquitectura analizan con AST
todos los archivos Python del backend.

Las capturas nuevas se generan en `frontend/test-results/`, excluido por Git, y se adjuntan a Notion.
Los informes de avance y las validaciones académicas también se conservan en Notion.

## Pendientes y límites

Embeddings y búsqueda por significado con pgvector (EN-013, HU-011), unificación con `backend/database/migrations` (EN-024),
orquestación de los agentes de las cinco etapas sin repetir contenido (HU-003), OCR de PDF escaneados, recuperación
de contraseña, importación en LMS reales y mediciones del piloto. Indicadores (antes una pantalla con valores de
ejemplo) se medirán con datos reales en el Sprint 2.
Faltan validación con docentes, lectores de pantalla y pruebas amplias de rendimiento.

## Investigaciones y antecedentes

- [SP-001](../spikes/SP-001-embedding-models.md): propuesta de embeddings; no añade procesamiento real.
- [SP-002](../spikes/SP-002-models-per-resource-type.md): propuesta de modelos por tipo de recurso; estimaciones,
  no mediciones de generación con docentes.
- [SP-003](../spikes/SP-003-export-formats.md): Moodle XML para Moodle y ZIP QTI 2.1 para Chamilo.
- HU-045 y HU-046: sesión, catálogo y chat locales publicados; sus registros de avance están en Notion.
- HU-053 y EP-002: solicitudes, sesión, cursos, archivos e historial conectados; mantienen ejemplos preparados.
- HU-054: recorrido enlazado, secuencia, versiones y exportación local en los dos formatos seleccionados.

Las verificaciones históricas de interfaz, contraste y base vectorial se conservan como antecedentes en Notion;
no se presentan como nuevas mediciones del Sprint ni como aprobación académica.


### Organización del frontend por funcionalidad

`frontend/src/app/` reúne los proveedores, las rutas y la protección de sesión.
`shared/` contiene el cliente HTTP, la sesión, los componentes, los hooks y los tipos compartidos.
`features/` agrupa `auth`, `courses`, `units`, `materials`, `generation`, `review` y `export`;
cada funcionalidad separa `api/`, `model/` y sus páginas o componentes según corresponda.
El alias `@/` apunta a `src/`. Los textos visibles permanecen en español.

Esta primera entrega de la tarea 7 cambia la estructura y las rutas del navegador. Conserva
los endpoints y valores JSON actuales para seguir funcionando con el backend de `main`.
Quedan pendientes de la integración con Sergio: los contratos REST en inglés, los motivos
de bloqueo de aprobación enviados por la API y la descarga de archivos generados por el
backend. Mientras tanto, `review/model/reviewRules.ts` conserva las validaciones actuales y
`export/model/fileBuilders.ts` y `unitDocument.ts` conservan los generadores existentes.
Estos pendientes impiden considerar terminada toda la reestructuración del plan.
