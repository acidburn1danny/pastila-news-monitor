"""Immutable regeneration-only policy."""

from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

POLICY_VERSION = "1"


class DraftRegenerationPolicy(FrozenModel):
    policy_version: str = POLICY_VERSION
    require_fresh_generation: bool = True
    allow_source_draft_as_context: bool = True
    require_output_draft_fingerprint: bool = True
    require_distinct_output_identity: bool = True
    require_generation_lineage: bool = True
    policy_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> DraftRegenerationPolicy:
        values.setdefault("policy_version", POLICY_VERSION)
        values.setdefault("require_fresh_generation", True)
        values.setdefault("allow_source_draft_as_context", True)
        values.setdefault("require_output_draft_fingerprint", True)
        values.setdefault("require_distinct_output_identity", True)
        values.setdefault("require_generation_lineage", True)
        values["policy_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.policy_version != POLICY_VERSION:
            raise ValueError("unsupported draft-regeneration policy version")
        if not all(
            (
                self.require_fresh_generation,
                self.require_output_draft_fingerprint,
                self.require_distinct_output_identity,
                self.require_generation_lineage,
            )
        ):
            raise ValueError("draft regeneration requires fixed safety invariants")
        expected = fingerprint(
            self.model_dump(exclude={"policy_fingerprint"}, mode="python")
        )
        if self.policy_fingerprint != expected:
            raise ValueError("draft-regeneration policy fingerprint is inconsistent")
        return self


def build_standard_draft_regeneration_policy() -> DraftRegenerationPolicy:
    """Build the one standard immutable Part 1 policy."""

    return DraftRegenerationPolicy.build()
