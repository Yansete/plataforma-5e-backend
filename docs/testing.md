# Pruebas del proyecto

**Responsable:** Juan Alegria (TA-001, TA-007, TA-008) · **Última actualización:** 16/10/2026

Este documento responde a la pregunta del asesor: *«Si van a hacer casos de prueba, por ejemplo una prueba
unitaria, ¿cuál es el directorio?»*. Cada tipo de prueba tiene su carpeta y las pruebas corren solas en GitHub
Actions en cada `push` (archivo `.github/workflows/backend-ci.yml`, pestaña **Actions** del repositorio).


## Repositorios separados (EN-033)

El backend está en este repositorio. Las rutas plataforma-5e-frontend/
corresponden al clon independiente:
https://github.com/Yansete/plataforma-5e-frontend

Los comandos de Python se ejecutan desde backend/ y los de npm desde
la raíz del repositorio del frontend. Las verificaciones anteriores se conservan como historial.

## Dónde va cada prueba

```
backend/tests/
├── unit/                    Pruebas unitarias, sin base de datos ni red
│   ├── test_application_services.py             Servicios de aplicación con puertos falsos en memoria
│   ├── test_accounts_and_review.py              Cuentas, borrado de cursos, revisión guardada, resumen e historial
│   ├── test_configuration_limits.py             Límites y variables de entorno (nombres nuevos y anteriores)
│   ├── test_courses_with_syllabus_and_outcomes.py  Sumilla, logro y resultados de aprendizaje del curso
│   ├── test_five_e_contracts.py                 Contratos 5E: se aceptan con evidencia y se rechazan sin ella
│   ├── test_material_retrieval.py               Limpiar y fragmentar el texto; búsqueda de evidencia (BM25)
│   ├── test_material_service.py                 Procesar documentos y crear material desde un tema
│   ├── test_generation_with_material.py         Generación con el material: citas, respaldo, validación, solo texto
│   ├── test_material_adapters_llm.py            PDF, PPTX y TXT; Wikipedia e IA con HTTP simulado; generador por reglas
│   ├── test_export_unit_resources.py            Caso de uso de exportación con puertos falsos
│   ├── test_scorm_package_exporter.py           Paquete SCORM 1.2 para Chamilo
│   ├── test_moodle_xml_exporter.py              Moodle XML contra la muestra que Moodle importó en SP-003
│   └── test_legacy_stored_data.py               Datos guardados antes del contrato en inglés
├── architecture/            Regla de dependencia entre capas y nombres en inglés (análisis del código con AST)
├── integration/             Persistencia contra una base real y documentación de la API (OpenAPI)
├── e2e/                     Punta a punta: servidor uvicorn real, por HTTP, con SQLite o PostgreSQL
│   ├── conftest.py                       Levanta y apaga el servidor en un puerto libre (TA-007)
│   ├── test_accounts_and_review_api.py   Cuenta nueva → curso → material → generación → revisión → descargas → borrado
│   ├── test_courses_and_documents_api.py Cursos, archivos, historial, sesión y reinicio del servidor (EP-002)
│   ├── test_material_ingestion_api.py    Material real: subir, procesar, buscar por tema y generar con citas
│   └── test_exports_api.py               Exportación SCORM y Moodle XML por HTTP (TA-007)
├── support/moodle_xml_validator.py       Reglas de la muestra que Moodle importó en SP-003
└── fixtures/verified_moodle_sample.xml   Esa muestra

plataforma-5e-frontend/
├── src/features/**/{api,model}/*.test.ts y src/shared/**/*.test.ts   Pruebas unitarias (vitest), junto al código que prueban
├── src/test/fixtures.ts     Datos de prueba y respuestas simuladas del servidor
└── e2e/platform.spec.ts   Punta a punta en el navegador (Playwright + Chromium) con el backend real:
                             inicio de sesión, recorrido completo del docente, menú en el celular y regreso a ruta protegida
```

