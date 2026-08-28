from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1 import (
    ConstructionObligationV2RunnerPreflightV1_1,
)
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import (
    bind_static_projector_preflight_v1_2,
)
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import (
    bind_static_callback_preflight_v1_3,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_authority_contract_v1 import (
    AUTHORITY_CONTRACT_IDENTITY,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    POLICY_GATE_IDENTITY,
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_supervisor_v1 import (
    SUPERVISOR_IDENTITY,
    supervise_injected_generation_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1 import (
    WORKER_IDENTITY,
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    DECODER_IDENTITY, EOS_TOKEN_ID, PROJECTOR_FREEZE_IDENTITY, TOKENIZER_IDENTITY,
    TokenPieceBundleV1,
)
from test_experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import preflight
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _valid_text


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-injected-generation-worker-supervisor-v1.json"
COMPATIBILITY = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-adapter-compatibility-validation-receipt-v1.json"
WORKER_SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_injected_generation_worker_v1.py"
SUPERVISOR_SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_injected_generation_supervisor_v1.py"


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":")) + "\n").encode()


def _bound(pieces):
    initial = preflight()
    bundle = TokenPieceBundleV1(
        MappingProxyType(pieces), frozenset((0, 1, 11)), EOS_TOKEN_ID,
        TOKENIZER_IDENTITY, DECODER_IDENTITY, PROJECTOR_FREEZE_IDENTITY,
    )
    base = ConstructionObligationV2RunnerPreflightV1_1(initial.request, bundle)
    return bind_static_callback_preflight_v1_3(
        projector_preflight=bind_static_projector_preflight_v1_2(preflight=base))


def _terminal_fixture():
    initial = preflight()
    context = bind_static_projector_preflight_v1_2(preflight=initial).projector.controller.tracker.context
    text = _valid_text(context)
    return _bound({100: text, EOS_TOKEN_ID: ""}), text, (100,)


def _authority(bound):
    request = bound.projector_preflight.preflight.request
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.0.0", "authority_contract_identity": AUTHORITY_CONTRACT_IDENTITY,
        "policy_gate_identity": POLICY_GATE_IDENTITY,
        "runner_protocol_identity": "cb9f14284353fafba05094b005f3a97793dbb079e5bed81abacddaafb7d155bf",
        "projector_freeze_identity": PROJECTOR_FREEZE_IDENTITY,
        "compatibility_receipt_identity": "8ddafa5e60e892abf56a2b67d9ab646deb94a7b024e739ea8ea967c45e3ec39f",
        "generation_candidate_identity": WORKER_IDENTITY,
        "owner_authority_identity": "synthetic-launch-forbidden-test",
        "host_payload_sha256": request.host_payload_sha256,
        "provider_request_id": request.provider_request_id,
        "source_context_identity": request.source_context_identity,
        "required_free_vram_mib": 14000, "attempt_ceiling": 1,
        "operation": "GENERATE_ONCE_STAGE_P_ONLY", "model_load_authorized": True,
        "generation_authorized": True, "prompt_token_ceiling": 8192,
        "output_token_ceiling": 3200, "retry_authorized": False,
        "fallback_authorized": False, "repair_authorized": False,
        "selection_authorized": False, "stage_c_authorized": False,
        "authority_receipt_identity": "",
    }
    value["authority_receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "authority_receipt_identity"}
    )).hexdigest()
    return _canonical(value)


def _policy():
    return validate_generation_execution_policy_gate_v1(
        observed=canonical_observed_generation_execution_policy_v1())


def _resource():
    return InjectedCompatibleGenerationResourceV1(object(), COMPATIBILITY.read_bytes())


def _events(result):
    return [json.loads(raw)["event"] for raw in result.lifecycle_events]


def test_terminal_success_uses_one_callback_and_cleanup() -> None:
    bound, text, generated = _terminal_fixture()
    calls = []

    def generate(resource, prompt_ids, maximum, allowed):
        calls.append(("generate", resource, maximum))
        assert allowed((*prompt_ids, *generated)) == (EOS_TOKEN_ID,)
        return InjectedGenerationOutputV1(text.encode(), (*generated, EOS_TOKEN_ID), True)

    result = supervise_injected_generation_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        callback_preflight=bound, rendered_prompt="synthetic prompt",
        operations=InjectedGenerationOperationsV1(
            lambda _: (900, 901), lambda: _resource(), generate,
            lambda resource: calls.append(("cleanup", resource))),
    )
    assert result.status == "TERMINAL_OUTPUT"
    assert _events(result) == [
        "MODEL_LOAD_STARTED", "MODEL_LOAD_COMPLETED", "GENERATION_STARTED",
        "TERMINAL_EOS", "CLEANUP_COMPLETED",
    ]
    typed = json.loads(result.runner_result)
    assert typed["status"] == "TERMINAL_OUTPUT" and typed["terminal_eos"] is True
    assert result.raw_output == text.encode() and result.raw_partial_output is None
    assert len([call for call in calls if call[0] == "generate"]) == 1
    assert len([call for call in calls if call[0] == "cleanup"]) == 1


