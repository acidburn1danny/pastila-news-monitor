from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_durable_filesystem_sink_v1 import (
    DURABLE_FILESYSTEM_SINK_IDENTITY,
    MAX_ARTIFACT_BYTES,
    MAX_ARTIFACT_COUNT,
    SUPERVISOR_CANDIDATE_IDENTITY,
    DurableEvidenceRootBindingV1,
    create_durable_filesystem_sink_v1,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_durable_filesystem_sink_v1.py"
)
ARTIFACT = (
    ROOT
    / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-durable-filesystem-sink-v1.json"
)


def _binding(**changes):
    values = {
        "provider_request_id": "request-001",
        "source_context_identity": "1" * 64,
        "authority_receipt_identity": "2" * 64,
        "supervisor_candidate_identity": SUPERVISOR_CANDIDATE_IDENTITY,
    }
    values.update(changes)
    return DurableEvidenceRootBindingV1(**values)


def test_creates_new_bound_root_and_publishes_exact_receipt(tmp_path):
    sink = create_durable_filesystem_sink_v1(
        root=tmp_path / "evidence", binding=_binding()
    )
    raw = "Știință, țară — exact.\n".encode()
    receipt = sink.persist("result.json", raw)

    assert (sink.root / "result.json").read_bytes() == raw
    assert receipt.sink_identity == DURABLE_FILESYSTEM_SINK_IDENTITY
    assert receipt.sink_instance_identity == sink.sink_instance_identity
    assert receipt.byte_count == len(raw)
    assert receipt.sha256 == hashlib.sha256(raw).hexdigest()
    parsed = json.loads(receipt.canonical_receipt)
    identity = parsed.pop("receipt_identity")
    canonical = (
        json.dumps(parsed, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()
    assert identity == hashlib.sha256(canonical).hexdigest()
    assert not list(sink.root.glob(".pending-*"))


def test_rejects_existing_root_duplicate_and_preexisting_target(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        create_durable_filesystem_sink_v1(root=existing, binding=_binding())

    sink = create_durable_filesystem_sink_v1(root=tmp_path / "new", binding=_binding())
    sink.persist("one.json", b"first")
    with pytest.raises(FileExistsError):
        sink.persist("one.json", b"second")
    assert (sink.root / "one.json").read_bytes() == b"first"
    (sink.root / "raced.json").write_bytes(b"owner")
    with pytest.raises(FileExistsError):
        sink.persist("raced.json", b"replacement")
    assert (sink.root / "raced.json").read_bytes() == b"owner"


@pytest.mark.parametrize("label", ["", "../x", "a/b", "a\\b", ".hidden", "UPPER"])
def test_rejects_traversal_and_noncanonical_labels(tmp_path, label):
    sink = create_durable_filesystem_sink_v1(
        root=tmp_path / "evidence", binding=_binding()
    )
    with pytest.raises(ValueError):
        sink.persist(label, b"x")
    assert not list(sink.root.iterdir())


def test_binding_and_size_fail_closed(tmp_path):
    with pytest.raises(ValueError):
        create_durable_filesystem_sink_v1(
            root=tmp_path / "bad", binding=_binding(source_context_identity="stale")
        )
    with pytest.raises(ValueError):
        create_durable_filesystem_sink_v1(
            root=tmp_path / "bad2",
            binding=_binding(supervisor_candidate_identity="0" * 64),
        )
    sink = create_durable_filesystem_sink_v1(root=tmp_path / "good", binding=_binding())
    with pytest.raises(ValueError):
        sink.persist("large.bin", b"x" * (MAX_ARTIFACT_BYTES + 1))
    assert not list(sink.root.iterdir())


def test_exact_count_ceiling_is_enforced_without_extra_file(tmp_path):
    sink = create_durable_filesystem_sink_v1(
        root=tmp_path / "evidence", binding=_binding()
    )
    for index in range(MAX_ARTIFACT_COUNT):
        sink.persist(f"item-{index:03d}.bin", b"")
    with pytest.raises(ValueError):
        sink.persist("overflow.bin", b"")
    assert len(list(sink.root.iterdir())) == MAX_ARTIFACT_COUNT
    assert not (sink.root / "overflow.bin").exists()


def test_failed_publication_leaves_no_target_or_partial_file(tmp_path, monkeypatch):
    sink = create_durable_filesystem_sink_v1(
        root=tmp_path / "evidence", binding=_binding()
    )

    def fail_link(source, target):
        raise FileExistsError("synthetic race")

    monkeypatch.setattr(os, "link", fail_link)
    with pytest.raises(FileExistsError):
        sink.persist("result.json", b"never visible")
    assert not (sink.root / "result.json").exists()
    assert not list(sink.root.glob(".pending-*"))


def test_symlink_target_is_rejected_when_supported(tmp_path):
    sink = create_durable_filesystem_sink_v1(
        root=tmp_path / "evidence", binding=_binding()
    )
    outside = tmp_path / "outside"
    outside.write_bytes(b"preserve")
    target = sink.root / "linked.json"
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(FileExistsError):
        sink.persist("linked.json", b"replacement")
    assert outside.read_bytes() == b"preserve"


def test_artifact_identity_and_no_execution_surface():
    artifact = json.loads(ARTIFACT.read_bytes())
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == DURABLE_FILESYSTEM_SINK_IDENTITY
    )
    assert artifact["canonical_identity"] == DURABLE_FILESYSTEM_SINK_IDENTITY
    assert artifact["authority"] == {
        "source_candidate_normalization": True,
        "filesystem_persistence_when_called": True,
        "process_or_wsl_execution": False,
        "tokenizer_or_model_loading": False,
        "generation_or_inference": False,
        "runner_or_probe_execution": False,
        "stage_c": False,
        "runtime_or_production": False,
    }
    source = SOURCE.read_text("utf-8")
    for forbidden in (
        "subprocess",
        "multiprocessing",
        "wsl.exe",
        "from_pretrained",
        ".generate(",
        ".execute(",
        "if __name__",
    ):
        assert forbidden not in source
