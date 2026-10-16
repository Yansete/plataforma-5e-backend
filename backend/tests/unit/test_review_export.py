"""
Regresión de decisiones, revisión y XML fiel al contenido aprobado.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

import pytest

from platform5e.application.services.review.learning_resource_service import LearningResourceService as ResourceReviewService
from platform5e.application.use_cases.export.export_approved_resources import ExportApprovedResourcesUseCase
from platform5e.domain.shared.errors import EntityNotFoundError, NoApprovedResourcesError
from platform5e.infrastructure.exporters.moodle_xml_exporter import MoodleXMLExporter
from tests.unit.test_application_services import MockLearningResourceRepository, _make_resource_item


def test_exportacion_conserva_titulo_html_y_delimitadores():
    resource = _make_resource_item()
    resource.title = "Pilas & colas <comparación>"
    resource.prompt = "<p>Contenido con ]]> y &</p>"
    resource.alternatives[0].text = "O(n) & O(1) ]]>"
    repo = MockLearningResourceRepository([resource])
    service = ResourceReviewService(repo)
    for letter in "ABC":
        service.decide_option(resource.id, letter, "aceptar")
    service.approve_resource(resource.id)

    xml_output = ExportApprovedResourcesUseCase(service, MoodleXMLExporter()).execute("moodle_xml")
    question_node = ET.fromstring(xml_output).find("question[@type='multichoice']")
    assert question_node.findtext("name/text") == resource.title
    assert question_node.findtext("questiontext/text") == resource.prompt
    assert question_node.findtext("answer/text") == resource.alternatives[0].text


@pytest.mark.parametrize("invalid_decision", ["aprobar", "", "ACEPTAR"])
def test_decision_invalida_no_modifica_ni_guarda(invalid_decision: str):
    repo = MockLearningResourceRepository([_make_resource_item()])
    service = ResourceReviewService(repo)
    with pytest.raises(ValueError, match="Decisión inválida"):
        service.decide_option("rec-1", "A", invalid_decision)
    assert repo.save_count == 0
    assert repo.resources["rec-1"].alternativas[0].review_status == "pendiente"


def test_exportacion_sin_aprobados_y_formato_invalido():
    exporter_use_case = ExportApprovedResourcesUseCase(
        ResourceReviewService(MockLearningResourceRepository([_make_resource_item()])), MoodleXMLExporter()
    )
    with pytest.raises(NoApprovedResourcesError):
        exporter_use_case.execute("moodle_xml")
    with pytest.raises(ValueError, match="Formato no soportado"):
        exporter_use_case.execute("scorm")


def test_obtener_recurso_inexistente_es_error_de_dominio():
    with pytest.raises(EntityNotFoundError):
        ResourceReviewService(MockLearningResourceRepository([])).get_resource("ausente")


def test_el_dominio_no_inventa_evidencia():
    first_res, second_res = _make_resource_item(), _make_resource_item()
    assert first_res.citations == []
    assert first_res.alternativas[0].fragmentos_origen == []
    first_res.citations.append({"fragment_id": "real"})
    first_res.alternativas[0].fragmentos_origen.append("real")
    assert second_res.citations == []
    assert second_res.alternativas[0].fragmentos_origen == []