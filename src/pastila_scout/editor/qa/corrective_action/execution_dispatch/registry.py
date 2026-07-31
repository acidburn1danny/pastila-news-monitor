"""Immutable canonical executor-descriptor registry for M6C.6B Part 2."""

from collections.abc import Iterable
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionPlanType,
)
from pastila_scout.editor.qa.models import fingerprint

from .models import CorrectiveActionExecutorDescriptor
from .validation import validate_executor_descriptor

REGISTRY_VERSION = "1"
REGISTRY_REPORT_VERSION = "1"


class CorrectiveActionExecutorRegistry(FrozenModel):
    """Immutable descriptor-only snapshot with deterministic lookup."""

    registry_version: str = REGISTRY_VERSION
    descriptors: tuple[CorrectiveActionExecutorDescriptor, ...]
    registry_fingerprint: str

    @classmethod
    def build(
        cls, descriptors: Iterable[CorrectiveActionExecutorDescriptor]
    ) -> CorrectiveActionExecutorRegistry:
        canonical = tuple(
            sorted(
                descriptors,
                key=lambda item: (item.executor_id, item.descriptor_fingerprint),
            )
        )
        values = {
            "registry_version": REGISTRY_VERSION,
            "descriptors": canonical,
        }
        return cls(
            **values, registry_fingerprint=fingerprint(_registry_identity(values))
        )

    def lookup(
        self,
        capability: CorrectiveActionExecutionCapability,
        plan_type: CorrectiveActionExecutionPlanType,
    ) -> tuple[CorrectiveActionExecutorDescriptor, ...]:
        """Return all exact compatible descriptors in canonical order."""

        return tuple(
            descriptor
            for descriptor in self.descriptors
            if descriptor.supported_capability is capability
            and plan_type in descriptor.supported_plan_types
        )

    @model_validator(mode="after")
    def invariants(self):
        if self.registry_version != REGISTRY_VERSION:
            raise ValueError("unsupported executor registry version")
        canonical = tuple(
            sorted(
                self.descriptors,
                key=lambda item: (item.executor_id, item.descriptor_fingerprint),
            )
        )
        if canonical != self.descriptors:
            raise ValueError("executor registry ordering is not canonical")
        identifiers = tuple(item.executor_id for item in self.descriptors)
        fingerprints = tuple(item.descriptor_fingerprint for item in self.descriptors)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("executor registry contains duplicate identifiers")
        if len(set(fingerprints)) != len(fingerprints):
            raise ValueError("executor registry contains duplicate descriptors")
        for descriptor in self.descriptors:
            validate_executor_descriptor(descriptor)
        expected = fingerprint(_registry_identity(self.model_dump(mode="python")))
        if self.registry_fingerprint != expected:
            raise ValueError("executor registry fingerprint is inconsistent")
        return self


class CorrectiveActionExecutorRegistryReport(FrozenModel):
    """Safe non-authoritative registry snapshot projection."""

    report_version: str = REGISTRY_REPORT_VERSION
    registry_version: str
    descriptor_count: int
    executor_ids: tuple[str, ...]
    descriptor_fingerprints: tuple[str, ...]
    registry_fingerprint: str
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutorRegistryReport:
        values.setdefault("report_version", REGISTRY_REPORT_VERSION)
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.report_version != REGISTRY_REPORT_VERSION:
            raise ValueError("unsupported registry report version")
        if self.descriptor_count != len(
            self.executor_ids
        ) or self.descriptor_count != len(self.descriptor_fingerprints):
            raise ValueError("registry report counts are inconsistent")
        expected = fingerprint(
            self.model_dump(exclude={"report_fingerprint"}, mode="python")
        )
        if self.report_fingerprint != expected:
            raise ValueError("registry report fingerprint is inconsistent")
        return self


def build_executor_registry_report(
    registry: CorrectiveActionExecutorRegistry,
) -> CorrectiveActionExecutorRegistryReport:
    """Build a safe deterministic registry projection."""

    return CorrectiveActionExecutorRegistryReport.build(
        registry_version=registry.registry_version,
        descriptor_count=len(registry.descriptors),
        executor_ids=tuple(item.executor_id for item in registry.descriptors),
        descriptor_fingerprints=tuple(
            item.descriptor_fingerprint for item in registry.descriptors
        ),
        registry_fingerprint=registry.registry_fingerprint,
    )


def validate_executor_registry(registry: CorrectiveActionExecutorRegistry) -> None:
    """Validate registry structure, nested descriptors, and fingerprint."""

    if not isinstance(registry, CorrectiveActionExecutorRegistry):
        raise TypeError("invalid executor registry")
    registry.invariants()


def _registry_identity(values):
    descriptors = values["descriptors"]
    return {
        "registry_version": values["registry_version"],
        "descriptor_fingerprints": tuple(
            _field(item, "descriptor_fingerprint") for item in descriptors
        ),
    }


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)
