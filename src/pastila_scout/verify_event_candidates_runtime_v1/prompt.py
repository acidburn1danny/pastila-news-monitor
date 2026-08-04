"""Exact legacy event-verification task construction and neutral serialization."""

import json

from pastila_scout.ai.provider import StructuredAIRequest
from pastila_scout.models.ai import (
    EventVerificationRequest,
    ProviderVerificationDecision,
)

_INSTRUCTIONS = (
    "Compare only the supplied confirmed facts. Decide whether both "
    "articles describe the same concrete real-world event. Unknown "
    "entities must be null. Keep reasoning concise."
)


def build_event_verification_task(
    request: EventVerificationRequest,
) -> StructuredAIRequest:
    """Reproduce the existing structured task without editorial changes."""

    return StructuredAIRequest(
        name="event_verification",
        instructions=_INSTRUCTIONS,
        input_json=json.dumps(request.model_dump(mode="json"), ensure_ascii=False),
        json_schema=ProviderVerificationDecision.model_json_schema(),
    )


def serialize_event_verification_task(task: StructuredAIRequest) -> str:
    """Carry the exact structured task fields through the one-prompt authority."""

    return json.dumps(
        {
            "name": task.name,
            "instructions": task.instructions,
            "input_json": task.input_json,
            "json_schema": task.json_schema,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


__all__ = ("build_event_verification_task", "serialize_event_verification_task")
