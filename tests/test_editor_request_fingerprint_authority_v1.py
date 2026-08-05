from __future__ import annotations

import copy
import hashlib
import inspect
import json
import pickle
import subprocess
import sys
import traceback
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

import pastila_scout.editor_request_fingerprint_authority_v1 as public_api
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationApplicationRequestV1,
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_request_fingerprint_authority_v1 import (
    EditorRequestFingerprintAuthorityError,
    EditorRequestFingerprintAuthorityV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1


def _schema(value: dict[str, object] | None = None) -> tuple[str, str]:
    payload = value or {"properties": {"answer": {"type": "string"}}, "type": "object"}
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return encoded, hashlib.sha256(encoded.encode()).hexdigest()


def _options(**changes: object) -> EditorGenerationRuntimeOptionsV1:
    values = {
        "provider": ProviderChoiceV1.OPENAI,
        "model_identifier": "gpt-4.1-mini",
        "model_revision": None,
        "temperature": 0.3,
        "top_p": 1.0,
        "max_output_tokens": 500,
        "seed": None,
        "stop_sequences": (),
        "structured_output_mode": True,
        "timeout_policy": TimeoutPolicyV2(timeout_seconds=30.0),
    }
    values.update(changes)
    return EditorGenerationRuntimeOptionsV1(**values)


def _fields(**changes: object) -> dict[str, object]:
    schema_json, schema_hash = _schema()
    values: dict[str, object] = {
        "provider": ProviderChoiceV1.OPENAI,
        "prompt": "Write a concise answer.",
        "request_reference": "editor-operation-1-attempt-1",
        "requested_at": datetime(2026, 8, 5, 10, 11, 12, 345678, tzinfo=UTC),
        "options": _options(),
        "output_schema_name": "AnswerV1",
        "output_schema_canonical_json": schema_json,
        "output_schema_fingerprint": schema_hash,
        "cancellation": CancellationTokenV2(cancellation_requested=False),
    }
    values.update(changes)
    return values


def _fingerprint(**changes: object) -> str:
    return EditorRequestFingerprintAuthorityV1().fingerprint(**_fields(**changes))


def test_exact_public_surface_files_and_signatures() -> None:
    package = Path(public_api.__file__).parent
    assert sorted(path.name for path in package.iterdir() if path.is_file()) == [
        "__init__.py",
        "authority.py",
        "errors.py",
    ]
    assert public_api.__all__ == (
        "EditorRequestFingerprintAuthorityError",
        "EditorRequestFingerprintAuthorityV1",
    )
    assert list(inspect.signature(EditorRequestFingerprintAuthorityV1).parameters) == []
    assert list(
        inspect.signature(EditorRequestFingerprintAuthorityV1.fingerprint).parameters
    ) == [
        "self",
        "provider",
        "prompt",
        "request_reference",
        "requested_at",
        "options",
        "output_schema_name",
        "output_schema_canonical_json",
        "output_schema_fingerprint",
        "cancellation",
    ]
    assert list(
        inspect.signature(EditorRequestFingerprintAuthorityV1.reconstruct).parameters
    ) == [
        "self",
        "fingerprint",
        "provider",
        "prompt",
        "request_reference",
        "requested_at",
        "options",
        "output_schema_name",
        "output_schema_canonical_json",
        "output_schema_fingerprint",
        "cancellation",
    ]


def test_fingerprint_has_byte_parity_with_frozen_request() -> None:
    fields = _fields()
    fingerprint = EditorRequestFingerprintAuthorityV1().fingerprint(**fields)
    request = EditorGenerationApplicationRequestV1(
        **fields, request_fingerprint=fingerprint
    )
    assert request.request_fingerprint == fingerprint
    assert len(fingerprint) == 64
    assert fingerprint == fingerprint.lower()


def test_reconstruction_is_deterministic_and_rejects_foreign_forms() -> None:
    fields = _fields()
    authority = EditorRequestFingerprintAuthorityV1()
    fingerprint = authority.fingerprint(**fields)
    assert authority.fingerprint(**fields) == fingerprint
    assert authority.reconstruct(fingerprint, **fields) == fingerprint
    for invalid in (
        fingerprint.upper(),
        f"sha256:{fingerprint}",
        "0" * 64,
        fingerprint[:-1],
        str.__new__(type("ForeignString", (str,), {}), fingerprint),
    ):
        with pytest.raises(EditorRequestFingerprintAuthorityError):
            authority.reconstruct(invalid, **fields)


@pytest.mark.parametrize(
    "changes",
    [
        {"prompt": "Write another concise answer."},
        {"request_reference": "editor-operation-1-attempt-2"},
        {"requested_at": datetime(2026, 8, 5, 10, 11, 13, tzinfo=UTC)},
        {"options": _options(model_identifier="gpt-4.1")},
        {"output_schema_name": "OtherAnswerV1"},
        {"cancellation": CancellationTokenV2(cancellation_requested=True)},
    ],
)
def test_each_independently_variable_field_participates(
    changes: dict[str, object],
) -> None:
    assert _fingerprint(**changes) != _fingerprint()


def test_provider_and_coherent_schema_changes_participate() -> None:
    ollama_options = _options(
        provider=ProviderChoiceV1.OLLAMA, model_identifier="qwen3:14b"
    )
    assert (
        _fingerprint(provider=ProviderChoiceV1.OLLAMA, options=ollama_options)
        != _fingerprint()
    )
    schema_json, schema_hash = _schema({"type": "object", "required": ["answer"]})
    assert (
        _fingerprint(
            output_schema_canonical_json=schema_json,
            output_schema_fingerprint=schema_hash,
        )
        != _fingerprint()
    )


def test_unicode_datetime_and_numeric_canonical_semantics() -> None:
    composed = "Scrie în română: țară"
    decomposed = "Scrie i\u0302n roma\u0302na\u0306: t\u0326ara\u0306"
    assert _fingerprint(prompt=composed) == _fingerprint(prompt=decomposed)
    requested = datetime(2026, 8, 5, 12, tzinfo=timezone(timedelta(hours=2)))
    assert _fingerprint(requested_at=requested) == _fingerprint(
        requested_at=datetime(2026, 8, 5, 10, tzinfo=UTC)
    )
    assert _fingerprint(options=_options(temperature=1)) != _fingerprint(
        options=_options(temperature=1.0)
    )
    assert _fingerprint(options=_options(top_p=1)) != _fingerprint(
        options=_options(top_p=1.0)
    )
    assert (
        _fingerprint(
            options=_options(timeout_policy=TimeoutPolicyV2(timeout_seconds=30))
        )
        != _fingerprint()
    )


def test_invalid_and_copied_invalid_inputs_map_to_one_safe_error() -> None:
    authority = EditorRequestFingerprintAuthorityV1()
    invalid_options = _options()
    object.__setattr__(invalid_options, "temperature", float("nan"))
    invalid_cancellation = CancellationTokenV2(cancellation_requested=False)
    object.__setattr__(invalid_cancellation, "cancellation_requested", "secret")
    cases = [
        {"options": invalid_options},
        {"cancellation": invalid_cancellation},
        {"prompt": " prompt-with-secret "},
        {"requested_at": datetime(2026, 8, 5)},  # noqa: DTZ001 - invalid input
        {"output_schema_canonical_json": "{not-json}"},
    ]
    for changes in cases:
        with pytest.raises(EditorRequestFingerprintAuthorityError) as caught:
            authority.fingerprint(**_fields(**changes))
        assert str(caught.value) == "Editor request fingerprint authority is invalid."
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is None
        rendered = "".join(traceback.format_tb(caught.value.__traceback__))
        assert "prompt-with-secret" not in rendered
        assert "{not-json}" not in rendered


def test_authority_object_is_inert_safe_and_stateless() -> None:
    authority = EditorRequestFingerprintAuthorityV1()
    assert repr(authority) == "EditorRequestFingerprintAuthorityV1()"
    assert not hasattr(authority, "__dict__")
    assert authority == EditorRequestFingerprintAuthorityV1()
    assert copy.copy(authority) is authority
    assert copy.deepcopy(authority) is authority
    with pytest.raises(TypeError, match="does not support pickle"):
        pickle.dumps(authority)


def test_cross_process_fingerprint_and_passive_import() -> None:
    script = """
from datetime import UTC, datetime
from pastila_scout.editor_request_fingerprint_authority_v1 import EditorRequestFingerprintAuthorityV1
from pastila_scout.editor_generation_authority_v1 import EditorGenerationRuntimeOptionsV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
import hashlib, json
s=json.dumps({'type':'object'},sort_keys=True,separators=(',',':'))
o=EditorGenerationRuntimeOptionsV1(ProviderChoiceV1.OPENAI,'gpt-4.1-mini',None,0.3,1.0,500,None,(),True,TimeoutPolicyV2(timeout_seconds=30.0))
print(EditorRequestFingerprintAuthorityV1().fingerprint(provider=ProviderChoiceV1.OPENAI,prompt='Prompt',request_reference='ref-1',requested_at=datetime(2026,8,5,tzinfo=UTC),options=o,output_schema_name='AnswerV1',output_schema_canonical_json=s,output_schema_fingerprint=hashlib.sha256(s.encode()).hexdigest(),cancellation=CancellationTokenV2(cancellation_requested=False)))
"""
    first = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    second = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    assert len(first.stdout.strip()) == 64


def test_forbidden_dependency_direction() -> None:
    source = inspect.getsource(
        sys.modules["pastila_scout.editor_request_fingerprint_authority_v1.authority"]
    )
    for forbidden in (
        "editor_generation_authority_v1.canonical",
        "scout_runtime",
        "scout_workflow",
        "provider_execution_openai",
        "provider_execution_ollama",
        "controlled_generator",
    ):
        assert forbidden not in source
