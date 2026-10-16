"""
Plantilla y adaptador Moodle XML para exportación de recursos formativos (ADR-005).
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from platform5e.application.ports.outbound.resource_exporter_port import ResourceExporterPort
from platform5e.domain.review.learning_resource import LearningResourceDomain


def _wrap_cdata(text: str) -> str:
    """Envuelve texto en un bloque CDATA de XML escapando secuencias de cierre."""
    return text.replace("]]>", "]]]]><![CDATA[>")


def generate_moodle_xml(approved_resources: list[LearningResourceDomain]) -> str:
    """Genera la estructura XML completa en formato Moodle Quiz a partir de recursos aprobados."""
    xml_lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<quiz>",
        '  <question type="category"><category><text>$course$/top/Por defecto en Curso</text></category><info format="html"><text></text></info><idnumber></idnumber></question>',
    ]

    for resource in approved_resources:
        active_options = [
            opt
            for opt in resource.alternatives
            if getattr(opt, "review_status", getattr(opt, "estado", "")) != "descartado"
        ]
        xml_lines.append('  <question type="multichoice">')
        xml_lines.append(f"    <name><text>{escape(resource.title)}</text></name>")
        xml_lines.append(
            f'    <questiontext format="html"><text><![CDATA[{_wrap_cdata(resource.prompt)}]]></text></questiontext>'
        )
        xml_lines.append(
            f'    <generalfeedback format="html"><text><![CDATA[{_wrap_cdata(resource.feedback)}]]></text></generalfeedback>'
        )
        xml_lines.append("    <defaultgrade>1.0000000</defaultgrade>")
        xml_lines.append("    <penalty>0.3333333</penalty>")
        xml_lines.append("    <hidden>0</hidden>")
        xml_lines.append("    <idnumber></idnumber>")
        xml_lines.append("    <single>true</single>")
        xml_lines.append("    <shuffleanswers>true</shuffleanswers>")
        xml_lines.append("    <answernumbering>abc</answernumbering>")
        xml_lines.append("    <showstandardinstruction>0</showstandardinstruction>")
        xml_lines.append(
            '    <correctfeedback format="html"><text><![CDATA[<p>Respuesta correcta.</p>]]></text></correctfeedback>'
        )
        xml_lines.append(
            '    <partiallycorrectfeedback format="html"><text><![CDATA[<p>Respuesta parcialmente correcta.</p>]]></text></partiallycorrectfeedback>'
        )
        xml_lines.append(
            '    <incorrectfeedback format="html"><text><![CDATA[<p>Respuesta incorrecta.</p>]]></text></incorrectfeedback>'
        )
        xml_lines.append("    <shownumcorrect/>")

        for opt in active_options:
            fraction = "100" if opt.is_correct else "0"
            xml_lines.append(f'    <answer fraction="{fraction}" format="html">')
            xml_lines.append(f"      <text><![CDATA[{_wrap_cdata(opt.text)}]]></text>")
            xml_lines.append(
                f"      <feedback format=\"html\"><text><![CDATA[{_wrap_cdata(opt.justification)}]]></text></feedback>"
            )
            xml_lines.append("    </answer>")
        xml_lines.append("  </question>")

    xml_lines.append("</quiz>")
    return "\n".join(xml_lines)


class MoodleXMLExporter(ResourceExporterPort):
    """Adaptador de infraestructura para exportar recursos de dominio a formato Moodle XML."""

    def export(self, resources: list[LearningResourceDomain]) -> str:
        """Serializa la lista de recursos de dominio aprobados al esquema XML."""
        return generate_moodle_xml(resources)