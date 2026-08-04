from __future__ import annotations

import copy
import dataclasses
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

import pastila_scout.runtime_rollout_v2 as public_api
from pastila_scout.runtime_rollout_v2 import (
    RUNTIME_CONSUMER_DISCOVERY_V1,
    RUNTIME_CONSUMER_INVENTORY_V1,
    RUNTIME_MIGRATION_PLAN_V1,
    CompatibilityRiskV1,
    MigrationDifficultyV1,
    RuntimeConsumerClassificationV1,
    RuntimeConsumerDiscoveryRecordV1,
    RuntimeConsumerInventoryEntryV1,
    RuntimeMigrationPlanEntryV1,
)
from pastila_scout.runtime_rollout_v2.discovery import (
    discover_direct_runtime_consumers,
)
from pastila_scout.runtime_rollout_v2.models import (
    _validated_discovery_tuple,
    _validated_unique_tuple,
)

ROOT = Path(__file__).parents[1]
SOURCE_ROOT = ROOT / "src" / "pastila_scout"


def test_public_api_is_exact() -> None:
    assert public_api.__all__ == (
        "RUNTIME_CONSUMER_DISCOVERY_V1",
        "RUNTIME_CONSUMER_INVENTORY_V1",
        "RUNTIME_MIGRATION_PLAN_V1",
        "CompatibilityRiskV1",
        "MigrationDifficultyV1",
        "RuntimeConsumerClassificationV1",
        "RuntimeConsumerDiscoveryRecordV1",
        "RuntimeConsumerInventoryEntryV1",
        "RuntimeMigrationPlanEntryV1",
    )


def test_repository_discovery_matches_authoritative_inventory() -> None:
    discovered = discover_direct_runtime_consumers(SOURCE_ROOT)
    authoritative = tuple(
        sorted(item.package for item in RUNTIME_CONSUMER_INVENTORY_V1)
    )

    assert discovered == authoritative
    assert discovered == (
        "pastila_scout.ai.openai_provider",
        "pastila_scout.cli",
        "pastila_scout.editor.generation.ai_provider_adapter.openai",
    )


def test_discovery_classifies_excluded_candidates() -> None:
    classifications = {
        item.package: item.classification for item in RUNTIME_CONSUMER_DISCOVERY_V1
    }

    assert classifications["pastila_scout.editor.script_composer"] is (
        RuntimeConsumerClassificationV1.FROZEN_MODULE
    )
    assert classifications["pastila_scout.provider_composition_v2"] is (
        RuntimeConsumerClassificationV1.PROVIDER_NEUTRAL_INFRASTRUCTURE
    )
    assert classifications["pastila_scout.ai.verification"] is (
        RuntimeConsumerClassificationV1.TRANSITIVE_CONSUMER
    )
    assert classifications["pastila_scout.ai.editorial_scoring"] is (
        RuntimeConsumerClassificationV1.TRANSITIVE_CONSUMER
    )


def test_inventory_contains_only_verified_migration_candidates() -> None:
    candidates = tuple(
        record.package
        for record in RUNTIME_CONSUMER_DISCOVERY_V1
        if record.migration_candidate
    )
    assert tuple(item.package for item in RUNTIME_CONSUMER_INVENTORY_V1) == candidates
    assert all(
        item.classification
        in {
            RuntimeConsumerClassificationV1.DIRECT_RUNTIME_CONSUMER,
            RuntimeConsumerClassificationV1.COMPOSITION_ROOT,
        }
        for item in RUNTIME_CONSUMER_INVENTORY_V1
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("package", ""),
        ("package", " padded"),
        ("dependency", " "),
        ("execution_boundary", "padded "),
    ),
)
def test_inventory_entry_rejects_blank_or_padded_text(
    field: str, value: object
) -> None:
    values: dict[str, object] = {
        "package": "package",
        "dependency": "dependency",
        "classification": RuntimeConsumerClassificationV1.DIRECT_RUNTIME_CONSUMER,
        "execution_boundary": "boundary",
    }
    values[field] = value

    with pytest.raises(ValueError):
        RuntimeConsumerInventoryEntryV1(**values)  # type: ignore[arg-type]


