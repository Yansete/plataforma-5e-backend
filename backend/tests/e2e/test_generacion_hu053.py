"""HU-053 / EN-006: contrato, persistencia y errores contra el servidor real."""
import httpx
import pytest

SOLICITUD = {'unidad_id': 'u2', 'resultado_aprendizaje_id': None, 'etapa_5e': 'explore', 'tipo_recurso': 'guia_exploracion', 'cantidad': 1, 'dificultad': 'intermedia', 'alternativas': 4, 'top_k': 10, 'umbral_evidencia': .6, 'indicaciones': 'Contexto de prueba', 'publico_objetivo': 'Tercer ciclo', 'competencia': 'Pensamiento crítico', 'modalidades': ['Textual']}

def test_http_real_respeta_solicitud_conserva_generaciones_y_evidencia(servidor):
    with httpx.Client(base_url=servidor, timeout=10) as api:
        primera = api.post('/api/v1/generaciones', json=SOLICITUD)
        assert primera.status_code == 200, primera.text
        data = primera.json()
        assert data['mode'] == 'api_demo'
        assert len(data['resources']) == 1
        resource = data['resources'][0]
        assert (resource['unitId'], resource['stage'], resource['type']) == ('u2', 'explore', 'guia_exploracion')
        assert resource['status'] == 'pendiente' and resource['decidedAt'] is None
        assert data['request']['audience'] == 'Tercer ciclo'
        assert data['request']['competency'] == 'Pensamiento crítico'
        assert data['request']['modalities'] == ['Textual']
        fragments = {f['id']: f for f in data['fragments']}
        documents = {d['id'] for d in data['documents']}
        for c in resource['citations']:
            for fid in c['fragmentIds']:
                assert fid in fragments
                assert fragments[fid]['unitId'] == 'u2'
                assert fragments[fid]['documentId'] in documents
                assert fragments[fid]['text'] and fragments[fid]['location']
        second = api.post('/api/v1/generaciones', json={**SOLICITUD, 'etapa_5e': 'evaluate', 'tipo_recurso': 'item_opcion_multiple', 'cantidad': 2}).json()
        assert len(second['resources']) == 2
        assert all(o['decision'] == 'pendiente' for r in second['resources'] for o in r['options'])
        assert second['request']['id'] != data['request']['id']
        assert api.get(f'/api/v1/generaciones/{data["request"]["id"]}').json() == data
        assert api.get(f'/api/v1/generaciones/{second["request"]["id"]}').json() == second

@pytest.mark.parametrize('cantidad', [0, 6, 2.5])
def test_cantidad_invalida_devuelve_422(servidor, cantidad):
    response = httpx.post(f'{servidor}/api/v1/generaciones', json={**SOLICITUD, 'cantidad': cantidad})
    assert response.status_code == 422
    assert response.json()['error']['codigo'] == 'PARAMETROS_INVALIDOS'

@pytest.mark.parametrize('modalidades', [['Multimedia'], ['Textual', 'Gamificado']])
def test_solo_texto_rechaza_otras_modalidades(servidor, modalidades):
    response = httpx.post(f'{servidor}/api/v1/generaciones', json={**SOLICITUD, 'modalidades': modalidades})
    assert response.status_code == 422
    assert response.json()['error']['codigo'] == 'PARAMETROS_INVALIDOS'

@pytest.mark.parametrize('patch,code', [({'unidad_id': 'unidad-nueva'}, 'SIN_MATERIAL_PROCESADO'), ({'etapa_5e': 'explore', 'tipo_recurso': 'item_opcion_multiple'}, 'EVIDENCIA_INSUFICIENTE'), ({'resultado_aprendizaje_id': 'ra-3-1'}, 'RESULTADO_INVALIDO')])
def test_rechazos_estandarizados_sin_recursos(servidor, patch, code):
    response = httpx.post(f'{servidor}/api/v1/generaciones', json={**SOLICITUD, **patch})
    assert response.status_code == 400
    assert response.json()['error']['codigo'] == code
    assert 'resources' not in response.json()

def test_generacion_inexistente_devuelve_404_y_openapi(servidor):
    response = httpx.get(f'{servidor}/api/v1/generaciones/no-existe')
    assert response.status_code == 404
    assert response.json()['error']['codigo'] == 'GENERACION_NO_ENCONTRADA'
    spec = httpx.get(f'{servidor}/openapi.json').json()
    assert '/api/v1/generaciones' in spec['paths']
    assert 'SolicitudIntegrada' in spec['components']['schemas']
