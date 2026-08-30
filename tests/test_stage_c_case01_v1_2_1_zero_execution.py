from __future__ import annotations

import hashlib
import json
import subprocess
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import stage_c_case01_linux_runner_v1_2_1 as linux_runner
from pastila_scout.semantic_admission_v2 import stage_c_case01_wsl_v1_2_1 as stage_c_wsl

from pastila_scout.semantic_admission_v2.stage_c_case01_frozen_input_v1_2_1 import (
    RAW_OUTPUT_SHA256, admit_frozen_stage_c_case01_input_v1_2_1,
)
from pastila_scout.semantic_admission_v2.stage_c_case01_wsl_v1_2_1 import (
    EVIDENCE_RELATIVE, PACKET_RELATIVE,
    PreparedStageCCase01WslInvocationV1_2_1,
    execute_stage_c_case01_host_v1_2_1,
    materialize_stage_c_case01_packet_v1_2_1,
    prepare_stage_c_case01_wsl_invocation_v1_2_1,
)
from pastila_scout.wsl_execution_v1 import canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

ROOT = Path(__file__).parents[1]


@pytest.fixture(autouse=True)
def _admit_temporary_test_packets(monkeypatch):
    monkeypatch.setattr(stage_c_wsl, "_verify_current_packet_git_objects",
                        lambda project_root, packet_root, expected: "f" * 40)


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def _frozen_args():
    pack = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json").read_text("utf-8"))
    case = next(item for item in pack["cases"] if item["case_id"] == "HMCV1-SASC-01")
    raw = subprocess.check_output([
        "git", "show",
        "2c5ce79396ecd14df16a452e8ce46ff65b394f54:.semantic-admission-v2-stage-p-"
        "construction-obligation-v2-case01-successor-v1-2-1-creative-semantics-"
        "pruning-bound-evidence/linux-generation/raw-output.bin"], cwd=ROOT)
    return dict(raw_ledger=raw, candidate=case["candidate"].encode(),
                factual_authority=case["factual_summary"].encode(),
                raw_evaluation_receipt=(ROOT / "docs/artifacts/semantic-admission-v2-case01-creative-semantics-pruning-bound-semantic-evaluation-v1.json").read_bytes(),
                raw_closure_receipt=(ROOT / "docs/artifacts/semantic-admission-v2-case01-creative-semantics-pruning-bound-closure-v1.json").read_bytes())


def _packet(tmp_path: Path):
    files = materialize_stage_c_case01_packet_v1_2_1(
        project_root=ROOT, deployment_root=tmp_path)
    packet = tmp_path / PACKET_RELATIVE
    packet.mkdir(parents=True)
    for name, raw in files.items():
        (packet / name).write_bytes(raw)
    return packet, tmp_path / EVIDENCE_RELATIVE, files


def _issue_for_test(packet: Path):
    candidate = json.loads((packet / "authority-receipt-candidate.json").read_bytes())
    body = candidate["authority_body"]
    identity = hashlib.sha256(_canonical(body)).hexdigest()
    assert identity == candidate["proposed_receipt_identity"]
    (packet / "authority-receipt-issued.json").write_bytes(
        _canonical({**body, "authority_receipt_identity": identity}))


def test_frozen_input_exact_current_lineage_passes_and_mutations_fail():
    args = _frozen_args()
    admitted = admit_frozen_stage_c_case01_input_v1_2_1(**args)
    assert admitted.raw_output_sha256 == RAW_OUTPUT_SHA256
    for name in ("raw_ledger", "candidate", "factual_authority",
                 "raw_evaluation_receipt", "raw_closure_receipt"):
        mutated = dict(args)
        mutated[name] = mutated[name] + b" "
        with pytest.raises(ValueError):
            admit_frozen_stage_c_case01_input_v1_2_1(**mutated)


def test_packet_is_unissued_zero_execution_and_stage_p_is_prohibited(tmp_path):
    _, evidence, files = _packet(tmp_path)
    manifest = json.loads(files["manifest.json"])
    request = json.loads(files["stage-c-request.json"])
    assert manifest["receipt_status"] == "UNISSUED"
    assert manifest["attempts"] == {"completed": 0, "ceiling": 1}
    assert not any(manifest["execution"].values())
    assert manifest["stage_p_calls_authorized"] == 0
    assert request["stage_p_calls_authorized"] == 0
    assert not evidence.exists()
    assert "authority-receipt-issued.json" not in files


