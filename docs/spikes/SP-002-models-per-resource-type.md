# SP-002 · Modelos de generación por tipo de recurso

**Fecha:** 05/10/2026 · **Estado:** recomendación **propuesta**. Requiere aprobación del equipo y una evaluación de
calidad con docentes (sección 8). **Alcance:** modelos de **generación**. El modelo de embeddings ya se eligió en
[SP-001](SP-001-embedding-models.md).

> Identificadores según el backlog vigente en Notion. En el backlog v3.0 de `docs/project-management/`, SP-002 es el spike de
> embeddings y EN-004 es la línea base manual de tiempos, no una decisión de arquitectura.

## 1. Objetivo y criterios

Determinar qué modelo de IA necesita cada tipo de recurso que generará el sistema y cuánto cuesta cada generación.

| Criterio | Cumplimiento |
|---|---|
| C01: cada tipo de recurso tiene un modelo candidato | Cumplido: candidato y alternativa por tipo (sección 3) |
| C02: se estima el costo por generación | Cumplido como **estimación**: precios oficiales consultados el 05/10/2026 y tamaños supuestos (sección 4). No se midió con llamadas reales |

## 2. Punto de partida (lo que hay en el repositorio)

- **No hay ningún proveedor de LLM configurado.** No existen SDKs, claves ni variables de entorno de IA. El frontend
  solo depende de React y Vite, y `.env.example` solo tiene variables de PostgreSQL.
- **No hay documento de arquitectura que condicione la elección.** El backend y su lenguaje siguen sin decidirse (EN-001).
- La generación del frontend es **simulada** (`frontend/src/services/generationService.ts`). Los tipos de recurso
  definidos en `frontend/src/data/catalog.ts` son: pregunta detonante, sondeo diagnóstico, guía de exploración, caso
  de indagación, explicación citada, glosario, ejercicio de aplicación e ítem de opción múltiple. La pantalla de
  Configuración (HU-024) ofrece además los enfoques «Textual, Gamificado, Multimedia, Kinestésico».
- Restricciones de los documentos del curso:
  - El Project Charter descarta entrenar o afinar modelos: el LLM «actúa únicamente como redactor» sobre la
    evidencia recuperada.
  - Presupuesta **USD 40** en créditos de API para LLM y embeddings juntos.
  - Excluye del alcance el «contenido multimodal (video, audio)» y los «simuladores complejos».
- Decisiones anteriores que afectan a esta: contrato JSON con citas por afirmación (HU-006, indicador I22 ≥ 95 %),
  revisión docente obligatoria (HU-010) y exportación Moodle XML / QTI 2.1 (SP-003).

## 3. Tipos de recurso: salida, capacidades y modelos

### 3.1 Qué produce cada tipo

| Tipo | Salida concreta | Capacidades necesarias |
|---|---|---|
| **Textual** | Pregunta detonante, sondeo, guía de exploración, caso, explicación citada, glosario, ejercicio. JSON del contrato HU-006: título, cuerpo y `citas[]` con identificadores de fragmento | Redacción en español, seguir instrucciones pedagógicas, **salida JSON con esquema**, citar fragmentos |
| **Ítem de opción múltiple** | JSON: enunciado, clave, 3 o 4 distractores con retroalimentación y fragmento de origen cada uno. **El XML QTI lo genera código**, no el modelo | Razonamiento sobre errores conceptuales (distractores plausibles), JSON con esquema |
| **Gamificado** | JSON de juego: quiz, emparejamiento, ordenar pasos, completar huecos, crucigrama. En el crucigrama, el modelo da pares palabra-pista y **la cuadrícula la arma código** | JSON con esquema, variedad sin repetir, fidelidad al material |
| **Multimedia · diagrama** | Código **Mermaid** (flujo, secuencia, árbol, mapa conceptual) más una descripción alternativa. Se renderiza en el cliente | Generar código válido, texto en español exacto |
| **Multimedia · imagen** (opcional) | Imagen ilustrativa (portada, escena para «Enganchar»). Sin texto dentro de la imagen | Generación de imagen |
| **Multimedia · guion** | Guion de audio o video con tiempos y narración, en texto | Redacción en español |
| **Multimedia · audio** (fuera del MVP) | Narración del guion | Texto a voz en español |
| **Interactivo** | JSON de contenido **H5P** con bibliotecas fijas (Drag the Words, Fill in the Blanks, Interactive Book…). El empaquetado `.h5p` lo hace código | JSON con esquema; no código ejecutable libre |

