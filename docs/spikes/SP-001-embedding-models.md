# SP-001 · Investigación de modelos de embeddings

**Fecha:** 05/10/2026 · **Estado:** recomendación **propuesta**, pendiente de aprobación del equipo y de la prueba con
material real · **Código del experimento:** [`docs/spikes/sp-001-embedding-benchmark/`](sp-001-embedding-benchmark/)

> Identificadores según el backlog vigente en Notion. En el backlog v3.0 de `docs/project-management/` esta investigación
> corresponde a SP-002 («modelo de embeddings y motor vectorial»), cuyo alcance incluye también comparar motores
> vectoriales; este spike cubre solo los modelos.

## 1. Objetivo

Comparar modelos de embeddings multilingües y recomendar uno para vectorizar el material de los cursos
(PDF/TXT, mayormente en español), de modo que la búsqueda semántica recupere el fragmento correcto para
generar recursos de la secuencia 5E.

Criterios de aceptación:

| Criterio | Cumplimiento |
|---|---|
| C01: comparar al menos dos modelos por calidad, costo y latencia | Cumplido: cinco modelos medidos, tres locales y dos de API (Gemini). OpenAI no se pudo medir por falta de saldo; su costo se calculó con el precio oficial |
| C02: dejar la recomendación registrada en un documento | Cumplido (este documento, sección 6) |

## 2. Punto de partida

- El repositorio solo contiene el frontend de demostración (React + TypeScript). **No hay backend, base de datos,
  extracción de PDF, segmentación ni embeddings**; la vectorización de la interfaz es simulada.
- El lenguaje del backend no está decidido (EN-001).
- El Project Charter prevé PostgreSQL con **pgvector** (Qdrant como alternativa), búsqueda **híbrida**
  (densa + léxica) con reordenamiento y un presupuesto de **USD 40** en créditos de API para LLM y embeddings juntos.

## 3. Candidatos

| Modelo | Tipo | Dimensión | Máx. tokens | Licencia | Precio (USD / 1M tokens) | Motivo de inclusión |
|---|---|---|---|---|---|---|
| `intfloat/multilingual-e5-base` | Local | 768 | 512 | MIT | 0 | Buen rendimiento multilingüe con poco consumo; exige prefijos `query:` / `passage:` |
| `BAAI/bge-m3` | Local | 1024 | 8192 | MIT | 0 | Admite fragmentos largos y también produce vectores léxicos dispersos (útil para búsqueda híbrida) |
| OpenAI `text-embedding-3-small` | API | 1536 (ajustable) | 8191 | Comercial | 0,02 | El más barato de los de API; dimensión reducible |
| Google `gemini-embedding-001` | API | 3072 (reducible a 768/1536) | 2048 | Comercial | 0,15* | Multilingüe; capa gratuita |
| `paraphrase-multilingual-MiniLM-L12-v2` | Local | 384 | 128 | Apache 2.0 | 0 | Solo línea base de referencia |

\*Precios consultados el 05/10/2026 en las páginas oficiales. `gemini-embedding-001` ya no figura en la página de precios de
Google (se usa su último precio conocido). Google publicó en abril de 2026 **`gemini-embedding-2`** (8.192 tokens, multimodal,
USD 0,20 / 1M tokens, capa gratuita); se añadió a la comparación (`gemini-2`).

## 4. Metodología

**Conjunto de prueba** (`dataset.json`):

- 18 fragmentos en español sobre estructuras de datos: 12 tomados de los datos de demostración del frontend
  (material ficticio) y 6 redactados para el spike como **distractores cercanos** (p. ej. pila con lista enlazada
  frente a pila con arreglo; recorrido por niveles, que menciona colas y árboles).
- 16 consultas que **parafrasean** su fragmento relevante sin repetir sus palabras clave
  (p. ej. «notación polaca inversa» para el fragmento que dice «notación posfija»). Una respuesta correcta por consulta.

**Métricas:**

- *Calidad*: se ordenan los 18 fragmentos por similitud coseno con cada consulta. **Recall@k** = proporción de consultas
  cuyo fragmento relevante queda entre los k primeros; **MRR** = promedio de 1/posición. Se calcula sin filtro y con
  filtro por unidad, como hará el sistema.
- *Latencia*: ms por fragmento al indexar por lotes (con los fragmentos del conjunto, ~48 tokens, y con fragmentos
  de ~400 tokens, tamaño esperado en producción) y ms por consulta individual (promedio y p95 sobre 3 rondas).
  Se excluyen la descarga y la carga del modelo.
- *Costo*: USD por 1.000 fragmentos de 400 tokens = 400.000 tokens × precio por token. Los modelos locales no tienen
  costo por uso, pero sí de hardware (memoria del servidor).

**Entorno:** MacBook con Apple M1, 8 GB de RAM, macOS, Python 3.9.6, sentence-transformers 5.1.2, torch 2.8.0,
**solo CPU** (para aproximar un servidor sin GPU).

