# Decisiones técnicas

Estados posibles de cada decisión:

- **Tomada (implementada)**: aplicada en el código por necesidad técnica; puede revisarse.
- **Propuesta**: aplicada provisionalmente o sugerida; **requiere aprobación del equipo** (y, si afecta al sistema de
  diseño, registro en ese documento según su sección 7).
- Ninguna decisión de este archivo ha sido aprobada por el docente asesor ni validada con docentes.

## 1. Tecnología

| # | Decisión | Motivo | Estado |
|---|---|---|---|
| T1 | React 18 + TypeScript (modo estricto) + Vite 5 | Pedido explícito; tipado para modelos compartidos con el backend | Tomada |
| T2 | React Router 6 (`BrowserRouter`) | Enrutamiento estándar y simple. Si se publica en un hosting estático sin redirección a `index.html`, cambiar a `HashRouter` | Tomada |
| T3 | Sin librerías de estado, UI ni gráficos | «Sin dependencias innecesarias»; el estado cabe en un almacén propio de ~70 líneas y las barras son CSS | Tomada |
| T4 | Vitest solo como dependencia de desarrollo | Verificar reglas críticas (aprobación explícita, exportación de aprobados, persistencia) | Tomada |
| T5 | CSS global con variables en `tokens.css` + clases en `base.css` | El sistema de diseño exige «un único archivo de estilos compartido» y componentes implementados una sola vez | Tomada |
| T6 | Fuentes desde Google Fonts con respaldo Georgia / Segoe UI | Indicado en el sistema de diseño (sección 7) | Tomada |

### 1.1 Base de datos (EN-011, 05/10/2026)

| # | Decisión | Motivo | Estado |
|---|---|---|---|
| B1 | PostgreSQL 17 + pgvector 0.8.1 (imagen `pgvector/pgvector:0.8.1-pg17`) | Previsto en el Project Charter; una sola base para datos relacionales y vectores. 0.8 aporta *iterative scan* para top-k con filtros | Propuesta |
| B2 | Migraciones con dbmate (contenedor Docker), SQL puro con `migrate:up` / `migrate:down` | El backend usa Python/FastAPI; dbmate mantiene las migraciones en SQL independientes del ORM | Propuesta (confirmada por el usuario) |
| B3 | `embedding vector(768)` nullable + `modelo_embedding` (ambos nulos o ambos presentes) | Dimensión de SP-001; la ingesta guarda el texto antes de vectorizar (EN-013); el modelo permite reindexar | Propuesta |
| B4 | Índice HNSW con `vector_cosine_ops`, `m = 16`, `ef_construction = 64` | Coseno para embeddings normalizados; HNSW no necesita datos previos como IVFFlat; valores por defecto de pgvector hasta medir con datos reales | Propuesta |
| B5 | `unidad_id` y `curso_id` repetidos en `fragmento`, con índice en `unidad_id` | Filtrar por unidad (HU-013) sin JOIN | Propuesta |
| B6 | `texto_tsv` generado con `to_tsvector('spanish', texto)` + índice GIN | Base para la búsqueda híbrida (HU-012). Sin `unaccent` por ahora (exige función IMMUTABLE propia) | Propuesta |
| B7 | Esquema base mínimo (`curso`, `unidad`, `documento`) en la migración 0001 | EN-002 no existe en el repositorio; se ajustará con migraciones nuevas | Provisional |
| B8 | La verificación se ejecuta en una base temporal (`backend/database/verification/verify.sh`) | Repetirla sobre la misma base infla el índice HNSW con entradas muertas | Tomada |

## 2. Arquitectura del frontend

