"""M6C.6C Part 3 exactly-once runtime tests."""

from test_draft_regeneration_contracts import _executor_request, _input

from pastila_scout.editor.generation.models import (
    ControlledGenerationResult,
    EpisodeDraft,
    GenerationTrace,
)
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
    validate_executor_result,
)
from pastila_scout.editor.qa.corrective_action.executors import (
    ControlledGenerationResultValidator,
    DraftRegenerationExecutor,
    DraftRegenerationResultFactory,
)
from pastila_scout.editor.qa.corrective_action.executors.draft_regeneration import (
    DraftRegenerationInputResolver,
    DraftRegenerationRequestFactory,
    build_standard_draft_regeneration_policy,
)


def _draft(label="generated"):
    text = f"Deschidere {label}.\n\nÎnchidere {label}."
    return EpisodeDraft(
        episode_id=f"episode-{label}",
        opening=f"Deschidere {label}.",
        stories=(),
        transitions=(),
        closing=f"Închidere {label}.",
        cta=None,
        assembled_text=text,
        teleprompter_text=text,
    )


class GatewaySpy:
    def __init__(self, result=None, error=None):
        self.result = result or ControlledGenerationResult(
            draft=_draft(),
            trace=GenerationTrace(attempts=()),
            manifest="safe-manifest",
            final_state="safe-state",
        )
        self.error = error
        self.calls = 0
        self.request = None

    def generate(self, request):
        self.calls += 1
        self.request = request
        if self.error:
            raise self.error
        return self.result


def _executor(gateway, regeneration_input=None):
    regeneration_input = regeneration_input or _input()
    return (
        DraftRegenerationExecutor(
            DraftRegenerationRequestFactory(
                DraftRegenerationInputResolver(regeneration_input)
            ),
            gateway,
            ControlledGenerationResultValidator(),
            DraftRegenerationResultFactory(),
            build_standard_draft_regeneration_policy(),
        ),
        regeneration_input,
    )


def test_success_invokes_generation_exactly_once_and_returns_version_two_reference():
    gateway = GatewaySpy()
    executor, regeneration_input = _executor(gateway)
    request = _executor_request()

    result = executor.execute(request)

    assert gateway.calls == 1
    assert gateway.request is regeneration_input.generation_invocation
    assert result.operational_outcome is CorrectiveActionExecutorOutcome.COMPLETED
    assert result.execution_status is CorrectiveActionExecutionStatus.COMPLETED
    assert result.result_version == "2"
    assert result.output_reference is not None
    validate_executor_result(result)


def test_preparation_failure_never_invokes_generation():
    gateway = GatewaySpy()
    executor = DraftRegenerationExecutor(
        DraftRegenerationRequestFactory(DraftRegenerationInputResolver(None)),
        gateway,
        ControlledGenerationResultValidator(),
        DraftRegenerationResultFactory(),
        build_standard_draft_regeneration_policy(),
    )
    result = executor.execute(_executor_request())

    assert gateway.calls == 0
    assert result.execution_status is CorrectiveActionExecutionStatus.FAILED
    assert result.output_reference is None


def test_generation_exception_is_sanitized_without_retry():
    gateway = GatewaySpy(error=RuntimeError("provider secret traceback"))
    executor, _ = _executor(gateway)
    result = executor.execute(_executor_request())

    assert gateway.calls == 1
    assert result.operational_outcome is CorrectiveActionExecutorOutcome.FAILED_INTERNAL
    assert "secret" not in result.diagnostic.safe_message.casefold()


def test_reused_source_draft_fails_closed():
    source = _draft("source")
    regeneration_input = _input(source)
    generated = ControlledGenerationResult(
        draft=source,
        trace=GenerationTrace(attempts=()),
        manifest="safe-manifest",
        final_state="safe-state",
    )
    gateway = GatewaySpy(result=generated)
    executor, _ = _executor(gateway, regeneration_input)

    result = executor.execute(_executor_request())

    assert gateway.calls == 1
    assert result.execution_status is CorrectiveActionExecutionStatus.FAILED
    assert result.output_reference is None
