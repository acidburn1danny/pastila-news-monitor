"""Immutable architecture descriptor for M6C.6D Part 1."""

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint


class DraftRevisionArchitectureDescriptor(FrozenModel):
    milestone_id: str = "m6c6d.draft_revision"
    contract_version: str = "1"
    authoritative_input: str = "CorrectiveActionExecutorRequest"
    accepted_plan_type: str = "revise_draft"
    accepted_capability: str = "draft_revision"
    semantic_boundary: str = "targeted immutable revision; never regeneration"
    part_one_has_runtime: bool = False
    descriptor_fingerprint: str

    @classmethod
    def build(cls):
        values = cls.model_construct(descriptor_fingerprint="").model_dump(
            exclude={"descriptor_fingerprint"}, mode="python"
        )
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != "1" or self.part_one_has_runtime:
            raise ValueError("invalid draft-revision Part 1 architecture")
        expected = fingerprint(
            self.model_dump(exclude={"descriptor_fingerprint"}, mode="python")
        )
        if self.descriptor_fingerprint != expected:
            raise ValueError("draft-revision architecture fingerprint is inconsistent")
        return self
