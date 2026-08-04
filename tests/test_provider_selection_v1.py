"""Focused offline tests for explicit application-owned provider selection."""

from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import dataclass
from inspect import Parameter, Signature
from pathlib import Path

import pytest

import pastila_scout.provider_selection_v1 as public_api
from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_selection_v1 import (
    DuplicateProviderRegistrationError,
    InvalidProviderExecutorError,
    MissingProviderRegistrationError,
    ProviderChoiceV1,
    ProviderExecutorRegistrationV1,
    ProviderSelectionConfigurationError,
    ProviderSelectionConfigV1,
    ProviderSelectorV1,
)

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "pastila_scout" / "provider_selection_v1"
EXPECTED_API = (
    "DuplicateProviderRegistrationError",
    "InvalidProviderExecutorError",
    "MissingProviderRegistrationError",
    "ProviderChoiceV1",
    "ProviderExecutorRegistrationV1",
    "ProviderSelectionConfigV1",
    "ProviderSelectionConfigurationError",
    "ProviderSelectionError",
    "ProviderSelectorV1",
    "UnknownProviderSelectionError",
)


@dataclass
class _RecordingExecutor:
    calls: int = 0

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        del request
        self.calls += 1
        raise AssertionError("selection must not execute providers")


def _registrations() -> (
    tuple[ProviderExecutorRegistrationV1, ProviderExecutorRegistrationV1]
):
    return (
        ProviderExecutorRegistrationV1(
            provider=ProviderChoiceV1.OPENAI,
            executor=_RecordingExecutor(),
        ),
        ProviderExecutorRegistrationV1(
            provider=ProviderChoiceV1.OLLAMA,
            executor=_RecordingExecutor(),
        ),
    )


def test_public_api_is_exact_and_provider_vocabulary_has_no_aliases() -> None:
    assert public_api.__all__ == EXPECTED_API
    assert tuple(ProviderChoiceV1) == (
        ProviderChoiceV1.OPENAI,
        ProviderChoiceV1.OLLAMA,
    )
    assert tuple(item.value for item in ProviderChoiceV1) == ("openai", "ollama")


@pytest.mark.parametrize("provider", (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA))
def test_explicit_selection_exposes_only_requested_executor_without_execution(
    provider: ProviderChoiceV1,
) -> None:
    registrations = _registrations()

    selector = ProviderSelectorV1(
        ProviderSelectionConfigV1(provider=provider), registrations
    )

    expected = next(
        item.executor for item in registrations if item.provider is provider
    )
    assert selector.executor is expected
    assert not hasattr(selector, "execute")
    assert tuple(item.executor.calls for item in registrations) == (0, 0)


@pytest.mark.parametrize(
    "provider", ("OPENAI", "OLLAMA", "OpenAI", "local", "remote", "auto", "")
)
def test_raw_unknown_alias_or_normalized_provider_is_rejected(provider: str) -> None:
    with pytest.raises(ProviderSelectionConfigurationError):
        ProviderSelectionConfigV1(provider=provider)  # type: ignore[arg-type]

    forged = ProviderSelectionConfigV1(provider=ProviderChoiceV1.OPENAI)
    object.__setattr__(
        forged,
        "provider",
        provider,
    )
    with pytest.raises(ProviderSelectionConfigurationError) as captured:
        ProviderSelectorV1(forged, _registrations())
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    assert captured.value.__suppress_context__ is True


def test_duplicate_registration_is_rejected_deterministically() -> None:
    executor = _RecordingExecutor()
    registrations = (
        ProviderExecutorRegistrationV1(ProviderChoiceV1.OPENAI, executor),
        ProviderExecutorRegistrationV1(ProviderChoiceV1.OPENAI, executor),
        ProviderExecutorRegistrationV1(ProviderChoiceV1.OLLAMA, _RecordingExecutor()),
    )

    with pytest.raises(
        DuplicateProviderRegistrationError,
        match="provider registration is duplicated",
    ):
        ProviderSelectorV1(
            ProviderSelectionConfigV1(provider=ProviderChoiceV1.OPENAI),
            registrations,
        )
    assert executor.calls == 0


