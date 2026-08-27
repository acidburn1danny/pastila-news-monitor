"""Proof-neutral canonical serialization and deterministic span rendering."""

from __future__ import annotations

import hashlib
import json
from itertools import pairwise

from .models import (
    DeterministicVoiceResultV1,
    RenderedProvenanceSpanV1,
    RenderOutcomeV1,
)


class DeterministicVoiceValidationError(ValueError):
    pass


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_ir_bytes(ir) -> bytes:
    return json.dumps(
        ir.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def render_governed_spans(
    ir, *, mismatch_message: str = "rendered bytes differ from expected identity"
) -> DeterministicVoiceResultV1:
    ir_identity = _sha256(canonical_ir_bytes(ir))
    parts: list[str] = []
    provenance: list[RenderedProvenanceSpanV1] = []
    cursor = 0
    for span in ir.spans:
        parts.append(span.text)
        end = cursor + len(span.text)
        provenance.append(
            RenderedProvenanceSpanV1(
                start=cursor,
                end=end,
                provenance_class=span.provenance_class,
                source_identity=span.source_identity,
                fictional_actor_id=span.fictional_actor_id,
                nonliteral_mapping_id=span.nonliteral_mapping_id,
                callback_id=span.callback_id,
                expression_binding=span.expression_binding,
            )
        )
        cursor = end
    output = "".join(parts).encode("utf-8")
    output_sha = _sha256(output)
    if output_sha != ir.expected_output_sha256:
        raise DeterministicVoiceValidationError(mismatch_message)
    if not provenance or provenance[0].start != 0 or provenance[-1].end != cursor:
        raise DeterministicVoiceValidationError("incomplete provenance coverage")
    if any(left.end != right.start for left, right in pairwise(provenance)):
        raise DeterministicVoiceValidationError("overlapping or uncovered provenance")
    return DeterministicVoiceResultV1(
        outcome=RenderOutcomeV1.ACCEPTED,
        commentary_bytes=output,
        output_sha256=output_sha,
        provenance=tuple(provenance),
        ir_identity=ir_identity,
        result_identity=_sha256(f"{ir_identity}:accepted:{output_sha}".encode()),
    )


__all__ = [
    "DeterministicVoiceValidationError",
    "canonical_ir_bytes",
    "render_governed_spans",
]
