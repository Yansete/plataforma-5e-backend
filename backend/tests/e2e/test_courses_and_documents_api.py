"""EP-002: peticiones reales, archivos reales y recuperación con nueva sesión."""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Any

import httpx
import pytest

SOLICITUD = {
    "unidad_id": "u2",
    "resultado_aprendizaje_id": None,
    "etapa_5e": "explore",
    "tipo_recurso": "guia_exploracion",
    "cantidad": 1,
    "dificultad": "intermedia",
    "alternativas": 4,
    "top_k": 10,
    "umbral_evidencia": 0.6,
    "indicaciones": "Contexto de prueba",
    "publico_objetivo": "Tercer ciclo",
    "competencia": "Pensamiento crítico",
    "modalidades": ["Textual"],
}

CREDENCIALES = {"email": "docente@5e.demo", "password": "Demo5E!2026"}
CURSO = {"code": "EP002", "name": "Curso de integración", "term": "2026-II", "units": [{"title": "Unidad conectada"}]}


def login(api: httpx.Client) -> dict[str, str]:
    r = api.post("/api/v1/sesiones", json=CREDENCIALES)
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def contexto(unidad: str = "u2", ra: list[str] | None = None) -> dict[str, Any]:
    return {
        "unitId": unidad,
        "outcomeIds": ["ra-2-1"] if ra is None else ra,
        "documentType": "Guía de práctica",
        "suggestedStage": "explore",
        "usePermission": True,
    }


def upload(
    api: httpx.Client,
    headers: dict[str, str],
    nombre: str = "evidencia.txt",
    contenido: bytes = b"Material docente real",
    datos: dict[str, Any] | None = None,
) -> httpx.Response:
    return api.post(
        "/api/v1/documentos",
        headers=headers,
        files={"file": (nombre, contenido)},
        data={"contexto": json.dumps(datos or contexto())},
    )


def test_login_catalogo_archivo_historial_persisten_con_nueva_sesion(servidor: str):
    with httpx.Client(base_url=servidor) as api:
        h = login(api)
        c = api.post("/api/v1/cursos", headers=h, json=CURSO)
        assert c.status_code == 201, c.text
        curso = c.json()
        unidad = curso["units"][0]
        assert unidad["outcomes"] == []
        editado = api.put(
            "/api/v1/cursos/" + curso["id"],
            headers=h,
            json={
                **CURSO,
                "name": "Curso actualizado",
                "units": [{"id": unidad["id"], "title": "Unidad actualizada"}, {"title": "Segunda unidad"}],
            },
        )
        assert editado.status_code == 200
        assert editado.json()["units"][0]["id"] == unidad["id"]
        doc = upload(api, h, datos=contexto(unidad["id"], []))
        assert doc.status_code == 201, doc.text
        documento = doc.json()
        assert documento["source"] == "backend" and documento["fragmentCount"] == 0
        assert documento["status"] == "registrado" and documento["processedAt"] is None
        archivo = api.get("/api/v1/documentos/" + documento["id"] + "/archivo", headers=h)
        assert archivo.content == b"Material docente real"
        generacion = api.post("/api/v1/generaciones", headers=h, json=SOLICITUD)
        assert generacion.status_code == 200, generacion.text
        req = generacion.json()["request"]
        assert api.get("/api/v1/solicitudes", headers=h).json() == [req]
        assert api.get("/api/v1/generaciones/" + req["id"]).status_code == 401
        assert api.delete("/api/v1/sesiones/actual", headers=h).status_code == 204
        assert api.get("/api/v1/cursos", headers=h).status_code == 401
        h2 = login(api)
        assert any(c["name"] == "Curso actualizado" for c in api.get("/api/v1/cursos", headers=h2).json())
        assert api.get("/api/v1/documentos", headers=h2).json() == [documento]
        assert api.get("/api/v1/solicitudes", headers=h2).json() == [req]
        assert api.get("/api/v1/generaciones/" + req["id"], headers=h2).json()["request"] == req
        assert api.delete("/api/v1/documentos/" + documento["id"], headers=h2).status_code == 204
        assert api.get("/api/v1/documentos/" + documento["id"] + "/archivo", headers=h2).status_code == 404


@pytest.mark.parametrize(
    "ruta",
    ["/api/v1/cursos", "/api/v1/documentos", "/api/v1/solicitudes", "/api/v1/sesiones/actual"],
)
def test_rutas_privadas_requieren_sesion(servidor: str, ruta: str):
    assert httpx.get(servidor + ruta).status_code == 401
    assert httpx.get(servidor + ruta, headers={"Authorization": "Bearer inventado"}).status_code == 401


