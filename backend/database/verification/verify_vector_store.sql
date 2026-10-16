-- Verificación de EN-011 (C01: extensión instalada y probada; C02: el índice responde consultas de prueba).
-- Se ejecuta dentro de una transacción que termina en ROLLBACK: no deja datos en la base.
-- Uso recomendado: ./database/verification/verify.sh, que lo ejecuta en una base temporal recién migrada.
-- (Ejecutarlo muchas veces sobre la misma base acumula entradas muertas en el índice HNSW, y el planificador
-- puede dejar de elegirlo hasta un REINDEX.) Cualquier comprobación fallida detiene el script con un error.

\set ON_ERROR_STOP on
\pset footer off

BEGIN;

-- ---------------------------------------------------------------------------
-- C01 · Extensión instalada y operativa
-- ---------------------------------------------------------------------------
DO $$
DECLARE
    version_vector text;
BEGIN
    SELECT extversion INTO version_vector FROM pg_extension WHERE extname = 'vector';
    IF version_vector IS NULL THEN
        RAISE EXCEPTION 'C01: la extensión vector no está instalada';
    END IF;
    RAISE NOTICE 'C01 · pgvector instalado, versión %', version_vector;

    IF ('[1,0]'::vector <=> '[0,1]'::vector) <> 1 THEN
        RAISE EXCEPTION 'C01: la distancia coseno entre vectores ortogonales debería ser 1';
    END IF;
    IF ('[1,2]'::vector <=> '[2,4]'::vector) > 1e-6 THEN
        RAISE EXCEPTION 'C01: la distancia coseno entre vectores paralelos debería ser 0';
    END IF;
    RAISE NOTICE 'C01 · operador de distancia coseno (<=>) correcto';

    BEGIN
        PERFORM '[1,2,3]'::vector(768);
        RAISE EXCEPTION 'C01: vector(768) aceptó un vector de 3 dimensiones';
    EXCEPTION WHEN data_exception THEN
        RAISE NOTICE 'C01 · vector(768) rechaza dimensiones distintas: %', SQLERRM;
    END;
END
$$;

-- ---------------------------------------------------------------------------
-- Datos de prueba: 1 curso, 4 unidades, 1 documento por unidad, 4.000 fragmentos con vectores aleatorios
-- ---------------------------------------------------------------------------
INSERT INTO curso (codigo, nombre) VALUES ('PRUEBA-EN011', 'Curso de prueba EN-011');

INSERT INTO unidad (curso_id, numero, nombre)
SELECT c.id, n, 'Unidad de prueba ' || n
FROM curso c, generate_series(1, 4) AS n
WHERE c.codigo = 'PRUEBA-EN011';

INSERT INTO documento (unidad_id, nombre_archivo, tipo, paginas)
SELECT u.id, 'prueba-unidad-' || u.numero || '.pdf', 'pdf', 50
FROM unidad u JOIN curso c ON c.id = u.curso_id
WHERE c.codigo = 'PRUEBA-EN011';

-- Componentes uniformes en [-0,5; 0,5]. La referencia a g en la subconsulta obliga a generar un vector por fila.
INSERT INTO fragmento (documento_id, unidad_id, curso_id, pagina, orden, texto, embedding, modelo_embedding)
SELECT d.id, u.id, u.curso_id, 1 + g % 50, g, 'Fragmento de ruido ' || g,
       (SELECT array_agg(random() - 0.5) FROM generate_series(1, 768) WHERE g > 0)::vector(768),
       'prueba-aleatorio'
FROM generate_series(1, 4000) AS g
JOIN unidad u ON u.numero = 1 + g % 4
JOIN curso c ON c.id = u.curso_id AND c.codigo = 'PRUEBA-EN011'
JOIN documento d ON d.unidad_id = u.id;

