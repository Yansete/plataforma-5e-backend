# Arquitectura y estado de la Plataforma Docente

Actualizado el 10/10/2026 (noche), con el rediseño de la interfaz aprobado por el equipo: una sola forma de trabajo,
con cuentas reales y todo guardado en la base de datos. Este documento reúne el estado del proyecto, la integración
con el backend y las convenciones para retomar el trabajo.

## Estado actual

Existe un frontend React 18, TypeScript y Vite 5 y un backend FastAPI con SQLAlchemy. El frontend siempre trabaja con
el backend: no hay modo local ni datos de demostración. El backend extrae el texto del material, lo parte en
fragmentos, recupera los relacionados con cada pedido (BM25) y un generador redacta los recursos citándolos (RAG).
El generador es un modelo de lenguaje si hay clave de IA o un generador por reglas si no la hay (o si la IA falla).
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
| Material | Archivo en la BD, extracción de PDF, PPTX y TXT, fragmentos de unas 220 palabras con su página, «Ver fragmentos» y búsqueda por tema en Wikipedia en español | Los PDF escaneados (solo imágenes) no tienen texto; no hay OCR. Sin embeddings todavía (EN-013) |
| Pedido | «Elegir opciones» (agrupadas por momento de la clase) o «Escribir pedido»: reglas que interpretan tipo, cantidad, dificultad, alternativas y resultado, y muestran lo entendido; el texto completo va como indicación | La interpretación del pedido escrito es por reglas, no por IA |
| Generación | Recuperación BM25 y redacción con IA (Gemini, Anthropic u OpenAI) o por reglas; solo se aceptan recursos con citas válidas. Cada recurso guarda una copia de su evidencia y los parámetros del pedido | Un solo agente por pedido; el orquestador entre etapas es HU-003. El umbral de evidencia aún no filtra |
| Revisión | En el servidor: aceptar, editar o descartar distractores (con motivo), aprobar con las mismas reglas que el backend, regenerar (la versión anterior pasa a «Descartados») y borrar | No hay «Aceptar todos» (decisión del equipo: se revisa uno por uno) |
| Descargas | Moodle XML y ZIP QTI 2.1 de las preguntas aprobadas, y el documento de la unidad (HTML) con todos los recursos aprobados y su evidencia. Nombres con el curso y la unidad. Historial en el servidor, con «Borrar historial» | Importación en LMS reales pendiente (TA-006) |

## Backend hexagonal

La estructura de EN-004 es `backend/plataforma5e/`:

- `domain/`: entidades y errores propios. `material.py` fragmenta el texto y `recuperacion.py` busca con BM25.
  No importa aplicación, adaptadores, FastAPI ni SQLAlchemy.
- `application/ports/`: contratos de repositorios y `ExportadorPort`.
- `application/services/`: reglas de recursos, configuración, ingesta (`material_service.py`), generación y redacción
  (`redaccion.py`: instrucciones para la IA y validación de citas); no importa adaptadores ni frameworks.
- `application/ports/`: además, `ExtractorTextoPort`, `MaterialRepositoryPort`, `FuenteAbiertaPort` y `GeneradorRecursosPort`.
- `application/use_cases/`: `RevisarAlternativa`, `AprobarRecurso` y `ExportarAprobados`.
- `adapters/inbound/`: rutas HTTP, contratos Pydantic en `contratos/`, autorización y manejadores de errores.
  No importa SQLAlchemy. Las rutas de configuración consultan el servicio, sin acceder a su repositorio.
- `adapters/outbound/persistence/`: repositorios SQLAlchemy y traducción de errores de persistencia.
- `adapters/outbound/exportacion/`: plantilla fija de Moodle XML; escapa el título y conserva el HTML de los campos.
- `adapters/outbound/extraccion/`: texto de PDF (pypdf), PPTX (python-pptx) y TXT.
- `adapters/outbound/fuentes/`: búsqueda de artículos en Wikipedia en español.
- `adapters/outbound/ia/`: generador con modelo de lenguaje por HTTP, generador por reglas y selección por variables de entorno.
- `bootstrap/`: crea los adaptadores, inyecta servicios y casos de uso y registra routers y manejadores.

Las cuentas se crean con `POST /api/v1/cuentas` y se guardan en `ep002_usuarios` con su sal y la huella PBKDF2 de la
contraseña. Opcionalmente, bootstrap pasa una cuenta inicial (`EP002_DOCENTE_EMAIL` y `EP002_DOCENTE_PASSWORD`); si no
se definen, no existe. `CATALOGO_DEMO=true` (solo pruebas) activa la cuenta y el curso de ejemplo y las propuestas
preparadas para unidades sin material. El servicio no lee variables de entorno.

`RevisionService` guarda la revisión de cada recurso (`ep002_recursos`) y el historial de descargas
(`ep002_descargas`). Un recurso solo queda «aprobado» si no hay distractores pendientes, hay al menos dos aceptados y
una clave: la misma regla que muestra la pantalla.
El repositorio de configuración recibe el catálogo de generación por constructor; no crea otro repositorio.

