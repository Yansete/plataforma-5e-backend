"""
Errores del núcleo de dominio independientes de HTTP y de la infraestructura de persistencia.
"""


class DomainError(Exception):
    """Excepción base para todos los errores que ocurren dentro de las reglas de negocio."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ResourceNotFoundError(ValueError, DomainError):
    """Se lanza cuando un recurso educativo solicitado no existe."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)


class NoApprovedResourcesError(ValueError, DomainError):
    """Se lanza cuando se intenta exportar un lote sin recursos aprobados."""

    def __init__(self, message: str = "No approved resources available for export") -> None:
        super().__init__(message)


class PersistenceUnavailableError(DomainError):
    """Se lanza cuando la capa de persistencia no responde o no está disponible."""

    def __init__(
        self,
        message: str = "Could not save or query. Please check database connection.",
    ) -> None:
        super().__init__(message)


class DuplicateRecordError(DomainError):
    """Se lanza cuando se intenta crear una entidad con identificadores o claves ya existentes."""

    def __init__(
        self,
        message: str = "The record already exists. Refresh the list and review the data.",
    ) -> None:
        super().__init__(message)


# ---------------------------------------------------------------------------
# Alias de compatibilidad temporal en español mientras se migran las capas externas
# ---------------------------------------------------------------------------
RecursoNoEncontrado = ResourceNotFoundError
SinRecursosAprobados = NoApprovedResourcesError
PersistenciaNoDisponible = PersistenceUnavailableError
RegistroDuplicado = DuplicateRecordError
EntityNotFoundError = ResourceNotFoundError