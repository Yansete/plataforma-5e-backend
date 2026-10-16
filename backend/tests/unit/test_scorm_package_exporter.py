"""Paquete SCORM 1.2 para Chamilo: manifiesto en la raíz, un SCO por recurso en orden 5E y sin distractores descartados."""
import io
import xml.etree.ElementTree as ET
import zipfile

from platform5e.infrastructure.exporters.scorm_package_exporter import ScormPackageExporter

NS = {"cp": "http://www.imsproject.org/xsd/imscp_rootv1p1p2", "adlcp": "http://www.adlnet.org/xsd/adlcp_rootv1p2"}
COURSE = {"code": "RED-301"}
UNIT = {"number": 2, "title": "Capa de transporte"}
QUESTION = {
    "id": "r2", "stage": "evaluate", "title": "TCP o UDP", "createdAt": "2026-10-10T10:00", "body": "¿Cuál tiene menos retardo?",
    "options": [
        {"id": "a", "text": "UDP", "isCorrect": True, "feedback": "No espera confirmaciones.", "decision": "pendiente"},
        {"id": "b", "text": "TCP <confiable>", "isCorrect": False, "feedback": "Retransmite.", "decision": "aceptado"},
        {"id": "c", "text": "ICMP", "isCorrect": False, "feedback": "", "decision": "descartado"},
    ],
    "evidence": [{"documentName": "protocolos.pdf", "location": "p. 3"}],
}
TRIGGER = {"id": "r1", "stage": "engage", "title": "¿Por qué se corta una llamada?", "createdAt": "2026-10-10T09:00",
           "body": "Piensa en tu última videollamada.", "options": None, "evidence": []}


def package(resources):
    exported = ScormPackageExporter().export(resources, COURSE, UNIT)
    return exported, zipfile.ZipFile(io.BytesIO(exported.content))


def test_manifest_at_root_with_one_sco_per_resource_in_5e_order():
    exported, archive = package([QUESTION, TRIGGER])
    assert exported.file_name == "red-301-unidad-2-scorm.zip" and exported.media_type == "application/zip"
    assert archive.namelist()[0] == "imsmanifest.xml"
    root = ET.fromstring(archive.read("imsmanifest.xml"))
    default = root.find("cp:organizations", NS).get("default")
    items = root.findall(f"cp:organizations/cp:organization[@identifier='{default}']/cp:item", NS)
    resources = {r.get("identifier"): r for r in root.findall("cp:resources/cp:resource", NS)}
    assert [i.find("cp:title", NS).text for i in items] == ["¿Por qué se corta una llamada?", "TCP o UDP"]  # engage antes que evaluate
    for item in items:
        sco = resources[item.get("identifierref")]
        assert sco.get(f"{{{NS['adlcp']}}}scormtype") == "sco" and sco.get("href") in archive.namelist()
    for resource in resources.values():
        assert all(f.get("href") in archive.namelist() for f in resource.findall("cp:file", NS))


def test_question_page_grades_and_leaves_out_discarded_distractors():
    _, archive = package([QUESTION])
    page = archive.read("sco/01.html").decode()
    assert 'data-kind="question"' in page and "ICMP" not in page
    assert "TCP &lt;confiable&gt;" in page and page.count('data-correct="true"') == 1
    assert "protocolos.pdf, p. 3" in page


def test_same_resources_give_the_same_file():
    assert package([QUESTION, TRIGGER])[0].content == package([QUESTION, TRIGGER])[0].content
