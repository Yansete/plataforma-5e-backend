"""
Pruebas unitarias de la capa de aplicación con puertos falsos en memoria.

No usan base de datos ni HTTP: cada servicio recibe un repositorio falso que cumple su
puerto. Así se comprueba la regla de negocio aislada de los adaptadores (arquitectura
hexagonal, EN-004).
"""

from __future__ import annotations

from copy import deepcopy
import io
import time
from typing import Any
import zipfile

import pytest

from platform5e.application.ports.outbound.generation_repository_port import GenerationRepositoryPort
from platform5e.application.ports.outbound.resource_repository_port import LearningResourceRepositoryPort
from platform5e.application.ports.outbound.teacher_repository_port import TeacherRepositoryPort
from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.generation.generation_service import GenerationService
from platform5e.application.services.review.learning_resource_service import LearningResourceService as ResourceReviewService
from platform5e.domain.accounts.teacher_account import AccountConfigurationError
from platform5e.domain.generation.errors import GenerationError
from platform5e.domain.review.learning_resource import LearningOptionDomain, LearningResourceDomain


# --------------------------------------------------------------------------- recursos

class MockLearningResourceRepository(LearningResourceRepositoryPort):
    def __init__(self, resources: list[LearningResourceDomain]) -> None:
        self.resources = {r.id: r for r in resources}
        self.save_count = 0

    def get_all(self) -> list[LearningResourceDomain]:
        return list(self.resources.values())

    def get_by_id(self, resource_id: str) -> LearningResourceDomain | None:
        return self.resources.get(resource_id)

    def save(self, resource: LearningResourceDomain) -> LearningResourceDomain:
        self.save_count += 1
        self.resources[resource.id] = resource
        return resource

    def reset_demo(self) -> list[LearningResourceDomain]:
        return list(self.resources.values())


def _make_resource_item(res_id: str = "rec-1") -> LearningResourceDomain:
    return LearningResourceDomain(
        id=res_id,
        title="Tope de la pila",
        prompt="¿Qué elemento queda en el tope?",
        feedback="La pila es LIFO.",
        alternatives=[
            LearningOptionDomain("A", "7", True, "Último en entrar"),
            LearningOptionDomain("B", "3", False, "Primero en entrar"),
            LearningOptionDomain("C", "5", False, "Elemento intermedio"),
        ],
    )


def test_decisiones_sobre_alternativas():
    repo = MockLearningResourceRepository([_make_resource_item()])
    service = ResourceReviewService(repo)
    service.decide_option("rec-1", "A", "aceptar")
    service.decide_option("rec-1", "B", "descartar")
    resource = service.decide_option("rec-1", "C", "editar", "6")
    statuses = {opt.letter: (opt.review_status, opt.text) for opt in resource.alternatives}
    assert statuses == {"A": ("aceptado", "7"), "B": ("descartado", "3"), "C": ("editado", "6")}
    assert repo.save_count == 3


def test_editar_sin_texto_conserva_el_texto():
    service = ResourceReviewService(MockLearningResourceRepository([_make_resource_item()]))
    resource = service.decide_option("rec-1", "C", "editar")
    assert resource.alternatives[2].text == "5"


def test_recurso_o_alternativa_inexistente():
    service = ResourceReviewService(MockLearningResourceRepository([_make_resource_item()]))
    with pytest.raises(ValueError, match="Recurso no encontrado"):
        service.decide_option("no-existe", "A", "aceptar")
    with pytest.raises(ValueError, match="Alternativa no encontrada"):
        service.decide_option("rec-1", "Z", "aceptar")
    with pytest.raises(ValueError, match="Recurso no encontrado"):
        service.approve_resource("no-existe")


def test_no_se_aprueba_con_alternativas_pendientes():
    service = ResourceReviewService(MockLearningResourceRepository([_make_resource_item()]))
    service.decide_option("rec-1", "A", "aceptar")
    with pytest.raises(ValueError, match="aprobacion_bloqueada"):
        service.approve_resource("rec-1")
    assert service.get_approved_for_export() == []


