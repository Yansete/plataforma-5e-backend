"""HU-053 y HU-018: genera propuestas para la revisión docente.

Si la unidad del docente tiene material procesado, se recuperan sus fragmentos más
relacionados con la solicitud y el generador (IA o reglas) redacta citándolos (RAG).
Las unidades de demostración sin material propio siguen usando los ejemplos preparados.
"""
import logging
import random
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from plataforma5e.application.ports.configuracion_repository import ConfiguracionRepositoryPort
from plataforma5e.application.ports.generacion_repository import GeneracionRepositoryPort
from plataforma5e.application.ports.generador import GeneradorRecursosPort
from plataforma5e.application.ports.material import MaterialRepositoryPort
from plataforma5e.application.ports.revision import RevisionRepositoryPort
from plataforma5e.application.services.redaccion import construir_contexto, normalizar_recursos
from plataforma5e.domain.generacion import GeneracionError
from plataforma5e.domain.recuperacion import recuperar

LETRAS = 'abcdefghij'
SIN_MATERIAL = ('Esta unidad todavía no tiene material procesado. Sube un documento o busca el tema '
                'en la pestaña Material y vuelve a intentar.')
PARAMETROS = ('resourceType', 'stage', 'outcomeId', 'difficulty', 'optionCount', 'instructions', 'audience',
              'competency', 'modalities', 'topK', 'evidenceThreshold')
registro = logging.getLogger('plataforma5e.generacion')


