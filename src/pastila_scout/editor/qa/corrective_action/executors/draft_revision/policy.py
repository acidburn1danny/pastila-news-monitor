"""Immutable fail-closed draft-revision policy."""

from typing import Any

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

POLICY_VERSION = "1"


class DraftRevisionPolicy(FrozenModel):
    contract_version: str = POLICY_VERSION
    preserve_unmodified_content: bool = True
    require_explicit_scope: bool = True
    allow_structural_changes: bool = False
    allow_factual_changes: bool = False
    maximum_revision_targets: int = Field(default=10, ge=1, le=50)
    policy_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", POLICY_VERSION)
        values.setdefault("preserve_unmodified_content", True)
        values.setdefault("require_explicit_scope", True)
        values.setdefault("allow_structural_changes", False)
        values.setdefault("allow_factual_changes", False)
        values.setdefault("maximum_revision_targets", 10)
        values["policy_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != POLICY_VERSION:
            raise ValueError("unsupported draft-revision policy version")
        if not self.preserve_unmodified_content or not self.require_explicit_scope:
            raise ValueError("draft revision requires explicit scope preservation")
        expected = fingerprint(
            self.model_dump(exclude={"policy_fingerprint"}, mode="python")
        )
        if self.policy_fingerprint != expected:
            raise ValueError("draft-revision policy fingerprint is inconsistent")
        return self


def build_standard_draft_revision_policy() -> DraftRevisionPolicy:
    return DraftRevisionPolicy.build()
