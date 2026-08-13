from __future__ import annotations

import builtins
import copy
import hashlib
import inspect
import json
import os
import pickle
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest
from test_editor_operational_execution_v1 import (
    controlled_output,
    execute_fake,
    observation,
)

import pastila_scout.editor_application_v1 as public
import pastila_scout.editor_application_v1.serialization as implementation
from pastila_scout.editor.generation.controlled_generator import (
    ControlledGenerationError,
)
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalGenerationStatusV1,
    EditorOperationalResultV1,
)
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2

EXPECTED_API = (
    "EditorApplicationConfigurationError",
    "EditorApplicationCoordinatorError",
    "EditorApplicationExitCodeV1",
    "EditorApplicationExportError",
    "EditorApplicationFailureCodeV1",
    "EditorApplicationFailureV1",
    "EditorApplicationGenerationConfigurationV1",
    "EditorApplicationGenerationConfigurationAuthorityV1",
    "EditorApplicationLifecycleStateV1",
    "EditorApplicationRequestV1",
    "EditorApplicationResultV1",
    "EditorApplicationSerializationError",
    "EditorApplicationStatusV1",
    "EditorEpisodeContextAuthorityV1",
    "EditorOperationalResultSerializerV1",
    "EditorOutputDestinationV1",
    "EditorOverwritePolicyV1",
    "EditorSelectionProfileAuthorityV1",
)
RESULT_FIELDS = {
    "source_report_id",
    "source_report_fingerprint",
    "preparation_result_fingerprint",
    "execution_request_reference",
    "execution_request_fingerprint",
    "status",
    "lifecycle",
    "draft",
    "generation_trace",
    "generation_manifest",
    "final_state_revision",
    "attempts",
    "attempt_count",
    "timeout_retry_count",
    "failure",
    "cleanup_failed",
    "result_fingerprint",
}


def completed_result(monkeypatch: pytest.MonkeyPatch) -> EditorOperationalResultV1:
    result, *_ = execute_fake(
        monkeypatch,
        (observation(1, "a", ExecutionOutcomeV2.COMPLETED),),
        output=controlled_output(),
    )
    assert result.status is EditorOperationalGenerationStatusV1.COMPLETED
    return result


def failed_result(monkeypatch: pytest.MonkeyPatch) -> EditorOperationalResultV1:
    result, *_ = execute_fake(
        monkeypatch,
        (observation(1, "a", ExecutionOutcomeV2.PROVIDER_FAILURE),),
        failure=ControlledGenerationError("private provider detail"),
    )
    return result


def decode(payload: bytes) -> dict[str, object]:
    assert payload.endswith(b"\n")
    return json.loads(payload[:-1].decode("utf-8"))


