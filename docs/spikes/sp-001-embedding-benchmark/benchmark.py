"""Benchmark de modelos de embeddings para SP-001.

Mide, sobre dataset.json:
  - calidad de recuperación: recall@1, recall@3, recall@5 y MRR (sin filtro y con filtro por unidad);
  - latencia: ms por fragmento al indexar (por lotes) y ms por consulta (una a una);
  - costo estimado por cada 1.000 fragmentos.

Uso:
  python benchmark.py                       # todos los modelos (los de API se omiten si falta su clave)
  python benchmark.py --modelos e5-base bge-m3
  python benchmark.py --tabla               # solo regenera results/summary-table.md con los JSON existentes

Es un experimento aislado: no forma parte del código de producción.
"""

import argparse
import datetime
import json
import os
import platform
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

RAIZ = Path(__file__).resolve().parent
RESULTADOS = RAIZ / "results"

# Tamaño de fragmento de referencia para estimar costos de producción (supuesto: segmentación de 300-500 tokens).
TOKENS_REFERENCIA = 400
# Lote de consultas repetidas para estabilizar la latencia.
RONDAS_CONSULTA = 3

# Precios en USD por millón de tokens de entrada. Verificar en la web del proveedor antes de decidir.
PRECIOS_CONSULTADOS = "2026-10-05"

MODELOS: Dict[str, dict] = {
    "minilm": {
        "nombre": "paraphrase-multilingual-MiniLM-L12-v2 (línea base)",
        "tipo": "local",
        "id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "prefijo_consulta": "",
        "prefijo_fragmento": "",
    },
    "e5-base": {
        "nombre": "multilingual-e5-base",
        "tipo": "local",
        "id": "intfloat/multilingual-e5-base",
        "prefijo_consulta": "query: ",
        "prefijo_fragmento": "passage: ",
    },
    "bge-m3": {
        "nombre": "bge-m3 (denso)",
        "tipo": "local",
        "id": "BAAI/bge-m3",
        "prefijo_consulta": "",
        "prefijo_fragmento": "",
    },
    "openai-3-small": {
        "nombre": "OpenAI text-embedding-3-small",
        "tipo": "openai",
        "id": "text-embedding-3-small",
        "dimension": None,  # 1536 por defecto
        "precio_millon": 0.02,  # igual en modo estándar y por lotes
        "variable_clave": "OPENAI_API_KEY",
    },
    "gemini-001": {
        "nombre": "Google gemini-embedding-001 (768 dim.)",
        "tipo": "gemini",
        "id": "gemini-embedding-001",
        "dimension": 768,  # se reduce de 3072 para entrar en el límite de índice de pgvector (2000)
        "precio_millon": 0.15,  # último precio publicado conocido; ya no figura en la página de precios
        "variable_clave": "GEMINI_API_KEY",
    },
    # Opcional (publicado en abril de 2026): no usa task_type; la tarea va escrita dentro del texto.
    "gemini-2": {
        "nombre": "Google gemini-embedding-2 (768 dim.)",
        "tipo": "gemini",
        "id": "gemini-embedding-2",
        "dimension": 768,
        "prefijo_consulta": "task: search result | query: ",
        "prefijo_fragmento": "title: none | text: ",
        "precio_millon": 0.20,
        "variable_clave": "GEMINI_API_KEY",
    },
}


# ---------------------------------------------------------------------------
# Codificadores
# ---------------------------------------------------------------------------

class CodificadorLocal:
    def __init__(self, cfg: dict, dispositivo: str):
        from sentence_transformers import SentenceTransformer

        inicio = time.perf_counter()
        self.modelo = SentenceTransformer(cfg["id"], device=dispositivo)
        self.carga_s = time.perf_counter() - inicio
        self.cfg = cfg
        self.tokens_usados = 0
        self.tokens_medidos = False

    def contar_tokens(self, textos: List[str]) -> List[int]:
        tok = self.modelo.tokenizer
        return [len(tok(t, add_special_tokens=True)["input_ids"]) for t in textos]

    def limite_tokens(self) -> int:
        return int(self.modelo.max_seq_length)

    def dimension(self) -> int:
        return int(self.modelo.get_sentence_embedding_dimension())

    def fragmentos(self, textos: List[str]) -> np.ndarray:
        textos = [self.cfg["prefijo_fragmento"] + t for t in textos]
        return self.modelo.encode(textos, batch_size=16, normalize_embeddings=True)

    def consulta(self, texto: str) -> np.ndarray:
        return self.modelo.encode([self.cfg["prefijo_consulta"] + texto], normalize_embeddings=True)[0]


