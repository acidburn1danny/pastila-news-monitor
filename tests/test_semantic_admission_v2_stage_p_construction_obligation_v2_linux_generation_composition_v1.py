from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_composition_v1 as composition
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_durable_filesystem_sink_v1 import (
    DURABLE_FILESYSTEM_SINK_IDENTITY,
    DurableArtifactReceiptV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_composition_v1 import (
    LINUX_GENERATION_COMPOSITION_IDENTITY,
    run_linux_generation_composition_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1 import (
    LinuxGenerationSupervisorOutcomeV1,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_generation_composition_v1.py"
)
ARTIFACT = (
    ROOT
    / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-linux-generation-composition-v1.json"
)
sys.path.insert(0, str(ROOT / "tests"))
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (
    _policy,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1 import (
    SYSTEM_PROMPT,
    _authority,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    _fixture,
)


def _inputs():
    raw_request, request = _fixture()
    return raw_request, request, _authority(request)


def _receipt(label, raw):
    digest = hashlib.sha256(raw).hexdigest()
    return DurableArtifactReceiptV1(
        DURABLE_FILESYSTEM_SINK_IDENTITY,
        "sink-instance",
        label,
        len(raw),
        digest,
        "receipt-identity",
        b"{}\n",
    )


def test_composition_orders_validation_binding_persistence_and_supervision(
    tmp_path, monkeypatch
):
    raw_request, request, raw_authority = _inputs()
    authority = composition.parse_generation_authority_v1(
        raw_receipt=raw_authority,
        expected_generation_candidate_identity=composition.SUPERVISOR_CANDIDATE_IDENTITY,
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )
    trace = []
    fake_operations = object()

    def build_operations(**kwargs):
        trace.append(("operations", kwargs))
        return fake_operations

    class Sink:
        sink_instance_identity = "sink-instance"

        def persist(self, label, raw):
            trace.append(("persist", (label, raw)))
            return _receipt(label, raw)

    def create_sink(**kwargs):
        trace.append(("sink", kwargs))
        return Sink()

    first = b"first\n"
    terminal = b"terminal\n"

    def supervise(**kwargs):
        trace.append(("supervise", kwargs))
        assert kwargs["child_operations"] is fake_operations
        kwargs["durable_sink"].persist("runner-result.json", first)
        kwargs["durable_sink"].persist("supervisor-receipt.json", terminal)
        return LinuxGenerationSupervisorOutcomeV1(
            "EXECUTION_FAILURE",
            authority.authority_receipt_identity,
            (
                ("runner-result.json", hashlib.sha256(first).hexdigest()),
                ("supervisor-receipt.json", hashlib.sha256(terminal).hexdigest()),
            ),
            terminal,
        )

    monkeypatch.setattr(
        composition, "build_linux_child_process_operations_v1", build_operations
    )
    monkeypatch.setattr(composition, "create_durable_filesystem_sink_v1", create_sink)
    monkeypatch.setattr(
        composition, "supervise_linux_generation_candidate_v1", supervise
    )
    root = tmp_path / "not-created-by-fake"
    outcome = run_linux_generation_composition_v1(
        raw_policy_receipt=_policy(),
        raw_authority_receipt=raw_authority,
        raw_runner_request=raw_request,
        system_prompt=SYSTEM_PROMPT,
        evidence_root=root,
        timeout_seconds=30.0,
        context_factory=lambda _: object(),
    )
    assert [item[0] for item in trace] == [
        "operations",
        "sink",
        "supervise",
        "persist",
        "persist",
    ]
    binding = trace[1][1]["binding"]
    assert (
        binding.provider_request_id,
        binding.source_context_identity,
        binding.authority_receipt_identity,
    ) == (
        request.provider_request_id,
        request.source_context_identity,
        authority.authority_receipt_identity,
    )
    assert outcome.composition_identity == LINUX_GENERATION_COMPOSITION_IDENTITY
    assert outcome.sink_instance_identity == "sink-instance"
    assert len(outcome.durable_receipts) == 2
    assert root.exists() is False


def test_invalid_authority_fails_before_operations_root_or_supervisor(monkeypatch):
    raw_request, _, _ = _inputs()
    calls = []
    monkeypatch.setattr(
        composition,
        "build_linux_child_process_operations_v1",
        lambda **kwargs: calls.append("operations"),
    )
    monkeypatch.setattr(
        composition,
        "create_durable_filesystem_sink_v1",
        lambda **kwargs: calls.append("sink"),
    )
    monkeypatch.setattr(
        composition,
        "supervise_linux_generation_candidate_v1",
        lambda **kwargs: calls.append("supervisor"),
    )
    with pytest.raises(ValueError):
        run_linux_generation_composition_v1(
            raw_policy_receipt=_policy(),
            raw_authority_receipt=b"{}\n",
            raw_runner_request=raw_request,
            system_prompt=SYSTEM_PROMPT,
            evidence_root=Path("unused"),
            timeout_seconds=30.0,
        )
    assert calls == []


def test_durable_receipt_reconciliation_fails_closed(tmp_path, monkeypatch):
    raw_request, _, raw_authority = _inputs()
    monkeypatch.setattr(
        composition,
        "build_linux_child_process_operations_v1",
        lambda **kwargs: object(),
    )
    sink = SimpleNamespace(
        sink_instance_identity="sink-instance",
        persist=lambda label, raw: _receipt(label, raw),
    )
    monkeypatch.setattr(
        composition, "create_durable_filesystem_sink_v1", lambda **kwargs: sink
    )

    def supervise(**kwargs):
        kwargs["durable_sink"].persist("actual.json", b"actual")
        return LinuxGenerationSupervisorOutcomeV1(
            "EXECUTION_FAILURE",
            "authority",
            (("different.json", hashlib.sha256(b"different").hexdigest()),),
            b"receipt",
        )

    monkeypatch.setattr(
        composition, "supervise_linux_generation_candidate_v1", supervise
    )
    with pytest.raises(RuntimeError, match="DURABLE_RECONCILIATION"):
        run_linux_generation_composition_v1(
            raw_policy_receipt=_policy(),
            raw_authority_receipt=raw_authority,
            raw_runner_request=raw_request,
            system_prompt=SYSTEM_PROMPT,
            evidence_root=tmp_path / "unused",
            timeout_seconds=30.0,
        )


def test_artifact_identity_and_execution_boundary_is_explicit():
    artifact = json.loads(ARTIFACT.read_bytes())
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == LINUX_GENERATION_COMPOSITION_IDENTITY
    )
    assert artifact["canonical_identity"] == LINUX_GENERATION_COMPOSITION_IDENTITY
    assert artifact["authority"] == {
        "source_normalization": True,
        "effectful_composition_invoked_during_verification": False,
        "filesystem_persistence_executed": False,
        "process_or_wsl_launch_executed": False,
        "tokenizer_or_model_loading_executed": False,
        "generation_or_inference_executed": False,
        "provider_execution": False,
        "stage_c": False,
        "runtime_or_production": False,
    }
    assert (
        "actual filesystem, process, tokenizer, model, and generation"
        in artifact["authority_boundary"]["function_invocation"]
    )
    source = SOURCE.read_text("utf-8")
    for forbidden in ("if __name__", "wsl.exe", "subprocess", "multiprocessing"):
        assert forbidden not in source