def test_prompt_ceiling_and_identity_fail_before_load_or_generation() -> None:
    bound, _, _ = _terminal_fixture()
    calls = []
    operations = InjectedGenerationOperationsV1(
        lambda _: tuple(range(8193)), lambda: calls.append("load"),
        lambda *args: calls.append("generate"), lambda _: calls.append("cleanup"))
    with pytest.raises(ValueError, match="PROMPT_TOKEN_CEILING"):
        supervise_injected_generation_v1(
            raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
            callback_preflight=bound, rendered_prompt="x", operations=operations)
    with pytest.raises(ValueError, match="POLICY_RECEIPT_MISMATCH"):
        supervise_injected_generation_v1(
            raw_policy_receipt=_policy() + b"x", raw_authority_receipt=_authority(bound),
            callback_preflight=bound, rendered_prompt="x", operations=operations)
    assert calls == []


def test_compatibility_mismatch_fails_before_generation_and_cleans_once() -> None:
    bound, _, _ = _terminal_fixture()
    resource = object(); calls = []
    bad = COMPATIBILITY.read_bytes().replace(b"336", b"335", 1)
    result = supervise_injected_generation_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        callback_preflight=bound, rendered_prompt="x",
        operations=InjectedGenerationOperationsV1(
            lambda _: (1,), lambda: InjectedCompatibleGenerationResourceV1(resource, bad),
            lambda *args: calls.append("generate"),
            lambda value: calls.append(("cleanup", value))),
    )
    assert result.status == "EXECUTION_FAILURE"
    assert "GENERATION_STARTED" not in _events(result)
    assert calls == [("cleanup", resource)]


def test_no_legal_token_is_liveness_only_with_bound_receipt() -> None:
    bound = _bound({EOS_TOKEN_ID: "", 20: "x"})
    resource = object(); calls = []

    def generate(_resource_value, prompt_ids, _maximum, allowed):
        allowed(prompt_ids)
        raise AssertionError("unreachable")

    result = supervise_injected_generation_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        callback_preflight=bound, rendered_prompt="x",
        operations=InjectedGenerationOperationsV1(
            lambda _: (8, 9), lambda: InjectedCompatibleGenerationResourceV1(
                resource, COMPATIBILITY.read_bytes()), generate,
            lambda value: calls.append(value)),
    )
    assert result.status == "CONSTRAINT_LIVENESS_FAILURE"
    assert json.loads(result.runner_result)["status"] == "CONSTRAINT_LIVENESS_FAILURE"
    assert result.raw_output is result.raw_partial_output is None
    assert calls == [resource]


def test_partial_output_has_no_semantic_authority_and_cleanup_failure_is_terminal() -> None:
    bound, text, generated = _terminal_fixture()

    def partial(_resource, prompt_ids, _maximum, allowed):
        assert allowed((*prompt_ids, *generated)) == (EOS_TOKEN_ID,)
        return InjectedGenerationOutputV1(text.encode(), generated, False)

    result = supervise_injected_generation_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        callback_preflight=bound, rendered_prompt="x",
        operations=InjectedGenerationOperationsV1(
            lambda _: (1, 2), lambda: _resource(), partial, lambda _: None),
    )
    assert result.status == "EXECUTION_FAILURE"
    assert result.raw_output is None and result.raw_partial_output == text.encode()
    assert json.loads(result.runner_result)["output_utf8_base64"] is None

    bound, text, generated = _terminal_fixture()
    result = supervise_injected_generation_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        callback_preflight=bound, rendered_prompt="x",
        operations=InjectedGenerationOperationsV1(
            lambda _: (1, 2), lambda: _resource(),
            lambda resource, prompt, maximum, allowed: (
                allowed((*prompt, *generated)) and
                InjectedGenerationOutputV1(text.encode(), (*generated, EOS_TOKEN_ID), True)
            ),
            lambda _: (_ for _ in ()).throw(RuntimeError("synthetic cleanup"))),
    )
    assert result.status == "EXECUTION_FAILURE"
    assert json.loads(result.cleanup_receipt)["cleanup_status"] == "CLEANUP_FAILED"
    assert json.loads(result.runner_result)["output_utf8_base64"] is None


def test_sources_are_launch_forbidden_and_artifact_identities_are_exact() -> None:
    text = WORKER_SOURCE.read_text("utf-8") + SUPERVISOR_SOURCE.read_text("utf-8")
    modules = {
        node.module for node in ast.walk(ast.parse(text))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not modules.intersection({"transformers", "torch", "peft", "subprocess", "importlib"})
    assert all(term not in text for term in (
        "from_pretrained", ".generate(", "build_invocation", ".execute(",
        "Popen", "wsl.exe", "if __name__", "AutoTokenizer", "AutoModel",
    ))
    artifact = json.loads(ARTIFACT.read_text("utf-8"))
    worker = artifact["worker"]
    supervisor = artifact["supervisor"]
    assert hashlib.sha256("\n".join(worker["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest() == WORKER_IDENTITY
    assert hashlib.sha256("\n".join(supervisor["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest() == SUPERVISOR_IDENTITY
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "source_candidate_normalization")
