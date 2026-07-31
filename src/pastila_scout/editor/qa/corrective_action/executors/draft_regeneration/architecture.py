"""Immutable architecture descriptor for M6C.6C Part 1."""

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

ARCHITECTURE_VERSION = "1"


class DraftRegenerationArchitectureDescriptor(FrozenModel):
    milestone_id: str = "m6c6c.draft_regeneration"
    milestone_version: str = ARCHITECTURE_VERSION
    authoritative_input: str = "CorrectiveActionExecutorRequest"
    accepted_plan_type: str = "regenerate_draft"
    accepted_capability: str = "draft_regeneration"
    capability_output: str = "DraftRegenerationResult"
    generic_output_boundary: str = "CorrectiveActionExecutorResult"
    ownership_statement: str = (
        "M6C.6C regenerates a draft. It does not select the corrective action "
        "or create the execution plan."
    )
    regeneration_statement: str = (
        "Regeneration produces a new draft. It does not revise the existing "
        "draft in place."
    )
    part_one_invokes_generation: bool = False
    future_generation_boundary: str = "M6C.6C Part 2+"
    part_two_prepares_generation: bool = True
    part_two_invokes_generation: bool = False
    preparation_boundary: str = "DraftRegenerationRequestFactory"
    descriptor_fingerprint: str

    @classmethod
    def build(cls) -> DraftRegenerationArchitectureDescriptor:
        values = cls.model_construct(descriptor_fingerprint="").model_dump(
            exclude={"descriptor_fingerprint"}, mode="python"
        )
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def invariants(self):
        if self.milestone_version != ARCHITECTURE_VERSION:
            raise ValueError("unsupported draft-regeneration architecture version")
        if self.part_one_invokes_generation:
            raise ValueError("Part 1 cannot invoke Controlled Generation")
        if not self.part_two_prepares_generation or self.part_two_invokes_generation:
            raise ValueError("Part 2 prepares but cannot invoke Controlled Generation")
        expected = fingerprint(
            self.model_dump(exclude={"descriptor_fingerprint"}, mode="python")
        )
        if self.descriptor_fingerprint != expected:
            raise ValueError("regeneration architecture fingerprint is inconsistent")
        return self