| # | Decisión | Motivo | Estado |
|---|---|---|---|
| A1 | Capas: `pages` → `services` → `store` / `data` | Las pantallas no conocen el origen de los datos; al llegar el backend solo cambian los servicios | Tomada |
| A2 | Las pantallas leen con `useAppState` y escriben solo mediante servicios | Un único punto de sustitución y reglas de negocio centralizadas | Tomada |
| A3 | Servicios asíncronos con latencia simulada (`simulation.ts`) | Que la interfaz ya maneje estados de carga como con una API real | Tomada |
| A4 | Persistencia en `localStorage` de metadatos, decisiones y preferencias; nunca contenido de archivos | Requisito del usuario; el objeto `File` solo aporta nombre y tamaño | Tomada |
| A5 | Versión del estado (`STATE_VERSION`); si no coincide, se cargan los datos iniciales | Evitar errores al cambiar la forma de los datos | Tomada |
| A6 | Un procesamiento interrumpido por recarga pasa a «Error» | No puede continuar un temporizador tras recargar; se explica y se ofrece reintento | Tomada |

## 3. Reglas de negocio aplicadas (supuestos)

| # | Regla | Fuente o motivo | Estado |
|---|---|---|---|
| R1 | Solo `approveResource` cambia un recurso a «aprobado»; editar lo mantiene en revisión | HU-010: «Nada se publica sin aprobación explícita» | Tomada |
| R2 | Un ítem no se aprueba mientras haya distractores sin decidir | HU-010: tres acciones por distractor | Propuesta |
| R3 | Un ítem necesita al menos 2 distractores aceptados (≥ 3 alternativas) | Supuesto pedagógico; los documentos no lo fijan | Propuesta |
| R4 | Editar un distractor equivale a aceptarlo con cambios | Simplifica el flujo: la edición es una decisión explícita | Propuesta |
| R5 | Descartar exige motivo: sin sentido, también correcto, duplicado, fuera de la unidad, otro | Alimenta I3 (NDR) e I5 (fiabilidad) | Propuesta |
| R6 | Se puede devolver a revisión un recurso aprobado o descartado; deja de ser exportable | Control docente; queda registrado | Propuesta |
| R7 | La generación no duplica un ejemplo que ya está en la cola | Evitar ruido en la demo | Tomada (solo demo) |
| R8 | Moodle XML para Moodle y QTI 2.1 en ZIP para Chamilo; solo ítems de opción múltiple | Catálogo actual y SP-003; QTI 3.0 y SCORM descartados | Tomada en el prototipo; importación LMS pendiente |
| R9 | I2 = aprobados sin edición / propuestos (incluye pendientes en el denominador) | Definición literal de S2 | Tomada |
| R10 | El filtro de periodo del tablero usa la fecha de propuesta del recurso y solo afecta a indicadores locales | Los valores de ejemplo no tienen fechas | Propuesta |
| R11 | Tamaño máximo de archivo: 25 MB | Los documentos no lo definen | Propuesta |
| R12 | Tipos de documento: separata, diapositivas, guía de práctica, sílabo, transcripción | Derivado de HU-002 y del Anexo B (PDF, PPTX, transcripciones) | Propuesta |
| R13 | Destinos Moodle y Chamilo | SP-003 y catálogo de HU-054 | Tomada en el prototipo |

## 4. Sistema de diseño: aplicación y ajustes

Se implementaron todos los valores del documento: paleta, tipografías y escala, espaciado (4–40 px), radios (8/10/12/999),
bordes de 1 px, sin sombras salvo diálogos, barra lateral de 244 px con ítem activo `#22493E` e inactivo `#C9D6CF`,
botones de 44 px, campos con etiqueta visible, etiquetas de estado, barra de progreso de 8 px, tablas con cabecera en
versalitas e iconos de trazo 1,5 px sobre 20 px. Padding de contenido: 32 px (el documento indica 30–34 px).

### 4.1 Contraste verificado (fórmula WCAG 2.1, calculado el 26/09/2026)

