from __future__ import annotations

import ast
import hashlib
import json
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_v1_2_1_identity_contract as identities
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 as authority
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_2_1 as host
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_2_1 as binding
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_injected_generation_supervisor_v1_2_1 as injected
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 as worker
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_child_process_adapter_v1_2_1 as child
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_generation_composition_v1_2_1 as composition
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1 as runner
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 as supervisor
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1 import PACKET_RELATIVE, EVIDENCE_RELATIVE, materialize_case01_issuance_packet_v1_2_1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_1 import PreparedGenerationWslInvocationV1
from pastila_scout.wsl_execution_v1 import canonical_model_profile_v1, windows_path_to_wsl_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

ROOT = Path(__file__).resolve().parents[1]


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def test_exact_identity_propagation_and_single_prospective_edge():
    assert authority.AUTHORITY_PRELOAD_IDENTITY == identities.AUTHORITY_PRELOAD_IDENTITY
    assert worker.WORKER_IDENTITY == identities.WORKER_IDENTITY
    assert injected.SUPERVISOR_IDENTITY == identities.INJECTED_SUPERVISOR_IDENTITY
    assert supervisor.SUPERVISOR_CANDIDATE_IDENTITY == identities.SUPERVISOR_IDENTITY
    assert child.LINUX_CHILD_PROCESS_ADAPTER_IDENTITY == identities.CHILD_ADAPTER_IDENTITY
    assert composition.LINUX_GENERATION_COMPOSITION_IDENTITY == identities.COMPOSITION_IDENTITY
    assert runner.LINUX_GENERATION_RUNNER_IDENTITY == identities.RUNNER_IDENTITY
    assert host.GENERATION_WSL_HOST_EXECUTOR_IDENTITY == identities.HOST_EXECUTOR_IDENTITY
    assert binding.GENERATION_WSL_INVOCATION_BINDING_IDENTITY == identities.WSL_BINDING_IDENTITY
    tree = ast.parse((ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_2_1.py").read_text("utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "execute"]
    assert len(calls) == 1


def test_v1_2_receipt_is_rejected_without_structural_compatibility():
    old = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2/authority-receipt-issued.json"
    old_value = json.loads(old.read_bytes())
    with pytest.raises(ValueError):
        authority.parse_generation_authority_v1_2_1(
            raw_receipt=old.read_bytes(),
            expected_host_payload_sha256=old_value["host_payload_sha256"],
            expected_runner_request_sha256=old_value["runner_request_sha256"],
            expected_provider_request_id=old_value["provider_request_id"],
            expected_source_context_identity=old_value["source_context_identity"],
        )


def test_runner_source_binding_is_exact_and_imports_are_inert():
    path = ROOT / binding.RUNNER_RELATIVE
    assert hashlib.sha256(path.read_bytes()).hexdigest() == binding.RUNNER_SOURCE_SHA256
    for module in (worker, injected, supervisor, child, composition, runner, host, binding):
        assert module.__name__.endswith("v1_2_1")
    from pastila_scout.provider_execution_v2.models import ProviderExecutionRequestV2
    assert child.CANONICAL_PROVIDER_EXECUTION_SOURCE_SHA256 == hashlib.sha256(
        (ROOT / "src/pastila_scout/provider_execution_v2/models.py").read_bytes()
    ).hexdigest()
    assert child.CANONICAL_PROVIDER_EXECUTION_REQUEST_TYPE == (
        f"{ProviderExecutionRequestV2.__module__}.{ProviderExecutionRequestV2.__qualname__}"
    )
    from pastila_scout.application_request_authority_v1.models import ApplicationProviderRequestV1
    assert child.CANONICAL_APPLICATION_REQUEST_SOURCE_SHA256 == hashlib.sha256(
        (ROOT / "src/pastila_scout/application_request_authority_v1/models.py").read_bytes()
    ).hexdigest()
    assert child.CANONICAL_APPLICATION_PROVIDER_REQUEST_TYPE == (
        f"{ApplicationProviderRequestV1.__module__}.{ApplicationProviderRequestV1.__qualname__}"
    )
    assert runner.CANONICAL_DURABLE_SINK_SOURCE_SHA256 == hashlib.sha256(
        (ROOT / "src/pastila_scout/semantic_admission_v2/"
         "stage_p_construction_obligation_v2_durable_filesystem_sink_v1.py").read_bytes()
    ).hexdigest()
    assert runner.CANONICAL_COMPOSITION_SOURCE_SHA256 == hashlib.sha256(
        (ROOT / "src/pastila_scout/semantic_admission_v2/"
         "stage_p_construction_obligation_v2_linux_generation_composition_v1_2_1.py").read_bytes()
    ).hexdigest()


def test_optimized_projector_and_generated_suffix_contract_are_source_bound():
    source_root = ROOT / "src/pastila_scout/semantic_admission_v2"
    expected = {
        "CANONICAL_OPTIMIZED_PROJECTOR_SOURCE_SHA256":
            "stage_p_construction_obligation_v2_token_projector_v2.py",
        "CANONICAL_GENERATED_SUFFIX_SOURCE_SHA256":
            "stage_p_construction_obligation_v2_generated_suffix_callback_v1.py",
        "CANONICAL_OPTIMIZED_CALLBACK_SOURCE_SHA256":
            "stage_p_construction_obligation_v2_request_bound_callback_adapter_v1_2_1.py",
    }
    for constant, filename in expected.items():
        assert getattr(runner, constant) == hashlib.sha256(
            (source_root / filename).read_bytes()).hexdigest()
    adapter_source = (source_root /
        "stage_p_construction_obligation_v2_linux_runtime_operations_adapter_v1.py"
    ).read_text("utf-8")
    assert "input_token_ids[batch.prompt_token_count:]" in adapter_source
    assert "allowed(tuple(generated_suffix.tolist()))" in adapter_source
    callback_source = (source_root /
        "stage_p_construction_obligation_v2_request_bound_callback_adapter_v1_2_1.py"
    ).read_text("utf-8")
    assert "StagePConstructionObligationV2TokenProjectorV2(" in callback_source
    assert "RequestBoundGeneratedSuffixCallbackV1(" in callback_source
    assert runner.CANONICAL_RUNTIME_ADAPTER_SOURCE_SHA256 == hashlib.sha256(
        (ROOT / "src/pastila_scout/semantic_admission_v2/"
         "stage_p_construction_obligation_v2_linux_runtime_operations_adapter_v1.py").read_bytes()
    ).hexdigest()
    assert runner.CANONICAL_EXACT_OPERATIONS_ADAPTER_SOURCE_SHA256 == hashlib.sha256(
        (ROOT / "src/pastila_scout/semantic_admission_v2/"
         "stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2_1.py").read_bytes()
    ).hexdigest()
    assert runner.CANONICAL_CHILD_ADAPTER_SOURCE_SHA256 == hashlib.sha256(
        (ROOT / "src/pastila_scout/semantic_admission_v2/"
         "stage_p_construction_obligation_v2_linux_child_process_adapter_v1_2_1.py").read_bytes()
    ).hexdigest()


def _prepared(tmp_path: Path, monkeypatch=None):
    packet = tmp_path / PACKET_RELATIVE
    packet.mkdir(parents=True)
    generated = materialize_case01_issuance_packet_v1_2_1(
        project_root=ROOT, deployment_root=tmp_path)
    for name, raw in generated.items():
        (packet / name).write_bytes(raw)
    policy = tmp_path / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json"
    prompt = tmp_path / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"
    policy.parent.mkdir(parents=True, exist_ok=True)
    prompt.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / policy.relative_to(tmp_path), policy)
    shutil.copyfile(ROOT / prompt.relative_to(tmp_path), prompt)
    candidate = json.loads((packet / "authority-receipt-candidate.json").read_bytes())
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = candidate["proposed_receipt_identity"]
    receipt = packet / "authority-receipt-issued.json"
    receipt.write_bytes(_canonical(issued))
    manifest = json.loads((packet / "manifest.json").read_bytes())
    outer = Path(manifest["proposed_evidence_root"])
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    invocation = boundary.build_invocation(
        consumer_id="construction-obligation-v2-generation-v1-2-1",
        authority_reference=candidate["proposed_receipt_identity"],
        arguments=("-m", binding.RUNNER_MODULE,
                   windows_path_to_wsl_v1(policy),
                   windows_path_to_wsl_v1(receipt),
                   windows_path_to_wsl_v1(packet / "runner-request.json"),
                   windows_path_to_wsl_v1(prompt),
                   windows_path_to_wsl_v1(outer / "linux-generation")))
    evidence = manifest["evidence_root_identity"]
    prepared = binding.build_generation_wsl_invocation_v1_2_1(
        project_root=ROOT,
        policy_receipt_path=policy,
        authority_receipt_path=receipt, runner_request_path=packet / "runner-request.json",
        system_prompt_path=prompt,
        packet_manifest_path=packet / "manifest.json", outer_evidence_root=outer,
        evidence_root_identity=evidence, boundary=boundary)
    return prepared, boundary