## 5. Resultados

Medición del 05/10/2026 (`docs/spikes/sp-001-embedding-benchmark/results/`).

| Modelo | Dim. | R@1 | R@3 | R@5 | MRR | MRR (filtro unidad) | ms/fragmento (~48 tokens) | ms/fragmento (~400 tokens) | ms/consulta (prom.) | ms/consulta (p95) | USD / 1.000 fragmentos |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **multilingual-e5-base** | 768 | 0,94 | 1,00 | 1,00 | **0,969** | 0,969 | 21,2 | 124,4 | 36,1 | 40,5 | 0 |
| bge-m3 (denso) | 1024 | 0,94 | 1,00 | 1,00 | 0,958 | 0,958 | 74,2 | 426,0 | 109,4 | 132,7 | 0 |
| MiniLM-L12-v2 (línea base) | 384 | 0,81 | 1,00 | 1,00 | 0,906 | 0,906 | 8,3 | 13,9† | 12,4 | 13,6 | 0 |
| Google gemini-embedding-001 (768) | 768 | **1,00** | 1,00 | 1,00 | **1,000** | 1,000 | 217,6 | 113,1 | 1.329,0‡ | 1.712,2‡ | 0,060 |
| Google gemini-embedding-2 (768) | 768 | **1,00** | 1,00 | 1,00 | **1,000** | 1,000 | 114,1 | 113,9 | 1.285,8‡ | 1.502,3‡ | 0,080 |
| OpenAI text-embedding-3-small | 1536 | — | — | — | — | — | — | — | — | — | 0,008 |

— No medido: OpenAI respondió `HTTP 429 insufficient_quota` (clave válida, cuenta sin saldo, 05/10/2026). Para medirlo
basta recargar saldo y ejecutar `benchmark.py --modelos openai-3-small`.
‡ Latencia de API medida desde una conexión doméstica: incluye la ida y vuelta por la red, que domina el tiempo.
En los modelos de Gemini los tokens se estiman (la API no los informa).
† MiniLM trunca a 128 tokens: es rápido porque **descarta** el 70 % de cada fragmento de 400 tokens.

**Fallos por consulta** (posición del fragmento relevante cuando no fue el primero):

| Modelo | Consultas no resueltas en 1.ª posición |
|---|---|
| multilingual-e5-base | q12 (recorrido inorden) → 2.ª |
| bge-m3 | q14 (rebalanceo AVL) → 3.ª |
| MiniLM | q11 (pila llena), q13 (árbol degenerado), q14 (rebalanceo AVL) → 2.ª |
| gemini-embedding-001 y gemini-embedding-2 | Ninguna |

**Observaciones:**

- Todos los modelos encuentran siempre el fragmento correcto entre los 3 primeros (R@3 = 1,00). Los dos de Gemini
  aciertan las 16 consultas en primera posición; e5-base y bge-m3 fallan una cada uno. Con 18 fragmentos el conjunto
  **no discrimina bien**: la diferencia entre Gemini, e5-base y bge-m3 es **una sola consulta**. La línea base es
  claramente inferior.
- El filtro por unidad no cambió resultados: los errores fueron confusiones dentro de la misma unidad, que es lo que
  el sistema tendrá que resolver.
- e5-base es **~3,4 veces más rápido** que bge-m3 en CPU y ocupa ~1,1 GB frente a ~4,3 GB en disco.
  Indexar 1.000 fragmentos de 400 tokens tomaría ~2 min con e5-base y ~7 min con bge-m3 en este equipo.
- La latencia varía entre ejecuciones en un portátil compartido (en una primera corrida bge-m3 dio 301 ms/fragmento);
  se reporta la segunda ejecución, con los modelos ya descargados.
- Al **indexar** por lotes, Gemini cuesta lo mismo en tiempo que e5-base local (~113 ms frente a ~124 ms por fragmento
  de 400 tokens). En cada **consulta**, en cambio, tarda ~1,3 s frente a ~36 ms: unas 35 veces más, por la red.
- Los costos de API son muy bajos: indexar 1.000 fragmentos cuesta menos de USD 0,10 con cualquiera de ellos. El
  presupuesto no es un factor decisivo; sí lo son la latencia de consulta, la dependencia de un servicio externo y el
  envío del material docente.
- **Condiciones de uso de Gemini (consultadas el 05/10/2026):** en la capa **gratuita**, Google usa el contenido enviado
  para mejorar sus productos, puede ser leído por revisores humanos y sus términos piden no enviar información
  confidencial o personal. En la capa **de pago** no se usa para mejorar productos. El material de los cursos solo
  debería enviarse a la capa de pago, y con el permiso de uso que ya registra la pantalla de Carga.

## 6. Recomendación (propuesta)

**Usar `intfloat/multilingual-e5-base` (768 dimensiones), ejecutado localmente en el backend.**