| Combinación | Declarado en el documento | Calculado | Resultado |
|---|---|---|---|
| Texto `#1A211E` sobre fondo `#F6F4EF` | 15,2:1 | 14,92:1 | AAA |
| Texto `#1A211E` sobre blanco | — | 16,40:1 | AAA |
| Secundario `#4A544F` sobre fondo | 7,4:1 | 7,15:1 | AAA |
| Secundario `#4A544F` sobre blanco | — | 7,86:1 | AAA |
| Secundario `#4A544F` sobre `#EDE9E0` | — | 6,49:1 | AA |
| Acento `#1F5C4A` sobre blanco | 6,8:1 (AA) | 7,81:1 | AAA |
| Acento sobre fondo | — | 7,11:1 | AAA |
| Acento sobre `#DCEBE3` (etiqueta aprobado) | — | 6,34:1 | AA |
| Blanco sobre acento (botón primario) | — | 7,81:1 | AAA |
| Blanco sobre `#123B30` (hover) | 10,6:1 | 12,40:1 | AAA |
| Blanco sobre `#16352C` (barra lateral) | 13,1:1 | 13,29:1 | AAA |
| `#C9D6CF` sobre `#16352C` (ítem inactivo) | — | 8,86:1 | AAA |
| Blanco sobre `#22493E` (ítem activo) | — | 10,04:1 | AAA |
| Terracota `#A84A26` sobre blanco | 5,3:1 (AA) | 5,72:1 | AA |
| Terracota sobre fondo | — | 5,20:1 | AA |
| Terracota sobre `#F6E8D8` (etiqueta en revisión) | — | 4,75:1 | AA (margen estrecho) |
| **Borde `#DCD7CC` sobre blanco** | — | **1,43:1** | **No cumple 3:1 (WCAG 1.4.11) para contorno de campos** |
| Borde `#DCD7CC` sobre fondo | — | 1,31:1 | No cumple 3:1 |

Conclusiones:

- Todo el texto cumple AA. Las cifras declaradas no coinciden exactamente con las calculadas (no se sabe sobre qué
  fondo se midieron); conviene corregirlas en el documento.
- **Incompatibilidad detectada:** el documento pide borde `#DCD7CC` en los campos de texto, pero ese borde no alcanza el
  contraste 3:1 que WCAG 2.1 (1.4.11) exige para identificar el contorno de un control. Esto contradice el criterio
  «Accesibilidad verificable» del propio documento.

### 4.2 Propuestas de ajuste (no aprobadas)

| # | Propuesta | Detalle | Estado |
|---|---|---|---|
| D1 | Token `--color-line-strong: #8A8578` para bordes de campos, casillas, selector y zona de carga | 3,68:1 sobre blanco, 3,35:1 sobre fondo, 3,04:1 sobre `#EDE9E0`. Tarjetas y separadores siguen con `#DCD7CC` (decorativos) | Propuesta, aplicada |
| D2 | Color «marrón» de la etiqueta «En revisión» = `#A84A26` (terracota) | El documento dice «marrón» sin definir un token | Propuesta, aplicada |
| D3 | Etiqueta «Descartado»: terracota sobre blanco con borde `#DCD7CC` e icono ✕ | El documento no define esta variante; se distingue de «En revisión» por texto e icono | Propuesta, aplicada |
| D4 | Foco: contorno 2 px `#1F5C4A` con separación 2 px; blanco dentro de la barra lateral | El acento sobre `#16352C` da 1,7:1 y no se vería | Propuesta, aplicada |
| D5 | Botones deshabilitados: fondo `#EDE9E0`, texto `#4A544F` (6,49:1) | No definido en el documento | Propuesta, aplicada |
| D6 | Marca de meta en barras de indicadores: línea de 2 px en `#1A211E` | No definido | Propuesta, aplicada |
| D7 | `.h2` (Fraunces 19 px) para el enunciado de ítems; títulos de tarjeta en Public Sans 16 px | Sigue la escala del documento | Tomada |
| D8 | Registrar D1–D6 en el documento del sistema de diseño e incrementar su versión | Sección 7 del documento (gobernanza) | Pendiente del equipo |

### 4.3 Adaptación a pantallas pequeñas (propuesta; el documento solo define 1280 px)

- **≤ 1100 px**: rejillas de 3–4 columnas pasan a 2; paneles laterales (evidencia, ayudas) bajan debajo del contenido.
- **≤ 960 px**: la barra lateral se oculta y se abre con el botón «Menú» de una barra superior `#16352C`; se cierra con
  Esc, con el botón ✕ o tocando el fondo.
