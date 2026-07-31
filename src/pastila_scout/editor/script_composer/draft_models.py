"""Immutable structural draft contracts for Module 2.9 Phase 4.1."""

import re
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from .canonical import canonical_json, semantic_fingerprint
from .defaults import CUSTOM_PATTERN, FINGERPRINT_PATTERN, IDENTITY_PATTERN
from .models import FrozenDomainModel


class DraftStatus(StrEnum):
    """Structural readiness states; these are not execution states."""

    PLANNED = "planned"
    VALIDATED = "validated"
    INELIGIBLE = "ineligible"


class DraftSectionKind(StrEnum):
    """Built-in structural section kinds."""

    INTRO = "intro"
    CONTEXT = "context"
    TIMELINE = "timeline"
    ANALYSIS = "analysis"
    REACTION = "reaction"
    FACT = "fact"
    BACKGROUND = "background"
    QUOTE = "quote"
    COMPARISON = "comparison"
    SUMMARY = "summary"
    CONCLUSION = "conclusion"
    CLOSING = "closing"


ReferenceToken = Annotated[str, Field(strict=True, min_length=1)]
_METADATA_KEYS = frozenset(
    {
        "schema_extension_identifier",
        "structural_category",
        "structural_label",
        "structural_note_code",
    }
)
_METADATA_VALUE_PATTERN = re.compile(r"^[a-z0-9]+(?:[._:-][a-z0-9]+)*$")
_TIMESTAMP_VALUE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")


class DraftDomainModel(FrozenDomainModel):
    """Base contract whose generic fingerprint field is self-excluding."""

    @property
    def semantic_sha256(self) -> str:
        return draft_semantic_fingerprint(self)

    def canonical_json(self) -> str:
        return canonical_json(self)


class StructuralMetadataEntry(DraftDomainModel):
    """One provider-neutral structural metadata entry."""

    key: str = Field(
        strict=True,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$",
    )
    value: str = Field(strict=True, min_length=1, max_length=80)

    @field_validator("key")
    @classmethod
    def validate_structural_key(cls, value: str) -> str:
        if value not in _METADATA_KEYS:
            raise PydanticCustomError(
                "draft-prohibited-metadata-key", "draft-prohibited-metadata-key"
            )
        return value

    @field_validator("value")
    @classmethod
    def reject_blank_value(cls, value: str) -> str:
        if (
            not value.strip()
            or not _METADATA_VALUE_PATTERN.fullmatch(value)
            or _TIMESTAMP_VALUE_PATTERN.match(value)
        ):
            raise PydanticCustomError(
                "draft-prohibited-metadata-value", "draft-prohibited-metadata-value"
            )
        return value


class TransitionSlot(DraftDomainModel):
    """A structural edge between two draft sections, without wording."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    transition_reference: ReferenceToken
    from_section: ReferenceToken
    to_section: ReferenceToken
    required: bool = Field(strict=True)


class DraftSection(DraftDomainModel):
    """One ordered structural draft section; it contains no generated text."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    section_reference: ReferenceToken
    order_index: int = Field(strict=True, ge=0)
    section_kind: DraftSectionKind | str
    purpose: str = Field(strict=True, min_length=1, max_length=200)
    required_claim_references: tuple[ReferenceToken, ...] = ()
    optional_claim_references: tuple[ReferenceToken, ...] = ()
    required_evidence_references: tuple[ReferenceToken, ...] = ()
    optional_evidence_references: tuple[ReferenceToken, ...] = ()
    transition_before: ReferenceToken | None = None
    transition_after: ReferenceToken | None = None
    metadata: tuple[StructuralMetadataEntry, ...] = ()

    @field_validator("section_kind", mode="before")
    @classmethod
    def validate_section_kind(cls, value):
        raw = getattr(value, "value", value)
        built_ins = {item.value for item in DraftSectionKind}
        if raw not in built_ins and not (
            isinstance(raw, str) and re.fullmatch(CUSTOM_PATTERN, raw)
        ):
            raise PydanticCustomError(
                "draft-unknown-section-kind", "draft-unknown-section-kind"
            )
        return value

    @field_validator("purpose")
    @classmethod
    def reject_blank_purpose(cls, value: str) -> str:
        if not value.strip():
            raise PydanticCustomError("draft-blank-purpose", "draft-blank-purpose")
        return value

    @field_validator(
        "required_claim_references",
        "optional_claim_references",
        "required_evidence_references",
        "optional_evidence_references",
        mode="before",
    )
    @classmethod
    def canonicalize_reference_sets(cls, value):
        return tuple(sorted(value))

    @field_validator("metadata", mode="before")
    @classmethod
    def canonicalize_metadata(cls, value):
        def key(item):
            if isinstance(item, dict):
                return (item.get("key", ""), item.get("value", ""))
            return (item.key, item.value)

        return tuple(sorted(value, key=key))

    @model_validator(mode="after")
    def validate_metadata_keys(self) -> Self:
        _reject_duplicate_metadata_keys(self.metadata)
        return self


