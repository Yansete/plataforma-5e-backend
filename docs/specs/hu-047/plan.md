# HU-047 · Plan técnico

Especificación: [spec.md](spec.md) · Decisión: ADR-020

## Backend (`plataforma-5e-backend`, rama `feat/hu-047-prediction-challenge`)

Rutas desde `backend/src/platform5e/`.

| Capa | Archivo | Cambio | Requisito |
|---|---|---|---|
| Dominio | `domain/generation/resource_catalog.py` | Tipo `reto_prediccion` después de la cápsula de audio | R1 |
| Dominio | `domain/generation/resource_formats.py` | `_predictions` y mínimo de 3 en `MIN_ITEMS` | R2, R3 |
| Dominio | `domain/generation/grounding.py` | `_link_sources` común, `LinkedSourcesResult` y `link_prediction_sources` (50 %); `link_step_sources` sigue igual | R4, R5, R7 |
| Aplicación | `application/services/generation/prompt_drafting.py` | Descripción e instrucciones del tipo, traducción de `predicciones` y verificación con rechazo si quedan menos de 3 | R4–R7 |
| Aplicación | `application/services/generation/rule_based_generator.py` | `_prediction_challenge` | R11 |
| Infraestructura | `infrastructure/llm/gemini_language_model.py` | `predicciones` en el esquema de respuesta | R2 |
| Infraestructura | `infrastructure/http/schemas/generations.py` | Tipo nuevo en la API | R1 |
| Infraestructura | `infrastructure/exporters/scorm_package_exporter.py` | Juego en `ACTIVITY_JS`, `scorm5e.complete`, fuentes por predicción e insignias | R8, R9 |
| Infraestructura | `infrastructure/exporters/unit_document_exporter.py` | Opciones en orden alfabético y clave con la fuente | R10 |
| Pruebas | `tests/unit/test_engage_agent.py` | 13 pruebas | Todos |
| Pruebas | `tests/fixtures/resource_catalog.json`, `test_resource_catalog.py`, `tests/e2e/test_resource_catalog_api.py` | Tipo nuevo; 20 tipos | R1 |
| Docs | `docs/decisions/technical-decisions.md`, `docs/testing.md`, `docs/api/openapi.json`, `docs/api/contracts/generation-request.v1.json` | ADR-020, sección de pruebas y contratos regenerados con los scripts | — |

## Frontend (`plataforma-5e-frontend`, rama `feat/hu-047-prediction-challenge`)

Rutas desde `src/`.

| Archivo | Cambio | Requisito |
|---|---|---|
| `shared/types/domain.ts` | Tipo `reto_prediccion` y estructura `predictions` | R1, R2 |
| `features/review/model/structureFields.ts` | Edición de cada predicción (pregunta, opciones, lo que se revela); mínimo 3 y opciones distintas | R3, R12 |
| `features/review/model/stepSources.ts` → `itemSources.ts` | Fuente de cada paso o predicción («documento, p. X») | R12 |
| `features/review/components/ResourceMediaView.tsx` | Vista previa con las opciones, la correcta marcada, lo que se revela y la fuente | R12 |
| `features/generation/model/requestInterpreter.ts` | Reconoce «reto de predicción» o «reto inicial» al escribir el pedido | R1 |
| `test/resourceCatalogFixture.ts`, `generation/api/resourceCatalogApi.test.ts` | Tipo nuevo; 20 tipos | R1 |
| `features/review/model/itemSources.test.ts` | Pruebas de la revisión | R12 |

## Orden de integración

1. PR del frontend primero: no rompe nada en producción, porque el tipo no aparece hasta que el backend lo publique.
2. PR del backend después; volver a correr su check «End-to-end» si se corrió antes del merge del frontend.
3. Probar en producción y cerrar HU-047 en Notion con la evidencia.