-- Vectores conocidos: consulta q y fragmentos cercanos (q + ruido · escala).
-- Unidad 1: escalas 0,1 / 0,3 / 0,6 (deben salir 1.º, 2.º, 3.º).
-- Unidad 2: escala 0,05, más cercano que todos, pero debe quedar fuera al filtrar por la unidad 1.
CREATE TEMP TABLE consulta_prueba ON COMMIT DROP AS
SELECT (SELECT array_agg(random() - 0.5) FROM generate_series(1, 768))::vector(768) AS q;

INSERT INTO fragmento (documento_id, unidad_id, curso_id, pagina, orden, texto, embedding, modelo_embedding)
SELECT d.id, u.id, u.curso_id, 1, 10000 + p.orden, p.texto,
       (SELECT array_agg(qv.c + p.escala * (random() - 0.5))
          FROM unnest((SELECT q::real[] FROM consulta_prueba)) AS qv(c))::vector(768),
       'prueba-plantado'
FROM (VALUES (1, 1, 0.10, 'PLANTADO-A1'),
             (1, 2, 0.30, 'PLANTADO-A2'),
             (1, 3, 0.60, 'PLANTADO-A3'),
             (2, 4, 0.05, 'PLANTADO-B1')) AS p(numero_unidad, orden, escala, texto)
JOIN unidad u ON u.numero = p.numero_unidad
JOIN curso c ON c.id = u.curso_id AND c.codigo = 'PRUEBA-EN011'
JOIN documento d ON d.unidad_id = u.id;

-- Fragmento para la búsqueda por palabras.
INSERT INTO fragmento (documento_id, unidad_id, curso_id, pagina, orden, texto)
SELECT d.id, u.id, u.curso_id, 3, 20000, 'Las pilas siguen la política LIFO: el último en entrar es el primero en salir.'
FROM unidad u
JOIN curso c ON c.id = u.curso_id AND c.codigo = 'PRUEBA-EN011'
JOIN documento d ON d.unidad_id = u.id
WHERE u.numero = 1;

ANALYZE fragmento;

SELECT count(*) AS fragmentos_de_prueba,
       count(embedding) AS con_embedding,
       count(DISTINCT unidad_id) AS unidades
FROM fragmento;

-- ---------------------------------------------------------------------------
-- C02 · Consulta top-k por similitud filtrada por unidad
-- ---------------------------------------------------------------------------
-- pgvector ≥ 0.8: si el filtro descarta candidatos, el índice sigue buscando hasta completar el LIMIT.
SET LOCAL hnsw.iterative_scan = relaxed_order;

-- Funciones auxiliares temporales (desaparecen con el ROLLBACK).
CREATE FUNCTION pg_temp.plan_de(consulta text) RETURNS text LANGUAGE plpgsql AS $f$
DECLARE
    plan text := '';
    fila record;
BEGIN
    FOR fila IN EXECUTE 'EXPLAIN (COSTS OFF) ' || consulta LOOP
        plan := plan || E'\n    ' || fila."QUERY PLAN";
    END LOOP;
    -- El vector literal tiene 768 valores: se abrevia para que el plan sea legible.
    RETURN regexp_replace(plan, '''\[[^]]*\]''', '''[q: 768 valores]''', 'g');
END
$f$;

CREATE FUNCTION pg_temp.textos_de(consulta text) RETURNS text[] LANGUAGE plpgsql AS $f$
DECLARE
    resultado text[];
BEGIN
    EXECUTE 'SELECT array_agg(texto) FROM (' || consulta || ') r' INTO resultado;
    RETURN resultado;
END
$f$;

\echo
\echo 'C02 · Top-5 de la unidad 1 por distancia coseno:'
SELECT f.texto, u.numero AS unidad, round((f.embedding <=> cp.q)::numeric, 4) AS distancia
FROM fragmento f
JOIN unidad u ON u.id = f.unidad_id
CROSS JOIN consulta_prueba cp
WHERE f.unidad_id = (SELECT u1.id FROM unidad u1 JOIN curso c ON c.id = u1.curso_id
                     WHERE c.codigo = 'PRUEBA-EN011' AND u1.numero = 1)
