"""
Verificación de anclaje (HU-016): cada afirmación que cita el material se contrasta con la evidencia recuperada, y lo
que no tiene respaldo se rechaza con su motivo. Alimenta el indicador I21 (tasa de alucinación).

El respaldo de una afirmación es la proporción de sus palabras útiles (sin vacías, con su raíz) que aparecen en los
fragmentos que cita. Dos palabras coinciden si tienen la misma raíz o comparten sus seis primeras letras
(«confirma» y «confirmación», pero no «confirma» y «confiable»). Es una regla por palabras y explicable: no entiende sinónimos, y la búsqueda por
significado (EN-013) podrá reforzarla.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from platform5e.domain.materials.text_analysis import extract_terms

DEFAULT_THRESHOLD: float = 0.6
SHARED_PREFIX: int = 6
# Un recurso se rechaza si menos de esta proporción de sus afirmaciones tiene respaldo.
MIN_SUPPORTED_SHARE: float = 0.5
# Una afirmación con menos palabras útiles no se puede contrastar: se rechaza.
MIN_CLAIM_TERMS: int = 2


def _matches(term: str, evidence_terms: set[str], evidence_prefixes: set[str]) -> bool:
    return term in evidence_terms or (len(term) >= SHARED_PREFIX and term[:SHARED_PREFIX] in evidence_prefixes)


def terms_support(terms: set[str], evidence_texts: list[str]) -> float:
    """Proporción (0 a 1) de los términos (ya extraídos con `extract_terms`) que aparecen en los textos de evidencia."""
    if not terms:
        return 0.0
    evidence_terms = {term for text in evidence_texts for term in extract_terms(text)}
    evidence_prefixes = {term[:SHARED_PREFIX] for term in evidence_terms if len(term) >= SHARED_PREFIX}
    found = sum(1 for term in terms if _matches(term, evidence_terms, evidence_prefixes))
    return found / len(terms)


def claim_support(claim: str, evidence_texts: list[str]) -> float:
    """Proporción (0 a 1) de las palabras útiles de la afirmación que aparecen en los textos de evidencia."""
    return terms_support(set(extract_terms(claim)), evidence_texts)


@dataclass
class ClaimCheck:
    """Resultado de contrastar una afirmación con la evidencia."""

    claim: str
    fragment_ids: list[str]
    support: float
    supported: bool
    reason: str | None = None
    corrected: bool = False  # la respaldaba otro fragmento recuperado, no el que citó

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"claim": self.claim, "support": round(self.support, 2), "supported": self.supported}
        if self.reason:
            data["reason"] = self.reason
        if self.corrected:
            data["corrected"] = True
        return data


@dataclass
class GroundingResult:
    """Verificación de todas las afirmaciones de un recurso."""

    checks: list[ClaimCheck] = field(default_factory=list)
    threshold: float = DEFAULT_THRESHOLD

    @property
    def supported(self) -> list[ClaimCheck]:
        return [check for check in self.checks if check.supported]

    @property
    def unsupported(self) -> list[ClaimCheck]:
        return [check for check in self.checks if not check.supported]

    @property
    def accepted(self) -> bool:
        """El recurso se conserva si tiene afirmaciones respaldadas y son al menos la mitad."""
        return bool(self.supported) and len(self.supported) / len(self.checks) >= MIN_SUPPORTED_SHARE

    def rejection_reason(self, title: str) -> str:
        if not self.checks:
            return f"«{title}» no cita ninguna afirmación del material."
        return (
            f"«{title}»: {len(self.unsupported)} de {len(self.checks)} afirmaciones sin respaldo en el material "
            f"(p. ej. «{_short(self.unsupported[0].claim)}»)."
        )

    def summary(self) -> dict[str, Any]:
        """Lo que se guarda en el recurso para la revisión y para calcular I21."""
        return {
            "threshold": self.threshold,
            "checkedClaims": len(self.checks),
            "supportedClaims": len(self.supported),
            "correctedClaims": sum(1 for check in self.supported if check.corrected),
            "removedClaims": [check.as_dict() for check in self.unsupported],
        }


def _short(text: str, limit: int = 80) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def check_claim(
    claim: str,
    cited_ids: list[str],
    fragments_by_id: dict[str, str],
    threshold: float = DEFAULT_THRESHOLD,
) -> ClaimCheck:
    """Contrasta una afirmación con los fragmentos que cita y, si no la respaldan, con el resto de lo recuperado."""
    if len(set(extract_terms(claim))) < MIN_CLAIM_TERMS:
        return ClaimCheck(claim, cited_ids, 0.0, False, "La afirmación es demasiado breve para contrastarla.")

    support = claim_support(claim, [fragments_by_id[f_id] for f_id in cited_ids if f_id in fragments_by_id])
    if support >= threshold:
        return ClaimCheck(claim, cited_ids, support, True)

    # El modelo pudo citar la etiqueta equivocada: se busca el fragmento recuperado que mejor la respalda.
    best_id, best_support = None, support
    for fragment_id, text in fragments_by_id.items():
        candidate = claim_support(claim, [text])
        if candidate > best_support:
            best_id, best_support = fragment_id, candidate
    if best_id is not None and best_support >= threshold:
        return ClaimCheck(claim, [best_id], best_support, True, corrected=True)

    return ClaimCheck(
        claim,
        cited_ids,
        support,
        False,
        f"Solo el {round(support * 100)} % de sus palabras aparece en los fragmentos citados "
        f"(mínimo {round(threshold * 100)} %).",
    )


def verify_citations(
    citations: list[dict[str, Any]],
    fragments_by_id: dict[str, str],
    threshold: float = DEFAULT_THRESHOLD,
) -> GroundingResult:
    """Verifica cada cita `{"claim", "fragmentIds"}` de un recurso contra la evidencia recuperada."""
    result = GroundingResult(threshold=threshold)
    for citation in citations:
        result.checks.append(
            check_claim(citation["claim"], list(citation["fragmentIds"]), fragments_by_id, threshold)
        )
    return result


def hallucination_rate(checked: int, unsupported: int) -> float | None:
    """I21: afirmaciones sin respaldo / afirmaciones verificadas (None si no se verificó ninguna)."""
    return round(unsupported / checked, 4) if checked else None