### 3.2 Modelo candidato y alternativa por tipo

| Tipo | Candidato principal | Alternativa | Por qué |
|---|---|---|---|
| Textual | **Claude Sonnet 5.5** (API) | Gemini 3.8 Flash (API) | Sonnet: buena redacción y salida estructurada. Flash: unas 3 veces más barato |
| Ítem de opción múltiple | **Claude Sonnet 5.5**, esfuerzo `high` | Claude Opus 5.5 (API) | Es el recurso donde más importa la calidad (distractores no funcionales, I3/I5). Opus solo si la evaluación muestra distractores débiles |
| Gamificado | **Claude Sonnet 5.5** | Qwen3.6-27B (open source, Apache 2.0, autoalojado) | JSON sencillo: es el tipo que mejor admite un modelo abierto si se quiere evitar el envío de datos |
| Multimedia · diagrama | **Claude Sonnet 5.5** (código Mermaid) | Gemini 3.8 Flash | Un diagrama como código conserva el texto exacto y se puede editar y citar; no hace falta un modelo de imagen |
| Multimedia · imagen | **Gemini 3.1 Flash Image** (API) | FLUX.1 [schnell] (open source, Apache 2.0) | Único tipo que necesita un modelo distinto. FLUX exige una GPU propia o un servicio de terceros |
| Multimedia · guion | **Claude Sonnet 5.5** | Gemini 3.8 Flash | Es texto: mismo modelo que Textual |
| Multimedia · audio | Gemini 3.8 Flash TTS (API) | OpenAI gpt-4o-mini-tts (API) | Solo si el equipo amplía el alcance (el Charter excluye audio y video) |
| Interactivo (H5P) | **Claude Sonnet 5.5** | OpenAI gpt-5.4-mini (API) | Requiere JSON largo y exacto. gpt-5.4-mini es la opción barata de otro proveedor |

### 3.3 Ficha de los modelos

