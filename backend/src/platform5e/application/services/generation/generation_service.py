"""
HU-053 y HU-018: genera propuestas pedagógicas para revisión docente.
Recupera fragmentos relevantes del material procesado de la unidad (RAG)
y solicita la redacción con citas exactas al modelo o motor generador.
"""

from __future__ import annotations

import logging
import random
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from platform5e.application.ports.outbound.chunk_repository_port import ChunkRepositoryPort
from platform5e.application.ports.outbound.evidence_retriever_port import EvidenceRetrieverPort
from platform5e.application.ports.outbound.generation_repository_port import GenerationRepositoryPort
from platform5e.application.ports.outbound.language_model_port import ResourceGeneratorPort
from platform5e.application.ports.outbound.media_port import MediaGeneratorPort, MediaRepositoryPort
from platform5e.application.ports.outbound.resource_repository_port import ResourceReviewRepositoryPort
from platform5e.application.ports.outbound.teacher_repository_port import TeacherRepositoryPort
from platform5e.application.services.generation.prompt_drafting import (
    build_generation_context,
    normalize_generated_resources,
)
from platform5e.domain.generation.errors import GenerationError
from platform5e.domain.generation.resource_formats import AUDIO, IMAGE, resource_format

OPTION_LETTERS: str = "abcdefghij"
NO_MATERIAL_NOTICE: str = (
    "Esta unidad todavía no tiene material procesado. Sube un documento o busca el tema "
    "en la pestaña Material y vuelve a intentar."
)
REQUEST_PARAMETERS: tuple[str, ...] = (
    "resourceType",
    "stage",
    "outcomeId",
    "difficulty",
    "optionCount",
    "instructions",
    "audience",
    "competency",
    "modalities",
    "topK",
    "evidenceThreshold",
)

logger = logging.getLogger("platform5e.generation")


