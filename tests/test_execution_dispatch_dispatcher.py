"""M6C.6B Part 3 authoritative dispatcher tests."""

from test_corrective_action_execution_dispatch_contracts import (
    _context,
    _descriptor,
    _planning_result,
)

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CapabilityResolver,
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutionDispatchDiagnostic,
    CorrectiveActionExecutionDispatchDiagnosticCategory,
    CorrectiveActionExecutionDispatchDiagnosticCode,
    CorrectiveActionExecutionDispatchPolicy,
    CorrectiveActionExecutionDispatchRequest,
    CorrectiveActionExecutionDispatchService,
    CorrectiveActionExecutionDispatchStatus,
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorBinding,
    CorrectiveActionExecutorBindings,
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorRegistry,
    CorrectiveActionExecutorResult,
    DispatchEligibilityEvaluator,
    build_standard_corrective_action_execution_dispatch_policy,
)


class _Executor:
    def __init__(self, descriptor, behavior="completed"):
        self._descriptor = descriptor
        self.behavior = behavior
        self.calls = 0
        self.request = None

    @property
    def descriptor(self):
        return self._descriptor

    def execute(self, request):
        self.calls += 1
        self.request = request
        if self.behavior == "raise":
            raise RuntimeError("API_KEY=secret C:\\private\\draft.txt")
        if self.behavior == "invalid":
            valid = CorrectiveActionExecutorResult.build(
                executor_descriptor=self.descriptor,
                request=request,
                operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
                execution_status=CorrectiveActionExecutionStatus.COMPLETED,
                diagnostic=None,
            )
            return valid.model_copy(update={"result_fingerprint": "sha256:bad"})
        if self.behavior == "failed":
            diagnostic = CorrectiveActionExecutionDispatchDiagnostic.build(
                code=CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_INVOCATION_FAILED,
                category=CorrectiveActionExecutionDispatchDiagnosticCategory.EXECUTOR,
                safe_message="Executor declared a controlled failure.",
            )
            return CorrectiveActionExecutorResult.build(
                executor_descriptor=self.descriptor,
                request=request,
                operational_outcome=CorrectiveActionExecutorOutcome.FAILED_PRECONDITION,
                execution_status=CorrectiveActionExecutionStatus.FAILED,
                diagnostic=diagnostic,
            )
        return CorrectiveActionExecutorResult.build(
            executor_descriptor=self.descriptor,
            request=request,
            operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
            execution_status=CorrectiveActionExecutionStatus.COMPLETED,
            diagnostic=None,
        )


class _EligibilitySpy(DispatchEligibilityEvaluator):
    def __init__(self):
        self.calls = 0

    def evaluate(self, *args, **kwargs):
        self.calls += 1
        return super().evaluate(*args, **kwargs)


class _ResolverSpy(CapabilityResolver):
    def __init__(self):
        self.calls = 0

    def resolve(self, *args, **kwargs):
        self.calls += 1
        return super().resolve(*args, **kwargs)


def _runtime(
    action=CorrectiveAction.REQUEST_REVISION,
    *,
    authorization=CorrectiveActionAuthorizationState.NOT_REQUIRED,
    behavior="completed",
    policy=None,
    empty=False,
    ambiguous=False,
):
    plan_result = _planning_result(
        action,
        revision_requires_human_authorization=(
            authorization is not CorrectiveActionAuthorizationState.NOT_REQUIRED
        ),
    )
    descriptors = () if empty else (_descriptor(plan_result.plan),)
    if ambiguous:
        first = descriptors[0]
        descriptors = (
            first,
            CorrectiveActionExecutorDescriptor.build(
                executor_id="alternate-executor.v1",
                supported_capability=first.supported_capability,
                supported_plan_types=first.supported_plan_types,
                supports_automatic_invocation=True,
                supports_human_gated_invocation=True,
            ),
        )
    registry = CorrectiveActionExecutorRegistry.build(descriptors)
    executors = tuple(_Executor(descriptor, behavior) for descriptor in descriptors)
    bindings = CorrectiveActionExecutorBindings.build(
        registry,
        tuple(
            CorrectiveActionExecutorBinding(descriptor, executor)
            for descriptor, executor in zip(descriptors, executors, strict=True)
        ),
    )
    eligibility = _EligibilitySpy()
    resolver = _ResolverSpy()
    from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
        CorrectiveActionExecutionDispatcher,
    )

    dispatcher = CorrectiveActionExecutionDispatcher(bindings, eligibility, resolver)
    service = CorrectiveActionExecutionDispatchService(bindings, dispatcher)
    request = CorrectiveActionExecutionDispatchRequest.build(
        plan_result,
        policy or build_standard_corrective_action_execution_dispatch_policy(),
        _context(authorization),
    )
    return service.dispatch_runtime(request), executors, eligibility, resolver