def test_models_reject_string_instead_of_enum() -> None:
    with pytest.raises(TypeError):
        RuntimeConsumerDiscoveryRecordV1(
            package="package",
            dependency="dependency",
            classification="direct_runtime_consumer",  # type: ignore[arg-type]
            execution_boundary="boundary",
            migration_candidate=True,
        )
    with pytest.raises(TypeError):
        RuntimeMigrationPlanEntryV1(
            package="package",
            migration_order=1,
            planned_revision="revision",
            migration_boundary="boundary",
            migration_difficulty="high",  # type: ignore[arg-type]
            compatibility_risk=CompatibilityRiskV1.HIGH,
        )
    with pytest.raises(TypeError):
        RuntimeMigrationPlanEntryV1(
            package="package",
            migration_order=1,
            planned_revision="revision",
            migration_boundary="boundary",
            migration_difficulty=MigrationDifficultyV1.HIGH,
            compatibility_risk="high",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("package", ""),
        ("planned_revision", " padded"),
        ("migration_boundary", " "),
    ),
)
def test_migration_plan_rejects_blank_or_padded_text(field: str, value: object) -> None:
    values: dict[str, object] = {
        "package": "package",
        "migration_order": 1,
        "planned_revision": "revision",
        "migration_boundary": "boundary",
        "migration_difficulty": MigrationDifficultyV1.LOW,
        "compatibility_risk": CompatibilityRiskV1.LOW,
    }
    values[field] = value

    with pytest.raises(ValueError):
        RuntimeMigrationPlanEntryV1(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("order", (0, -1, "1", True))
def test_migration_plan_rejects_invalid_order(order: object) -> None:
    with pytest.raises(ValueError):
        RuntimeMigrationPlanEntryV1(
            package="package",
            migration_order=order,  # type: ignore[arg-type]
            planned_revision="revision",
            migration_boundary="boundary",
            migration_difficulty=MigrationDifficultyV1.LOW,
            compatibility_risk=CompatibilityRiskV1.LOW,
        )


def test_collection_validation_rejects_duplicate_package_and_order() -> None:
    entry = RUNTIME_CONSUMER_INVENTORY_V1[0]
    with pytest.raises(ValueError, match="duplicate package"):
        _validated_unique_tuple((entry, entry))

    first = RUNTIME_MIGRATION_PLAN_V1[0]
    duplicate_order = RuntimeMigrationPlanEntryV1(
        package="another.package",
        migration_order=first.migration_order,
        planned_revision="another-revision",
        migration_boundary="another boundary",
        migration_difficulty=MigrationDifficultyV1.LOW,
        compatibility_risk=CompatibilityRiskV1.LOW,
    )
    with pytest.raises(ValueError, match="duplicate migration order"):
        _validated_unique_tuple((first, duplicate_order))

    discovery = RUNTIME_CONSUMER_DISCOVERY_V1[0]
    with pytest.raises(ValueError, match="duplicate package"):
        _validated_discovery_tuple((discovery, discovery))


def test_discovery_candidate_flag_must_match_classification() -> None:
    with pytest.raises(ValueError, match="agree with classification"):
        RuntimeConsumerDiscoveryRecordV1(
            package="package",
            dependency="dependency",
            classification=RuntimeConsumerClassificationV1.FROZEN_MODULE,
            execution_boundary="boundary",
            migration_candidate=True,
        )


@pytest.mark.parametrize(
    "reconstruct",
    (
        copy.copy,
        copy.deepcopy,
        lambda value: pickle.loads(pickle.dumps(value)),
    ),
    ids=("copy", "deepcopy", "pickle"),
)
def test_authoritative_inventory_rejects_copied_invalid_retained_state(
    reconstruct: object,
) -> None:
    entry = RuntimeConsumerInventoryEntryV1(
        package="package",
        dependency="dependency",
        classification=RuntimeConsumerClassificationV1.DIRECT_RUNTIME_CONSUMER,
        execution_boundary="boundary",
    )
    object.__setattr__(entry, "package", " ")
    retained = reconstruct(entry)  # type: ignore[operator]

    with pytest.raises(ValueError, match="package"):
        _validated_unique_tuple((retained,))


@pytest.mark.parametrize(
    ("field", "invalid"),
    (
        ("package", " "),
        ("dependency", " padded"),
        ("classification", "direct_runtime_consumer"),
        ("execution_boundary", "boundary "),
    ),
)
def test_inventory_collection_revalidates_every_field(
    field: str, invalid: object
) -> None:
    entry = RuntimeConsumerInventoryEntryV1(
        package="package",
        dependency="dependency",
        classification=RuntimeConsumerClassificationV1.DIRECT_RUNTIME_CONSUMER,
        execution_boundary="boundary",
    )
    object.__setattr__(entry, field, invalid)

    with pytest.raises((TypeError, ValueError)):
        _validated_unique_tuple((entry,))


def test_discovery_collection_revalidates_retained_state() -> None:
    entry = RUNTIME_CONSUMER_DISCOVERY_V1[0]
    retained = copy.copy(entry)
    object.__setattr__(retained, "migration_candidate", False)

    with pytest.raises(ValueError, match="agree with classification"):
        _validated_discovery_tuple((retained,))


def test_plan_collection_revalidates_retained_state() -> None:
    entry = copy.deepcopy(RUNTIME_MIGRATION_PLAN_V1[0])
    object.__setattr__(entry, "migration_order", True)

    with pytest.raises(ValueError, match="positive integer"):
        _validated_unique_tuple((entry,))


def test_semantic_validation_precedes_duplicate_detection() -> None:
    first = copy.copy(RUNTIME_CONSUMER_INVENTORY_V1[0])
    duplicate = copy.copy(first)
    object.__setattr__(first, "dependency", " ")

    with pytest.raises(ValueError, match="dependency"):
        _validated_unique_tuple((first, duplicate))


def test_collections_reject_subclassed_retained_primitives_and_enum_lookalikes() -> (
    None
):
    class StringSubclass(str):
        pass

    class IntegerSubclass(int):
        pass

    class ClassificationLookalike(str):
        pass

    inventory = copy.copy(RUNTIME_CONSUMER_INVENTORY_V1[0])
    object.__setattr__(inventory, "package", StringSubclass(inventory.package))
    with pytest.raises(ValueError, match="package"):
        _validated_unique_tuple((inventory,))

    plan = copy.copy(RUNTIME_MIGRATION_PLAN_V1[0])
    object.__setattr__(plan, "migration_order", IntegerSubclass(1))
    with pytest.raises(ValueError, match="positive integer"):
        _validated_unique_tuple((plan,))

    discovery = copy.copy(RUNTIME_CONSUMER_DISCOVERY_V1[0])
    object.__setattr__(
        discovery,
        "classification",
        ClassificationLookalike("direct_runtime_consumer"),
    )
    with pytest.raises(TypeError, match="classification"):
        _validated_discovery_tuple((discovery,))


def test_inventory_is_immutable_and_deterministic() -> None:
    assert type(RUNTIME_CONSUMER_INVENTORY_V1) is tuple
    assert RUNTIME_CONSUMER_INVENTORY_V1 == tuple(RUNTIME_CONSUMER_INVENTORY_V1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        RUNTIME_CONSUMER_INVENTORY_V1[0].package = "changed"  # type: ignore[misc]


def test_passive_import_does_not_load_operational_modules() -> None:
    script = """
import sys
before = set(sys.modules)
import pastila_scout.runtime_rollout_v2
loaded = set(sys.modules) - before
for name in loaded:
    assert name != 'openai' and not name.startswith('openai.')
    assert 'provider_runtime_openai' not in name
    assert 'provider_execution_openai' not in name
print('PASSIVE_OK')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "PASSIVE_OK\n"
    assert result.stderr == ""