| Modelo | Proveedor · licencia | Capacidades relevantes | Español | Precio (USD) · fuente y fecha | Límites y notas |
|---|---|---|---|---|---|
| Claude Sonnet 5.5 (`claude-sonnet-5-5`) | Anthropic · comercial (API) | Texto, salida estructurada (`output_config.format`), razonamiento adaptativo, visión; **no genera imágenes** | Bueno (multilingüe); **sin medir** en este proyecto | 2 entrada / 10 salida por 1M tokens; lectura de caché 0,20; lotes −50 % · claude.com/pricing, 05/10/2026 | Contexto de 1M tokens, salida hasta 128K. El razonamiento se cobra como salida. La función de citas nativa no se puede combinar con salida estructurada: las citas van en nuestro propio JSON |
| Claude Opus 5.5 (`claude-opus-5-5`) | Anthropic · comercial | Igual que Sonnet, con más capacidad | Bueno; sin medir | 4 / 20; caché 0,20; lotes −50 % · claude.com/pricing, 05/10/2026 | El esfuerzo por defecto es `medium` |
| Gemini 3.8 Flash (`gemini-3.8-flash`) | Google · comercial | Texto, salida estructurada (por verificar en este modelo), multimodal | Bueno; sin medir | 0,75 / 3,75 **hasta el 31/12/2026**; **1,50 / 7,50 desde el 01/01/2027**; lotes −50 % · ai.google.dev/pricing, 05/10/2026 | Capa gratuita: Google usa los datos para mejorar sus productos (ver SP-001). Usar la capa de pago con material real |
| OpenAI gpt-5.4-mini | OpenAI · comercial | Texto, salida estructurada (por verificar en este modelo) | Bueno; sin medir | 0,75 / 4,50; entrada en caché 0,075; lotes −50 % · developers.openai.com/api/docs/pricing, 05/10/2026 | La cuenta del equipo no tenía saldo (SP-001) |
| Qwen3.6-27B | Alibaba · **Apache 2.0** (pesos abiertos) | Texto y código; más de 200 idiomas según la publicación | Por verificar | Sin costo por token; costo de GPU **por verificar** | Necesita una GPU con mucha memoria (estimación: 24 GB o más con cuantización, por verificar). No cabe en el hosting de bajo costo del Charter |
| Gemini 3.1 Flash Image (`gemini-3.1-flash-image`) | Google · comercial | Generación de imagen | El texto dentro de la imagen no es fiable; se evita | **0,067 por imagen** de 1K; versión Lite 0,0336; lotes −50 %; sin capa gratuita · ai.google.dev/pricing, 05/10/2026 | — |
| FLUX.1 [schnell] | Black Forest Labs · **Apache 2.0** | Generación de imagen | Igual que el anterior: no poner texto | Sin costo por imagen; GPU **por verificar** | Necesita GPU dedicada (requisito de memoria por verificar) |
| gpt-image-2 / 2.5 | OpenAI · comercial | Generación de imagen | OpenAI reconoce que aún tiene problemas con el texto | Por tokens (salida 30 por 1M); **costo por imagen por verificar** (la documentación no da los tokens por imagen) | Descartado por falta de un precio por imagen verificable |
| Gemini 3.8 Flash TTS | Google · comercial | Texto a voz | Por verificar (voces en español) | 0,50 por 1M tokens de texto de entrada y 9,00 por 1M tokens de audio de salida hasta el 31/12/2026 (el doble desde 2027) · 05/10/2026 | Fuera del alcance actual |
| gpt-4o-mini-tts | OpenAI · comercial | Texto a voz | Por verificar | La página indica 0,60 por 1M caracteres; **estructura de precio por verificar** | Fuera del alcance actual |

No se incluye la **generación de video**: el Charter la excluye, su costo es alto y no puede anclarse ni citarse.

## 4. Costo estimado por generación

### 4.1 Supuestos

| Concepto | Valor supuesto | Base |
|---|---|---|
| Instrucciones del agente y esquema JSON | 1.500 tokens | Estimación: sistema, contrato HU-006 y reglas pedagógicas |
| Contexto RAG | 5 fragmentos × 400 tokens = 2.000 tokens | Límite de 450 tokens por fragmento de SP-001; se toma el extremo alto (3-5 fragmentos) |
| Metadatos y pedido del docente | 500 tokens | Unidad, RA, etapa, indicaciones |
| **Entrada total por generación** | **4.000 tokens** | |
| Razonamiento | 500 a 2.000 tokens según el tipo | **Supuesto sin medir**; se cobra como salida. Más alto en ítems |
| Una sola llamada por generación, sin reintentos | — | Las regeneraciones se tratan en 4.3 |
| Sin caché ni lotes | — | El docente espera la respuesta. La caché ahorraría ~USD 0,003 por llamada en Sonnet |

Fórmula: **costo = entrada × precio de entrada + (salida + razonamiento) × precio de salida**.

### 4.2 Resultado

Precios del 05/10/2026, en USD.

