"""
Entidades del dominio para la generación y revisión de recursos pedagógicos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AlternativeDomain:
    """Representa una alternativa o respuesta dentro de un recurso de evaluación o aprendizaje."""

    letter: str
    text: str
    is_correct: bool
    justification: str
    review_status: str = "pendiente"  # pendiente, aceptado, editado, descartado
    citations: list[dict[str, Any]] = field(default_factory=list)
    source_chunks: list[str] = field(default_factory=list)

    @property
    def letra(self) -> str:
        return self.letter

    @letra.setter
    def letra(self, val: str) -> None:
        self.letter = val

    @property
    def texto(self) -> str:
        return self.text

    @texto.setter
    def texto(self, val: str) -> None:
        self.text = val

    @property
    def es_correcta(self) -> bool:
        return self.is_correct

    @es_correcta.setter
    def es_correcta(self, val: bool) -> None:
        self.is_correct = val

    @property
    def justificacion(self) -> str:
        return self.justification

    @justificacion.setter
    def justificacion(self, val: str) -> None:
        self.justification = val

    @property
    def estado(self) -> str:
        return self.review_status

    @estado.setter
    def estado(self, val: str) -> None:
        self.review_status = val

    @property
    def citas(self) -> list[dict[str, Any]]:
        return self.citations

    @citas.setter
    def citas(self, val: list[dict[str, Any]]) -> None:
        self.citations = val

    @property
    def fragmentos_origen(self) -> list[str]:
        return self.source_chunks

    @fragmentos_origen.setter
    def fragmentos_origen(self, val: list[str]) -> None:
        self.source_chunks = val


@dataclass
class LearningResourceDomain:
    """Entidad principal que representa un recurso pedagógico generado y sujeto a revisión."""

    id: str
    title: str
    prompt: str
    feedback: str
    alternatives: list[AlternativeDomain]
    review_status: str = "borrador"  # borrador, aprobado, rechazado
    citations: list[dict[str, Any]] = field(default_factory=list)

    @property
    def titulo(self) -> str:
        return self.title

    @titulo.setter
    def titulo(self, val: str) -> None:
        self.title = val

    @property
    def enunciado(self) -> str:
        return self.prompt

    @enunciado.setter
    def enunciado(self, val: str) -> None:
        self.prompt = val

    @property
    def retroalimentacion(self) -> str:
        return self.feedback

    @retroalimentacion.setter
    def retroalimentacion(self, val: str) -> None:
        self.feedback = val

    @property
    def estado_revision(self) -> str:
        return self.review_status

    @estado_revision.setter
    def estado_revision(self, val: str) -> None:
        self.review_status = val

    @property
    def citas(self) -> list[dict[str, Any]]:
        return self.citations

    @citas.setter
    def citas(self, val: list[dict[str, Any]]) -> None:
        self.citations = val

    @property
    def alternativas(self) -> list[AlternativeDomain]:
        return self.alternatives

    @alternativas.setter
    def alternativas(self, val: list[AlternativeDomain]) -> None:
        self.alternatives = val


# ---------------------------------------------------------------------------
# Clases puente para permitir inicialización con parámetros en español
# ---------------------------------------------------------------------------
class AlternativaDominio(AlternativeDomain):
    def __init__(
        self,
        letra: str = "",
        texto: str = "",
        es_correcta: bool = False,
        justificacion: str = "",
        estado: str = "pendiente",
        citas: list[dict[str, Any]] | None = None,
        fragmentos_origen: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        letter = kwargs.get("letter", letra)
        text = kwargs.get("text", texto)
        is_correct = kwargs.get("is_correct", es_correcta)
        just_text = kwargs.get("justification", justificacion)
        st = kwargs.get("review_status", estado)
        cit = kwargs.get("citations", citas if citas is not None else [])
        frag = kwargs.get("source_chunks", fragmentos_origen if fragmentos_origen is not None else [])
        super().__init__(
            letter=letter,
            text=text,
            is_correct=is_correct,
            justification=just_text,
            review_status=st,
            citations=cit,
            source_chunks=frag,
        )


class RecursoDominio(LearningResourceDomain):
    def __init__(
        self,
        id: str = "",
        titulo: str = "",
        enunciado: str = "",
        retroalimentacion: str = "",
        alternativas: list[Any] | None = None,
        estado_revision: str = "borrador",
        citas: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        rec_id = kwargs.get("id", id)
        tit = kwargs.get("title", titulo)
        pr = kwargs.get("prompt", enunciado)
        feed = kwargs.get("feedback", retroalimentacion)
        alts = kwargs.get("alternatives", alternativas if alternativas is not None else [])
        st = kwargs.get("review_status", estado_revision)
        cit = kwargs.get("citations", citas if citas is not None else [])
        super().__init__(
            id=rec_id,
            title=tit,
            prompt=pr,
            feedback=feed,
            alternatives=alts,
            review_status=st,
            citations=cit,
        )


LearningOptionDomain = AlternativeDomain