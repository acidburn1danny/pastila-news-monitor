"""Application-owned configuration authorities for the Editor."""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

from pydantic import BaseModel

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.io import load_contract
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.generation.models import LanguageGenerationConfig
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.provider_execution_v2 import TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .errors import raise_configuration_error
from .models import (
    EditorApplicationGenerationConfigurationV1,
    reconstruct_generation_configuration,
)

_MAX_CONFIGURATION_BYTES = 1024 * 1024
_PATH_TYPE = type(Path())
_CONFIGURATION_FIELDS = (
    "contract_version",
    "provider",
    "model_identifier",
    "model_revision",
    "temperature",
    "top_p",
    "max_output_tokens",
    "seed",
    "structured_output_mode",
    "timeout_seconds",
)


def _reconstruct_model[ModelT: BaseModel](model: type[ModelT], value: object) -> ModelT:
    if type(value) is not model:
        raise TypeError
    rebuilt = model.model_validate(
        value.model_dump(mode="python", warnings=False), strict=True
    )
    if not _all_strings_nfc(rebuilt.model_dump(mode="python", warnings=False)):
        raise TypeError
    return rebuilt


def _all_strings_nfc(value: object) -> bool:
    if type(value) is str:
        return unicodedata.is_normalized("NFC", value)
    if type(value) in {int, float, bool} or value is None:
        return True
    if type(value) in {tuple, list, set, frozenset}:
        return all(_all_strings_nfc(item) for item in value)
    if type(value) is dict:
        return all(
            _all_strings_nfc(key) and _all_strings_nfc(item)
            for key, item in value.items()
        )
    return True


class _StatelessAuthority:
    __slots__ = ()

    def __init_subclass__(cls, **kwargs) -> None:
        del kwargs
        if cls.__module__ != __name__:
            raise TypeError("Editor application authorities cannot be subclassed")

    def __repr__(self) -> str:
        if type(self).__module__ != __name__:
            raise_configuration_error()
        return f"{type(self).__name__}()"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self)

    def __copy__(self):
        return type(self)()

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return type(self)()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        name = type(self).__name__
        del self, protocol
        raise TypeError(f"{name} does not support pickle")


class EditorSelectionProfileAuthorityV1(_StatelessAuthority):
    __slots__ = ()

    def load(self, *, path: Path) -> SelectionProfileV1:
        loaded = None
        try:
            loaded = load_contract(path)
            return _reconstruct_model(SelectionProfileV1, loaded)
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, path, loaded
            raise_configuration_error()

    def reconstruct(self, *, profile: SelectionProfileV1) -> SelectionProfileV1:
        rebuilt = None
        try:
            rebuilt = _reconstruct_model(SelectionProfileV1, profile)
            return rebuilt
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, profile, rebuilt
            raise_configuration_error()


class EditorEpisodeContextAuthorityV1(_StatelessAuthority):
    __slots__ = ()

    def load(self, *, path: Path) -> EpisodeContextV1:
        loaded = None
        try:
            loaded = load_contract(path)
            return _reconstruct_model(EpisodeContextV1, loaded)
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, path, loaded
            raise_configuration_error()

    def reconstruct(self, *, context: EpisodeContextV1) -> EpisodeContextV1:
        rebuilt = None
        try:
            rebuilt = _reconstruct_model(EpisodeContextV1, context)
            return rebuilt
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, context, rebuilt
            raise_configuration_error()


@dataclass(frozen=True, slots=True, repr=False)
class _MaterializedGenerationConfigurationV1:
    generation_configuration: LanguageGenerationConfig
    runtime_options: EditorGenerationRuntimeOptionsV1