def _post_json(url: str, cuerpo: dict, cabeceras: dict) -> dict:
    datos = json.dumps(cuerpo).encode("utf-8")
    peticion = urllib.request.Request(url, data=datos, headers={"Content-Type": "application/json", **cabeceras})
    try:
        with urllib.request.urlopen(peticion, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}") from None


class CodificadorOpenAI:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.clave = os.environ[cfg["variable_clave"]]
        self.carga_s = 0.0
        self.tokens_usados = 0
        self.tokens_medidos = True  # la API devuelve el uso real
        self._dim = None

    def _embed(self, textos: List[str]) -> np.ndarray:
        cuerpo = {"model": self.cfg["id"], "input": textos}
        if self.cfg.get("dimension"):
            cuerpo["dimensions"] = self.cfg["dimension"]
        r = _post_json("https://api.openai.com/v1/embeddings", cuerpo, {"Authorization": f"Bearer {self.clave}"})
        self.tokens_usados += r["usage"]["prompt_tokens"]
        vecs = np.array([d["embedding"] for d in sorted(r["data"], key=lambda d: d["index"])], dtype=np.float32)
        self._dim = vecs.shape[1]
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    def contar_tokens(self, textos: List[str]) -> Optional[List[int]]:
        return None

    def limite_tokens(self) -> int:
        return 8191

    def dimension(self) -> int:
        return self._dim

    def fragmentos(self, textos: List[str]) -> np.ndarray:
        return self._embed(textos)

    def consulta(self, texto: str) -> np.ndarray:
        return self._embed([texto])[0]


class CodificadorGemini:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.clave = os.environ[cfg["variable_clave"]]
        self.carga_s = 0.0
        self.tokens_usados = 0
        self.tokens_medidos = False  # la API de embeddings no informa tokens: se estiman
        self._dim = None

    def _embed(self, textos: List[str], tarea: str) -> np.ndarray:
        modelo = f"models/{self.cfg['id']}"
        peticiones = []
        prefijo = self.cfg.get("prefijo_consulta" if tarea == "RETRIEVAL_QUERY" else "prefijo_fragmento")
        for t in textos:
            if prefijo is None:
                p = {"model": modelo, "content": {"parts": [{"text": t}]}, "taskType": tarea}
            else:
                p = {"model": modelo, "content": {"parts": [{"text": prefijo + t}]}}
            if self.cfg.get("dimension"):
                p["outputDimensionality"] = self.cfg["dimension"]
            peticiones.append(p)
        url = f"https://generativelanguage.googleapis.com/v1beta/{modelo}:batchEmbedContents"
        r = _post_json(url, {"requests": peticiones}, {"x-goog-api-key": self.clave})
        vecs = np.array([e["values"] for e in r["embeddings"]], dtype=np.float32)
        self._dim = vecs.shape[1]
        self.tokens_usados += sum(estimar_tokens(t) for t in textos)
        # Con dimensión reducida los vectores no vienen normalizados.
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

    def contar_tokens(self, textos: List[str]) -> Optional[List[int]]:
        return None

    def limite_tokens(self) -> int:
        return 8192 if self.cfg["id"] == "gemini-embedding-2" else 2048

    def dimension(self) -> int:
        return self._dim

    def fragmentos(self, textos: List[str]) -> np.ndarray:
        return self._embed(textos, "RETRIEVAL_DOCUMENT")

    def consulta(self, texto: str) -> np.ndarray:
        return self._embed([texto], "RETRIEVAL_QUERY")[0]


