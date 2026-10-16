"""Servidor real para las pruebas de punta a punta (TA-007).

Levanta uvicorn en un subproceso independiente y ejecuta llamadas HTTP reales.
"""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _vaciar_postgres(url: str) -> None:
    """Deja la base de PostgreSQL sin tablas para que cada servidor arranque limpio."""
    from sqlalchemy import create_engine, text

    motor = create_engine(url)
    with motor.begin() as conexion:
        conexion.execute(text("DROP SCHEMA public CASCADE"))
        conexion.execute(text("CREATE SCHEMA public"))
    motor.dispose()


@pytest.fixture
def servidor(tmp_path: Path) -> Iterator[str]:
    """Levanta la API en un puerto libre y devuelve su URL base. Se apaga al terminar."""
    url_bd = os.getenv("E2E_DATABASE_URL")
    if url_bd:
        _vaciar_postgres(url_bd)
    else:
        url_bd = f"sqlite:///{tmp_path / 'e2e.db'}"

    puerto = _puerto_libre()
    src_dir = str(RAIZ_BACKEND / "src")
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = f"{src_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_dir

    entorno = {
        **os.environ,
        "PYTHONPATH": pythonpath,
        "DATABASE_URL": url_bd,
        "CARGAR_DATOS_DEMO": "true",
        "CATALOGO_DEMO": "true",
        "IA_PROVEEDOR": "reglas",
        "BUSQUEDA_POR_TEMA": "false",
    }
    registro = (tmp_path / "uvicorn.log").open("w", encoding="utf-8")

    proceso = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "platform5e.main:create_application",
            "--factory",
            "--app-dir",
            src_dir,
            "--host",
            "127.0.0.1",
            "--port",
            str(puerto),
        ],
        cwd=RAIZ_BACKEND,
        env=entorno,
        stdout=registro,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{puerto}"
    try:
        limite = time.monotonic() + 30
        while True:
            if proceso.poll() is not None:
                registro.flush()
                registro.close()
                error_log = (tmp_path / "uvicorn.log").read_text(encoding="utf-8", errors="replace")
                pytest.fail("El servidor terminó al arrancar:\n" + error_log)
            try:
                if httpx.get(f"{base}/salud", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if time.monotonic() > limite:
                registro.flush()
                registro.close()
                error_log = (tmp_path / "uvicorn.log").read_text(encoding="utf-8", errors="replace")
                pytest.fail("El servidor no respondió en 30 s:\n" + error_log)
            time.sleep(0.2)
        yield base
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
        if not registro.closed:
            registro.close()