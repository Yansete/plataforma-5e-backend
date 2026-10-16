"""Generación con el material del docente (RAG) usando puertos falsos: sin red y sin base de datos."""
import pytest

from plataforma5e.application.services.generacion_service import GeneracionService
from plataforma5e.application.services.redaccion import (construir_contexto, construir_instrucciones, extraer_json,
                                                          normalizar_recursos)
from plataforma5e.domain.generacion import GeneracionError

UNIDAD = {'id': 'u1', 'number': 1, 'title': 'Protocolos de transporte',
          'outcomes': [{'id': 'ra-1', 'code': 'RA1.1', 'text': 'Distingue TCP y UDP'}]}
CURSO = {'id': 'c1', 'name': 'Redes', 'sumilla': 'Curso de redes.', 'logro': 'Explica cómo se comunican los equipos.', 'units': [UNIDAD]}
FRAGMENTOS = [
    {'id': 'f1', 'documento_id': 'doc1', 'unidad_id': 'u1', 'orden': 0, 'ubicacion': 'p. 1',
     'texto': 'El protocolo TCP es orientado a la conexión y garantiza una entrega confiable.'},
    {'id': 'f2', 'documento_id': 'doc1', 'unidad_id': 'u1', 'orden': 1, 'ubicacion': 'p. 2',
     'texto': 'El protocolo UDP no establece conexión y es más rápido.'},
]
DOCUMENTO = {'id': 'doc1', 'unitId': 'u1', 'fileName': 'apuntes.pdf'}


def solicitud(**cambios):
    base = {'unitId': 'u1', 'outcomeId': None, 'stage': 'evaluate', 'resourceType': 'item_opcion_multiple', 'quantity': 1,
            'difficulty': 'intermedia', 'optionCount': 3, 'topK': 5, 'evidenceThreshold': .6, 'instructions': 'contexto peruano',
            'audience': 'Tercer ciclo', 'competency': 'Pensamiento crítico', 'modalities': ['Textual']}
    return {**base, **cambios}


ITEM = {'titulo': 'TCP o UDP', 'contenido': '¿Qué protocolo garantiza una entrega confiable?',
        'citas': [{'afirmacion': 'TCP garantiza la entrega', 'fragmentos': ['F1']}],
        'alternativas': [
            {'texto': 'TCP', 'correcta': True, 'retroalimentacion': 'Correcto.', 'fragmentos': ['F1']},
            {'texto': 'UDP', 'correcta': False, 'retroalimentacion': 'No confirma la entrega.', 'fragmentos': ['F2']},
            {'texto': 'IP', 'correcta': False, 'retroalimentacion': '', 'fragmentos': []},
        ]}


class RepoGeneraciones:
    def __init__(self):
        self.guardados = []

    def catalogo_demo(self):
        return {'units': [], 'examples': [], 'fragments': [], 'documents': [], 'notice': ''}

    def guardar(self, resultado, docente=None):
        self.guardados.append((resultado, docente))

    def obtener(self, generacion_id):
        return None


class Config:
    def cursos(self, docente):
        return [CURSO]

    def documentos(self, docente):
        return [DOCUMENTO]


class Material:
    def __init__(self, fragmentos=FRAGMENTOS):
        self.lista = fragmentos

    def fragmentos_de_unidad(self, docente, unidad_id):
        return [f for f in self.lista if f['unidad_id'] == unidad_id]


class Generador:
    def __init__(self, respuesta=None, error=None, descripcion='IA falsa', usa_ia=True):
        self.respuesta, self.error, self.descripcion, self.usa_ia = respuesta, error, descripcion, usa_ia
        self.contextos = []

    def generar(self, contexto):
        self.contextos.append(contexto)
        if self.error:
            raise self.error
        return self.respuesta


def servicio(generador=None, respaldo=None, material=None):
    repo = RepoGeneraciones()
    return GeneracionService(repo, Config(), material or Material(), generador, respaldo), repo


