-- Esquema base mínimo: curso, unidad y documento.
-- PROVISIONAL: sustituye a EN-002 (modelo de datos relacional), que aún no existe en el repositorio.
-- Los nombres siguen los modelos propuestos del frontend (frontend/src/types/index.ts). Cuando EN-002 se apruebe,
-- se ajustará con migraciones nuevas, no editando esta.

-- migrate:up
CREATE TABLE curso (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo      text NOT NULL UNIQUE,
    nombre      text NOT NULL
);

CREATE TABLE unidad (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    curso_id    bigint NOT NULL REFERENCES curso (id) ON DELETE CASCADE,
    numero      integer NOT NULL CHECK (numero > 0),
    nombre      text NOT NULL,
    UNIQUE (curso_id, numero)
);

CREATE TABLE documento (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unidad_id       bigint NOT NULL REFERENCES unidad (id) ON DELETE CASCADE,
    nombre_archivo  text NOT NULL,
    tipo            text NOT NULL CHECK (tipo IN ('pdf', 'pptx', 'txt')),
    paginas         integer CHECK (paginas > 0),
    creado_en       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX documento_unidad_idx ON documento (unidad_id);

-- migrate:down
DROP TABLE documento;
DROP TABLE unidad;
DROP TABLE curso;