def test_validaciones_del_servidor_no_guardan_datos_invalidos(servidor: str):
    with httpx.Client(base_url=servidor) as api:
        assert api.post("/api/v1/sesiones", json={**CREDENCIALES, "password": "incorrecta"}).status_code == 401
        h = login(api)
        assert api.post("/api/v1/cursos", headers=h, json=CURSO).status_code == 201
        assert api.post("/api/v1/cursos", headers=h, json={**CURSO, "code": "ep002"}).status_code == 409
        assert api.post("/api/v1/cursos", headers=h, json={**CURSO, "units": [{"title": "   "}]}).status_code == 422
        assert upload(api, h, datos=contexto("unidad-ajena")).status_code == 404
        assert upload(api, h, datos=contexto(ra=["ra-3-1"])).status_code == 400
        assert upload(api, h, datos={**contexto(), "usePermission": False}).status_code == 400
        for nombre, contenido in [
            ("falso.pdf", b"no pdf"),
            ("falso.pptx", b"PK mentira"),
            ("vacio.txt", b""),
            ("binario.txt", b"\xff"),
            ("../ruta.txt", b"contenido"),
            ("script.exe", b"contenido"),
        ]:
            assert upload(api, h, nombre, contenido).status_code == 400
        assert upload(api, h).status_code == 201
        assert upload(api, h).status_code == 409
        assert len(api.get("/api/v1/documentos", headers=h).json()) == 1
        assert (
            api.post("/api/v1/generaciones", headers=h, json={**SOLICITUD, "unidad_id": "unidad-ajena"}).status_code
            == 404
        )
        assert api.get("/api/v1/solicitudes", headers=h).json() == []


def test_archivo_excede_limite_y_no_se_guarda(servidor: str):
    with httpx.Client(base_url=servidor, timeout=30) as api:
        h = login(api)
        r = upload(api, h, contenido=b"x" * (25 * 1024 * 1024 + 1))
        assert r.status_code == 400
        assert r.json()["error"]["codigo"] == "TAMANO_INVALIDO"
        assert api.get("/api/v1/documentos", headers=h).json() == []


def test_catalogo_sesion_archivo_historial_sobreviven_reinicio(tmp_path: Path):
    """Dos procesos distintos utilizan el mismo archivo SQLite, sin caché de aplicación."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    base = f"http://127.0.0.1:{puerto}"
    src_dir = str(Path(__file__).resolve().parents[2] / "src")
    existing_pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = f"{src_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else src_dir
    env = {
        **os.environ,
        "PYTHONPATH": pythonpath,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'persistente.db'}",
        "CATALOGO_DEMO": "true",
    }
    headers = None
    doc_id = None
    req_id = None
    for intento in range(2):
        with (tmp_path / f"servidor{intento}.log").open("w", encoding="utf-8") as log:
            proceso = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "platform5e.main:create_application",
                    "--factory",
                    "--app-dir",
                    src_dir,
                    "--port",
                    str(puerto),
                ],
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                for _ in range(100):
                    try:
                        if httpx.get(base + "/salud", timeout=0.5).status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if proceso.poll() is not None:
                        pytest.fail("No arrancó el servidor persistente.")
                    time.sleep(0.1)
                else:
                    pytest.fail("El servidor persistente no respondió.")
                with httpx.Client(base_url=base) as api:
                    if intento == 0:
                        headers = login(api)
                        assert api.post("/api/v1/cursos", headers=headers, json=CURSO).status_code == 201
                        doc_id = upload(api, headers).json()["id"]
                        req_id = api.post("/api/v1/generaciones", headers=headers, json=SOLICITUD).json()["request"]["id"]
                    else:
                        assert api.get("/api/v1/sesiones/actual", headers=headers).status_code == 200
                        assert any(c["code"] == "EP002" for c in api.get("/api/v1/cursos", headers=headers).json())
                        assert (
                            api.get("/api/v1/documentos/" + doc_id + "/archivo", headers=headers).content
                            == b"Material docente real"
                        )
                        assert api.get("/api/v1/solicitudes", headers=headers).json()[0]["id"] == req_id
            finally:
                proceso.terminate()
                proceso.wait(timeout=10)


def test_openapi_declara_bearer_para_swagger(servidor: str):
    spec = httpx.get(servidor + "/openapi.json").json()
    assert spec["components"]["securitySchemes"]["SesionDocente"]["type"] == "http"
    assert spec["components"]["securitySchemes"]["SesionDocente"]["scheme"] == "bearer"
    for ruta, metodo in [
        ("/api/v1/solicitudes", "get"),
        ("/api/v1/cursos", "get"),
        ("/api/v1/documentos", "post"),
        ("/api/v1/sesiones/actual", "delete"),
        ("/api/v1/generaciones", "post"),
    ]:
        operacion = spec["paths"][ruta][metodo]
        assert {"SesionDocente": []} in operacion["security"]
        assert not any(
            p["in"] == "header" and p["name"].lower() == "authorization" for p in operacion.get("parameters", [])
        )
    assert "security" not in spec["paths"]["/api/v1/sesiones"]["post"]
    with httpx.Client(base_url=servidor) as api:
        h = login(api)
        assert api.get("/api/v1/solicitudes", headers=h).status_code == 200
        assert api.get("/api/v1/solicitudes", headers={"Authorization": "Basic incorrecto"}).status_code == 401
        assert (
            api.post(
                "/api/v1/generaciones",
                headers={"Authorization": "Basic incorrecto"},
                json=SOLICITUD,
            ).status_code
            == 401
        )