def test_exact_prepared_type_and_mutation_fail_before_execute(tmp_path, monkeypatch):
    packet, evidence, _ = _packet(tmp_path)
    _issue_for_test(packet)
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    prepared = prepare_stage_c_case01_wsl_invocation_v1_2_1(
        project_root=ROOT, packet_root=packet.resolve(), evidence_root=evidence,
        boundary=boundary)
    assert type(prepared) is PreparedStageCCase01WslInvocationV1_2_1
    assert prepared.issuance_commit == "f" * 40
    calls = []
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute",
                        lambda *args, **kwargs: calls.append((args, kwargs)))
    with pytest.raises(TypeError):
        execute_stage_c_case01_host_v1_2_1(prepared=object(), boundary=boundary)
    with pytest.raises(ValueError):
        execute_stage_c_case01_host_v1_2_1(
            prepared=replace(prepared, command_identity="0" * 64), boundary=boundary)
    assert calls == []
    assert not evidence.exists()


def test_packet_file_mutation_and_extra_file_fail_closed(tmp_path):
    packet, evidence, _ = _packet(tmp_path)
    _issue_for_test(packet)
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    (packet / "frozen-stage-p-ledger.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="FILE_HASH"):
        prepare_stage_c_case01_wsl_invocation_v1_2_1(
            project_root=ROOT, packet_root=packet.resolve(), evidence_root=evidence,
            boundary=boundary)


def test_stale_receipt_and_packet_relocation_fail_closed(tmp_path):
    packet, evidence, _ = _packet(tmp_path / "original")
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    (packet / "authority-receipt-issued.json").write_bytes(_canonical({
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.2.1", "authority_receipt_identity": "0" * 64}))
    with pytest.raises(ValueError, match="AUTHORITY_BINDING"):
        prepare_stage_c_case01_wsl_invocation_v1_2_1(
            project_root=ROOT, packet_root=packet.resolve(), evidence_root=evidence,
            boundary=boundary)
    (packet / "authority-receipt-issued.json").unlink()
    _issue_for_test(packet)
    relocated = tmp_path / "relocated" / PACKET_RELATIVE
    relocated.parent.mkdir(parents=True)
    shutil.copytree(packet, relocated)
    with pytest.raises(ValueError):
        prepare_stage_c_case01_wsl_invocation_v1_2_1(
            project_root=ROOT, packet_root=relocated.resolve(),
            evidence_root=tmp_path / "relocated" / EVIDENCE_RELATIVE,
            boundary=boundary)
    (packet / "extra.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="FILE_SET"):
        prepare_stage_c_case01_wsl_invocation_v1_2_1(
            project_root=ROOT, packet_root=packet.resolve(), evidence_root=evidence,
            boundary=boundary)


def test_sole_prospective_execute_edge_and_imports_are_inert():
    source = (ROOT / "src/pastila_scout/semantic_admission_v2/stage_c_case01_wsl_v1_2_1.py").read_text("utf-8")
    assert source.count("boundary.execute(") == 1
    runner = (ROOT / "src/pastila_scout/semantic_admission_v2/stage_c_case01_linux_runner_v1_2_1.py").read_text("utf-8")
    assert "AutoModel" not in runner
    assert "from transformers" not in runner


def test_request_authority_fields_and_frozen_commit_blobs_fail_closed(tmp_path):
    packet, evidence, _ = _packet(tmp_path)
    _issue_for_test(packet)
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    request = json.loads((packet / "stage-c-request.json").read_bytes())
    request["stage_p_calls_authorized"] = 1
    (packet / "stage-c-request.json").write_bytes(_canonical(request))
    with pytest.raises(ValueError):
        prepare_stage_c_case01_wsl_invocation_v1_2_1(
            project_root=ROOT, packet_root=packet.resolve(), evidence_root=evidence,
            boundary=boundary)


def test_git_object_packet_admission_is_mandatory(tmp_path, monkeypatch):
    packet, evidence, _ = _packet(tmp_path)
    _issue_for_test(packet)
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    monkeypatch.setattr(stage_c_wsl, "_verify_current_packet_git_objects",
                        lambda *args: (_ for _ in ()).throw(
                            ValueError("STAGE_C_PACKET_GIT_OBJECT_MISMATCH")))
    with pytest.raises(ValueError, match="GIT_OBJECT"):
        prepare_stage_c_case01_wsl_invocation_v1_2_1(
            project_root=ROOT, packet_root=packet.resolve(), evidence_root=evidence,
            boundary=boundary)


def test_prepared_identity_changes_with_exact_issuance_commit(tmp_path, monkeypatch):
    packet, evidence, _ = _packet(tmp_path)
    _issue_for_test(packet)
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    first = prepare_stage_c_case01_wsl_invocation_v1_2_1(
        project_root=ROOT, packet_root=packet.resolve(), evidence_root=evidence,
        boundary=boundary)
    monkeypatch.setattr(stage_c_wsl, "_verify_current_packet_git_objects",
                        lambda *args: "e" * 40)
    second = prepare_stage_c_case01_wsl_invocation_v1_2_1(
        project_root=ROOT, packet_root=packet.resolve(), evidence_root=evidence,
        boundary=boundary)
    assert first.issuance_commit == "f" * 40
    assert second.issuance_commit == "e" * 40
    assert first.invocation_identity != second.invocation_identity


def test_linux_supervisor_terminal_success_uses_real_durable_sink_without_model(tmp_path, monkeypatch):
    packet, evidence, _ = _packet(tmp_path)
    _issue_for_test(packet)
    evidence.mkdir()
    monkeypatch.setattr(linux_runner, "STAGE_C_PROMPT",
                        ROOT / "docs/artifacts/semantic-admission-v2-stage-c-prompt-v1.txt")
    monkeypatch.setattr(linux_runner, "SYSTEM_PROMPT",
                        ROOT / "docs/artifacts/semantic-admission-v2-stage-c-prompt-v1.txt")
    def fake_run(command, **kwargs):
        response, lifecycle = Path(command[4]), Path(command[6])
        response.write_bytes(_canonical({
            "output": '{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]}',
            "terminal_eos": True, "constraint_active": True}))
        lifecycle.write_bytes(_canonical({"model_load_succeeded": True,
                                          "inference_succeeded": True}))
        return subprocess.CompletedProcess(command, 0, b"", b"")
    monkeypatch.setattr(linux_runner.subprocess, "run", fake_run)
    status = linux_runner.supervise(
        packet / "stage-c-request.json", packet / "authority-receipt-issued.json",
        packet / "frozen-stage-p-ledger.json", evidence / "linux-stage-c")
    assert status == 0
    result = json.loads((evidence / "linux-stage-c/result-envelope.json").read_bytes())
    assert result["status"] == "TERMINAL_OUTPUT"
    assert result["failure"] is None
    assert (evidence / "linux-stage-c/cleanup-observation.json").is_file()


def test_linux_supervisor_timeout_is_distinct_and_cleanup_is_durable(tmp_path, monkeypatch):
    packet, evidence, _ = _packet(tmp_path)
    _issue_for_test(packet)
    evidence.mkdir()
    monkeypatch.setattr(linux_runner, "STAGE_C_PROMPT",
                        ROOT / "docs/artifacts/semantic-admission-v2-stage-c-prompt-v1.txt")
    monkeypatch.setattr(linux_runner, "SYSTEM_PROMPT",
                        ROOT / "docs/artifacts/semantic-admission-v2-stage-c-prompt-v1.txt")
    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, linux_runner.CHILD_TIMEOUT_SECONDS,
                                        output=b"partial", stderr=b"timed out")
    monkeypatch.setattr(linux_runner.subprocess, "run", timeout)
    status = linux_runner.supervise(
        packet / "stage-c-request.json", packet / "authority-receipt-issued.json",
        packet / "frozen-stage-p-ledger.json", evidence / "linux-stage-c")
    assert status == 20
    result = json.loads((evidence / "linux-stage-c/result-envelope.json").read_bytes())
    assert result["status"] == "EXECUTION_FAILURE"
    assert result["failure"] == "STAGE_C_CHILD_TIMEOUT"
    cleanup = json.loads((evidence / "linux-stage-c/cleanup-observation.json").read_bytes())
    assert cleanup["child_process_terminated"] is True
