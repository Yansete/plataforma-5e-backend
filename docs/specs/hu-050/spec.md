# HU-050 · Generar recursos de Elaborar — especificación

- **Épica:** EP-003 Creación de contenido por etapa 5E · **Sprint:** 1 · **Estimación:** 1 pt
- **Responsable:** Juan Alegría
- **Depende de:** HU-003 (orquestador de agentes) y HU-047 (catálogo de 20 tipos)
- **Decisión técnica:** ADR-021 · **Plan:** [plan.md](plan.md)

## Historia

Como docente, quiero que el agente de Elaborar genere un caso aplicado a partir de mi material, con una consigna y
criterios de logro, para que los estudiantes transfieran lo aprendido a una situación nueva sin repetir lo que ya
vieron en las etapas anteriores de la clase.

## Criterios de aceptación (Notion)

- **C01.** Genera un caso aplicado con consigna y criterios de logro.
- **C02.** No repite contenido de las etapas anteriores.

## Alcance

- El «Ejercicio de aplicación» ya existe, cita el material y se verifica desde HU-016, pero es texto corrido: la
  consigna y los criterios quedan mezclados en el contenido y no se pueden revisar ni exportar por separado. Esta
  historia agrega el recurso estructurado: el **Caso aplicado**.
- El C02 ya lo cumple el orquestador de HU-003: un recurso demasiado parecido a otro de la secuencia (60 % de palabras
  útiles compartidas) se pide de nuevo una vez y, si sigue repetido, se rechaza. Esta historia agrega las pruebas que lo
  demuestran para Elaborar.
- Fuera de alcance: calificar la solución del estudiante de forma automática, imágenes o audio dentro del caso
  (Sprint 2, HU-057) y cambiar el «Ejercicio de aplicación».

## Requisitos

| N.º | Requisito | Criterio |
|---|---|---|
| R1 | Nuevo tipo `caso_aplicado` («Caso aplicado»), etapa Elaborar, formato interactivo, publicado en el catálogo del backend | C01 |
| R2 | El caso tiene una situación nueva (`scenario`), una consigna (`task`) y de 3 a 10 criterios de logro (`criteria`); cada criterio tiene su texto y los fragmentos que lo respaldan | C01 |
| R3 | Sin situación, sin consigna o con menos de 3 criterios completos, el caso no es válido; dos criterios iguales cuentan como uno | C01 |
| R4 | Cada criterio cita el fragmento con el concepto que aplica. Se contrasta con la regla de palabras del ADR-014 y un mínimo de 30 %, porque mezcla el concepto con verbos de logro («justifica», «propone»). La situación y la consigna no se contrastan, porque a propósito están en un contexto que no aparece en el material | C01 |
| R5 | Si la cita no respalda el criterio, se enlaza al fragmento que más lo respalda; si ninguno llega al mínimo, el criterio se quita con su motivo | C01 |
| R6 | Si quedan menos de 3 criterios con respaldo, el caso se rechaza con su motivo | C01 |
| R7 | La respuesta de la generación informa `criterionThreshold`, `checkedCriteria`, `supportedCriteria`, `correctedCriteria` y `removedCriteria` | C01 |
| R8 | En una secuencia, un caso demasiado parecido a un recurso de una etapa anterior se pide de nuevo una vez y, si sigue repetido, se rechaza con el motivo «repetía …»; un caso distinto se conserva | C02 |
| R9 | En el SCORM, el estudiante lee la situación y la consigna, escribe su solución y marca los criterios que cumple; cada criterio muestra su fuente | C01 |
| R10 | El LMS recibe el porcentaje de criterios marcados, pero la actividad queda «completada», no aprobada ni desaprobada, porque la solución la califica el docente | C01 |
| R11 | El documento imprimible muestra la situación, la consigna, un espacio para resolver y los criterios con su fuente | C01 |
| R12 | Si la IA no responde, el generador por reglas arma un caso con 3 o 4 criterios tomados de oraciones del material | C01 |
| R13 | En el frontend, el docente ve la situación, la consigna y cada criterio con su fuente; puede editarlos sin perder la cita | C01 |

## Escenarios

1. **Caso con respaldo.** Dado un material sobre TCP y UDP, cuando el docente pide un «Caso aplicado», entonces recibe
   una situación nueva (por ejemplo, la red de un colegio), una consigna y de 3 a 5 criterios, cada uno con su fuente.
2. **Cita equivocada.** Dado un criterio sobre UDP que cita el fragmento de TCP, entonces queda enlazado al fragmento de
   UDP y se cuenta en `correctedCriteria`.
3. **Criterio inventado.** Dado un criterio cuyo concepto no está en el material («Calcula la latencia con la fórmula de
   Shannon»), entonces se quita y aparece en `removedCriteria` con el motivo «Solo el X % … (mínimo 30 %)».
4. **Caso sin respaldo suficiente.** Dado un caso con solo 2 criterios respaldados, entonces no se guarda y el rechazo
   dice «solo 2 criterio(s) de logro se apoyan en el material».
5. **Situación fuera del material.** Dada una situación sobre un colegio, que no aparece en el material, entonces el
   caso no se rechaza por eso.
6. **Repite la explicación.** Dada una secuencia con una explicación y un caso aplicado que la copia, entonces el caso
   se pide de nuevo y, si sigue igual, se rechaza con «repetía».
7. **Caso distinto en la secuencia.** Dada una secuencia de Enganchar, Explicar y Elaborar, entonces el caso se
   conserva, lo redacta el «Agente de Elaborar» y recibe lo que redactaron los agentes anteriores.
8. **En el LMS.** Dado un estudiante que escribe su solución y marca 2 de 3 criterios, entonces ve «2 de 3 criterios
   de logro» y el LMS recibe 67 con estado `completed`.
9. **Sin IA.** Dado que Gemini no responde, entonces el generador por reglas arma el caso y todos sus criterios pasan
   la verificación.

## Verificación

- Pruebas unitarias: `backend/tests/unit/test_elaborate_agent.py`.
- Catálogo con 21 tipos: `test_resource_catalog.py`, `tests/e2e/test_resource_catalog_api.py` y, en el frontend,
  `resourceCatalogApi.test.ts`.
- Frontend: `src/features/review/model/itemSources.test.ts`.
- En producción: generar un «Caso aplicado» con Gemini en la Unidad 2 del curso de Redes, también dentro de una
  secuencia con Explicar, revisarlo, resolverlo en el SCORM y guardar la evidencia.
