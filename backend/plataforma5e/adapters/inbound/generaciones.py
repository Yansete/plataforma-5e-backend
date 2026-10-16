"""Contrato HTTP HU-053 / EN-006: con material procesado genera con RAG; sin él, usa la demo."""
from fastapi import APIRouter, Depends
from plataforma5e.adapters.inbound.autorizacion import obtener_autorizacion
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from plataforma5e.domain.errores import PersistenciaNoDisponible
from plataforma5e.adapters.inbound.contratos.solicitud import GenerationRequestModel
from plataforma5e.application.services.generacion_service import GeneracionService
from plataforma5e.domain.generacion import GeneracionError

class SolicitudIntegrada(GenerationRequestModel):
    model_config = ConfigDict(extra='forbid')
    publico_objetivo: str = Field(default='', max_length=200)
    competencia: str = Field(default='', max_length=200)
    # Sprint 1: solo texto. Otra modalidad responde 422 (HU-053, alcance acordado con el docente).
    modalidades: list[Literal['Textual']] = Field(default_factory=lambda: ['Textual'], max_length=1)

    def a_dominio(self) -> dict:
        return {'unitId': self.unidad_id, 'outcomeId': self.resultado_aprendizaje_id, 'stage': self.etapa_5e, 'resourceType': self.tipo_recurso, 'quantity': self.cantidad, 'difficulty': self.dificultad, 'optionCount': self.alternativas, 'topK': self.top_k, 'evidenceThreshold': self.umbral_evidencia, 'instructions': self.indicaciones or '', 'audience': self.publico_objetivo, 'competency': self.competencia, 'modalities': self.modalidades}

class GeneracionRespuesta(BaseModel):
    mode: Literal['api_demo', 'rag']
    notice: str
    generator: dict | None = None
    request: dict
    resources: list[dict]
    available: int
    fragments: list[dict]
    documents: list[dict]

def crear_router_generaciones(servicio: GeneracionService, configuracion=None) -> APIRouter:
    router = APIRouter(prefix='/api/v1/generaciones', tags=['EP-003 Generación de recursos'])
    @router.post('', response_model=GeneracionRespuesta)
    def generar(req: SolicitudIntegrada, authorization: str | None = Depends(obtener_autorizacion)):
        try:
            docente = configuracion.autenticar(authorization) if authorization and configuracion else None
            if docente: configuracion.unidad(docente, req.unidad_id)
            return servicio.generar(req.a_dominio(), docente)
        except GeneracionError as exc:
            return JSONResponse(status_code=400, content={'error': {'codigo': exc.codigo, 'mensaje': exc.mensaje}})
        except PersistenciaNoDisponible:
            return JSONResponse(status_code=503, content={'error': {'codigo': 'PERSISTENCIA_NO_DISPONIBLE', 'mensaje': 'No se pudo guardar la solicitud. Comprueba la conexión de la base de datos.'}})
    @router.get('/{generacion_id}', response_model=GeneracionRespuesta)
    def obtener(generacion_id: str, authorization: str | None = Depends(obtener_autorizacion)):
        try:
            if configuracion: configuracion.comprobar_generacion(generacion_id, authorization)
            return servicio.obtener(generacion_id)
        except GeneracionError as exc:
            return JSONResponse(status_code=404, content={'error': {'codigo': exc.codigo, 'mensaje': exc.mensaje}})
    return router