def test_exact_api_layout_signature_and_passive_serializer() -> None:
    root = Path(__file__).resolve().parents[1]
    exporter_name = "EditorAtomicExporterV1"
    coordinator_name = "EditorApplicationCoordinatorV1"
    coordinator_exists = (
        root / "src/pastila_scout/editor_application_v1/application.py"
    ).is_file()
    exporter_exists = (
        root / "src/pastila_scout/editor_application_v1/export.py"
    ).is_file()
    expected_current_api = (
        *EXPECTED_API[:2],
        *((coordinator_name,) if coordinator_exists else ()),
        *EXPECTED_API[2:13],
        *((exporter_name,) if exporter_exists else ()),
        *EXPECTED_API[13:15],
        "EditorSerializedOperationalResultV1",
        "load_editor_operational_result_v1",
        *EXPECTED_API[15:],
    )
    assert public.__all__ == expected_current_api
    assert coordinator_exists == hasattr(public, coordinator_name)
    if coordinator_exists:
        assert public.__all__[2] == coordinator_name
    if exporter_exists:
        assert getattr(public, exporter_name).__module__ == (
            "pastila_scout.editor_application_v1.export"
        )
    else:
        assert not hasattr(public, exporter_name)
    assert (
        public.EditorOperationalResultSerializerV1
        is implementation.EditorOperationalResultSerializerV1
    )
    serializer = public.EditorOperationalResultSerializerV1()
    assert not hasattr(serializer, "__dict__")
    assert repr(serializer) == "EditorOperationalResultSerializerV1()"
    assert copy.copy(serializer) == serializer
    assert copy.copy(serializer) is not serializer
    assert copy.deepcopy(serializer) == serializer
    with pytest.raises(TypeError):
        pickle.dumps(serializer)
    with pytest.raises(TypeError):
        type("ForgedSerializer", (type(serializer),), {})
    signature = inspect.signature(serializer.serialize)
    assert tuple(signature.parameters) == ("result",)
    assert signature.parameters["result"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.return_annotation in {
        public.EditorSerializedOperationalResultV1,
        "EditorSerializedOperationalResultV1",
    }


def test_completed_result_serializes_all_fields_and_exact_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = completed_result(monkeypatch)
    serialized = public.EditorOperationalResultSerializerV1().serialize(result=result)
    payload = serialized.payload
    envelope = decode(payload)
    assert set(envelope) == {
        "schema_name",
        "schema_version",
        "operation_reference",
        "source_lineage",
        "operational_result",
        "payload_sha256",
    }
    assert envelope["schema_name"] == "pastila-editor-operational-export"
    assert envelope["schema_version"] == "1"
    assert envelope["operation_reference"] == result.execution_request_reference
    lineage = envelope["source_lineage"]
    assert lineage == {
        "source_report_id": result.source_report_id,
        "source_report_fingerprint": result.source_report_fingerprint,
        "preparation_result_fingerprint": result.preparation_result_fingerprint,
        "execution_request_reference": result.execution_request_reference,
        "execution_request_fingerprint": result.execution_request_fingerprint,
    }
    projected = envelope["operational_result"]
    assert set(projected) == RESULT_FIELDS
    assert projected["execution_request_fingerprint"] == (
        result.execution_request_fingerprint
    )
    assert projected["status"] == "completed"
    assert projected["failure"] is None
    assert projected["cleanup_failed"] is False


def test_canonical_json_terminal_lf_and_embedded_checksum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = completed_result(monkeypatch)
    serializer = public.EditorOperationalResultSerializerV1()
    first_result = serializer.serialize(result=result)
    second_result = serializer.serialize(result=result)
    first = first_result.payload
    second = second_result.payload
    assert first == second
    assert first_result.payload_sha256 == second_result.payload_sha256
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert b"\r\n" not in first and not first.startswith(b"\xef\xbb\xbf")
    envelope = decode(first)
    checksum = envelope["payload_sha256"]
    assert first_result.payload_sha256 == checksum
    assert isinstance(checksum, str)
    assert checksum.startswith("sha256:") and len(checksum) == 71
    assert checksum[7:] == checksum[7:].lower()
    envelope["payload_sha256"] = ""
    blank = (
        json.dumps(
            envelope,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    assert checksum == f"sha256:{hashlib.sha256(blank).hexdigest()}"
    assert first[:-1] == json.dumps(
        decode(first),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert f"sha256:{hashlib.sha256(first).hexdigest()}" != checksum


def test_serialized_result_object_contract_and_reconstruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    serialized = public.EditorOperationalResultSerializerV1().serialize(
        result=completed_result(monkeypatch)
    )
    assert not hasattr(serialized, "__dict__")
    assert tuple(type(serialized).__slots__) == ("payload", "payload_sha256")
    assert repr(serialized) == (
        "EditorSerializedOperationalResultV1("
        "payload=<redacted>, payload_sha256=<redacted>)"
    )
    copied = copy.copy(serialized)
    deep = copy.deepcopy(serialized)
    assert copied == deep == serialized
    assert copied is not serialized and deep is not serialized
    with pytest.raises(TypeError, match="does not support pickle"):
        pickle.dumps(serialized)
    with pytest.raises(TypeError, match="cannot be subclassed"):
        type("ForgedSerializedResult", (type(serialized),), {})
    with pytest.raises((AttributeError, TypeError)):
        serialized.payload = b"changed\n"  # type: ignore[misc]


def test_wrapper_construction_rejects_invalid_payload_and_checksum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    serialized = public.EditorOperationalResultSerializerV1().serialize(
        result=completed_result(monkeypatch)
    )
    cases = (
        (bytearray(serialized.payload), serialized.payload_sha256),
        (serialized.payload, serialized.payload_sha256.upper()),
        (serialized.payload[:-1], serialized.payload_sha256),
        (serialized.payload + b"\n", serialized.payload_sha256),
        (b"\xef\xbb\xbf" + serialized.payload, serialized.payload_sha256),
        (
            serialized.payload.replace(
                b'"schema_version":"1"', b'"schema_version":"2"'
            ),
            serialized.payload_sha256,
        ),
        (serialized.payload, "sha256:" + "0" * 64),
    )
    for payload, checksum in cases:
        with pytest.raises(public.EditorApplicationSerializationError) as caught:
            public.EditorSerializedOperationalResultV1(payload, checksum)
        assert caught.value.__cause__ is caught.value.__context__ is None


def test_wrapper_rejects_resigned_invalid_operational_semantics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    serialized = public.EditorOperationalResultSerializerV1().serialize(
        result=completed_result(monkeypatch)
    )
    envelope = decode(serialized.payload)
    envelope["operational_result"]["status"] = "failed"
    envelope["payload_sha256"] = ""
    placeholder = implementation._encode(envelope)
    checksum = f"sha256:{hashlib.sha256(placeholder).hexdigest()}"
    envelope["payload_sha256"] = checksum
    forged = implementation._encode(envelope)
    with pytest.raises(public.EditorApplicationSerializationError):
        public.EditorSerializedOperationalResultV1(forged, checksum)


@pytest.mark.parametrize(
    "payload",
    [
        b"{\n",
        b"[]\n",
        b'{"a":1,"a":1}\n',
        b'{"e\\u0301":1,"\\u00e9":1}\n',
        b'{"schema_name":"pastila-editor-operational-export"} trailing\n',
    ],
)
def test_wrapper_rejects_malformed_nonobject_duplicate_and_noncanonical_json(
    payload: bytes,
) -> None:
    with pytest.raises(public.EditorApplicationSerializationError) as caught:
        public.EditorSerializedOperationalResultV1(payload, "sha256:" + "0" * 64)
    assert str(caught.value) == "Editor operational result serialization failed."
    assert caught.value.__cause__ is caught.value.__context__ is None


def test_copied_invalid_wrapper_operations_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    serialized = public.EditorOperationalResultSerializerV1().serialize(
        result=completed_result(monkeypatch)
    )
    valid_peer = copy.copy(serialized)
    object.__setattr__(serialized, "payload_sha256", "sha256:" + "0" * 64)
    operations = (
        lambda: copy.copy(serialized),
        lambda: copy.deepcopy(serialized),
        lambda: repr(serialized),
        lambda: serialized == valid_peer,
    )
    for operation in operations:
        with pytest.raises(public.EditorApplicationSerializationError):
            operation()


def test_later_wrapper_reconstruction_performs_one_validation_checksum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    serialized = public.EditorOperationalResultSerializerV1().serialize(
        result=completed_result(monkeypatch)
    )
    original = implementation.hashlib.sha256
    count = 0

    def counted(value=b""):
        nonlocal count
        count += 1
        return original(value)

    monkeypatch.setattr(implementation.hashlib, "sha256", counted)
    copied = copy.copy(serialized)
    assert copied.payload == serialized.payload
    assert copied.payload_sha256 == serialized.payload_sha256
    assert count == 1


def test_no_legacy_serialization_entry_point() -> None:
    serializer = public.EditorOperationalResultSerializerV1()
    assert not hasattr(serializer, "serialize_bytes")
    assert not hasattr(serializer, "extract_checksum")


@pytest.mark.parametrize("bad", [None, object(), b"payload", "result"])
def test_invalid_exact_input_reduces_to_fixed_public_error(bad: object) -> None:
    with pytest.raises(public.EditorApplicationSerializationError) as caught:
        public.EditorOperationalResultSerializerV1().serialize(result=bad)
    assert str(caught.value) == "Editor operational result serialization failed."
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.__suppress_context__ is True


def test_failed_cancelled_timeout_and_cleanup_results_are_ineligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    results = [failed_result(monkeypatch)]
    for attempts in (
        (observation(1, "a", ExecutionOutcomeV2.CANCELLED),),
        (
            observation(1, "a", ExecutionOutcomeV2.TIMEOUT),
            observation(2, "a", ExecutionOutcomeV2.TIMEOUT),
        ),
    ):
        result, *_ = execute_fake(
            monkeypatch,
            attempts,
            failure=ControlledGenerationError("private lower detail"),
        )
        results.append(result)
    cleanup, *_ = execute_fake(
        monkeypatch,
        (observation(1, "a", ExecutionOutcomeV2.COMPLETED),),
        output=controlled_output(),
        close_fails=True,
    )
    results.append(cleanup)
    for result in results:
        with pytest.raises(public.EditorApplicationSerializationError):
            public.EditorOperationalResultSerializerV1().serialize(result=result)


def test_copied_invalid_and_subclass_results_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = completed_result(monkeypatch)
    object.__setattr__(result, "cleanup_failed", True)
    with pytest.raises(public.EditorApplicationSerializationError):
        public.EditorOperationalResultSerializerV1().serialize(result=result)

    class ForgedResult(EditorOperationalResultV1):
        pass

    forged = object.__new__(ForgedResult)
    with pytest.raises(public.EditorApplicationSerializationError):
        public.EditorOperationalResultSerializerV1().serialize(result=forged)


def test_serialization_performs_no_filesystem_io(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = completed_result(monkeypatch)

    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("filesystem access is forbidden")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "write_bytes", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    payload = (
        public.EditorOperationalResultSerializerV1().serialize(result=result).payload
    )
    assert payload.endswith(b"\n")


def test_error_traceback_contains_no_protected_package_locals() -> None:
    protected = "protected-editorial-result-value"
    with pytest.raises(public.EditorApplicationSerializationError) as caught:
        public.EditorOperationalResultSerializerV1().serialize(result=protected)
    traceback = caught.value.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_globals.get("__name__") == (
            "pastila_scout.editor_application_v1.serialization"
        ):
            assert protected not in repr(traceback.tb_frame.f_locals)
        traceback = traceback.tb_next


def test_nontrivial_attempt_order_and_numeric_types_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result, *_ = execute_fake(
        monkeypatch,
        (
            observation(1, "a", ExecutionOutcomeV2.TIMEOUT),
            observation(2, "a", ExecutionOutcomeV2.COMPLETED),
        ),
        output=controlled_output(),
    )
    projected = decode(
        public.EditorOperationalResultSerializerV1().serialize(result=result).payload
    )["operational_result"]
    assert [item["attempt_number"] for item in projected["attempts"]] == [1, 2]
    assert [item["outcome"] for item in projected["attempts"]] == [
        "timeout",
        "completed",
    ]
    assert type(projected["attempt_count"]) is int
    assert type(projected["cleanup_failed"]) is bool
    assert projected["timeout_retry_count"] == 1


def test_one_result_reconstruction_and_exact_two_checksums(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = completed_result(monkeypatch)
    original_copy = implementation.copy.copy
    original_sha256 = implementation.hashlib.sha256
    original_encode = implementation._encode
    counts = {"result_copy": 0, "encode": 0, "sha256": 0}

    def counted_copy(value):
        if type(value) is EditorOperationalResultV1:
            counts["result_copy"] += 1
        return original_copy(value)

    def counted_sha256(value=b""):
        counts["sha256"] += 1
        return original_sha256(value)

    def counted_encode(value):
        counts["encode"] += 1
        return original_encode(value)

    monkeypatch.setattr(implementation.copy, "copy", counted_copy)
    monkeypatch.setattr(implementation.hashlib, "sha256", counted_sha256)
    monkeypatch.setattr(implementation, "_encode", counted_encode)
    public.EditorOperationalResultSerializerV1().serialize(result=result)
    assert counts == {"result_copy": 1, "encode": 4, "sha256": 2}


def test_ineligible_input_suppresses_projection_and_checksum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = failed_result(monkeypatch)

    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("later serializer stage must remain suppressed")

    monkeypatch.setattr(implementation, "_envelope", forbidden)
    monkeypatch.setattr(implementation.hashlib, "sha256", forbidden)
    with pytest.raises(public.EditorApplicationSerializationError):
        public.EditorOperationalResultSerializerV1().serialize(result=result)


@pytest.mark.parametrize("stage", ["_envelope", "_encode"])
def test_package_owned_failure_stages_reduce_to_fixed_error(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    result = completed_result(monkeypatch)

    def corrupted(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("protected package corruption detail")

    monkeypatch.setattr(implementation, stage, corrupted)
    with pytest.raises(public.EditorApplicationSerializationError) as caught:
        public.EditorOperationalResultSerializerV1().serialize(result=result)
    assert str(caught.value) == "Editor operational result serialization failed."
    assert caught.value.__cause__ is caught.value.__context__ is None


def test_production_checksum_failure_suppresses_wrapper_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = completed_result(monkeypatch)
    wrapper_calls = 0

    def broken_sha256(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("protected checksum detail")

    class ForbiddenWrapper:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs
            nonlocal wrapper_calls
            wrapper_calls += 1

    monkeypatch.setattr(implementation.hashlib, "sha256", broken_sha256)
    monkeypatch.setattr(
        implementation, "EditorSerializedOperationalResultV1", ForbiddenWrapper
    )
    with pytest.raises(public.EditorApplicationSerializationError):
        public.EditorOperationalResultSerializerV1().serialize(result=result)
    assert wrapper_calls == 0


def test_final_encoding_and_wrapper_validation_are_distinct_fail_closed_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = completed_result(monkeypatch)
    original_encode = implementation._encode
    encode_calls = 0

    def fail_second_encode(value):
        nonlocal encode_calls
        encode_calls += 1
        if encode_calls == 2:
            raise RuntimeError("protected final encoding detail")
        return original_encode(value)

    monkeypatch.setattr(implementation, "_encode", fail_second_encode)
    with pytest.raises(public.EditorApplicationSerializationError):
        public.EditorOperationalResultSerializerV1().serialize(result=result)
    assert encode_calls == 2

    monkeypatch.setattr(implementation, "_encode", original_encode)

    def invalid_pair(*args, **kwargs):
        del args, kwargs
        raise TypeError("protected wrapper validation detail")

    monkeypatch.setattr(implementation, "_validated_serialized_pair", invalid_pair)
    with pytest.raises(public.EditorApplicationSerializationError) as caught:
        public.EditorOperationalResultSerializerV1().serialize(result=result)
    assert caught.value.__cause__ is caught.value.__context__ is None


def test_closed_projection_unicode_datetime_numeric_and_mapping_rules() -> None:
    assert implementation._value("e\u0301") == "é"
    assert implementation._value(datetime(2026, 1, 2, 3, 4, 5, 6, UTC)) == (
        "2026-01-02T03:04:05.000006Z"
    )
    offset = timezone(timedelta(hours=2))
    assert implementation._value(datetime(2026, 1, 2, 5, 4, 5, 6, offset)) == (
        "2026-01-02T03:04:05.000006Z"
    )
    projected = implementation._value({"z": (1, 1.0, True, None), "a": [0, -1, 0.5]})
    assert projected == {"z": [1, 1.0, True, None], "a": [0, -1, 0.5]}
    assert [type(item) for item in projected["z"][:3]] == [int, float, bool]

    invalid_values = (
        datetime(2026, 1, 2),  # noqa: DTZ001
        float("nan"),
        float("inf"),
        Decimal("1.0"),
        Fraction(1, 2),
        {1: "value"},
        {"e\u0301": 1, "é": 2},
        {1, 2},
        (item for item in (1, 2)),
    )
    for invalid in invalid_values:
        with pytest.raises(TypeError):
            implementation._value(invalid)


def test_unicode_escape_normalization_and_non_equivalence() -> None:
    composed = implementation._encode({"value": "é\n\u0001"})
    decomposed = implementation._encode(
        implementation._value({"value": "e\u0301\n\u0001"})
    )
    distinct = implementation._encode({"value": "è\n\u0001"})
    assert composed == decomposed
    assert composed != distinct
    assert "é" in composed.decode("utf-8")
    assert b"\\n\\u0001" in composed


def test_private_import_and_architectural_prohibition_audit() -> None:
    source = Path(implementation.__file__).read_text(encoding="utf-8")
    prohibited = (
        "request_fingerprint_authority",
        "execution_request_authority",
        "ProviderSelector",
        "OpenAI",
        "Ollama",
        "tempfile",
        "os.replace",
        "os.rename",
        "Path.write_",
        "EditorAtomicExporter",
        "EditorApplicationCoordinator",
    )
    assert not any(term in source for term in prohibited)
    assert implementation.__all__ == (
        "EditorOperationalResultSerializerV1",
        "EditorSerializedOperationalResultV1",
        "load_editor_operational_result_v1",
    )


def test_fresh_process_determinism() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = """
import socket, sys
sys.path.insert(0, 'tests')
socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network'))
from _pytest.monkeypatch import MonkeyPatch
from test_editor_operational_execution_v1 import controlled_output, execute_fake, observation
from pastila_scout.editor_application_v1 import EditorOperationalResultSerializerV1
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
m=MonkeyPatch()
r,*_=execute_fake(m,(observation(1,'a',ExecutionOutcomeV2.COMPLETED),),output=controlled_output())
p=EditorOperationalResultSerializerV1().serialize(result=r)
print(p.payload.hex(),p.payload_sha256)
m.undo()
"""
    outputs = []
    for seed in ("1", "8675309"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        completed = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        assert completed.stderr == ""
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]


def test_public_loader_is_one_narrow_serialization_extension() -> None:
    source = Path(implementation.__file__).read_text(encoding="utf-8")
    assert source.count("def load_editor_operational_result_v1(") == 1
    assert "EditorSerializedOperationalResultV1(payload, payload_sha256)" in source
    assert "_reconstruct_projected_operational" in source


def test_completed_artifact_public_loader_reconstructs_and_rejects_checksum(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    serialized = public.EditorOperationalResultSerializerV1().serialize(
        result=completed_result(monkeypatch)
    )
    path = tmp_path / "editor.json"
    path.write_bytes(serialized.payload)

    loaded = public.load_editor_operational_result_v1(
        path=path, payload_sha256=serialized.payload_sha256
    )

    assert loaded.status is EditorOperationalGenerationStatusV1.COMPLETED
    assert loaded.draft is not None
    with pytest.raises(public.EditorApplicationSerializationError):
        public.load_editor_operational_result_v1(
            path=path, payload_sha256="sha256:" + "0" * 64
        )
    path.write_bytes(
        serialized.payload.replace(b'"status":"completed"', b'"status":"failed"')
    )
    changed_checksum = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(public.EditorApplicationSerializationError):
        public.load_editor_operational_result_v1(
            path=path, payload_sha256=changed_checksum
        )
    with pytest.raises(public.EditorApplicationSerializationError):
        public.load_editor_operational_result_v1(
            path=tmp_path / "missing.json", payload_sha256=serialized.payload_sha256
        )
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(public.EditorApplicationSerializationError):
        public.load_editor_operational_result_v1(
            path=directory, payload_sha256=serialized.payload_sha256
        )
