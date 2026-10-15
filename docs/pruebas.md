# Pruebas del proyecto

**Responsable:** Juan Alegria (TA-001, TA-007, TA-008) · **Última actualización:** 10/10/2026 (noche)

Este documento responde a la pregunta del asesor: *«Si van a hacer casos de prueba, por ejemplo una prueba
unitaria, ¿cuál es el directorio?»*. Cada tipo de prueba tiene su carpeta y las pruebas corren solas en GitHub
Actions en cada `push` (archivo `.github/workflows/ci.yml`, pestaña **Actions** del repositorio).

## Dónde va cada prueba

```
backend/tests/
├── unit/                    Pruebas unitarias, sin base de datos ni red
│   ├── test_servicios_aplicacion.py             Capa de servicios con puertos falsos en memoria
│   ├── test_contratos_5e.py                     Contratos de generación (pydantic)
│   ├── test_revision_exportacion.py             Reglas de revisión y exportación
│   ├── test_recurso_unit.py                     Entidad del dominio
│   ├── test_configuracion_limites.py            Límites de la configuración
│   ├── test_cursos_con_sumilla_y_resultados.py  Sumilla, logro y resultados de aprendizaje del curso
│   ├── test_material_y_recuperacion.py          Ingesta: limpiar y fragmentar el texto; búsqueda de evidencia (BM25)
│   ├── test_material_service.py                 Procesar documentos y crear material desde un tema
│   ├── test_generacion_con_material.py          Generación con el material del docente: citas, respaldo, validación
│   ├── test_cuentas_y_revision.py               Crear cuenta, borrar curso, revisión guardada, resumen e historial
│   └── test_adaptadores_material_ia.py          Lectura de PDF, PPTX y TXT; Wikipedia e IA con HTTP simulado;
│                                                generador por reglas
├── arquitectura/            Vigila la regla de dependencia entre las capas hexagonales (análisis del código)
├── integration/             Adaptadores de persistencia contra una base real y traducción de sus errores
├── e2e/                     Punta a punta: servidor uvicorn real, por HTTP, con SQLite o PostgreSQL
│   ├── conftest.py                    Levanta y apaga el servidor en un puerto libre (TA-007)
│   ├── test_demo_punta_a_punta.py     Historia de la demo (HU-043) y fidelidad del XML exportado (TA-007)
│   ├── validador_moodle_xml.py        Reglas de la muestra que Moodle importó en SP-003 (TA-007)
│   ├── test_validador_moodle_xml.py   Controles del validador (TA-007)
│   ├── test_configuracion_ep002.py    Configuración del docente (EP-002)
│   ├── test_generacion_hu053.py       Generación desde la configuración (HU-053)
│   ├── test_material_real.py          Material real: subir, procesar, ver fragmentos y generar con citas
│   ├── test_cuentas_y_revision.py     Cuenta nueva → curso → material → generación → revisión → descargas → borrado
│   └── test_errores_recursos.py       Errores de la API de recursos
└── data/                    Archivos de referencia (muestra_moodle_verificada.xml)

frontend/
├── src/features/**/{api,model}/*.test.ts y src/shared/**/*.test.ts   Pruebas unitarias (vitest), junto al código que prueban
├── src/test/fixtures.ts     Datos de prueba y respuestas simuladas del servidor
└── e2e/platform.spec.ts   Punta a punta en el navegador (Playwright + Chromium) con el backend real:
                             inicio de sesión, recorrido completo del docente, menú en el celular y regreso a ruta protegida
```

| Tipo | Qué comprueba | Dónde | Comando |
|---|---|---|---|
| Unitaria | Una pieza aislada: entidad, contrato, servicio, adaptador | `backend/tests/unit`, `frontend/src/**/*.test.ts` | `pytest tests/unit` · `npm test` |
| Arquitectura | Que las capas respeten la regla de dependencia | `backend/tests/arquitectura` | `pytest tests/arquitectura` |
| Integración | Los adaptadores de persistencia con una base real | `backend/tests/integration` | `pytest tests/integration` |
| Punta a punta (backend) | Historias completas contra el servidor real y fidelidad del XML exportado (I19) | `backend/tests/e2e` | `pytest tests/e2e` |
| Punta a punta (sistema completo) | El recorrido del docente en el navegador contra el backend real, de crear la cuenta a la descarga | `frontend/e2e` | `npm run test:e2e` |
| Cobertura (caja blanca) | Qué parte del código ejecutan las pruebas; falla si baja del umbral | La CI y `frontend/coverage/` | `npm run test:coverage` · `pytest --cov` |
| Prueba manual con IA real | Que el proveedor configurado responda en el sistema publicado | Sistema desplegado | Ver «Prueba manual después del despliegue» |
| Caja negra, carga, concurrencia y disponibilidad | Sistema desplegado y bajo carga | Sprint 2 (TA-005) | — |

### Pruebas sin red ni clave de IA

