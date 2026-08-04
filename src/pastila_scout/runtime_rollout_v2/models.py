"""Strict immutable contracts for Module 3.0 runtime rollout discovery."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RuntimeConsumerClassificationV1(StrEnum):
    """Static classification assigned to one discovered dependency candidate."""

    DIRECT_RUNTIME_CONSUMER = "direct_runtime_consumer"
    TRANSITIVE_CONSUMER = "transitive_consumer"
    COMPOSITION_ROOT = "composition_root"
    PROVIDER_NEUTRAL_INFRASTRUCTURE = "provider_neutral_infrastructure"
    FROZEN_MODULE = "frozen_module"
    DOCUMENTATION_ONLY = "documentation_only"
    TEST_ONLY = "test_only"


class MigrationDifficultyV1(StrEnum):
    """Estimated implementation difficulty for a planned consumer migration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CompatibilityRiskV1(StrEnum):
    """Estimated compatibility risk for a planned consumer migration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _strict_text(value: object, field_name: str) -> None:
    if type(value) is not str or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a non-blank unpadded string")


@dataclass(frozen=True, slots=True)
class RuntimeConsumerDiscoveryRecordV1:
    """One statically discovered candidate and its verified classification."""

    package: str
    dependency: str
    classification: RuntimeConsumerClassificationV1
    execution_boundary: str
    migration_candidate: bool

    def __post_init__(self) -> None:
        _strict_text(self.package, "package")
        _strict_text(self.dependency, "dependency")
        _strict_text(self.execution_boundary, "execution_boundary")
        if type(self.classification) is not RuntimeConsumerClassificationV1:
            raise TypeError("classification must be RuntimeConsumerClassificationV1")
        if type(self.migration_candidate) is not bool:
            raise TypeError("migration_candidate must be bool")
        eligible = self.classification in {
            RuntimeConsumerClassificationV1.DIRECT_RUNTIME_CONSUMER,
            RuntimeConsumerClassificationV1.COMPOSITION_ROOT,
        }
        if self.migration_candidate is not eligible:
            raise ValueError("migration_candidate must agree with classification")


@dataclass(frozen=True, slots=True)
class RuntimeConsumerInventoryEntryV1:
    """One application-owned direct runtime migration candidate."""

    package: str
    dependency: str
    classification: RuntimeConsumerClassificationV1
    execution_boundary: str

    def __post_init__(self) -> None:
        _strict_text(self.package, "package")
        _strict_text(self.dependency, "dependency")
        _strict_text(self.execution_boundary, "execution_boundary")
        if type(self.classification) is not RuntimeConsumerClassificationV1:
            raise TypeError("classification must be RuntimeConsumerClassificationV1")
        if self.classification not in {
            RuntimeConsumerClassificationV1.DIRECT_RUNTIME_CONSUMER,
            RuntimeConsumerClassificationV1.COMPOSITION_ROOT,
        }:
            raise ValueError(
                "inventory entries must represent direct runtime candidates"
            )


@dataclass(frozen=True, slots=True)
class RuntimeMigrationPlanEntryV1:
    """Prescriptive migration metadata kept separate from discovered inventory."""

    package: str
    migration_order: int
    planned_revision: str
    migration_boundary: str
    migration_difficulty: MigrationDifficultyV1
    compatibility_risk: CompatibilityRiskV1

    def __post_init__(self) -> None:
        _strict_text(self.package, "package")
        _strict_text(self.planned_revision, "planned_revision")
        _strict_text(self.migration_boundary, "migration_boundary")
        if type(self.migration_order) is not int or self.migration_order <= 0:
            raise ValueError("migration_order must be a positive integer")
        if type(self.migration_difficulty) is not MigrationDifficultyV1:
            raise TypeError("migration_difficulty must be MigrationDifficultyV1")
        if type(self.compatibility_risk) is not CompatibilityRiskV1:
            raise TypeError("compatibility_risk must be CompatibilityRiskV1")


def _validated_unique_tuple[
    EntryT: (RuntimeConsumerInventoryEntryV1, RuntimeMigrationPlanEntryV1),
](entries: tuple[EntryT, ...]) -> tuple[EntryT, ...]:
    if type(entries) is not tuple:
        raise TypeError("entries must be a tuple")
    if entries:
        expected_type = type(entries[0])
        if expected_type not in {
            RuntimeConsumerInventoryEntryV1,
            RuntimeMigrationPlanEntryV1,
        }:
            raise TypeError("entries must use an authoritative model type")
        for entry in entries:
            if type(entry) is not expected_type:
                raise TypeError("entries must use one exact model type")
            _revalidate_entry(entry)
    packages = tuple(entry.package for entry in entries)
    if len(packages) != len(set(packages)):
        raise ValueError("duplicate package")
    if entries and type(entries[0]) is RuntimeMigrationPlanEntryV1:
        orders = tuple(entry.migration_order for entry in entries)  # type: ignore[attr-defined]
        if len(orders) != len(set(orders)):
            raise ValueError("duplicate migration order")
        if orders != tuple(sorted(orders)):
            raise ValueError("migration plan must be ordered")
    return entries


def _validated_discovery_tuple(
    entries: tuple[RuntimeConsumerDiscoveryRecordV1, ...],
) -> tuple[RuntimeConsumerDiscoveryRecordV1, ...]:
    if type(entries) is not tuple:
        raise TypeError("discovery entries must be an exact tuple")
    for entry in entries:
        if type(entry) is not RuntimeConsumerDiscoveryRecordV1:
            raise TypeError("discovery entries must use the exact model type")
        _revalidate_entry(entry)
    packages = tuple(entry.package for entry in entries)
    if len(packages) != len(set(packages)):
        raise ValueError("duplicate package")
    return entries


def _revalidate_entry(
    entry: (
        RuntimeConsumerDiscoveryRecordV1
        | RuntimeConsumerInventoryEntryV1
        | RuntimeMigrationPlanEntryV1
    ),
) -> None:
    """Reapply exact model semantics to potentially reconstructed retained state."""

    if type(entry) is RuntimeConsumerDiscoveryRecordV1:
        RuntimeConsumerDiscoveryRecordV1(
            package=entry.package,
            dependency=entry.dependency,
            classification=entry.classification,
            execution_boundary=entry.execution_boundary,
            migration_candidate=entry.migration_candidate,
        )
        return
    if type(entry) is RuntimeConsumerInventoryEntryV1:
        RuntimeConsumerInventoryEntryV1(
            package=entry.package,
            dependency=entry.dependency,
            classification=entry.classification,
            execution_boundary=entry.execution_boundary,
        )
        return
    if type(entry) is RuntimeMigrationPlanEntryV1:
        RuntimeMigrationPlanEntryV1(
            package=entry.package,
            migration_order=entry.migration_order,
            planned_revision=entry.planned_revision,
            migration_boundary=entry.migration_boundary,
            migration_difficulty=entry.migration_difficulty,
            compatibility_risk=entry.compatibility_risk,
        )
        return
    raise TypeError("entry must use an authoritative model type")


__all__ = (
    "CompatibilityRiskV1",
    "MigrationDifficultyV1",
    "RuntimeConsumerClassificationV1",
    "RuntimeConsumerDiscoveryRecordV1",
    "RuntimeConsumerInventoryEntryV1",
    "RuntimeMigrationPlanEntryV1",
)
