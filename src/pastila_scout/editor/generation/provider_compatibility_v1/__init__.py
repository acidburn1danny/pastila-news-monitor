"""Application-owned Producer compatibility contracts (Phase A)."""

from .errors import ProducerCompatibilityConfigurationError
from .models import (
    ProducerAttemptDiagnosticsV1,
    ProducerCompatibilityEventCodeV1,
    ProducerCompatibilityEventV1,
    ProducerDiagnosticAuthorityV1,
    ProducerDiagnosticsObservationV1,
    ProducerExecutionAttemptV1,
    ProducerExecutionDiagnosticsV1,
    ProducerExecutionFailureV1,
    ProducerExecutionLifecycleStateV1,
    ProducerExecutionLifecycleV1,
    ProducerExecutionRequestV1,
    ProducerExecutionResultV1,
    ProducerFailureCodeV1,
    ProducerFinishMetadataV1,
    ProducerTokenUsageV1,
)
from .protocols import (
    ProducerCompatibilityClockV1,
    ProducerCompatibilityObserverV1,
    ProducerDiagnosticsAuthorityV1,
)

__all__ = (  # noqa: RUF022 - normative public order
    "ProducerCompatibilityConfigurationError",
    "ProducerCompatibilityClockV1",
    "ProducerCompatibilityEventCodeV1",
    "ProducerCompatibilityEventV1",
    "ProducerCompatibilityObserverV1",
    "ProducerDiagnosticAuthorityV1",
    "ProducerDiagnosticsAuthorityV1",
    "ProducerDiagnosticsObservationV1",
    "ProducerExecutionAttemptV1",
    "ProducerExecutionDiagnosticsV1",
    "ProducerExecutionFailureV1",
    "ProducerExecutionLifecycleStateV1",
    "ProducerExecutionLifecycleV1",
    "ProducerExecutionRequestV1",
    "ProducerExecutionResultV1",
    "ProducerFailureCodeV1",
    "ProducerFinishMetadataV1",
    "ProducerAttemptDiagnosticsV1",
    "ProducerTokenUsageV1",
)