class GeneracionService:
    def __init__(self, repositorio: GeneracionRepositoryPort,
                 configuracion: ConfiguracionRepositoryPort | None = None,
                 material: MaterialRepositoryPort | None = None,
                 generador: GeneradorRecursosPort | None = None,
                 respaldo: GeneradorRecursosPort | None = None,
                 revision: RevisionRepositoryPort | None = None,
                 ejemplos_demo: bool = True):
        """`ejemplos_demo`: sin material propio, responde con los ejemplos preparados del curso de prueba.
        Solo lo usan las pruebas (CATALOGO_DEMO=true); el sistema publicado genera únicamente con material."""
        self._repo = repositorio
        self._ejemplos_demo = ejemplos_demo
        self._revision = revision
        self._config = configuracion
        self._material = material
        self._generador = generador
        self._respaldo = respaldo

    def generar(self, solicitud: dict, docente: str | None = None) -> dict:
        if docente and self._config and self._material and (self._generador or self._respaldo):
            curso, unidad = self._curso_y_unidad(docente, solicitud['unitId'])
            if unidad is not None:
                fragmentos = self._material.fragmentos_de_unidad(docente, unidad['id'])
                if fragmentos:
                    return self._generar_con_material(solicitud, docente, curso, unidad, fragmentos)
        if not self._ejemplos_demo:
            raise GeneracionError('SIN_MATERIAL_PROCESADO', SIN_MATERIAL)
        return self._generar_demo(solicitud, docente)

    # ------------------------------------------------------------------ material real (RAG)

    def _curso_y_unidad(self, docente: str, unidad_id: str) -> tuple[dict, dict | None]:
        for curso in self._config.cursos(docente):
            for unidad in curso['units']:
                if unidad['id'] == unidad_id:
                    return curso, unidad
        return {}, None

    def _generar_con_material(self, solicitud: dict, docente: str, curso: dict, unidad: dict, fragmentos: list[dict]) -> dict:
        if solicitud['outcomeId'] and not any(o['id'] == solicitud['outcomeId'] for o in unidad.get('outcomes', [])):
            raise GeneracionError('RESULTADO_INVALIDO', 'El resultado de aprendizaje no pertenece a la unidad.')
        consulta = ' '.join(filter(None, [
            unidad.get('title', ''),
            *(o.get('text', '') for o in unidad.get('outcomes', []) if not solicitud['outcomeId'] or o['id'] == solicitud['outcomeId']),
            solicitud.get('instructions', ''), solicitud.get('competency', ''),
        ]))
        elegidos = recuperar(consulta, fragmentos, max(3, min(int(solicitud.get('topK') or 8), 12)))
        documentos = {d['id']: d for d in self._config.documentos(docente) if d['unitId'] == unidad['id']}
        contexto = construir_contexto(curso, unidad, solicitud, elegidos, {i: d['fileName'] for i, d in documentos.items()})

        recursos, usado, aviso = [], None, None
        if self._generador is not None:
            try:
                recursos = normalizar_recursos(self._generador.generar(contexto), contexto)
                usado = self._generador
                if not recursos:
                    aviso = f'{self._generador.descripcion} no devolvió recursos con citas válidas del material.'
            except Exception as exc:  # proveedor caído, límite de uso o respuesta ilegible
                aviso = f'{self._generador.descripcion} no respondió ({str(exc)[:160]}).'
        if not recursos and self._respaldo is not None and self._respaldo is not self._generador:
            recursos = normalizar_recursos(self._respaldo.generar(contexto), contexto)
            usado = self._respaldo
            if aviso:
                aviso += ' Se usó el generador por reglas.'
        if aviso:
            # Queda en los registros del servidor (Render, Logs) para saber por qué no respondió la IA.
            registro.warning('Generación con respaldo: %s', aviso)
        if not recursos:
            # El motivo técnico (proveedor, código de error) queda en los registros; la pantalla da la salida.
            raise GeneracionError('EVIDENCIA_INSUFICIENTE', 'No se pudieron redactar recursos que citen el material. '
                                  'Prueba con otro tipo de recurso o agrega más material a la unidad.')

        ahora = datetime.now(timezone.utc).isoformat()
        request = {**solicitud, 'id': f'sol-api-{uuid4()}', 'createdAt': ahora}
        outcome = solicitud['outcomeId'] or next((o['id'] for o in unidad.get('outcomes', [])), '')
        salida = [self._recurso(r, request, unidad['id'], outcome, usado.descripcion, ahora) for r in recursos]
        citados = {fid for r in salida for c in r['citations'] for fid in c['fragmentIds']}
        citados |= {fid for r in salida for o in (r['options'] or []) for fid in o['sourceFragmentIds']}
        usados = [f for f in elegidos if f['id'] in citados]
        docs = [documentos[i] for i in dict.fromkeys(f['documento_id'] for f in usados) if i in documentos]
        usa_ia = bool(getattr(usado, 'usa_ia', False))
        self._guardar_para_revision(docente, unidad['id'], salida, usados, docs, request, usa_ia)
        aviso_final = f' {aviso}' if aviso else ''
        resultado = {
            'mode': 'rag',
            'notice': f'Generado con {usado.descripcion} a partir de {len(elegidos)} fragmento(s) de tu material.{aviso_final}',
            'generator': {'descripcion': usado.descripcion, 'usaIA': usa_ia, 'fallback': aviso is not None},
            'request': request,
            'resources': salida,
            'available': len(salida),
            'fragments': [{'id': f['id'], 'documentId': f['documento_id'], 'location': f['ubicacion'], 'unitId': unidad['id'],
                           'outcomeId': outcome, 'text': f['texto'], 'relevance': f.get('relevancia', 0.0)} for f in usados],
            'documents': docs,
            # Todo lo recuperado (no solo lo citado): lo usa la evaluación RAG. La interfaz no lo muestra.
            'retrievedChunks': [{'id': f['id'], 'location': f['ubicacion'], 'text': f['texto'],
                                 'relevance': f.get('relevancia', 0.0)} for f in elegidos],
        }
        self._repo.guardar(resultado, docente)
        return resultado

    def _guardar_para_revision(self, docente, unidad_id, salida, usados, docs, request, usa_ia) -> None:
        """Cada recurso guarda su evidencia (copia de los fragmentos citados) y los parámetros con que se pidió:
        así la revisión se ve igual aunque luego se borre el documento, y «Regenerar» repite el pedido."""
        nombres = {d['id']: d.get('fileName', '') for d in docs}
        origenes = {d['id']: d.get('origin') or {} for d in docs}
        por_id = {f['id']: f for f in usados}
        parametros = {k: request.get(k) for k in PARAMETROS}
        for r in salida:
            citados = [fid for c in r['citations'] for fid in c['fragmentIds']]
            citados += [fid for o in (r['options'] or []) for fid in o['sourceFragmentIds']]
            r['evidence'] = [{'id': fid, 'text': por_id[fid]['texto'], 'location': por_id[fid]['ubicacion'],
                              'documentId': por_id[fid]['documento_id'], 'documentName': nombres.get(por_id[fid]['documento_id'], ''),
                              'sourceUrl': origenes.get(por_id[fid]['documento_id'], {}).get('url'),
                              'license': origenes.get(por_id[fid]['documento_id'], {}).get('licencia')}
                             for fid in dict.fromkeys(citados) if fid in por_id]
            r['params'] = parametros
            r['generatorKind'] = 'ia' if usa_ia else 'respaldo'
        if self._revision is not None:
            self._revision.recursos_guardar(docente, unidad_id, salida)

    @staticmethod
    def _recurso(r: dict, request: dict, unidad_id: str, outcome: str, generador: str, ahora: str) -> dict:
        rid = f'rec-api-{uuid4()}'
        opciones = None
        if r['alternativas']:
            alternativas = list(r['alternativas'])
            random.Random(rid).shuffle(alternativas)  # la clave no queda siempre en la misma posición
            opciones = [{
                'id': f'{rid}:{LETRAS[i]}', 'text': a['texto'], 'isCorrect': a['correcta'], 'feedback': a['retroalimentacion'],
                'sourceFragmentIds': a['fragmentos'], 'decision': 'pendiente', 'discardReason': None, 'edited': False,
                'reliabilityWarning': None,
            } for i, a in enumerate(alternativas)]
        return {
            'exampleId': 'material-docente', 'unitId': unidad_id, 'outcomeId': outcome, 'stage': request['stage'],
            'type': request['resourceType'], 'title': r['titulo'], 'body': r['contenido'], 'id': rid,
            'requestId': request['id'], 'source': 'rag', 'generator': generador, 'options': opciones,
            'citations': r['citas'], 'status': 'pendiente', 'edited': False, 'discardReason': None,
            'createdAt': ahora, 'updatedAt': ahora, 'decidedAt': None,
        }

    # ------------------------------------------------------------------ ejemplos de demostración

    def _generar_demo(self, solicitud: dict, docente: str | None = None) -> dict:
        catalogo = self._repo.catalogo_demo()
        unidad = next((u for u in catalogo['units'] if u['id'] == solicitud['unitId']), None)
        if unidad is None:
            raise GeneracionError('SIN_MATERIAL_PROCESADO', SIN_MATERIAL)
        if solicitud['outcomeId'] and not any(o['id'] == solicitud['outcomeId'] for o in unidad['outcomes']):
            raise GeneracionError('RESULTADO_INVALIDO', 'El resultado de aprendizaje no pertenece a la unidad.')
        disponibles = [e for e in catalogo['examples'] if e['unitId'] == solicitud['unitId'] and e['stage'] == solicitud['stage'] and e['type'] == solicitud['resourceType'] and (solicitud['outcomeId'] is None or e['outcomeId'] == solicitud['outcomeId'])]
        if solicitud['stage'] == 'evaluate':
            disponibles = [e for e in disponibles if len(e.get('options', [])) == solicitud['optionCount']]
        if not disponibles:
            raise GeneracionError('EVIDENCIA_INSUFICIENTE', 'La API de demostración no tiene ejemplos para esta combinación de unidad, etapa y tipo. No se generó contenido.')
        ahora = datetime.now(timezone.utc).isoformat()
        request = {**solicitud, 'id': f'sol-api-{uuid4()}', 'createdAt': ahora}
        recursos = []
        referencias = set()
        for original in disponibles[:solicitud['quantity']]:
            e = deepcopy(original)
            rid = f'rec-api-{uuid4()}'
            citations = []
            for c in e['citations']:
                referencias.update(c['fragmentIds'])
                citations.append({**c, 'fragmentIds': [f'api-demo:{f}' for f in c['fragmentIds']]})
            options = None
            if e.get('options') is not None:
                options = []
                for o in e['options']:
                    referencias.update(o['sourceFragmentIds'])
                    options.append({**o, 'id': f'{rid}:{o["id"]}', 'sourceFragmentIds': [f'api-demo:{f}' for f in o['sourceFragmentIds']], 'decision': 'pendiente', 'discardReason': None, 'edited': False, 'reliabilityWarning': o.get('reliabilityWarning')})
            recursos.append({**{k: e[k] for k in ['exampleId','unitId','outcomeId','stage','type','title','body']}, 'id': rid, 'requestId': request['id'], 'source': 'api_demo', 'options': options, 'citations': citations, 'status': 'pendiente', 'edited': False, 'discardReason': None, 'createdAt': ahora, 'updatedAt': ahora, 'decidedAt': None})
        fragments = [f for f in catalogo['fragments'] if f['id'] in referencias]
        if {f['id'] for f in fragments} != referencias:
            raise GeneracionError('EVIDENCIA_INSUFICIENTE', 'Faltan fragmentos de demostración para sustentar la propuesta. No se generó contenido.')
        document_ids = {f['documentId'] for f in fragments}
        documents = [d for d in catalogo['documents'] if d['id'] in document_ids]
        if {d['id'] for d in documents} != document_ids:
            raise GeneracionError('EVIDENCIA_INSUFICIENTE', 'Falta el documento de origen de la evidencia de demostración.')
        resultado = {'mode': 'api_demo', 'notice': catalogo['notice'], 'request': request, 'resources': recursos, 'available': len(disponibles), 'fragments': [{**f, 'id': f'api-demo:{f["id"]}', 'documentId': f'api-demo:{f["documentId"]}'} for f in fragments], 'documents': [{**d, 'id': f'api-demo:{d["id"]}'} for d in documents]}
        self._repo.guardar(resultado, docente) if docente else self._repo.guardar(resultado)
        return resultado

    def obtener(self, generacion_id: str) -> dict:
        resultado = self._repo.obtener(generacion_id)
        if resultado is None:
            raise GeneracionError('GENERACION_NO_ENCONTRADA', 'La solicitud de generación no existe.')
        return resultado