def estimar_tokens(texto: str) -> int:
    # Aproximación para español: ~4 caracteres por token.
    return max(1, round(len(texto) / 4))


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def posiciones(mat_frag: np.ndarray, mat_cons: np.ndarray, frags: List[dict], consultas: List[dict], filtrar: bool) -> List[int]:
    """Posición (1 = primero) del fragmento relevante para cada consulta, por similitud coseno."""
    ids = [f["id"] for f in frags]
    unidades = np.array([f["unidad"] for f in frags])
    resultado = []
    for i, c in enumerate(consultas):
        sims = mat_frag @ mat_cons[i]
        if filtrar:
            sims = np.where(unidades == c["unidad"], sims, -np.inf)
        orden = np.argsort(-sims)
        resultado.append(int(np.where(orden == ids.index(c["relevante"]))[0][0]) + 1)
    return resultado


def metricas(pos: List[int]) -> dict:
    n = len(pos)
    return {
        "recall@1": sum(p <= 1 for p in pos) / n,
        "recall@3": sum(p <= 3 for p in pos) / n,
        "recall@5": sum(p <= 5 for p in pos) / n,
        "mrr": sum(1 / p for p in pos) / n,
    }


def percentil(valores: List[float], p: float) -> float:
    return float(np.percentile(np.array(valores), p))


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------

def ejecutar(clave: str, cfg: dict, datos: dict, dispositivo: str) -> dict:
    frags = datos["fragmentos"]
    consultas = datos["consultas"]
    textos_frag = [f["texto"] for f in frags]

    if cfg["tipo"] == "local":
        cod = CodificadorLocal(cfg, dispositivo)
        cod.fragmentos(["calentamiento"])  # excluye la inicialización de la medición
        cod.consulta("calentamiento")
    elif cfg["tipo"] == "openai":
        cod = CodificadorOpenAI(cfg)
    else:
        cod = CodificadorGemini(cfg)

    # Indexación: todos los fragmentos por lotes.
    cod.tokens_usados = 0
    inicio = time.perf_counter()
    mat_frag = np.asarray(cod.fragmentos(textos_frag), dtype=np.float32)
    ms_por_fragmento = (time.perf_counter() - inicio) * 1000 / len(frags)
    tokens_indexacion = cod.tokens_usados

    # Indexación con fragmentos del tamaño esperado en producción (~400 tokens), armados concatenando el dataset.
    corpus = " ".join(textos_frag)
    largos = [(corpus[i * 97:] + " " + corpus)[: TOKENS_REFERENCIA * 4] for i in range(16)]
    inicio = time.perf_counter()
    cod.fragmentos(largos)
    ms_por_fragmento_largo = (time.perf_counter() - inicio) * 1000 / len(largos)

    # Consultas: una a una, varias rondas.
    tiempos = []
    mat_cons = None
    for _ in range(RONDAS_CONSULTA):
        vecs = []
        for c in consultas:
            inicio = time.perf_counter()
            vecs.append(cod.consulta(c["texto"]))
            tiempos.append((time.perf_counter() - inicio) * 1000)
        mat_cons = np.asarray(vecs, dtype=np.float32)

    pos_global = posiciones(mat_frag, mat_cons, frags, consultas, filtrar=False)
    pos_unidad = posiciones(mat_frag, mat_cons, frags, consultas, filtrar=True)

    # Tokens por fragmento: tokenizador propio (local), uso real (OpenAI) o estimación (Gemini).
    conteo = cod.contar_tokens(textos_frag)
    if conteo is not None:
        tokens_frag = conteo
        origen_tokens = "tokenizador del modelo"
    elif cod.tokens_medidos:
        tokens_frag = None
        origen_tokens = "uso informado por la API"
    else:
        tokens_frag = [estimar_tokens(t) for t in textos_frag]
        origen_tokens = "estimado (caracteres / 4)"
    prom_tokens = (sum(tokens_frag) / len(tokens_frag)) if tokens_frag else tokens_indexacion / len(frags)

    precio = cfg.get("precio_millon")
    costo = None
    if precio is not None:
        costo = {
            "usd_1000_fragmentos_dataset": round(prom_tokens * 1000 * precio / 1e6, 6),
            "usd_1000_fragmentos_400_tokens": round(TOKENS_REFERENCIA * 1000 * precio / 1e6, 6),
            "precio_usd_millon_tokens": precio,
            "precios_consultados": PRECIOS_CONSULTADOS,
        }

    return {
        "clave": clave,
        "modelo": cfg["nombre"],
        "id": cfg["id"],
        "tipo": cfg["tipo"],
        "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
        "entorno": {
            "plataforma": f"{platform.system()} {platform.machine()}",
            "python": platform.python_version(),
            "dispositivo": dispositivo if cfg["tipo"] == "local" else "API remota",
        },
        "dimension": cod.dimension(),
        "limite_tokens": cod.limite_tokens(),
        "tokens_fragmento": {
            "promedio": round(prom_tokens, 1),
            "maximo": max(tokens_frag) if tokens_frag else None,
            "origen": origen_tokens,
        },
        "n_fragmentos": len(frags),
        "n_consultas": len(consultas),
        "calidad_sin_filtro": metricas(pos_global),
        "calidad_filtro_unidad": metricas(pos_unidad),
        "posiciones_sin_filtro": dict(zip([c["id"] for c in consultas], pos_global)),
        "latencia": {
            "carga_modelo_s": round(cod.carga_s, 2),
            "ms_por_fragmento_indexacion": round(ms_por_fragmento, 2),
            "ms_por_fragmento_400_tokens": round(ms_por_fragmento_largo, 2),
            "ms_por_consulta_promedio": round(statistics.mean(tiempos), 2),
            "ms_por_consulta_p95": round(percentil(tiempos, 95), 2),
            "rondas_consulta": RONDAS_CONSULTA,
        },
        "costo": costo,
    }


