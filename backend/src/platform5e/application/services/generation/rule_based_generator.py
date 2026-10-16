"""
Generador basado en reglas deterministas: extrae oraciones y términos del material
para componer propuestas sin requerir dependencias de modelos LLM externos.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from platform5e.domain.materials.chunking import extract_sentences
from platform5e.domain.materials.text_analysis import (
    STOPWORDS,
    extract_key_terms,
    normalize_text,
    stem_word,
)

_URL_PATTERN: re.Pattern[str] = re.compile(r"https?://|^(Fuente|Licencia):", re.IGNORECASE)
_WORD_REGEX: str = r"[\wáéíóúñÁÉÍÓÚÑ/-]+"
_SUBJECT_REGEX: re.Pattern[str] = re.compile(
    rf"(?:^|[,;:]\s+)(?:[Ee]l|[Ll]a|[Ll]os|[Ll]as|[Uu]n|[Uu]na)\s+((?:{_WORD_REGEX}\s+){{0,2}}?{_WORD_REGEX})\s+"
    r"(?:no\s+|también\s+|solo\s+)?(?:es|son|fue|se\s+encarga|se\s+usa|se\s+utiliza|se\s+define|trabaja|trabajan|"
    r"permite|permiten|consiste|establece|garantiza|divide|tiene|tienen|ofrece|decide|traduce|agrega)\b"
)
_ACRONYM_REGEX: re.Pattern[str] = re.compile(r"(?<![\w/])([A-Z]{2,6}(?:/[A-Z]{2,6})?)(?![\w/])")
_ROMAN_NUMERALS: set[str] = {"II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII"}


def _extract_domain_terms(
    sentence_pairs: list[tuple[str, str]], fallback_terms: list[str]
) -> list[str]:
    """Identifica sujetos gramaticales de definiciones, siglas y términos frecuentes."""
    identified_subjects: list[str] = []
    for _, sentence in sentence_pairs:
        for match in _SUBJECT_REGEX.finditer(sentence):
            words = match.group(1).split()
            while words and normalize_text(words[-1]) in STOPWORDS:
                words.pop()
            if words and normalize_text(words[0]) not in STOPWORDS:
                identified_subjects.append(" ".join(words))

    acronym_counts = Counter(
        match
        for _, sentence in sentence_pairs
        for match in _ACRONYM_REGEX.findall(sentence)
        if match not in _ROMAN_NUMERALS
    )

    seen_stems: set[str] = set()
    ordered_terms: list[str] = []
    candidates = [
        *identified_subjects,
        *(acronym for acronym, _ in acronym_counts.most_common()),
        *fallback_terms,
    ]

    for candidate in candidates:
        normalized_candidate = normalize_text(candidate)
        if normalized_candidate not in seen_stems and len(normalized_candidate) >= 2:
            seen_stems.add(normalized_candidate)
            ordered_terms.append(candidate)

    return ordered_terms


def _are_related_terms(term_a: str, term_b: str) -> bool:
    """Verifica si dos términos comparten la raíz morfológica o subcadenas completas."""
    norm_a, norm_b = normalize_text(term_a), normalize_text(term_b)
    if norm_a in norm_b or norm_b in norm_a:
        return True
    if " " not in norm_a or " " not in norm_b:
        return stem_word(norm_a.split()[0]) == stem_word(norm_b.split()[0])
    return False


def _share_head_word(term_a: str, term_b: str) -> bool:
    """Determina si ambos términos inician con el mismo sustantivo o palabra principal."""
    return normalize_text(term_a.split()[0]) == normalize_text(term_b.split()[0])


def _contains_word(text: str, word: str) -> bool:
    """Busca coincidencia exacta de palabra evitando falsos positivos de subcadena."""
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text, re.IGNORECASE) is not None


def _mask_target_word(sentence: str, target: str) -> str:
    """Oculta el término central para crear el ítem de completación."""
    return re.sub(rf"(?<!\w){re.escape(target)}(?!\w)", "________", sentence, count=1, flags=re.IGNORECASE)


def _capitalize_first(text: str) -> str:
    """Pone en mayúscula únicamente el primer carácter del texto."""
    return text[:1].upper() + text[1:]


class RuleBasedGenerator:
    """Generador determinista de recursos pedagógicos para respaldo ante caídas de red."""

    description: str = "Generador por reglas (sin IA)"
    uses_ai: bool = False

    def generate(self, context: dict[str, Any]) -> dict[str, Any]:
        """Procesa los fragmentos de entrada y genera propuestas según el tipo solicitado."""
        sentence_pairs: list[tuple[str, str]] = []
        seen_sentences: set[str] = set()

        for frag in context["fragmentos"]:
            for sentence in extract_sentences(frag["texto"]):
                sentence_key = normalize_text(sentence)
                if (
                    8 <= len(sentence.split()) <= 45
                    and not _URL_PATTERN.search(sentence)
                    and re.search(r'[.!?…»”")]$', sentence)
                    and sentence_key not in seen_sentences
                ):
                    seen_sentences.add(sentence_key)
                    sentence_pairs.append((frag["etiqueta"], sentence))

        fragment_texts = [f["texto"] for f in context["fragmentos"]]
        frequent_terms = [
            term
            for term in extract_key_terms(fragment_texts, 24)
            if normalize_text(term) not in {"fuente", "licencia", "wikipedia"}
        ]
        key_terms = _extract_domain_terms(sentence_pairs, frequent_terms)

        request_info = context["solicitud"]
        builder_method = getattr(self, f"_{request_info['tipo']}", None)
        if builder_method is None:
            return {"recursos": []}

        built_resources: list[dict[str, Any]] = []
        for index in range(request_info["cantidad"]):
            resource = builder_method(index, sentence_pairs, key_terms, context)
            if resource and all(resource["contenido"] != item["contenido"] for item in built_resources):
                built_resources.append(resource)

        return {"recursos": built_resources}

    @staticmethod
    def _find_matching_pair(
        sentence_pairs: list[tuple[str, str]], terms: list[str], index: int
    ) -> tuple[str, str, str] | None:
        """Selecciona de forma determinista una oración que contenga uno de los términos."""
        matches = [
            (tag, sentence, term)
            for term in terms
            for tag, sentence in sentence_pairs
            if _contains_word(sentence, term)
        ]
        return matches[(index * 3) % len(matches)] if matches else None

    def _item_opcion_multiple(
        self,
        index: int,
        sentence_pairs: list[tuple[str, str]],
        terms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Construye un ítem de opción múltiple ocultando la palabra clave."""
        options_count = context["solicitud"]["alternativas"]
        matches = [
            (tag, sentence, term)
            for term in terms
            for tag, sentence in sentence_pairs
            if _contains_word(sentence, term)
        ]

        for offset in range(len(matches)):
            tag, sentence, key_term = matches[(index * 3 + offset) % len(matches)]
            candidates = [
                term
                for term in terms
                if not _are_related_terms(key_term, term) and not _contains_word(sentence, term)
            ]
            head_word = normalize_text(key_term.split()[0])
            candidates.sort(key=lambda term: normalize_text(term.split()[0]) != head_word)

            distractors: list[str] = []
            for candidate in candidates:
                if not any(_are_related_terms(candidate, dist) for dist in distractors):
                    distractors.append(candidate)

            distractors = distractors[: options_count - 1]
            if len(distractors) < options_count - 1:
                continue

            origins = {
                dist: next((t for t, s in sentence_pairs if _contains_word(s, dist)), tag)
                for dist in distractors
            }

            alternatives: list[dict[str, Any]] = [
                {
                    "texto": key_term,
                    "correcta": True,
                    "fragmentos": [tag],
                    "retroalimentacion": f"Correcto. El material lo afirma así: «{sentence}»",
                }
            ]
            alternatives += [
                {
                    "texto": dist,
                    "correcta": False,
                    "fragmentos": [origins[dist]],
                    "retroalimentacion": (
                        f"Incorrecto. «{dist}» aparece en el material, pero con otro sentido. "
                        f"La afirmación original es: «{sentence}»"
                    ),
                }
                for dist in distractors
            ]

            return {
                "titulo": f"Concepto clave {index + 1}: {context['unidad']['titulo']}",
                "contenido": (
                    "Según el material de la unidad, ¿qué término completa correctamente la siguiente afirmación?\n\n"
                    f"«{_mask_target_word(sentence, key_term)}»"
                ),
                "citas": [{"afirmacion": sentence, "fragmentos": [tag]}],
                "alternativas": alternatives,
            }
        return None

    def _pregunta_detonante(
        self,
        index: int,
        sentence_pairs: list[tuple[str, str]],
        terms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        matched = self._find_matching_pair(sentence_pairs, terms, index)
        if not matched:
            return None
        tag, sentence, term = matched
        return {
            "titulo": f"¿Qué sabes sobre {term}?",
            "contenido": (
                f"Situación para iniciar la clase:\n«{sentence}»\n\n"
                f"Pregunta detonante: ¿Dónde has visto {term} en tu vida diaria y qué pasaría si no existiera? "
                "Comparte una respuesta breve antes de revisar el tema."
            ),
            "citas": [{"afirmacion": sentence, "fragmentos": [tag]}],
            "alternativas": [],
        }

    def _sondeo_diagnostico(
        self,
        index: int,
        sentence_pairs: list[tuple[str, str]],
        terms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        selected_pairs = sentence_pairs[index * 4 : index * 4 + 4] or sentence_pairs[:4]
        if len(selected_pairs) < 2:
            return None

        statements: list[str] = []
        answers_key: list[str] = []
        citations: list[dict[str, Any]] = []

        for num, (tag, sentence) in enumerate(selected_pairs, start=1):
            replacement = next(
                (
                    (p, q)
                    for p in terms
                    if _contains_word(sentence, p)
                    for q in terms
                    if q != p
                    and _share_head_word(p, q)
                    and not _are_related_terms(p, q)
                    and not _contains_word(sentence, q)
                ),
                None,
            )

            if num % 2 == 0 and replacement:
                false_statement = re.sub(
                    rf"(?<!\w){re.escape(replacement[0])}(?!\w)",
                    replacement[1],
                    sentence,
                    count=1,
                    flags=re.IGNORECASE,
                )
                statements.append(f"{num}. {false_statement} (V / F)")
                answers_key.append(f"{num}. Falso: el material dice «{sentence}»")
            else:
                statements.append(f"{num}. {sentence} (V / F)")
                answers_key.append(f"{num}. Verdadero")

            citations.append({"afirmacion": sentence, "fragmentos": [tag]})

        body_content = (
            "Marca verdadero (V) o falso (F) antes de empezar el tema:\n"
            + "\n".join(statements)
            + "\n\nClave para el docente:\n"
            + "\n".join(answers_key)
        )
        return {
            "titulo": f"Sondeo de ideas previas: {context['unidad']['titulo']}",
            "contenido": body_content,
            "citas": citations,
            "alternativas": [],
        }

    def _guia_exploracion(
        self,
        index: int,
        sentence_pairs: list[tuple[str, str]],
        terms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        if len(sentence_pairs) < 2 or len(terms) < 2:
            return None
        tag_1, sent_1 = sentence_pairs[(index * 2) % len(sentence_pairs)]
        tag_2, sent_2 = sentence_pairs[(index * 2 + 1) % len(sentence_pairs)]
        term_1, term_2 = terms[index % len(terms)], terms[(index + 1) % len(terms)]

        content = (
            f"Objetivo: explorar {term_1} y su relación con {term_2}.\n\nPasos:\n"
            f"1. Lee este fragmento del material: «{sent_1}»\n"
            f"2. Subraya las palabras clave y escribe con tus palabras qué es {term_1}.\n"
            f"3. Lee este otro fragmento: «{sent_2}»\n"
            f"4. Compara ambos fragmentos: ¿qué tienen en común {term_1} y {term_2}? Anótalo en una tabla.\n"
            "5. Escribe una pregunta que te gustaría investigar sobre el tema.\n\n"
            "Registro: anota tus observaciones y compártelas con tu grupo."
        )
        return {
            "titulo": f"Guía de exploración: {term_1}",
            "contenido": content,
            "citas": [
                {"afirmacion": sent_1, "fragmentos": [tag_1]},
                {"afirmacion": sent_2, "fragmentos": [tag_2]},
            ],
            "alternativas": [],
        }

    def _caso_indagacion(
        self,
        index: int,
        sentence_pairs: list[tuple[str, str]],
        terms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        if len(sentence_pairs) < 2 or not terms:
            return None
        tag_1, sent_1 = sentence_pairs[(index * 2) % len(sentence_pairs)]
        tag_2, sent_2 = sentence_pairs[(index * 2 + 1) % len(sentence_pairs)]
        term_1 = terms[index % len(terms)]
        term_2 = terms[(index + 1) % len(terms)] if len(terms) > 1 else term_1

        content = (
            f"Caso: {sent_1} {sent_2}\n\nPreguntas de indagación:\n"
            f"1. ¿Qué papel cumple {term_1} en este caso?\n"
            f"2. ¿Qué pasaría si cambiara {term_2}?\n"
            "3. ¿Qué evidencia del material respalda tu respuesta?\n"
            "4. ¿En qué otra situación de tu entorno ocurre algo parecido?"
        )
        return {
            "titulo": f"Caso para indagar: {term_1}",
            "contenido": content,
            "citas": [
                {"afirmacion": sent_1, "fragmentos": [tag_1]},
                {"afirmacion": sent_2, "fragmentos": [tag_2]},
            ],
            "alternativas": [],
        }

    def _explicacion(
        self,
        index: int,
        sentence_pairs: list[tuple[str, str]],
        terms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        order_index = {pair: n for n, pair in enumerate(sentence_pairs)}
        scored_pairs = sorted(
            sentence_pairs, key=lambda pair: -sum(_contains_word(pair[1], term) for term in terms[:10])
        )
        selected = sorted(
            scored_pairs[index * 4 : index * 4 + 4] or scored_pairs[:4],
            key=lambda item: order_index.get(item, 0),
        )
        if not selected:
            return None

        topic = terms[0] if terms else context["unidad"]["titulo"]
        return {
            "titulo": f"{_capitalize_first(topic)}: explicación del material",
            "contenido": "\n\n".join(sentence for _, sentence in selected),
            "citas": [{"afirmacion": sentence, "fragmentos": [tag]} for tag, sentence in selected],
            "alternativas": [],
        }

    def _glosario(
        self,
        index: int,
        sentence_pairs: list[tuple[str, str]],
        terms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        glossary_entries: list[str] = []
        citations: list[dict[str, Any]] = []

        for term in terms[index * 8 :]:
            matched_definition = next(
                (
                    (tag, sentence)
                    for tag, sentence in sentence_pairs
                    if _contains_word(sentence, term)
                    and re.search(
                        r"\b(es|son|se define|consiste|significa|permite)\b", sentence, re.IGNORECASE
                    )
                ),
                None,
            ) or next(
                ((tag, sentence) for tag, sentence in sentence_pairs if _contains_word(sentence, term)),
                None,
            )

            if matched_definition:
                glossary_entries.append(f"{_capitalize_first(term)}: {matched_definition[1]}")
                citations.append(
                    {"afirmacion": matched_definition[1], "fragmentos": [matched_definition[0]]}
                )

            if len(glossary_entries) == 8:
                break

        if len(glossary_entries) < 3:
            return None

        return {
            "titulo": f"Glosario: {context['unidad']['titulo']}",
            "contenido": "\n".join(glossary_entries),
            "citas": citations,
            "alternativas": [],
        }

    def _ejercicio_aplicacion(
        self,
        index: int,
        sentence_pairs: list[tuple[str, str]],
        terms: list[str],
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        matched = self._find_matching_pair(sentence_pairs, terms, index)
        if not matched:
            return None
        tag, sentence, term = matched
        content = (
            f"Idea del material: «{sentence}»\n\n"
            f"Consigna: aplica {term} a una situación nueva de tu entorno (tu institución o comunidad). "
            "Describe la situación, explica paso a paso cómo intervendría y qué resultado esperas.\n\n"
            f"Criterios de logro:\n- Usa correctamente el concepto de {term}.\n"
            "- Justifica cada paso con ideas del material.\n- Presenta una conclusión clara."
        )
        return {
            "titulo": f"Ejercicio de aplicación: {term}",
            "contenido": content,
            "citas": [{"afirmacion": sentence, "fragmentos": [tag]}],
            "alternativas": [],
        }