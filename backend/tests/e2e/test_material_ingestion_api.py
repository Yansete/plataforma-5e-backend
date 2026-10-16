"""Recorrido real por HTTP: curso con sumilla y resultados, material procesado y generación con evidencia (RAG)."""

from __future__ import annotations

import json

import httpx

CREDENTIALS = {"email": "docente@5e.demo", "password": "Demo5E!2026"}

MATERIAL = (
    "Unidad 1: Protocolos de transporte\n\n"
    "El protocolo TCP es orientado a la conexión: establece la conexión con un saludo de tres vías y garantiza una entrega confiable. "
    "El protocolo UDP no establece conexión ni confirma la entrega; por eso es más rápido y se usa en videollamadas.\n\n"
    "El protocolo IP se encarga del direccionamiento y del enrutamiento de los paquetes. "
    "El enrutador es el dispositivo que decide por qué camino viaja cada paquete hasta llegar a su destino. "
    "La encapsulación es el proceso por el cual cada capa agrega su propio encabezado a los datos."
).encode()


def test_real_material_is_processed_and_generates_cited_resources(server: str):
    with httpx.Client(base_url=server, timeout=30) as api:
        h = {"Authorization": "Bearer " + api.post("/api/v1/sesiones", json=CREDENTIALS).json()["token"]}
        assert api.get("/api/v1/ia").json()["usaIA"] is False
        course = api.post(
            "/api/v1/cursos",
            headers=h,
            json={
                "code": "RED-E2E",
                "name": "Redes",
                "term": "2026-II",
                "sumilla": "Curso de redes de computadoras.",
                "logro": "Explica cómo se comunican los equipos.",
                "units": [{"title": "Protocolos de transporte", "outcomes": [{"text": "Distingue TCP y UDP"}]}],
            },
        )
        assert course.status_code == 201, course.text
        unit = course.json()["units"][0]
        assert course.json()["sumilla"] == "Curso de redes de computadoras." and unit["outcomes"][0]["code"] == "RA1.1"

        context = {
            "unitId": unit["id"],
            "outcomeIds": [unit["outcomes"][0]["id"]],
            "documentType": "Separata o apuntes de clase",
            "suggestedStage": None,
            "usePermission": True,
        }
        uploaded = api.post(
            "/api/v1/documentos",
            headers=h,
            files={"file": ("protocolos.txt", MATERIAL)},
            data={"contexto": json.dumps(context)},
        )
        assert uploaded.status_code == 201 and uploaded.json()["status"] == "registrado"
        processed = api.post(f"/api/v1/documentos/{uploaded.json()['id']}/procesar", headers=h)
        assert processed.status_code == 200, processed.text
        assert processed.json()["status"] == "procesado" and processed.json()["fragmentCount"] >= 1
        chunks = api.get(f"/api/v1/documentos/{uploaded.json()['id']}/fragmentos", headers=h).json()
        assert chunks[0]["location"] == "sección 1" and "protocolo TCP" in " ".join(f["text"] for f in chunks)

        request_body = {
            "unidad_id": unit["id"],
            "resultado_aprendizaje_id": None,
            "etapa_5e": "evaluate",
            "tipo_recurso": "item_opcion_multiple",
            "cantidad": 2,
            "dificultad": "intermedia",
            "alternativas": 4,
            "top_k": 8,
            "umbral_evidencia": 0.6,
            "indicaciones": "",
            "publico_objetivo": "Tercer ciclo",
            "competencia": "Pensamiento crítico",
            "modalidades": ["Textual"],
        }
        response = api.post("/api/v1/generaciones", headers=h, json=request_body)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["mode"] == "rag" and data["generator"]["usaIA"] is False
        ids = {f["id"] for f in data["fragments"]}
        # Lo recuperado incluye todo lo citado (la evaluación con Ragas lo usa como contexto).
        retrieved = {f["id"] for f in data["retrievedChunks"]}
        assert ids and ids <= retrieved and all(f["text"] for f in data["retrievedChunks"])
        for resource in data["resources"]:
            assert resource["source"] == "rag" and resource["status"] == "pendiente"
            assert all(set(c["fragmentIds"]) <= ids for c in resource["citations"])
            assert len(resource["options"]) == 4 and sum(o["isCorrect"] for o in resource["options"]) == 1
        assert api.get(f"/api/v1/generaciones/{data['request']['id']}", headers=h).json()["mode"] == "rag"

        explanation = api.post(
            "/api/v1/generaciones",
            headers=h,
            json={**request_body, "etapa_5e": "explain", "tipo_recurso": "explicacion", "cantidad": 1},
        )
        assert explanation.status_code == 200 and explanation.json()["resources"][0]["options"] is None

        assert api.delete(f"/api/v1/documentos/{uploaded.json()['id']}", headers=h).status_code == 204
        without_material = api.post("/api/v1/generaciones", headers=h, json=request_body)
        assert without_material.status_code == 400 and without_material.json()["error"]["codigo"] == "SIN_MATERIAL_PROCESADO"


def test_material_routes_validate_session_and_data(server: str):
    with httpx.Client(base_url=server, timeout=30) as api:
        assert api.post("/api/v1/documentos/x/procesar").status_code == 401
        h = {"Authorization": "Bearer " + api.post("/api/v1/sesiones", json=CREDENTIALS).json()["token"]}
        assert (
            api.post("/api/v1/documentos/no-existe/procesar", headers=h).json()["error"]["codigo"]
            == "DOCUMENTO_NO_ENCONTRADO"
        )
        assert api.post("/api/v1/documentos/desde-tema", headers=h, json={"unitId": "u1", "tema": "ab"}).status_code == 422
        disabled_search = api.post("/api/v1/documentos/desde-tema", headers=h, json={"unitId": "u2", "tema": "redes"})
        assert disabled_search.status_code == 503 and disabled_search.json()["error"]["codigo"] == "BUSQUEDA_NO_DISPONIBLE"