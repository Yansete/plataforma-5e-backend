# HU-047 · Generar recursos de Enganchar — especificación

- **Épica:** EP-003 Creación de contenido por etapa 5E · **Sprint:** 1 · **Estimación:** 1 pt
- **Responsable:** Yan Hui Liu Dai · **Revisor:** Juan Alegría
- **Depende de:** HU-003 (orquestador de agentes)
- **Decisión técnica:** ADR-020 · **Plan:** [plan.md](plan.md)

## Historia

Como docente, quiero que el agente de Enganchar genere, además de una pregunta o un sondeo, un recurso gamificado
basado en mi material, para iniciar la clase despertando la curiosidad de los estudiantes y sabiendo de qué parte del
material sale cada respuesta.

## Criterios de aceptación (Notion)

- **C01.** Genera al menos un recurso gamificado y uno textual anclados a la unidad.
- **C02.** Cada recurso cita su fragmento de origen.

## Alcance

- Los recursos textuales de Enganchar ya existen y se verifican desde HU-016: «Pregunta detonante» y «Sondeo de ideas
  previas». Esta historia agrega el recurso gamificado: el **Reto de predicción**.
- Fuera de alcance: imágenes o audio dentro del reto (Sprint 2, HU-057), y cambiar la evaluación por niveles de
  HU-051.

## Requisitos

| N.º | Requisito | Criterio |
|---|---|---|
| R1 | Nuevo tipo `reto_prediccion` («Reto de predicción»), etapa Enganchar, formato interactivo, publicado en el catálogo del backend | C01 |
| R2 | De 3 a 10 predicciones. Cada una tiene una pregunta, la opción correcta, una opción equivocada, una segunda opción equivocada opcional y lo que dice el material (`reveal`) | C01 |
| R3 | No se aceptan dos opciones iguales ni predicciones incompletas | C01 |
| R4 | Cada predicción cita el fragmento que contiene su respuesta. Se contrastan la opción correcta y lo que se revela (mínimo 50 % de sus palabras útiles en el fragmento); la pregunta y las opciones equivocadas no se contrastan | C02 |
| R5 | Si la cita no respalda la respuesta, la predicción se enlaza al fragmento que más la respalda; si ninguno llega al mínimo, se quita con su motivo | C02 |
| R6 | Si quedan menos de 3 predicciones con respaldo, el recurso se rechaza con su motivo | C02 |
| R7 | La respuesta de la generación informa `predictionThreshold`, `checkedPredictions`, `supportedPredictions`, `correctedPredictions` y `removedPredictions` | C02 |
| R8 | En el SCORM es un juego: al elegir se ve al instante si acertó, lo que dice el material y su fuente; suma 100 puntos por acierto y 50 de racha desde el segundo acierto seguido; al final muestra aciertos, puntos e insignia (umbrales de HU-051) | C01 |
| R9 | El LMS recibe el porcentaje de aciertos, pero la actividad queda «completada», no aprobada ni desaprobada, porque es para iniciar la clase | C01 |
| R10 | El documento imprimible muestra las opciones en orden alfabético y una clave con la respuesta, lo que dice el material y la fuente | C02 |
| R11 | Si la IA no responde, el generador por reglas arma de 3 a 4 predicciones con oraciones del material | C01, C02 |
| R12 | En el frontend, el docente ve cada predicción con sus opciones, la correcta marcada, lo que se revela y su fuente; puede editarlas sin perder la cita | C01, C02 |

## Escenarios

1. **Reto con respaldo.** Dado un material sobre TCP y UDP, cuando el docente pide un «Reto de predicción», entonces
   recibe de 3 a 5 predicciones, cada una con la fuente de su respuesta.
2. **Cita equivocada.** Dada una predicción sobre UDP que cita el fragmento de TCP, entonces queda enlazada al
   fragmento de UDP y se cuenta en `correctedPredictions`.
3. **Respuesta inventada.** Dada una predicción cuya respuesta no está en el material («ARPANET se creó en 1969»),
   entonces se quita y aparece en `removedPredictions` con el motivo «Solo el X % … (mínimo 50 %)».
4. **Reto sin respaldo suficiente.** Dado un reto con solo 2 predicciones respaldadas, entonces no se guarda y el
   rechazo dice «solo 2 predicción(es) tienen su respuesta en el material».
5. **Opción equivocada fuera del material.** Dada una opción equivocada que no aparece en el material, entonces la
   predicción no se quita por eso.
6. **Juego en el LMS.** Dado un estudiante que acierta 2 de 3, entonces ve 250 de 400 puntos, la insignia Bronce, y
   el LMS recibe 67 con estado `completed`.
7. **Sin IA.** Dado que Gemini no responde, entonces el generador por reglas arma el reto y todas sus predicciones
   pasan la verificación.

## Verificación

- Pruebas unitarias: `backend/tests/unit/test_engage_agent.py`.
- Catálogo con 20 tipos: `test_resource_catalog.py`, `tests/e2e/test_resource_catalog_api.py` y, en el frontend,
  `resourceCatalogApi.test.ts`.
- Frontend: `src/features/review/model/itemSources.test.ts`.
- En producción: generar un «Reto de predicción» con Gemini en la Unidad 2 del curso de Redes, revisarlo, jugarlo en
  el SCORM y guardar la evidencia.