def test_valid_automatic_dispatch_invokes_each_authority_once() -> None:
    runtime, executors, eligibility, resolver = _runtime()
    assert (
        runtime.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED
    )
    assert eligibility.calls == resolver.calls == executors[0].calls == 1
    assert runtime.result.request.planning_result is runtime.eligibility.plan_result
    assert runtime.result.executor_descriptor is executors[0].descriptor
    assert runtime.result.executor_request is executors[0].request


def test_human_gate_requires_explicit_grant_and_denial_never_invokes() -> None:
    waiting, executors, eligibility, resolver = _runtime(
        CorrectiveAction.REQUEST_REGENERATION,
        authorization=CorrectiveActionAuthorizationState.REQUIRED_NOT_GRANTED,
    )
    assert (
        waiting.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.AWAITING_AUTHORIZATION
    )
    assert eligibility.calls == 1 and resolver.calls == 0 and executors[0].calls == 0
    denied, executors, _, resolver = _runtime(
        CorrectiveAction.REQUEST_REGENERATION,
        authorization=CorrectiveActionAuthorizationState.DENIED,
    )
    assert (
        denied.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED
    )
    assert resolver.calls == 0 and executors[0].calls == 0
    granted, executors, _, resolver = _runtime(
        CorrectiveAction.REQUEST_REGENERATION,
        authorization=CorrectiveActionAuthorizationState.GRANTED,
    )
    assert (
        granted.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED
    )
    assert resolver.calls == executors[0].calls == 1


def test_non_executable_and_policy_blocked_never_resolve_or_invoke() -> None:
    runtime, executors, eligibility, resolver = _runtime(
        CorrectiveAction.CONTINUE_WORKFLOW, empty=True
    )
    assert (
        runtime.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE
    )
    assert eligibility.calls == 1 and resolver.calls == 0 and executors == ()
    blocked = CorrectiveActionExecutionDispatchPolicy.build(
        allow_automatic_dispatch=False
    )
    runtime, executors, _, resolver = _runtime(policy=blocked)
    assert (
        runtime.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED
    )
    assert resolver.calls == 0 and executors[0].calls == 0


def test_zero_and_ambiguous_resolution_never_invoke() -> None:
    zero, executors, _, resolver = _runtime(empty=True)
    assert (
        zero.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED
    )
    assert resolver.calls == 1 and executors == ()
    ambiguous, executors, _, resolver = _runtime(ambiguous=True)
    assert (
        ambiguous.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED
    )
    assert resolver.calls == 1 and all(executor.calls == 0 for executor in executors)


def test_executor_failure_exception_and_invalid_result_remain_distinct() -> None:
    failed, executors, _, _ = _runtime(behavior="failed")
    assert (
        failed.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.EXECUTOR_FAILED
    )
    assert failed.result.executor_result is not None and executors[0].calls == 1
    raised, executors, _, _ = _runtime(behavior="raise")
    assert (
        raised.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED
    )
    assert raised.result.executor_result is None and executors[0].calls == 1
    assert "secret" not in raised.result.diagnostic.safe_message.casefold()
    invalid, executors, _, _ = _runtime(behavior="invalid")
    assert (
        invalid.result.dispatch_status
        is CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED
    )
    assert invalid.result.executor_result is None and executors[0].calls == 1
