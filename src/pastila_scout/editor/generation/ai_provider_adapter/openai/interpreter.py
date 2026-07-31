"""OpenAI Responses semantic interpretation for Controlled Revision."""

from __future__ import annotations

import json
from typing import Any

from openai.types.responses import Response, ResponseOutputMessage
from pydantic import ValidationError

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderClientResponse,
    AIProviderExecutionFailureKind,
    AIProviderExecutionRequest,
    AIProviderInterpretationFailure,
    AIProviderInterpretationResult,
    AIProviderUsage,
)
from pastila_scout.editor.generation.revision import (
    ControlledRevisionGatewayResult,
    RevisionGatewayStatus,
    revision_fingerprint,
)

from .models import OpenAIControlledRevisionProviderOutput
from .reconstructor import (
    OpenAIControlledRevisionReconstructor,
    OpenAIReconstructionError,
)
from .validation_diagnostics import build_safe_dto_validation_diagnostics


class OpenAIProviderOutputValidationFailure(AIProviderInterpretationFailure):
    """Internal content-free validation detail; public diagnostics stay canonical."""

    def __init__(self, diagnostic_code: str, safe_metadata=()):
        super().__init__(AIProviderExecutionFailureKind.SCHEMA, diagnostic_code)
        self.safe_metadata = tuple(safe_metadata)


