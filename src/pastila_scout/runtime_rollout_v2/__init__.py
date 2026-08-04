"""Public contracts for verified Module 3.0 runtime-consumer discovery."""

from .inventory import (
    RUNTIME_CONSUMER_DISCOVERY_V1,
    RUNTIME_CONSUMER_INVENTORY_V1,
    RUNTIME_MIGRATION_PLAN_V1,
)
from .models import (
    CompatibilityRiskV1,
    MigrationDifficultyV1,
    RuntimeConsumerClassificationV1,
    RuntimeConsumerDiscoveryRecordV1,
    RuntimeConsumerInventoryEntryV1,
    RuntimeMigrationPlanEntryV1,
)

__all__ = (
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