def tabla() -> str:
    filas = []
    for ruta in sorted(RESULTADOS.glob("*.json")):
        r = json.loads(ruta.read_text(encoding="utf-8"))
        q, qu, lat = r["calidad_sin_filtro"], r["calidad_filtro_unidad"], r["latencia"]
        if r["costo"]:
            costo = f"{r['costo']['usd_1000_fragmentos_400_tokens']:.4f}"
        else:
            costo = "0 (hardware propio)"
        filas.append(
            f"| {r['modelo']} | {r['dimension']} | {q['recall@1']:.2f} | {q['recall@3']:.2f} | {q['recall@5']:.2f} "
            f"| {q['mrr']:.3f} | {qu['mrr']:.3f} | {lat['ms_por_fragmento_indexacion']:.1f} "
            f"| {lat['ms_por_fragmento_400_tokens']:.1f} "
            f"| {lat['ms_por_consulta_promedio']:.1f} | {lat['ms_por_consulta_p95']:.1f} | {costo} |"
        )
    cabecera = (
        "| Modelo | Dim. | R@1 | R@3 | R@5 | MRR | MRR (filtro unidad) | ms/fragmento (dataset) "
        "| ms/fragmento (~400 tokens) | ms/consulta (prom.) | ms/consulta (p95) | USD / 1.000 fragmentos (400 tokens) |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|"
    )
    return cabecera + "\n" + "\n".join(filas) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelos", nargs="+", choices=list(MODELOS), default=list(MODELOS))
    ap.add_argument("--dispositivo", default="cpu", help="cpu (por defecto, comparable con un servidor sin GPU), mps o cuda")
    ap.add_argument("--tabla", action="store_true", help="solo regenera results/summary-table.md")
    args = ap.parse_args()

    RESULTADOS.mkdir(exist_ok=True)
    if not args.tabla:
        datos = json.loads((RAIZ / "dataset.json").read_text(encoding="utf-8"))
        for clave in args.modelos:
            cfg = MODELOS[clave]
            var = cfg.get("variable_clave")
            if var and not os.environ.get(var):
                print(f"[omitido] {clave}: falta la variable de entorno {var}")
                continue
            print(f"[ejecutando] {clave} ...", flush=True)
            try:
                r = ejecutar(clave, cfg, datos, args.dispositivo)
            except Exception as e:  # noqa: BLE001 — un modelo fallido no detiene a los demás
                print(f"[error] {clave}: {e}", file=sys.stderr)
                continue
            (RESULTADOS / f"{clave}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[listo] {clave}: MRR={r['calidad_sin_filtro']['mrr']:.3f}")

    contenido = tabla()
    (RESULTADOS / "summary-table.md").write_text(contenido, encoding="utf-8")
    print("\n" + contenido)


if __name__ == "__main__":
    main()
