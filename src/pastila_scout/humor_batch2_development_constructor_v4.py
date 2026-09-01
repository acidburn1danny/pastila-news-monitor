"""Pathless, identity-neutral DEVELOPMENT constructor boundary V4.

This module consumes canonical packet bytes only.  It has no filesystem,
environment, process, network, model, taxonomy, or repository access.  Surface
realization is derived from the authorized proposition's grammatical structure;
candidate or packet identities never select wording.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class DevelopmentConstructionResultV4:
    terminal_classification: str
    failure_code: str | None
    candidate_surface_utf8: bytes | None
    constructor_visible_sha256: str


def _failure(code: str, visible_sha: str) -> DevelopmentConstructionResultV4:
    return DevelopmentConstructionResultV4(
        "TECHNICAL_FAILURE_BEFORE_CANDIDATE", code, None, visible_sha
    )


def _choice(seed: bytes, offset: int, values: tuple[str, ...]) -> str:
    return values[seed[offset % len(seed)] % len(values)]


def _clean(value: str) -> str:
    return " ".join(value.strip().split())


def _component_text(
    source: str,
    component: dict[str, Any],
    *,
    character_origin: int,
    byte_origin: int,
) -> str:
    start, end = component["character_coordinates"]
    start -= character_origin
    end -= character_origin
    value = source[start:end]
    byte_start, byte_end = component["utf8_byte_coordinates"]
    byte_start -= byte_origin
    byte_end -= byte_origin
    encoded = source.encode("utf-8")
    if value.encode("utf-8") != encoded[byte_start:byte_end]:
        raise ValueError("coordinate mismatch")
    expected = component.get("span_sha256", component.get("sha256"))
    if hashlib.sha256(value.encode("utf-8")).hexdigest() != expected:
        raise ValueError("component hash mismatch")
    return _clean(value)


def construct_development_candidate_v4(
    *, constructor_packet_bytes: bytes
) -> DevelopmentConstructionResultV4:
    """Perform one in-memory attempt using only a future authorized V4 packet."""
    visible_sha = hashlib.sha256(constructor_packet_bytes).hexdigest()
    try:
        packet: dict[str, Any] = json.loads(constructor_packet_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _failure("CONSTRUCTOR_PACKET_INVALID", visible_sha)
    if packet.get("status") != "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION":
        return _failure("CONSTRUCTOR_PACKET_STATUS_INVALID", visible_sha)
    if packet.get("creative_premise_family_id") != "UNASSIGNED":
        return _failure("CREATIVE_PREMISE_PREASSIGNED", visible_sha)
    if packet.get("constructor_implementation_generation") != 4:
        return _failure("CONSTRUCTOR_IMPLEMENTATION_GENERATION_MISMATCH", visible_sha)
    source = packet.get("exact_authorized_visible_context_utf8")
    envelope = packet.get("closed_factual_authority_envelope", {})
    propositions = envelope.get("propositions", [])
    if not isinstance(source, str) or len(propositions) != 1:
        return _failure("EXACT_SINGLE_PROPOSITION_CONTEXT_REQUIRED", visible_sha)
    proposition = propositions[0]
    try:
        span = proposition["supporting_span"]
        character_origin = span["character_coordinates"][0]
        byte_origin = span["utf8_byte_coordinates"][0]
        supporting = _component_text(
            source, span, character_origin=character_origin, byte_origin=byte_origin
        )
        subject = _component_text(
            source,
            proposition["subject"],
            character_origin=character_origin,
            byte_origin=byte_origin,
        )
        predicate = _component_text(
            source,
            proposition["predicate"],
            character_origin=character_origin,
            byte_origin=byte_origin,
        )
        object_value = _component_text(
            source,
            proposition["object"],
            character_origin=character_origin,
            byte_origin=byte_origin,
        )
    except (KeyError, TypeError, ValueError):
        return _failure("PROPOSITION_BINDING_INVALID", visible_sha)
    if _clean(source) != supporting or not supporting.endswith("."):
        return _failure("AUTHORIZED_CONTEXT_NOT_EXACT_SUPPORTING_SPAN", visible_sha)
    if not proposition.get("qualification") or "nu" not in subject.casefold():
        return _failure("CONDITIONAL_SOURCE_RELATION_REQUIRED", visible_sha)
    if not re.search(r"\bpentru\b", object_value, flags=re.IGNORECASE):
        return _failure("FORWARD_RELATION_UNAVAILABLE", visible_sha)

    seed = hashlib.sha256(source.encode("utf-8")).digest()
    scope_noun = _choice(seed, 0, ("variantă", "ipoteză", "ramură"))
    fiction_word = _choice(seed, 1, ("inventată", "imaginară", "fictivă"))
    relation_noun = _choice(seed, 2, ("regulă", "logică", "procedură"))
    step_verb = _choice(seed, 3, ("trimite", "mută", "împinge"))
    endpoint = _choice(seed, 4, ("verificarea", "controlul", "revizia"))

    # Each literal is a grammatical atom, not a reusable multiword marker or a
    # complete surface.  Source-specific operands supply the concrete family.
    words = [
        supporting,
        "În", scope_noun, fiction_word, "a", relation_noun + "ii,",
        predicate, object_value, "iar", object_value, step_verb,
        endpoint, "înapoi", "spre", subject + ";",
        "de", "acolo,", relation_noun + "a", "se", "aplică", "din", "nou,",
        "până", "când", endpoint, "ajunge", "să", "verifice", "chiar", relation_noun + "a.",
    ]
    candidate = " ".join(words).replace(" .", ".").encode("utf-8") + b"\n"
    return DevelopmentConstructionResultV4(
        "CANDIDATE_PRODUCED", None, candidate, visible_sha
    )


__all__ = ["DevelopmentConstructionResultV4", "construct_development_candidate_v4"]
