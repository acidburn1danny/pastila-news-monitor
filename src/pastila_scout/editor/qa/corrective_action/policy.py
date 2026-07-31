"""Standard immutable M6C.5F Part 1 decision policy."""

from pastila_scout.editor.qa.corrective_action.models import (
    CorrectiveActionDecisionPolicy,
)


def build_standard_corrective_action_decision_policy():
    return CorrectiveActionDecisionPolicy.build()
