"""Prepared one-shot Role Coherence V1 Case 01 probe; not yet authorized to execute."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from .stage_p_phase_receipt_v2 import execute_and_capture_stage_p_v2, persist_phase_receipt_v2
from .stage_p_role_coherence_contract_v1 import RoleCoherentLedgerV1, validate_role_coherent_source_membership
from .stage_p_role_coherence_durable_executor_v1 import DurableRoleCoherenceStagePExecutorV1
from .stage_p_role_coherence_evaluator_v1 import StagePRoleCoherenceEvaluatorV1


PACK_RELATIVE = Path("docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json")
PACK_SHA256 = "4163307ccb8cfa8997b520a1cea04cddacd347e9b1ffde498db925ffccac6c2d"
CASE_ID = "HMCV1-SASC-01"


def _write_exclusive(path: Path, value: object) -> None:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def construct(*, project_root: Path, evidence_root: Path):
    raw = (project_root / PACK_RELATIVE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PACK_SHA256:
        raise RuntimeError("proof pack identity drift")
    matches = [item for item in json.loads(raw)["cases"] if item["case_id"] == CASE_ID]
    if len(matches) != 1:
        raise RuntimeError("Case 01 selection drift")
    case = matches[0]
    request = {"stage_id": "PROPOSITION_LEDGER", "factual_summary": case["factual_summary"], "candidate": case["candidate"]}
    executor = DurableRoleCoherenceStagePExecutorV1(
        project_root=project_root, durable_lifecycle_root=evidence_root / "durable-lifecycle",
    )
    evaluator = StagePRoleCoherenceEvaluatorV1(project_root=project_root, executor=executor, timeout_seconds=240.0)
    binding = {
        "case_id": CASE_ID, "pack_sha256": PACK_SHA256,
        "factual_summary_sha256": case["factual_summary_sha256"], "candidate_sha256": case["candidate_sha256"],
        "candidate_identity": evaluator.candidate_identity, "prompt_identity": evaluator.prompt_identity,
        "schema_identity": evaluator.schema_identity, "grammar_identity": evaluator.grammar_identity,
        "model_identity": evaluator.model_identity, "maximum_provider_calls": 1, "retry_count": 0,
        "repair_count": 0, "selection_count": 0, "projector_bound": False,
        "stage_c_constructed": False, "stage_c_called": False,
    }
    return request, binding, evaluator


def run(*, project_root: Path, evidence_root: Path):
    evidence_root.mkdir(parents=True, exist_ok=False)
    request, binding, evaluator = construct(project_root=project_root, evidence_root=evidence_root)
    _write_exclusive(evidence_root / "stage-p-request.json", request)
    _write_exclusive(evidence_root / "identity-binding.json", binding)
    receipt = execute_and_capture_stage_p_v2(
        evaluator=evaluator, request=request, raw_path=evidence_root / "stage-p-raw.bin",
        schema_validator=lambda data: RoleCoherentLedgerV1.model_validate_json(data, strict=True),
        membership_validator=lambda ledger: validate_role_coherent_source_membership(
            ledger, factual_summary=request["factual_summary"], candidate=request["candidate"],
        ),
    )
    persist_phase_receipt_v2(evidence_root / "stage-p-phase-receipt-v2.json", receipt)
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: runner PROJECT_ROOT EVIDENCE_ROOT")
    value = run(project_root=Path(sys.argv[1]), evidence_root=Path(sys.argv[2]))
    print(json.dumps(value.as_json_value(), ensure_ascii=False))