class EditorApplicationGenerationConfigurationAuthorityV1(_StatelessAuthority):
    __slots__ = ()

    def load(self, *, path: Path) -> EditorApplicationGenerationConfigurationV1:
        data = provider_text = provider = values = None
        try:
            data = _load_configuration_json(path)
            provider_text = data["provider"]
            if type(provider_text) is not str:
                raise TypeError
            provider = ProviderChoiceV1(provider_text)
            values = tuple(
                provider if name == "provider" else data[name]
                for name in _CONFIGURATION_FIELDS
            )
            return EditorApplicationGenerationConfigurationV1(*values)
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, path, data, provider_text, provider, values
            raise_configuration_error()

    def reconstruct(
        self, *, configuration: EditorApplicationGenerationConfigurationV1
    ) -> EditorApplicationGenerationConfigurationV1:
        rebuilt = None
        try:
            rebuilt = reconstruct_generation_configuration(configuration)
            return rebuilt
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, configuration, rebuilt
            raise_configuration_error()

    def _materialize(
        self, *, configuration: EditorApplicationGenerationConfigurationV1
    ) -> _MaterializedGenerationConfigurationV1:
        valid = timeout = generation = options = None
        try:
            valid = reconstruct_generation_configuration(configuration)
            timeout = TimeoutPolicyV2(timeout_seconds=valid.timeout_seconds)
            generation = LanguageGenerationConfig(
                provider=valid.provider.value,
                model_identifier=valid.model_identifier,
                model_revision=valid.model_revision,
                temperature=valid.temperature,
                top_p=valid.top_p,
                max_output_tokens=valid.max_output_tokens,
                seed=valid.seed,
                structured_output_mode=valid.structured_output_mode,
                timeout_seconds=valid.timeout_seconds,
            )
            options = EditorGenerationRuntimeOptionsV1(
                valid.provider,
                valid.model_identifier,
                valid.model_revision,
                valid.temperature,
                valid.top_p,
                valid.max_output_tokens,
                valid.seed,
                (),
                valid.structured_output_mode,
                timeout,
            )
            _require_lower_parity(valid, generation, options)
            return _MaterializedGenerationConfigurationV1(generation, options)
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, configuration, valid, timeout, generation, options
            raise_configuration_error()


def _require_lower_parity(
    source: EditorApplicationGenerationConfigurationV1,
    generation: LanguageGenerationConfig,
    options: EditorGenerationRuntimeOptionsV1,
) -> None:
    if not (
        generation.provider == source.provider.value
        and options.provider is source.provider
        and generation.model_identifier
        == options.model_identifier
        == source.model_identifier
        and generation.model_revision == options.model_revision == source.model_revision
        and type(generation.temperature) is float
        and type(options.temperature) is float
        and generation.temperature == options.temperature == source.temperature
        and type(generation.top_p) is float
        and type(options.top_p) is float
        and generation.top_p == options.top_p == source.top_p == 1.0
        and generation.max_output_tokens
        == options.max_output_tokens
        == source.max_output_tokens
        and generation.seed is options.seed is source.seed is None
        and generation.structured_output_mode
        is options.structured_output_mode
        is source.structured_output_mode
        is True
        and type(generation.timeout_seconds) is float
        and type(options.timeout_policy.timeout_seconds) is float
        and generation.timeout_seconds
        == options.timeout_policy.timeout_seconds
        == source.timeout_seconds
        and options.stop_sequences == ()
    ):
        raise TypeError


def _load_configuration_json(path: object) -> dict[str, object]:
    if type(path) is not _PATH_TYPE:
        raise TypeError
    raw = str(path)
    lowered = raw.lower()
    if (
        "://" in raw
        or lowered.startswith(("http:", "https:", "ftp:", "file:"))
        or raw.startswith(("\\\\", "//"))
    ):
        raise TypeError
    if path.is_symlink():
        raise TypeError
    resolved = path.resolve(strict=False)
    reserved = {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
    reserved.update(
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    )
    if any(part.split(".", 1)[0].upper() in reserved for part in resolved.parts):
        raise TypeError
    if not resolved.is_file() or resolved.is_symlink():
        raise TypeError
    if resolved.stat().st_size > _MAX_CONFIGURATION_BYTES:
        raise TypeError
    text = resolved.read_text(encoding="utf-8")
    data = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_nonfinite,
    )
    if type(data) is not dict or tuple(data) != _CONFIGURATION_FIELDS:
        raise TypeError
    if set(data) != set(_CONFIGURATION_FIELDS):
        raise TypeError
    return data


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TypeError
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> NoReturn:
    del value
    raise TypeError


__all__ = (
    "EditorApplicationGenerationConfigurationAuthorityV1",
    "EditorEpisodeContextAuthorityV1",
    "EditorSelectionProfileAuthorityV1",
)
