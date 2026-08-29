"""Zero-execution materialization of the current Case 01 V1.2.1 issuance packet."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.wsl_execution_v1 import (
    canonical_model_profile_v1,
    windows_path_to_wsl_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_p_construction_obligation_v2_application_request_v1 import (
    build_construction_obligation_v2_application_request_v1,
)
from .stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import (
    AUTHORITY_CONTRACT_V1_IDENTITY,
    AUTHORITY_PRELOAD_IDENTITY,
    POLICY_GATE_IDENTITY,
    SUPERVISOR_IDENTITY,
    WORKER_IDENTITY,
    WSL_PROFILE_IDENTITY,
)
from .stage_p_construction_obligation_v2_generation_v1_2_1_identity_contract import (
    COMPOSITION_IDENTITY, HOST_EXECUTOR_IDENTITY, RUNNER_IDENTITY,
    WSL_BINDING_IDENTITY,
)
from .stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_2_1 import (
    RUNNER_MODULE,
)
from .stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import (
    build_construction_obligation_v2_host_wsl_payload_v1,
    parse_construction_obligation_v2_host_wsl_payload_v1,
)
from .stage_p_construction_obligation_v2_projector_binding_v1 import (
    prepare_construction_obligation_v2_projector_binding_v1,
)
from .stage_p_construction_obligation_v2_provider_execution_request_binding_v1 import (
    bind_construction_obligation_v2_provider_execution_request_v1,
)
from .stage_p_construction_obligation_v2_request_renderer_v1 import (
    ConstructionObligationV2RequestRendererV1,
)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    build_runner_request_v1,
    parse_runner_request_v1,
)
from .stage_p_construction_obligation_v2_static_executor_binding_v1 import (
    bind_construction_obligation_v2_static_executor_v1,
)
from .stage_p_construction_obligation_v2_static_payload_binding_v1 import (
    build_construction_obligation_v2_static_payload_v1,
)

CASE_ID = "HMCV1-SASC-01"
SOURCE_CONTEXT_IDENTITY = "2ba2c7dcb5c8e19350a3acf37ed9d9c9daf6d058fc38811d06d3460825e9b610"
CASE_PACK_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json")
CASE_PACK_SHA256 = "4163307ccb8cfa8997b520a1cea04cddacd347e9b1ffde498db925ffccac6c2d"
REQUESTED_AT = datetime(2026, 8, 29, 10, 0, tzinfo=UTC)
PACKET_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-"
    "case01-successor-issuance-packet-v1-2-1-authority-plan-bound")
EVIDENCE_RELATIVE = Path(
    ".semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-v1-2-1-authority-plan-bound-evidence")
SYSTEM_PROMPT_RELATIVE = Path(
    ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/"
    "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt")
POLICY_RECEIPT_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-"
    "generation-policy-validation-receipt-v1.json")


def materialize_case01_issuance_packet_v1_2_1(
    *, project_root: Path,
    deployment_root: Path = Path(r"C:\Projects\pastila-news-monitor"),
) -> dict[str, bytes]:
    """Return deterministic packet files; write, issue, launch, or load nothing."""
    root = project_root.resolve(strict=True)
    if not deployment_root.is_absolute():
        raise ValueError("CASE01_DEPLOYMENT_ROOT_ABSOLUTE_REQUIRED")
    pack_raw = (root / CASE_PACK_RELATIVE).read_bytes()
    if hashlib.sha256(pack_raw).hexdigest() != CASE_PACK_SHA256:
        raise RuntimeError("CASE01_CURRENT_PACK_IDENTITY_DRIFT")
    pack = json.loads(pack_raw.decode("utf-8", errors="strict"))
    eligible = [item for item in pack.get("cases", ()) if item.get("case_id") == CASE_ID]
    if len(eligible) != 1:
        raise RuntimeError("CASE01_CURRENT_SOURCE_NOT_UNIQUE")
    case = eligible[0]
    candidate = case["candidate"].encode("utf-8")
    factual = case["factual_summary"].encode("utf-8")
    if (hashlib.sha256(candidate).hexdigest() != case["candidate_sha256"] or
            hashlib.sha256(factual).hexdigest() != case["factual_summary_sha256"]):
        raise RuntimeError("CASE01_CURRENT_SOURCE_HASH_DRIFT")
    source = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate, factual_authority_utf8=factual)
    if source.source_context_identity != SOURCE_CONTEXT_IDENTITY:
        raise RuntimeError("CASE01_CURRENT_SOURCE_CONTEXT_DRIFT")
    static = build_construction_obligation_v2_static_payload_v1(source_binding=source)
    rendered = ConstructionObligationV2RequestRendererV1(project_root=root).render(
        canonical_static_payload=static)
    application = build_construction_obligation_v2_application_request_v1(
        rendered_request=rendered, requested_at=REQUESTED_AT)
    execution = bind_construction_obligation_v2_provider_execution_request_v1(
        candidate=application)
    host_raw = build_construction_obligation_v2_host_wsl_payload_v1(
        execution_binding=execution, rendered_request=rendered,
        canonical_static_payload=static, max_output_tokens=3200)
    parse_construction_obligation_v2_host_wsl_payload_v1(raw_payload=host_raw)
    static_executor = bind_construction_obligation_v2_static_executor_v1(
        project_root=root, raw_host_payload=host_raw,
        wsl_boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1()))
    runner_raw = build_runner_request_v1(
        raw_host_payload=host_raw, static_binding=static_executor)
    runner = parse_runner_request_v1(raw_request=runner_raw)
    runner_sha = hashlib.sha256(runner_raw).hexdigest()
    if runner.source_context_identity != SOURCE_CONTEXT_IDENTITY:
        raise RuntimeError("CASE01_RUNNER_SOURCE_CONTEXT_DRIFT")
    packet_root = deployment_root / PACKET_RELATIVE
    evidence_root = deployment_root / EVIDENCE_RELATIVE
    if evidence_root.exists() or evidence_root.is_symlink():
        raise FileExistsError("CASE01_V1_2_SUCCESSOR_EVIDENCE_ROOT_NOT_EXCLUSIVE")
    receipt_path = packet_root / "authority-receipt-issued.json"
    boundary = WslExecutionBoundaryV1_1(
        canonical_model_profile_v1(with_pydantic_bridge=True))
    arguments = (
        "-m", RUNNER_MODULE,
        windows_path_to_wsl_v1(deployment_root / POLICY_RECEIPT_RELATIVE),
        windows_path_to_wsl_v1(receipt_path),
        windows_path_to_wsl_v1(packet_root / "runner-request.json"),
        windows_path_to_wsl_v1(deployment_root / SYSTEM_PROMPT_RELATIVE),
        windows_path_to_wsl_v1(evidence_root / "linux-generation"),
    )
    command_plan = boundary.build_invocation(
        consumer_id="construction-obligation-v2-generation-v1-2-1",
        authority_reference="0" * 64, arguments=arguments)
    application_value = {
        "schema_name": "pastila-construction-obligation-v2-application-provider-request",
        "schema_version": "1.2.1", "case_id": CASE_ID,
        "application_request_identity": application.application_request_identity,
        "provider": application.application_request.provider.value,
        "prompt_utf8_base64": base64.b64encode(
            application.application_request.prompt.encode()).decode("ascii"),
        "request_reference": application.application_request.request_reference,
        "requested_at": application.application_request.requested_at.isoformat(),
        "timeout_seconds": application.application_request.timeout_policy.timeout_seconds,
        "cancellation_requested": False,
    }
    static_value = {key: value for key, value in asdict(static_executor).items()
                    if key != "_wsl_boundary"}
    rendered_bytes = rendered.rendered_prompt.encode("utf-8")
    rendered_value = {
        "schema_name": "pastila-construction-obligation-v2-rendered-prompt-bytes",
        "schema_version": "1.0.0", "rendered_request_identity": rendered.request_identity,
        "rendered_prompt_sha256": hashlib.sha256(rendered_bytes).hexdigest(),
        "rendered_prompt_utf8_bytes": len(rendered_bytes),
        "rendered_prompt_utf8_base64": base64.b64encode(rendered_bytes).decode("ascii"),
    }
    files = {
        "application-provider-request.json": _canonical(application_value),
        "rendered-prompt.json": _canonical(rendered_value), "host-payload.json": host_raw,
        "static-executor-binding.json": _canonical(static_value),
        "runner-request.json": runner_raw,
    }
    plan_file_hashes = {name: hashlib.sha256(raw).hexdigest()
                        for name, raw in files.items()}
    packet_plan_identity = _packet_plan_identity(
        packet_root=packet_root, evidence_root=evidence_root,
        command_plan_identity=command_plan.command_identity,
        source_context_identity=SOURCE_CONTEXT_IDENTITY,
        plan_file_hashes=plan_file_hashes)
    authority_body = _authority_body(
        host_sha=runner.host_payload_sha256, runner_sha=runner_sha,
        provider_request_id=runner.provider_request_id,
        packet_plan_identity=packet_plan_identity,
        command_plan_identity=command_plan.command_identity)
    proposed_receipt_identity = hashlib.sha256(_canonical(authority_body)).hexdigest()
    invocation = boundary.build_invocation(
            consumer_id="construction-obligation-v2-generation-v1-2-1",
            authority_reference=proposed_receipt_identity,
            arguments=arguments)
    candidate_value = {
        "schema_name": "pastila-construction-obligation-v2-generation-authority-candidate",
        "schema_version": "1.2.1", "receipt_status": "UNISSUED",
        "proposed_receipt_identity": proposed_receipt_identity,
        "authority_receipt_identity": None, "authority_body": authority_body,
    }
    files["authority-receipt-candidate.json"] = _canonical(candidate_value)
    file_hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()}
    evidence_root_identity = hashlib.sha256("\n".join((
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_CASE01_V1_2_1_AUTHORITY_PLAN_BOUND_EVIDENCE_ROOT",
        SOURCE_CONTEXT_IDENTITY, invocation.command_identity, str(evidence_root),
    )).encode()).hexdigest()
    manifest = {
        "schema_name": "pastila-construction-obligation-v2-case01-issuance-packet",
        "schema_version": "1.2.1", "case_id": CASE_ID,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "historical_request_reused": False, "receipt_status": "UNISSUED",
        "attempts": {"completed": 0, "ceiling": 1},
        "proposed_evidence_root": str(evidence_root),
        "evidence_root_identity": evidence_root_identity,
        "evidence_root_exclusive_at_materialization": True,
        "command": list(invocation.command),
        "command_identity": invocation.command_identity,
        "command_plan_identity": command_plan.command_identity,
        "packet_plan_identity": packet_plan_identity,
        "authority_reference_if_issued": proposed_receipt_identity,
        "file_sha256": file_hashes,
        "limits": {"attempt_ceiling": 1, "prompt_token_ceiling": 8192,
                   "output_token_ceiling": 3200, "minimum_free_vram_mib": 14000,
                   "retry": 0, "fallback": 0, "repair": 0, "selection": 0,
                   "stage_c": False},
        "execution": {"receipt_issued": False, "execute_called": False,
                      "wsl_launched": False, "model_loaded": False,
                      "generation_started": False},
        "packet_identity": "",
    }
    manifest["packet_identity"] = hashlib.sha256(_canonical(
        {key: value for key, value in manifest.items() if key != "packet_identity"}
    )).hexdigest()
    files["manifest.json"] = _canonical(manifest)
    return files


def _authority_body(*, host_sha: str, runner_sha: str, provider_request_id: str,
                    packet_plan_identity: str,
                    command_plan_identity: str) -> dict[str, object]:
    return {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "schema_version": "1.2.1", "authority_preload_identity": AUTHORITY_PRELOAD_IDENTITY,
        "authority_contract_v1_identity": AUTHORITY_CONTRACT_V1_IDENTITY,
        "policy_gate_identity": POLICY_GATE_IDENTITY,
        "supervisor_identity": SUPERVISOR_IDENTITY, "worker_identity": WORKER_IDENTITY,
        "composition_identity": COMPOSITION_IDENTITY, "runner_identity": RUNNER_IDENTITY,
        "wsl_binding_identity": WSL_BINDING_IDENTITY,
        "host_executor_identity": HOST_EXECUTOR_IDENTITY,
        "wsl_profile_identity": WSL_PROFILE_IDENTITY,
        "owner_authority_identity": "owner-selection:construction-obligation-case01:2026-08-28",
        "host_payload_sha256": host_sha, "runner_request_sha256": runner_sha,
        "provider_request_id": provider_request_id,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "packet_plan_identity": packet_plan_identity,
        "command_plan_identity": command_plan_identity,
        "required_free_vram_mib": 14000, "attempt_ceiling": 1,
        "operation": "GENERATE_ONCE_STAGE_P_ONLY", "model_load_authorized": True,
        "generation_authorized": True, "prompt_token_ceiling": 8192,
        "output_token_ceiling": 3200, "retry_authorized": False,
        "fallback_authorized": False, "repair_authorized": False,
        "selection_authorized": False, "stage_c_authorized": False,
    }


def _packet_plan_identity(*, packet_root: Path, evidence_root: Path,
                          command_plan_identity: str, source_context_identity: str,
                          plan_file_hashes: dict[str, str]) -> str:
    value = {
        "schema": "STAGE_P_CONSTRUCTION_OBLIGATION_V2_PACKET_PLAN_V1_2_1",
        "packet_root": str(packet_root), "evidence_root": str(evidence_root),
        "source_context_identity": source_context_identity,
        "wsl_binding_identity": WSL_BINDING_IDENTITY,
        "command_plan_identity": command_plan_identity,
        "plan_file_sha256": plan_file_hashes,
    }
    return hashlib.sha256(_canonical(value)).hexdigest()


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "CASE_ID", "EVIDENCE_RELATIVE", "PACKET_RELATIVE", "SOURCE_CONTEXT_IDENTITY",
    "materialize_case01_issuance_packet_v1_2_1",
)
