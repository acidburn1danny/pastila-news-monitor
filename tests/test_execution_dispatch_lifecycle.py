"""M6C.6B Part 3 immutable lifecycle tests."""

import pytest

from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionDispatchPhase,
    CorrectiveActionExecutionDispatchState,
    transition_dispatch_state,
    validate_dispatch_state,
)


def test_success_lifecycle_is_immutable_deterministic_and_sequential() -> None:
    initial = CorrectiveActionExecutionDispatchState.prepared("sha256:" + "1" * 64)
    first = transition_dispatch_state(
        initial, CorrectiveActionExecutionDispatchPhase.VALIDATING
    )
    second = transition_dispatch_state(
        first, CorrectiveActionExecutionDispatchPhase.EVALUATING_ELIGIBILITY
    )
    assert initial.revision == 0 and initial.events == ()
    assert second.revision == 2
    assert tuple(event.sequence for event in second.events) == (1, 2)
    assert second == transition_dispatch_state(
        transition_dispatch_state(
            initial, CorrectiveActionExecutionDispatchPhase.VALIDATING
        ),
        CorrectiveActionExecutionDispatchPhase.EVALUATING_ELIGIBILITY,
    )
    validate_dispatch_state(second)


def test_terminal_states_and_phase_skips_are_rejected() -> None:
    state = CorrectiveActionExecutionDispatchState.prepared("sha256:" + "2" * 64)
    with pytest.raises(ValueError, match="transition"):
        transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.RESOLVING
        )
    state = transition_dispatch_state(
        state, CorrectiveActionExecutionDispatchPhase.VALIDATING
    )
    state = transition_dispatch_state(
        state, CorrectiveActionExecutionDispatchPhase.FAILED
    )
    with pytest.raises(ValueError, match="transition"):
        transition_dispatch_state(
            state, CorrectiveActionExecutionDispatchPhase.FINALIZED
        )


def test_state_and_event_fingerprint_tampering_fails_closed() -> None:
    state = CorrectiveActionExecutionDispatchState.prepared("sha256:" + "3" * 64)
    state = transition_dispatch_state(
        state, CorrectiveActionExecutionDispatchPhase.VALIDATING
    )
    with pytest.raises(ValueError):
        validate_dispatch_state(state.model_copy(update={"state_fingerprint": "bad"}))
    bad_event = state.events[0].model_copy(update={"event_fingerprint": "bad"})
    with pytest.raises(ValueError):
        validate_dispatch_state(state.model_copy(update={"events": (bad_event,)}))
