-- EN-011: extensión vectorial, tabla de fragmentos e índices de búsqueda.
-- Dimensión 768 según SP-001 (docs/spikes/SP-001-modelos-embeddings.md: multilingual-e5-base).
-- La vectorización (rellenar embedding) corresponde a EN-013.

-- migrate:up
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE fragmento (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    documento_id      bigint NOT NULL REFERENCES documento (id) ON DELETE CASCADE,
    -- Unidad y curso se repiten aquí (también se deducen del documento) para filtrar sin JOIN (HU-013).
    unidad_id         bigint NOT NULL REFERENCES unidad (id),
    curso_id          bigint NOT NULL REFERENCES curso (id),
    pagina            integer CHECK (pagina > 0),  -- en PPTX, número de diapositiva
    orden             integer NOT NULL,            -- posición del fragmento dentro del documento
    texto             text NOT NULL,
    -- Nulo hasta que EN-013 vectorice el fragmento.
    embedding         vector(768),
    -- Modelo con el que se generó el embedding, para detectar y reindexar si cambia.
    modelo_embedding  text,
    -- Búsqueda por palabras (HU-012), con el diccionario español de PostgreSQL.
    texto_tsv         tsvector GENERATED ALWAYS AS (to_tsvector('spanish', texto)) STORED,
    creado_en         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (documento_id, orden),
    CONSTRAINT fragmento_embedding_con_modelo
        CHECK ((embedding IS NULL) = (modelo_embedding IS NULL))
);

-- Búsqueda semántica por distancia coseno. HNSW no necesita datos previos (a diferencia de IVFFlat).
CREATE INDEX fragmento_embedding_hnsw ON fragmento
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Filtrado por unidad.
CREATE INDEX fragmento_unidad_idx ON fragmento (unidad_id);

-- Búsqueda por palabras.
CREATE INDEX fragmento_texto_tsv_gin ON fragmento USING gin (texto_tsv);

-- Clave foránea y borrado en cascada desde documento.
CREATE INDEX fragmento_documento_idx ON fragmento (documento_id);

-- migrate:down
DROP TABLE fragmento;
DROP EXTENSION IF EXISTS vector;