def test_aprobar_y_listar_solo_aprobados():
    repo = MockLearningResourceRepository([_make_resource_item("rec-1"), _make_resource_item("rec-2")])
    service = ResourceReviewService(repo)
    for letter in "ABC":
        service.decide_option("rec-1", letter, "aceptar")
    assert service.approve_resource("rec-1").review_status == "aprobado"
    assert [r.id for r in service.get_approved_for_export()] == ["rec-1"]
    assert service.get_resource("rec-2").review_status == "borrador"
    assert len(service.generate_or_reset_resources()) == 2


# --------------------------------------------------------------------------- generación

DEMO_CATALOG = {
    "notice": "Datos ficticios de demostración.",
    "units": [{"id": "u2", "outcomes": [{"id": "ra-1"}]}],
    "documents": [{"id": "doc-1", "fileName": "separata.pdf", "unitId": "u2"}],
    "fragments": [
        {"id": "f-1", "documentId": "doc-1", "unitId": "u2", "location": "p. 1", "text": "Una pila es LIFO."},
        {"id": "f-2", "documentId": "doc-1", "unitId": "u2", "location": "p. 2", "text": "Apilar y desapilar."},
    ],
    "examples": [
        {
            "exampleId": "ex-guia",
            "unitId": "u2",
            "outcomeId": "ra-1",
            "stage": "explore",
            "type": "guia_exploracion",
            "title": "Guía de pilas",
            "body": "Explora la pila.",
            "options": None,
            "citations": [{"claim": "Definición", "fragmentIds": ["f-1"]}],
        },
        {
            "exampleId": "ex-item",
            "unitId": "u2",
            "outcomeId": "ra-1",
            "stage": "evaluate",
            "type": "item_opcion_multiple",
            "title": "Tope",
            "body": "¿Qué queda en el tope?",
            "citations": [{"claim": "LIFO", "fragmentIds": ["f-1"]}],
            "options": [
                {"id": "o1", "text": "7", "isCorrect": True, "feedback": "Bien", "sourceFragmentIds": ["f-2"]},
                {"id": "o2", "text": "3", "isCorrect": False, "feedback": "No", "sourceFragmentIds": ["f-2"]},
                {"id": "o3", "text": "5", "isCorrect": False, "feedback": "No", "sourceFragmentIds": []},
                {"id": "o4", "text": "1", "isCorrect": False, "feedback": "No", "sourceFragmentIds": []},
            ],
        },
    ],
}


class MockGenerationRepository(GenerationRepositoryPort):
    def __init__(self, catalog: dict[str, Any] | None = None) -> None:
        self.catalog = deepcopy(catalog or DEMO_CATALOG)
        self.saved: dict[str, dict[str, Any]] = {}
        self.teachers: dict[str, str | None] = {}

    def get_demo_catalog(self) -> dict[str, Any]:
        return self.catalog

    def save(self, result: dict[str, Any], teacher_id: str | None = None) -> None:
        self.saved[result["request"]["id"]] = result
        self.teachers[result["request"]["id"]] = teacher_id

    def get_by_id(self, generation_id: str) -> dict[str, Any] | None:
        return self.saved.get(generation_id)


def _make_request_payload(**overrides) -> dict[str, Any]:
    base = {
        "unitId": "u2",
        "outcomeId": None,
        "stage": "explore",
        "resourceType": "guia_exploracion",
        "quantity": 1,
        "optionCount": 4,
    }
    return {**base, **overrides}


def test_genera_con_evidencia_y_la_guarda():
    repo = MockGenerationRepository()
    service = GenerationService(repo)
    result = service.generate(_make_request_payload(), "docente@5e.demo")
    resource = result["resources"][0]
    assert result["mode"] == "api_demo" and result["available"] == 1
    assert resource["status"] == "pendiente" and resource["source"] == "api_demo"
    assert resource["citations"][0]["fragmentIds"] == ["api-demo:f-1"]
    assert [f["id"] for f in result["fragments"]] == ["api-demo:f-1"]
    assert result["documents"][0]["id"] == "api-demo:doc-1"
    assert repo.teachers[result["request"]["id"]] == "docente@5e.demo"
    assert service.get_by_id(result["request"]["id"]) is result


