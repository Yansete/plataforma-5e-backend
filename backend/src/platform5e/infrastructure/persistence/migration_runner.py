"""Runner nativo para aplicar migraciones SQL en backend/database/migrations."""
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.engine import Engine


def apply_database_migrations(engine: Engine) -> None:
    """Aplica archivos .sql pendientes de la carpeta migrations de forma determinista."""
    # Localizar la carpeta database/migrations
    current_path = Path(__file__).resolve()
    # Buscar subiendo hasta la raíz del backend
    backend_root = None
    for parent in current_path.parents:
        if (parent / "database" / "migrations").is_dir():
            backend_root = parent
            break

    if not backend_root:
        return

    migrations_dir = backend_root / "database" / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        return

    with engine.begin() as conn:
        # Tabla para registrar migraciones aplicadas (compatible con formato dbmate)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY
                );
                """
            )
        )
        applied = {
            row[0]
            for row in conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
        }

        for file_path in migration_files:
            # El version es el prefijo timestamp del archivo, ej: 20261029000001
            version = file_path.name.split("_")[0]
            if version in applied:
                continue

            content = file_path.read_text(encoding="utf-8")
            # Extraer solo la sección de migración ascendente si usa directivas dbmate
            if "-- migrate:up" in content:
                content = content.split("-- migrate:up")[1]
                if "-- migrate:down" in content:
                    content = content.split("-- migrate:down")[0]

            # Ejecutar el script SQL de la migración
            # Dividir por sentencias evitando fallos en bloques anónimos simples
            conn.execute(text(content))
            conn.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:v)"),
                {"v": version},
            )