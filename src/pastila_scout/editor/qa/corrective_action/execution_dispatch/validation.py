"""Pure fail-closed validators for M6C.6B Part 1 contracts."""

from pydantic import ValidationError

from .models import (
    DISPATCH_RESULT_VERSION,
    EXECUTOR_REQUEST_VERSION,
    EXECUTOR_RESULT_OUTPUT_VERSION,
    EXECUTOR_RESULT_VERSION,
    CorrectiveActionExecutionContext,
    CorrectiveActionExecutionDispatchDiagnostic,
    CorrectiveActionExecutionDispatchPolicy,
    CorrectiveActionExecutionDispatchRequest,
    CorrectiveActionExecutionDispatchResult,
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorRequest,
    CorrectiveActionExecutorResult,
    CorrectiveActionOutputReference,
)


def validate_execution_dispatch_policy(
    policy: CorrectiveActionExecutionDispatchPolicy,
) -> None:
    """Validate dispatch policy identity and fixed semantic constraints."""

    _revalidate(CorrectiveActionExecutionDispatchPolicy, policy)


def validate_execution_context(context: CorrectiveActionExecutionContext) -> None:
    """Validate narrow execution-context structure and identity."""

    _revalidate(CorrectiveActionExecutionContext, context)


def validate_executor_descriptor(
    descriptor: CorrectiveActionExecutorDescriptor,
) -> None:
    """Validate exact capability and plan compatibility declarations."""

    _revalidate(CorrectiveActionExecutorDescriptor, descriptor)


def validate_execution_dispatch_request(
    request: CorrectiveActionExecutionDispatchRequest,
) -> None:
    """Validate authoritative planning lineage without invoking planning."""

    _revalidate(CorrectiveActionExecutionDispatchRequest, request)
    validate_execution_dispatch_policy(request.policy)
    validate_execution_context(request.execution_context)


def validate_executor_request(request: CorrectiveActionExecutorRequest) -> None:
    """Validate executor request identity, compatibility, and authorization."""

    _require_type(CorrectiveActionExecutorRequest, request)
    if request.request_version != EXECUTOR_REQUEST_VERSION:
        raise ValueError("unsupported executor request version")
    request.invariants()
    validate_executor_descriptor(request.executor_descriptor)
    validate_execution_context(request.execution_context)


def validate_execution_dispatch_diagnostic(
    diagnostic: CorrectiveActionExecutionDispatchDiagnostic,
) -> None:
    """Validate typed safe diagnostic content and fingerprint."""

    _revalidate(CorrectiveActionExecutionDispatchDiagnostic, diagnostic)


def validate_executor_result(result: CorrectiveActionExecutorResult) -> None:
    """Validate generic executor outcome shape and identity lineage."""

    _require_type(CorrectiveActionExecutorResult, result)
    if result.result_version not in {
        EXECUTOR_RESULT_VERSION,
        EXECUTOR_RESULT_OUTPUT_VERSION,
    }:
        raise ValueError("unsupported executor result version")
    result.invariants()
    validate_executor_request(result.request)
    if result.output_reference is not None:
        _revalidate(CorrectiveActionOutputReference, result.output_reference)


def validate_execution_dispatch_result(
    result: CorrectiveActionExecutionDispatchResult,
) -> None:
    """Validate authoritative dispatch/result/report cross-consistency."""

    _require_type(CorrectiveActionExecutionDispatchResult, result)
    if result.result_version != DISPATCH_RESULT_VERSION:
        raise ValueError("unsupported dispatch result version")
    result.invariants()
    validate_execution_dispatch_request(result.request)
    if result.executor_descriptor is not None:
        validate_executor_descriptor(result.executor_descriptor)
    if result.executor_request is not None:
        validate_executor_request(result.executor_request)
    if result.executor_result is not None:
        validate_executor_result(result.executor_result)
    if result.diagnostic is not None:
        validate_execution_dispatch_diagnostic(result.diagnostic)


def _revalidate(model_type, value) -> None:
    _require_type(model_type, value)
    try:
        model_type.model_validate(value.model_dump(mode="python"))
    except ValidationError as exc:
        raise ValueError(f"{model_type.__name__} integrity validation failed") from exc


def _require_type(model_type, value) -> None:
    if not isinstance(value, model_type):
        raise TypeError(f"invalid {model_type.__name__}")