| Tipo | Salida + razonamiento (tokens) | Candidato: cálculo | **Costo** | Alternativa: cálculo | Costo alternativa |
|---|---|---|---|---|---|
| Textual (1 recurso) | 1.500 + 1.000 = 2.500 | Sonnet 5.5: 4.000×2/1M + 2.500×10/1M = 0,008 + 0,025 | **0,033** | Gemini 3.8 Flash: 4.000×0,75/1M + 2.500×3,75/1M | 0,012 (0,025 desde 2027) |
| Ítem de opción múltiple (1 ítem) | 800 + 2.000 = 2.800 | Sonnet 5.5: 0,008 + 2.800×10/1M = 0,008 + 0,028 | **0,036** | Opus 5.5: 4.000×4/1M + 2.800×20/1M = 0,016 + 0,056 | 0,072 |
| Gamificado (1 juego de 10 elementos) | 2.000 + 1.000 = 3.000 | Sonnet 5.5: 0,008 + 0,030 | **0,038** | Qwen3.6-27B autoalojado | 0 por llamada + GPU (por verificar) |
| Diagrama Mermaid | 800 + 1.000 = 1.800 | Sonnet 5.5: 0,008 + 0,018 | **0,026** | Gemini 3.8 Flash: 0,003 + 1.800×3,75/1M | 0,010 |
| Imagen ilustrativa | Prompt de imagen con Sonnet (salida 300 + 500) + 1 imagen | 0,008 + 800×10/1M + 0,067 = 0,008 + 0,008 + 0,067 | **0,083** | Igual con Flash Lite Image (0,0336) | 0,050 |
| Guion de audio o video | 1.200 + 500 = 1.700 | Sonnet 5.5: 0,008 + 0,017 | **0,025** | Gemini 3.8 Flash: 0,003 + 1.700×3,75/1M | 0,009 |
| Audio de 90 s (fuera del MVP) | ~2.900 tokens de audio | Gemini 3.8 Flash TTS: 2.900×9/1M ≈ 0,026 (supone ~32 tokens de audio por segundo, **por verificar**) | **≈ 0,03 (por verificar)** | gpt-4o-mini-tts | Por verificar |
| Interactivo H5P | 3.000 + 1.500 = 4.500 | Sonnet 5.5: 0,008 + 0,045 | **0,053** | gpt-5.4-mini: 4.000×0,75/1M + 4.500×4,5/1M = 0,003 + 0,020 | 0,023 |

### 4.3 Costo de una secuencia 5E completa y del presupuesto

Ejemplo de una unidad: 5 recursos textuales, 10 ítems, 2 juegos, 1 diagrama y 1 recurso interactivo, todos con el
candidato principal y sin imágenes:

5 × 0,033 + 10 × 0,036 + 2 × 0,038 + 0,026 + 0,053 = **USD 0,68 por unidad**.

Si cada recurso se genera unas 3 veces de media (descartes y regeneraciones), sale a **unos USD 2 por unidad**. Con el
presupuesto del Charter (USD 40, del que los embeddings consumen una cantidad despreciable según SP-001) alcanzaría para
**unas 20 unidades completas**, sin contar el consumo durante el desarrollo y las pruebas. Ese consumo puede ser mayor
y conviene vigilarlo con el `usage` que devuelve cada llamada.

## 5. Riesgos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Los tokens de razonamiento son una suposición | El costo real puede ser el doble o la mitad | Registrar el `usage` de cada llamada desde la primera prueba y recalcular |
| Cambios de precio: Gemini 3.8 Flash duplica su precio el 01/01/2027; los modelos *preview* pueden cambiar | La alternativa barata deja de serlo poco después del piloto | Fijar el modelo por configuración y revisar los precios antes de cada sprint |
| La calidad en español **no se midió** con ningún modelo | La elección se basa en documentación, no en evidencia propia | Evaluación con docentes antes de cerrar la decisión (sección 8) |
| Texto erróneo dentro de imágenes generadas | Faltas de ortografía o datos falsos en material didáctico | No pedir texto en imágenes; usar diagramas como código (Mermaid) |
| Las imágenes no se pueden anclar a un fragmento | Rompe la trazabilidad (I22) si se presentan como evidencia | Marcarlas como ilustrativas; la cita queda en el recurso de texto que las acompaña; revisión docente obligatoria |
| HTML/JS generado libremente | Riesgo de seguridad (scripts en el LMS) y difícil de validar | Solo JSON H5P con bibliotecas fijas, validado contra un esquema |
| Crucigramas y sopas de letras armados por el LLM | Cuadrículas inconsistentes | El modelo da palabras y pistas; un algoritmo arma la cuadrícula |
| Envío del material docente a terceros | Privacidad y permiso de uso | Capa de pago (sin entrenamiento con los datos) y respeto del permiso registrado en Carga. Si se exige no enviar nada, la opción es un modelo abierto autoalojado (más costo de infraestructura) |
| Dependencia de un solo proveedor | Caídas, cambios de precio o rechazos de contenido | Interfaz de generación independiente del proveedor, con la alternativa configurada para cambiar de modelo |
| Alcance: el Charter excluye audio, video y simuladores | Generar multimedia o interactivos podría salirse del alcance aprobado | Confirmar con el equipo qué incluye «Multimedia» e «Interactivo/Kinestésico» antes de implementarlos |
| Presupuesto de USD 40 compartido con el desarrollo | Agotar los créditos antes del piloto (ya ocurrió con la cuenta de OpenAI en SP-001) | Límite de gasto en la consola del proveedor y una cuenta separada para el piloto |

