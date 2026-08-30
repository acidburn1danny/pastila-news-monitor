"""Mechanism-blind, pathless DEVELOPMENT constructor boundary V1.

The constructor accepts only canonical packet bytes. It imports no filesystem,
environment, process, network, model, taxonomy, or repository facilities.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class DevelopmentConstructionResultV1:
    terminal_classification: str
    failure_code: str | None
    candidate_surface_utf8: bytes | None
    constructor_visible_sha256: str


def construct_development_candidate_v1(*, constructor_packet_bytes: bytes) -> DevelopmentConstructionResultV1:
    """Perform one attempt using no authority beyond the supplied bytes."""
    visible_sha = hashlib.sha256(constructor_packet_bytes).hexdigest()
    packet: dict[str, Any] = json.loads(constructor_packet_bytes)
    if packet.get("status") != "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION":
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "CONSTRUCTOR_PACKET_STATUS_INVALID", None, visible_sha)
    if packet.get("creative_premise_family_id") != "UNASSIGNED":
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "CREATIVE_PREMISE_PREASSIGNED", None, visible_sha)
    # Hashes and coordinates authorize claims but cannot supply the lexical source
    # material needed to preserve exact Romanian assertions. Inventing that material
    # would widen factual authority, so the clean-room constructor fails closed.
    source = packet.get("source_object", {})
    if not isinstance(source.get("source_text_utf8"), str):
        return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                               "CONSTRUCTOR_SOURCE_SURFACE_UNAVAILABLE", None, visible_sha)
    return DevelopmentConstructionResultV1("TECHNICAL_FAILURE_BEFORE_CANDIDATE",
                                           "NO_AUTHORIZED_REALIZATION_ENGINE_V1", None, visible_sha)


__all__ = ["DevelopmentConstructionResultV1", "construct_development_candidate_v1"]
