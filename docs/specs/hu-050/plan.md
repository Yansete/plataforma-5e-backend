# HU-050 · Plan técnico

Especificación: [spec.md](spec.md) · Decisión: ADR-021

## Backend (`plataforma-5e-backend`, rama `feat/hu-050-applied-case`)

Rutas desde `backend/src/platform5e/`. La rama parte de `feat/hu-047-prediction-challenge` (o de `main` cuando HU-047
ya esté integrada), porque reutiliza `_link_sources` y el catálogo de 20 tipos.

| Capa | Archivo | Cambio | Requisito |
|---|---|---|---|
| Dominio | `domain/generation/resource_catalog.py` | Tipo `caso_aplicado` después del ejercicio de aplicación | R1 |
| Dominio | `domain/generation/resource_formats.py` | `_criteria` y mínimo de 3 en `MIN_ITEMS`; situación y consigna obligatorias | R2, R3 |
| Dominio | `domain/generation/grounding.py` | `link_criterion_sources` (30 %) sobre `_link_sources`; nombre `criterion` en el resumen | R4, R5, R7 |
| Aplicación | `application/services/generation/prompt_drafting.py` | Descripción e instrucciones del tipo, traducción de `situacion`, `consigna` y `criterios`, y verificación con rechazo si quedan menos de 3 | R4–R7 |
| Aplicación | `application/services/generation/rule_based_generator.py` | `_applied_case` | R12 |
| Infraestructura | `infrastructure/llm/gemini_language_model.py` | `situacion`, `consigna` y `criterios` en el esquema de respuesta | R2 |
| Infraestructura | `infrastructure/http/schemas/generations.py` | Tipo nuevo en la API | R1 |
| Infraestructura | `infrastructure/exporters/scorm_package_exporter.py` | `caso_aplicado` en `ACTIVITY_JS`, fuente por criterio y actividad «completada» | R9, R10 |
| Infraestructura | `infrastructure/exporters/unit_document_exporter.py` | Situación, consigna, espacio para resolver y criterios con su fuente | R11 |
| Pruebas | `tests/unit/test_elaborate_agent.py` | Tipo, estructura, prompt, citas, rechazo, secuencia sin repetir (C02), reglas y exportaciones | Todos |
| Pruebas | `tests/fixtures/resource_catalog.json`, `test_resource_catalog.py`, `tests/e2e/test_resource_catalog_api.py` | Tipo nuevo; 21 tipos | R1 |
| Docs | `docs/decisions/technical-decisions.md`, `docs/testing.md`, `docs/api/openapi.json`, `docs/api/contracts/generation-request.v1.json` | ADR-021, sección de pruebas y contratos regenerados con los scripts | — |

## Frontend (`plataforma-5e-frontend`, rama `feat/hu-050-applied-case`)

Rutas desde `src/`.

| Archivo | Cambio | Requisito |
|---|---|---|
| `shared/types/domain.ts` | Tipo `caso_aplicado` y estructura `scenario`, `task` y `criteria` | R1, R2 |
| `features/review/model/structureFields.ts` | Edición de la situación, la consigna y cada criterio; mínimo 3 y sin criterios repetidos | R3, R13 |
| `features/review/model/itemSources.ts` | Fuente de cada criterio («documento, p. X») | R13 |
| `features/review/components/ResourceMediaView.tsx` | Vista previa con la situación, la consigna y los criterios con su fuente | R13 |
| `features/generation/model/requestInterpreter.ts` | Reconoce «caso aplicado» o «caso de aplicación» al escribir el pedido | R1 |
| `test/resourceCatalogFixture.ts`, `generation/api/resourceCatalogApi.test.ts` | Tipo nuevo; 21 tipos | R1 |
| `features/review/model/itemSources.test.ts` | Pruebas de la revisión | R13 |

## Orden de integración

1. PR del frontend primero: no rompe nada en producción, porque el tipo no aparece hasta que el backend lo publique.
2. PR del backend después; volver a correr su check «End-to-end» si se corrió antes del merge del frontend.
3. Antes del commit del backend, correr `python scripts/export_openapi.py` y `python scripts/export_contracts.py`.
4. Probar en producción y cerrar HU-050 en Notion con la evidencia; con eso se puede cerrar la épica EP-003.
