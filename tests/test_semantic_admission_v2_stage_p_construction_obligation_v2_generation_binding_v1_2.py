from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_2 as binding
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_generation_composition_v1_2 as composition
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_generation_runner_v1_2 as runner
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_durable_filesystem_sink_v1 import DurableArtifactReceiptV1

ROOT = Path(__file__).resolve().parents[1]


def test_composition_persists_bound_pre_model_failure(monkeypatch, tmp_path):
    request = SimpleNamespace(
        host_payload_sha256="a" * 64, provider_request_id="request",
        source_context_identity="b" * 64,
    )
    authority = SimpleNamespace(authority_receipt_identity="c" * 64)
    persisted = []
    monkeypatch.setattr(composition, "parse_runner_request_v1", lambda **kw: request)
    monkeypatch.setattr(composition, "parse_generation_authority_v1_2", lambda **kw: authority)

    class Sink:
        sink_instance_identity = "sink"
        def persist(self, label, raw):
            persisted.append((label, raw))
            return DurableArtifactReceiptV1("d" * 64, "sink", label, len(raw), hashlib.sha256(raw).hexdigest(), "e" * 64, b"{}\n")

    monkeypatch.setattr(composition, "create_durable_filesystem_sink_v1", lambda **kw: Sink())
    monkeypatch.setattr(composition, "build_linux_child_process_operations_v1_2", lambda **kw: (_ for _ in ()).throw(TypeError("blocked")))
    with pytest.raises(TypeError, match="blocked"):
        composition.run_linux_generation_composition_v1_2(
            raw_policy_receipt=b"policy", raw_authority_receipt=b"authority",
            raw_runner_request=b"request", system_prompt="prompt",
            evidence_root=tmp_path / "root", timeout_seconds=1.0,
        )
    assert [item[0] for item in persisted] == ["composition-pre-model-failure-v1-2.json"]
    receipt = json.loads(persisted[0][1])
    assert receipt["model_load_started"] is False
    assert receipt["generation_started"] is False
    assert receipt["retry_count"] == 0
    assert receipt["authority_receipt_identity"] == "c" * 64


def test_runner_and_binding_identities_are_source_exact_and_inert():
    runner_path = ROOT / binding.RUNNER_RELATIVE
    assert hashlib.sha256(runner_path.read_bytes()).hexdigest() == binding.RUNNER_SOURCE_SHA256
    assert binding.RUNNER_MODULE.endswith("linux_generation_runner_v1_2")
    assert binding.GENERATION_WSL_INVOCATION_BINDING_IDENTITY == hashlib.sha256(
        "\n".join(binding.GENERATION_WSL_INVOCATION_BINDING_IDENTITY_FIELDS).encode()
    ).hexdigest()
    assert runner.LINUX_GENERATION_RUNNER_IDENTITY == hashlib.sha256(
        "\n".join(runner.LINUX_GENERATION_RUNNER_IDENTITY_FIELDS).encode()
    ).hexdigest()
    assert composition.LINUX_GENERATION_COMPOSITION_IDENTITY == hashlib.sha256(
        "\n".join(composition.LINUX_GENERATION_COMPOSITION_IDENTITY_FIELDS).encode()
    ).hexdigest()
