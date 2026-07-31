"""Capability-specific authorized planning input for Draft Revision."""

import json
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
)
from pastila_scout.editor.qa.corrective_action.execution_plan.planning_input import (
    PLANNING_INPUT_VERSION,
    CorrectiveActionPlanningInput,
    CorrectiveActionPlanningInputType,
)
from pastila_scout.editor.qa.models import fingerprint

from .models import DraftRevisionInstructions, DraftRevisionScope
from .policy import DraftRevisionPolicy
from .validation import (
    validate_draft_revision_instructions,
    validate_draft_revision_policy,
    validate_draft_revision_scope,
)


class DraftRevisionPlanningInput(CorrectiveActionPlanningInput):
    """Authorized immutable revision input before generic planning begins."""

    source_draft: EpisodeDraft
    revision_policy: DraftRevisionPolicy
    revision_scope: DraftRevisionScope
    revision_instructions: DraftRevisionInstructions

    @property
    def authoritative_source_object(self):
        return self.source_draft

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", PLANNING_INPUT_VERSION)
        values.setdefault(
            "input_type", CorrectiveActionPlanningInputType.DRAFT_REVISION
        )
        values.setdefault("corrective_action", CorrectiveAction.REQUEST_REVISION)
        values.setdefault(
            "required_capability", CorrectiveActionExecutionCapability.DRAFT_REVISION
        )
        values["input_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def revision_invariants(self):
        if self.input_type is not CorrectiveActionPlanningInputType.DRAFT_REVISION:
            raise ValueError("revision planning input type is inconsistent")
        if self.corrective_action is not CorrectiveAction.REQUEST_REVISION:
            raise ValueError("revision planning input action is inconsistent")
        if (
            self.required_capability
            is not CorrectiveActionExecutionCapability.DRAFT_REVISION
        ):
            raise ValueError("revision planning input capability is inconsistent")
        validate_draft_revision_policy(self.revision_policy)
        validate_draft_revision_scope(self.revision_scope)
        validate_draft_revision_instructions(self.revision_instructions)
        if (
            self.revision_scope.maximum_targets
            != self.revision_policy.maximum_revision_targets
        ):
            raise ValueError("revision policy and scope limits differ")
        if (
            self.revision_instructions.scope_fingerprint
            != self.revision_scope.scope_fingerprint
        ):
            raise ValueError("revision instructions do not reference scope")
        _validate_source_targets(self)
        _reject_implicit_regeneration(self)
        return self


def build_draft_revision_planning_input_report(
    value: DraftRevisionPlanningInput,
) -> dict[str, object]:
    """Project safe planning metadata without draft or instruction prose."""

    return {
        "contract_version": value.contract_version,
        "input_type": value.input_type.value,
        "corrective_action": value.corrective_action.value,
        "required_capability": value.required_capability.value,
        "target_count": len(value.revision_scope.targets),
        "policy_fingerprint": value.revision_policy.policy_fingerprint,
        "scope_fingerprint": value.revision_scope.scope_fingerprint,
        "instructions_fingerprint": value.revision_instructions.instructions_fingerprint,
        "source_draft_fingerprint": fingerprint(value.source_draft),
        "source_lineage_fingerprint": value.source_lineage_fingerprint,
        "authorization_policy_fingerprint": value.authorization_policy_fingerprint,
        "input_fingerprint": value.input_fingerprint,
    }


def serialize_draft_revision_planning_input_report(report: dict[str, object]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_source_targets(value: DraftRevisionPlanningInput) -> None:
    from .enums import DraftRevisionTargetType

    stories = {story.story_id for story in value.source_draft.stories}
    transitions = {
        (item.from_story_id, item.to_story_id)
        for item in value.source_draft.transitions
    }
    for target in value.revision_scope.targets:
        if (
            target.target_type is DraftRevisionTargetType.STORY
            and target.story_id not in stories
        ):
            raise ValueError("revision planning target is absent from source draft")
        if (
            target.target_type is DraftRevisionTargetType.TRANSITION
            and (target.from_story_id, target.to_story_id) not in transitions
        ):
            raise ValueError("revision transition is absent from source draft")
        if (
            target.target_type is DraftRevisionTargetType.CALL_TO_ACTION
            and value.source_draft.cta is None
        ):
            raise ValueError("revision call-to-action target is absent")


def _reject_implicit_regeneration(value: DraftRevisionPlanningInput) -> None:
    from .enums import DraftRevisionTargetType

    editable = {
        (DraftRevisionTargetType.OPENING, None, None),
        (DraftRevisionTargetType.CLOSING, None, None),
        *(
            (DraftRevisionTargetType.STORY, item.story_id, None)
            for item in value.source_draft.stories
        ),
        *(
            (DraftRevisionTargetType.TRANSITION, item.from_story_id, item.to_story_id)
            for item in value.source_draft.transitions
        ),
    }
    if value.source_draft.cta is not None:
        editable.add((DraftRevisionTargetType.CALL_TO_ACTION, None, None))
    selected = {
        (item.target_type, item.story_id or item.from_story_id, item.to_story_id)
        for item in value.revision_scope.targets
    }
    if editable and selected == editable:
        raise ValueError("revision planning input implicitly requests regeneration")
    normalized = value.revision_instructions.editorial_instruction.casefold()
    if any(
        phrase in normalized
        for phrase in (
            "rewrite everything",
            "rewrite the entire",
            "rescrie tot",
            "refă tot",
        )
    ):
        raise ValueError("revision instructions imply regeneration")
