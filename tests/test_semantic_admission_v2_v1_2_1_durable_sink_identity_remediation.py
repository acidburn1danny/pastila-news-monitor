from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from pastila_scout.semantic_admission_v2 import (
    stage_p_construction_obligation_v2_linux_generation_composition_v1_2_1 as composition,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_durable_filesystem_sink_v1 import (
    SUPERVISOR_CANDIDATE_IDENTITY,
    SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1,
    DurableEvidenceRootBindingV1,
    create_durable_filesystem_sink_v1,
    create_durable_filesystem_sink_v1_2_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 import (
    SUPERVISOR_CANDIDATE_IDENTITY as CANONICAL_V1_2_1_SUPERVISOR_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_case01_issuance_packet_v1_2_1 import (
    PACKET_RELATIVE,
)
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1 import (
    ConstructionObligationV2RunnerPreflightV1_1,
)
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import (
    bind_static_projector_preflight_v1_2,
)
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import (
    bind_static_callback_preflight_v1_3,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import (
    PACKAGE_IDENTITIES, GenerationPreloadObservationV1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_supervisor_v1_2_1 import (
    supervise_injected_generation_v1_2_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 import (
    InjectedCompatibleGenerationResourceV1, InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 import (
    InjectedChildProcessOperationsV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    parse_runner_request_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    DECODER_IDENTITY, DECODER_MECHANISM_IDENTITY, EOS_TOKEN_ID,
    PROJECTOR_FREEZE_IDENTITY, TOKENIZER_IDENTITY, TokenPieceBundleV1,
)
from test_semantic_admission_v2_stage_p_semantic_completeness_v1 import _positive_value

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / PACKET_RELATIVE
POLICY = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json"
COMPATIBILITY = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-adapter-compatibility-validation-receipt-v1.json"
SYSTEM_PROMPT = ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"


def _binding(supervisor_identity: str) -> DurableEvidenceRootBindingV1:
    return DurableEvidenceRootBindingV1(
        "application-request-v1:test", "1" * 64, "2" * 64, supervisor_identity,
    )


def test_v1_2_1_sink_accepts_only_exact_current_supervisor(tmp_path: Path) -> None:
    assert SUPERVISOR_CANDIDATE_IDENTITY_V1_2_1 == CANONICAL_V1_2_1_SUPERVISOR_IDENTITY
    sink = create_durable_filesystem_sink_v1_2_1(
        root=tmp_path / "v1-2-1", binding=_binding(CANONICAL_V1_2_1_SUPERVISOR_IDENTITY),
    )
    assert sink.binding.supervisor_candidate_identity == CANONICAL_V1_2_1_SUPERVISOR_IDENTITY
    with pytest.raises(ValueError, match="DURABLE_SUPERVISOR_IDENTITY_MISMATCH"):
        create_durable_filesystem_sink_v1_2_1(
            root=tmp_path / "legacy-rejected", binding=_binding(SUPERVISOR_CANDIDATE_IDENTITY),
        )


def test_legacy_sink_contract_remains_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="DURABLE_SUPERVISOR_IDENTITY_MISMATCH"):
        create_durable_filesystem_sink_v1(
            root=tmp_path / "current-rejected",
            binding=_binding(CANONICAL_V1_2_1_SUPERVISOR_IDENTITY),
        )


def test_real_current_sink_accepts_every_reconciliation_branch_label(
        tmp_path: Path) -> None:
    sink = create_durable_filesystem_sink_v1_2_1(
        root=tmp_path / "all-reconciliation-labels",
        binding=_binding(CANONICAL_V1_2_1_SUPERVISOR_IDENTITY),
    )
    lifecycle = (
        "model-load-started", "model-load-completed", "generation-started",
        "terminal-eos", "no-legal-token", "execution-failed",
        "cleanup-completed", "cleanup-failed",
    )
    labels = [f"lifecycle-{index:05d}-{event}.json"
              for index, event in enumerate(lifecycle, 1)]
    labels.extend((
        "adapter-compatibility-receipt.json", "raw-output.bin",
        "raw-partial-output.bin", "runner-result.json",
        "cleanup-receipt-v1-1.json", "result-envelope-v1-1.json",
        "termination-cleanup-observation.json", "generation-progress-00001.json",
        "supervisor-receipt.json", "composition-pre-model-failure-v1-2.json",
    ))
    receipts = tuple(sink.persist(label, b"{}\n") for label in labels)
    assert tuple(receipt.label for receipt in receipts) == tuple(labels)
    assert all((sink.root / label).read_bytes() == b"{}\n" for label in labels)


def test_v1_2_1_composition_binds_versioned_sink_without_execution_surface() -> None:
    source = Path(composition.__file__).read_text("utf-8")
    assert "create_durable_filesystem_sink_v1_2_1" in source
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    assert all(not (isinstance(node.func, ast.Attribute) and node.func.attr == "execute")
               for node in calls)
    assert all(term not in source for term in (
        "subprocess", "wsl.exe", "from_pretrained", ".generate(", "nvidia-smi",
    ))


def test_real_composition_crosses_sink_binding_and_persists_injected_failure(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    candidate = json.loads((PACKET / "authority-receipt-candidate.json").read_bytes())
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = candidate["proposed_receipt_identity"]
    canonical = lambda value: (json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False) + "\n").encode()
    monkeypatch.setattr(
        composition, "build_linux_child_process_operations_v1_2_1",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("INJECTED_AFTER_SINK")))
    evidence = tmp_path / "linux-generation"
    with pytest.raises(RuntimeError, match="INJECTED_AFTER_SINK"):
        composition.run_linux_generation_composition_v1_2_1(
            raw_policy_receipt=(ROOT / "docs/artifacts/semantic-admission-v2-stage-p-"
                "construction-obligation-v2-generation-policy-validation-receipt-v1.json"
            ).read_bytes(),
            raw_authority_receipt=canonical(issued),
            raw_runner_request=(PACKET / "runner-request.json").read_bytes(),
            system_prompt="not consumed before injected failure",
            evidence_root=evidence, timeout_seconds=1200.0)
    persisted = evidence / "composition-pre-model-failure-v1-2.json"
    assert persisted.is_file()
    receipt = json.loads(persisted.read_bytes())
    assert receipt["failure_type"] == "RuntimeError"
    assert receipt["model_load_started"] is False
    assert receipt["generation_started"] is False


def test_exact_current_fake_runtime_reaches_terminal_output_through_real_sink(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the exact child/worker/supervisor/durable path without a process or model."""
    raw_request = (PACKET / "runner-request.json").read_bytes()
    request = parse_runner_request_v1(raw_request=raw_request)
    candidate = json.loads((PACKET / "authority-receipt-candidate.json").read_bytes())
    issued = dict(candidate["authority_body"])
    issued["authority_receipt_identity"] = candidate["proposed_receipt_identity"]
    canonical = lambda value: (json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False) + "\n").encode()
    raw_authority = canonical(issued)

    # The canonical source binding supplies the exact Case 01 context.  A single
    # synthetic token carries a valid terminal document; EOS remains terminal-only.
    seed = ConstructionObligationV2RunnerPreflightV1_1(
        request, TokenPieceBundleV1(
            MappingProxyType({EOS_TOKEN_ID: ""}), frozenset((0, 1, 11)),
            EOS_TOKEN_ID, TOKENIZER_IDENTITY, DECODER_IDENTITY,
            PROJECTOR_FREEZE_IDENTITY,
            decoder_mechanism_identity=DECODER_MECHANISM_IDENTITY))
    context = bind_static_projector_preflight_v1_2(
        preflight=seed).projector.controller.tracker.context
    terminal_text = json.dumps(
        _positive_value(), ensure_ascii=False, separators=(",", ":"))
    bundle = TokenPieceBundleV1(
        MappingProxyType({100: terminal_text, EOS_TOKEN_ID: ""}),
        frozenset((0, 1, 11)), EOS_TOKEN_ID, TOKENIZER_IDENTITY,
        DECODER_IDENTITY, PROJECTOR_FREEZE_IDENTITY,
        decoder_mechanism_identity=DECODER_MECHANISM_IDENTITY)
    callback = bind_static_callback_preflight_v1_3(
        projector_preflight=bind_static_projector_preflight_v1_2(
            preflight=ConstructionObligationV2RunnerPreflightV1_1(request, bundle)))

    progress: list[tuple[str, bytes]] = []
    resource = object()
    cleanup_calls: list[object] = []

    def generate(observed, prompt_ids, maximum, allowed):
        assert observed is resource and prompt_ids == (7, 8) and maximum == 3200
        assert allowed((100,)) == (EOS_TOKEN_ID,)
        return InjectedGenerationOutputV1(
            terminal_text.encode(), (100, EOS_TOKEN_ID), True)

    child_result = supervise_injected_generation_v1_2_1(
        raw_policy_receipt=validate_generation_execution_policy_gate_v1(
            observed=canonical_observed_generation_execution_policy_v1()),
        raw_authority_receipt=raw_authority,
        expected_runner_request_sha256=hashlib.sha256(raw_request).hexdigest(),
        preload_observation=GenerationPreloadObservationV1_1(
            PACKAGE_IDENTITIES,
            "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
            "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
            "NVIDIA GeForce RTX 5080", 16303, 15000, "12.0", 0,
            "NF4_4BIT", True, "BF16"),
        callback_preflight=callback, rendered_prompt="synthetic exact-current prompt",
        operations=InjectedGenerationOperationsV1(
            lambda _: (7, 8),
            lambda: InjectedCompatibleGenerationResourceV1(
                resource, COMPATIBILITY.read_bytes()),
            generate, cleanup_calls.append),
        lifecycle_sink=lambda raw: progress.append(("lifecycle", raw)),
        compatibility_sink=lambda raw: progress.append(("compatibility", raw)),
        generation_progress_sink=lambda raw: progress.append(("generation_progress", raw)),
    )
    assert child_result.status == "TERMINAL_OUTPUT"
    assert cleanup_calls == [resource]

    handle = object()
    fake_child = InjectedChildProcessOperationsV1(
        lambda invocation: handle,
        lambda observed, timeout: None,
        lambda observed: False,
        lambda observed: pytest.fail("terminate must not be called"),
        lambda observed: pytest.fail("kill must not be called"),
        lambda observed: 0,
        lambda observed: child_result,
        lambda observed: tuple(progress),
    )
    monkeypatch.setattr(
        composition, "build_linux_child_process_operations_v1_2_1",
        lambda **kwargs: fake_child)
    outcome = composition.run_linux_generation_composition_v1_2_1(
        raw_policy_receipt=POLICY.read_bytes(), raw_authority_receipt=raw_authority,
        raw_runner_request=raw_request, system_prompt=SYSTEM_PROMPT.read_text("utf-8"),
        evidence_root=tmp_path / "terminal-success", timeout_seconds=1200.0)
    assert outcome.supervisor_outcome.status == "TERMINAL_OUTPUT"
    labels = tuple(receipt.label for receipt in outcome.durable_receipts)
    assert labels == tuple(label for label, _ in
                           outcome.supervisor_outcome.persisted_artifact_sha256)
    assert "raw-output.bin" in labels
    assert "adapter-compatibility-receipt.json" in labels
    assert "lifecycle-00005-cleanup-completed.json" in labels
    assert "result-envelope-v1-1.json" in labels
    assert "supervisor-receipt.json" in labels
