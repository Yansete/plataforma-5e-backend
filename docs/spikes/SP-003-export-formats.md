# SP-003 Formatos de exportación

## Decisión del proyecto

El catálogo `frontend/src/data/catalog.ts` y el estado de HU-054 establecen dos destinos:

| Destino | Formato | Archivo e importación prevista |
|---|---|---|
| Moodle | Moodle XML | `.xml`; Banco de preguntas → Importar; ítems de opción múltiple |
| Chamilo | QTI 2.1 | `.zip` con `imsmanifest.xml` e ítems QTI 2.1; Ejercicios → Importar QTI2 |

Se descartan QTI 3.0 y SCORM para esta entrega. Las plantillas son fijas (ADR-005): el código construye
el archivo a partir de lo aprobado; un modelo no genera XML libremente.

## Alcance comprobado y pendiente

HU-054 construye ambos archivos en el navegador. La API de demo exporta Moodle XML. Las pruebas
comprueban estructura y fidelidad del Moodle XML, y la estructura ZIP del paquete QTI 2.1.
La importación en instancias reales y sus versiones de Moodle y Chamilo permanece pendiente en TA-006;
esta decisión de formato no acredita esa validación.

Fuentes internas: `frontend/src/data/catalog.ts` y [arquitectura y estado del proyecto](../architecture/overview.md),
que reúne el antiguo registro de estado. No se añaden funciones de exportación en esta limpieza.
