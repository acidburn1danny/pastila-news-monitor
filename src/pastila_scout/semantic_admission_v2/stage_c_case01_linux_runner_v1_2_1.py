"""Linux Stage C Case 01 V1.2.1 supervisor using the current durable sink."""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .source_span_validation_v1 import validate_reason_span_sources_v1
from .stage_c_case01_frozen_input_v1_2_1 import (
    CASE_ID, CLOSURE_RECEIPT_IDENTITY, EVALUATION_RECEIPT_IDENTITY,
    RAW_OUTPUT_SHA256, SOURCE_CONTEXT_IDENTITY,
    admit_frozen_stage_c_case01_input_v1_2_1,
)
from .stage_p_construction_obligation_v2_durable_filesystem_sink_v1 import (
    DurableEvidenceRootBindingV1, create_durable_filesystem_sink_v1_2_1,
)
from .stage_p_construction_obligation_v2_generation_v1_2_1_identity_contract import (
    SUPERVISOR_IDENTITY,
)

CHILD_TIMEOUT_SECONDS = 1200.0
SYSTEM_PROMPT = Path(
    "/mnt/c/Projects/pastila-news-monitor/.experimental-0-3-core-v1-2-"
    "journalistic-deontology-prime-directive-v1-evidence/"
    "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt")
STAGE_C_PROMPT = Path(
    "/mnt/c/Projects/pastila-news-monitor/docs/artifacts/"
    "semantic-admission-v2-stage-c-prompt-v1.txt")
CHILD_MODULE = "pastila_scout.semantic_admission_v2.stage_c_case01_linux_runner_v1_2_1"


