"""Pure authoritative regeneration input resolution and request construction."""

from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutorRequest,
)

from .models import DraftRegenerationInput, DraftRegenerationRequest
from .policy import DraftRegenerationPolicy
from .validation import validate_draft_regeneration_input


class DraftRegenerationInputResolver:
    """Resolve one explicitly injected, typed, immutable authoritative input.

    The frozen generic executor request contains lineage but no generation payload.
    Composition therefore binds the approved input explicitly; no lookup or global
    fallback is performed.
    """

    def __init__(self, authoritative_input: DraftRegenerationInput | None):
        self._authoritative_input = authoritative_input

    def resolve(
        self, executor_request: CorrectiveActionExecutorRequest
    ) -> DraftRegenerationInput:
        del executor_request
        if self._authoritative_input is None:
            raise ValueError("authoritative generation input is unavailable")
        validate_draft_regeneration_input(self._authoritative_input)
        return self._authoritative_input


def construct_draft_regeneration_request(
    executor_request: CorrectiveActionExecutorRequest,
    policy: DraftRegenerationPolicy,
    regeneration_input: DraftRegenerationInput,
) -> DraftRegenerationRequest:
    """Construct the capability request while preserving every nested identity."""

    return DraftRegenerationRequest.build(
        executor_request=executor_request,
        policy=policy,
        regeneration_input=regeneration_input,
    )