def test_genera_un_item_con_alternativas_sin_decidir():
    service = GenerationService(MockGenerationRepository())
    result = service.generate(
        _make_request_payload(stage="evaluate", resourceType="item_opcion_multiple", outcomeId="ra-1")
    )
    options = result["resources"][0]["options"]
    assert len(options) == 4 and all(o["decision"] == "pendiente" for o in options)
    assert sum(o["isCorrect"] for o in options) == 1


def test_rechaza_solicitudes_sin_sustento():
    service = GenerationService(MockGenerationRepository())
    test_cases = [
        (_make_request_payload(unitId="u9"), "SIN_MATERIAL_PROCESADO"),
        (_make_request_payload(outcomeId="ra-otra"), "RESULTADO_INVALIDO"),
        (_make_request_payload(resourceType="glosario"), "EVIDENCIA_INSUFICIENTE"),
        (_make_request_payload(stage="evaluate", resourceType="item_opcion_multiple", optionCount=5), "EVIDENCIA_INSUFICIENTE"),
    ]
    for payload, error_code in test_cases:
        with pytest.raises(GenerationError) as err:
            service.generate(payload)
        assert err.value.code == error_code


def test_no_genera_si_falta_un_fragmento_o_su_documento():
    missing_fragment = deepcopy(DEMO_CATALOG)
    missing_fragment["fragments"] = []
    with pytest.raises(GenerationError, match="Faltan fragmentos"):
        GenerationService(MockGenerationRepository(missing_fragment)).generate(_make_request_payload())

    missing_document = deepcopy(DEMO_CATALOG)
    missing_document["documents"] = []
    with pytest.raises(GenerationError, match="documento de origen"):
        GenerationService(MockGenerationRepository(missing_document)).generate(_make_request_payload())


def test_obtener_generacion_inexistente():
    with pytest.raises(GenerationError) as err:
        GenerationService(MockGenerationRepository()).get_by_id("sol-no-existe")
    assert err.value.code == "GENERACION_NO_ENCONTRADA"


# --------------------------------------------------------------------------- configuración (EP-002)

class MockAccountRepository(TeacherRepositoryPort):
    def __init__(self) -> None:
        self.sessions: dict[str, tuple[str, float]] = {}
        self.catalogs: dict[str, list[dict[str, Any]]] = {}
        self.docs: dict[tuple[str, str], tuple[dict[str, Any], bytes]] = {}
        self.owners: dict[str, str] = {}
        self.users: dict[str, dict[str, Any]] = {}
        self.deleted_entries: list[tuple[str, str, list[str]]] = []

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self.users.get(email)

    def create_user(self, user_data: dict[str, Any]) -> None:
        self.users[user_data["email"]] = user_data

    def delete_course(self, teacher_id: str, course_id: str, unit_ids: list[str]) -> None:
        self.catalogs[teacher_id] = [c for c in self.catalogs.get(teacher_id, []) if c["id"] != course_id]
        self.deleted_entries.append((teacher_id, course_id, unit_ids))

    def init_catalog(self, teacher_id: str) -> None:
        self.catalogs.setdefault(
            teacher_id,
            [
                {
                    "id": "curso-1",
                    "code": "ED-201",
                    "name": "Estructuras de datos",
                    "term": "2026-II",
                    "units": [
                        {
                            "id": "unidad-1",
                            "courseId": "curso-1",
                            "number": 1,
                            "title": "Pilas",
                            "outcomes": [{"id": "ra-1"}],
                        }
                    ],
                }
            ],
        )

    def save_session(self, fingerprint: str, teacher_id: str, expires_at: float) -> None:
        self.sessions[fingerprint] = (teacher_id, expires_at)

    def get_session(self, fingerprint: str) -> tuple[str, float] | None:
        return self.sessions.get(fingerprint)

    def delete_session(self, fingerprint: str) -> None:
        self.sessions.pop(fingerprint, None)

    def get_courses(self, teacher_id: str) -> list[dict[str, Any]]:
        return deepcopy(self.catalogs.get(teacher_id, []))

    def save_course(self, teacher_id: str, course_data: dict[str, Any]) -> None:
        courses = [c for c in self.catalogs.get(teacher_id, []) if c["id"] != course_data["id"]]
        self.catalogs[teacher_id] = courses + [course_data]

    def get_documents(self, teacher_id: str) -> list[dict[str, Any]]:
        return [metadata for (owner, _), (metadata, _) in self.docs.items() if owner == teacher_id]

    def save_document(self, teacher_id: str, metadata: dict[str, Any], content: bytes) -> None:
        self.docs[(teacher_id, metadata["id"])] = (metadata, content)

    def get_document(self, teacher_id: str, document_id: str) -> tuple[dict[str, Any], bytes] | None:
        return self.docs.get((teacher_id, document_id))

    def delete_document(self, teacher_id: str, document_id: str) -> None:
        self.docs.pop((teacher_id, document_id), None)

    def get_history(self, teacher_id: str) -> list[dict[str, Any]]:
        return []

    def get_generation_owner(self, generation_id: str) -> str | None:
        return self.owners.get(generation_id)


