"""Typed factual-field extraction with field-local candidate provenance."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .extraction import extract_surface_candidates
from .models import AuthorityClass, SurfaceCandidateV1
from .persistence import canonical_identity

EXTRACTION_POLICY_VERSION_V2 = "voice-fact-candidate-extraction-v2"
SOURCE_INPUT_CONTRACT_V2 = "typed-authority-fields-v2"


class TypedAuthorityFieldInputV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_name: Literal["pastilaacida-voice-typed-authority-field-input"] = (
        "pastilaacida-voice-typed-authority-field-input"
    )
    schema_version: Literal["2"] = "2"
    authority_class: AuthorityClass
    authority_identity: str = Field(min_length=1)
    article_id: int = Field(gt=0)
    source_id: str = Field(min_length=1)
    field_name: Literal["title", "summary"]
    text: str = Field(min_length=1)
    text_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @property
    def source_identity(self) -> str:
        return f"article:{self.article_id}:{self.source_id}:field:{self.field_name}"

    @model_validator(mode="after")
    def exact_text_identity(self):
        expected = "sha256:" + hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        if self.text_sha256 != expected:
            raise ValueError("typed authority field identity mismatch")
        return self


def extract_typed_authority_candidates_v2(
    fields: tuple[TypedAuthorityFieldInputV2, ...],
) -> tuple[SurfaceCandidateV1, ...]:
    """Extract independently per field; offsets are Python string indices."""
    result: list[SurfaceCandidateV1] = []
    for field in fields:
        v1_candidates = extract_surface_candidates(
            authority_class=field.authority_class,
            authority_identity=field.authority_identity,
            source_identity=field.source_identity,
            text=field.text,
        )
        for candidate in v1_candidates:
            seed = {
                "kind": candidate.kind.value,
                "evidence": candidate.evidence.model_dump(mode="json"),
            }
            receipt = canonical_identity(
                {"policy": EXTRACTION_POLICY_VERSION_V2, "candidate": seed}
            )
            result.append(
                candidate.model_copy(
                    update={
                        "candidate_id": f"candidate:{receipt}",
                        "extraction_receipt_identity": receipt,
                    }
                )
            )
    return tuple(result)


__all__ = [
    "EXTRACTION_POLICY_VERSION_V2",
    "SOURCE_INPUT_CONTRACT_V2",
    "TypedAuthorityFieldInputV2",
    "extract_typed_authority_candidates_v2",
]