Justificación:

1. **Calidad:** MRR de 0,969, a una sola consulta de Gemini (1,000). Con este conjunto de prueba la diferencia
   no es concluyente.
2. **Latencia:** ~36 ms por consulta y ~124 ms por fragmento de 400 tokens en CPU, suficiente para indexación por
   lotes y búsqueda interactiva.
3. **Costo:** sin costo por uso ni claves; libera los créditos de API para el LLM de generación.
4. **Privacidad y dependencia:** el material del docente no sale del servidor para vectorizarse; el sistema puede
   indexar sin conexión a servicios externos y las pruebas no dependen de la red.
5. **Licencia MIT** y modelo ampliamente usado, con soporte en sentence-transformers, ONNX y servidores de inferencia.

Condiciones y alternativas:

- **Límite de 512 tokens:** la segmentación debe producir fragmentos de **≤ 450 tokens** (margen para el prefijo y
  tokens especiales). Si el equipo prefiere fragmentos más largos, la alternativa es **bge-m3** (8.192 tokens), que
  además aporta vectores dispersos para la búsqueda híbrida, a costa de ~3,4 veces más latencia y más memoria.
- **Alternativa de API: `gemini-embedding-2` a 768 dimensiones, en la capa de pago.** Fue el mejor en calidad junto
  con gemini-embedding-001 y es el modelo vigente de Google (001 ya no figura en su página de precios). Admite
  fragmentos de 8.192 tokens. Conviene si el hosting no tiene ~1,5 GB de RAM libres para e5-base o si la prueba con
  material real confirma su ventaja de calidad. Exige conexión y añade ~1,3 s a cada búsqueda.
- **Revisión pendiente:** repetir la prueba con **material real** de una unidad del piloto (≥ 100 fragmentos y ≥ 30
  consultas redactadas por docentes) comparando e5-base y gemini-embedding-2. Si Gemini supera a e5-base por más de
  0,05 de MRR, adoptarlo.

**Dimensión del vector elegida: 768** (`vector(768)` en pgvector, ~3 KB por fragmento en float32). Queda por debajo del
límite de 2.000 dimensiones que pgvector admite para índices HNSW/IVFFlat sobre `vector`, y coincide con las versiones
reducidas de los modelos de API, lo que facilita un cambio de proveedor (que exigiría, de todos modos, reindexar todo).

## 7. Impacto en otras historias

### EN-013 · Vectorizar e indexar

- Columna `embedding vector(768)` en la tabla de fragmentos e índice **HNSW** con `vector_cosine_ops`, combinado con
  el filtro por unidad.
- Prefijos obligatorios: `"passage: "` al vectorizar fragmentos y `"query: "` al vectorizar consultas. Olvidarlos
  degrada la recuperación sin dar error.
- Vectores normalizados (norma 1), de modo que coseno y producto interno coinciden.
- Guardar en cada fragmento el **modelo y la versión** usados (`modelo_embedding`) para poder detectar y reindexar
  cuando cambie el modelo.
- Validar la longitud en tokens antes de vectorizar (rechazar o resegmentar si supera 512) para evitar truncamientos
  silenciosos.
- Caché por hash del texto e indexación incremental (mitigación de costo/latencia del Project Charter).
- **Decisión que se deriva para EN-001:** el modelo se ejecuta de forma natural en Python (sentence-transformers). Si
  el backend no es Python, opciones: un microservicio de embeddings en Python, un servidor de inferencia
  (p. ej. Text Embeddings Inference) o el modelo exportado a ONNX.

### TA-002 · Pruebas unitarias

- Definir una interfaz de codificador (como `CodificadorLocal` del spike) y usar un **doble de prueba** en las pruebas
  unitarias, para no descargar el modelo (~1,1 GB) en cada ejecución.
- Casos mínimos: dimensión = 768; prefijos aplicados según sea fragmento o consulta; vectores normalizados;
  rechazo de fragmentos que superan el límite de tokens; registro de `modelo_embedding`.
- Una **prueba de regresión de recuperación** (más lenta, opcional en CI) que reutilice `dataset.json` y falle si el
  MRR baja de 0,90, para detectar cambios de modelo, de prefijos o de segmentación que empeoren la búsqueda.

## 8. Limitaciones

- Conjunto pequeño y de un solo tema (estructuras de datos), con material ficticio; los resultados son **orientativos**
  y no estadísticamente concluyentes.
- Latencias medidas en un portátil con Apple M1, no en el servidor de despliegue.
- Solo se evaluó la recuperación densa; no se probó la búsqueda léxica, la híbrida ni el reordenamiento.
- OpenAI text-embedding-3-small no se midió (cuenta sin saldo).
- La latencia de Gemini depende de la conexión desde la que se midió; desde el servidor de despliegue puede variar.
- No se comparan motores vectoriales (pgvector frente a Qdrant), que el backlog v3.0 incluía en este spike.