- **≤ 640 px**: una columna; padding de 16 px; tablas se muestran como tarjetas apiladas con la etiqueta de cada dato;
  botones de cabecera a ancho completo; título de pantalla a 24 px.
- Estado: **Propuesta**, aplicada y verificada sin desbordamiento a 820 y 375 px.

## 5. Contradicciones y vacíos detectados en los documentos

| # | Tema | Detalle | Impacto en el frontend |
|---|---|---|---|
| C1 | Prototipo existente | `Sistema_de_Diseno_UI` (sección 8) y la Presentación afirman que el prototipo de la semana 4 «ya implementa» el sistema en seis pantallas y registra decisiones. Según el usuario, solo existe una maqueta hecha a mano y no hay código. El backlog marca HU-001 como «Pendiente» | Se construyó desde cero; no se afirma validación previa |
| C2 | Calendario | El Project Charter ubica Sprint 0 en semanas 5–6, Sprint 1 en 7–10 y el piloto en la 14. La Presentación y el Sprint Planning ubican Sprint 1 en 4–7, Sprint 2 en 8–11 y el piloto en la 11. La Presentación llama a la semana 6 «iteración 2» y la hoja Dedicación, «iteración 1» | Ninguno directo; el periodo del tablero no usa sprints |
| C3 | Épicas | La Presentación lista 13 épicas (E1–E13) y «40 historias»; el backlog v3.0 tiene 10 épicas (EP-001 a EP-010) y 41 ítems no épicos. Hay diferencias de MoSCoW (p. ej. Explore «Should» en la Presentación; EP-005 «Could Have») | Se citan los identificadores del backlog v3.0 |
| C4 | Etapas por sprint | El Charter asigna Evaluate y Explore al Sprint 1; el backlog pone Explore (HU-013) en el Sprint 2 | Ninguno |
| C5 | Fuentes del estado del arte | S1 y el Charter piden ≥ 20 fuentes; S2 contiene 16 y declara una línea de búsqueda pendiente. Plazo de OE1: semana 5 (S1) o semana 6 (Charter) | Ninguno |
| C6 | Color «marrón» | La etiqueta «En revisión» usa un «marrón» que no existe como token | Ver D2 |
| C7 | Contraste | Cifras declaradas distintas a las calculadas y borde de campos insuficiente | Ver 4.1 y D1 |
| C8 | Contratos | Existen contratos 5E en adapters/inbound/contratos y OpenAPI; futuras ampliaciones deben acordarse | Ver `docs/architecture/overview.md` |
| C9 | LMS objetivo | Moodle y Chamilo según SP-003 | Importación real pendiente en TA-006 |
| C10 | Límites de carga | No hay tamaño máximo ni lista cerrada de tipos de documento | Ver R11 y R12 |
| C11 | Roles | TA-001 exige roles docente/estudiante/administrador; el alcance actual no incluye autenticación | Usuario único de demostración |
| C12 | Capacidad | Sprint 1 planifica 65 SP con capacidad de 64 SP | Ninguno |
| C13 | I16 e I17 en el tablero | HU-021 exige mostrarlos, pero no pueden calcularse sin exportador, validador ni LMS | Se muestran como «Pendiente» sin valor inventado |

## HU-045 sesión y catálogo de demostración 09/10/2026

Implementado: sessionStorage conserva solo el identificador público de la sesión, nunca contraseñas. No autentica contra backend. courseService valida y guarda curso/unidad en el store; la versión 2 migra el estado 1 conservando decisiones. La edición mantiene identificadores, números y resultados de aprendizaje de unidades existentes; no permite eliminarlas para proteger referencias. El catálogo expone todas las unidades; el contexto global por curso queda pendiente.

