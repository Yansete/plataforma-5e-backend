"""Exportación SCORM por HTTP: solo recursos aprobados, archivo .zip descargable y registro en el historial."""
import io
import json
import zipfile

import httpx

MATERIAL = ('El protocolo TCP es orientado a la conexión y garantiza una entrega confiable. '
            'El protocolo UDP no confirma la entrega; por eso es más rápido e introduce menos retardo.').encode()


def test_exports_approved_resources_as_scorm(servidor):
    with httpx.Client(base_url=servidor, timeout=60) as api:
        token = api.post('/api/v1/cuentas', json={'name': 'Eva Ruiz', 'email': 'eva@correo.pe', 'password': 'clave-segura-1'}).json()['token']
        h = {'Authorization': f'Bearer {token}'}
        unidad = api.post('/api/v1/cursos', headers=h, json={'code': 'RED-301', 'name': 'Redes', 'term': '2026-II',
                          'units': [{'title': 'Transporte', 'outcomes': [{'text': 'Distingue TCP y UDP'}]}]}).json()['units'][0]
        contexto = {'unitId': unidad['id'], 'outcomeIds': [unidad['outcomes'][0]['id']],
                    'documentType': 'Separata o apuntes de clase', 'usePermission': True}
        documento = api.post('/api/v1/documentos', headers=h, files={'file': ('tcp.txt', MATERIAL)},
                             data={'contexto': json.dumps(contexto)}).json()
        api.post(f"/api/v1/documentos/{documento['id']}/procesar", headers=h)
        recurso = api.post('/api/v1/generaciones', headers=h, json={
            'unidad_id': unidad['id'], 'etapa_5e': 'evaluate', 'tipo_recurso': 'item_opcion_multiple', 'cantidad': 1,
            'alternativas': 4, 'modalidades': ['Textual']}).json()['resources'][0]
        exportar = f"/api/v1/units/{unidad['id']}/exports"

        assert api.post(exportar, json={'format': 'scorm_zip'}).status_code == 401
        assert api.post(exportar, headers=h, json={'format': 'scorm_zip'}).status_code == 422  # todavía no hay aprobados

        opciones = [{'id': o['id'], 'text': o['text'], 'feedback': o['feedback'],
                     'decision': 'pendiente' if o['isCorrect'] else 'aceptado'} for o in recurso['options']]
        aprobado = api.put(f"/api/v1/unidades/{unidad['id']}/recursos/{recurso['id']}", headers=h,
                           json={'title': recurso['title'], 'body': recurso['body'], 'status': 'aprobado', 'options': opciones})
        assert aprobado.status_code == 200

        archivo = api.post(exportar, headers=h, json={'format': 'scorm_zip', 'resourceIds': [recurso['id']]})
        assert archivo.status_code == 200 and archivo.headers['content-type'] == 'application/zip'
        assert 'red-301-unidad-1-scorm.zip' in archivo.headers['content-disposition']
        assert zipfile.ZipFile(io.BytesIO(archivo.content)).namelist()[0] == 'imsmanifest.xml'
        historial = api.get(f"/api/v1/unidades/{unidad['id']}/descargas", headers=h).json()
        assert [d['format'] for d in historial] == ['scorm_zip']
