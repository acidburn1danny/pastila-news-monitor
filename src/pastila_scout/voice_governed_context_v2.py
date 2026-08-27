"""Desktop-neutral governed Voice context contract.

The contract carries already-authorized callbacks and immutable eligibility
state.  It grants no execution, selection, acceptance, or persistence
authority by itself.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pastila_scout.expression_catalog_v2.eligibility_models import (
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
)
from pastila_scout.voice_eligibility_v2.models import (
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_executor_v2.models import (
    VoiceDeterministicExecutionRequestV2,
    VoiceDeterministicTerminalResultV2,
)
from pastila_scout.voice_repetition_v2.models import VoiceAcceptanceRequestV1


@dataclass(frozen=True, slots=True)
class VoiceGovernedContextV2:
    event_id: int
    program_eligibility: VoiceEligibilityResultV1
    repetition_snapshot: VoiceRepetitionSnapshotV1
    expression_eligibility_for_program: Callable[
        [VoiceOwnerSelectionReceiptV1], ExpressionEligibilityResultV1
    ]
    execution_request: Callable[
        [VoiceOwnerSelectionReceiptV1, ExpressionOwnerSelectionReceiptV1],
        VoiceDeterministicExecutionRequestV2,
    ]
    acceptance_store: object
    acceptance_request: Callable[
        [VoiceDeterministicTerminalResultV2], VoiceAcceptanceRequestV1
    ]
    factual_summary: str = ""
    accepted_commentary_text: str | None = None
    persist_program_selection: Callable[[VoiceOwnerSelectionReceiptV1], object] | None = None
    persist_expression_selection: Callable[
        [ExpressionEligibilityResultV1, ExpressionOwnerSelectionReceiptV1], object
    ] | None = None
    persist_preview: Callable[
        [VoiceDeterministicExecutionRequestV2, VoiceDeterministicTerminalResultV2],
        object,
    ] | None = None


__all__ = ["VoiceGovernedContextV2"]