Las pruebas automáticas no llaman a servicios externos. Las de punta a punta levantan el backend con
`IA_PROVEEDOR=reglas` (generador por reglas, sin IA) y `BUSQUEDA_POR_TEMA=false`, y las llamadas a Gemini,
Anthropic, OpenAI y Wikipedia se prueban con respuestas HTTP simuladas (`httpx.MockTransport`) en
`test_adaptadores_material_ia.py`. Así las pruebas no gastan cuota, no dependen de internet y nunca necesitan la
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

Frontend (desde `frontend/`):

```bash
npm install
npm test                          # unitarias
npx playwright install chromium   # solo la primera vez
npm run test:e2e                  # navegador contra el backend real (levanta uvicorn en el 8765 y Vite en el 5174)
```

`test:e2e` usa el Python que tenga instalado el backend (`pip install -e ../backend`) y una base SQLite nueva en la
carpeta temporal, así que no toca tus datos. Si ese Python no es el `python` por defecto, indícalo con la variable
`PYTHON`; en PowerShell, con el entorno del backend: `$env:PYTHON="..\backend\.venv\Scripts\python.exe"; npm run test:e2e`.

Revisar un XML antes de importarlo en Moodle (desde `backend/`):

```bash
python -m tests.e2e.validador_moodle_xml salida_demo/archivo.xml
```

## Cobertura (caja blanca, TA-008)

La cobertura mide qué líneas, funciones y ramas del código ejecutan las pruebas. Es la prueba de caja blanca:
mira el código por dentro y señala lo que ninguna prueba recorre.

| Parte | Qué se mide | Umbral mínimo | Última medición documentada |
|---|---|---|---|
| Backend | `plataforma5e/domain` y `plataforma5e/application` (reglas y servicios) | 80 % | 98,9 % (10/10/2026) |
| Frontend | `src/features/**/api`, `src/features/**/model`, `src/shared/api`, `src/shared/lib` | 80 % en líneas, sentencias y funciones; 70 % en ramas | 98,56 % en líneas, 100 % en funciones, 94,71 % en ramas (15/10/2026; tarea 7, entrega de estructura y rutas) |

Si un cambio hace bajar la cobertura del umbral, la CI marca el commit en rojo. Dónde ver el detalle:

- En GitHub, en cada ejecución de **Actions** aparece la tabla de cobertura en el resumen (*Summary*), y los
  reportes se descargan como `cobertura-frontend` y `reportes-pytest`.
- En local:

```bash
# Frontend (desde frontend/)
npm run test:coverage            # luego abre coverage/index.html

# Backend (desde backend/)
python -m pytest tests/unit tests/arquitectura tests/integration --cov=plataforma5e.domain --cov=plataforma5e.application --cov-report=term-missing
```

## Qué hace la integración continua

| Trabajo | Pasos |
|---|---|
| Frontend | `npm ci` → tipos → unitarias con cobertura → build → instala el backend → Playwright contra el backend real |
| Backend | unitarias y arquitectura → integración → cobertura → punta a punta con SQLite → punta a punta con PostgreSQL 16 |

PostgreSQL se descarga del espejo público de Amazon ECR para evitar el límite de descargas de Docker Hub.
Si el commit rompe algo, GitHub lo marca con ✗ y guarda los reportes (`reportes-pytest`, `cobertura-frontend`,
`informe-playwright`). Si alguna vez falta `backend/pyproject.toml`, el trabajo del backend se omite con un aviso.

Las pruebas en navegador ya corren en la CI contra el backend real (antes usaban datos de demostración).

## Prueba manual después del despliegue

Se hace en el enlace de Vercel, con el backend de Render configurado (ver [despliegue.md](despliegue.md)), y se
anota el resultado en el acta de la semana:

1. Abrir `https://<servicio>.onrender.com/api/v1/ia`: debe indicar el proveedor y el modelo configurados
   (por ejemplo, `Gemini · gemini-3.8-flash`). Si dice «Generador por reglas», falta la clave o el proveedor.
2. En la plataforma: crear una cuenta y un curso con un resultado de aprendizaje, subir un PDF con texto (o
   buscar el tema) y comprobar que aparecen fragmentos.
3. Generar preguntas de opción múltiple: el aviso debe decir «Listo: … para revisar» sin mencionar el generador de
   respaldo, y en Revisión el recurso debe llevar la etiqueta «Redactado con IA». Si aparece «Generador de respaldo»,
   el motivo está en los *Logs* de Render («Generación con respaldo: …»).
4. En Revisión, comprobar con «Ver origen» que cada alternativa lleva a un fragmento del material; aprobar, recargar
   la página (lo aprobado sigue ahí) y descargar el Moodle XML y el documento de la unidad (.html).
5. Validar el XML descargado con `python -m tests.e2e.validador_moodle_xml <archivo.xml>` antes de importarlo en Moodle.

## Última verificación: 10/10/2026 (noche), copia limpia de `main` con el rediseño (antes del merge)

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