class OpenAIControlledRevisionInterpreter:
    """Fail closed while projecting one completed OpenAI response to the gateway."""

    def __init__(self, reconstructor=None) -> None:
        self.reconstructor = reconstructor or OpenAIControlledRevisionReconstructor()

    def interpret(
        self,
        request: AIProviderExecutionRequest,
        response: AIProviderClientResponse,
    ) -> AIProviderInterpretationResult:
        """Validate status, content, schema, usage, and authoritative lineage."""

        raw = response.payload
        if not isinstance(raw, Response):
            self._fail(
                AIProviderExecutionFailureKind.MALFORMED_RESPONSE,
                "openai_response_type_invalid",
            )
        status = raw.status
        if status == "incomplete":
            self._fail(
                AIProviderExecutionFailureKind.INCOMPLETE_RESPONSE,
                "openai_response_incomplete",
            )
        if status != "completed":
            self._fail(
                AIProviderExecutionFailureKind.MALFORMED_RESPONSE,
                f"openai_response_status_{self._safe_status(status)}",
            )
        output_text = self._extract_output(raw)
        try:
            decoded = json.loads(output_text)
        except (TypeError, json.JSONDecodeError):
            self._fail(
                AIProviderExecutionFailureKind.SCHEMA,
                "openai_structured_output_malformed_json",
            )
        try:
            provider_output = OpenAIControlledRevisionProviderOutput.model_validate(
                decoded
            )
        except ValidationError as error:
            raise _safe_validation_failure(error) from None

        invocation = request.invocation
        revision = invocation.request
        try:
            revised_draft = self.reconstructor.reconstruct(invocation, provider_output)
        except OpenAIReconstructionError as error:
            self._fail(
                AIProviderExecutionFailureKind.INVALID_GATEWAY_PROJECTION,
                error.diagnostic_code,
            )
        except ValidationError:
            self._fail(
                AIProviderExecutionFailureKind.INVALID_GATEWAY_PROJECTION,
                "openai_reconstructed_draft_domain_invalid",
            )
        gateway_result = ControlledRevisionGatewayResult.build(
            status=RevisionGatewayStatus.SUCCESS,
            revised_draft=revised_draft,
            source_draft_fingerprint=revision_fingerprint(revision.source_draft),
            revision_request_fingerprint=revision.revision_request_fingerprint,
            invocation_fingerprint=invocation.invocation_fingerprint,
            output_contract_fingerprint=(
                revision.expected_output_contract.output_contract_fingerprint
            ),
            preservation_fingerprint=(
                revision.preservation_requirements.preservation_fingerprint
            ),
        )
        usage = self._usage(raw, response.latency_ms)
        request_identifier = getattr(raw, "_request_id", None)
        model_identifier = raw.model if isinstance(raw.model, str) else None
        return AIProviderInterpretationResult(
            gateway_result=gateway_result,
            usage=usage,
            provider_request_identifier=(
                request_identifier if isinstance(request_identifier, str) else None
            ),
            provider_model_identifier=model_identifier,
            metadata=(
                ("completion_status", "completed"),
                ("output_mode", "strict_json_schema"),
                ("response_type", "response"),
            ),
        )

    def _extract_output(self, raw: Response) -> str:
        messages = [
            item for item in raw.output if isinstance(item, ResponseOutputMessage)
        ]
        if len(messages) != 1 or len(raw.output) != 1:
            self._fail(
                AIProviderExecutionFailureKind.UNSUPPORTED_OUTPUT,
                "openai_output_items_ambiguous",
            )
        message = messages[0]
        if message.status != "completed":
            self._fail(
                AIProviderExecutionFailureKind.INCOMPLETE_RESPONSE,
                "openai_output_message_incomplete",
            )
        refusals = [part for part in message.content if part.type == "refusal"]
        texts = [part.text for part in message.content if part.type == "output_text"]
        if refusals:
            self._fail(
                AIProviderExecutionFailureKind.REFUSAL,
                "openai_response_refusal",
            )
        if len(texts) != 1 or len(message.content) != 1:
            self._fail(
                AIProviderExecutionFailureKind.MISSING_STRUCTURED_OUTPUT,
                "openai_structured_output_missing_or_ambiguous",
            )
        if not texts[0].strip():
            self._fail(
                AIProviderExecutionFailureKind.MISSING_STRUCTURED_OUTPUT,
                "openai_structured_output_empty",
            )
        return texts[0]

    def _usage(self, raw: Response, latency_ms: float | None) -> AIProviderUsage | None:
        value: Any = raw.usage
        if value is None:
            return (
                AIProviderUsage(latency_ms=latency_ms)
                if latency_ms is not None
                else None
            )
        values = (value.input_tokens, value.output_tokens, value.total_tokens)
        if any(not isinstance(item, int) or item < 0 for item in values):
            self._fail(
                AIProviderExecutionFailureKind.MALFORMED_USAGE,
                "openai_usage_invalid",
            )
        try:
            return AIProviderUsage(
                prompt_tokens=value.input_tokens,
                completion_tokens=value.output_tokens,
                total_tokens=value.total_tokens,
                latency_ms=latency_ms,
            )
        except ValidationError:
            self._fail(
                AIProviderExecutionFailureKind.MALFORMED_USAGE,
                "openai_usage_inconsistent",
            )

    @staticmethod
    def _safe_status(status: object) -> str:
        value = status if isinstance(status, str) else "unknown"
        return (
            value
            if value in {"failed", "cancelled", "queued", "in_progress"}
            else "unknown"
        )

    @staticmethod
    def _fail(kind: AIProviderExecutionFailureKind, code: str) -> None:
        raise AIProviderInterpretationFailure(kind, code)


def _safe_validation_failure(error: ValidationError):
    errors = error.errors(include_input=False, include_url=False)
    first = errors[0] if errors else {"loc": (), "type": "unknown"}
    location = first.get("loc", ())
    top_level = str(location[0]) if location else "root"
    diagnostics = build_safe_dto_validation_diagnostics(error)
    return OpenAIProviderOutputValidationFailure(
        "openai_provider_output_schema_invalid",
        (
            ("validation_stage", "provider_dto"),
            ("error_count", str(len(errors))),
            ("first_top_level_field", top_level),
            ("pydantic_error_type", str(first.get("type", "unknown"))),
            ("input_present", "unknown"),
            *diagnostics.safe_metadata(),
        ),
    )
