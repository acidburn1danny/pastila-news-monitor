"""Verified consumer discovery, inventory, and separate migration planning."""

from .models import (
    CompatibilityRiskV1,
    MigrationDifficultyV1,
    RuntimeConsumerClassificationV1,
    RuntimeConsumerDiscoveryRecordV1,
    RuntimeConsumerInventoryEntryV1,
    RuntimeMigrationPlanEntryV1,
    _validated_discovery_tuple,
    _validated_unique_tuple,
)

RUNTIME_CONSUMER_DISCOVERY_V1 = _validated_discovery_tuple(
    (
        RuntimeConsumerDiscoveryRecordV1(
            package="pastila_scout.editor.generation.ai_provider_adapter.openai",
            dependency="official OpenAI SDK client and Responses execution",
            classification=RuntimeConsumerClassificationV1.DIRECT_RUNTIME_CONSUMER,
            execution_boundary="OpenAI controlled-revision adapter transport",
            migration_candidate=True,
        ),
        RuntimeConsumerDiscoveryRecordV1(
            package="pastila_scout.ai.openai_provider",
            dependency="official OpenAI SDK client and Responses execution",
            classification=RuntimeConsumerClassificationV1.DIRECT_RUNTIME_CONSUMER,
            execution_boundary="legacy structured-AI provider implementation",
            migration_candidate=True,
        ),
        RuntimeConsumerDiscoveryRecordV1(
            package="pastila_scout.cli",
            dependency="legacy OpenAI provider construction and API-key resolution",
            classification=RuntimeConsumerClassificationV1.COMPOSITION_ROOT,
            execution_boundary="Scout command provider composition",
            migration_candidate=True,
        ),
        RuntimeConsumerDiscoveryRecordV1(
            package="pastila_scout.ai.verification",
            dependency="provider-neutral AIProvider protocol",
            classification=RuntimeConsumerClassificationV1.TRANSITIVE_CONSUMER,
            execution_boundary="no direct provider execution boundary",
            migration_candidate=False,
        ),
        RuntimeConsumerDiscoveryRecordV1(
            package="pastila_scout.ai.editorial_scoring",
            dependency="provider-neutral StructuredAIProvider protocol",
            classification=RuntimeConsumerClassificationV1.TRANSITIVE_CONSUMER,
            execution_boundary="no direct provider execution boundary",
            migration_candidate=False,
        ),
        RuntimeConsumerDiscoveryRecordV1(
            package="pastila_scout.editor.script_composer",
            dependency="frozen Module 2.9 provider contracts",
            classification=RuntimeConsumerClassificationV1.FROZEN_MODULE,
            execution_boundary="frozen architecture; not an application migration seam",
            migration_candidate=False,
        ),
        RuntimeConsumerDiscoveryRecordV1(
            package="pastila_scout.provider_composition_v2",
            dependency="frozen provider-neutral registry composition",
            classification=RuntimeConsumerClassificationV1.PROVIDER_NEUTRAL_INFRASTRUCTURE,
            execution_boundary="registry infrastructure; no provider execution",
            migration_candidate=False,
        ),
    )
)

RUNTIME_CONSUMER_INVENTORY_V1 = _validated_unique_tuple(
    tuple(
        RuntimeConsumerInventoryEntryV1(
            package=record.package,
            dependency=record.dependency,
            classification=record.classification,
            execution_boundary=record.execution_boundary,
        )
        for record in RUNTIME_CONSUMER_DISCOVERY_V1
        if record.migration_candidate
    )
)

RUNTIME_MIGRATION_PLAN_V1 = _validated_unique_tuple(
    (
        RuntimeMigrationPlanEntryV1(
            package="pastila_scout.editor.generation.ai_provider_adapter.openai",
            migration_order=1,
            planned_revision="3.0-r3-producer",
            migration_boundary="replace only the Producer execution transport",
            migration_difficulty=MigrationDifficultyV1.HIGH,
            compatibility_risk=CompatibilityRiskV1.HIGH,
        ),
        RuntimeMigrationPlanEntryV1(
            package="pastila_scout.ai.openai_provider",
            migration_order=2,
            planned_revision="3.0-r4-scout-runtime",
            migration_boundary="preserve the structured-AI provider protocol",
            migration_difficulty=MigrationDifficultyV1.MEDIUM,
            compatibility_risk=CompatibilityRiskV1.HIGH,
        ),
        RuntimeMigrationPlanEntryV1(
            package="pastila_scout.cli",
            migration_order=3,
            planned_revision="3.0-r5-cli-composition",
            migration_boundary="move provider construction behind rollout wiring",
            migration_difficulty=MigrationDifficultyV1.HIGH,
            compatibility_risk=CompatibilityRiskV1.HIGH,
        ),
    )
)

__all__ = (
    "RUNTIME_CONSUMER_DISCOVERY_V1",
    "RUNTIME_CONSUMER_INVENTORY_V1",
    "RUNTIME_MIGRATION_PLAN_V1",
)
