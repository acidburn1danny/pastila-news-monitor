"""Explicit opt-in Producer compatibility execution API."""

from .protocols import ProducerGatewayProjectorV1
from .runtime import (
    ProducerCompatibilityCoordinatorV1,
    ProducerCompatibilityRuntimeV1,
    compose_producer_compatibility_runtime_v1,
)

__all__ = (
    "ProducerCompatibilityCoordinatorV1",
    "ProducerCompatibilityRuntimeV1",
    "ProducerGatewayProjectorV1",
    "compose_producer_compatibility_runtime_v1",
)
