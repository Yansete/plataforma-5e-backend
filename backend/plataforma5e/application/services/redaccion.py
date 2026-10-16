"""Redacción de recursos con evidencia: arma el contexto, escribe las instrucciones para el
modelo de IA y valida lo que responde.

Se mantiene fuera de los adaptadores para que la regla «solo se acepta lo que cita
fragmentos del material» se pruebe sin red y sea la misma con cualquier proveedor.
"""
import json
import re

ETAPAS = {
    'engage': ('Enganchar', 'activar ideas previas y despertar la curiosidad'),
    'explore': ('Explorar', 'que el estudiante indague y descubra a partir de actividades'),
    'explain': ('Explicar', 'formalizar el concepto con lenguaje disciplinar preciso'),
    'elaborate': ('Elaborar', 'aplicar lo aprendido a situaciones nuevas'),
    'evaluate': ('Evaluar', 'comprobar el logro del resultado de aprendizaje'),
}

TIPOS = {
    'pregunta_detonante': ('Pregunta detonante', 'Una situación breve tomada del material y una pregunta abierta que despierte curiosidad y conecte con la experiencia del estudiante.'),
    'sondeo_diagnostico': ('Sondeo diagnóstico de ideas previas', 'Entre 4 y 6 afirmaciones de verdadero o falso para detectar ideas previas, con la respuesta y una explicación breve de cada una al final.'),
    'guia_exploracion': ('Guía de exploración', 'Objetivo, materiales y de 4 a 6 pasos de indagación que el estudiante sigue, con preguntas para registrar lo que observa.'),
    'caso_indagacion': ('Caso con preguntas de indagación', 'Un caso breve basado en el material y de 3 a 4 preguntas de indagación.'),
    'explicacion': ('Explicación citada', 'Una explicación de 3 a 5 párrafos del concepto central de la unidad; cada párrafo se apoya en una cita.'),
    'glosario': ('Glosario de la unidad', 'De 6 a 10 términos clave con su definición tomada del material, uno por línea con el formato «Término: definición».'),
    'ejercicio_aplicacion': ('Ejercicio de aplicación', 'Un ejercicio de transferencia a un contexto nuevo, con consigna, datos necesarios y criterios de logro.'),
    'item_opcion_multiple': ('Ítem de opción múltiple', 'Un enunciado con una sola respuesta correcta (clave) y distractores plausibles basados en errores conceptuales típicos. Cada alternativa lleva una retroalimentación que explica por qué es correcta o incorrecta.'),
}

DIFICULTADES = {'basica': 'básica', 'intermedia': 'intermedia', 'avanzada': 'avanzada'}
MAX_TITULO, MAX_CONTENIDO, MAX_AFIRMACION, MAX_ALTERNATIVA = 160, 8000, 600, 600


def etiqueta(indice: int) -> str:
    return f'F{indice + 1}'


def construir_contexto(curso: dict, unidad: dict, solicitud: dict, fragmentos: list[dict], documentos: dict[str, str]) -> dict:
    """Reúne todo lo que el generador necesita. Los fragmentos se rotulan F1, F2… para citarlos."""
    resultados = [o for o in unidad.get('outcomes', []) if not solicitud.get('outcomeId') or o['id'] == solicitud['outcomeId']]
    return {
        'curso': {'nombre': curso.get('name', ''), 'sumilla': curso.get('sumilla', ''), 'logro': curso.get('logro', '')},
        'unidad': {'numero': unidad.get('number'), 'titulo': unidad.get('title', ''), 'resultados': [f"{o.get('code', '')}: {o.get('text', '')}" for o in resultados]},
        'solicitud': {
            'etapa': solicitud['stage'], 'tipo': solicitud['resourceType'], 'cantidad': solicitud['quantity'],
            'dificultad': solicitud.get('difficulty', 'intermedia'), 'alternativas': solicitud.get('optionCount', 4),
            'indicaciones': solicitud.get('instructions', ''), 'publico': solicitud.get('audience', ''),
            'competencia': solicitud.get('competency', ''), 'modalidades': solicitud.get('modalities', []),
        },
        'fragmentos': [
            {'etiqueta': etiqueta(i), 'id': f['id'], 'ubicacion': f['ubicacion'], 'documento': documentos.get(f['documento_id'], ''), 'texto': f['texto']}
            for i, f in enumerate(fragmentos)
        ],
    }