El token de foco cambia a `2px solid var(--color-brand-dark)` (#16352C) por la instrucción expresa de HU-023; actualiza D4 para superficies claras. El foco de la barra lateral conserva blanco por contraste. Esta implementación no implica aprobación del asesor.

## ADR-005 Plantillas fijas para exportación

Moodle usa Moodle XML y Chamilo usa QTI 2.1 en ZIP con `imsmanifest.xml`, según
[SP-003](../spikes/SP-003-export-formats.md). QTI 3.0 y SCORM quedan descartados.
El código arma el XML y el paquete mediante plantillas fijas a partir de recursos aprobados.
El frontend mantiene sus exportadores; el backend de demo delega Moodle XML en un adaptador
de salida mediante `ExportadorPort`. El título se escapa y los campos HTML se conservan.
La validación estructural no acredita importación real en un LMS; TA-006 permanece pendiente.

## Limpieza hexagonal del Sprint 1

Las rutas HTTP y sus contratos se agrupan en adapters/inbound; los casos de uso de revisión,
aprobación y exportación viven en application/use_cases. Bootstrap solo conecta piezas.
Los errores SQLAlchemy se traducen en persistencia. El correo y la clave demo se inyectan desde
bootstrap. Dominio y aplicación no dependen de FastAPI ni SQLAlchemy; los adaptadores de entrada
no dependen de SQLAlchemy. Las pruebas AST verifican estas reglas para todos sus módulos.

## ADR-006 Monorepo de dos aplicaciones independientes (15/10/2026)

La raíz es un monorepo de dos aplicaciones independientes: el frontend se despliega en Vercel y el backend en Render.
Solo comparten el contrato OpenAPI (`docs/api/openapi.json`); ninguna importa código de la otra. Cada una tiene su
propio CI (Frontend CI y Backend CI) y un tercer flujo (End-to-end) prueba las dos juntas.

## ADR-007 SCORM 1.2 para Chamilo (15/10/2026)

Chamilo recibe un paquete SCORM 1.2 generado en el backend, con una página HTML por recurso aprobado. Reemplaza al
ZIP QTI 2.1 de ADR-005 y SP-003: Chamilo lo importaba como lección, pero sin ninguna página que mostrar.

## ADR-008 Sprint 1 solo genera texto (15/10/2026) · reemplazada por ADR-011

En el Sprint 1 los recursos se generan solo como texto. El material de entrada también es solo texto: el extractor lee
el texto de PDF, PPTX y TXT e ignora las imágenes. Imágenes, video y otras modalidades se evalúan en el Sprint 2. La
interfaz ya no ofrece modalidades, la API responde 422 a cualquier modalidad distinta de «Textual» y el prompt pide no
incluir material multimedia.

## ADR-009 Hexagonal en tres capas y contrato en inglés (16/10/2026)

El backend vive en `backend/src/platform5e/` con tres capas: `domain`, `application` (puertos en `ports/outbound`,
servicios y casos de uso) e `infrastructure` (adaptadores HTTP, persistencia, LLM, exportadores, extracción y fuentes).
`main.py` es el único punto de composición. Reemplaza a «Limpieza hexagonal del Sprint 1» (`adapters/inbound`,
`bootstrap`). La API HU-043 (`/recursos/generar`, `/exportaciones`) se eliminó: la interfaz nunca la usó y duplicaba
la revisión real.

Todo el código, las rutas, las claves del JSON, los códigos de error y las variables de entorno están en inglés; los
textos que lee el docente siguen en español. Se vigila con `tests/architecture/test_english_names.py` y
`tests/integration/test_openapi_documentation.py`.

Queda en español, como deuda declarada para el Sprint 2 porque exige migrar los datos de Neon:

- Los nombres de tablas y columnas (`ep002_cursos`, `docente`…). Los atributos del ORM ya están en inglés.
- Los valores guardados: estados (`pendiente`, `aprobado`, `descartado`), tipos de recurso (`item_opcion_multiple`…),
  dificultades (`basica`, `intermedia`, `avanzada`) y el formato `documento` del historial de descargas, que también
  se acepta en `POST /units/{unit_id}/exports`.
- Los nombres anteriores de las variables de entorno (`CORS_ORIGENES`, `IA_API_KEY`…) se siguen leyendo si falta el
  nombre nuevo, para que Render no se caiga mientras se renombran en el panel.
- Los cursos, documentos y generaciones guardados antes del contrato se adaptan al leerlos (claves `sumilla`, `logro`,
  `fuente`, `licencia`, `tema`, `descripcion`, `usaIA`).

## ADR-010 Las exportaciones para LMS se arman en el backend (16/10/2026)

Moodle XML y SCORM 1.2 se arman en el backend con plantillas fijas, como dos adaptadores del mismo puerto
`UnitExporterPort`, y se piden con `POST /api/v1/units/{unit_id}/exports`. El caso de uso `ExportUnitResourcesUseCase`
filtra lo aprobado, deja que cada formato elija lo que admite (Moodle solo ítems de opción múltiple) y registra la
descarga. El navegador solo arma el documento de la unidad (HTML). Actualiza ADR-005: el ZIP QTI 2.1 ya no se usa
(ver ADR-007). El Moodle XML se valida contra la muestra que Moodle importó en SP-003.

## ADR-011 Recursos multimodales e interactivos, editor enriquecido y SCORM multirrecurso (17/10/2026)

El docente pidió más variedad por etapa, recursos visuales, sonoros e interactivos, selección múltiple, edición con
formato y un paquete SCORM con todos los recursos y sus medios (documento «Plan de cambios y ajustes solicitados por el
docente», 17/10/2026, en `docs/project-management/actas/`). Reemplaza a ADR-008.

- **Catálogo.** 18 tipos de recurso: cada etapa 5E combina texto con al menos otro formato (gráfico, imagen, audio o
  actividad interactiva). El dominio (`domain/generation/resource_formats.py`) fija la etapa y el formato de cada tipo
  y valida su estructura (nodos, pasos, pares, afirmaciones, oraciones, guion, descripción de la imagen).
- **Gráficos.** El mapa conceptual, la infografía y el diagrama de proceso los dibuja la plataforma en SVG a partir de
  la estructura que redacta la IA (o el generador por reglas): el texto viene del material y la forma es una
  plantilla fija, así que siempre se pueden mostrar, editar y exportar.
- **Imagen y audio.** Puerto `MediaGeneratorPort` con el adaptador `GeminiMediaGenerator` (Interactions API:
  `gemini-3.1-flash-lite-image` y `gemini-3.8-flash-tts`, configurables con `IMAGE_MODEL` y `SPEECH_MODEL`). La capa
  gratuita de Gemini no incluye imágenes: sin facturación, la imagen queda como tarjeta con su descripción y el audio
  se escucha con la voz del navegador (`speechSynthesis`), en la plataforma y dentro del SCORM. Los archivos se
  guardan en la tabla nueva `media_assets` (puerto `MediaRepositoryPort`) y el audio se convierte a MP3 con `lameenc`.
- **Medios después de editar** (revisión del PR #35). Si el docente cambia el guion o la descripción de un recurso con
  audio o imagen generados, ese archivo deja de usarse: la revisión y el SCORM pasan al respaldo con el texto nuevo, y
  «Generar el audio (o la imagen) de nuevo» (`POST /units/{id}/resources/{id}/media`) crea uno con el texto actual.
  Un archivo marcado como desactualizado bloquea la aprobación y nunca se exporta.
- **Prueba con la clave real.** `backend/scripts/check_media_generation.py` genera un audio y una imagen con la clave
  configurada y explica cada error (pedido inválido, sin facturación, modelo inexistente o sin cuota).
- **Actividades interactivas.** Relacionar conceptos, ordenar pasos, verdadero o falso y completar espacios. En el
  SCORM se califican en la página (`shared/activity.js`) y envían el puntaje y `passed`/`failed` (60 %) al LMS.
- **Selección múltiple.** Casillas por etapa; el frontend pide los tipos marcados uno tras otro (la API sigue
  recibiendo un tipo por pedido) y, si uno falla, los demás se generan igual.
- **Revisión unificada.** Los recursos se agrupan por etapa en el orden de la clase; los elementos de cada recurso se
  editan en la revisión y el texto se edita con un editor enriquecido (Tiptap) que guarda `bodyHtml`.
- **Seguridad del HTML.** El HTML del editor se limpia al recibirlo (`nh3`, solo formato de texto y enlaces web) y otra
  vez al exportarlo; el navegador lo limpia también antes de mostrarlo (DOMPurify).
- **SCORM multirrecurso.** Un SCO por recurso en orden 5E con sus archivos en `media/`; el manifiesto declara todos los
  archivos del paquete (lo comprueba una prueba). Es SCORM 1.2, el formato que importan Canvas y Chamilo.
- **Moodle XML** sigue exportando solo preguntas de opción múltiple: es el único tipo verificado en una importación
  real (SP-003). Las actividades nuevas van en el SCORM y en el documento de la unidad (con su clave de respuestas).
- Los tipos nuevos se guardan, como los anteriores, con valores en español (`mapa_conceptual`, `verdadero_falso`…);
  entran en la deuda declarada de ADR-009.

## ADR-012 Evaluación gamificada por niveles (26/10/2026)

HU-051 pide que los ítems de evaluación se presenten con puntaje, niveles o tiempo (C01) y que la actividad se exporte
como cuestionario de Moodle (C02). Las actividades interactivas del ADR-011 ya enviaban un puntaje al LMS, pero no
había niveles, tiempo ni recompensa, así que no bastaban para cerrar la historia.

- **Niveles y puntos.** El nivel sale de la dificultad con que el docente pidió el ítem (`params.difficulty`):
  básica = Nivel 1 (10 puntos), intermedia = Nivel 2 (20), avanzada = Nivel 3 (30). Un ítem sin dificultad guardada
  (recursos anteriores) cuenta como intermedio. Las reglas viven en `domain/generation/gamification.py`.
- **SCORM.** Los ítems de opción múltiple aprobados ya no van en páginas sueltas: forman un solo SCO «Evaluación por
  niveles», en el lugar del primero de ellos. El nivel siguiente se desbloquea al responder el anterior, cada respuesta
  correcta suma los puntos de su nivel, un cronómetro mide el tiempo y al final se muestra la insignia (oro ≥ 90 %,
  plata ≥ 75 %, bronce ≥ 60 %). El LMS recibe el porcentaje de puntos, `passed`/`failed` (60 %) y
  `cmi.core.session_time`. Las actividades interactivas de Evaluar siguen como SCO propios.
- **Moodle XML.** Cada nivel es una subcategoría del banco («RED-301 · Unidad 1/Nivel 1 · Básico») y cada ítem vale los
  puntos de su nivel en `<defaultgrade>`. Con eso el docente arma el cuestionario por niveles (o con preguntas
  aleatorias de cada nivel) y Moodle muestra el puntaje de cada pregunta. El tiempo límite es una opción del
  cuestionario en Moodle, no de la pregunta, así que no viaja en el XML.
- **Pendiente de verificar.** Subcategorías y `<defaultgrade>` son parte del formato Moodle XML y el archivo pasa el
  validador construido con la muestra de SP-003, pero la importación con categorías por nivel todavía no se probó en
  una instancia real de Moodle (TA-006).

## ADR-013 Orquestador de la secuencia con un agente por etapa (26/10/2026)

El docente pidió un sistema multiagente para que los recursos de una clase no repitan contenido entre etapas (HU-003).
Hasta ahora el frontend pedía cada tipo marcado por separado y ningún recurso sabía qué habían redactado los demás.

- **Contrato.** `POST /api/v1/generations` acepta `resourceTypes` (de 1 a 8 tipos) además del pedido de un solo tipo,
  que sigue igual. Con `resourceTypes`, `stage` y `resourceType` se ignoran; sin ninguno de los dos, la API responde 422.
- **Agentes.** Cada etapa 5E tiene su agente (`domain/generation/sequence.py`): Enganchar, Explorar, Explicar, Elaborar
  y Evaluar. Los tipos se ordenan según la clase y cada uno lo redacta el agente de su etapa. En esta versión los agentes
  comparten los puertos de recuperación y de modelo de lenguaje; los agentes especializados (HU-047 a HU-050) cambiarán
  cómo redacta cada uno sin tocar el orquestador.
- **Contexto compartido.** Todos los agentes usan la misma evidencia recuperada y reciben, en el prompt, el título y un
  resumen de lo que redactaron los anteriores, con la instrucción de no repetirlo.
- **Rechazo de repetidos.** Un recurso cuya proporción de palabras compartidas (Jaccard sobre los términos de BM25) con
  otro de la secuencia llega a 0,6 se pide de nuevo una vez; si sigue repetido, se rechaza y el motivo queda en
  `sequence[].rejected`. Es una regla por palabras: la búsqueda por significado (EN-013) podrá reforzarla.
- **Trazabilidad.** Cada recurso guarda su `agent`, y la respuesta trae `sequence` con lo que generó o rechazó cada
  agente. Los recursos comparten el id del pedido y conservan sus propios parámetros, así que «Regenerar» funciona igual.
- El frontend todavía pide los tipos uno por uno; pasar a un solo pedido con `resourceTypes` queda como tarea aparte.

## ADR-014 Verificación de anclaje de las afirmaciones (30/10/2026)

HU-016 pide que cada afirmación se contraste con la evidencia recuperada (C01) y que lo que no tiene respaldo se rechace
con su motivo (C02), para medir el indicador I21 (tasa de alucinación, meta ≤ 3 %). Hasta ahora solo se comprobaba que
la etiqueta citada (F1, F2…) existiera; un recurso podía citar F2 para algo que F2 no dice.

- **Respaldo de una afirmación.** Proporción de sus palabras útiles (sin palabras vacías, reducidas a su raíz con
  `extract_terms`, la misma función de BM25) que aparecen en los fragmentos que cita. Dos palabras coinciden si tienen
  la misma raíz o comparten sus cinco primeras letras («confirma» y «confirmación»). Vive en
  `domain/generation/grounding.py` y no depende del modelo de lenguaje.
- **Umbral.** Es el `evidenceThreshold` del pedido (0,6 por defecto; el frontend envía 0,6), que la API ya recibía pero
  no usaba. Una afirmación con menos de dos palabras útiles no se puede contrastar y se rechaza.
- **Cita equivocada.** Si los fragmentos citados no respaldan la afirmación pero otro fragmento recuperado sí, la cita
  se corrige a ese fragmento y se cuenta en `correctedClaims`. No se descarta contenido verdadero por una etiqueta mal
  puesta.
- **Rechazo.** Las afirmaciones sin respaldo se quitan de las citas y quedan en `grounding.removedClaims` del recurso,
  con su motivo. Si menos de la mitad de las afirmaciones de un recurso tiene respaldo, el recurso entero se rechaza:
  no se guarda para revisión y aparece en `grounding.rejectedResources` de la respuesta (y, en una secuencia, en
  `sequence[].rejected` del agente). Si se rechaza todo, la API responde 422 `INSUFFICIENT_EVIDENCE` con el motivo.
- **I21.** La respuesta trae `grounding.hallucinationRate` = afirmaciones sin respaldo / afirmaciones verificadas,
  contando las de los recursos conservados y las de los rechazados. Es la verificación automática que pide la ficha del
  indicador; la auditoría manual por muestra sigue siendo del cierre de sprint.
- **Límites.** Es una regla por palabras: no reconoce sinónimos ni paráfrasis lejanas, y una afirmación que reordena
  palabras del fragmento para decir lo contrario puede pasar. La búsqueda por significado (EN-013, HU-011) podrá
  reforzarla. Con el generador por reglas el respaldo es siempre completo, porque cita frases del material; con Gemini
  hay que revisar en la plataforma publicada cuántos recursos se rechazan y ajustar el umbral si hace falta.