SEED_EMAIL: str = "docente@5e.demo"
SEED_PASSWORD: str = "Demo5E!2026"


@pytest.fixture(scope="module")
def base_account_service() -> AccountService:
    return AccountService(MockAccountRepository(), SEED_EMAIL, SEED_PASSWORD)


@pytest.fixture
def account_service(base_account_service: AccountService) -> AccountService:
    base_account_service.repository = MockAccountRepository()
    return base_account_service


def _get_bearer_header(service: AccountService) -> str:
    return "Bearer " + service.login(SEED_EMAIL, SEED_PASSWORD)["token"]


def _make_doc_context(**overrides) -> dict[str, Any]:
    base = {
        "unitId": "unidad-1",
        "usePermission": True,
        "documentType": "Guía de práctica",
        "outcomeIds": ["ra-1"],
    }
    return {**base, **overrides}


def _get_account_error_code(func, *args) -> str:
    with pytest.raises(AccountConfigurationError) as err:
        func(*args)
    return err.value.code


def test_login_autentica_y_cierra_sesion(account_service: AccountService):
    authorization = _get_bearer_header(account_service)
    assert account_service.authenticate_token(authorization) == SEED_EMAIL
    account_service.logout(authorization)
    assert _get_account_error_code(account_service.authenticate_token, authorization) == "SESION_VENCIDA"


def test_credenciales_y_sesiones_invalidas(account_service: AccountService):
    assert _get_account_error_code(account_service.login, SEED_EMAIL, "otra") == "CREDENCIALES_INVALIDAS"
    assert _get_account_error_code(account_service.login, "otro@5e.demo", SEED_PASSWORD) == "CREDENCIALES_INVALIDAS"
    assert _get_account_error_code(account_service.authenticate_token, None) == "SESION_REQUERIDA"
    assert _get_account_error_code(account_service.authenticate_token, "Token abc") == "SESION_REQUERIDA"

    authorization = _get_bearer_header(account_service)
    fingerprint = next(iter(account_service.repository.sessions))
    account_service.repository.sessions[fingerprint] = (SEED_EMAIL, time.time() - 1)
    assert _get_account_error_code(account_service.authenticate_token, authorization) == "SESION_VENCIDA"


def test_unidad_solo_de_los_cursos_del_docente(account_service: AccountService):
    account_service.login(SEED_EMAIL, SEED_PASSWORD)
    assert account_service.get_unit(SEED_EMAIL, "unidad-1")["title"] == "Pilas"
    assert _get_account_error_code(account_service.get_unit, SEED_EMAIL, "unidad-ajena") == "UNIDAD_NO_ENCONTRADA"


def test_crear_y_editar_curso(account_service: AccountService):
    account_service.login(SEED_EMAIL, SEED_PASSWORD)
    new_course = account_service.save_course(
        SEED_EMAIL,
        {
            "code": " ed-301 ",
            "name": "Grafos",
            "term": "2026-II",
            "units": [{"title": "Recorridos"}],
        },
    )
    assert new_course["code"] == "ED-301" and new_course["units"][0]["number"] == 1
    unit = new_course["units"][0]
    edited_course = account_service.save_course(
        SEED_EMAIL,
        {
            "code": "ED-301",
            "name": "Grafos II",
            "term": "2026-II",
            "units": [{"id": unit["id"], "title": "BFS y DFS"}, {"title": "Caminos"}],
        },
        new_course["id"],
    )
    assert [u["number"] for u in edited_course["units"]] == [1, 2]
    assert edited_course["units"][0]["id"] == unit["id"]


