"""Recorrido por HTTP de una cuenta nueva: curso, material, generación, revisión guardada, descargas y borrado."""

from __future__ import annotations

import json

import httpx

MATERIAL = (
    "Unidad 1: Protocolos de transporte\n\n"
    "El protocolo TCP es orientado a la conexión y garantiza una entrega confiable de los datos. "
    "El protocolo UDP no establece conexión ni confirma la entrega; por eso es más rápido.\n\n"
    "El protocolo IP se encarga del direccionamiento y del enrutamiento de los paquetes. "
    "El enrutador es el dispositivo que decide el camino de cada paquete hasta su destino. "
    "La encapsulación es el proceso por el cual cada capa agrega su propio encabezado a los datos."
).encode()
CUENTA = {"name": "Ana Pérez", "email": "ana.perez@correo.pe", "password": "clave-segura-1"}


def test_cuenta_nueva_revisa_descarga_y_borra_su_curso(servidor: str):
    with httpx.Client(base_url=servidor, timeout=30) as api:
        creada = api.post("/api/v1/cuentas", json=CUENTA)
        assert creada.status_code == 201 and creada.json()["name"] == "Ana Pérez"
        h = {"Authorization": "Bearer " + creada.json()["token"]}
        assert api.post("/api/v1/cuentas", json=CUENTA).status_code == 409
        assert (
            api.post("/api/v1/cuentas", json={**CUENTA, "email": "otra@correo.pe", "password": "corta"}).status_code
            == 422
        )
        assert api.get("/api/v1/sesiones/actual", headers=h).json() == {
            "email": "ana.perez@correo.pe",
            "name": "Ana Pérez",
        }
        assert api.get("/api/v1/cursos", headers=h).json() == []
        assert (
            api.post(
                "/api/v1/sesiones",
                json={"email": "ANA.PEREZ@correo.pe", "password": "clave-segura-1"},
            ).status_code
            == 200
        )

        curso = api.post(
            "/api/v1/cursos",
            headers=h,
            json={
                "code": "RED-301",
                "name": "Redes",
                "term": "2026-II",
                "units": [{"title": "Protocolos", "outcomes": [{"text": "Distingue TCP y UDP"}]}],
            },
        ).json()
        unidad = curso["units"][0]
        contexto = {
            "unitId": unidad["id"],
            "outcomeIds": [unidad["outcomes"][0]["id"]],
            "documentType": "Separata o apuntes de clase",
            "suggestedStage": None,
            "usePermission": True,
        }
        documento = api.post(
            "/api/v1/documentos",
            headers=h,
            files={"file": ("protocolos.txt", MATERIAL)},
            data={"contexto": json.dumps(contexto)},
        ).json()
        assert (
            api.post(f"/api/v1/documentos/{documento['id']}/procesar", headers=h).json()["status"]
            == "procesado"
        )

        solicitud = {
            "unidad_id": unidad["id"],
            "resultado_aprendizaje_id": None,
            "etapa_5e": "evaluate",
            "tipo_recurso": "item_opcion_multiple",
            "cantidad": 1,
            "dificultad": "intermedia",
            "alternativas": 4,
            "top_k": 8,
            "umbral_evidencia": 0.6,
            "indicaciones": "",
            "publico_objetivo": "",
            "competencia": "",
            "modalidades": ["Textual"],
        }
        generado = api.post("/api/v1/generaciones", headers=h, json=solicitud).json()
        assert generado["generator"]["fallback"] is False

        base = f"/api/v1/unidades/{unidad['id']}"
        recursos = api.get(base + "/recursos", headers=h).json()
        assert [r["id"] for r in recursos] == [generado["resources"][0]["id"]]
        recurso = recursos[0]
        assert recurso["evidence"] and recurso["evidence"][0]["documentName"] == "protocolos.txt"
        assert recurso["params"]["resourceType"] == "item_opcion_multiple" and recurso["generatorKind"] == "respaldo"

        revision = {
            "title": recurso["title"],
            "body": recurso["body"],
            "status": "aprobado",
            "discardReason": None,
            "edited": False,
            "options": [
                {
                    "id": o["id"],
                    "text": o["text"],
                    "feedback": o["feedback"],
                    "decision": "pendiente",
                    "discardReason": None,
                    "edited": False,
                }
                for o in recurso["options"]
            ],
        }
        bloqueada = api.put(f"{base}/recursos/{recurso['id']}", headers=h, json=revision)
        assert bloqueada.status_code == 409 and bloqueada.json()["error"]["codigo"] == "APROBACION_BLOQUEADA"
        for o in revision["options"]:
            o["decision"] = "aceptado"
        aprobado = api.put(f"{base}/recursos/{recurso['id']}", headers=h, json=revision)
        assert aprobado.status_code == 200 and aprobado.json()["status"] == "aprobado"
        assert api.get(base + "/recursos", headers=h).json()[0]["status"] == "aprobado"
        assert api.get("/api/v1/resumen", headers=h).json() == [
            {"courseId": curso["id"], "unitId": unidad["id"], "approved": 1, "pending": 0}
        ]

        otra = {
            "Authorization": "Bearer "
            + api.post("/api/v1/cuentas", json={**CUENTA, "email": "beto@correo.pe"}).json()["token"]
        }
        assert api.get(base + "/recursos", headers=otra).status_code == 404
        assert api.get(base + "/recursos").status_code == 401

        descarga = api.post(
            base + "/descargas",
            headers=h,
            json={"format": "moodle_xml", "fileName": "red-301-unidad-1-moodle.xml", "resourceCount": 1},
        )
        assert descarga.status_code == 201
        assert [d["fileName"] for d in api.get(base + "/descargas", headers=h).json()] == [
            "red-301-unidad-1-moodle.xml"
        ]
        assert (
            api.post(
                base + "/descargas",
                headers=h,
                json={"format": "pdf", "fileName": "x.pdf", "resourceCount": 1},
            ).status_code
            == 422
        )
        assert api.delete(base + "/descargas", headers=h).status_code == 204
        assert api.get(base + "/descargas", headers=h).json() == []

        assert api.delete(f"{base}/recursos/{recurso['id']}", headers=h).status_code == 204
        assert api.get(base + "/recursos", headers=h).json() == []

        assert api.delete(f"/api/v1/cursos/{curso['id']}", headers=h).status_code == 204
        assert api.get("/api/v1/documentos", headers=h).json() == []
        assert api.get(base + "/recursos", headers=h).status_code == 404
        assert api.delete(f"/api/v1/cursos/{curso['id']}", headers=h).status_code == 404