def test_genera_con_material_cita_fragmentos_y_guarda_historial():
    ia = Generador({'recursos': [ITEM]})
    gen, repo = servicio(ia)
    resultado = gen.generar(solicitud(), 'docente')
    assert resultado['mode'] == 'rag' and resultado['generator'] == {'descripcion': 'IA falsa', 'usaIA': True, 'fallback': False}
    recurso = resultado['resources'][0]
    assert recurso['source'] == 'rag' and recurso['status'] == 'pendiente' and recurso['outcomeId'] == 'ra-1'
    # Las etiquetas F1, F2… se asignan en el orden de relevancia de la búsqueda.
    real = {f['etiqueta']: f['id'] for f in ia.contextos[0]['fragmentos']}
    assert recurso['citations'] == [{'claim': 'TCP garantiza la entrega', 'fragmentIds': [real['F1']]}]
    assert sorted(o['text'] for o in recurso['options']) == ['IP', 'TCP', 'UDP']
    assert sum(o['isCorrect'] for o in recurso['options']) == 1
    sin_fuente = next(o for o in recurso['options'] if o['text'] == 'IP')
    assert sin_fuente['sourceFragmentIds'] == [real['F1']] and sin_fuente['feedback']  # hereda la cita y una retroalimentación
    assert {f['id'] for f in resultado['fragments']} == {'f1', 'f2'}
    assert resultado['documents'] == [DOCUMENTO]
    assert repo.guardados[0][1] == 'docente'
    contexto = ia.contextos[0]
    assert contexto['curso']['sumilla'] == 'Curso de redes.' and contexto['fragmentos'][0]['etiqueta'] == 'F1'
    # Cada recurso lleva su evidencia copiada y los parámetros para poder regenerarlo.
    assert recurso['generatorKind'] == 'ia' and recurso['params']['optionCount'] == 3
    assert {e['id'] for e in recurso['evidence']} == {real['F1'], real['F2']} and recurso['evidence'][0]['documentName'] == 'apuntes.pdf'


def test_los_recursos_generados_se_guardan_para_la_revision():
    class Revision:
        def __init__(self):
            self.guardados = []

        def recursos_guardar(self, docente, unidad_id, recursos):
            self.guardados.append((docente, unidad_id, [r['id'] for r in recursos]))

    revision = Revision()
    gen = GeneracionService(RepoGeneraciones(), Config(), Material(), Generador({'recursos': [ITEM]}), None, revision)
    resultado = gen.generar(solicitud(), 'docente')
    assert revision.guardados == [('docente', 'u1', [resultado['resources'][0]['id']])]


def test_si_la_ia_falla_usa_el_respaldo_y_lo_avisa(caplog):
    reglas = Generador({'recursos': [ITEM]}, descripcion='Reglas', usa_ia=False)
    gen, _ = servicio(Generador(error=RuntimeError('429 límite')), reglas)
    resultado = gen.generar(solicitud(), 'docente')
    assert resultado['generator']['descripcion'] == 'Reglas' and resultado['generator']['fallback'] is True
    assert resultado['resources'][0]['generatorKind'] == 'respaldo'
    assert '429 límite' in caplog.text  # el motivo queda en los registros del servidor
    assert 'no respondió' in resultado['notice'] and 'generador por reglas' in resultado['notice']


def test_si_la_ia_no_cita_bien_usa_el_respaldo():
    malo = {'recursos': [{'titulo': 'x', 'contenido': 'y', 'citas': [{'afirmacion': 'z', 'fragmentos': ['F9']}], 'alternativas': []}]}
    reglas = Generador({'recursos': [ITEM]}, descripcion='Reglas', usa_ia=False)
    gen, _ = servicio(Generador(malo), reglas)
    resultado = gen.generar(solicitud(), 'docente')
    assert 'citas válidas' in resultado['notice']


def test_sin_recursos_validos_rechaza_sin_inventar():
    gen, repo = servicio(Generador({'recursos': []}))
    with pytest.raises(GeneracionError) as error:
        gen.generar(solicitud(), 'docente')
    assert error.value.codigo == 'EVIDENCIA_INSUFICIENTE' and repo.guardados == []


def test_resultado_ajeno_a_la_unidad_se_rechaza():
    gen, _ = servicio(Generador({'recursos': [ITEM]}))
    with pytest.raises(GeneracionError) as error:
        gen.generar(solicitud(outcomeId='ra-otro'), 'docente')
    assert error.value.codigo == 'RESULTADO_INVALIDO'


def test_unidad_sin_material_ni_demo_pide_subir_material():
    gen, _ = servicio(Generador({'recursos': [ITEM]}), material=Material([]))
    with pytest.raises(GeneracionError) as error:
        gen.generar(solicitud(), 'docente')
    assert error.value.codigo == 'SIN_MATERIAL_PROCESADO' and 'pestaña Material' in error.value.mensaje


def test_sin_docente_usa_la_demostracion():
    gen, _ = servicio(Generador({'recursos': [ITEM]}))
    with pytest.raises(GeneracionError) as error:  # el catálogo falso de demo está vacío
        gen.generar(solicitud(unitId='u2'))
    assert error.value.codigo == 'SIN_MATERIAL_PROCESADO'


def test_instrucciones_incluyen_curso_pedido_y_fragmentos():
    contexto = construir_contexto(CURSO, UNIDAD, solicitud(outcomeId='ra-1'), [{**f, 'relevancia': 1} for f in FRAGMENTOS], {'doc1': 'apuntes.pdf'})
    sistema, usuario = construir_instrucciones(contexto)
    assert 'Evaluar' in sistema and 'JSON' in sistema
    assert 'Genera solo texto' in sistema  # Sprint 1: sin multimedia
    for texto in ('SUMILLA: Curso de redes.', 'RA1.1: Distingue TCP y UDP', 'exactamente 3 alternativas', 'Tercer ciclo',
                  'Pensamiento crítico', 'contexto peruano', '[F1] (apuntes.pdf, p. 1)'):
        assert texto in usuario
    vacio = construir_contexto({}, {'title': 'U', 'number': 2}, solicitud(stage='explain', resourceType='glosario', audience='',
                                                                          competency='', modalities=[], instructions=''), [], {})
    _, usuario = construir_instrucciones(vacio)
    assert 'no registrada' in usuario and 'alternativas' in usuario


