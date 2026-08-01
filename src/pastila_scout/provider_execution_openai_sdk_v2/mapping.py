"""Pure mapping and reconstruction for the future SDK dispatch."""

from pydantic import ValidationError

from pastila_scout.provider_execution_openai_v2 import (
    OpenAIClientErrorCategoryV2,
    OpenAIExecutionOutputV2,
    OpenAIExecutionRequestV2,
    OpenAIExecutionResponseV2,
)
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

from .errors import OpenAISDKBoundaryError, OpenAISDKResponseError
from .models import OpenAISDKMessageV2, OpenAISDKRequestV2, OpenAISDKResponseV2


def build_openai_sdk_request(request: OpenAIExecutionRequestV2) -> OpenAISDKRequestV2:
    """Reconstruct verified input and map it without transport side effects."""

    try:
        authority = OpenAIExecutionRequestV2.model_validate(request)
        return OpenAISDKRequestV2(
            model=authority.model,
            messages=tuple(
                OpenAISDKMessageV2(role=item.role, content=item.content)
                for item in authority.messages
            ),
            timeout_seconds=authority.timeout_seconds,
            temperature=authority.temperature,
            max_output_tokens=authority.max_output_tokens,
            stop_sequences=authority.stop_sequences,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise OpenAISDKBoundaryError("invalid OpenAI SDK request authority") from error


def reconstruct_openai_sdk_response(value: object) -> OpenAIExecutionResponseV2:
    """Discard raw SDK identity and reconstruct only strict response data."""

    try:
        response = OpenAISDKResponseV2.model_validate(value)
        reasons = tuple(_finish_reason(item.finish_reason) for item in response.outputs)
        filtered = any(
            reason is ProviderFinishReasonV2.CONTENT_FILTERED for reason in reasons
        )
        limited = any(reason is ProviderFinishReasonV2.LENGTH for reason in reasons)
        if filtered and any(
            reason is not ProviderFinishReasonV2.CONTENT_FILTERED for reason in reasons
        ):
            raise ValueError("mixed content-filter response")
        if limited and any(
            reason is not ProviderFinishReasonV2.LENGTH for reason in reasons
        ):
            raise ValueError("mixed length-limited response")
        partial = filtered or limited
        return OpenAIExecutionResponseV2(
            provider_request_id=response.response_id,
            model=response.model,
            finished_at=response.finished_at,
            status=(
                ProviderResultStatusV2.PARTIAL
                if partial
                else ProviderResultStatusV2.SUCCESS
            ),
            outputs=tuple(
                OpenAIExecutionOutputV2(
                    ordinal=item.ordinal,
                    generated_text=item.text,
                    finish_reason=reason,
                )
                for item, reason in zip(response.outputs, reasons, strict=True)
            ),
            failure_category=(
                OpenAIClientErrorCategoryV2.CONTENT_FILTERED if filtered else None
            ),
            failure_code=(
                "openai-content-filtered"
                if filtered
                else "openai-length-limited" if limited else None
            ),
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise OpenAISDKResponseError("invalid OpenAI SDK response") from error


def _finish_reason(value: str) -> ProviderFinishReasonV2:
    mapping = {
        "stop": ProviderFinishReasonV2.COMPLETED,
        "length": ProviderFinishReasonV2.LENGTH,
        "content_filter": ProviderFinishReasonV2.CONTENT_FILTERED,
    }
    try:
        return mapping[value]
    except KeyError as error:
        raise ValueError("unknown SDK finish reason") from error


__all__ = ("build_openai_sdk_request", "reconstruct_openai_sdk_response")
