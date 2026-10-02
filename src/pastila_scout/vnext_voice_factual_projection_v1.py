"""Evidence taxonomy and design primitives for constrained VOICE projection."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum

NUMBER = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)")


class FactualSafetyClass(StrEnum):
    SUPPORTED_COPY = "SUPPORTED_COPY"
    ENTAILED_DERIVATION = "ENTAILED_DERIVATION"
    SEMANTIC_EQUIVALENCE = "SEMANTIC_EQUIVALENCE"
    UNSUPPORTED_FACT = "UNSUPPORTED_FACT"


@dataclass(frozen=True)
class NumericClaim:
    surface: str
    classification: FactualSafetyClass
    support: tuple[str, ...]


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", "."))


def classify_numeric_claims(setup: str, commentary: str) -> tuple[NumericClaim, ...]:
    """Classify numeric surfaces conservatively against an immutable setup.

    This bounded classifier recognizes exact copies, exact pairwise differences,
    and lei/bani equivalence. Everything else remains unsupported. It does not
    claim to solve general semantic factuality.
    """
    source_surfaces = NUMBER.findall(setup)
    source_values = []
    for item in source_surfaces:
        try:
            source_values.append((item, _decimal(item)))
        except InvalidOperation:
            pass
    results = []
    for surface in NUMBER.findall(commentary):
        value = _decimal(surface)
        if surface in source_surfaces:
            results.append(NumericClaim(surface, FactualSafetyClass.SUPPORTED_COPY, (surface,)))
            continue
        differences = [(a, b) for a, av in source_values for b, bv in source_values if av > bv and av - bv == value]
        if differences:
            results.append(NumericClaim(surface, FactualSafetyClass.ENTAILED_DERIVATION, differences[0]))
            continue
        equivalence = []
        if re.search(rf"\b{re.escape(surface)}\s+(?:de\s+)?bani(?:i)?\b", commentary, re.I):
            equivalence = [src for src, val in source_values if val * 100 == value and re.search(rf"\b{re.escape(src)}\s+lei\b", setup, re.I)]
        if equivalence:
            results.append(NumericClaim(surface, FactualSafetyClass.SEMANTIC_EQUIVALENCE, (equivalence[0],)))
            continue
        results.append(NumericClaim(surface, FactualSafetyClass.UNSUPPORTED_FACT, ()))
    return tuple(results)


def projection_decision(setup: str, commentary: str) -> dict[str, object]:
    claims = classify_numeric_claims(setup, commentary)
    unsupported = [claim.surface for claim in claims if claim.classification is FactualSafetyClass.UNSUPPORTED_FACT]
    return {
        "decision": "REJECT_UNSUPPORTED_FACT" if unsupported else "ALLOW_NUMERIC_PROJECTION",
        "claims": [
            {"surface": claim.surface, "classification": claim.classification.value, "support": list(claim.support)}
            for claim in claims
        ],
        "unsupported": unsupported,
    }