@pytest.mark.parametrize("registrations", ((), None, [], object()))
def test_missing_or_invalid_registrations_are_rejected(registrations) -> None:
    error = (
        MissingProviderRegistrationError
        if registrations == ()
        else ProviderSelectionConfigurationError
    )
    with pytest.raises(error):
        ProviderSelectorV1(
            ProviderSelectionConfigV1(provider=ProviderChoiceV1.OPENAI),
            registrations,  # type: ignore[arg-type]
        )


def test_one_missing_supported_provider_is_rejected_without_execution() -> None:
    executor = _RecordingExecutor()
    with pytest.raises(MissingProviderRegistrationError):
        ProviderSelectorV1(
            ProviderSelectionConfigV1(provider=ProviderChoiceV1.OPENAI),
            (ProviderExecutorRegistrationV1(ProviderChoiceV1.OPENAI, executor),),
        )
    assert executor.calls == 0


def test_missing_or_invalid_configuration_uses_application_error() -> None:
    for config in (None, object()):
        with pytest.raises(ProviderSelectionConfigurationError):
            ProviderSelectorV1(config, _registrations())  # type: ignore[arg-type]


@pytest.mark.parametrize("executor", (None, object(), "executor"))
def test_invalid_executor_is_rejected_without_dynamic_lookup(executor) -> None:
    with pytest.raises(InvalidProviderExecutorError):
        ProviderExecutorRegistrationV1(ProviderChoiceV1.OPENAI, executor)


def test_malformed_protocol_names_annotations_and_forged_signature_are_rejected() -> (
    None
):
    class WrongNames:
        def execute(
            instance, payload: ProviderExecutionRequestV2
        ) -> ProviderExecutionResultV2:
            raise AssertionError

    class WrongReturn:
        def execute(self, request: ProviderExecutionRequestV2) -> str:
            raise AssertionError

    class MissingAnnotations:
        def execute(self, request):
            raise AssertionError

    class ForgedSignature:
        def execute(self) -> str:
            raise AssertionError

    ForgedSignature.execute.__signature__ = Signature(  # type: ignore[attr-defined]
        (
            Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),
            Parameter("request", Parameter.POSITIONAL_OR_KEYWORD),
        )
    )
    for executor_type in (
        WrongNames,
        WrongReturn,
        MissingAnnotations,
        ForgedSignature,
    ):
        with pytest.raises(InvalidProviderExecutorError):
            ProviderExecutorRegistrationV1(ProviderChoiceV1.OPENAI, executor_type())


def test_copied_invalid_registration_is_revalidated_before_set_invariants() -> None:
    registration = ProviderExecutorRegistrationV1(
        ProviderChoiceV1.OPENAI, _RecordingExecutor()
    )
    object.__setattr__(registration, "executor", object())
    valid_ollama = ProviderExecutorRegistrationV1(
        ProviderChoiceV1.OLLAMA, _RecordingExecutor()
    )

    with pytest.raises(InvalidProviderExecutorError):
        ProviderSelectorV1(
            ProviderSelectionConfigV1(provider=ProviderChoiceV1.OPENAI),
            (registration, valid_ollama),
        )

    object.__setattr__(registration, "provider", "foreign")
    with pytest.raises(ProviderSelectionConfigurationError):
        ProviderSelectorV1(
            ProviderSelectionConfigV1(provider=ProviderChoiceV1.OPENAI),
            (registration, valid_ollama),
        )


def test_repeated_selection_is_deterministic_and_preserves_injected_identity() -> None:
    registrations = _registrations()
    config = ProviderSelectionConfigV1(provider=ProviderChoiceV1.OLLAMA)

    selections = tuple(ProviderSelectorV1(config, registrations) for _ in range(3))

    assert all(item.executor is registrations[1].executor for item in selections)
    assert tuple(item.executor.calls for item in registrations) == (0, 0)


def test_import_is_passive_and_package_has_no_operational_dependencies() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-W",
            "error",
            "-c",
            "import pastila_scout.provider_selection_v1",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stdout == completed.stderr == ""

    forbidden = {
        "httpx",
        "openai",
        "socket",
        "subprocess",
        "threading",
        "provider_execution_openai_v2",
        "provider_execution_ollama_v1",
    }
    imports = set()
    for path in PACKAGE.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports.update(
            (node.module or "").split(".")[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        imports.update(
            alias.name.split(".")[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        )
    assert not imports & forbidden
