"""Evaluation-only, no-repair source membership checks for Gate F reason spans."""
from __future__ import annotations

from dataclasses import dataclass

from .models import GateResponseV2


@dataclass(frozen=True)
class SpanSourceViolationV1(ValueError):
    code: str
    record_index: int

    def __str__(self) -> str:
        return f"{self.code}:reason_records[{self.record_index}]"


def validate_reason_span_sources_v1(*, raw_response: str, factual_summary: str, candidate: str) -> GateResponseV2:
    response = GateResponseV2.model_validate_json(raw_response, strict=True)
    for index, record in enumerate(response.reason_records):
        if record.candidate_span is not None and record.candidate_span not in candidate:
            raise SpanSourceViolationV1("CANDIDATE_SPAN_NOT_IN_CANDIDATE", index)
        if record.authority_support is not None and record.authority_support not in factual_summary:
            raise SpanSourceViolationV1("AUTHORITY_SUPPORT_NOT_IN_FACTUAL_SUMMARY", index)
    return response


__all__ = ("SpanSourceViolationV1", "validate_reason_span_sources_v1")
