"""OpenAI benchmark-only early response diagnostics capture."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderClientRequest,
    AIProviderClientResponse,
)
from pastila_scout.editor.generation.controlled_revision_quality.provider_diagnostics import (
    ProviderUsageDiagnostic,
    ReferenceDiagnostic,
    build_reference_diagnostic,
    build_usage_diagnostic,
    hash_provider_request_id,
)


@dataclass(slots=True)
class EarlyProviderCapture:
    """Mutable per-trial state retained only inside the benchmark runner."""

    provider_call_started: bool = False
    provider_response_received: bool = False
    provider_latency_ms: float | None = None
    usage: ProviderUsageDiagnostic | None = None
    provider_request_id_hash: str | None = None
    references: ReferenceDiagnostic | None = None


class CapturingProviderClient:
    """Time one existing transport call without retrying or interpreting it."""

    def __init__(
        self,
        delegate: Any,
        capture: EarlyProviderCapture,
        clock: Callable[[], float] = monotonic,
        pre_request_validator: Callable[[AIProviderClientRequest], None] | None = None,
        request_transformer: (
            Callable[[AIProviderClientRequest], AIProviderClientRequest] | None
        ) = None,
    ) -> None:
        self.delegate = delegate
        self.capture = capture
        self.clock = clock
        self.pre_request_validator = pre_request_validator
        self.request_transformer = request_transformer

    def send(self, request: AIProviderClientRequest, *, credential_provider):
        if self.request_transformer is not None:
            request = self.request_transformer(request)
        if self.pre_request_validator is not None:
            self.pre_request_validator(request)
        self.capture.provider_call_started = True
        started = self.clock()
        try:
            response = self.delegate.send(
                request, credential_provider=credential_provider
            )
        finally:
            self.capture.provider_latency_ms = max(0.0, (self.clock() - started) * 1000)
        self.capture.provider_response_received = True
        return response


class CapturingOpenAIInterpreter:
    """Capture structural OpenAI response metadata before production interpretation."""

    def __init__(self, delegate: Any, capture: EarlyProviderCapture) -> None:
        self.delegate = delegate
        self.capture = capture

    def interpret(self, request: Any, response: AIProviderClientResponse):
        capture_openai_response_metadata(request, response, self.capture)
        return self.delegate.interpret(request, response)


def capture_openai_response_metadata(
    request: Any,
    response: AIProviderClientResponse,
    capture: EarlyProviderCapture,
) -> None:
    """Extract only usage, hashed correlation, and structural references."""

    raw = response.payload
    usage = getattr(raw, "usage", None)
    capture.usage = _usage(usage)
    capture.provider_request_id_hash = hash_provider_request_id(
        getattr(raw, "_request_id", None) or getattr(raw, "id", None)
    )
    if capture.provider_latency_ms is None:
        capture.provider_latency_ms = response.latency_ms
    produced = _references(raw)
    authorized = _authorized(request)
    registry = _registry(request)
    capture.references = build_reference_diagnostic(
        authorized=authorized,
        produced=produced,
        recognized_registry=registry,
    )


def _usage(value: Any) -> ProviderUsageDiagnostic:
    if value is None:
        return build_usage_diagnostic(prompt=None, completion=None, total=None)
    input_details = getattr(value, "input_tokens_details", None)
    output_details = getattr(value, "output_tokens_details", None)
    return build_usage_diagnostic(
        prompt=_non_negative(getattr(value, "input_tokens", None)),
        completion=_non_negative(getattr(value, "output_tokens", None)),
        total=_non_negative(getattr(value, "total_tokens", None)),
        cached_prompt_tokens=_non_negative(
            getattr(input_details, "cached_tokens", None)
        ),
        reasoning_tokens=_non_negative(
            getattr(output_details, "reasoning_tokens", None)
        ),
        input_audio_tokens=_non_negative(getattr(input_details, "audio_tokens", None)),
        output_audio_tokens=_non_negative(
            getattr(output_details, "audio_tokens", None)
        ),
    )


def _non_negative(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def _references(raw: Any) -> tuple[object, ...]:
    """Parse transient output and return reference fields only, never prose."""

    text = getattr(raw, "output_text", None)
    if not isinstance(text, str):
        return ()
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return ()
    if not isinstance(document, dict):
        return ()
    components = document.get("revised_components")
    if not isinstance(components, list):
        return ()
    return tuple(
        item.get("component_reference") if isinstance(item, dict) else None
        for item in components
    )


def _authorized(request: Any) -> tuple[str, ...]:
    return tuple(
        _target_reference(target)
        for target in request.invocation.request.revision_targets
    )


def _registry(request: Any) -> frozenset[str]:
    source = request.invocation.request.source_draft
    values = {"opening", "closing"}
    values.update(f"story:{item.story_id}" for item in source.stories)
    values.update(
        f"transition:{item.from_story_id}:{item.to_story_id}"
        for item in source.transitions
    )
    if source.cta is not None:
        values.add("call_to_action")
    return frozenset(values)


def _target_reference(target: Any) -> str:
    value = target.target_type.value
    if value == "story":
        return f"story:{target.story_id}"
    if value == "transition":
        return f"transition:{target.from_story_id}:{target.to_story_id}"
    return value
