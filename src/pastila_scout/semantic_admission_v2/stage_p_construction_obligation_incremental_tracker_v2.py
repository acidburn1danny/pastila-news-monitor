"""Request-bound incremental prefix tracker for the V2 full-ledger character DFA."""
from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .stage_p_construction_obligation_constraint_v2 import (
    StagePConstructionObligationConstraintStateV2,
)
from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1


class StagePConstructionObligationTrackerViolationV2(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ConstructionObligationPrefixResultV2:
    state: StagePConstructionObligationConstraintStateV2
    decoded: str
    decoded_sha256: str
    token_ids: tuple[int, ...]
    path: str
    suffix_characters: int
    context_identity: str
    decoder_identity: str


class StagePConstructionObligationIncrementalTrackerV2:
    """Track one immutable context and one externally bound decoder identity."""

    def __init__(self, *, context: SourceReferenceConstraintContextV1,
                 decoder_identity: str) -> None:
        if not decoder_identity:
            raise ValueError("DECODER_IDENTITY_REQUIRED")
        self.context = context
        self.decoder_identity = decoder_identity
        self._last_ids: tuple[int, ...] = ()
        self._last_decoded = ""
        self._last_state = StagePConstructionObligationConstraintStateV2.for_context(context)
        self.incremental_steps = 0
        self.rebuild_steps = 0

    def state_for(
        self, token_ids: Sequence[int], decode: Callable[[Sequence[int]], str],
    ) -> ConstructionObligationPrefixResultV2:
        ids = tuple(token_ids)
        decoded = decode(ids)
        if type(decoded) is not str:
            raise StagePConstructionObligationTrackerViolationV2("DECODE_OUTPUT_NOT_STRING")
        if ids == self._last_ids and decoded != self._last_decoded:
            raise StagePConstructionObligationTrackerViolationV2(
                "DECODE_INSTABILITY_FOR_IDENTICAL_TOKEN_IDS")
        extends = (len(ids) >= len(self._last_ids) and
                   ids[:len(self._last_ids)] == self._last_ids)
        if extends and decoded.startswith(self._last_decoded):
            suffix = decoded[len(self._last_decoded):]
            state = self._last_state.feed(suffix)
            path = "INCREMENTAL"
            self.incremental_steps += 1
        else:
            suffix = decoded
            state = StagePConstructionObligationConstraintStateV2.for_context(
                self.context).feed(decoded)
            path = "FULL_REBUILD"
            self.rebuild_steps += 1
        self._last_ids = ids
        self._last_decoded = decoded
        self._last_state = state
        return ConstructionObligationPrefixResultV2(
            state=state, decoded=decoded,
            decoded_sha256=hashlib.sha256(decoded.encode("utf-8")).hexdigest(),
            token_ids=ids, path=path, suffix_characters=len(suffix),
            context_identity=self.context.binding_identity,
            decoder_identity=self.decoder_identity,
        )


__all__ = (
    "ConstructionObligationPrefixResultV2",
    "StagePConstructionObligationIncrementalTrackerV2",
    "StagePConstructionObligationTrackerViolationV2",
)
