"""Safe deterministic Part 2 registry, eligibility, and resolution reports."""

import json

from pastila_scout.editor.generation.models import FrozenModel

from .eligibility import DispatchEligibilityReport
from .registry import CorrectiveActionExecutorRegistryReport
from .resolution import CapabilityResolutionReport


def serialize_executor_registry_report(
    report: CorrectiveActionExecutorRegistryReport,
) -> str:
    """Serialize a safe registry projection deterministically."""

    return _serialize(report)


def serialize_dispatch_eligibility_report(
    report: DispatchEligibilityReport,
) -> str:
    """Serialize a safe eligibility projection deterministically."""

    return _serialize(report)


def serialize_capability_resolution_report(
    report: CapabilityResolutionReport,
) -> str:
    """Serialize a safe resolution projection deterministically."""

    return _serialize(report)


def render_executor_registry_report(
    report: CorrectiveActionExecutorRegistryReport,
) -> str:
    """Render safe registry identity and descriptor count."""

    return (
        f"Registry version: {report.registry_version}\n"
        f"Descriptors: {report.descriptor_count}\n"
        f"Registry fingerprint: {report.registry_fingerprint}\n"
    )


def render_dispatch_eligibility_report(report: DispatchEligibilityReport) -> str:
    """Render safe eligibility classification and lineage."""

    return (
        f"Eligibility: {report.status.value}\n"
        f"Capability: {report.required_capability.value if report.required_capability else 'absent'}\n"
        f"Diagnostic: {report.diagnostic_code.value if report.diagnostic_code else 'absent'}\n"
    )


def render_capability_resolution_report(report: CapabilityResolutionReport) -> str:
    """Render safe resolution status, cardinality, and executor identity."""

    return (
        f"Resolution: {report.status.value}\n"
        f"Matches: {report.matching_descriptor_count}\n"
        f"Executor: {report.executor_id or 'absent'}\n"
        f"Diagnostic: {report.diagnostic_code.value if report.diagnostic_code else 'absent'}\n"
    )


def _serialize(report: FrozenModel) -> str:
    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