Una decisión debe ser `aceptar`, `descartar` o `editar`. Los recursos inexistentes producen 404.
La aprobación permanece bloqueada con alternativas pendientes y la exportación rechaza una lista sin aprobados.
Los valores de evidencia del dominio empiezan vacíos: no se inventa el fragmento `chunk-001`.

## API y contratos

Swagger está en `http://localhost:8000/docs`; OpenAPI está en `/openapi.json` y en
[openapi.json](../api/openapi.json). El esquema HTTP Bearer `SesionDocente` permite autorizar con el token obtenido
al iniciar sesión o al crear la cuenta.

| URL con prefijo `/api/v1` | Operación |
|---|---|
| `/cuentas` | POST crear cuenta de docente (abre la sesión) |
| `/sesiones` y `/sesiones/actual` | POST login; GET perfil (correo y nombre); DELETE cierre |
| `/cursos` y `/cursos/{id}` | GET lista; POST creación; PUT edición; DELETE borrado con su material, recursos y descargas |
| `/unidades/{id}/recursos` y `/unidades/{id}/recursos/{rid}` | GET recursos de la unidad con su revisión; PUT guardar la revisión; DELETE borrar |
| `/unidades/{id}/descargas` | GET historial; POST registrar una descarga; DELETE borrar el historial |
| `/resumen` | GET recursos aprobados y por revisar de cada unidad |
| `/documentos` y `/documentos/{id}` | GET lista; POST multipart con archivo y contexto; DELETE eliminación |
| `/documentos/{id}/archivo` | GET archivo original |
| `/generaciones` y `/generaciones/{id}` | POST generar con el material de la unidad (los recursos quedan para revisión); GET recuperación |
| `/solicitudes` | GET historial autenticado |
| `/recursos/generar`, `/recursos/{id}`, `/recursos/{id}/alternativas/{letra}/decision`, `/recursos/{id}/aprobar`, `/exportaciones` | API de HU-043 (revisión y Moodle XML sobre recursos de ejemplo). La conservan sus pruebas; la interfaz usa `/unidades/{id}/recursos` |
| `/documentos/{id}/procesar` | POST extraer el texto y crear los fragmentos |
| `/documentos/{id}/fragmentos` | GET fragmentos del documento |
| `/documentos/desde-tema` | POST buscar el tema en Wikipedia y guardarlo como material procesado |
| `/ia` | GET generador activo (modelo de IA o reglas) |

Los contratos 5E están en `backend/plataforma5e/adapters/inbound/contratos/`.
Desde `backend/`, `python scripts/export_contracts.py` regenera sus JSON Schema en `docs/api/contracts/`.
`pytest tests/unit/test_contratos_5e.py` comprueba aceptación y rechazo de evidencia incompleta.

## Frontend y puntos de integración

Rutas: `/entrar`, `/crear-cuenta`, `/` (Mis cursos), `/cursos/nuevo`, `/cursos/:id`, `/cursos/:id/editar` y
`/cursos/:id/unidades/:unidad/:pestaña` (`material`, `generacion`, `revision`, `exportacion`). Sin sesión, las rutas
internas llevan a «Inicio de sesión» y luego regresan a donde estaba el docente.

| Parte | Qué hace |
|---|---|
| `services/api.ts` | Cliente HTTP: agrega la sesión, traduce errores a mensajes, distingue «sin conexión» de «tiempo agotado» y cierra la sesión vencida |
| `services/sesion.ts`, `cursos.ts`, `material.ts`, `generacion.ts` | Cuentas, cursos (con borrado y resumen), material (subir, procesar, buscar tema) y generación |
| `services/pedido.ts` | Interpreta el pedido escrito por reglas (tipo, cantidad, dificultad, alternativas y resultado) |
| `services/revision.ts` | Reglas para aprobar (iguales a las del backend), cambios del docente, guardado, regeneración y evidencia |
| `services/descargas.ts`, `documento.ts`, `exportFormats.ts` | Archivos de descarga (Moodle XML, QTI 2.1 en ZIP, documento HTML) e historial |
| `state/datos.tsx` | Sesión (`useSession`) y datos compartidos: cursos, documentos y resumen de recursos |
| `pages/unidad/*` | Las cuatro pestañas de la unidad; los recursos se cargan una vez y las pestañas los comparten |

La sesión se guarda en `localStorage` (`plataforma-docente.sesion`); los datos del docente viven en el servidor.
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
uvicorn plataforma5e.bootstrap.app:crear_aplicacion --factory --reload --port 8000
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
pytest tests/unit tests/arquitectura tests/integration --cov=plataforma5e.domain --cov=plataforma5e.application --cov-fail-under=80
```

Las pruebas e2e del backend usan HTTP y una BD temporal SQLite, o PostgreSQL si se define `E2E_DATABASE_URL`
para una base exclusiva de pruebas. No debe apuntar a datos de trabajo. La prueba de arquitectura analiza con AST
todos los archivos Python de dominio, aplicación y adaptadores de entrada.

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