ORDER BY f.embedding <=> cp.q
LIMIT 5;

DO $$
DECLARE
    q                 vector(768);
    unidad_a          bigint;
    consulta_unidad   text;
    consulta_global   text;
    plan              text;
    top_natural       text[];
    top_global        text[];
    top_hnsw          text[];
    top_exacto        text[];
    comunes           integer;
    esperado_unidad   text[] := ARRAY['PLANTADO-A1', 'PLANTADO-A2', 'PLANTADO-A3'];
BEGIN
    SELECT cp.q INTO q FROM consulta_prueba cp;
    SELECT u.id INTO unidad_a FROM unidad u JOIN curso c ON c.id = u.curso_id
    WHERE c.codigo = 'PRUEBA-EN011' AND u.numero = 1;

    -- Consultas como las hará el backend, con valores literales para poder inspeccionar el plan.
    consulta_unidad := format(
        'SELECT texto FROM fragmento WHERE unidad_id = %s ORDER BY embedding <=> %L::vector(768) LIMIT 10',
        unidad_a, q::text);
    consulta_global := format(
        'SELECT texto FROM fragmento ORDER BY embedding <=> %L::vector(768) LIMIT 10', q::text);

    -- 1) Consulta filtrada por unidad con el plan que elige PostgreSQL.
    plan := pg_temp.plan_de(consulta_unidad);
    RAISE NOTICE 'C02.1 · Consulta filtrada por unidad, plan elegido por PostgreSQL:%', plan;
    IF position('fragmento_embedding_hnsw' IN plan) > 0 THEN
        RAISE NOTICE 'C02.1 · El planificador usa el índice HNSW';
    ELSE
        RAISE NOTICE 'C02.1 · El planificador prefiere filtrar por unidad y ordenar de forma exacta '
                     '(más barato con ~1.000 fragmentos por unidad)';
    END IF;
    top_natural := pg_temp.textos_de(consulta_unidad);
    IF top_natural[1:3] <> esperado_unidad OR 'PLANTADO-B1' = ANY (top_natural) THEN
        RAISE EXCEPTION 'C02.1: resultado inesperado: %', top_natural;
    END IF;
    RAISE NOTICE 'C02.1 · Top-3 correcto (%), sin fragmentos de otras unidades', array_to_string(top_natural[1:3], ', ');

    -- 2) Consulta sin filtro: debe usar el índice HNSW por sí sola.
    plan := pg_temp.plan_de(consulta_global);
    RAISE NOTICE 'C02.2 · Consulta sin filtro (todo el curso), plan:%', plan;
    IF position('fragmento_embedding_hnsw' IN plan) = 0 THEN
        RAISE EXCEPTION 'C02.2: la consulta sin filtro no usa el índice fragmento_embedding_hnsw';
    END IF;
    top_global := pg_temp.textos_de(consulta_global);
    IF top_global[1:4] <> ARRAY['PLANTADO-B1', 'PLANTADO-A1', 'PLANTADO-A2', 'PLANTADO-A3'] THEN
        RAISE EXCEPTION 'C02.2: top-4 inesperado: %', top_global[1:4];
    END IF;
    RAISE NOTICE 'C02.2 · Usa fragmento_embedding_hnsw y devuelve el top-4 esperado (%)', array_to_string(top_global[1:4], ', ');

    -- 3) Consulta filtrada obligando a usar el índice HNSW (sin ordenación explícita, el orden solo puede venir
    --    del índice). Comprueba que el índice responde con el filtro gracias al iterative scan.
    PERFORM set_config('enable_sort', 'off', true);
    plan := pg_temp.plan_de(consulta_unidad);
    top_hnsw := pg_temp.textos_de(consulta_unidad);
    PERFORM set_config('enable_sort', 'on', true);
    RAISE NOTICE 'C02.3 · Consulta filtrada con el índice HNSW forzado (enable_sort = off), plan:%', plan;
    IF position('fragmento_embedding_hnsw' IN plan) = 0 THEN
        RAISE EXCEPTION 'C02.3: no se pudo usar el índice HNSW con el filtro por unidad';
    END IF;
    IF top_hnsw[1:3] <> esperado_unidad OR 'PLANTADO-B1' = ANY (top_hnsw) THEN
        RAISE EXCEPTION 'C02.3: resultado inesperado con el índice HNSW: %', top_hnsw;
    END IF;
    IF coalesce(array_length(top_hnsw, 1), 0) <> 10 THEN
        RAISE EXCEPTION 'C02.3: el índice devolvió % filas en lugar de 10', coalesce(array_length(top_hnsw, 1), 0);
    END IF;

    -- 4) Comparación con la búsqueda exacta (enable_indexscan = off impide usar HNSW).
    PERFORM set_config('enable_indexscan', 'off', true);
    top_exacto := pg_temp.textos_de(consulta_unidad);
    PERFORM set_config('enable_indexscan', 'on', true);
    SELECT count(*) INTO comunes FROM unnest(top_hnsw) t WHERE t = ANY (top_exacto);
    IF top_exacto[1:3] <> top_hnsw[1:3] THEN
        RAISE EXCEPTION 'C02.3: el top-3 del índice (%) difiere de la búsqueda exacta (%)', top_hnsw[1:3], top_exacto[1:3];
    END IF;
    RAISE NOTICE 'C02.3 · Con el índice HNSW y el filtro: 10 filas, top-3 correcto e igual a la búsqueda exacta; '
                 'recall@10 frente a la exacta: %/10 (los puestos 4-10 son vectores aleatorios casi equidistantes)', comunes;