def construir_instrucciones(contexto: dict) -> tuple[str, str]:
    """Devuelve (sistema, usuario): las instrucciones que recibe el modelo de IA."""
    s = contexto['solicitud']
    etapa, proposito = ETAPAS[s['etapa']]
    tipo, formato = TIPOS[s['tipo']]
    sistema = (
        f'Eres un asistente pedagógico que redacta recursos para la etapa «{etapa}» del modelo 5E ({proposito}). '
        'Escribes en español claro para docentes universitarios del Perú. '
        'No menciones el modelo 5E ni el nombre de la etapa en los títulos ni en el contenido: el docente ve el recurso tal cual. '
        'Usa SOLO la información de los FRAGMENTOS del material del docente: no agregues datos que no estén en ellos. '
        'Cada afirmación importante debe citar las etiquetas de los fragmentos que la respaldan (F1, F2…). '
        'Si los fragmentos no alcanzan para un recurso, no lo inventes: devuelve menos recursos. '
        'Genera solo texto: no incluyas imágenes, enlaces a video o audio, ni instrucciones para producir material multimedia. '
        'Responde únicamente con JSON válido, sin texto antes ni después.'
    )
    curso, unidad = contexto['curso'], contexto['unidad']
    lineas = [
        f"CURSO: {curso['nombre']}",
        f"SUMILLA: {curso['sumilla'] or 'no registrada'}",
        f"LOGRO DEL CURSO: {curso['logro'] or 'no registrado'}",
        f"UNIDAD {unidad['numero']}: {unidad['titulo']}",
        'RESULTADOS DE APRENDIZAJE: ' + ('; '.join(unidad['resultados']) or 'no registrados'),
        '',
        f"PEDIDO: {s['cantidad']} recurso(s) de tipo «{tipo}». {formato}",
        f"Dificultad: {DIFICULTADES.get(s['dificultad'], s['dificultad'])}.",
    ]
    if s['tipo'] == 'item_opcion_multiple':
        lineas.append(f"Cada ítem debe tener exactamente {s['alternativas']} alternativas: 1 correcta y {s['alternativas'] - 1} distractores.")
    if s['publico']:
        lineas.append(f"Público: {s['publico']}.")
    if s['competencia']:
        lineas.append(f"Competencia a desarrollar: {s['competencia']}.")
    if s['indicaciones']:
        lineas.append(f"Indicaciones del docente: {s['indicaciones']}")
    lineas += [
        '',
        'FORMATO DE RESPUESTA (JSON):',
        '{"recursos": [{"titulo": "texto corto", "contenido": "texto completo del recurso (en ítems, el enunciado)",',
        ' "citas": [{"afirmacion": "idea del recurso", "fragmentos": ["F1"]}],',
        ' "alternativas": [{"texto": "...", "correcta": true, "retroalimentacion": "...", "fragmentos": ["F2"]}]}]}',
        '«alternativas» solo se llena en ítems de opción múltiple; en los demás tipos usa [].',
        '',
        'FRAGMENTOS DEL MATERIAL:',
    ]
    for f in contexto['fragmentos']:
        origen = ', '.join(x for x in (f['documento'], f['ubicacion']) if x)
        lineas += [f"[{f['etiqueta']}] ({origen})", f['texto'], '']
    return sistema, '\n'.join(lineas).strip()


