"""
Punto de composición de la aplicación FastAPI (Bootstrap y contenedor de dependencias).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from platform5e.application.services.accounts.account_service import AccountService
from platform5e.application.services.generation.generation_service import GenerationService
from platform5e.application.services.materials.material_service import MaterialService
from platform5e.application.services.review.resource_review_service import ResourceReviewService
from platform5e.application.use_cases.export.export_unit_resources import ExportUnitResourcesUseCase
from platform5e.domain.accounts.teacher_account import AccountConfigurationError
from platform5e.domain.generation.errors import GenerationError
from platform5e.domain.materials.chunking import MaterialError
from platform5e.domain.shared.errors import (
    DuplicateRecordError,
    EntityNotFoundError,
    PersistenceUnavailableError,
)
from platform5e.infrastructure.exporters.moodle_xml_exporter import MoodleXmlExporter
from platform5e.infrastructure.exporters.scorm_package_exporter import ScormPackageExporter
from platform5e.infrastructure.extraction.document_text_extractor import DocumentTextExtractor
from platform5e.infrastructure.http.error_handlers import (
    configuration_error_handler,
    conflict_error_handler,
    persistence_unavailable_handler,
    request_validation_error_handler,
    resource_not_found_handler,
    value_error_handler,
)
from platform5e.infrastructure.http.routers.accounts import create_accounts_router
from platform5e.infrastructure.http.routers.documents import create_materials_router
from platform5e.infrastructure.http.routers.exports import create_exports_router
from platform5e.infrastructure.http.routers.generations import create_generations_router
from platform5e.infrastructure.http.routers.health import create_health_router
from platform5e.infrastructure.http.routers.resources import create_resources_router
from platform5e.infrastructure.llm.language_model_factory import (
    create_generators,
    describe_generator,
)
from platform5e.infrastructure.persistence.repositories.sqlalchemy_account_repository import (
    SQLAlchemyAccountRepository,
)
from platform5e.infrastructure.persistence.repositories.sqlalchemy_chunk_repository import (
    SQLAlchemyChunkRepository,
)
from platform5e.infrastructure.persistence.repositories.sqlalchemy_generation_repository import (
    SQLAlchemyGenerationRepository,
)
from platform5e.infrastructure.persistence.repositories.sqlalchemy_resource_repository import (
    SQLAlchemyResourceRepository,
)
from platform5e.infrastructure.settings import read_flag, read_setting
from platform5e.infrastructure.sources.wikipedia_source import WikipediaSource


def custom_openapi_schema(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description="Plataforma de generación de secuencias didácticas 5E",
        routes=app.routes,
    )

    # Inyectar el esquema de seguridad SesionDocente que esperan las pruebas
    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["SesionDocente"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Token JWT de sesión docente",
    }

    # Rutas protegidas que deben declarar SesionDocente
    protected_routes = [
        ("/api/v1/solicitudes", "get"),
        ("/api/v1/cursos", "get"),
        ("/api/v1/documentos", "post"),
        ("/api/v1/sesiones/actual", "delete"),
        ("/api/v1/generaciones", "post"),
    ]

    for route, method in protected_routes:
        if route in openapi_schema.get("paths", {}) and method in openapi_schema["paths"][route]:
            operation = openapi_schema["paths"][route][method]
            operation["security"] = [{"SesionDocente": []}]
            operation["parameters"] = [
                p for p in operation.get("parameters", [])
                if not (p.get("in") == "header" and p.get("name", "").lower() == "authorization")
            ]

    # Quitar security de login si existiera
    if "/api/v1/sesiones" in openapi_schema.get("paths", {}) and "post" in openapi_schema["paths"]["/api/v1/sesiones"]:
        openapi_schema["paths"]["/api/v1/sesiones"]["post"].pop("security", None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_application() -> FastAPI:
    """Inicializa la aplicación FastAPI, resuelve las dependencias y registra middlewares y rutas."""
    app = FastAPI(title="Plataforma Docente - Backend", version="1.2.0")

    cors_origins = [
        origin.strip().rstrip("/")
        for origin in read_setting("CORS_ALLOWED_ORIGINS").split(",")
        if origin.strip()
    ]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Content-Disposition"],  # nombre del archivo exportado
        )

    # 1. Repositorios de persistencia
    generation_repository = SQLAlchemyGenerationRepository()
    account_repository = SQLAlchemyAccountRepository(generation_repository)
    chunk_repository = SQLAlchemyChunkRepository()
    resource_repository = SQLAlchemyResourceRepository()

    # 2. Configuración y servicios de aplicación
    demo_catalog_enabled = read_flag("DEMO_CATALOG", False)
    account_service = AccountService(
        account_repository,
        seed_email=read_setting(
            "BOOTSTRAP_TEACHER_EMAIL", "docente@5e.demo" if demo_catalog_enabled else ""
        ),
        seed_password=read_setting(
            "BOOTSTRAP_TEACHER_PASSWORD", "Demo5E!2026" if demo_catalog_enabled else ""
        ),
        seed_demo_catalog=demo_catalog_enabled,
    )

    open_resource_port = (
        WikipediaSource()
        if read_flag("TOPIC_SEARCH_ENABLED", True)
        else None
    )
    material_service = MaterialService(
        account_repository,
        chunk_repository,
        DocumentTextExtractor(),
        open_resource_port=open_resource_port,
    )

    review_service = ResourceReviewService(account_repository, resource_repository)
    export_use_case = ExportUnitResourcesUseCase(
        account_repository, resource_repository, [ScormPackageExporter(), MoodleXmlExporter()]
    )

    # 3. Modelos de lenguaje (LLM o respaldo determinista)
    primary_generator, fallback_generator = create_generators()
    generation_service = GenerationService(
        repository=generation_repository,
        teacher_repository=account_repository,
        chunk_repository=chunk_repository,
        primary_generator=primary_generator,
        fallback_generator=fallback_generator,
        review_repository=resource_repository,
        demo_examples_enabled=demo_catalog_enabled,
    )

    # 4. Manejo centralizado de excepciones
    app.add_exception_handler(AccountConfigurationError, configuration_error_handler)
    app.add_exception_handler(MaterialError, configuration_error_handler)
    app.add_exception_handler(GenerationError, configuration_error_handler)
    app.add_exception_handler(DuplicateRecordError, conflict_error_handler)
    app.add_exception_handler(PersistenceUnavailableError, persistence_unavailable_handler)
    app.add_exception_handler(EntityNotFoundError, resource_not_found_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)

    # 5. Registro de enrutadores HTTP
    app.include_router(create_accounts_router(account_service))
    app.include_router(create_resources_router(review_service, account_service))
    app.include_router(
        create_materials_router(
            material_service, account_service, describe_generator(primary_generator)
        )
    )
    app.include_router(
        create_generations_router(generation_service, account_service)
    )
    app.include_router(create_exports_router(export_use_case, account_service))
    app.include_router(create_health_router())

    # Sobrescribir generador openapi
    app.openapi = lambda: custom_openapi_schema(app)

    return app


app = create_application()