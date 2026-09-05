"""Passive Milestone 10 Phase 1 authority design for a bounded Crossref pilot."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

FOUNDATION_COMMIT = "3fa29f45ae3d4ee57b495f39dc5518776c5c2da2"
SCHEMA = "pastila-crossref-pilot-authority-design-v1"


@dataclass(frozen=True, slots=True)
class CrossrefPilotAuthorityDesignV1:
    """Owner-approved Phase 1 boundary without transport authority."""

    schema: str
    foundation_commit: str
    phase: str
    status: str
    registry: str
    transport: str
    request_count: int
    maximum_records: int
    raw_and_normalized_storage: str
    unresolved_owner_values: tuple[str, ...]
    prohibited: tuple[str, ...]


def build_crossref_pilot_authority_design_v1() -> CrossrefPilotAuthorityDesignV1:
    """Return the exact passive Phase 1 design; performs no I/O."""

    return CrossrefPilotAuthorityDesignV1(
        schema=SCHEMA,
        foundation_commit=FOUNDATION_COMMIT,
        phase="MILESTONE_10_PHASE_1",
        status="DESIGN_ONLY_NOT_AUTHORIZED_FOR_CAPTURE",
        registry="CROSSREF_ONLY",
        transport="READ_ONLY_HTTPS",
        request_count=1,
        maximum_records=10,
        raw_and_normalized_storage="SEPARATE_IDENTITY_DOMAINS",
        unresolved_owner_values=("EXACT_ENDPOINT", "EXACT_DETERMINISTIC_QUERY"),
        prohibited=(
            "DOWNSTREAM_PUBLISHING",
            "METADATA_ACQUISITION",
            "NETWORK_REQUESTS",
            "OPENALEX",
            "PHASE_2_EXECUTION",
            "RFC3161",
            "SCHEDULED_ACTIVATION",
            "SIGSTORE",
        ),
    )


def canonical_authority_design_bytes_v1(
    design: CrossrefPilotAuthorityDesignV1,
) -> bytes:
    """Serialize the exact design deterministically without accepting substitutes."""

    if design != build_crossref_pilot_authority_design_v1():
        raise ValueError("Crossref pilot authority design is not canonical")
    return (
        json.dumps(
            asdict(design),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def crossref_pilot_authority_design_identity_v1(
    design: CrossrefPilotAuthorityDesignV1,
) -> str:
    """Return the SHA-256 identity of the canonical passive design."""

    return hashlib.sha256(canonical_authority_design_bytes_v1(design)).hexdigest()


__all__ = (
    "FOUNDATION_COMMIT",
    "SCHEMA",
    "CrossrefPilotAuthorityDesignV1",
    "build_crossref_pilot_authority_design_v1",
    "canonical_authority_design_bytes_v1",
    "crossref_pilot_authority_design_identity_v1",
)
