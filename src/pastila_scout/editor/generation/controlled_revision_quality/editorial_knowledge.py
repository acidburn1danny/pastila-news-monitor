"""Typed editorial knowledge contracts, fingerprints, and offline validation."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from enum import StrEnum
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_NAME = "scout_editorial_knowledge_base"
SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = 1


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class KnowledgeStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"
    INVALIDATED = "INVALIDATED"


class FindingType(StrEnum):
    PROMPT_BEHAVIOR = "PROMPT_BEHAVIOR"
    EDITORIAL_FAILURE = "EDITORIAL_FAILURE"
    TRADE_OFF = "TRADE_OFF"
    CAUSAL_RELATIONSHIP = "CAUSAL_RELATIONSHIP"
    PROMPT_INTERACTION = "PROMPT_INTERACTION"
    PROMPT_LIMITATION = "PROMPT_LIMITATION"
    BEST_PRACTICE = "BEST_PRACTICE"
    ANTI_PATTERN = "ANTI_PATTERN"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RelationshipType(StrEnum):
    SUPPORTS = "SUPPORTS"
    REFINES = "REFINES"
    CONTRADICTS = "CONTRADICTS"
    SUPERSEDES = "SUPERSEDES"
    DEPENDS_ON = "DEPENDS_ON"
    RELATED_TO = "RELATED_TO"


class EvidenceReference(StrictModel):
    experiment_id: str
    manifest_path: str
    manifest_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_paths: tuple[str, ...]
    scenario_ids: tuple[str, ...]


class KnowledgeEntry(StrictModel):
    knowledge_id: str = Field(pattern=r"^EK-[0-9]{3}$")
    entry_version: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    finding_type: FindingType
    status: KnowledgeStatus
    confidence: Confidence
    confidence_justification: str = Field(min_length=1)
    source_experiments: tuple[str, ...] = Field(min_length=1)
    supporting_evidence: tuple[EvidenceReference, ...] = Field(min_length=1)
    affected_categories: tuple[str, ...]
    affected_scenarios: tuple[str, ...]
    observed_behavior: str = Field(min_length=1)
    causal_explanation: str = Field(min_length=1)
    net_editorial_utility: int | None
    side_effects: tuple[str, ...]
    recommended_usage: str = Field(min_length=1)
    reusable: bool
    deprecated: bool
    superseded_by: str | None
    created_at: str
    entry_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def status_consistency(self) -> KnowledgeEntry:
        if self.deprecated != (self.status == KnowledgeStatus.DEPRECATED):
            raise ValueError("deprecated flag and status disagree")
        if self.status == KnowledgeStatus.SUPERSEDED and self.superseded_by is None:
            raise ValueError("superseded entry requires superseded_by")
        if not self.supporting_evidence or not self.source_experiments:
            raise ValueError("knowledge requires experiment evidence")
        return self


class KnowledgeRelationship(StrictModel):
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    explanation: str = Field(min_length=1)


class EditorialKnowledgeBase(StrictModel):
    schema_name: str
    schema_version: str
    contract_version: int
    generated_at: str
    generator: str
    entries: tuple[KnowledgeEntry, ...]
    relationships: tuple[KnowledgeRelationship, ...]
    knowledge_base_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_requests: int = 0
    network_calls: int = 0
    benchmark_executions: int = 0
    benchmark_replays: int = 0

    @model_validator(mode="after")
    def base_invariants(self) -> EditorialKnowledgeBase:
        errors: list[str] = []
        if self.schema_name != SCHEMA_NAME or self.schema_version != SCHEMA_VERSION:
            errors.append("unsupported knowledge schema")
        if self.contract_version != CONTRACT_VERSION:
            errors.append("unsupported knowledge contract")
        identifiers = [item.knowledge_id for item in self.entries]
        if len(identifiers) != len(set(identifiers)):
            errors.append("duplicate knowledge IDs")
        known = set(identifiers)
        for relationship in self.relationships:
            if (
                relationship.source_id not in known
                or relationship.target_id not in known
            ):
                errors.append("broken relationship")
            if relationship.source_id == relationship.target_id:
                errors.append("self relationship")
        supersession = {
            item.knowledge_id: item.superseded_by
            for item in self.entries
            if item.superseded_by is not None
        }
        for start in supersession:
            seen: set[str] = set()
            current: str | None = start
            while current in supersession:
                if current in seen:
                    errors.append("circular supersession")
                    break
                seen.add(current)
                current = supersession[current]
        if any(
            (
                self.provider_requests,
                self.network_calls,
                self.benchmark_executions,
                self.benchmark_replays,
            )
        ):
            errors.append("knowledge build must remain offline")
        if errors:
            raise ValueError("; ".join(errors))
        return self


class KnowledgeDiagnostics(StrictModel):
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    entries_validated: int
    artifacts_validated: int
    duplicate_findings: int


def _canonical_hash(value: object) -> str:
    serialized = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def entry_fingerprint(entry: KnowledgeEntry | dict) -> str:
    payload = (
        entry.model_dump(mode="json")
        if isinstance(entry, KnowledgeEntry)
        else json.loads(json.dumps(entry))
    )
    payload.pop("entry_fingerprint", None)
    return _canonical_hash(payload)


def knowledge_base_fingerprint(base: EditorialKnowledgeBase | dict) -> str:
    payload = (
        base.model_dump(mode="json")
        if isinstance(base, EditorialKnowledgeBase)
        else json.loads(json.dumps(base))
    )
    payload.pop("knowledge_base_fingerprint", None)
    payload.pop("generated_at", None)
    return _canonical_hash(payload)


def duplicate_signature(entry: KnowledgeEntry) -> tuple:
    return (
        entry.finding_type,
        " ".join(entry.observed_behavior.casefold().split()),
        tuple(sorted(entry.affected_categories)),
        tuple(sorted(entry.source_experiments)),
    )


def duplicate_findings(entries: tuple[KnowledgeEntry, ...]) -> int:
    counts = Counter(duplicate_signature(item) for item in entries)
    return sum(count - 1 for count in counts.values() if count > 1)


def validate_knowledge_base(
    base: EditorialKnowledgeBase, repository_root: Path
) -> KnowledgeDiagnostics:
    errors: list[str] = []
    warnings: list[str] = []
    artifacts = 0
    if knowledge_base_fingerprint(base) != base.knowledge_base_fingerprint:
        errors.append("knowledge base fingerprint mismatch")
    duplicates = duplicate_findings(base.entries)
    if duplicates:
        errors.append("duplicate findings")
    known_ids = {item.knowledge_id for item in base.entries}
    for entry in base.entries:
        if entry_fingerprint(entry) != entry.entry_fingerprint:
            errors.append(f"entry fingerprint mismatch: {entry.knowledge_id}")
        if entry.superseded_by and entry.superseded_by not in known_ids:
            errors.append(f"broken superseded_by: {entry.knowledge_id}")
        if not entry.affected_scenarios:
            warnings.append(f"no scenario-specific evidence: {entry.knowledge_id}")
        for evidence in entry.supporting_evidence:
            paths = (evidence.manifest_path, *evidence.artifact_paths)
            for value in paths:
                pure = PurePosixPath(value)
                if pure.is_absolute() or ".." in pure.parts:
                    errors.append(f"unsafe evidence path: {value}")
                    continue
                if not repository_root.joinpath(*pure.parts).is_file():
                    errors.append(f"missing evidence artifact: {value}")
                else:
                    artifacts += 1
            for scenario in evidence.scenario_ids:
                if scenario not in {f"SYN-{number:02d}" for number in range(1, 25)}:
                    errors.append(f"invalid scenario reference: {scenario}")
    return KnowledgeDiagnostics(
        valid=not errors,
        errors=tuple(errors),
        warnings=tuple(warnings),
        entries_validated=len(base.entries),
        artifacts_validated=artifacts,
        duplicate_findings=duplicates,
    )


def serialize_knowledge_base(path: Path, base: EditorialKnowledgeBase) -> None:
    payload = (
        json.dumps(
            base.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def deserialize_knowledge_base(path: Path) -> EditorialKnowledgeBase:
    return EditorialKnowledgeBase.model_validate_json(path.read_text(encoding="utf-8"))
