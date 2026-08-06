"""Thin command adapter for one explicit Editor application execution."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.contracts.io import ContractFileError, load_contract
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.editor_application_v1 import (
    EditorApplicationConfigurationError,
    EditorApplicationCoordinatorError,
    EditorApplicationExportError,
    EditorApplicationGenerationConfigurationAuthorityV1,
    EditorApplicationRequestV1,
    EditorApplicationResultV1,
    EditorApplicationSerializationError,
    EditorApplicationStatusV1,
    EditorEpisodeContextAuthorityV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
    EditorSelectionProfileAuthorityV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .composition import _compose_editor_cli_application_v1

_OPERATION_REFERENCE = "editor-run-v1"


def run_editor_command(
    *,
    input_path: Path,
    selection_profile_path: Path,
    episode_context_path: Path,
    generation_config_path: Path,
    provider: str,
    model: str,
    timeout_seconds: float,
    cancelled: str,
    output_path: Path,
    overwrite_policy: str,
) -> int:
    """Validate, compose, execute once, and project one safe public outcome."""

    try:
        scout_input = _load_scout_input(input_path)
        profile = EditorSelectionProfileAuthorityV1().load(path=selection_profile_path)
        context = EditorEpisodeContextAuthorityV1().load(path=episode_context_path)
        generation = EditorApplicationGenerationConfigurationAuthorityV1().load(
            path=generation_config_path
        )
        _confirm_configuration(generation, provider, model, timeout_seconds)
        destination = EditorOutputDestinationV1(
            _absolute_path(output_path),
            EditorOverwritePolicyV1(overwrite_policy),
        )
        cancellation = CancellationTokenV2(cancellation_requested=cancelled == "true")
        requested_at = datetime.now(UTC)
        coordinator = _compose_editor_cli_application_v1()
        request = EditorApplicationRequestV1(
            scout_input,
            profile,
            context,
            generation,
            destination,
            requested_at,
            _OPERATION_REFERENCE,
            cancellation,
        )
    except EditorApplicationConfigurationError:
        _failure("Editor application configuration is invalid.")
        return 2
    try:
        result = coordinator.execute(request=request)
    except EditorApplicationConfigurationError:
        _failure("Editor application configuration is invalid.")
        return 2
    except EditorApplicationSerializationError:
        _failure("Editor operational result serialization failed.")
        return 6
    except EditorApplicationExportError:
        _failure("Editor output export failed.")
        return 6
    except EditorApplicationCoordinatorError:
        _failure("Editor application coordinator failed.")
        return 7
    if type(result) is not EditorApplicationResultV1:
        _failure("Editor application coordinator failed.")
        return 7
    if result.status is EditorApplicationStatusV1.COMPLETED:
        print("Editor application completed.")
        return 0
    failure = result.failure
    if failure is None:
        _failure("Editor application coordinator failed.")
        return 7
    _failure(failure.safe_message)
    return int(result.exit_code)


def _load_scout_input(path: Path) -> ScoutEditorInputV1:
    try:
        loaded = load_contract(path)
        if type(loaded) is not ScoutEditorInputV1:
            raise TypeError
        return ScoutEditorInputV1.model_validate(
            loaded.model_dump(mode="python", warnings=False), strict=True
        )
    except (AttributeError, ContractFileError, TypeError, ValueError):
        raise EditorApplicationConfigurationError()


def _confirm_configuration(configuration, provider, model, timeout_seconds) -> None:
    try:
        provider_choice = ProviderChoiceV1(provider)
        valid = (
            configuration.provider is provider_choice
            and type(model) is str
            and bool(model)
            and model == model.strip()
            and configuration.model_identifier == model
            and type(timeout_seconds) is float
            and configuration.timeout_seconds == timeout_seconds
        )
    except (AttributeError, TypeError, ValueError):
        valid = False
    if not valid:
        raise EditorApplicationConfigurationError()


def _absolute_path(path: Path) -> Path:
    if type(path) is not type(Path()):
        raise EditorApplicationConfigurationError()
    return path if path.is_absolute() else Path.cwd() / path


def _failure(message: str) -> None:
    import sys

    print(message, file=sys.stderr)


__all__ = ("run_editor_command",)