def supervise(request_path: Path, authority_path: Path, ledger_path: Path,
              evidence_root: Path) -> int:
    request = _load(request_path)
    authority = _load(authority_path)
    body = {key: value for key, value in authority.items() if key != "authority_receipt_identity"}
    receipt_identity = _sha(_canonical(body))
    if not (authority.get("authority_receipt_identity") == receipt_identity
            and body.get("case_id") == CASE_ID
            and body.get("operation") == "EVALUATE_FROZEN_STAGE_P_LEDGER_ONCE"
            and body.get("stage_p_authorized") is False
            and body.get("stage_c_authorized") is True
            and body.get("attempt_ceiling") == 1
            and request.get("stage_p_calls_authorized") == 0
            and request.get("stage_c_calls_authorized") == 1):
        raise ValueError("STAGE_C_LINUX_AUTHORITY_INVALID")
    candidate = base64.b64decode(request["candidate_utf8_base64"], validate=True)
    factual = base64.b64decode(request["factual_authority_utf8_base64"], validate=True)
    packet_root = request_path.parent
    frozen = admit_frozen_stage_c_case01_input_v1_2_1(
        raw_ledger=ledger_path.read_bytes(), candidate=candidate,
        factual_authority=factual,
        raw_evaluation_receipt=(packet_root / "semantic-evaluation-receipt.json").read_bytes(),
        raw_closure_receipt=(packet_root / "case01-closure-receipt.json").read_bytes())
    if not (request.get("frozen_input_identity") == frozen.binding_identity
            == body.get("frozen_input_identity")
            and request.get("raw_output_sha256") == RAW_OUTPUT_SHA256
            and request.get("source_context_identity") == SOURCE_CONTEXT_IDENTITY
            and request.get("evaluation_receipt_identity") == EVALUATION_RECEIPT_IDENTITY
            and request.get("closure_receipt_identity") == CLOSURE_RECEIPT_IDENTITY):
        raise ValueError("STAGE_C_LINUX_FROZEN_INPUT_BINDING_INVALID")
    sink = create_durable_filesystem_sink_v1_2_1(
        root=evidence_root,
        binding=DurableEvidenceRootBindingV1(
            provider_request_id="stage-c-case01:" + frozen.binding_identity,
            source_context_identity=SOURCE_CONTEXT_IDENTITY,
            authority_receipt_identity=receipt_identity,
            supervisor_candidate_identity=SUPERVISOR_IDENTITY))
    receipts: list[str] = []
    def persist(label: str, value: bytes | dict[str, object]) -> None:
        raw = value if type(value) is bytes else _canonical(value)
        artifact = sink.persist(label, raw)
        receipt = sink.persist(label + ".receipt", artifact.canonical_receipt)
        receipts.extend((artifact.receipt_identity, receipt.receipt_identity))
    persist("lifecycle-00001-stage-c-admitted.json", {
        "event": "STAGE_C_ADMITTED", "frozen_input_identity": frozen.binding_identity,
        "authority_receipt_identity": receipt_identity})
    template = STAGE_C_PROMPT.read_text("utf-8")
    prompt = (template.replace("{factual_summary}", factual.decode("utf-8"))
              .replace("{candidate}", candidate.decode("utf-8"))
              .replace("{stage_p_ledger}", frozen.raw_ledger.decode("utf-8")))
    started = time.monotonic()
    status, failure = "EXECUTION_FAILURE", None
    with tempfile.TemporaryDirectory(prefix="pastila-stage-c-v1-2-1-") as directory:
        temp = Path(directory)
        payload, response = temp / "request.json", temp / "response.json"
        lifecycle, child_stdout, child_stderr = temp / "lifecycle.json", b"", b""
        payload.write_bytes(_canonical({"prompt": prompt, "max_new_tokens": 1400}))
        persist("lifecycle-00002-model-process-started.json", {
            "event": "MODEL_PROCESS_STARTED", "elapsed_ms": 0})
        command = (sys.executable, "-m", CHILD_MODULE, "--child",
                   str(payload), str(response), str(SYSTEM_PROMPT), str(lifecycle))
        try:
            completed = subprocess.run(command, check=False, capture_output=True,
                                       timeout=CHILD_TIMEOUT_SECONDS)
            child_stdout, child_stderr = completed.stdout, completed.stderr
            persist("child-stdout.bin", child_stdout)
            persist("child-stderr.bin", child_stderr)
            if lifecycle.is_file():
                persist("child-lifecycle.json", lifecycle.read_bytes())
            if completed.returncode != 0 or not response.is_file():
                failure = "STAGE_C_CHILD_EXECUTION_FAILURE"
            else:
                response_bytes = response.read_bytes()
                persist("child-response.json", response_bytes)
                try:
                    response_value = _load(response)
                    if set(response_value) != {"output", "terminal_eos", "constraint_active"}:
                        raise ValueError("STAGE_C_CHILD_RESPONSE_SCHEMA_INVALID")
                    raw_output = response_value["output"]
                    if (type(raw_output) is not str
                            or response_value["terminal_eos"] is not True
                            or response_value["constraint_active"] is not True):
                        failure = "STAGE_C_TERMINAL_OUTPUT_INVALID"
                    else:
                        raw_bytes = raw_output.encode("utf-8")
                        persist("raw-output.bin", raw_bytes)
                        validated = validate_reason_span_sources_v1(
                            raw_response=raw_output,
                            factual_summary=factual.decode("utf-8"),
                            candidate=candidate.decode("utf-8"))
                        status = "TERMINAL_OUTPUT"
                        persist("lifecycle-00003-stage-c-terminal.json", {
                            "event": "STAGE_C_TERMINAL", "raw_output_sha256": _sha(raw_bytes),
                            "decision": validated.decision.value})
                except Exception as exc:
                    failure = "STAGE_C_RESPONSE_VALIDATION_FAILURE:" + type(exc).__name__
                    persist("response-validation-failure.json", {
                        "failure": failure, "exception_type": type(exc).__name__,
                        "child_response_sha256": _sha(response_bytes)})
        except subprocess.TimeoutExpired as exc:
            child_stdout = bytes(exc.stdout or b"")
            child_stderr = bytes(exc.stderr or b"")
            persist("child-stdout.bin", child_stdout)
            persist("child-stderr.bin", child_stderr)
            failure = "STAGE_C_CHILD_TIMEOUT"
        except Exception as exc:
            failure = "STAGE_C_VALIDATION_FAILURE:" + type(exc).__name__
        cleanup = {"event": "CLEANUP_OBSERVED", "child_process_terminated": True,
                   "gpu_state_observed": False, "failure": failure}
        persist("cleanup-observation.json", cleanup)
    result = {"schema_name": "pastila-semantic-admission-v2-stage-c-linux-result",
              "schema_version": "1.2.1", "status": status, "failure": failure,
              "elapsed_ms": round((time.monotonic() - started) * 1000, 3),
              "authority_receipt_identity": receipt_identity,
              "frozen_input_identity": frozen.binding_identity,
              "durable_receipt_identities": receipts, "retry_count": 0}
    result["result_identity"] = _sha(_canonical(result))
    persist("result-envelope.json", result)
    return 0 if status == "TERMINAL_OUTPUT" else 20


def _child(args: list[str]) -> int:
    if len(args) != 4:
        return 64
    from pastila_scout.experimental_core_v1_2_gate_f_constrained_runner import run
    run(*map(Path, args))
    return 0


def _load(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8", errors="strict"))
    if type(value) is not dict or raw != _canonical(value):
        raise ValueError("STAGE_C_LINUX_CANONICAL_JSON_REQUIRED")
    return value


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


if __name__ == "__main__":
    if len(sys.argv) == 6 and sys.argv[1] == "--child":
        raise SystemExit(_child(sys.argv[2:]))
    if len(sys.argv) == 5:
        raise SystemExit(supervise(*map(Path, sys.argv[1:])))
    raise SystemExit(64)
