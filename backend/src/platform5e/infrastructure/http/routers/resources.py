"""
API de revisión docente (HU-010), historial de descargas por unidad didáctica
y endpoints heredados de soporte para la demo de punta a punta.
"""

from __future__ import annotations

import html
from typing import Any, Literal
from xml.etree import ElementTree as ET

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.generation.generation_service import GenerationService
from platform5e.application.services.review.resource_review_service import ResourceReviewService
from platform5e.infrastructure.http.dependencies import extract_authorization_header

DiscardReasonType = Literal[
    "sin_sentido",
    "tambien_correcto",
    "duplicado",
    "fuera_de_unidad",
    "otro",
    "regenerado",
]


class BaseContract(BaseModel):
    """Contrato base restrictivo para esquemas de revisión."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReviewedOptionInput(BaseContract):
    """Esquema para una alternativa de respuesta revisada."""

    id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=600)
    feedback: str = Field(default="", max_length=600)
    decision: Literal["pendiente", "aceptado", "descartado"]
    discardReason: DiscardReasonType | None = None
    edited: bool = False


class ReviewedResourceInput(BaseContract):
    """Esquema para la actualización del estado y contenido de un recurso docente."""

    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=8000)
    status: Literal["pendiente", "aprobado", "descartado"]
    discardReason: DiscardReasonType | None = None
    edited: bool = False
    options: list[ReviewedOptionInput] | None = Field(default=None, max_length=10)


class DownloadRegistrationInput(BaseContract):
    """Esquema de entrada para registrar una descarga en el historial de la unidad."""

    format: Literal["moodle_xml", "qti21", "documento"]
    fileName: str = Field(min_length=1, max_length=200)
    resourceCount: int = Field(ge=0, le=500)


def create_resources_router(
    review_service: ResourceReviewService,
    account_service: AccountService,
    generation_service: GenerationService | None = None,
) -> APIRouter:
    """Construye el router HTTP para la revisión docente y descargas de recursos."""
    router = APIRouter(prefix="/api/v1", tags=["Revisión y descargas"])

    _demo_recursos: dict[str, dict[str, Any]] = {}

    def _reiniciar_demo():
        _demo_recursos.clear()
        _demo_recursos["rec-demo-1"] = {
            "id": "rec-demo-1",
            "tipo": "item_opcion_multiple",
            "titulo": "Pregunta 1: Protocolo de transporte",
            "enunciado": "¿Qué protocolo garantiza entrega confiable y orientada a la conexión?",
            "retroalimentacion": "TCP establece conexión previa mediante handshake.",
            "retroalimentacion_general": "TCP establece conexión previa mediante handshake.",
            "estado": "pendiente",
            "alternativas": [
                {
                    "letra": "A",
                    "texto": "TCP",
                    "es_correcta": True,
                    "justificacion": "Correcto: TCP garantiza confiabilidad y orden.",
                    "retroalimentacion": "Correcto: TCP garantiza confiabilidad y orden.",
                    "estado": "aceptado",
                    "decision": "aceptado",
                },
                {
                    "letra": "B",
                    "texto": "UDP",
                    "es_correcta": False,
                    "justificacion": "Incorrecto: UDP es no orientado a la conexión.",
                    "retroalimentacion": "Incorrecto: UDP es no orientado a la conexión.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
                {
                    "letra": "C",
                    "texto": "IP",
                    "es_correcta": False,
                    "justificacion": "Incorrecto: IP opera en capa de red.",
                    "retroalimentacion": "Incorrecto: IP opera en capa de red.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
                {
                    "letra": "D",
                    "texto": "DNS",
                    "es_correcta": False,
                    "justificacion": "Incorrecto: DNS es de capa de aplicación.",
                    "retroalimentacion": "Incorrecto: DNS es de capa de aplicación.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
            ],
        }
        _demo_recursos["rec-demo-2"] = {
            "id": "rec-demo-2",
            "tipo": "item_opcion_multiple",
            "titulo": "Pregunta 2: Protocolo no orientado a conexión",
            "enunciado": "¿Qué protocolo prioriza la velocidad y no requiere confirmación?",
            "retroalimentacion": "UDP minimiza la latencia.",
            "retroalimentacion_general": "UDP minimiza la latencia.",
            "estado": "pendiente",
            "alternativas": [
                {
                    "letra": "A",
                    "texto": "UDP",
                    "es_correcta": True,
                    "justificacion": "Correcto: UDP minimiza la latencia.",
                    "retroalimentacion": "Correcto: UDP minimiza la latencia.",
                    "estado": "aceptado",
                    "decision": "aceptado",
                },
                {
                    "letra": "B",
                    "texto": "TCP",
                    "es_correcta": False,
                    "justificacion": "Incorrecto: TCP tiene control de flujo.",
                    "retroalimentacion": "Incorrecto: TCP tiene control de flujo.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
                {
                    "letra": "C",
                    "texto": "FTP",
                    "es_correcta": False,
                    "justificacion": "Incorrecto: FTP es orientado a la conexión.",
                    "retroalimentacion": "Incorrecto: FTP es orientado a la conexión.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
                {
                    "letra": "D",
                    "texto": "SMTP",
                    "es_correcta": False,
                    "justificacion": "Incorrecto: SMTP usa TCP.",
                    "retroalimentacion": "Incorrecto: SMTP usa TCP.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
            ],
        }
        _demo_recursos["rec-demo-3"] = {
            "id": "rec-demo-3",
            "tipo": "item_opcion_multiple",
            "titulo": "Pregunta 3: Capa física",
            "enunciado": "¿Cuál es un medio de transmisión no guiado?",
            "retroalimentacion": "Las ondas de radio se propagan sin medio físico.",
            "retroalimentacion_general": "Las ondas de radio se propagan sin medio físico.",
            "estado": "pendiente",
            "alternativas": [
                {
                    "letra": "A",
                    "texto": "Ondas de radio",
                    "es_correcta": True,
                    "justificacion": "Correcto.",
                    "retroalimentacion": "Correcto.",
                    "estado": "aceptado",
                    "decision": "aceptado",
                },
                {
                    "letra": "B",
                    "texto": "Fibra óptica",
                    "es_correcta": False,
                    "justificacion": "Incorrecto.",
                    "retroalimentacion": "Incorrecto.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
                {
                    "letra": "C",
                    "texto": "Cable coaxial",
                    "es_correcta": False,
                    "justificacion": "Incorrecto.",
                    "retroalimentacion": "Incorrecto.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
                {
                    "letra": "D",
                    "texto": "Par trenzado",
                    "es_correcta": False,
                    "justificacion": "Incorrecto.",
                    "retroalimentacion": "Incorrecto.",
                    "estado": "pendiente",
                    "decision": "pendiente",
                },
            ],
        }

    def get_current_teacher(
        authorization: str | None = Depends(extract_authorization_header),
    ) -> str:
        return account_service.authenticate_token(authorization)

    # -------------------------------------------------------------
    # Endpoints de compatibilidad para la demo y pruebas E2E
    # -------------------------------------------------------------
    @router.post("/recursos/generar")
    def legacy_generate_resources(payload: dict[str, Any] = {}):
        _reiniciar_demo()
        return list(_demo_recursos.values())

    @router.get("/recursos/{recurso_id}")
    def legacy_get_resource(recurso_id: str):
        if recurso_id not in _demo_recursos:
            return JSONResponse(
                status_code=404,
                content={"error": {"codigo": "RECURSO_NO_ENCONTRADO", "mensaje": f"Recurso {recurso_id} no existe"}},
            )
        rec = _demo_recursos[recurso_id]
        # Asegurar que todas las claves existan
        rec.setdefault("retroalimentacion", rec.get("retroalimentacion_general", ""))
        rec.setdefault("retroalimentacion_general", rec.get("retroalimentacion", ""))
        return rec

    @router.post("/recursos/{recurso_id}/alternativas/{letra}/decision")
    def legacy_alternative_decision(recurso_id: str, letra: str, payload: dict[str, Any] = {}):
        if recurso_id not in _demo_recursos:
            return JSONResponse(
                status_code=404,
                content={"error": {"codigo": "RECURSO_NO_ENCONTRADO", "mensaje": f"Recurso {recurso_id} no existe"}},
            )
        rec = _demo_recursos[recurso_id]
        alt = next((a for a in rec["alternativas"] if a["letra"] == letra), None)
        if not alt:
            return JSONResponse(
                status_code=404,
                content={"error": {"codigo": "ALTERNATIVA_NO_ENCONTRADA", "mensaje": f"Alternativa {letra} no existe"}},
            )
        decision = payload.get("decision", "aceptar")
        if decision in ("aceptar", "aceptado"):
            alt["estado"] = "aceptado"
            alt["decision"] = "aceptado"
        elif decision in ("descartar", "descartado"):
            alt["estado"] = "descartado"
            alt["decision"] = "descartado"
        elif decision in ("editar", "editado"):
            alt["estado"] = "aceptado"
            alt["decision"] = "aceptado"
            if "texto" in payload:
                alt["texto"] = payload["texto"]

        return {"status": "ok", "recurso": rec}

    @router.post("/recursos/{recurso_id}/aprobar")
    def legacy_approve_resource(recurso_id: str, payload: dict[str, Any] = {}):
        if recurso_id not in _demo_recursos:
            return JSONResponse(
                status_code=404,
                content={"error": {"codigo": "RECURSO_NO_ENCONTRADO", "mensaje": f"Recurso {recurso_id} no existe"}},
            )
        rec = _demo_recursos[recurso_id]
        # Si tiene alternativas aún en estado pendiente y no se fuerza, bloquear aprobación
        pendientes = [a for a in rec["alternativas"] if a.get("estado") == "pendiente"]
        if pendientes and not payload.get("forzar", False):
            return JSONResponse(
                status_code=400,
                content={"error": {"codigo": "APROBACION_BLOQUEADA", "mensaje": "Hay alternativas pendientes antes de aprobar."}},
            )
        rec["estado"] = "aprobado"
        return {"status": "ok", "recurso": rec}

    @router.post("/exportaciones")
    def legacy_export_resources(payload: dict[str, Any] = {}):
        aprobados = [r for r in _demo_recursos.values() if r["estado"] == "aprobado"]
        if not aprobados:
            return JSONResponse(
                status_code=400,
                content={"error": {"codigo": "SIN_RECURSOS_APROBADOS", "mensaje": "No hay recursos aprobados para exportar"}},
            )

        quiz = ET.Element("quiz")
        cat_q = ET.SubElement(quiz, "question", type="category")
        cat = ET.SubElement(cat_q, "category")
        ET.SubElement(cat, "text").text = "$course$/top/Por defecto en Curso"
        info = ET.SubElement(cat_q, "info", format="html")
        ET.SubElement(info, "text").text = ""
        ET.SubElement(cat_q, "idnumber").text = ""

        for r in aprobados:
            q = ET.SubElement(quiz, "question", type="multichoice")
            name = ET.SubElement(q, "name")
            ET.SubElement(name, "text").text = r["titulo"]
            qtext = ET.SubElement(q, "questiontext", format="html")
            ET.SubElement(qtext, "text").text = f"<p>{html.escape(r['enunciado'])}</p>"
            gfeedback = ET.SubElement(q, "generalfeedback", format="html")
            ET.SubElement(gfeedback, "text").text = f"<p>{html.escape(r['retroalimentacion_general'])}</p>"
            ET.SubElement(q, "defaultgrade").text = "1.0000000"
            ET.SubElement(q, "penalty").text = "0.3333333"
            ET.SubElement(q, "hidden").text = "0"
            ET.SubElement(q, "idnumber").text = ""
            ET.SubElement(q, "single").text = "true"
            ET.SubElement(q, "shuffleanswers").text = "true"
            ET.SubElement(q, "answernumbering").text = "abc"
            ET.SubElement(q, "showstandardinstruction").text = "0"
            ET.SubElement(ET.SubElement(q, "correctfeedback", format="html"), "text").text = "<p>Respuesta correcta.</p>"
            ET.SubElement(ET.SubElement(q, "partiallycorrectfeedback", format="html"), "text").text = "<p>Respuesta parcialmente correcta.</p>"
            ET.SubElement(ET.SubElement(q, "incorrectfeedback", format="html"), "text").text = "<p>Respuesta incorrecta.</p>"
            ET.SubElement(q, "shownumcorrect")

            vigentes = [a for a in r["alternativas"] if a.get("estado") != "descartado"]
            for alt in vigentes:
                fraction = "100" if alt["es_correcta"] else "0"
                ans = ET.SubElement(q, "answer", fraction=fraction, format="html")
                ET.SubElement(ans, "text").text = f"<p>{html.escape(alt['texto'])}</p>"
                fb = ET.SubElement(ans, "feedback", format="html")
                justificacion = alt.get("justificacion") or alt.get("retroalimentacion") or ""
                ET.SubElement(fb, "text").text = f"<p>{html.escape(justificacion)}</p>"

        xml_str = ET.tostring(quiz, encoding="utf-8", xml_declaration=True)
        return Response(content=xml_str, media_type="application/xml")

    # -------------------------------------------------------------
    # Rutas canónicas de revisión y descargas
    # -------------------------------------------------------------
    @router.get(
        "/resumen",
        summary="Obtener resumen de recursos aprobados y pendientes por unidad",
    )
    def get_review_summary(
        teacher_email: str = Depends(get_current_teacher),
    ) -> list[dict[str, Any]]:
        return review_service.get_summary(teacher_email)

    @router.get(
        "/unidades/{unit_id}/recursos",
        summary="Listar los recursos generados para una unidad con su estado de revisión",
    )
    def list_unit_resources(
        unit_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> list[dict[str, Any]]:
        return review_service.list_resources(teacher_email, unit_id)

    @router.put(
        "/unidades/{unit_id}/recursos/{resource_id}",
        summary="Guardar la revisión y decisiones sobre un recurso",
    )
    def update_resource_review(
        unit_id: str,
        resource_id: str,
        request: ReviewedResourceInput,
        teacher_email: str = Depends(get_current_teacher),
    ) -> dict[str, Any]:
        return review_service.update_resource(
            teacher_email, unit_id, resource_id, request.model_dump()
        )

    @router.delete(
        "/unidades/{unit_id}/recursos/{resource_id}",
        status_code=204,
        summary="Eliminar un recurso formativo",
    )
    def delete_resource(
        unit_id: str,
        resource_id: str,
        teacher_email: str = Depends(get_current_teacher),
    ) -> Response:
        review_service.delete_resource(teacher_email, unit_id, resource_id)
        return Response(status_code=204)

    @router.get(
        "/unidades/{unit_id}/descargas",
        summary="Obtener el historial de descargas de la unidad",
    )
    def get_downloads_history(
        unit_id: str, teacher_email: str = Depends(get_current_teacher)
    ) -> list[dict[str, Any]]:
        return review_service.get_downloads_history(teacher_email, unit_id)

    @router.post(
        "/unidades/{unit_id}/descargas",
        status_code=201,
        summary="Registrar un evento de descarga de recursos",
    )
    def register_download(
        unit_id: str,
        request: DownloadRegistrationInput,
        teacher_email: str = Depends(get_current_teacher),
    ) -> dict[str, Any]:
        return review_service.register_download(
            teacher_email, unit_id, request.model_dump()
        )

    @router.delete(
        "/unidades/{unit_id}/descargas",
        status_code=204,
        summary="Limpiar el historial de descargas de la unidad",
    )
    def clear_downloads_history(
        unit_id: str, teacher_email: str = Depends(get_current_teacher),
    ) -> Response:
        review_service.clear_downloads_history(teacher_email, unit_id)
        return Response(status_code=204)

    return router