class DraftStructure(DraftDomainModel):
    """A complete deterministic structural draft plan."""

    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    title: str | None = Field(default=None, strict=True, min_length=1, max_length=200)
    normalized_input_reference: ReferenceToken
    execution_plan_reference: ReferenceToken
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    section_references: tuple[ReferenceToken, ...] = Field(min_length=1)
    sections: tuple[DraftSection, ...] = Field(min_length=1)
    transitions: tuple[TransitionSlot, ...] = ()
    draft_metadata: tuple[StructuralMetadataEntry, ...] = ()
    status: DraftStatus

    @field_validator("title")
    @classmethod
    def reject_blank_title(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise PydanticCustomError("draft-blank-title", "draft-blank-title")
        return value

    @field_validator("sections", mode="before")
    @classmethod
    def canonicalize_sections(cls, value):
        def key(item):
            if isinstance(item, dict):
                return (item.get("order_index", -1), item.get("section_reference", ""))
            return (item.order_index, item.section_reference)

        return tuple(sorted(value, key=key))

    @field_validator("transitions", mode="before")
    @classmethod
    def canonicalize_transitions(cls, value):
        def key(item):
            if isinstance(item, dict):
                return item.get("transition_reference", "")
            return item.transition_reference

        return tuple(sorted(value, key=key))

    @field_validator("draft_metadata", mode="before")
    @classmethod
    def canonicalize_metadata(cls, value):
        def key(item):
            if isinstance(item, dict):
                return (item.get("key", ""), item.get("value", ""))
            return (item.key, item.value)

        return tuple(sorted(value, key=key))

    @model_validator(mode="after")
    def validate_metadata_keys(self) -> Self:
        _reject_duplicate_metadata_keys(self.draft_metadata)
        return self


class DraftExecutionPlanReference(DraftDomainModel):
    """One exact execution-plan reference and fingerprint pair."""

    execution_plan_reference: ReferenceToken
    execution_plan_fingerprint: str = Field(strict=True, pattern=FINGERPRINT_PATTERN)


class NormalizedInputDraftScope(DraftDomainModel):
    """Authoritative Phase 4.1 inventory owned by one normalized input."""

    normalized_input_reference: ReferenceToken
    claim_references: tuple[ReferenceToken, ...] = ()
    evidence_references: tuple[ReferenceToken, ...] = ()
    execution_plans: tuple[DraftExecutionPlanReference, ...] = ()

    @field_validator("claim_references", "evidence_references", mode="before")
    @classmethod
    def validate_and_order_references(cls, value, info):
        values = _context_collection(value)
        if any(not isinstance(item, str) for item in values):
            raise PydanticCustomError(
                "draft-invalid-context-collection-member",
                "draft-invalid-context-collection-member",
            )
        _reject_duplicates(
            values, f"draft-duplicate-context-{info.field_name[:-11]}-identity"
        )
        return tuple(sorted(values))

    @field_validator("execution_plans", mode="before")
    @classmethod
    def validate_and_order_plans(cls, value):
        values = _context_collection(value)
        if any(
            not isinstance(item, (dict, DraftExecutionPlanReference)) for item in values
        ):
            raise PydanticCustomError(
                "draft-invalid-context-collection-member",
                "draft-invalid-context-collection-member",
            )
        references = tuple(
            (
                item.get("execution_plan_reference", "")
                if isinstance(item, dict)
                else item.execution_plan_reference
            )
            for item in values
        )
        _reject_duplicates(
            references, "draft-duplicate-context-execution-plan-identity"
        )
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.get("execution_plan_reference", "")
                    if isinstance(item, dict)
                    else item.execution_plan_reference
                ),
            )
        )


class DraftValidationContext(DraftDomainModel):
    """Deeply immutable normalized-input-scoped ownership context."""

    normalized_input_scopes: tuple[NormalizedInputDraftScope, ...]

    @field_validator("normalized_input_scopes", mode="before")
    @classmethod
    def validate_and_order_scopes(cls, value):
        values = _context_collection(value)
        if any(
            not isinstance(item, (dict, NormalizedInputDraftScope)) for item in values
        ):
            raise PydanticCustomError(
                "draft-invalid-context-collection-member",
                "draft-invalid-context-collection-member",
            )
        references = tuple(
            (
                item.get("normalized_input_reference", "")
                if isinstance(item, dict)
                else item.normalized_input_reference
            )
            for item in values
        )
        _reject_duplicates(
            references, "draft-duplicate-context-normalized-input-identity"
        )
        return tuple(
            sorted(
                values,
                key=lambda item: (
                    item.get("normalized_input_reference", "")
                    if isinstance(item, dict)
                    else item.normalized_input_reference
                ),
            )
        )


def _reject_duplicates(values: tuple[str, ...], code: str) -> None:
    if len(values) != len(set(values)):
        raise PydanticCustomError(code, code)


def _context_collection(value) -> tuple:
    if isinstance(value, (str, bytes, dict)):
        raise PydanticCustomError(
            "draft-invalid-context-collection",
            "draft-invalid-context-collection",
        )
    try:
        return tuple(value)
    except TypeError as error:
        raise PydanticCustomError(
            "draft-invalid-context-collection",
            "draft-invalid-context-collection",
        ) from error


def _reject_duplicate_metadata_keys(
    metadata: tuple[StructuralMetadataEntry, ...],
) -> None:
    keys = tuple(item.key for item in metadata)
    _reject_duplicates(keys, "draft-duplicate-metadata-key")


def draft_semantic_fingerprint(value: DraftDomainModel) -> str:
    """Derive a semantic fingerprint while excluding the artifact's own seal."""

    return semantic_fingerprint(
        _draft_semantic_payload(value, exclude_fingerprint=True)
    )


def _draft_semantic_payload(
    value: DraftDomainModel, *, exclude_fingerprint: bool
) -> dict:
    excluded = {"fingerprint"} if exclude_fingerprint else set()
    payload = value.model_dump(mode="python", exclude=excluded, warnings=False)
    if isinstance(value, DraftStructure):
        payload["section_references"] = {
            str(index): reference
            for index, reference in enumerate(value.section_references)
        }
    return payload


__all__ = (
    "DraftExecutionPlanReference",
    "DraftSection",
    "DraftSectionKind",
    "DraftStatus",
    "DraftStructure",
    "DraftValidationContext",
    "NormalizedInputDraftScope",
    "StructuralMetadataEntry",
    "TransitionSlot",
    "draft_semantic_fingerprint",
)
