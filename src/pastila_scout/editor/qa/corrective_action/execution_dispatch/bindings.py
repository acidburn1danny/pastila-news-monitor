"""Immutable runtime bindings between frozen descriptors and executors."""

from __future__ import annotations

from dataclasses import dataclass

from pastila_scout.editor.qa.models import fingerprint

from .contracts import CorrectiveActionExecutor
from .models import CorrectiveActionExecutorDescriptor
from .registry import CorrectiveActionExecutorRegistry, validate_executor_registry

BINDINGS_VERSION = "1"


@dataclass(frozen=True, slots=True)
class CorrectiveActionExecutorBinding:
    """Bind one exact registry descriptor to one protocol implementation."""

    descriptor: CorrectiveActionExecutorDescriptor
    executor: CorrectiveActionExecutor

    def __post_init__(self) -> None:
        advertised = self.executor.descriptor
        if advertised is not self.descriptor:
            raise ValueError("executor binding must preserve descriptor identity")


@dataclass(frozen=True, slots=True)
class CorrectiveActionExecutorBindings:
    """Canonical complete binding snapshot for one immutable registry."""

    registry: CorrectiveActionExecutorRegistry
    bindings: tuple[CorrectiveActionExecutorBinding, ...]
    bindings_version: str
    bindings_fingerprint: str

    @classmethod
    def build(
        cls,
        registry: CorrectiveActionExecutorRegistry,
        bindings: tuple[CorrectiveActionExecutorBinding, ...],
    ) -> CorrectiveActionExecutorBindings:
        validate_executor_registry(registry)
        canonical = tuple(
            sorted(bindings, key=lambda item: item.descriptor.executor_id)
        )
        for binding in canonical:
            validate_executor_binding(binding)
        descriptor_ids = tuple(item.descriptor.executor_id for item in canonical)
        descriptor_fingerprints = tuple(
            item.descriptor.descriptor_fingerprint for item in canonical
        )
        if len(set(descriptor_ids)) != len(descriptor_ids):
            raise ValueError("executor bindings contain duplicate identifiers")
        if len(set(descriptor_fingerprints)) != len(descriptor_fingerprints):
            raise ValueError("executor bindings contain duplicate descriptors")
        if len(canonical) != len(registry.descriptors) or any(
            binding.descriptor is not descriptor
            for binding, descriptor in zip(canonical, registry.descriptors, strict=True)
        ):
            raise ValueError("executor bindings must exactly cover the registry")
        values = {
            "bindings_version": BINDINGS_VERSION,
            "registry_fingerprint": registry.registry_fingerprint,
            "descriptor_fingerprints": descriptor_fingerprints,
        }
        return cls(
            registry=registry,
            bindings=canonical,
            bindings_version=BINDINGS_VERSION,
            bindings_fingerprint=fingerprint(values),
        )

    def binding_for(
        self, descriptor: CorrectiveActionExecutorDescriptor
    ) -> CorrectiveActionExecutorBinding | None:
        """Return the binding preserving exact descriptor identity, if present."""

        matches = tuple(item for item in self.bindings if item.descriptor is descriptor)
        return matches[0] if len(matches) == 1 else None


def validate_executor_binding(binding: CorrectiveActionExecutorBinding) -> None:
    """Validate descriptor identity against the executor protocol."""

    if not isinstance(binding, CorrectiveActionExecutorBinding):
        raise TypeError("invalid executor binding")
    binding.__post_init__()


def validate_executor_bindings(bindings: CorrectiveActionExecutorBindings) -> None:
    """Rebuild and compare an immutable binding snapshot."""

    if not isinstance(bindings, CorrectiveActionExecutorBindings):
        raise TypeError("invalid executor bindings")
    rebuilt = CorrectiveActionExecutorBindings.build(
        bindings.registry, bindings.bindings
    )
    if rebuilt != bindings:
        raise ValueError("executor bindings fingerprint is inconsistent")
