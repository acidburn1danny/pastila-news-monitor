"""Deterministic surface candidate extraction; never semantic adjudication."""

from __future__ import annotations

import re
import unicodedata

from .models import (
    AuthorityClass,
    AuthorityPassageV1,
    CandidateKind,
    SurfaceCandidateV1,
)
from .persistence import canonical_identity

_QUANTITY = re.compile(
    r"(?i)\b(?:(aproximativ|circa|peste|cel puțin|maximum|minimum)\s+)?\d[\d. ,]*(?:%|\s+(?:de\s+)?(?:lei|euro|dolari|persoane|oameni|tranzacții|state|metri|ani|luni|zile|ore))\b"
)
_DATE = re.compile(r"\b(?:[0-3]?\d[./-][01]?\d[./-]\d{2,4}|[0-2]?\d:[0-5]\d)\b")
_ENTITY = re.compile(
    r"\b(?:[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț.-]+(?:\s+[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț.-]+){0,4})\b"
)
_MARKERS = {
    CandidateKind.ALLEGATION_MARKER: re.compile(
        r"(?i)\b(?:ar fi|acuză că|acuzați(?:e|i)|susține că)\b"
    ),
    CandidateKind.UNCERTAINTY_MARKER: re.compile(
        r"(?i)\b(?:nu se știe|rămâne o suspiciune|posibil(?:ă)?|disputat(?:ă)?|contestă|poate fi contestat(?:ă)?)\b"
    ),
    CandidateKind.ATTRIBUTION_MARKER: re.compile(
        r"(?i)\b(?:potrivit|conform|spune că|susține că|raportat(?:ă)?)\b"
    ),
}


def extract_surface_candidates(
    *,
    authority_class: AuthorityClass,
    authority_identity: str,
    source_identity: str,
    text: str,
) -> tuple[SurfaceCandidateV1, ...]:
    """Extract closed lexical surfaces, all still requiring human adjudication."""
    matches: list[tuple[int, int, CandidateKind]] = []
    for match in _QUANTITY.finditer(text):
        matches.append((match.start(), match.end(), CandidateKind.COMPLETE_QUANTITY))
    for match in _DATE.finditer(text):
        matches.append((match.start(), match.end(), CandidateKind.DATE_TIME))
    for match in _ENTITY.finditer(text):
        matches.append((match.start(), match.end(), CandidateKind.NAMED_ENTITY))
    for kind, pattern in _MARKERS.items():
        for match in pattern.finditer(text):
            matches.append((match.start(), match.end(), kind))
    seen: set[tuple[int, int, CandidateKind]] = set()
    result = []
    for start, end, kind in sorted(
        matches, key=lambda item: (item[0], item[1], item[2].value)
    ):
        if (start, end, kind) in seen:
            continue
        seen.add((start, end, kind))
        passage = text[start:end]
        evidence = AuthorityPassageV1(
            authority_class=authority_class,
            authority_identity=authority_identity,
            source_identity=source_identity,
            passage=passage,
            start=start,
            end=end,
        )
        seed = {"kind": kind.value, "evidence": evidence.model_dump(mode="json")}
        receipt = canonical_identity(
            {"policy": "voice-fact-candidate-extraction-v1", "candidate": seed}
        )
        result.append(
            SurfaceCandidateV1(
                candidate_id=f"candidate:{receipt}",
                kind=kind,
                evidence=evidence,
                normalized_key=unicodedata.normalize("NFKC", passage).casefold(),
                extraction_receipt_identity=receipt,
            )
        )
    return tuple(result)