def extraer_json(texto: str):
    """Lee el JSON de la respuesta del modelo, aunque venga entre ``` o con texto alrededor."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError('La respuesta del modelo está vacía.')
    limpio = re.sub(r'^```(?:json)?\s*|\s*```$', '', texto.strip())
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        pass
    inicio, fin = limpio.find('{'), limpio.rfind('}')
    if inicio != -1 and fin > inicio:
        try:
            return json.loads(limpio[inicio:fin + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError('La respuesta del modelo no es JSON válido.')


def _texto(valor, maximo: int) -> str:
    return ' '.join(valor.split())[:maximo] if isinstance(valor, str) else ''


def _bloque(valor, maximo: int) -> str:
    """Como _texto, pero conserva los saltos de línea del contenido."""
    if not isinstance(valor, str):
        return ''
    lineas = [' '.join(linea.split()) for linea in valor.replace('\r', '').split('\n')]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lineas)).strip()[:maximo]


def _ids(valor, etiquetas: dict[str, str]) -> list[str]:
    """Convierte ['F1', 'f2', '[F3]', 4, 'F1, F5'] en ids reales de fragmentos; descarta lo que no existe."""
    if isinstance(valor, (str, int)) and not isinstance(valor, bool):
        valor = [valor]
    if not isinstance(valor, list):
        return []
    ids = []
    for v in valor:
        if isinstance(v, bool):
            continue
        numeros = [str(v)] if isinstance(v, int) else re.findall(r'\d+', str(v))
        for numero in numeros:
            clave = f'F{int(numero)}'
            if clave in etiquetas and etiquetas[clave] not in ids:
                ids.append(etiquetas[clave])
    return ids


def _es_correcta(alternativa: dict) -> bool:
    """La clave puede venir como booleano o como texto («true», «sí»), según el modelo."""
    valor = next((alternativa[k] for k in ('correcta', 'esCorrecta', 'correct') if k in alternativa), False)
    if isinstance(valor, str):
        return valor.strip().lower() in ('true', 'sí', 'si', 'verdadero', 'correcta')
    return valor is True


def normalizar_recursos(datos, contexto: dict) -> list[dict]:
    """Valida la respuesta del generador y la deja lista para el docente.

    Se descarta todo recurso sin al menos una cita válida (no se acepta contenido sin evidencia)
    y todo ítem que no tenga exactamente una clave y la cantidad pedida de alternativas.
    """
    etiquetas = {f['etiqueta']: f['id'] for f in contexto['fragmentos']}
    s = contexto['solicitud']
    lista = datos.get('recursos') if isinstance(datos, dict) else datos
    if not isinstance(lista, list):
        return []
    recursos = []
    for crudo in lista:
        if len(recursos) >= s['cantidad'] or not isinstance(crudo, dict):
            continue
        contenido = _bloque(crudo.get('contenido'), MAX_CONTENIDO)
        citas = []
        for c in crudo.get('citas') or []:
            if isinstance(c, dict):
                ids = _ids(c.get('fragmentos'), etiquetas)
                afirmacion = _texto(c.get('afirmacion'), MAX_AFIRMACION)
                if ids and afirmacion:
                    citas.append({'claim': afirmacion, 'fragmentIds': ids})
        if not contenido or not citas:
            continue
        titulo = _texto(crudo.get('titulo'), MAX_TITULO) or f"{TIPOS[s['tipo']][0]} {len(recursos) + 1}"
        alternativas = None
        if s['tipo'] == 'item_opcion_multiple':
            alternativas = _alternativas(crudo.get('alternativas'), etiquetas, citas, s['alternativas'])
            if alternativas is None:
                continue
        recursos.append({'titulo': titulo, 'contenido': contenido, 'citas': citas, 'alternativas': alternativas})
    return recursos


def _alternativas(lista, etiquetas: dict[str, str], citas: list[dict], cantidad: int) -> list[dict] | None:
    if not isinstance(lista, list):
        return None
    respaldo = citas[0]['fragmentIds']
    vistas, clave, distractores = set(), None, []
    for a in lista:
        if not isinstance(a, dict):
            continue
        texto = _texto(a.get('texto'), MAX_ALTERNATIVA)
        if not texto or texto.casefold() in vistas:
            continue
        vistas.add(texto.casefold())
        opcion = {
            'texto': texto,
            'correcta': _es_correcta(a),
            'retroalimentacion': _texto(a.get('retroalimentacion'), MAX_ALTERNATIVA) or 'Revisa el fragmento citado del material.',
            'fragmentos': _ids(a.get('fragmentos'), etiquetas) or respaldo,
        }
        if opcion['correcta']:
            if clave is not None:
                return None  # dos claves: el ítem no es válido
            clave = opcion
        else:
            distractores.append(opcion)
    if clave is None or len(distractores) < cantidad - 1:
        return None
    return [clave, *distractores[:cantidad - 1]]
