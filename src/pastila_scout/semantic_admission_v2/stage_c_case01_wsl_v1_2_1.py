"""Stage C Case 01 V1.2.1 packet, prepared invocation, and exact host boundary."""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from pastila_scout.wsl_execution_v1 import (
    WslExecutionResultV1, WslInvocationV1, canonical_model_profile_v1,
    canonical_receipt_bytes_v1, windows_path_to_wsl_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_c_case01_frozen_input_v1_2_1 import (
    CASE_ID, CLOSURE_COMMIT, CLOSURE_RECEIPT_IDENTITY, EVALUATION_COMMIT,
    EVALUATION_RECEIPT_IDENTITY, EVIDENCE_COMMIT, EXPECTED_TOPOLOGY,
    RAW_OUTPUT_SHA256, SOURCE_CONTEXT_IDENTITY,
    admit_frozen_stage_c_case01_input_v1_2_1,
)
from .stage_p_construction_obligation_semantic_completeness_v1 import (
    CASE01_CANONICAL_POLICY_IDENTITY,
)

RUNNER_MODULE = "pastila_scout.semantic_admission_v2.stage_c_case01_linux_runner_v1_2_1"
CONSUMER_ID = "semantic-admission-v2-stage-c-case01-v1-2-1"
TIMEOUT_SECONDS = 1260.0
CHILD_TIMEOUT_SECONDS = 1200.0
PACKET_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-stage-c-case01-successor-v1-2-1-"
    "canonical-response-bound")
EVIDENCE_RELATIVE = Path(
    ".semantic-admission-v2-stage-c-case01-successor-v1-2-1-canonical-response-bound-evidence")
CASE_PACK_RELATIVE = Path("docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json")
RAW_LEDGER_RELATIVE = Path(
    ".semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-"
    "v1-2-1-creative-semantics-pruning-bound-evidence/linux-generation/raw-output.bin")
EVALUATION_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-case01-creative-semantics-pruning-bound-"
    "semantic-evaluation-v1.json")
CLOSURE_RELATIVE = Path(
    "docs/artifacts/semantic-admission-v2-case01-creative-semantics-pruning-bound-closure-v1.json")

