# Acuerdos · Plan de cambios solicitado por el docente (17/10/2026)

**Semana:** 8 (12–18/10/2026) · **Sprint:** cierre del Sprint 1 · **Documento del docente:**
[2026-10-17-plan-de-cambios-docente.pdf](2026-10-17-plan-de-cambios-docente.pdf)

## Pedidos del docente

| # | Pedido | Prioridad |
|---|---|---|
| 01 | Editor de texto enriquecido (WYSIWYG) en lugar de texto plano: encabezados H1–H3, negritas, cursivas, listas y enlaces; los estilos se guardan y se exportan | Alta |
| 02 | Selección múltiple e independiente por etapa 5E (casillas en lugar de una sola opción), con formatos combinados | Alta |
| 03 | Más opciones por etapa y generación multimodal: imágenes, diagramas, esquemas e infografías, audios (pódcast, cápsulas detonantes) y actividades interactivas | Media |
| 04 | Revisión unificada en la secuencia didáctica, SCORM multirrecurso con sus medios (mp3, png…) y validación en Canvas | Media |
| 05 | Registrar todas las actas de reunión y acuerdos de sprint en la carpeta de evidencias | Obligatorio |

El docente confirmó que el punto 03 entra en esta entrega, aunque el Sprint 1 se había acordado solo con texto
(ADR-008). Plazo: domingo 18/10/2026.

## Decisiones del equipo

- Los cinco puntos se implementan en una sola entrega (detalle técnico en ADR-011).
- Catálogo de 18 tipos de recurso: cada etapa combina texto con gráficos, imagen, audio o actividades.
- Los gráficos (mapa conceptual, infografía, diagrama de proceso) los dibuja la plataforma a partir de la estructura
  que redacta la IA, para que siempre se puedan editar y exportar.
- Imágenes y voz con Gemini. La capa gratuita no genera imágenes: sin facturación activa, la imagen se muestra como
  una tarjeta con su descripción y el audio se escucha con la voz del navegador. La decisión de activar la
  facturación queda a cargo del equipo.
- El paquete SCORM 1.2 incluye todos los recursos aprobados con sus archivos. No hay una instancia de Canvas para
  probar; Canvas importa SCORM 1.2, y el paquete se valida con las pruebas automáticas y en SCORM Cloud.
- Moodle XML sigue con preguntas de opción múltiple (único tipo verificado en Moodle).
- Las actas se copian desde Notion a `docs/project-management/actas/` (instrucciones en el README de esta carpeta).

## Responsables

| Tarea | Responsable |
|---|---|
| Cambios 01–04 (código, pruebas y despliegue) | Juan Alegria; revisa y fusiona el líder de la semana |
| Exportar las actas de Notion a esta carpeta | Silvana Diaz (Scrum Master) |
| Validación del SCORM en SCORM Cloud | Juan Alegria |