class GenerationService:
    """Servicio de aplicación para orquestar la generación 5E con evidencia y respaldo."""

    def __init__(
        self,
        repository: GenerationRepositoryPort,
        teacher_repository: TeacherRepositoryPort | None = None,
        chunk_repository: ChunkRepositoryPort | None = None,
        primary_generator: ResourceGeneratorPort | None = None,
        fallback_generator: ResourceGeneratorPort | None = None,
        review_repository: ResourceReviewRepositoryPort | None = None,
        demo_examples_enabled: bool = True,
        evidence_retriever: EvidenceRetrieverPort | None = None,
        media_generator: MediaGeneratorPort | None = None,
        media_repository: MediaRepositoryPort | None = None,
    ) -> None:
        self._media_generator = media_generator
        self._media_repository = media_repository
        self._repository = repository
        self._evidence_retriever = evidence_retriever
        self._demo_examples_enabled = demo_examples_enabled
        self._review_repository = review_repository
        self._teacher_repository = teacher_repository
        self._chunk_repository = chunk_repository
        self._primary_generator = primary_generator
        self._fallback_generator = fallback_generator

    def generate(self, request_data: dict[str, Any], teacher_id: str | None = None) -> dict[str, Any]:
        """Dispara la generación de propuestas basada en material o modo demostración."""
        if (
            teacher_id
            and self._teacher_repository
            and self._chunk_repository
            and self._evidence_retriever
            and (self._primary_generator or self._fallback_generator)
        ):
            course, unit = self._get_course_and_unit(teacher_id, request_data["unitId"])
            if unit is not None:
                chunks = self._chunk_repository.get_chunks_by_unit(teacher_id, unit["id"])
                if chunks:
                    return self._generate_with_material(
                        request_data, teacher_id, course, unit, chunks
                    )

        if not self._demo_examples_enabled:
            raise GenerationError("NO_PROCESSED_MATERIAL", NO_MATERIAL_NOTICE)

        return self._generate_demo(request_data, teacher_id)

    def _get_course_and_unit(
        self, teacher_id: str, unit_id: str
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        """Localiza el curso y la unidad dentro del repositorio de configuración."""
        assert self._teacher_repository is not None
        for course in self._teacher_repository.get_courses(teacher_id):
            for unit in course["units"]:
                if unit["id"] == unit_id:
                    return course, unit
        return {}, None

    def _generate_with_material(
        self,
        request_data: dict[str, Any],
        teacher_id: str,
        course: dict[str, Any],
        unit: dict[str, Any],
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Orquesta la recuperación de evidencia (puerto de recuperación) y la redacción (puerto del modelo)."""
        assert self._teacher_repository is not None and self._evidence_retriever is not None
        if request_data["outcomeId"] and not any(
            outcome["id"] == request_data["outcomeId"] for outcome in unit.get("outcomes", [])
        ):
            raise GenerationError("INVALID_OUTCOME", "El resultado de aprendizaje no pertenece a la unidad.")

        query_text = " ".join(
            filter(
                None,
                [
                    unit.get("title", ""),
                    *(
                        outcome.get("text", "")
                        for outcome in unit.get("outcomes", [])
                        if not request_data["outcomeId"] or outcome["id"] == request_data["outcomeId"]
                    ),
                    request_data.get("instructions", ""),
                    request_data.get("competency", ""),
                ],
            )
        )

        top_k = max(3, min(int(request_data.get("topK") or 8), 12))
        selected_chunks = self._evidence_retriever.retrieve(query_text, chunks, top_k)

        documents_map = {
            doc["id"]: doc
            for doc in self._teacher_repository.get_documents(teacher_id)
            if doc["unitId"] == unit["id"]
        }
        generation_context = build_generation_context(
            course,
            unit,
            request_data,
            selected_chunks,
            {doc_id: doc["fileName"] for doc_id, doc in documents_map.items()},
        )

        resources: list[dict[str, Any]] = []
        active_generator: ResourceGeneratorPort | None = None
        warning_message: str | None = None

        if self._primary_generator is not None:
            try:
                raw_response = self._primary_generator.generate(generation_context)
                resources = normalize_generated_resources(raw_response, generation_context)
                active_generator = self._primary_generator
                if not resources:
                    warning_message = (
                        f"{self._primary_generator.description} no devolvió recursos con citas válidas del material."
                    )
            except Exception as exc:
                warning_message = f"{self._primary_generator.description} no respondió ({str(exc)[:160]})."

        if (
            not resources
            and self._fallback_generator is not None
            and self._fallback_generator is not self._primary_generator
        ):
            raw_response = self._fallback_generator.generate(generation_context)
            resources = normalize_generated_resources(raw_response, generation_context)
            active_generator = self._fallback_generator
            if warning_message:
                warning_message += " Se usó el generador por reglas."

        if warning_message:
            logger.warning("Generación con respaldo: %s", warning_message)

        if not resources or active_generator is None:
            raise GenerationError(
                "INSUFFICIENT_EVIDENCE",
                "No se pudieron redactar recursos que citen el material. "
                "Prueba con otro tipo de recurso o agrega más material a la unidad.",
            )

        current_timestamp = datetime.now(timezone.utc).isoformat()
        enriched_request = {**request_data, "id": f"sol-api-{uuid4()}", "createdAt": current_timestamp}
        resolved_outcome_id = request_data["outcomeId"] or next(
            (o["id"] for o in unit.get("outcomes", [])), ""
        )

        output_resources = [
            self._build_resource_dict(
                resource,
                enriched_request,
                unit["id"],
                resolved_outcome_id,
                active_generator.description,
                current_timestamp,
            )
            for resource in resources
        ]

        cited_fragment_ids = {
            f_id for r in output_resources for c in r["citations"] for f_id in c["fragmentIds"]
        }
        cited_fragment_ids |= {
            f_id for r in output_resources for opt in (r["options"] or []) for f_id in opt["sourceFragmentIds"]
        }

        used_chunks = [c for c in selected_chunks if c["id"] in cited_fragment_ids]
        associated_docs = [
            documents_map[doc_id]
            for doc_id in dict.fromkeys(
                chunk.get("documentId") or chunk.get("documento_id") for chunk in used_chunks
            )
            if doc_id in documents_map
        ]

        uses_ai = bool(getattr(active_generator, "uses_ai", False))
        for resource in output_resources:
            self._attach_media(teacher_id, resource)
        self._save_for_review(
            teacher_id,
            unit["id"],
            output_resources,
            used_chunks,
            associated_docs,
            enriched_request,
            uses_ai,
        )

        suffix_notice = f" {warning_message}" if warning_message else ""
        result_payload: dict[str, Any] = {
            "mode": "rag",
            "notice": (
                f"Generado con {active_generator.description} a partir de tu material.{suffix_notice}"
            ),
            "generator": {
                "description": active_generator.description,
                "usesAi": uses_ai,
                "fallback": warning_message is not None,
            },
            "request": enriched_request,
            "resources": output_resources,
            "available": len(output_resources),
            "fragments": [
                {
                    "id": chunk["id"],
                    "documentId": chunk.get("documentId") or chunk.get("documento_id"),
                    "location": chunk.get("location") or chunk.get("ubicacion"),
                    "unitId": unit["id"],
                    "outcomeId": resolved_outcome_id,
                    "text": chunk.get("text") or chunk.get("texto"),
                    "relevance": chunk.get("relevance", chunk.get("relevancia", 0.0)),
                }
                for chunk in used_chunks
            ],
            "documents": associated_docs,
            # Todo lo recuperado (no solo lo citado): lo usa la evaluación RAG. La interfaz no lo muestra.
            "retrievedChunks": [
                {
                    "id": chunk["id"],
                    "location": chunk.get("location") or chunk.get("ubicacion"),
                    "text": chunk.get("text") or chunk.get("texto"),
                    "relevance": chunk.get("relevance", chunk.get("relevancia", 0.0)),
                }
                for chunk in selected_chunks
            ],
        }

        self._repository.save(result_payload, teacher_id)
        return result_payload

    def _attach_media(self, teacher_id: str, resource: dict[str, Any]) -> None:
        """Genera la imagen o el audio del recurso. Si el servicio falla, deja el respaldo y la generación sigue."""
        kind = resource["format"]
        if kind not in (IMAGE, AUDIO):
            return
        fallback_note = (
            "Sin imagen generada: se muestra la descripción de la ilustración."
            if kind == IMAGE
            else "Sin audio generado: el guion se escucha con la voz del navegador."
        )
        resource["media"] = {"status": "fallback", "note": fallback_note}
        if self._media_generator is None or self._media_repository is None:
            return
        structure = resource.get("structure") or {}
        try:
            generated = (
                self._media_generator.generate_image(structure["prompt"])
                if kind == IMAGE
                else self._media_generator.synthesize_speech(structure["script"])
            )
        except Exception as exc:  # el recurso se conserva con su respaldo
            logger.warning("Medio no generado para %s: %s", resource["id"], str(exc)[:200])
            resource["media"]["note"] += f" ({str(exc)[:120]})"
            return
        media = {
            "id": f"media-{uuid4()}",
            "resourceId": resource["id"],
            "status": "ready",
            "mimeType": generated.mime_type,
            "fileName": f"{resource['id']}.{generated.extension}",
            "sizeBytes": len(generated.content),
            "generator": self._media_generator.description,
        }
        self._media_repository.save_media(teacher_id, media, generated.content)
        resource["media"] = media

    def _save_for_review(
        self,
        teacher_id: str,
        unit_id: str,
        output_resources: list[dict[str, Any]],
        used_chunks: list[dict[str, Any]],
        documents: list[dict[str, Any]],
        request_data: dict[str, Any],
        uses_ai: bool,
    ) -> None:
        """Asocia la evidencia textual y parámetros congelados al recurso para su revisión posterior."""
        doc_names = {d["id"]: d.get("fileName", "") for d in documents}
        doc_origins = {d["id"]: d.get("origin") or {} for d in documents}
        chunks_by_id = {c["id"]: c for c in used_chunks}
        saved_parameters = {param: request_data.get(param) for param in REQUEST_PARAMETERS}

        for resource in output_resources:
            referenced_ids = [f_id for c in resource["citations"] for f_id in c["fragmentIds"]]
            referenced_ids += [
                f_id for opt in (resource["options"] or []) for f_id in opt["sourceFragmentIds"]
            ]

            evidence_list: list[dict[str, Any]] = []
            for f_id in dict.fromkeys(referenced_ids):
                if f_id in chunks_by_id:
                    matched_chunk = chunks_by_id[f_id]
                    doc_id = matched_chunk.get("documentId") or matched_chunk.get("documento_id")
                    evidence_list.append(
                        {
                            "id": f_id,
                            "text": matched_chunk.get("text") or matched_chunk.get("texto"),
                            "location": matched_chunk.get("location") or matched_chunk.get("ubicacion"),
                            "documentId": doc_id,
                            "documentName": doc_names.get(doc_id, ""),
                            "sourceUrl": doc_origins.get(doc_id, {}).get("url"),
                            "license": doc_origins.get(doc_id, {}).get("license"),
                        }
                    )

            resource["evidence"] = evidence_list
            resource["params"] = saved_parameters
            resource["generatorKind"] = "ia" if uses_ai else "respaldo"

        if self._review_repository is not None:
            self._review_repository.save_resources(teacher_id, unit_id, output_resources)

    @staticmethod
    def _build_resource_dict(
        resource_data: dict[str, Any],
        request_data: dict[str, Any],
        unit_id: str,
        outcome_id: str,
        generator_name: str,
        timestamp: str,
    ) -> dict[str, Any]:
        """Crea el diccionario con formato estándar para la API de revisión docente."""
        resource_id = f"rec-api-{uuid4()}"
        options_list = None

        if resource_data.get("alternativas"):
            alternatives = list(resource_data["alternativas"])
            random.Random(resource_id).shuffle(alternatives)
            options_list = [
                {
                    "id": f"{resource_id}:{OPTION_LETTERS[idx]}",
                    "text": alt["texto"],
                    "isCorrect": alt["correcta"],
                    "feedback": alt["retroalimentacion"],
                    "sourceFragmentIds": alt["fragmentos"],
                    "decision": "pendiente",
                    "discardReason": None,
                    "edited": False,
                    "reliabilityWarning": None,
                }
                for idx, alt in enumerate(alternatives)
            ]

        return {
            "exampleId": "material-docente",
            "unitId": unit_id,
            "outcomeId": outcome_id,
            "stage": request_data["stage"],
            "type": request_data["resourceType"],
            "format": resource_format(request_data["resourceType"]),
            "structure": resource_data.get("estructura"),
            "title": resource_data["titulo"],
            "body": resource_data["contenido"],
            "id": resource_id,
            "requestId": request_data["id"],
            "source": "rag",
            "generator": generator_name,
            "options": options_list,
            "citations": resource_data["citas"],
            "status": "pendiente",
            "edited": False,
            "discardReason": None,
            "createdAt": timestamp,
            "updatedAt": timestamp,
            "decidedAt": None,
        }

    def _generate_demo(self, request_data: dict[str, Any], teacher_id: str | None = None) -> dict[str, Any]:
        """Genera resultados basados en el catálogo de demostración precargado."""
        demo_catalog = self._repository.get_demo_catalog()
        matched_unit = next(
            (u for u in demo_catalog["units"] if u["id"] == request_data["unitId"]), None
        )
        if matched_unit is None:
            raise GenerationError("NO_PROCESSED_MATERIAL", NO_MATERIAL_NOTICE)

        if request_data["outcomeId"] and not any(
            o["id"] == request_data["outcomeId"] for o in matched_unit["outcomes"]
        ):
            raise GenerationError("INVALID_OUTCOME", "El resultado de aprendizaje no pertenece a la unidad.")

        available_examples = [
            ex
            for ex in demo_catalog["examples"]
            if ex["unitId"] == request_data["unitId"]
            and ex["stage"] == request_data["stage"]
            and ex["type"] == request_data["resourceType"]
            and (request_data["outcomeId"] is None or ex["outcomeId"] == request_data["outcomeId"])
        ]

        if request_data["stage"] == "evaluate":
            available_examples = [
                ex for ex in available_examples if len(ex.get("options", [])) == request_data["optionCount"]
            ]

        if not available_examples:
            raise GenerationError(
                "INSUFFICIENT_EVIDENCE",
                "La API de demostración no tiene ejemplos para esta combinación de unidad, etapa y tipo.",
            )

        timestamp = datetime.now(timezone.utc).isoformat()
        enriched_request = {**request_data, "id": f"sol-api-{uuid4()}", "createdAt": timestamp}
        demo_resources: list[dict[str, Any]] = []
        referenced_fragments: set[str] = set()

        for original_example in available_examples[: request_data["quantity"]]:
            cloned = deepcopy(original_example)
            rec_id = f"rec-api-{uuid4()}"
            rebased_citations = []
            for cit in cloned["citations"]:
                referenced_fragments.update(cit["fragmentIds"])
                rebased_citations.append(
                    {**cit, "fragmentIds": [f"api-demo:{fid}" for fid in cit["fragmentIds"]]}
                )

            rebased_options = None
            if cloned.get("options") is not None:
                rebased_options = []
                for opt in cloned["options"]:
                    referenced_fragments.update(opt["sourceFragmentIds"])
                    rebased_options.append(
                        {
                            **opt,
                            "id": f"{rec_id}:{opt['id']}",
                            "sourceFragmentIds": [f"api-demo:{fid}" for fid in opt["sourceFragmentIds"]],
                            "decision": "pendiente",
                            "discardReason": None,
                            "edited": False,
                            "reliabilityWarning": opt.get("reliabilityWarning"),
                        }
                    )

            demo_resources.append(
                {
                    **{
                        k: cloned[k]
                        for k in ("exampleId", "unitId", "outcomeId", "stage", "type", "title", "body")
                    },
                    "id": rec_id,
                    "requestId": enriched_request["id"],
                    "source": "api_demo",
                    "options": rebased_options,
                    "citations": rebased_citations,
                    "status": "pendiente",
                    "edited": False,
                    "discardReason": None,
                    "createdAt": timestamp,
                    "updatedAt": timestamp,
                    "decidedAt": None,
                }
            )

        matched_fragments = [f for f in demo_catalog["fragments"] if f["id"] in referenced_fragments]
        if {f["id"] for f in matched_fragments} != referenced_fragments:
            raise GenerationError(
                "INSUFFICIENT_EVIDENCE",
                "Faltan fragmentos de demostración para sustentar la propuesta.",
            )

        matched_doc_ids = {f["documentId"] for f in matched_fragments}
        matched_documents = [d for d in demo_catalog["documents"] if d["id"] in matched_doc_ids]
        if {d["id"] for d in matched_documents} != matched_doc_ids:
            raise GenerationError(
                "INSUFFICIENT_EVIDENCE",
                "Falta el documento de origen de la evidencia de demostración.",
            )

        result_payload: dict[str, Any] = {
            "mode": "api_demo",
            "notice": demo_catalog["notice"],
            "request": enriched_request,
            "resources": demo_resources,
            "available": len(available_examples),
            "fragments": [
                {
                    **frag,
                    "id": f"api-demo:{frag['id']}",
                    "documentId": f"api-demo:{frag['documentId']}",
                }
                for frag in matched_fragments
            ],
            "documents": [{**doc, "id": f"api-demo:{doc['id']}"} for doc in matched_documents],
        }

        self._repository.save(result_payload, teacher_id)
        return result_payload

    def get_by_id(self, generation_id: str) -> dict[str, Any]:
        """Recupera una generación previamente procesada."""
        result = self._repository.get_by_id(generation_id)
        if result is None:
            raise GenerationError("GENERATION_NOT_FOUND", "La solicitud de generación no existe.")
        return result