def test_reglas_del_catalogo(account_service: AccountService):
    account_service.login(SEED_EMAIL, SEED_PASSWORD)
    data = {"code": "ED-201", "name": "Copia", "term": "2026-II", "units": []}
    assert _get_account_error_code(account_service.save_course, SEED_EMAIL, data) == "CODIGO_DUPLICADO"
    assert (
        _get_account_error_code(account_service.save_course, SEED_EMAIL, {**data, "code": "X-1"}, "curso-no-existe")
        == "CURSO_NO_ENCONTRADO"
    )
    without_units = {"code": "ED-201", "name": "Estructuras", "term": "2026-II", "units": []}
    assert _get_account_error_code(account_service.save_course, SEED_EMAIL, without_units, "curso-1") == "UNIDADES_INVALIDAS"


def test_registra_material_valido(account_service: AccountService):
    account_service.login(SEED_EMAIL, SEED_PASSWORD)
    doc = account_service.register_document(SEED_EMAIL, "separata.pdf", b"%PDF-1.7 contenido", _make_doc_context())
    assert doc["kind"] == "pdf" and doc["status"] == "registrado" and doc["source"] == "backend"

    pptx_buffer = io.BytesIO()
    with zipfile.ZipFile(pptx_buffer, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("ppt/presentation.xml", "<p/>")

    assert (
        account_service.register_document(SEED_EMAIL, "clase.pptx", pptx_buffer.getvalue(), _make_doc_context())["kind"]
        == "pptx"
    )
    assert (
        account_service.register_document(SEED_EMAIL, "notas.txt", "Pilas y colas".encode(), _make_doc_context())["kind"]
        == "txt"
    )
    assert (
        _get_account_error_code(
            account_service.register_document, SEED_EMAIL, "SEPARATA.pdf", b"%PDF-1.7", _make_doc_context()
        )
        == "DOCUMENTO_DUPLICADO"
    )


def test_rechaza_material_invalido(account_service: AccountService):
    account_service.login(SEED_EMAIL, SEED_PASSWORD)
    test_cases = [
        ("a.pdf", b"%PDF-1", _make_doc_context(usePermission=False), "PERMISO_REQUERIDO"),
        ("a.pdf", b"%PDF-1", _make_doc_context(documentType="Otro"), "TIPO_INVALIDO"),
        ("a.pdf", b"%PDF-1", _make_doc_context(outcomeIds=["ra-ajeno"]), "RESULTADO_INVALIDO"),
        ("a.pdf", b"%PDF-1", _make_doc_context(outcomeIds=[]), "RESULTADO_INVALIDO"),
        ("../a.pdf", b"%PDF-1", _make_doc_context(), "NOMBRE_INVALIDO"),
        ("a.docx", b"datos", _make_doc_context(), "FORMATO_INVALIDO"),
        ("a.pdf", b"", _make_doc_context(), "TAMANO_INVALIDO"),
        ("a.pdf", b"no es pdf", _make_doc_context(), "FORMATO_INVALIDO"),
        ("a.pptx", b"no es zip", _make_doc_context(), "FORMATO_INVALIDO"),
        ("a.txt", b"\xff\xfe\x00", _make_doc_context(), "FORMATO_INVALIDO"),
    ]
    for filename, content, context, error_code in test_cases:
        assert (
            _get_account_error_code(account_service.register_document, SEED_EMAIL, filename, content, context)
            == error_code
        ), filename


def test_generacion_de_otro_docente_no_se_expone(account_service: AccountService):
    authorization = _get_bearer_header(account_service)
    account_service.repository.owners["sol-1"] = "otro@5e.demo"
    assert (
        _get_account_error_code(account_service.verify_generation_ownership, "sol-1", authorization)
        == "GENERACION_NO_ENCONTRADA"
    )
    account_service.repository.owners["sol-2"] = SEED_EMAIL
    assert account_service.verify_generation_ownership("sol-2", authorization) is None
    assert account_service.verify_generation_ownership("sol-sin-dueño", None) is None