def test_builder_exercises_only_v1_2_1_parser(tmp_path, monkeypatch):
    calls = []
    real = binding.parse_generation_authority_v1_2_1
    monkeypatch.setattr(binding, "parse_generation_authority_v1_2_1",
                        lambda **kwargs: (calls.append(kwargs) or real(**kwargs)))
    prepared, _ = _prepared(tmp_path)
    assert type(prepared) is binding.PreparedGenerationWslInvocationV1_2_1
    assert len(calls) == 1
    source = (ROOT / binding.__file__).read_text("utf-8")
    assert "parse_generation_authority_v1_1" not in source


def test_exact_prepared_invocation_passes_host_revalidation_without_execute(tmp_path, monkeypatch):
    prepared, boundary = _prepared(tmp_path)
    calls = []
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute",
                        lambda self, invocation, timeout_seconds: calls.append(invocation))
    host._revalidate_prepared_v1_2_1(prepared, boundary)
    assert type(prepared) is binding.PreparedGenerationWslInvocationV1_2_1
    assert calls == []


@pytest.mark.parametrize("legacy", ("v1", "v1-2"))
def test_legacy_receipts_cannot_build_v1_2_1(tmp_path, legacy):
    old_dir = ROOT / f"docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-{legacy}"
    old_receipt = old_dir / "authority-receipt-issued.json"
    if not old_receipt.exists():
        pytest.skip("legacy issued fixture absent")
    packet = ROOT / PACKET_RELATIVE
    with pytest.raises(ValueError):
        binding.build_generation_wsl_invocation_v1_2_1(
            project_root=ROOT,
            policy_receipt_path=ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json",
            authority_receipt_path=old_receipt, runner_request_path=packet / "runner-request.json",
            system_prompt_path=ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
            packet_manifest_path=packet / "manifest.json",
            outer_evidence_root=tmp_path / "never",
            evidence_root_identity="1" * 64,
            boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True)))


