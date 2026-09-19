"""Fail-closed, read-only input closure for completed V15 R4 adjudication."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

R4_AUTHORITY = "a1bbd95e21b73c903a99d661c43a53448c7d50dab38c95c09e143b5d40740aa9"
R4_ATTEMPT = "6671bb3c42a30a66848f95481618e21d604bd12b393b5de942e6851e92232578"
R4_ATTEMPT_SHA256 = "0143a388bceec186de8463eb49b1c53fd98d22e1faebf48c31d4daa01f7b1c35"
R4_COMPLETION = "5067e19c3b136d1215c0093815baf5864d21232b6719c59230ddd63ae173f3c5"
R4_COMPLETION_SHA256 = "05afc403c32402fa1dc1e2f1018fe794fe54c9e6708e90c9a266411b0b4a115d"
R4_ARTIFACT_ROOT = "d74fe24e49db127d92fe03c2591bdcef13aa0ae67b56f601aab5995c024dac2a"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode()


def identity(value: object) -> str:
    return sha256(canonical(value))


def execution_identity(value: object) -> str:
    """Identity used by the frozen execution producer (insertion-order JSON)."""
    return sha256(json.dumps(value, ensure_ascii=False, allow_nan=False,
                             separators=(",", ":")).encode())


def _read_regular(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"R4 evidence object invalid: {path}")
    return path.read_bytes()


def close_r4_evidence(output: Path, schedule: list[Mapping[str, object]]) -> dict[str, object]:
    """Validate immutable completion evidence and derive a blinded adjudication index."""
    if output.is_symlink() or not output.is_dir():
        raise ValueError("R4 output root invalid")
    before = {str(p.relative_to(output)): sha256(_read_regular(p))
              for p in sorted(output.rglob("*")) if p.is_file()}
    if "terminal-failure.json" in before or len(schedule) != 2400:
        raise ValueError("R4 is not one successful frozen 2400-row completion")
    attempt_raw = _read_regular(output / "attempt.json")
    completion_raw = _read_regular(output / "completion.json")
    if sha256(attempt_raw) != R4_ATTEMPT_SHA256 or sha256(completion_raw) != R4_COMPLETION_SHA256:
        raise ValueError("R4 terminal artifact identity drift")
    attempt, completion = json.loads(attempt_raw), json.loads(completion_raw)
    if (attempt.get("attempt_identity") != R4_ATTEMPT
            or completion.get("completion_identity") != R4_COMPLETION
            or completion.get("artifact_root") != R4_ARTIFACT_ROOT):
        raise ValueError("R4 terminal claim drift")
    inventory = completion.get("artifact_inventory")
    if not isinstance(inventory, list):
        raise ValueError("R4 completion inventory absent")
    attempt_core = dict(attempt); attempt_claim = attempt_core.pop("attempt_identity", None)
    completion_core = dict(completion); completion_claim = completion_core.pop("completion_identity", None)
    if (attempt_claim != execution_identity(attempt_core)
            or attempt.get("execution_authority_identity") != R4_AUTHORITY
            or attempt.get("matrix_rows") != 2400
            or attempt.get("attempt_ordinal") != 1
            or attempt.get("retry_or_redraw_authorized") is not False
            or attempt.get("promotion_effect") is not False
            or attempt.get("status") != "CONSUMED_BEFORE_EXECUTION"
            or completion_claim != execution_identity(completion_core)
            or completion.get("completed_rows") != 2400
            or completion.get("retry_or_redraw") is not False
            or completion.get("adjudication_performed") is not False
            or completion.get("promotion_effect") is not False):
        raise ValueError("R4 attempt/completion semantic closure mismatch")
    artifacts = {str(row["path"]): _read_regular(output / str(row["path"])) for row in inventory}
    observed_inventory = [{"path": path, "sha256": sha256(raw)} for path, raw in sorted(artifacts.items())]
    if (inventory != observed_inventory or completion.get("artifact_root") != execution_identity(inventory)
            or artifacts.get("attempt.json") != json.dumps(
                attempt, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode()
            or len(inventory) != 12073):
        raise ValueError("R4 completion inventory closure mismatch")
    rows = []
    for row in schedule:
        directory = (f"materialization-{row['materialization']}/repetition-{row['repetition']}/"
                     f"{row['candidate_alias']}")
        receipt_matches = [path for path in artifacts
                           if path.startswith(f"{directory}/{row['case_id']}.")
                           and path.endswith(".receipt.json")]
        if len(receipt_matches) != 1:
            raise ValueError("R4 scheduled receipt membership mismatch")
        receipt_path = receipt_matches[0]
        stem = receipt_path.removeprefix(f"{directory}/").removesuffix(".receipt.json")
        raw_path = f"{directory}/results/{stem}.raw"
        observation_path = f"{directory}/results/{stem}.observation.json"
        receipt = json.loads(artifacts[receipt_path])
        observation = json.loads(artifacts[observation_path])
        receipt_core = dict(receipt); receipt_identity = receipt_core.pop("receipt_identity", None)
        observation_core = dict(observation); observation_identity = observation_core.pop("observation_identity", None)
        if (receipt_identity != execution_identity(receipt_core)
                or observation_identity != execution_identity(observation_core)
                or receipt.get("global_ordinal") != row["global_ordinal"]
                or receipt.get("candidate_alias") != row["candidate_alias"]
                or receipt.get("case_id") != row["case_id"]
                or receipt.get("request_identity") != f"sha256:{stem.rsplit('.', 1)[1]}"
                or receipt.get("raw_output_sha256") != sha256(artifacts[raw_path])
                or receipt.get("observation_identity") != observation_identity
                or receipt.get("retry_or_redraw") is not False
                or receipt.get("adjudication_performed") is not False
                or receipt.get("promotion_effect") is not False):
            raise ValueError("R4 row evidence closure mismatch")
        rows.append({
            "global_ordinal": row["global_ordinal"],
            "materialization": row["materialization"],
            "repetition": row["repetition"],
            "candidate_alias": row["candidate_alias"],
            "case_id": row["case_id"],
            "request_identity": receipt["request_identity"],
            "execution_receipt_identity": receipt["receipt_identity"],
            "structural_status": receipt["structural_status"],
            "raw_output_sha256": sha256(artifacts[raw_path]),
            "observation_sha256": sha256(artifacts[observation_path]),
        })
    if len(rows) != 2400 or [r["global_ordinal"] for r in rows] != list(range(1, 2401)):
        raise ValueError("R4 adjudication row closure mismatch")
    after = {str(p.relative_to(output)): sha256(_read_regular(p))
             for p in sorted(output.rglob("*")) if p.is_file()}
    if before != after:
        raise ValueError("R4 evidence changed during read-only closure")
    return {
        "attempt_identity": R4_ATTEMPT,
        "attempt_sha256": R4_ATTEMPT_SHA256,
        "completion_identity": R4_COMPLETION,
        "completion_sha256": R4_COMPLETION_SHA256,
        "artifact_root": R4_ARTIFACT_ROOT,
        "artifact_count": len(inventory),
        "row_count": len(rows),
        "structurally_valid_rows": sum(r["structural_status"] == "STRUCTURALLY_VALID_PENDING_ADJUDICATION" for r in rows),
        "structurally_failed_rows": sum(r["structural_status"] == "FAIL_CLOSED_INVALID_OUTPUT" for r in rows),
        "adjudication_input_root": identity(rows),
        "evidence_inventory_root": identity([{"path": k, "sha256": v} for k, v in before.items()]),
    }
