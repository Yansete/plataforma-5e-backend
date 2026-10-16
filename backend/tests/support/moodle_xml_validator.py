"""Validador del Moodle XML que exporta la plataforma (TA-007, indicadores I17 e I19).

Las reglas salen de la muestra que se importó con éxito en Moodle durante SP-003
(tests/data/muestra_moodle_verificada.xml): si lo exportado tiene la misma estructura y
cumple las reglas de un ítem de opción múltiple, Moodle lo importa sin pérdidas.

Uso desde la terminal:
    python -m tests.support.moodle_xml_validator salida_demo/archivo.xml
"""

from __future__ import annotations

from dataclasses import dataclass
import html
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET

# Búsqueda dinámica de la muestra para compatibilidad sin importar la ruta de ejecución
_POSIBLES_RUTAS = [
    Path(__file__).resolve().parents[1] / "fixtures" / "verified_moodle_sample.xml",
    Path(__file__).resolve().parents[2] / "fixtures" / "verified_moodle_sample.xml",
    Path(__file__).resolve().parents[1] / "data" / "muestra_moodle_verificada.xml",
    Path(__file__).resolve().parents[2] / "data" / "muestra_moodle_verificada.xml",
]

MUESTRA_VERIFICADA = next((p for p in _POSIBLES_RUTAS if p.is_file()), _POSIBLES_RUTAS[0])

TIPOS_ADMITIDOS = {"category", "multichoice"}
MIN_ALTERNATIVAS, MAX_ALTERNATIVAS = 3, 5


@dataclass(frozen=True)
class PreguntaExportada:
    """Lo que el docente verá en Moodle, sin etiquetas HTML."""

    nombre: str
    enunciado: str
    retroalimentacion_general: str
    alternativas: list[tuple[str, str, str]]  # (texto, fracción, retroalimentación)


def texto_plano(valor: str | None) -> str:
    sin_etiquetas = re.sub(r"<[^>]+>", " ", valor or "")
    return re.sub(r"\s+", " ", html.unescape(sin_etiquetas)).strip()


def _etiquetas_hijas(pregunta: ET.Element) -> set[str]:
    return {hijo.tag for hijo in pregunta}


def etiquetas_de_referencia() -> set[str]:
    """Etiquetas de un ítem de opción múltiple en la muestra que Moodle importó bien."""
    if not MUESTRA_VERIFICADA.is_file():
        raise FileNotFoundError(
            f"No se encontró el archivo de referencia en: {MUESTRA_VERIFICADA}"
        )
    raiz = ET.parse(MUESTRA_VERIFICADA).getroot()
    pregunta = raiz.find("question[@type='multichoice']")
    assert pregunta is not None, "la muestra verificada no tiene ítems de opción múltiple"
    return _etiquetas_hijas(pregunta)


def validar(contenido: bytes | str) -> list[str]:
    """Devuelve la lista de problemas encontrados. Lista vacía = el archivo es importable."""
    errores: list[str] = []
    try:
        raiz = ET.fromstring(contenido)
    except ET.ParseError as error:
        return [f"El XML no está bien formado: {error}"]

    if raiz.tag != "quiz":
        return [f"La raíz debe ser <quiz> y es <{raiz.tag}>."]

    preguntas = raiz.findall("question")
    items = [p for p in preguntas if p.get("type") == "multichoice"]
    if not items:
        errores.append("No hay ninguna pregunta de opción múltiple.")

    referencia = etiquetas_de_referencia()
    for posicion, pregunta in enumerate(preguntas, start=1):
        tipo = pregunta.get("type")
        donde = f"Pregunta {posicion}"
        if tipo not in TIPOS_ADMITIDOS:
            errores.append(
                f"{donde}: tipo «{tipo}» no verificado en Moodle (se admiten {sorted(TIPOS_ADMITIDOS)})."
            )
            continue
        if tipo == "category":
            if not (pregunta.findtext("category/text") or "").strip():
                errores.append(f"{donde}: la categoría no tiene nombre.")
            continue

        nombre = (pregunta.findtext("name/text") or "").strip()
        donde = f"{donde} «{nombre or 'sin nombre'}»"
        if not nombre:
            errores.append(f"{donde}: falta el nombre.")

        faltan = referencia - _etiquetas_hijas(pregunta)
        if faltan:
            errores.append(f"{donde}: faltan etiquetas que tenía la muestra verificada: {sorted(faltan)}.")

        enunciado = pregunta.find("questiontext")
        if (
            enunciado is None
            or enunciado.get("format") != "html"
            or not texto_plano(enunciado.findtext("text"))
        ):
            errores.append(f"{donde}: el enunciado debe existir, tener texto y formato html.")

        if (pregunta.findtext("single") or "").strip() != "true":
            errores.append(f"{donde}: <single> debe ser true (una sola respuesta correcta).")

        respuestas = pregunta.findall("answer")
        if not MIN_ALTERNATIVAS <= len(respuestas) <= MAX_ALTERNATIVAS:
            errores.append(
                f"{donde}: tiene {len(respuestas)} alternativas; deben ser entre {MIN_ALTERNATIVAS} y {MAX_ALTERNATIVAS}."
            )

        fracciones = [r.get("fraction") for r in respuestas]
        if fracciones.count("100") != 1:
            errores.append(
                f"{donde}: debe haber exactamente una alternativa con fraction=\"100\" y hay {fracciones.count('100')}."
            )
        otras = [f for f in fracciones if f != "100"]
        if any(f != "0" for f in otras):
            errores.append(f"{donde}: las alternativas incorrectas deben tener fraction=\"0\" y hay {otras}.")

        textos = [texto_plano(r.findtext("text")) for r in respuestas]
        if any(not t for t in textos):
            errores.append(f"{donde}: hay alternativas sin texto.")
        if len(set(textos)) != len(textos):
            errores.append(f"{donde}: hay alternativas repetidas.")
        for letra, respuesta in zip("ABCDE", respuestas):
            if not texto_plano(respuesta.findtext("feedback/text")):
                errores.append(f"{donde}: la alternativa {letra} no tiene retroalimentación (I19).")
    return errores


def leer_preguntas(contenido: bytes | str) -> list[PreguntaExportada]:
    """Extrae el contenido de cada ítem tal como lo mostrará Moodle."""
    raiz = ET.fromstring(contenido)
    return [
        PreguntaExportada(
            nombre=(p.findtext("name/text") or "").strip(),
            enunciado=texto_plano(p.findtext("questiontext/text")),
            retroalimentacion_general=texto_plano(p.findtext("generalfeedback/text")),
            alternativas=[
                (
                    texto_plano(r.findtext("text")),
                    r.get("fraction") or "",
                    texto_plano(r.findtext("feedback/text")),
                )
                for r in p.findall("answer")
            ],
        )
        for p in raiz.findall("question[@type='multichoice']")
    ]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m tests.support.moodle_xml_validator <archivo.xml>")
    problemas = validar(Path(sys.argv[1]).read_bytes())
    if problemas:
        print("NO importable:")
        for problema in problemas:
            print(" -", problema)
        sys.exit(1)
    print("OK: el archivo cumple la estructura verificada en Moodle.")