def test_consumed_pre_fix_v1_2_1_receipt_cannot_build_successor(tmp_path):
    packet = ROOT / PACKET_RELATIVE
    consumed = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-authority-plan-bound/authority-receipt-issued.json"
    with pytest.raises(ValueError):
        binding.build_generation_wsl_invocation_v1_2_1(
            project_root=ROOT,
            policy_receipt_path=ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json",
            authority_receipt_path=consumed,
            runner_request_path=packet / "runner-request.json",
            packet_manifest_path=packet / "manifest.json",
            system_prompt_path=ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
            outer_evidence_root=tmp_path / "never",
            evidence_root_identity=json.loads((packet / "manifest.json").read_bytes())["evidence_root_identity"],
            boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True)))


def test_consumed_provider_source_receipt_cannot_build_successor(tmp_path):
    packet = ROOT / PACKET_RELATIVE
    consumed = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-provider-source-bound/authority-receipt-issued.json"
    with pytest.raises(ValueError):
        binding.build_generation_wsl_invocation_v1_2_1(
            project_root=ROOT,
            policy_receipt_path=ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json",
            authority_receipt_path=consumed,
            runner_request_path=packet / "runner-request.json",
            packet_manifest_path=packet / "manifest.json",
            system_prompt_path=ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
            outer_evidence_root=tmp_path / "never",
            evidence_root_identity=json.loads((packet / "manifest.json").read_bytes())["evidence_root_identity"],
            boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True)))


def test_consumed_application_source_receipt_cannot_build_successor(tmp_path):
    packet = ROOT / PACKET_RELATIVE
    consumed = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-application-source-bound/authority-receipt-issued.json"
    with pytest.raises(ValueError):
        binding.build_generation_wsl_invocation_v1_2_1(
            project_root=ROOT,
            policy_receipt_path=ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json",
            authority_receipt_path=consumed,
            runner_request_path=packet / "runner-request.json",
            packet_manifest_path=packet / "manifest.json",
            system_prompt_path=ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
            outer_evidence_root=tmp_path / "never",
            evidence_root_identity=json.loads((packet / "manifest.json").read_bytes())["evidence_root_identity"],
            boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True)))


