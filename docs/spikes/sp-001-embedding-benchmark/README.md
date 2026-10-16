# SP-001 · Benchmark de modelos de embeddings

Experimento aislado (no es código de producción). Resultados y recomendación en
[`docs/spikes/SP-001-embedding-models.md`](../SP-001-embedding-models.md).

## Archivos

- `dataset.json`: 18 fragmentos en español (12 de la demo del frontend + 6 distractores nuevos) y 16 consultas con su fragmento relevante.
- `benchmark.py`: mide recall@1/3/5, MRR (sin filtro y con filtro por unidad), latencia y costo estimado.
- `results/`: un JSON por modelo y `summary-table.md` con el resumen.

## Ejecutar (macOS / Linux, Python ≥ 3.9)

```bash
cd docs/spikes/sp-001-embedding-benchmark
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Modelos locales (la primera vez descarga ~6 GB en ~/.cache/huggingface)
.venv/bin/python benchmark.py --modelos minilm e5-base bge-m3
```

## Modelos de API (requieren clave)

Las claves se definen solo en la terminal; no se guardan en archivos ni en el repositorio.

```bash
export OPENAI_API_KEY="..."   # https://platform.openai.com/api-keys (requiere saldo)
export GEMINI_API_KEY="..."   # https://aistudio.google.com/apikey (tiene capa gratuita)

.venv/bin/python benchmark.py --modelos openai-3-small gemini-001 gemini-2
```

Cada ejecución completa consume unos 2.000 tokens por modelo (menos de USD 0,001).
Los modelos sin clave se omiten. Al terminar se regenera `results/summary-table.md` con todos los JSON existentes;
para regenerarla sin ejecutar nada: `.venv/bin/python benchmark.py --tabla`.

## Notas

- Por defecto se usa la CPU (`--dispositivo cpu`) para que la latencia sea comparable con un servidor sin GPU.
- La latencia de los modelos de API incluye la red; depende de la conexión desde la que se ejecute.
- Los precios están en `MODELOS` dentro de `benchmark.py` con su fecha de consulta.