| Tipo | Qué comprueba | Dónde | Comando |
|---|---|---|---|
| Unitaria | Una pieza aislada: entidad, contrato, servicio, adaptador | `backend/tests/unit`, `plataforma-5e-frontend/src/**/*.test.ts` | `pytest tests/unit` · `npm test` |
| Arquitectura | Que las capas respeten la regla de dependencia y que los nombres estén en inglés | `backend/tests/architecture` | `pytest tests/architecture` |
| Integración | Los adaptadores de persistencia con una base real | `backend/tests/integration` | `pytest tests/integration` |
| Punta a punta (backend) | Historias completas contra el servidor real y fidelidad del XML exportado (I19) | `backend/tests/e2e` | `pytest tests/e2e` |
| Punta a punta (sistema completo) | El recorrido del docente en el navegador contra el backend real, de crear la cuenta a la descarga | `plataforma-5e-frontend/e2e` | `npm run test:e2e` |
| Cobertura (caja blanca) | Qué parte del código ejecutan las pruebas; falla si baja del umbral | La CI y `plataforma-5e-frontend/coverage/` | `npm run test:coverage` · `pytest --cov` |
| Prueba manual con IA real | Que el proveedor configurado responda en el sistema publicado | Sistema desplegado | Ver «Prueba manual después del despliegue» |
| Caja negra, carga, concurrencia y disponibilidad | Sistema desplegado y bajo carga | Sprint 2 (TA-005) | — |

### Pruebas sin red ni clave de IA

Las pruebas automáticas no llaman a servicios externos. Las de punta a punta levantan el backend con
`LLM_PROVIDER=rules` (generador por reglas, sin IA) y `TOPIC_SEARCH_ENABLED=false`, y las llamadas a Gemini,
Anthropic, OpenAI y Wikipedia se prueban con respuestas HTTP simuladas (`httpx.MockTransport`) en
`test_material_adapters_llm.py`. Así las pruebas no gastan cuota, no dependen de internet y nunca necesitan la
clave. Que el proveedor real responda se comprueba a mano en el sistema publicado (ver más abajo).

## Cómo correrlas en local

Backend (desde `backend/`, con el entorno virtual activado):

```bash
pip install -e ".[dev]"
python -m pytest                      # todas
python -m pytest tests/e2e -v         # solo punta a punta (levanta su propio servidor)
```

Para la punta a punta contra PostgreSQL, con una base **vacía** creada para esto:

```bash
E2E_DATABASE_URL=postgresql+psycopg://plataforma:plataforma@localhost:5432/plataforma5e python -m pytest tests/e2e
```

En PowerShell: `$env:E2E_DATABASE_URL="postgresql+psycopg://..."; python -m pytest tests/e2e`.

Frontend: ejecutar desde la raíz de su repositorio independiente:

    npm ci
    npm test
    npx playwright install chromium

Para Playwright, configurar BACKEND_DIR con la ruta absoluta de la carpeta backend
y PYTHON con la ruta absoluta de su entorno virtual. Después ejecutar:

    npm run test:e2e

Consultar los ejemplos de configuración en:
https://github.com/Yansete/plataforma-5e-frontend#readme

Revisar un XML antes de importarlo en Moodle (desde `backend/`):

```bash
python -m tests.support.moodle_xml_validator red-301-unidad-1-moodle.xml
```

## Cobertura (caja blanca, TA-008)

La cobertura mide qué líneas, funciones y ramas del código ejecutan las pruebas. Es la prueba de caja blanca:
mira el código por dentro y señala lo que ninguna prueba recorre.

| Parte | Qué se mide | Umbral mínimo | Última medición documentada |
|---|---|---|---|
| Backend | `platform5e/domain` y `platform5e/application` (reglas, servicios y casos de uso) | 80 % | 98 % (16/10/2026) |
| Frontend | `src/features/**/api`, `src/features/**/model`, `src/shared/api`, `src/shared/lib` | 80 % en líneas, sentencias y funciones; 70 % en ramas | 98,56 % en líneas, 100 % en funciones, 94,71 % en ramas (15/10/2026; tarea 7, entrega de estructura y rutas) |