def test_consumed_durable_source_receipt_cannot_build_successor(tmp_path):
    packet = ROOT / PACKET_RELATIVE
    consumed = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-durable-source-bound/authority-receipt-issued.json"
    with pytest.raises(ValueError):
        binding.build_generation_wsl_invocation_v1_2_1(
            project_root=ROOT,
            policy_receipt_path=ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json",
            authority_receipt_path=consumed,
            runner_request_path=packet / "runner-request.json",
            packet_manifest_path=packet / "manifest.json",
            system_prompt_path=ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
            outer_evidence_root=tmp_path / "never",
            evidence_root_identity=json.loads((packet / "manifest.json").read_bytes())["evidence_root_identity"],
            boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True)))


def test_consumed_runtime_source_receipt_cannot_build_successor(tmp_path):
    packet = ROOT / PACKET_RELATIVE
    consumed = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-runtime-source-bound/authority-receipt-issued.json"
    with pytest.raises(ValueError):
        binding.build_generation_wsl_invocation_v1_2_1(
            project_root=ROOT,
            policy_receipt_path=ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json",
            authority_receipt_path=consumed,
            runner_request_path=packet / "runner-request.json",
            packet_manifest_path=packet / "manifest.json",
            system_prompt_path=ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
            outer_evidence_root=tmp_path / "never",
            evidence_root_identity=json.loads((packet / "manifest.json").read_bytes())["evidence_root_identity"],
            boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True)))


def test_consumed_exact_operations_receipt_cannot_build_timeout_successor(tmp_path):
    packet = ROOT / PACKET_RELATIVE
    consumed = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2-1-exact-operations-bound/authority-receipt-issued.json"
    with pytest.raises(ValueError):
        binding.build_generation_wsl_invocation_v1_2_1(
            project_root=ROOT,
            policy_receipt_path=ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json",
            authority_receipt_path=consumed,
            runner_request_path=packet / "runner-request.json",
            packet_manifest_path=packet / "manifest.json",
            system_prompt_path=ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
            outer_evidence_root=tmp_path / "never",
            evidence_root_identity=json.loads((packet / "manifest.json").read_bytes())["evidence_root_identity"],
            boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True)))


def test_legacy_type_and_mutations_fail_before_execute(tmp_path, monkeypatch):
    prepared, boundary = _prepared(tmp_path)
    calls = []
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute",
                        lambda self, invocation, timeout_seconds: calls.append(invocation))
    legacy = PreparedGenerationWslInvocationV1(
        prepared.invocation_instance_identity, prepared.invocation,
        prepared.authority_receipt_identity, prepared.provider_request_id,
        prepared.source_context_identity, prepared.runner_request_sha256,
        prepared.outer_evidence_root, prepared.linux_evidence_root)
    with pytest.raises(TypeError):
        host.execute_generation_wsl_host_v1_2_1(prepared=legacy, boundary=boundary)
    for mutated in (replace(prepared, command_identity="0" * 64),
                    replace(prepared, wsl_binding_identity="0" * 64),
                    replace(prepared, packet_identity="0" * 64)):
        with pytest.raises(ValueError):
            host.execute_generation_wsl_host_v1_2_1(prepared=mutated, boundary=boundary)
    assert calls == []


def test_recomputed_instance_cannot_substitute_packet_identity(tmp_path, monkeypatch):
    prepared, boundary = _prepared(tmp_path)
    forged_packet_identity = "0" * 64
    material = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_GENERATION_WSL_INVOCATION_INSTANCE_V1_2_1",
        binding.GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
        prepared.command_identity, prepared.authority_receipt_identity,
        prepared.runner_request_sha256, forged_packet_identity,
        prepared.provider_request_id, prepared.source_context_identity,
        prepared.evidence_root_identity, str(prepared.outer_evidence_root),
        str(prepared.policy_receipt_path), str(prepared.authority_receipt_path),
        str(prepared.runner_request_path), str(prepared.packet_manifest_path),
        str(prepared.system_prompt_path), str(binding.OUTER_TIMEOUT_SECONDS),
    )
    forged = replace(
        prepared, packet_identity=forged_packet_identity,
        invocation_instance_identity=hashlib.sha256(
            "\n".join(material).encode()).hexdigest())
    calls = []
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute",
                        lambda self, invocation, timeout_seconds: calls.append(invocation))
    with pytest.raises(ValueError, match="EXECUTION_PLAN_DRIFT"):
        host.execute_generation_wsl_host_v1_2_1(prepared=forged, boundary=boundary)
    assert calls == []


