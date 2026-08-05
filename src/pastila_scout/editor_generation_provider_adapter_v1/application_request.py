"""Package-private construction of frozen Editor application requests."""

from __future__ import annotations

import copy
import hmac
from dataclasses import dataclass
from datetime import datetime
from typing import NoReturn

from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationApplicationRequestV1,
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_request_fingerprint_authority_v1 import (
    EditorRequestFingerprintAuthorityV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .errors import EditorGenerationProviderAdapterError

_SAFE = "Editor generation provider adapter failed."


def _raise_invalid() -> NoReturn:
    error = EditorGenerationProviderAdapterError(_SAFE)
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _EditorGenerationApplicationRequestBuilderV1:
    _authority: EditorRequestFingerprintAuthorityV1

    def __init__(
        self, fingerprint_authority: EditorRequestFingerprintAuthorityV1
    ) -> None:
        if type(fingerprint_authority) is not EditorRequestFingerprintAuthorityV1:
            del self, fingerprint_authority
            _raise_invalid()
        object.__setattr__(self, "_authority", fingerprint_authority)

    def build(
        self,
        *,
        provider: ProviderChoiceV1,
        prompt: str,
        request_reference: str,
        requested_at: datetime,
        options: EditorGenerationRuntimeOptionsV1,
        output_schema_name: str,
        output_schema_canonical_json: str,
        output_schema_fingerprint: str,
        cancellation: CancellationTokenV2,
    ) -> EditorGenerationApplicationRequestV1:
        result = _build(
            self,
            provider,
            prompt,
            request_reference,
            requested_at,
            options,
            output_schema_name,
            output_schema_canonical_json,
            output_schema_fingerprint,
            cancellation,
        )
        del self, provider, prompt, request_reference, requested_at, options
        del output_schema_name, output_schema_canonical_json
        del output_schema_fingerprint, cancellation
        if result is None:
            del result
            _raise_invalid()
        return result

    def __repr__(self) -> str:
        _authority(self)
        return "_EditorGenerationApplicationRequestBuilderV1(<fingerprint authority>)"

    def __copy__(self) -> _EditorGenerationApplicationRequestBuilderV1:
        return type(self)(_authority(self))

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> _EditorGenerationApplicationRequestBuilderV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError(
            "_EditorGenerationApplicationRequestBuilderV1 does not support pickle"
        )


def _authority(value: object) -> EditorRequestFingerprintAuthorityV1:
    try:
        if type(value) is not _EditorGenerationApplicationRequestBuilderV1:
            raise TypeError
        authority = object.__getattribute__(value, "_authority")
        if type(authority) is not EditorRequestFingerprintAuthorityV1:
            raise TypeError
        return authority
    except Exception:  # noqa: BLE001
        _raise_invalid()


def _build(
    builder: object, *values: object
) -> EditorGenerationApplicationRequestV1 | None:
    try:
        authority = _authority(builder)
        names = (
            "provider",
            "prompt",
            "request_reference",
            "requested_at",
            "options",
            "output_schema_name",
            "output_schema_canonical_json",
            "output_schema_fingerprint",
            "cancellation",
        )
        semantics = dict(zip(names, values, strict=True))
        fingerprint = authority.fingerprint(**semantics)
        request = EditorGenerationApplicationRequestV1(*values, fingerprint)
        rebuilt = copy.copy(request)
        if type(rebuilt) is not EditorGenerationApplicationRequestV1:
            return None
        if any(
            type(object.__getattribute__(rebuilt, name)) is not type(expected)
            or object.__getattribute__(rebuilt, name) != expected
            for name, expected in semantics.items()
        ):
            return None
        retained = object.__getattribute__(rebuilt, "request_fingerprint")
        if type(retained) is not str or not hmac.compare_digest(retained, fingerprint):
            return None
        return rebuilt
    except Exception:  # noqa: BLE001
        return None


__all__: tuple[str, ...] = ()