END
$$;

-- ---------------------------------------------------------------------------
-- Preparación de HU-012 · Búsqueda por palabras en español
-- ---------------------------------------------------------------------------
\echo
\echo 'HU-012 · Fragmentos que contienen «pila» (con stemming en español):'
SELECT texto, texto_tsv FROM fragmento WHERE texto_tsv @@ plainto_tsquery('spanish', 'pila');

DO $$
DECLARE
    plan text := '';
    n    integer;
BEGIN
    SELECT count(*) INTO n FROM fragmento WHERE texto_tsv @@ plainto_tsquery('spanish', 'pila');
    IF n <> 1 THEN
        RAISE EXCEPTION 'HU-012: se esperaba 1 fragmento con «pila» y se obtuvieron %', n;
    END IF;
    RAISE NOTICE 'HU-012 · «pila» encuentra «pilas» (stemming español)';

    -- Plan elegido por PostgreSQL: con una tabla pequeña puede preferir leerla entera.
    plan := pg_temp.plan_de($q$SELECT id FROM fragmento WHERE texto_tsv @@ plainto_tsquery('spanish', 'pila')$q$);
    RAISE NOTICE 'HU-012 · Plan elegido por PostgreSQL:%', plan;

    -- Disponibilidad del índice GIN (sin lectura secuencial).
    PERFORM set_config('enable_seqscan', 'off', true);
    plan := pg_temp.plan_de($q$SELECT id FROM fragmento WHERE texto_tsv @@ plainto_tsquery('spanish', 'pila')$q$);
    SELECT count(*) INTO n FROM fragmento WHERE texto_tsv @@ plainto_tsquery('spanish', 'pila');
    PERFORM set_config('enable_seqscan', 'on', true);
    RAISE NOTICE 'HU-012 · Plan sin lectura secuencial (enable_seqscan = off):%', plan;
    IF position('fragmento_texto_tsv_gin' IN plan) = 0 OR n <> 1 THEN
        RAISE EXCEPTION 'HU-012: el índice fragmento_texto_tsv_gin no responde la búsqueda por palabras';
    END IF;
    RAISE NOTICE 'HU-012 · El índice fragmento_texto_tsv_gin responde la búsqueda (1 fragmento)';
END
$$;

\echo
\echo 'VERIFICACIÓN EN-011 SUPERADA'
ROLLBACK;