@pytest.mark.parametrize('texto,esperado', [
    ('{"recursos": []}', {'recursos': []}),
    ('```json\n{"recursos": [1]}\n```', {'recursos': [1]}),
    ('Aquí tienes: {"recursos": [2]} ¡listo!', {'recursos': [2]}),
])
def test_extraer_json_tolera_formatos_comunes(texto, esperado):
    assert extraer_json(texto) == esperado


@pytest.mark.parametrize('texto', ['', None, 'sin json', '{roto'])
def test_extraer_json_rechaza_lo_ilegible(texto):
    with pytest.raises(ValueError):
        extraer_json(texto)


def contexto_item(cantidad=1, alternativas=3):
    return construir_contexto(CURSO, UNIDAD, solicitud(quantity=cantidad, optionCount=alternativas), FRAGMENTOS, {})


def test_normalizar_acepta_etiquetas_juntas_y_clave_como_texto():
    alternativas = [{'texto': 'TCP', 'correcta': 'true', 'fragmentos': 'F1, F2'}, {'texto': 'UDP', 'correcta': 'false'},
                    {'texto': 'IP', 'esCorrecta': False}]
    item = {**ITEM, 'citas': [{'afirmacion': 'a', 'fragmentos': 'Fragmentos F2 y F1'}], 'alternativas': alternativas}
    recurso = normalizar_recursos({'recursos': [item]}, contexto_item())[0]
    assert recurso['citas'][0]['fragmentIds'] == ['f2', 'f1']
    clave = next(a for a in recurso['alternativas'] if a['correcta'])
    assert clave['texto'] == 'TCP' and clave['fragmentos'] == ['f1', 'f2']


def test_normalizar_acepta_etiquetas_en_varios_formatos_y_recorta_cantidad():
    item = {**ITEM, 'citas': [{'afirmacion': 'a', 'fragmentos': ['f2', '[F1]', 1, 'F7']}]}
    recursos = normalizar_recursos({'recursos': [item, item]}, contexto_item(cantidad=1))
    assert len(recursos) == 1 and recursos[0]['citas'][0]['fragmentIds'] == ['f2', 'f1']
    assert normalizar_recursos([item], contexto_item())[0]['titulo'] == 'TCP o UDP'
    assert normalizar_recursos('no es lista', contexto_item()) == []


@pytest.mark.parametrize('alternativas', [
    [{'texto': 'A', 'correcta': True}, {'texto': 'B', 'correcta': True}, {'texto': 'C'}],   # dos claves
    [{'texto': 'A'}, {'texto': 'B'}, {'texto': 'C'}],                                       # sin clave
    [{'texto': 'A', 'correcta': True}, {'texto': 'a'}, {'texto': 'B'}],                     # repetidas: faltan distractores
    'no es lista',
])
def test_normalizar_descarta_items_invalidos(alternativas):
    assert normalizar_recursos({'recursos': [{**ITEM, 'alternativas': alternativas}]}, contexto_item()) == []


def test_normalizar_descarta_recursos_sin_cita_o_sin_contenido_y_completa_titulo():
    ctx = construir_contexto(CURSO, UNIDAD, solicitud(stage='explain', resourceType='explicacion', quantity=3), FRAGMENTOS, {})
    recursos = normalizar_recursos({'recursos': [
        {'contenido': 'Texto', 'citas': [{'afirmacion': 'x', 'fragmentos': 'F1'}]},
        {'titulo': 'Sin cita', 'contenido': 'Texto', 'citas': []},
        {'titulo': 'Vacío', 'contenido': '', 'citas': [{'afirmacion': 'x', 'fragmentos': ['F1']}]},
        'basura',
    ]}, ctx)
    assert len(recursos) == 1 and recursos[0]['titulo'] == 'Explicación citada 1' and recursos[0]['alternativas'] is None


def test_sin_ejemplos_de_prueba_una_unidad_sin_material_pide_subirlo():
    gen = GeneracionService(RepoGeneraciones(), Config(), Material([]), Generador({'recursos': [ITEM]}), None,
                            ejemplos_demo=False)
    with pytest.raises(GeneracionError) as error:
        gen.generar(solicitud(), 'docente')
    assert error.value.codigo == 'SIN_MATERIAL_PROCESADO' and 'pestaña Material' in error.value.mensaje
    with pytest.raises(GeneracionError):
        gen.generar(solicitud(), None)  # sin sesión tampoco hay ejemplos preparados
