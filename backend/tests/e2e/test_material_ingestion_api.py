"""Recorrido real por HTTP: curso con sumilla y resultados, material procesado y generación con evidencia (RAG)."""

from __future__ import annotations

import json

import httpx

CREDENCIALES = {"email": "docente@5e.demo", "password": "Demo5E!2026"}

MATERIAL = (
    "Unidad 1: Protocolos de transporte\n\n"
    "El protocolo TCP es orientado a la conexión: establece la conexión con un saludo de tres vías y garantiza una entrega confiable. "
    "El protocolo UDP no establece conexión ni confirma la entrega; por eso es más rápido y se usa en videollamadas.\n\n"
    "El protocolo IP se encarga del direccionamiento y del enrutamiento de los paquetes. "
    "El enrutador es el dispositivo que decide por qué camino viaja cada paquete hasta llegar a su destino. "
    "La encapsulación es el proceso por el cual cada capa agrega su propio encabezado a los datos."
).encode()


def test_material_real_se_procesa_y_genera_recursos_citados(servidor: str):
    with httpx.Client(base_url=servidor, timeout=30) as api:
        h = {"Authorization": "Bearer " + api.post("/api/v1/sesiones", json=CREDENCIALES).json()["token"]}
        assert api.get("/api/v1/ia").json()["usaIA"] is False
        curso = api.post(
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
        assert curso.status_code == 201, curso.text
        unidad = curso.json()["units"][0]
        assert curso.json()["sumilla"] == "Curso de redes de computadoras." and unidad["outcomes"][0]["code"] == "RA1.1"

        contexto = {
            "unitId": unidad["id"],
            "outcomeIds": [unidad["outcomes"][0]["id"]],
            "documentType": "Separata o apuntes de clase",
            "suggestedStage": None,
            "usePermission": True,
        }
        subido = api.post(
            "/api/v1/documentos",
            headers=h,
            files={"file": ("protocolos.txt", MATERIAL)},
            data={"contexto": json.dumps(contexto)},
        )
        assert subido.status_code == 201 and subido.json()["status"] == "registrado"
        procesado = api.post(f"/api/v1/documentos/{subido.json()['id']}/procesar", headers=h)
        assert procesado.status_code == 200, procesado.text
        assert procesado.json()["status"] == "procesado" and procesado.json()["fragmentCount"] >= 1
        fragmentos = api.get(f"/api/v1/documentos/{subido.json()['id']}/fragmentos", headers=h).json()
        assert fragmentos[0]["location"] == "sección 1" and "protocolo TCP" in " ".join(f["text"] for f in fragmentos)

        solicitud = {
            "unidad_id": unidad["id"],
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
        respuesta = api.post("/api/v1/generaciones", headers=h, json=solicitud)
        assert respuesta.status_code == 200, respuesta.text
        datos = respuesta.json()
        assert datos["mode"] == "rag" and datos["generator"]["usaIA"] is False
        ids = {f["id"] for f in datos["fragments"]}
        # Lo recuperado incluye todo lo citado (la evaluación con Ragas lo usa como contexto).
        recuperados = {f["id"] for f in datos["retrievedChunks"]}
        assert ids and ids <= recuperados and all(f["text"] for f in datos["retrievedChunks"])
        for recurso in datos["resources"]:
            assert recurso["source"] == "rag" and recurso["status"] == "pendiente"
            assert all(set(c["fragmentIds"]) <= ids for c in recurso["citations"])
            assert len(recurso["options"]) == 4 and sum(o["isCorrect"] for o in recurso["options"]) == 1
        assert api.get(f"/api/v1/generaciones/{datos['request']['id']}", headers=h).json()["mode"] == "rag"

        explicacion = api.post(
            "/api/v1/generaciones",
            headers=h,
            json={**solicitud, "etapa_5e": "explain", "tipo_recurso": "explicacion", "cantidad": 1},
        )
        assert explicacion.status_code == 200 and explicacion.json()["resources"][0]["options"] is None

        assert api.delete(f"/api/v1/documentos/{subido.json()['id']}", headers=h).status_code == 204
        sin_material = api.post("/api/v1/generaciones", headers=h, json=solicitud)
        assert sin_material.status_code == 400 and sin_material.json()["error"]["codigo"] == "SIN_MATERIAL_PROCESADO"


def test_rutas_de_material_validan_sesion_y_datos(servidor: str):
    with httpx.Client(base_url=servidor, timeout=30) as api:
        assert api.post("/api/v1/documentos/x/procesar").status_code == 401
        h = {"Authorization": "Bearer " + api.post("/api/v1/sesiones", json=CREDENCIALES).json()["token"]}
        assert (
            api.post("/api/v1/documentos/no-existe/procesar", headers=h).json()["error"]["codigo"]
            == "DOCUMENTO_NO_ENCONTRADO"
        )
        assert api.post("/api/v1/documentos/desde-tema", headers=h, json={"unitId": "u1", "tema": "ab"}).status_code == 422
        apagada = api.post("/api/v1/documentos/desde-tema", headers=h, json={"unitId": "u2", "tema": "redes"})
        assert apagada.status_code == 503 and apagada.json()["error"]["codigo"] == "BUSQUEDA_NO_DISPONIBLE"