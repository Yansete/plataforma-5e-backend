| Modelo | Dim. | R@1 | R@3 | R@5 | MRR | MRR (filtro unidad) | ms/fragmento (dataset) | ms/fragmento (~400 tokens) | ms/consulta (prom.) | ms/consulta (p95) | USD / 1.000 fragmentos (400 tokens) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bge-m3 (denso) | 1024 | 0.94 | 1.00 | 1.00 | 0.958 | 0.958 | 74.2 | 426.0 | 109.4 | 132.7 | 0 (hardware propio) |
| multilingual-e5-base | 768 | 0.94 | 1.00 | 1.00 | 0.969 | 0.969 | 21.2 | 124.4 | 36.1 | 40.5 | 0 (hardware propio) |
| Google gemini-embedding-001 (768 dim.) | 768 | 1.00 | 1.00 | 1.00 | 1.000 | 1.000 | 217.6 | 113.1 | 1329.0 | 1712.2 | 0.0600 |
| Google gemini-embedding-2 (768 dim.) | 768 | 1.00 | 1.00 | 1.00 | 1.000 | 1.000 | 114.1 | 113.9 | 1285.8 | 1502.3 | 0.0800 |
| paraphrase-multilingual-MiniLM-L12-v2 (línea base) | 384 | 0.81 | 1.00 | 1.00 | 0.906 | 0.906 | 8.3 | 13.9 | 12.4 | 13.6 | 0 (hardware propio) |