def test_undeclared_packet_file_fails_before_execute(tmp_path, monkeypatch):
    prepared, boundary = _prepared(tmp_path)
    (prepared.packet_manifest_path.parent / "undeclared-extra.bin").write_bytes(b"extra")
    calls = []
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute",
                        lambda self, invocation, timeout_seconds: calls.append(invocation))
    with pytest.raises(ValueError, match="DIRECTORY_FILE_SET"):
        host.execute_generation_wsl_host_v1_2_1(prepared=prepared, boundary=boundary)
    assert calls == []


def test_resealed_relocated_packet_cannot_reuse_authority(tmp_path):
    prepared, boundary = _prepared(tmp_path / "original")
    relocated_root = tmp_path / "relocated"
    relocated_packet = relocated_root / PACKET_RELATIVE
    relocated_packet.parent.mkdir(parents=True)
    shutil.copytree(prepared.packet_manifest_path.parent, relocated_packet)
    relocated_outer = relocated_root / EVIDENCE_RELATIVE
    manifest = json.loads((relocated_packet / "manifest.json").read_bytes())
    manifest["proposed_evidence_root"] = str(relocated_outer)
    manifest["packet_identity"] = hashlib.sha256(_canonical({
        key: value for key, value in manifest.items() if key != "packet_identity"
    })).hexdigest()
    (relocated_packet / "manifest.json").write_bytes(_canonical(manifest))
    with pytest.raises(ValueError, match="PACKET_PLAN"):
        binding.build_generation_wsl_invocation_v1_2_1(
            project_root=ROOT, policy_receipt_path=prepared.policy_receipt_path,
            authority_receipt_path=relocated_packet / "authority-receipt-issued.json",
            runner_request_path=relocated_packet / "runner-request.json",
            packet_manifest_path=relocated_packet / "manifest.json",
            system_prompt_path=prepared.system_prompt_path,
            outer_evidence_root=relocated_outer,
            evidence_root_identity=prepared.evidence_root_identity, boundary=boundary)


def test_resealed_candidate_body_disagreement_fails_before_execute(tmp_path, monkeypatch):
    prepared, boundary = _prepared(tmp_path)
    packet = prepared.packet_manifest_path.parent
    candidate_path = packet / "authority-receipt-candidate.json"
    candidate = json.loads(candidate_path.read_bytes())
    candidate["authority_body"]["owner_authority_identity"] = "forged-owner"
    candidate_path.write_bytes(_canonical(candidate))
    manifest = json.loads(prepared.packet_manifest_path.read_bytes())
    manifest["file_sha256"]["authority-receipt-candidate.json"] = hashlib.sha256(
        candidate_path.read_bytes()).hexdigest()
    manifest["packet_identity"] = hashlib.sha256(_canonical({
        key: value for key, value in manifest.items() if key != "packet_identity"
    })).hexdigest()
    prepared.packet_manifest_path.write_bytes(_canonical(manifest))
    material = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_GENERATION_WSL_INVOCATION_INSTANCE_V1_2_1",
        binding.GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
        prepared.command_identity, prepared.authority_receipt_identity,
        prepared.runner_request_sha256, manifest["packet_identity"],
        prepared.provider_request_id, prepared.source_context_identity,
        prepared.evidence_root_identity, str(prepared.outer_evidence_root),
        str(prepared.policy_receipt_path), str(prepared.authority_receipt_path),
        str(prepared.runner_request_path), str(prepared.packet_manifest_path),
        str(prepared.system_prompt_path), str(binding.OUTER_TIMEOUT_SECONDS),
    )
    forged = replace(
        prepared, packet_identity=manifest["packet_identity"],
        invocation_instance_identity=hashlib.sha256(
            "\n".join(material).encode()).hexdigest())
    calls = []
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute",
                        lambda self, invocation, timeout_seconds: calls.append(invocation))
    with pytest.raises(ValueError, match="PACKET_BINDING"):
        host.execute_generation_wsl_host_v1_2_1(prepared=forged, boundary=boundary)
    assert calls == []