Si un cambio hace bajar la cobertura del umbral, la CI marca el commit en rojo. Dónde ver el detalle:

- En GitHub, en cada ejecución de **Actions** aparece la tabla de cobertura en el resumen (*Summary*), y los
  reportes se descargan como `frontend-coverage` y `backend-reports`.
- En local:

```bash
# Frontend (desde plataforma-5e-frontend/)
npm run test:coverage            # luego abre coverage/index.html

# Backend (desde backend/)
python -m pytest tests/unit tests/architecture tests/integration --cov=platform5e.domain --cov=platform5e.application --cov-report=term-missing
```

## Qué hace la integración continua

- backend-ci.yml ejecuta las comprobaciones del backend.
- e2e.yml descarga el frontend de su repositorio y ejecuta Playwright contra el backend del commit evaluado.
- El workflow registra el commit del frontend y adjunta los resultados como playwright-results.
- El frontend mantiene sus pruebas, cobertura y build en su propio repositorio.

## Prueba manual después del despliegue

Se hace en el enlace de Vercel, con el backend de Render configurado (ver [despliegue.md](deployment.md)), y se
anota el resultado en el acta de la semana:

1. Abrir `https://<servicio>.onrender.com/api/v1/generator`: debe indicar el proveedor y el modelo configurados
   (por ejemplo, `Gemini · gemini-3.8-flash`). Si dice «Generador por reglas», falta la clave o el proveedor.
2. En la plataforma: crear una cuenta y un curso con un resultado de aprendizaje, subir un PDF con texto (o
   buscar el tema) y comprobar que el documento queda «Listo para generar».
3. Generar preguntas de opción múltiple: el aviso debe decir «Listo: … para revisar» sin mencionar el generador de
   respaldo, y en Revisión el recurso debe llevar la etiqueta «Redactado con IA». Si aparece «Generador de respaldo»,
   el motivo está en los *Logs* de Render («Generación con respaldo: …»).
4. En Revisión, comprobar con «Ver origen» que cada alternativa lleva a un fragmento del material; aprobar, recargar
   la página (lo aprobado sigue ahí) y descargar el Moodle XML y el documento de la unidad (.html).
5. Validar el XML descargado con `python -m tests.support.moodle_xml_validator <archivo.xml>` antes de importarlo en Moodle.

## Verificación de los cambios pedidos por el docente el 17/10/2026

Sobre `main` en `4910bed` con los parches 9 y 10, Python 3.13 (y compilación con 3.11 y una instalación limpia con
`pip install .` en 3.12, como Render), Node 24 y Chromium:

- Backend: 334 pruebas superadas. Nuevas: `tests/unit/test_multimodal_resources.py` (catálogo por etapa, los 18 tipos
  con el generador por reglas, estructura, SVG bien formado y con texto escapado, imágenes y voz de Gemini con un
  servidor simulado, respaldo si el servicio falla, SCORM con todos los archivos declarados en el manifiesto y
  documento con clave de respuestas) y `tests/e2e/test_multimodal_api.py` (gráfico por HTTP, audio sin archivo,
  HTML limpiado, elementos validados, aprobación y exportación).
- Frontend: comprobación de tipos y compilación correctas; 78 pruebas unitarias, 98,15 % de líneas cubiertas.
- Punta a punta en Chromium: las 4 pruebas anteriores y `e2e/multimodal.spec.ts` (selección múltiple, revisión en el
  orden de la clase, editor con negrita, edición de una afirmación, aprobación y SCORM con los tres recursos).
- Sin clave de IA: se usan el generador por reglas, la tarjeta descriptiva de la imagen y la voz del navegador. Esta
  verificación no acredita la generación real de imágenes y audio con Gemini ni la importación en Canvas.

