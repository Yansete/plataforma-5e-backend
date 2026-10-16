"""Controles del validador: acepta lo que Moodle importó y rechaza lo que Moodle perdería."""

from __future__ import annotations

from tests.support.moodle_xml_validator import MUESTRA_VERIFICADA, leer_preguntas, validar

MUESTRA = MUESTRA_VERIFICADA.read_text(encoding="utf-8")


def test_acepta_la_muestra_que_se_importo_en_moodle_en_sp_003():
    assert validar(MUESTRA) == []
    assert len(leer_preguntas(MUESTRA)) == 2


def test_rechaza_dos_claves():
    roto = MUESTRA.replace('<answer fraction="0" format="html">', '<answer fraction="100" format="html">', 1)
    assert any("exactamente una alternativa" in e for e in validar(roto))


def test_rechaza_una_alternativa_sin_retroalimentacion():
    inicio = MUESTRA.index("<feedback", MUESTRA.index('<answer fraction="0"'))
    fin = MUESTRA.index("</feedback>", inicio) + len("</feedback>")
    roto = MUESTRA[:inicio] + MUESTRA[fin:]
    assert any("no tiene retroalimentación" in e for e in validar(roto))


def test_rechaza_menos_de_tres_alternativas():
    pregunta = MUESTRA.index('<question type="multichoice">')
    respuestas = [i for i in range(len(MUESTRA)) if MUESTRA.startswith('<answer fraction="0"', i) and i > pregunta]
    inicio = respuestas[0]
    fin = MUESTRA.index("</answer>", respuestas[1]) + len("</answer>")
    roto = MUESTRA[:inicio] + MUESTRA[fin:]
    assert any("alternativas; deben ser entre 3 y 5" in e for e in validar(roto))


def test_rechaza_tipos_no_verificados_y_xml_mal_formado():
    assert any("no verificado" in e for e in validar(MUESTRA.replace('type="multichoice"', 'type="essay"', 1)))
    assert validar("<quiz><question>")[0].startswith("El XML no está bien formado")
    assert validar("<otro/>") == ["La raíz debe ser <quiz> y es <otro>."]