STAGE_C_WSL_BINDING_IDENTITY = hashlib.sha256("\n".join((
    "STAGE_C_CASE01_WSL_BINDING_V1_2_1", "frozen-stage-p-input-only",
    "stage-p-call-count:0", "prepared-exact-type:v1.2.1",
    "manifest-canonical-file-set-bound", "authority:stage-c-only",
    "host-independent-revalidation", "single-execute-edge",
    "child-timeout:1200", "host-timeout:1260",
)).encode()).hexdigest()
STAGE_C_HOST_IDENTITY = hashlib.sha256("\n".join((
    "STAGE_C_CASE01_HOST_V1_2_1", STAGE_C_WSL_BINDING_IDENTITY,
    "durable-streams-before-reconciliation", "retry-fallback-repair-selection:0",
)).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PreparedStageCCase01WslInvocationV1_2_1:
    invocation_identity: str
    binding_identity: str
    invocation: WslInvocationV1
    authority_receipt_identity: str
    packet_identity: str
    packet_plan_identity: str
    command_identity: str
    frozen_input_identity: str
    source_context_identity: str
    semantic_policy_identity: str
    raw_output_sha256: str
    evidence_root_identity: str
    manifest_path: Path
    request_path: Path
    authority_path: Path
    evidence_root: Path
    project_root: Path
    issuance_commit: str


@dataclass(frozen=True, slots=True)
class StageCCase01HostOutcomeV1_2_1:
    transport: WslExecutionResultV1
    stdout_sha256: str
    stderr_sha256: str
    reconciliation_identity: str


def materialize_stage_c_case01_packet_v1_2_1(
    *, project_root: Path,
    deployment_root: Path = Path(r"C:\Projects\pastila-news-monitor"),
) -> dict[str, bytes]:
    """Return deterministic UNISSUED packet bytes; perform no execution or issuance."""
    root = project_root.resolve(strict=True)
    if not deployment_root.is_absolute():
        raise ValueError("STAGE_C_DEPLOYMENT_ROOT_ABSOLUTE_REQUIRED")
    pack = json.loads((root / CASE_PACK_RELATIVE).read_text("utf-8"))
    cases = [item for item in pack.get("cases", ()) if item.get("case_id") == CASE_ID]
    if len(cases) != 1:
        raise ValueError("STAGE_C_CASE01_SOURCE_NOT_UNIQUE")
    candidate = cases[0]["candidate"].encode("utf-8")
    authority = cases[0]["factual_summary"].encode("utf-8")
    raw_ledger = _git_blob(root, EVIDENCE_COMMIT, RAW_LEDGER_RELATIVE)
    raw_evaluation = _git_blob(root, EVALUATION_COMMIT, EVALUATION_RELATIVE)
    raw_closure = _git_blob(root, CLOSURE_COMMIT, CLOSURE_RELATIVE)
    frozen = admit_frozen_stage_c_case01_input_v1_2_1(
        raw_ledger=raw_ledger, candidate=candidate, factual_authority=authority,
        raw_evaluation_receipt=raw_evaluation, raw_closure_receipt=raw_closure)
    packet_root = deployment_root / PACKET_RELATIVE
    evidence_root = deployment_root / EVIDENCE_RELATIVE
    if evidence_root.exists() or evidence_root.is_symlink():
        raise FileExistsError("STAGE_C_EVIDENCE_ROOT_NOT_EXCLUSIVE")
    request = {
        "schema_name": "pastila-semantic-admission-v2-stage-c-case01-request",
        "schema_version": "1.2.1", "case_id": CASE_ID,
        "operation": "EVALUATE_FROZEN_STAGE_P_LEDGER_ONCE",
        "stage_p_calls_authorized": 0, "stage_c_calls_authorized": 1,
        "frozen_input_identity": frozen.binding_identity,
        "evidence_commit": EVIDENCE_COMMIT, "evaluation_commit": EVALUATION_COMMIT,
        "closure_commit": CLOSURE_COMMIT, "raw_output_sha256": RAW_OUTPUT_SHA256,
        "evaluation_receipt_identity": EVALUATION_RECEIPT_IDENTITY,
        "closure_receipt_identity": CLOSURE_RECEIPT_IDENTITY,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "semantic_policy_identity": CASE01_CANONICAL_POLICY_IDENTITY,
        "topology": EXPECTED_TOPOLOGY,
        "candidate_utf8_base64": base64.b64encode(candidate).decode("ascii"),
        "factual_authority_utf8_base64": base64.b64encode(authority).decode("ascii"),
        "frozen_ledger_sha256": RAW_OUTPUT_SHA256,
        "child_timeout_seconds": CHILD_TIMEOUT_SECONDS,
        "retry": 0, "fallback": 0, "repair": 0, "selection": 0,
    }
    files = {
        "stage-c-request.json": _canonical(request),
        "frozen-stage-p-ledger.json": raw_ledger,
        "semantic-evaluation-receipt.json": raw_evaluation,
        "case01-closure-receipt.json": raw_closure,
    }
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    args = ("-m", RUNNER_MODULE,
            windows_path_to_wsl_v1(packet_root / "stage-c-request.json"),
            windows_path_to_wsl_v1(packet_root / "authority-receipt-issued.json"),
            windows_path_to_wsl_v1(packet_root / "frozen-stage-p-ledger.json"),
            windows_path_to_wsl_v1(evidence_root / "linux-stage-c"))
    plan_invocation = boundary.build_invocation(
        consumer_id=CONSUMER_ID, authority_reference="0" * 64, arguments=args)
    source_lineage = _source_lineage(root)
    plan = {
        "schema": "STAGE_C_CASE01_PACKET_PLAN_V1_2_1",
        "packet_root": str(packet_root), "evidence_root": str(evidence_root),
        "frozen_input_identity": frozen.binding_identity,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "semantic_policy_identity": CASE01_CANONICAL_POLICY_IDENTITY,
        "wsl_binding_identity": STAGE_C_WSL_BINDING_IDENTITY,
        "host_identity": STAGE_C_HOST_IDENTITY,
        "command_plan_identity": plan_invocation.command_identity,
        "source_lineage_sha256": source_lineage,
        "plan_file_sha256": {name: _sha(raw) for name, raw in sorted(files.items())},
    }
    packet_plan_identity = _sha(_canonical(plan))
    authority_body = {
        "schema_name": "pastila-semantic-admission-v2-stage-c-case01-authority",
        "schema_version": "1.2.1", "case_id": CASE_ID,
        "operation": "EVALUATE_FROZEN_STAGE_P_LEDGER_ONCE",
        "stage_p_authorized": False, "stage_c_authorized": True,
        "attempt_ceiling": 1, "retry_authorized": False,
        "fallback_authorized": False, "repair_authorized": False,
        "selection_authorized": False,
        "frozen_input_identity": frozen.binding_identity,
        "raw_output_sha256": RAW_OUTPUT_SHA256,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "semantic_policy_identity": CASE01_CANONICAL_POLICY_IDENTITY,
        "evaluation_receipt_identity": EVALUATION_RECEIPT_IDENTITY,
        "closure_receipt_identity": CLOSURE_RECEIPT_IDENTITY,
        "packet_plan_identity": packet_plan_identity,
        "command_plan_identity": plan_invocation.command_identity,
        "wsl_binding_identity": STAGE_C_WSL_BINDING_IDENTITY,
        "host_identity": STAGE_C_HOST_IDENTITY,
    }
    proposed = _sha(_canonical(authority_body))
    invocation = boundary.build_invocation(
        consumer_id=CONSUMER_ID, authority_reference=proposed, arguments=args)
    candidate_receipt = {
        "schema_name": "pastila-semantic-admission-v2-stage-c-case01-authority-candidate",
        "schema_version": "1.2.1", "receipt_status": "UNISSUED",
        "proposed_receipt_identity": proposed,
        "authority_receipt_identity": None, "authority_body": authority_body,
    }
    files["authority-receipt-candidate.json"] = _canonical(candidate_receipt)
    host_binding = {
        "schema_name": "pastila-semantic-admission-v2-stage-c-case01-host-binding",
        "schema_version": "1.2.1", "binding_identity": STAGE_C_WSL_BINDING_IDENTITY,
        "host_identity": STAGE_C_HOST_IDENTITY,
        "command": list(invocation.command), "command_identity": invocation.command_identity,
        "packet_plan_identity": packet_plan_identity,
        "frozen_input_identity": frozen.binding_identity,
        "source_lineage_sha256": source_lineage,
        "timeouts": {"linux_child": CHILD_TIMEOUT_SECONDS, "host_wsl": TIMEOUT_SECONDS},
        "prospective_execute_edges": 1, "observed_execute_calls": 0,
    }
    files["host-binding.json"] = _canonical(host_binding)
    evidence_identity = _sha(_canonical({
        "schema": "STAGE_C_CASE01_EVIDENCE_ROOT_V1_2_1",
        "path": str(evidence_root), "command_identity": invocation.command_identity,
        "frozen_input_identity": frozen.binding_identity,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
    }))
    manifest = {
        "schema_name": "pastila-semantic-admission-v2-stage-c-case01-packet",
        "schema_version": "1.2.1", "case_id": CASE_ID,
        "receipt_status": "UNISSUED", "attempts": {"completed": 0, "ceiling": 1},
        "execution": {"receipt_issued": False, "execute_called": False,
                      "wsl_launched": False, "model_loaded": False,
                      "stage_c_started": False},
        "stage_p_calls_authorized": 0, "stage_c_calls_authorized": 1,
        "packet_plan_identity": packet_plan_identity,
        "command": list(invocation.command), "command_identity": invocation.command_identity,
        "authority_reference_if_issued": proposed,
        "frozen_input_identity": frozen.binding_identity,
        "raw_output_sha256": RAW_OUTPUT_SHA256,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "semantic_policy_identity": CASE01_CANONICAL_POLICY_IDENTITY,
        "evaluation_receipt_identity": EVALUATION_RECEIPT_IDENTITY,
        "closure_receipt_identity": CLOSURE_RECEIPT_IDENTITY,
        "topology": EXPECTED_TOPOLOGY,
        "proposed_evidence_root": str(evidence_root),
        "evidence_root_identity": evidence_identity,
        "source_lineage_sha256": source_lineage,
        "file_sha256": {name: _sha(raw) for name, raw in sorted(files.items())},
        "limits": {"attempt_ceiling": 1, "child_timeout_seconds": CHILD_TIMEOUT_SECONDS,
                   "host_timeout_seconds": TIMEOUT_SECONDS, "retry": 0,
                   "fallback": 0, "repair": 0, "selection": 0},
        "packet_identity": "",
    }
    manifest["packet_identity"] = _sha(_canonical(
        {key: value for key, value in manifest.items() if key != "packet_identity"}))
    files["manifest.json"] = _canonical(manifest)
    return files


def prepare_stage_c_case01_wsl_invocation_v1_2_1(
    *, project_root: Path, packet_root: Path, evidence_root: Path,
    boundary: WslExecutionBoundaryV1_1,
) -> PreparedStageCCase01WslInvocationV1_2_1:
    if type(boundary) is not WslExecutionBoundaryV1_1:
        raise TypeError("STAGE_C_CANONICAL_WSL_BOUNDARY_EXACT_TYPE_REQUIRED")
    if boundary.profile != canonical_model_profile_v1(with_pydantic_bridge=True):
        raise ValueError("STAGE_C_CANONICAL_WSL_PROFILE_REQUIRED")
    source_root = project_root.resolve(strict=True)
    manifest, authority, request, frozen, issuance_commit = _validate_issued_packet(
        source_root, packet_root, evidence_root, boundary)
    args = ("-m", RUNNER_MODULE, windows_path_to_wsl_v1(packet_root / "stage-c-request.json"),
            windows_path_to_wsl_v1(packet_root / "authority-receipt-issued.json"),
            windows_path_to_wsl_v1(packet_root / "frozen-stage-p-ledger.json"),
            windows_path_to_wsl_v1(evidence_root / "linux-stage-c"))
    invocation = boundary.build_invocation(
        consumer_id=CONSUMER_ID, authority_reference=authority["authority_receipt_identity"],
        arguments=args)
    if invocation.command_identity != manifest["command_identity"] or list(invocation.command) != manifest["command"]:
        raise ValueError("STAGE_C_COMMAND_BINDING_MISMATCH")
    material = {
        "schema": "PREPARED_STAGE_C_CASE01_WSL_INVOCATION_V1_2_1",
        "binding_identity": STAGE_C_WSL_BINDING_IDENTITY,
        "command_identity": invocation.command_identity,
        "authority_receipt_identity": authority["authority_receipt_identity"],
        "packet_identity": manifest["packet_identity"],
        "packet_plan_identity": manifest["packet_plan_identity"],
        "frozen_input_identity": frozen.binding_identity,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "semantic_policy_identity": CASE01_CANONICAL_POLICY_IDENTITY,
        "raw_output_sha256": RAW_OUTPUT_SHA256,
        "evidence_root_identity": manifest["evidence_root_identity"],
        "manifest_path": str(packet_root / "manifest.json"),
        "evidence_root": str(evidence_root),
        "project_root": str(source_root),
        "issuance_commit": issuance_commit,
    }
    return PreparedStageCCase01WslInvocationV1_2_1(
        _sha(_canonical(material)), STAGE_C_WSL_BINDING_IDENTITY, invocation,
        authority["authority_receipt_identity"], manifest["packet_identity"],
        manifest["packet_plan_identity"], invocation.command_identity,
        frozen.binding_identity, SOURCE_CONTEXT_IDENTITY,
        CASE01_CANONICAL_POLICY_IDENTITY, RAW_OUTPUT_SHA256,
        manifest["evidence_root_identity"], packet_root / "manifest.json",
        packet_root / "stage-c-request.json", packet_root / "authority-receipt-issued.json",
        evidence_root, source_root, issuance_commit)


def execute_stage_c_case01_host_v1_2_1(
    *, prepared: PreparedStageCCase01WslInvocationV1_2_1,
    boundary: WslExecutionBoundaryV1_1,
) -> StageCCase01HostOutcomeV1_2_1:
    if type(prepared) is not PreparedStageCCase01WslInvocationV1_2_1:
        raise TypeError("PREPARED_STAGE_C_CASE01_WSL_INVOCATION_V1_2_1_REQUIRED")
    if type(boundary) is not WslExecutionBoundaryV1_1:
        raise TypeError("STAGE_C_CANONICAL_WSL_BOUNDARY_EXACT_TYPE_REQUIRED")
    rebuilt = prepare_stage_c_case01_wsl_invocation_v1_2_1(
        project_root=prepared.project_root,
        packet_root=prepared.manifest_path.parent,
        evidence_root=prepared.evidence_root, boundary=boundary)
    if rebuilt != prepared:
        raise ValueError("STAGE_C_PREPARED_INVOCATION_REVALIDATION_MISMATCH")
    if prepared.evidence_root.exists() or prepared.evidence_root.is_symlink():
        raise FileExistsError("STAGE_C_EVIDENCE_ROOT_ALREADY_EXISTS")
    prepared.evidence_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    result = boundary.execute(prepared.invocation, timeout_seconds=TIMEOUT_SECONDS)
    if type(result) is not WslExecutionResultV1:
        raise TypeError("STAGE_C_WSL_RESULT_EXACT_TYPE_REQUIRED")
    stdout, stderr = result.stdout.encode("utf-8"), result.stderr.encode("utf-8")
    _exclusive(prepared.evidence_root / "wsl-stdout.bin", stdout)
    _exclusive(prepared.evidence_root / "wsl-stderr.bin", stderr)
    _exclusive(prepared.evidence_root / "wsl-execution-receipt.json", canonical_receipt_bytes_v1(result.receipt))
    body = {"schema_name": "pastila-semantic-admission-v2-stage-c-host-reconciliation",
            "schema_version": "1.2.1", "host_identity": STAGE_C_HOST_IDENTITY,
            "invocation_identity": prepared.invocation_identity,
            "authority_receipt_identity": prepared.authority_receipt_identity,
            "stdout_sha256": _sha(stdout), "stderr_sha256": _sha(stderr),
            "succeeded": result.succeeded, "retry_count": 0}
    identity = _sha(_canonical(body))
    _exclusive(prepared.evidence_root / "host-reconciliation.json",
               _canonical({**body, "reconciliation_identity": identity}))
    return StageCCase01HostOutcomeV1_2_1(result, _sha(stdout), _sha(stderr), identity)


def _validate_issued_packet(project_root: Path, packet_root: Path, evidence_root: Path,
                            boundary: WslExecutionBoundaryV1_1):
    root = packet_root.resolve(strict=True)
    if root != packet_root or evidence_root.exists() or evidence_root.is_symlink():
        raise ValueError("STAGE_C_PACKET_OR_EVIDENCE_PATH_INVALID")
    expected = {"stage-c-request.json", "frozen-stage-p-ledger.json",
                "semantic-evaluation-receipt.json", "case01-closure-receipt.json",
                "authority-receipt-candidate.json", "host-binding.json", "manifest.json",
                "authority-receipt-issued.json"}
    if {path.name for path in root.iterdir()} != expected:
        raise ValueError("STAGE_C_PACKET_FILE_SET_INVALID")
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file():
            raise ValueError("STAGE_C_PACKET_REGULAR_FILES_REQUIRED")
    issuance_commit = _verify_current_packet_git_objects(project_root, root, expected)
    manifest = _load_canonical(root / "manifest.json")
    if manifest.get("packet_identity") != _sha(_canonical(
            {key: value for key, value in manifest.items() if key != "packet_identity"})):
        raise ValueError("STAGE_C_PACKET_SEAL_INVALID")
    expected_hashed = expected - {"manifest.json", "authority-receipt-issued.json"}
    if set(manifest.get("file_sha256", {})) != expected_hashed:
        raise ValueError("STAGE_C_PACKET_HASH_SET_INVALID")
    for name, digest in manifest["file_sha256"].items():
        if _sha((root / name).read_bytes()) != digest:
            raise ValueError("STAGE_C_PACKET_FILE_HASH_MISMATCH")
    request = _load_canonical(root / "stage-c-request.json")
    candidate_receipt = _load_canonical(root / "authority-receipt-candidate.json")
    authority = _load_canonical(root / "authority-receipt-issued.json")
    authority_body = {key: value for key, value in authority.items() if key != "authority_receipt_identity"}
    authority_identity = _sha(_canonical(authority_body))
    if not (authority.get("authority_receipt_identity") == authority_identity
            == candidate_receipt.get("proposed_receipt_identity")
            == manifest.get("authority_reference_if_issued")
            and candidate_receipt.get("authority_body") == authority_body
            and candidate_receipt.get("receipt_status") == "UNISSUED"
            and candidate_receipt.get("authority_receipt_identity") is None
            and authority_body.get("stage_p_authorized") is False
            and authority_body.get("stage_c_authorized") is True
            and authority_body.get("attempt_ceiling") == 1):
        raise ValueError("STAGE_C_AUTHORITY_BINDING_INVALID")
    frozen = admit_frozen_stage_c_case01_input_v1_2_1(
        raw_ledger=(root / "frozen-stage-p-ledger.json").read_bytes(),
        candidate=base64.b64decode(request["candidate_utf8_base64"], validate=True),
        factual_authority=base64.b64decode(request["factual_authority_utf8_base64"], validate=True),
        raw_evaluation_receipt=(root / "semantic-evaluation-receipt.json").read_bytes(),
        raw_closure_receipt=(root / "case01-closure-receipt.json").read_bytes())
    expected_request = {
        "schema_name": "pastila-semantic-admission-v2-stage-c-case01-request",
        "schema_version": "1.2.1", "case_id": CASE_ID,
        "operation": "EVALUATE_FROZEN_STAGE_P_LEDGER_ONCE",
        "stage_p_calls_authorized": 0, "stage_c_calls_authorized": 1,
        "frozen_input_identity": frozen.binding_identity,
        "evidence_commit": EVIDENCE_COMMIT, "evaluation_commit": EVALUATION_COMMIT,
        "closure_commit": CLOSURE_COMMIT, "raw_output_sha256": RAW_OUTPUT_SHA256,
        "evaluation_receipt_identity": EVALUATION_RECEIPT_IDENTITY,
        "closure_receipt_identity": CLOSURE_RECEIPT_IDENTITY,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "semantic_policy_identity": CASE01_CANONICAL_POLICY_IDENTITY,
        "topology": EXPECTED_TOPOLOGY,
        "candidate_utf8_base64": request.get("candidate_utf8_base64"),
        "factual_authority_utf8_base64": request.get("factual_authority_utf8_base64"),
        "frozen_ledger_sha256": RAW_OUTPUT_SHA256,
        "child_timeout_seconds": CHILD_TIMEOUT_SECONDS,
        "retry": 0, "fallback": 0, "repair": 0, "selection": 0,
    }
    if request != expected_request:
        raise ValueError("STAGE_C_REQUEST_AUTHORITY_BINDING_INVALID")
    if ((root / "frozen-stage-p-ledger.json").read_bytes()
            != _git_blob(project_root, EVIDENCE_COMMIT, RAW_LEDGER_RELATIVE)
            or (root / "semantic-evaluation-receipt.json").read_bytes()
            != _git_blob(project_root, EVALUATION_COMMIT, EVALUATION_RELATIVE)
            or (root / "case01-closure-receipt.json").read_bytes()
            != _git_blob(project_root, CLOSURE_COMMIT, CLOSURE_RELATIVE)):
        raise ValueError("STAGE_C_FROZEN_COMMIT_BLOB_BINDING_INVALID")
    source_lineage = _source_lineage(project_root)
    if manifest.get("source_lineage_sha256") != source_lineage:
        raise ValueError("STAGE_C_SOURCE_LINEAGE_MISMATCH")
    args = ("-m", RUNNER_MODULE, windows_path_to_wsl_v1(root / "stage-c-request.json"),
            windows_path_to_wsl_v1(root / "authority-receipt-issued.json"),
            windows_path_to_wsl_v1(root / "frozen-stage-p-ledger.json"),
            windows_path_to_wsl_v1(evidence_root / "linux-stage-c"))
    command_plan = boundary.build_invocation(
        consumer_id=CONSUMER_ID, authority_reference="0" * 64, arguments=args)
    plan_files = expected_hashed - {"authority-receipt-candidate.json", "host-binding.json"}
    plan = {
        "schema": "STAGE_C_CASE01_PACKET_PLAN_V1_2_1",
        "packet_root": str(root), "evidence_root": str(evidence_root),
        "frozen_input_identity": frozen.binding_identity,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "semantic_policy_identity": CASE01_CANONICAL_POLICY_IDENTITY,
        "wsl_binding_identity": STAGE_C_WSL_BINDING_IDENTITY,
        "host_identity": STAGE_C_HOST_IDENTITY,
        "command_plan_identity": command_plan.command_identity,
        "source_lineage_sha256": source_lineage,
        "plan_file_sha256": {name: _sha((root / name).read_bytes())
                             for name in sorted(plan_files)},
    }
    packet_plan_identity = _sha(_canonical(plan))
    host_binding = _load_canonical(root / "host-binding.json")
    expected_evidence_identity = _sha(_canonical({
        "schema": "STAGE_C_CASE01_EVIDENCE_ROOT_V1_2_1",
        "path": str(evidence_root), "command_identity": manifest.get("command_identity"),
        "frozen_input_identity": frozen.binding_identity,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
    }))
    fixed = (
        manifest.get("schema_version") == "1.2.1"
        and manifest.get("receipt_status") == "UNISSUED"
        and manifest.get("attempts") == {"completed": 0, "ceiling": 1}
        and all(value is False for value in manifest.get("execution", {}).values())
        and manifest.get("stage_p_calls_authorized") == 0
        and manifest.get("stage_c_calls_authorized") == 1
        and manifest.get("frozen_input_identity") == frozen.binding_identity
        and manifest.get("raw_output_sha256") == RAW_OUTPUT_SHA256
        and manifest.get("source_context_identity") == SOURCE_CONTEXT_IDENTITY
        and manifest.get("semantic_policy_identity") == CASE01_CANONICAL_POLICY_IDENTITY
        and manifest.get("evaluation_receipt_identity") == EVALUATION_RECEIPT_IDENTITY
        and manifest.get("closure_receipt_identity") == CLOSURE_RECEIPT_IDENTITY
        and manifest.get("topology") == EXPECTED_TOPOLOGY
        and manifest.get("proposed_evidence_root") == str(evidence_root)
        and manifest.get("evidence_root_identity") == expected_evidence_identity
        and manifest.get("packet_plan_identity") == packet_plan_identity
        and authority_body.get("packet_plan_identity") == packet_plan_identity
        and authority_body.get("command_plan_identity") == command_plan.command_identity
        and authority_body.get("frozen_input_identity") == frozen.binding_identity
        and authority_body.get("raw_output_sha256") == RAW_OUTPUT_SHA256
        and authority_body.get("source_context_identity") == SOURCE_CONTEXT_IDENTITY
        and authority_body.get("semantic_policy_identity") == CASE01_CANONICAL_POLICY_IDENTITY
        and authority_body.get("evaluation_receipt_identity") == EVALUATION_RECEIPT_IDENTITY
        and authority_body.get("closure_receipt_identity") == CLOSURE_RECEIPT_IDENTITY
        and authority_body.get("wsl_binding_identity") == STAGE_C_WSL_BINDING_IDENTITY
        and authority_body.get("host_identity") == STAGE_C_HOST_IDENTITY
        and host_binding.get("binding_identity") == STAGE_C_WSL_BINDING_IDENTITY
        and host_binding.get("host_identity") == STAGE_C_HOST_IDENTITY
        and host_binding.get("packet_plan_identity") == packet_plan_identity
        and host_binding.get("frozen_input_identity") == frozen.binding_identity
        and host_binding.get("source_lineage_sha256") == source_lineage
        and host_binding.get("command") == manifest.get("command")
        and host_binding.get("command_identity") == manifest.get("command_identity")
        and host_binding.get("prospective_execute_edges") == 1
        and host_binding.get("observed_execute_calls") == 0
    )
    if not fixed:
        raise ValueError("STAGE_C_PACKET_BINDING_INVALID")
    return manifest, authority, request, frozen, issuance_commit


def _verify_current_packet_git_objects(
    project_root: Path, packet_root: Path, expected: set[str]
) -> str:
    """Require every admitted packet byte to be present in the current commit."""
    relative_root = packet_root.relative_to(project_root)
    if relative_root != PACKET_RELATIVE:
        raise ValueError("STAGE_C_PACKET_CANONICAL_PATH_REQUIRED")
    receipt_relative = relative_root / "authority-receipt-issued.json"
    try:
        commits = subprocess.check_output(
            ("git", "log", "--diff-filter=A", "--format=%H", "--",
             receipt_relative.as_posix()), cwd=project_root,
            stderr=subprocess.DEVNULL, text=True).splitlines()
        if len(commits) != 1:
            raise ValueError("STAGE_C_UNIQUE_ISSUANCE_COMMIT_REQUIRED")
        commit = commits[0]
        subprocess.check_call(
            ("git", "merge-base", "--is-ancestor", commit, "HEAD"),
            cwd=project_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        changed = subprocess.check_output(
            ("git", "diff-tree", "--no-commit-id", "--name-status", "-r", commit),
            cwd=project_root, stderr=subprocess.DEVNULL, text=True).splitlines()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("STAGE_C_ISSUANCE_COMMIT_UNAVAILABLE") from exc
    if changed != [f"A\t{receipt_relative.as_posix()}"]:
        raise ValueError("STAGE_C_ISSUANCE_COMMIT_SCOPE_INVALID")
    for name in sorted(expected):
        if _git_blob(project_root, commit, relative_root / name) != (packet_root / name).read_bytes():
            raise ValueError("STAGE_C_PACKET_GIT_OBJECT_MISMATCH")
    return commit


def _source_lineage(root: Path) -> dict[str, str]:
    names = (
        "stage_p_construction_obligation_v2_durable_filesystem_sink_v1.py",
        "stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1.py",
        "stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_2_1.py",
        "stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_2_1.py",
        "stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1.py",
        "stage_p_construction_obligation_semantic_completeness_v1.py",
        "gate_f_constraint_v1.py", "gate_f_trie_projector_v1.py",
        "stage_c_case01_linux_runner_v1_2_1.py",
    )
    base = root / "src/pastila_scout/semantic_admission_v2"
    lineage = {name: _sha((base / name).read_bytes()) for name in names}
    child_runner = root / "src/pastila_scout/experimental_core_v1_2_gate_f_constrained_runner.py"
    lineage[child_runner.name] = _sha(child_runner.read_bytes())
    return lineage


def _git_blob(root: Path, commit: str, relative: Path) -> bytes:
    try:
        return subprocess.check_output(
            ("git", "show", f"{commit}:{relative.as_posix()}"), cwd=root,
            stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("STAGE_C_REQUIRED_GIT_OBJECT_UNAVAILABLE") from exc


def _load_canonical(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8", errors="strict"))
    if type(value) is not dict or raw != _canonical(value):
        raise ValueError("STAGE_C_CANONICAL_JSON_REQUIRED")
    return value


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exclusive(path: Path, raw: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()


__all__ = ("PreparedStageCCase01WslInvocationV1_2_1",
           "StageCCase01HostOutcomeV1_2_1", "materialize_stage_c_case01_packet_v1_2_1",
           "prepare_stage_c_case01_wsl_invocation_v1_2_1",
           "execute_stage_c_case01_host_v1_2_1")