Corrección de la revisión del PR #35 (18/10/2026): `tests/unit/test_edited_media.py` cubre el guion editado (el
SCORM lleva el texto nuevo y la voz del navegador, no el audio anterior), el mismo guion (se conserva el audio), el
archivo desactualizado (bloquea la aprobación y no se exporta) y «Generar de nuevo» (usa el guion editado; 409 si el
servicio no está activo o el recurso no está por revisar). `e2e/multimodal.spec.ts` edita el guion en la pantalla.
Backend: 347 pruebas; frontend: 79 y las 5 pruebas en Chromium. Además se abrió en Chromium cada página de un paquete
SCORM con los 18 tipos, con una API de SCORM 1.2 simulada: imágenes y audio cargan, las páginas de contenido quedan
`completed`, la pregunta se califica y las cuatro actividades envían `score.raw` 100 y `passed` al responder bien.

## Distractores fiables, HU-019 (30/10/2026)

`tests/unit/test_distractor_reliability.py` cubre el distractor que el material presenta como respuesta (con la
oración y el fragmento), el que aparece en otro sentido, la oración negada, el que dice lo mismo que la clave, la
consigna que no cuenta, el prompt que pide el error conceptual, los distractores sin justificación o sin error
conceptual que no se usan, el generador por reglas, el descarte con motivo `tambien_correcto` en el servicio, el
informe `distractorReliability` (I5) y el ítem rechazado por quedarse con menos de dos distractores fiables.
`tests/e2e/test_material_ingestion_api.py` comprueba por HTTP la justificación y el error conceptual de cada distractor.

## Agente de Explicar, HU-049 (30/10/2026)

`tests/unit/test_explain_agent.py` cubre cómo se separa la explicación en párrafos y el glosario en entradas, el
fragmento con el que se enlaza cada párrafo (uno o dos), el párrafo sin respaldo marcado con su motivo, los subtítulos
que no se contrastan, el umbral de párrafo (10 puntos menos que el de las citas), el contenido que queda sin los
párrafos quitados, el rechazo con motivo cuando menos de la mitad tiene respaldo, el glosario entrada por entrada, el
prompt, y el informe del servicio (`unsupportedParagraphs`, aviso al docente y error `INSUFFICIENT_EVIDENCE`).

## Verificación de anclaje, HU-016 (30/10/2026)

`tests/unit/test_grounding.py` cubre el respaldo de una afirmación (palabras del fragmento, raíz y prefijo), la cita
corregida al fragmento que sí la respalda, el rechazo con motivo de una afirmación inventada o demasiado breve, el
umbral tomado de `evidenceThreshold`, el rechazo del recurso con menos de la mitad de afirmaciones respaldadas, el
cálculo de I21, el informe `grounding` de la respuesta (pedido simple y secuencia) y el error
`INSUFFICIENT_EVIDENCE` con su motivo. `tests/e2e/test_material_ingestion_api.py` comprueba por HTTP que cada recurso
trae su verificación y que, con el generador por reglas, I21 es 0.

## Evaluación gamificada por niveles, HU-051 (26/10/2026)

`tests/unit/test_gamification.py` cubre el nivel y los puntos de cada dificultad, las insignias y el orden por nivel.
`test_scorm_package_exporter.py` comprueba que los ítems de opción múltiple forman un solo SCO «Evaluación por
niveles» con tres niveles (10, 20 y 30 puntos), el nivel 1 abierto y los demás bloqueados, y que `scorm.js` envía
`cmi.core.session_time`. `test_moodle_xml_exporter.py` comprueba una subcategoría por nivel con `<defaultgrade>` de
10, 20 y 30, y que el archivo sigue pasando el validador de la muestra de SP-003. Además se respondió la evaluación en
Chromium con una API de SCORM 1.2 simulada: el nivel 2 se desbloquea al terminar el 1, el puntaje y el cronómetro
avanzan, aparece la insignia y el LMS recibe `session_time`, `score.raw` y `passed`. Falta importar el Moodle XML con
categorías por nivel en una instancia real de Moodle (TA-006).

## Verificación de la integración final de la tarea 7 (16/10/2026)

Sobre `main` en `55531cc`, con los ajustes de aprobación y documento HTML aplicados,
Python 3.12 y Node 24:

- Backend: 285 pruebas superadas (126 unitarias, 107 de arquitectura, 36 de integración y
  16 de punta a punta por HTTP). Cobertura de dominio y aplicación: 98,35 % (269 pruebas
  unitarias, de arquitectura e integración; mínimo requerido: 80 %).
- Frontend: comprobación de tipos y compilación correctas; 68 pruebas unitarias y
  97,89 % de líneas cubiertas (96,03 % de ramas, 100 % de funciones).
- El HTML se verifica en el backend: orden de las etapas, alternativas, citas, caracteres
  especiales, enlaces HTTP(S), nombre del archivo, selección y registro único de descarga.
  Las reglas de aprobación se prueban allí; el cliente no las vuelve a calcular.
- Las cuatro pruebas en Chromium contra el backend real pasaron (1,1 minutos).
- Las pruebas HTTP comprueban `approvalBlockers` al generar, listar y guardar un recurso.
  La prueba del navegador añade la descarga del HTML desde `/exports` y su historial.
- Se utilizan SQLite temporal y el generador por reglas. Esta verificación no acredita
  importaciones reales en LMS, proveedores de IA, Wikipedia ni la instalación en producción.

## Verificación anterior: 16/10/2026, estructura hexagonal y API en inglés

Hecha sobre `main` con la reestructuración del backend (#24) y los cambios de la tarea del docente aplicados, con
Python 3.13 y Node 22:

- Backend: 281 pruebas superadas: 124 unitarias, 105 de arquitectura (dependencias entre capas y nombres en inglés,
  archivo por archivo), 36 de integración (persistencia y documentación OpenAPI de las 28 operaciones) y 16 de punta a
  punta por HTTP. Cobertura de dominio y aplicación: 98 %.
- Frontend: tipos y build sin errores; 69 pruebas unitarias (95 % de las líneas) y 4 pruebas en navegador contra el
  backend real (inicio de sesión, recorrido completo hasta la descarga de Moodle XML, menú en el celular y regreso a la
  ruta protegida).
- No cubierto: las respuestas reales de los proveedores de IA y de Wikipedia (se simulan); la punta a punta con
  PostgreSQL la corre la CI.

## Verificación anterior: 10/10/2026 (noche), copia limpia de `main` con el rediseño (antes del merge)

Hecha en un clon nuevo de `main` (4bad0e6) con los cambios aplicados, Python 3.12 y Node 22:

- Backend: 166 pruebas superadas (120 unitarias, 9 de arquitectura, 5 de integración y 32 de punta a punta). Las
  de punta a punta pasaron con SQLite y con PostgreSQL 16. Cobertura de dominio y servicios: 98,9 %.
- Frontend: tipos y build sin errores; 68 pruebas unitarias (99,7 % de las líneas, 100 % de las funciones y 94,6 %
  de las ramas cubiertas) y 3 pruebas en navegador contra el backend real: inicio de sesión, recorrido completo
  (crear cuenta → curso → material → generación con opciones y con pedido escrito → revisión guardada → descarga
  de Moodle XML e historial → cerrar sesión y volver a entrar → borrar curso) y menú en el celular.
- No cubierto por estas pruebas: las respuestas reales de los proveedores de IA y de Wikipedia (se simulan) y la
  ejecución de la CI en GitHub para esta rama, que se verá al subirla.

## Historial

- 10/10/2026 (tarde), flujo real antes del rediseño: 144 pruebas del backend y 70 unitarias del frontend; 8 en
  navegador con datos de demostración y 5 contra el backend real.
- 10/10/2026 sobre `main` (antes del flujo real): 75 pruebas del backend y 64 unitarias del frontend; 8 en
  navegador con datos de demostración y 4 contra el backend real.
- Control de calidad de TA-007 (09/10): se rompió a propósito el exportador de tres formas (clave sin puntaje,
  exportar distractores descartados, quitar la retroalimentación) y la prueba falló en los tres casos.
- TA-008 (09/10): se comprobó que la CI falla si se exige un umbral de cobertura mayor al alcanzado.
- La CI de TA-001 y TA-008 corrió en verde en GitHub (ejecuciones #3 y #6 de «Pruebas»).