## 6. Recomendación (propuesta)

1. **Un solo modelo de texto para casi todo: Claude Sonnet 5.5.** Cubre textual, ítems, gamificado, diagramas,
   guiones e interactivos H5P, porque todos se reducen a **texto o JSON con esquema**. Los cinco agentes 5E comparten
   el modelo y cambian solo sus instrucciones y esquemas. Así hay un solo proveedor que integrar, un solo formato de
   salida estructurada y una sola caché.
2. **Un modelo aparte solo para imágenes ilustrativas opcionales: Gemini 3.1 Flash Image** (USD 0,067 por imagen).
   No se usa para diagramas ni para nada que deba contener texto.
3. **Gemini 3.8 Flash como segundo proveedor configurado**, por si falla Sonnet o se agota el presupuesto. Hasta fin
   de 2026 cuesta unas 3 veces menos.
4. **Lo que hace el código, no el modelo:** el Moodle XML y el paquete QTI 2.1, las cuadrículas de juego y el
   renderizado de Mermaid. Así el modelo solo produce contenido y no formatos estándar que puede romper.
5. **Fuera del MVP:** video (excluido por el Charter), audio TTS (excluido; costo estimado ≈ USD 0,03 por minuto y
   medio si se aprueba) y HTML/JS libre.
6. **Antes de implementar:** el equipo debe aclarar si «Kinestésico» (pantalla de HU-024) e «Interactivo»
   (tarea SP-002) son el mismo tipo. Si «kinestésico» significa una actividad física en el aula, es un recurso
   **textual** (instrucciones) y no necesita un modelo propio.

## 7. Impacto en otras tareas

- **Contratos (EN-003):** cada tipo necesita su esquema JSON, que se usará como salida estructurada del modelo. Las
  citas a fragmentos van dentro del esquema, porque la función de citas nativa de Claude no se combina con salida
  estructurada.
- **Backend (EN-001):** variables nuevas `ANTHROPIC_API_KEY` y, para las alternativas, `GEMINI_API_KEY`. Hay que
  registrar `usage` (tokens) por generación para medir I1 y el costo real.
- **Pruebas:** usar dobles de prueba del cliente del modelo en las pruebas unitarias, igual que en SP-001.

## 8. Evaluación pendiente para cerrar la decisión

Antes de implementar, generar con **Sonnet 5.5 y Gemini 3.8 Flash** la misma muestra a partir de fragmentos reales:
10 ítems de opción múltiple, 5 recursos textuales y 2 juegos. Pedir a dos docentes que los valoren a ciegas con la
rúbrica de I3/I5 y registrar el `usage` real. Se adopta Gemini si su calidad no es inferior, porque es más barato; y
Opus 5.5 para los ítems solo si Sonnet muestra distractores débiles. Costo de la prueba: menos de USD 1.

## Fuentes (consultadas el 05/10/2026)

- Precios de Claude: <https://claude.com/pricing>
- Precios de Gemini (texto, imagen, TTS): <https://ai.google.dev/gemini-api/docs/pricing>
- Precios de OpenAI (texto, imagen, TTS): <https://developers.openai.com/api/docs/pricing> y guía de imagen
  <https://developers.openai.com/api/docs/guides/image-generation>
- FLUX.1 [schnell], licencia Apache 2.0: <https://en.wikipedia.org/wiki/Flux_(text-to-image_model)>
- Qwen (pesos abiertos, Apache 2.0): <https://en.wikipedia.org/wiki/Qwen> y <https://qwenlm.github.io/blog/qwen3/>
