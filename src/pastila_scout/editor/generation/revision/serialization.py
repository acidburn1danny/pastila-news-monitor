"""Deterministic runtime and explicitly non-reconstructable safe serializers."""

from pastila_scout.editor.generation.models import FrozenModel

from .identity import canonical_json
from .reporting import (
    ControlledRevisionExecutionReport,
    ControlledRevisionRequestReport,
)


def serialize_revision_contract(value: FrozenModel) -> str:
    """Serialize an immutable runtime contract, including its authorized content."""

    return canonical_json(value)


def serialize_revision_report(
    value: ControlledRevisionRequestReport | ControlledRevisionExecutionReport,
) -> str:
    """Serialize a privacy-safe projection; this is not a runtime input format."""

    return canonical_json(value)
